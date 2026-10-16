# -*- coding: utf-8 -*-
import json
import math
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from syspy import Di, Distance, Laser, Loc, Motor, Navigation, NavSpeed, Recognize, RobotParam, ScriptStatus, _TR
from syspy.utils.param_server import BindType, ParamType

from standard.fork import ConfigParams, Fork
from standard.fork_utils import (
    CH_POLICY,
    EPS,
    ActionStatus,
    GoPathWithContactDi as BaseGoPathWithContactDi,
    Rec,
    RunMotorByPosition,
    RunMotorBySpeed,
    _policy_effective_value,
    _trace_log,
    _trace_chart,
    emit_event,
    emit_policy,
    _init_action_runtime,
    apply_tcp_target,
    build_path_adjust_plan,
    clamp,
    get_r_loc,
    has_valid_target_pos,
    load_pallet_z_offset,
    calculate_recognition_pick_height,
    create_start_height_param,
    update_back_laser_clear_region_by_height,
)
from syspy.lib.action_task import ActionBase
from syspy.lib.module import pos2Base, pos2World
from standard.weighing_scale import create_scale, weight_to_kg


def _softbag_period_run(robot, fork_height):
    update_back_laser_clear_region_by_height(robot, fork_height, ConfigParams)


def _normalize_recognition_class(value: Any) -> str:
    return str(value or "").strip().lower().replace("_", "").replace("-", "")


def _get_dm_rec_candidates(results: Dict[str, Any]) -> List[Dict[str, Any]]:
    reco_list = results.get("recoList") or []
    dm_candidates = []
    fallback_candidates = []
    for item in reco_list:
        if not isinstance(item, dict) or not item.get("valid", True):
            continue
        object_message = str(item.get("objectMessage", "")).strip()
        if object_message:
            fallback_candidates.append(item)
        if "dm" in _normalize_recognition_class(item.get("class")):
            dm_candidates.append(item)
    return dm_candidates or fallback_candidates


def _get_rec_candidate_xy(item: Dict[str, Any]) -> Optional[List[float]]:
    for result_key in ("robotResult", "worldResult"):
        result = item.get(result_key) or {}
        if not isinstance(result, dict):
            continue
        try:
            return [float(result.get("x")), float(result.get("y"))]
        except (TypeError, ValueError):
            continue
    return None


def _select_dm_rec_result(results: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    candidates = _get_dm_rec_candidates(results)
    if not candidates:
        return None

    def _sort_key(item: Dict[str, Any]):
        xy = _get_rec_candidate_xy(item)
        if xy is None:
            return (1, float("inf"), float("inf"), float("inf"))
        x, y = xy
        return (0, x * x + y * y, abs(x), abs(y))

    return min(candidates, key=_sort_key)


def _extract_good_name_from_rec_results(results: Dict[str, Any]) -> str:
    candidate = _select_dm_rec_result(results)
    if candidate is not None:
        obj_msg = candidate.get("objectMessage", "")
        if obj_msg:
            return str(obj_msg).strip()
    return ""


def _load_dm_code_recognition_config(rec_file: str) -> Dict[str, Any]:
    if not rec_file:
        return {}

    try:
        return {
            "deviceName": RobotParam.getConfig("recognition", "recognitionObject.dmCode.deviceName", rec_file) or "",
            "tagSize": RobotParam.getConfig("recognition", "recognitionObject.dmCode.tagSize", rec_file),
        }
    except Exception as exc:
        _trace_log(f"load dmCode config failed, rec_file={rec_file}, err={exc}", name="fork.cfg")
        return {}


def _normalize_string_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if item is not None and str(item).strip()]
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("["):
            try:
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    return _normalize_string_list(parsed)
            except (TypeError, ValueError, json.JSONDecodeError):
                pass
        return [part.strip() for part in text.split(",") if part.strip()]
    return [str(value).strip()] if str(value).strip() else []


def _resolve_serial_port(serial_interface: str, default: str = "") -> str:
    serial_interface = str(serial_interface or "").strip()
    if not serial_interface:
        return str(default or "").strip()

    for path in ("portName", "basic.portName", "devName", "basic.devName"):
        try:
            port = RobotParam.getDevice(serial_interface, path)
            if port:
                return str(port).strip()
        except Exception as exc:
            _trace_log(
                f"read serial interface port failed, device={serial_interface}, path={path}, err={exc}",
                name="fork.cfg",
            )
    return str(default or "").strip()


def _softbag_config_reload(config_cls, cfg):
    config_cls.loadEndHeightExtra = cfg.get("loadEndHeightExtra", 0.0)
    config_cls.forkRootCollisionShape = cfg.get("forkRootCollisionShape", "")
    legacy_layer = cfg.get("stackGoodsLayerDefault")
    if cfg.get("loadPalletLayer") is None and legacy_layer is not None:
        config_cls.loadPalletLayer = max(1, int(config_cls._safe_float(legacy_layer, 1)))
    # 兼容仍读取旧名字的现场代码；新逻辑统一使用 loadPalletLayer。
    config_cls.stackGoodsLayerDefault = config_cls.loadPalletLayer
    config_cls.stackHoleZAvgThreshold = cfg.get("stackHoleZAvgThreshold", 0.01)
    config_cls.ultrasonicDiKeys = _normalize_string_list(cfg.get("ultrasonicDiKeys"))
    if not config_cls.ultrasonicDiKeys:
        config_cls.ultrasonicDiKeys = _normalize_string_list(
            [cfg.get("ultrasonicDiKey1", ""), cfg.get("ultrasonicDiKey2", "")]
        )
    config_cls.ultrasonicTriggerMode = cfg.get("ultrasonicTriggerMode", "two")
    config_cls.weightSerialInterface = cfg.get("weightSerialInterface", "")
    config_cls.weightPort = _resolve_serial_port(config_cls.weightSerialInterface, cfg.get("weightPort", ""))
    config_cls.weightBaudrate = cfg.get("weightBaudrate", 9600)
    config_cls.weightTimeout = cfg.get("weightTimeout", 0.3)
    config_cls.weightSlaveId = cfg.get("weightSlaveId", 1)
    config_cls.weightEmptyThreshold = cfg.get("weightEmptyThreshold", 300.0)
    config_cls.releaseSlowDownSpeed = cfg.get("releaseSlowDownSpeed", 0.01)


def _softbag_config_builder(config_cls, builder):
    with builder.GROUP(key="softbag", name=_TR("Softbag"), desc=_TR("Softbag scene settings")):
        builder.TYPE(ParamType.ARRAY)
        with builder.CHILDREN():
            with builder.CHILD(key="loadEndHeightExtra", name=_TR("Load End Height Extra"), desc=_TR("Additional fork lift height after loading")):
                builder.TYPE(ParamType.FLOAT)
                builder.DEFAULTVALUE(0.0)
                builder.UNIT("m")
            with builder.CHILD(key="forkRootCollisionShape", name=_TR("Fork Root Collision Shape"),
                               desc=_TR("Map region used by the rear fork-root laser during insertion")):
                builder.TYPE(ParamType.BIND_TYPE)
                builder.BINDTYPE(BindType.Shape.RECTANGLE)
            with builder.CHILD(key="stackHoleZAvgThreshold", name=_TR("Stack Hole Z Avg Threshold"), desc=_TR("Maximum Z difference between two holes on the same layer")):
                builder.TYPE(ParamType.FLOAT)
                builder.DEFAULTVALUE(0.01)
                builder.UNIT("m")
            with builder.CHILD(key="ultrasonicDiKeys", name=_TR("Ultrasonic DI Keys"), desc=_TR("Ultrasonic DI keys")):
                builder.TYPE(ParamType.BIND_TYPE)
                builder.BINDTYPE(BindType.Device.DI, multiple=True)
            with builder.CHILD(key="ultrasonicTriggerMode", name=_TR("Ultrasonic Trigger Mode"), desc=_TR("Number of ultrasonic DIs that must clear")):
                builder.TYPE(ParamType.COMBO_BOX)
                builder.DEFAULTVALUE("two")
                with builder.CHILDREN():
                    with builder.CHILD(key="one", name=_TR("One"), desc=_TR("Any DI is clear")):
                        builder.TYPE(ParamType.ARRAY)
                    with builder.CHILD(key="two", name=_TR("Two"), desc=_TR("Both DIs are clear")):
                        builder.TYPE(ParamType.ARRAY)

    with builder.GROUP(key="weight", name=_TR("Weight"), desc=_TR("Weight measurement configuration")):
        builder.TYPE(ParamType.ARRAY)
        with builder.CHILDREN():
            with builder.CHILD(key="weightSerialInterface", name=_TR("Weight Serial Interface"), desc=_TR("Serial interface for the weighing scale")):
                builder.TYPE(ParamType.BIND_TYPE)
                builder.ADD_FIELD("bind_type", "device:SerialInterface")
            with builder.CHILD(key="weightBaudrate", name=_TR("Weight Baudrate"), desc=_TR("Serial baud rate")):
                builder.TYPE(ParamType.INT)
                builder.DEFAULTVALUE(9600)
            with builder.CHILD(key="weightTimeout", name=_TR("Weight Timeout"), desc=_TR("Serial communication timeout")):
                builder.TYPE(ParamType.FLOAT)
                builder.DEFAULTVALUE(0.3)
                builder.UNIT("s")
            with builder.CHILD(key="weightSlaveId", name=_TR("Weight Slave Id"), desc=_TR("Modbus slave ID")):
                builder.TYPE(ParamType.INT)
                builder.DEFAULTVALUE(1)
            with builder.CHILD(key="weightEmptyThreshold", name=_TR("Weight Empty Threshold"), desc=_TR("Empty-load weight threshold")):
                builder.TYPE(ParamType.FLOAT)
                builder.DEFAULTVALUE(300.0)
                builder.UNIT("kg")
            with builder.CHILD(key="releaseSlowDownSpeed", name=_TR("Release Slow Down Speed"), desc=_TR("Slow lowering speed during unloading")):
                builder.TYPE(ParamType.FLOAT)
                builder.DEFAULTVALUE(0.01)
                builder.UNIT("m/s")


def _softbag_recognize_on_params(_input_cls, builder):
    with builder.CHILD(key="qrRecFile", name=_TR("Qr Rec File"), desc=_TR("QR-code recognition file for the 3D camera")):
        builder.TYPE(ParamType.STRING)
        builder.DEFAULTVALUE("")
    with builder.CHILD(key="goodsName", name=_TR("Goods Name"), desc=_TR("Expected goods name from QR-code recognition")):
        builder.TYPE(ParamType.STRING)
        builder.DEFAULTVALUE("")


class RecPalletSelect(Rec):
    def __init__(
            self,
            pallet_file: str,
            goods_layer: int,
            rec_base_height: float,
            rec_center_x: float = -1.0,
            rec_center_y: float = 0.0,
            rec_radius: float = 0.7,
            height_offset: float = 0.2,
            z_max: bool = True,
            min_height: float = 0.0,
            max_height: float = 2.0,
            clamp_fn: Callable[[float, float, float], float] = None,
    ):
        super().__init__(
            pallet_file,
            rec_center_x,
            rec_center_y,
            rec_radius,
            action_name="RecPalletSelect",
            z_max=z_max,
        )
        self.goods_layer = max(1, int(goods_layer))
        self.rec_base_height = float(rec_base_height)
        self.height_offset = float(height_offset)
        self.min_height = float(min_height)
        self.max_height = float(max_height)
        self.clamp_fn = clamp_fn
        self.selected_pick_height: Optional[float] = None
        self.selected_recognition_z: Optional[float] = None
        self.selected_world_pos: Optional[List[float]] = None
        self.selected_robot_pos: Optional[List[float]] = None
        self.selected_result: Dict[str, Any] = {}
        self.total_layers: int = 0

    def run(self, ctx=None):
        if not self.init:
            self.init = True
            self.success = False
            time.sleep(1)

        self.action_status = ActionStatus.RUNNING
        if not self.success:
            self.success, self.rec_status, self.results_dict = self.rec(self.recfile)
            return

        results_list = self.results_dict.get("recoList", [])
        self.obstacle_polygon = self.results_dict.get("obstaclePolygon", [])
        parsed_list = []
        for item in results_list:
            if not isinstance(item, dict):
                continue
            info_data = item.get("info", [])
            try:
                info_list = json.loads(info_data) if isinstance(info_data, str) else info_data
            except (TypeError, json.JSONDecodeError):
                _trace_log(f"skip invalid info data: {info_data}")
                continue
            if not isinstance(info_list, list):
                continue
            info_count = len(info_list)
            info_item = None
            for info in info_list:
                if isinstance(info, str):
                    try:
                        info = json.loads(info)
                    except (TypeError, json.JSONDecodeError):
                        continue
                if isinstance(info, dict) and info.get("robotResultZ") is not None:
                    info_item = info
                    break
            if info_item is None:
                continue
            world_result = item.get("worldResult", {}) if isinstance(item.get("worldResult"), dict) else {}
            robot_result = item.get("robotResult", {}) if isinstance(item.get("robotResult"), dict) else {}
            parsed_list.append({
                "z": float(info_item.get("robotResultZ")),
                "world": [
                    float(world_result.get("x", item.get("x", 0.0))),
                    float(world_result.get("y", item.get("y", 0.0))),
                    float(world_result.get("yaw", item.get("yaw", 0.0))),
                ],
                "robot": [
                    float(robot_result.get("x", item.get("x", 0.0))),
                    float(robot_result.get("y", item.get("y", 0.0))),
                    float(robot_result.get("yaw", item.get("yaw", 0.0))),
                ],
                "info_count": info_count,
                "raw": item,
            })

        if not parsed_list:
            self.action_status = ActionStatus.FAILED
            return

        parsed_list.sort(key=lambda item: item["z"], reverse=True)
        avg_selected_z = None
        single_layer_two_holes = len(parsed_list) == 2 and all(item.get("info_count") == 1 for item in parsed_list)
        if single_layer_two_holes:
            self.total_layers = 1
            hole_z_avg_threshold = max(0.0, float(ConfigParams.stackHoleZAvgThreshold or 0.0))
            hole_z_diff = abs(parsed_list[0]["z"] - parsed_list[1]["z"])
            if hole_z_diff > hole_z_avg_threshold:
                avg_selected_z = (parsed_list[0]["z"] + parsed_list[1]["z"]) / 2.0
                _trace_log(
                    f"single layer two holes detected, use avg z={avg_selected_z}, "
                    f"left_right_diff={hole_z_diff}, threshold={hole_z_avg_threshold}"
                )
        else:
            self.total_layers = len(parsed_list)
        for idx, item in enumerate(parsed_list):
            _trace_log(f"\n############## parsed_list idx:{idx}, z:{item['z']}, world:{item['world']}, robot:{item['robot']} #########\n")
        if self.goods_layer > self.total_layers:
            Navigation.setTaskError(
                "GoodsLayerOutOfRange",
                f"requested goods layer {self.goods_layer}, but recognition found {self.total_layers} layers",
            )
            self.action_status = ActionStatus.FAILED
            return
        idx = self.goods_layer - 1
        selected = dict(parsed_list[idx])
        if avg_selected_z is not None:
            selected["z"] = avg_selected_z
        _trace_log(f"\n############### sleected idx: {idx}, z: {selected['z']} #############################\n")

        self.results_list = [selected["raw"]]
        self.result = selected["raw"]
        self.selected_result = selected["raw"]
        self.selected_world_pos = selected["world"]
        self.selected_robot_pos = selected["robot"]
        self.selected_recognition_z = selected["z"]
        self.fork_height_at_recognition = Motor.getMotorPos(ConfigParams.fork_motor_name)
        pick_h = calculate_recognition_pick_height(
            selected["z"],
            self.height_offset,
            camera_moves_with_fork=False,
            fork_height_at_recognition=self.fork_height_at_recognition,
            camera_calibration_fork_height=self.rec_base_height,
        )
        if self.clamp_fn is not None:
            self.selected_pick_height = self.clamp_fn(pick_h, self.min_height, self.max_height)
        else:
            self.selected_pick_height = pick_h
        _trace_log(
            f"rec total_layers={self.total_layers}, select layer={self.goods_layer}, rec_z={selected['z']}, "
            f"zOffset={self.height_offset}, "
            f"camCalibMotorHeight={self.rec_base_height}, pick={self.selected_pick_height}"
        )
        self.action_status = ActionStatus.FINISHED


class RunMotorWithLaserMonitor(ActionBase):
    DIST_INCREASE_THRESHOLD = 0.2
    DIST_INCREASE_DEBOUNCE = 2

    def __init__(self, motor_name: str, position: float, max_speed=None, action_name="RunMotorWithLaserMonitor"):
        super().__init__(action_name)
        _init_action_runtime(self)
        target_speed = ConfigParams.fork_max_speed if max_speed is None else abs(float(max_speed))
        self.motor_action = RunMotorBySpeed(motor_name, abs(target_speed), "")
        self.target_position = float(position)
        self.prev_dist: Optional[float] = None
        self.increase_count = 0
        self.obstacle_reduced = False
        self.beam_seen = False
        self.beam_missing_count = 0
        self._warn_no_data_once = False
        self._xy_sample_logged_once = False
        self._laser_xy_frame_mode = "auto"
        self._fork_root_collision_shape_points = None
        self._fork_root_collision_shape_error = ""

    def _resolve_back_laser_key(self) -> str:
        raw = ConfigParams.fork_root_2D_lasers
        parts = [p.strip() for p in str(raw or "").split(",")]
        for part in parts:
            if part:
                return part
        return ""

    def _get_fork_root_laser_keys(self) -> List[str]:
        raw = ConfigParams.fork_root_2D_lasers
        return [part.strip() for part in str(raw or "").split(",") if part.strip()]

    def _load_fork_root_collision_shape_points(self) -> Optional[List[Dict[str, float]]]:
        raw_shape = getattr(ConfigParams, "forkRootCollisionShape", "")
        self._fork_root_collision_shape_error = ""
        if not raw_shape:
            return []

        def _normalize_points(points) -> List[Dict[str, float]]:
            normalized_points = []
            if not isinstance(points, list):
                return normalized_points
            for point in points:
                if not isinstance(point, dict):
                    continue
                try:
                    normalized_points.append({"x": float(point["x"]), "y": float(point["y"])})
                except (KeyError, TypeError, ValueError):
                    continue
            return normalized_points

        try:
            data = json.loads(raw_shape) if isinstance(raw_shape, str) else raw_shape
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            self._fork_root_collision_shape_error = f"invalid fork root collision shape json: {exc}"
            return None

        if isinstance(data, dict):
            shape_items = [data]
        elif isinstance(data, list):
            normalized_points = _normalize_points(data)
            if len(normalized_points) >= 3:
                return normalized_points
            shape_items = data
        else:
            self._fork_root_collision_shape_error = (
                f"fork root collision shape type is unsupported: {type(data).__name__}"
            )
            return None

        for item in shape_items:
            if not isinstance(item, dict):
                continue
            normalized_points = _normalize_points(item.get("points", []))
            if len(normalized_points) >= 3:
                return normalized_points

        self._fork_root_collision_shape_error = "fork root collision shape has no valid polygon points"
        return None

    def _get_fork_root_collision_shape_points(self) -> Optional[List[Dict[str, float]]]:
        if self._fork_root_collision_shape_points is None:
            self._fork_root_collision_shape_points = self._load_fork_root_collision_shape_points()
        return self._fork_root_collision_shape_points

    def _read_back_laser_collision(self) -> Optional[bool]:
        laser_keys = self._get_fork_root_laser_keys()
        if not laser_keys:
            return None
        shape_points = self._get_fork_root_collision_shape_points()
        if shape_points == []:
            return None
        if shape_points is None:
            _trace_log(f"fork root collision shape invalid: {self._fork_root_collision_shape_error}")
            return None
        x_list = [float(point["x"]) for point in shape_points]
        y_list = [float(point["y"]) for point in shape_points]
        try:
            return bool(Navigation.collisionDetection(laser_keys, x_list, y_list))
        except Exception as exc:
            _trace_log(f"fork root collision detection failed: {exc}, robot_pose={get_r_loc()}")
            return None

    def _read_back_laser_dist(self) -> Optional[float]:
        key = self._resolve_back_laser_key()
        if not key:
            return None
        try:
            data = Laser.getData()
        except Exception:
            return None
        if data is None:
            return None

        lasers = data.get("laser", []) if isinstance(data, dict) else list(getattr(data, "laser", []) or [])
        if not lasers:
            return None

        target = None
        for laser in lasers:
            try:
                if isinstance(laser, dict):
                    laser_key = str((laser.get("deviceInfo", {}) or {}).get("key", ""))
                else:
                    laser_key = str(getattr(getattr(laser, "deviceInfo", None), "key", ""))
            except Exception:
                continue
            if laser_key == key:
                target = laser
                break
        if target is None:
            return None

        mode = str(getattr(self, "_laser_xy_frame_mode", "auto") or "auto").strip().lower()
        if mode not in ("auto", "robot", "world"):
            mode = "auto"
        use_world_as_input = mode == "world"
        r_loc = get_r_loc() if use_world_as_input else None
        beams = target.get("beams", []) if isinstance(target, dict) else list(getattr(target, "beams", []) or [])
        front_x_values = []
        fork_outer_half = max(
            0.05,
            (float(ConfigParams.center_distance_between_forks) + float(ConfigParams.fork_tip_width)) / 2.0,
        )
        y_half = fork_outer_half + max(0.0, float(ConfigParams.laserDetectionWidth or 0.0))
        xy_samples = []
        front_xy_samples = []

        for beam in beams:
            try:
                if isinstance(beam, dict):
                    valid = bool(beam.get("valid", True))
                    x = float(beam.get("x", 0.0))
                    y = float(beam.get("y", 0.0))
                    angle = beam.get("angle", None)
                    dist = beam.get("dist", None)
                    is_virtual = bool(beam.get("isVirtual", False))
                else:
                    valid = bool(getattr(beam, "valid", True))
                    x = float(getattr(beam, "x", 0.0))
                    y = float(getattr(beam, "y", 0.0))
                    angle = getattr(beam, "angle", None)
                    dist = getattr(beam, "dist", None)
                    is_virtual = bool(getattr(beam, "isVirtual", False))
            except Exception:
                continue
            if not valid or is_virtual:
                continue
            if abs(x) <= EPS and abs(y) <= EPS and angle is not None and dist is not None:
                try:
                    raw_dist = float(dist)
                    raw_angle = math.radians(float(angle))
                    if raw_dist > 0.02:
                        x = raw_dist * math.cos(raw_angle)
                        y = raw_dist * math.sin(raw_angle)
                except Exception:
                    continue
            if use_world_as_input and r_loc is not None:
                try:
                    x, y, _ = pos2Base([x, y, 0.0], r_loc)
                    x = float(x)
                    y = float(y)
                except Exception:
                    continue
            if len(xy_samples) < 20 and (abs(x) > EPS or abs(y) > EPS):
                xy_samples.append([round(x, 4), round(y, 4)])

            if angle is not None:
                try:
                    is_front = math.cos(math.radians(float(angle))) > 0
                except Exception:
                    is_front = False
            else:
                is_front = x > 0.02
            if not is_front or abs(y) > y_half or x <= 0.02 or x >= 3.0:
                continue
            front_x_values.append(x)
            if len(front_xy_samples) < 12:
                front_xy_samples.append([round(x, 4), round(y, 4)])

        if (not self._xy_sample_logged_once) and xy_samples:
            pose = Loc.getPose()
            _trace_log(
                f"laser xy sample(mode={mode}) usable_xy={xy_samples}, front_xy={front_xy_samples}, "
                f"robot_pose=({pose.get('x', 0.0):.3f},{pose.get('y', 0.0):.3f},{pose.get('yaw', 0.0):.2f})"
            )
            self._xy_sample_logged_once = True

        if not front_x_values:
            return None
        front_x_values.sort()
        idx = max(0, min(len(front_x_values) - 1, int(len(front_x_values) * 0.1)))
        return float(front_x_values[idx])

    def run(self, ctx=None):
        if self.action_status in (ActionStatus.FINISHED, ActionStatus.FAILED):
            return
        self.action_status = ActionStatus.RUNNING
        self.motor_action.run()
        cur_height = Motor.getMotorPos(ConfigParams.fork_motor_name)

        collision_blocked = self._read_back_laser_collision()
        if collision_blocked is False:
            self.obstacle_reduced = True

        dist = self._read_back_laser_dist()
        if dist is None:
            if not self._warn_no_data_once:
                _trace_log("back 2d laser has no valid beam data this cycle")
                self._warn_no_data_once = True
            if self.beam_seen:
                self.beam_missing_count += 1
                if self.beam_missing_count >= 1 and not self.obstacle_reduced:
                    self.obstacle_reduced = True
                    _trace_log("unload laser monitor: back laser data missing but previously seen, consider obstacle reduced")
        else:
            self._warn_no_data_once = False
            self.beam_seen = True
            self.beam_missing_count = 0
            _trace_log(f"back laser distance: {dist:.3f} m")

        if dist is not None:
            if self.prev_dist is not None and (dist - self.prev_dist) >= self.DIST_INCREASE_THRESHOLD:
                self.increase_count += 1
            else:
                self.increase_count = 0
            self.prev_dist = dist
            if (not self.obstacle_reduced) and self.increase_count >= self.DIST_INCREASE_DEBOUNCE:
                self.obstacle_reduced = True
                _trace_log(f"unload laser monitor: obstacle reduced, dist={dist}")

        if self.beam_seen and self.beam_missing_count >= 1 and not self.obstacle_reduced:
            self.obstacle_reduced = True
            _trace_log("unload laser monitor: 激光点云清除，认为已不被阻挡")

        if cur_height <= self.target_position + max(ConfigParams.reach_down_dist, 0.01):
            slow_speed = abs(float(getattr(ConfigParams, "releaseSlowDownSpeed", self.motor_action.max_speed)))
            if getattr(self.motor_action, "max_speed", 0.0) > slow_speed:
                self.motor_action.max_speed = slow_speed

        if self.obstacle_reduced:
            Motor.resetMotor(ConfigParams.fork_motor_name)
            self.action_status = ActionStatus.FINISHED
            self.motor_action.action_status = ActionStatus.FINISHED
            return

        if self.motor_action.action_status == ActionStatus.FINISHED:
            self.action_status = ActionStatus.FINISHED
            return
        if self.motor_action.action_status == ActionStatus.FAILED:
            self.action_status = ActionStatus.FAILED

    def reset(self):
        self.action_status = ActionStatus.RUNNING
        self.motor_action.reset()

    def cancel(self):
        self.motor_action.reset()
        self.action_status = ActionStatus.FAILED

    def _trace_state(self) -> dict:
        return {
            "action_status": int(self.action_status),
            "obstacle_reduced": self.obstacle_reduced,
            "beam_seen": self.beam_seen,
            "beam_missing_count": self.beam_missing_count,
        }


class WeightDropMonitor:
    SAMPLE_COUNT = 3
    SAMPLE_INTERVAL = 0.05
    POLL_INTERVAL = 0.25
    DROP_THRESHOLD = 0.8

    def __init__(self, cfg):
        self.cfg = cfg
        self.scale = None
        self.base_weight: Optional[float] = None
        self.last_weight: Optional[float] = None
        self.last_poll_time = 0.0
        self.drop_ok = False
        self._mock_sequence: Optional[List[float]] = None
        self._mock_idx = 0

    def start(self):
        if self._mock_sequence is not None:
            if not self._mock_sequence:
                raise RuntimeError("weight mock enabled but sequence is empty")
            self.base_weight = float(self._mock_sequence[0])
            self.last_weight = self.base_weight
            self.last_poll_time = 0.0
            self.drop_ok = False
            self._mock_idx = 1
            return
        if not self.cfg.weightPort:
            raise RuntimeError("weight serial port is empty")
        self.scale = create_scale(
            "modbus",
            port=self.cfg.weightPort,
            baudrate=self.cfg.weightBaudrate,
            timeout=self.cfg.weightTimeout,
            slave_id=self.cfg.weightSlaveId,
        )
        self.base_weight = self._sample_weight()
        self.last_weight = self.base_weight
        self.last_poll_time = time.time()
        self.drop_ok = False

    def mock_start(self, sequence: Optional[List[float]] = None):
        if sequence is None:
            sequence = [120.0, 120.0, 119.8, 119.2, 118.6, 118.2]
        self._mock_sequence = [float(value) for value in sequence]
        self._mock_idx = 0
        self.start()

    @staticmethod
    def _to_kg(value: Any, unit: Any) -> Optional[float]:
        try:
            return weight_to_kg(value, unit)
        except (TypeError, ValueError):
            return None

    def _sample_weight(self) -> float:
        if self._mock_sequence is not None:
            if not self._mock_sequence:
                return 0.0
            if self._mock_idx >= len(self._mock_sequence):
                return float(self._mock_sequence[-1])
            value = float(self._mock_sequence[self._mock_idx])
            self._mock_idx += 1
            return value

        sample = self.scale.read_weight_samples(
            sample_count=max(1, int(self.SAMPLE_COUNT)),
            sample_interval=max(0.0, float(self.SAMPLE_INTERVAL)),
        )
        average_value = float(sample.get("averageValue", 0.0))
        last_sample = sample.get("last", {}) or {}
        unit = last_sample.get("unit")
        weight_kg = self._to_kg(average_value, unit)
        if weight_kg is not None:
            _trace_log(
                f"weight samples avg={weight_kg:.3f}kg, raw_avg={average_value}, "
                f"unit={unit}, last_raw={last_sample.get('raw')}"
            )
            return weight_kg
        _trace_log(f"weight samples avg={average_value}, unit={unit}, cannot_convert_to_kg=True")
        return average_value

    def update(self) -> bool:
        now = time.time()
        if now - self.last_poll_time < max(0.01, float(self.POLL_INTERVAL)):
            return self.drop_ok
        self.last_poll_time = now
        self.last_weight = self._sample_weight()
        if self.base_weight is None:
            self.drop_ok = False
            return self.drop_ok

        empty_threshold = float(getattr(self.cfg, "weightEmptyThreshold", 0.0))
        if empty_threshold > 0.0:
            self.drop_ok = float(self.last_weight) < empty_threshold
            _trace_log(
                f"weight empty threshold check: current={float(self.last_weight):.3f}kg, "
                f"threshold={empty_threshold:.3f}kg, drop_ok={self.drop_ok}"
            )
            return self.drop_ok

        self.drop_ok = (float(self.base_weight) - float(self.last_weight)) >= float(self.DROP_THRESHOLD)
        _trace_log(
            f"weight drop delta={(float(self.base_weight) - float(self.last_weight)):.3f}kg, "
            f"threshold={float(self.DROP_THRESHOLD):.3f}kg, drop_ok={self.drop_ok}"
        )
        return self.drop_ok

    def close(self):
        if self.scale is not None:
            try:
                self.scale.close()
            except Exception:
                pass

    def snapshot(self) -> Dict[str, Any]:
        return {
            "baseWeight": self.base_weight,
            "lastWeight": self.last_weight,
            "emptyThreshold": getattr(self.cfg, "weightEmptyThreshold", 0.0),
            "dropThreshold": self.DROP_THRESHOLD,
            "dropOk": self.drop_ok,
        }


class UltrasonicDetachMonitor:
    CLEAR_DEBOUNCE = 0.30

    def __init__(self, di_keys: List[str], trigger_mode: str):
        self.di_keys = _normalize_string_list(di_keys)
        self.trigger_mode = str(trigger_mode or "two").strip().lower()
        self.required_clear_count = 1 if self.trigger_mode == "one" else 2
        self.prev_states: Dict[str, bool] = {}
        self.clear_since: Optional[float] = None
        self.detach_ok = False
        self._mock_states: Optional[List[Tuple[bool, ...]]] = None
        self._mock_idx = 0

    def _read_di_states(self) -> List[bool]:
        if self._mock_states is not None:
            if not self._mock_states:
                return [False for _ in self.di_keys]
            if self._mock_idx >= len(self._mock_states):
                return list(self._mock_states[-1])
            states = self._mock_states[self._mock_idx]
            self._mock_idx += 1
            return list(states)
        return [bool(Di.getDi(di_key)) for di_key in self.di_keys]

    def start(self) -> bool:
        if len(self.di_keys) < self.required_clear_count:
            _trace_log(
                f"ultrasonic di monitor start skipped: di_keys={self.di_keys}, "
                f"required_clear_count={self.required_clear_count}"
            )
            self.detach_ok = False
            return False
        cur_states = self._read_di_states()
        _trace_log(
            f"ultrasonic di monitor start: di_keys={self.di_keys}, states={cur_states}, "
            f"required_clear_count={self.required_clear_count}"
        )
        self.prev_states = dict(zip(self.di_keys, cur_states))
        self.clear_since = None
        self.detach_ok = False
        return True

    def mock_start(self, states: Optional[List[Tuple[bool, ...]]] = None):
        if states is None:
            states = [
                (True, True),
                (True, True),
                (False, False),
                (False, False),
                (False, False),
            ]
        self._mock_states = [tuple(bool(item) for item in row) for row in states]
        self._mock_idx = 0
        if not self.di_keys:
            self.di_keys = ["__mock_ultra_di1__", "__mock_ultra_di2__"]
        self.start()

    def update(self) -> bool:
        now = time.time()
        cur_states = self._read_di_states()
        self.prev_states = dict(zip(self.di_keys, cur_states))
        clear_count = sum(1 for state in cur_states if not state)
        if clear_count < self.required_clear_count:
            self.clear_since = None
            self.detach_ok = False
            return False
        if self.clear_since is None:
            self.clear_since = now
            self.detach_ok = False
            return False
        self.detach_ok = (now - self.clear_since) >= self.CLEAR_DEBOUNCE
        return self.detach_ok

    def snapshot(self) -> Dict[str, Any]:
        return {
            "diKeys": list(self.di_keys),
            "triggerMode": self.trigger_mode,
            "requiredClearCount": self.required_clear_count,
            "clearDebounce": self.CLEAR_DEBOUNCE,
            "detachOk": self.detach_ok,
            "states": dict(self.prev_states),
        }


class UnloadReleaseCheckAction(ActionBase):
    RELEASE_DETECT_TIMEOUT = 28.0
    RELEASE_EXTRA_DOWN_STEP = 0.003
    RELEASE_NEAR_END_HEIGHT = 0.01
    RELEASE_NEAR_MIN_HEIGHT = 0.03

    def __init__(self, motor_name: str, end_height: float, max_speed: float, cfg, clamp_fn):
        super().__init__("UnloadReleaseCheck")
        _init_action_runtime(self)
        self.cfg = cfg
        self.clamp_fn = clamp_fn
        self.motor_name = motor_name
        self.end_height = end_height
        self.max_speed = abs(float(max_speed or 0.03)) or 0.03
        self.phase = "release"
        self.current_target: Optional[float] = None
        self.post_release_down_done = False
        self.back_laser_key: str = ""
        self.search_start_time = 0.0
        self.start_height = 0.0
        self.speed_mode = "fast"
        self.post_release_down_start_time = 0.0
        self.weight_monitor: Optional[WeightDropMonitor] = None
        self.di_monitor: Optional[UltrasonicDetachMonitor] = None
        self.weight_required = False
        self.weight_skip_reason = ""
        self.di_required = False
        self.di_skip_reason = ""
        self.action_status = ActionStatus.INIT

    def _resolve_back_laser_key(self) -> str:
        if self.cfg.fork_root_2D_lasers:
            parts = [p.strip() for p in str(self.cfg.fork_root_2D_lasers).split(",")]
            for part in parts:
                if part:
                    return part
        return ""

    def _set_motor_down_speed(self, slow: bool):
        slow_down_speed = abs(float(getattr(self.cfg, "releaseSlowDownSpeed", self.max_speed)))
        abs_speed = slow_down_speed if slow else self.max_speed
        Motor.setMotorSpeed(self.motor_name, -max(0.001, abs_speed))
        self.speed_mode = "slow" if slow else "fast"

    def _init_release_monitors(self) -> bool:
        self.weight_required = False
        self.weight_skip_reason = ""
        self.di_required = False
        self.di_skip_reason = ""

        di_keys = _normalize_string_list(getattr(self.cfg, "ultrasonicDiKeys", []))
        if di_keys:
            try:
                self.di_monitor = UltrasonicDetachMonitor(
                    di_keys=di_keys,
                    trigger_mode=getattr(self.cfg, "ultrasonicTriggerMode", "two"),
                )
                if not self.di_monitor.start():
                    self.di_monitor = None
                    self.di_required = False
                    self.di_skip_reason = "di_start_return_false"
                else:
                    self.di_required = True
            except Exception as exc:
                self.di_monitor = None
                self.di_required = False
                self.di_skip_reason = f"di_init_failed:{exc}"
                _trace_log(f"ultrasonic di init failed, fallback to weight only, err={exc}")
        else:
            self.di_skip_reason = "di_keys_empty"
            _trace_log("ultrasonic di disabled: keys empty, fallback to laser(+weight if available)")

        try:
            self.weight_monitor = WeightDropMonitor(self.cfg)
            self.weight_monitor.start()
            self.weight_required = True
        except Exception as exc:
            self.weight_monitor = None
            self.weight_required = False
            self.weight_skip_reason = f"scale_init_failed:{exc}"
            _trace_log(f"weight monitor init failed, fallback to DI only, err={exc}")
        return True

    def _update_release_condition(self) -> Tuple[bool, bool, bool]:
        try:
            weight_ok = self.weight_monitor.update() if self.weight_required and self.weight_monitor is not None else True
            di_ok = self.di_monitor.update() if self.di_required and self.di_monitor is not None else True
        except Exception as exc:
            if self.weight_required:
                _trace_log(f"weight monitor read failed, fallback to DI only, err={exc}")
                self.weight_required = False
                self.weight_skip_reason = f"runtime_error:{exc}"
                if self.weight_monitor is not None:
                    try:
                        self.weight_monitor.close()
                    except Exception:
                        pass
                    self.weight_monitor = None
                weight_ok = True
                di_ok = self.di_monitor.update() if self.di_required and self.di_monitor is not None else True
                return weight_ok, di_ok, (weight_ok or di_ok)
            self._fail_with_report("ReleaseSensorReadFail", f"sensor read failed: {exc}")
            self.action_status = ActionStatus.FAILED
            self.cancel()
            return False, False, False
        return weight_ok, di_ok, (weight_ok or di_ok)

    def _cleanup_monitors(self):
        if self.weight_monitor is not None:
            self.weight_monitor.close()
            self.weight_monitor = None
        self.di_monitor = None

    def _fail_with_report(self, err: str, msg: str):
        report = {
            "phase": self.phase,
            "backLaserKey": self.back_laser_key,
            "weightRequired": self.weight_required,
            "weightSkipReason": self.weight_skip_reason,
            "diRequired": self.di_required,
            "diSkipReason": self.di_skip_reason,
        }
        if self.weight_monitor:
            report["weight"] = self.weight_monitor.snapshot()
        if self.di_monitor:
            report["ultrasonic"] = self.di_monitor.snapshot()
        _trace_chart({
            "event": "detach_fail",
            "error": err,
            "message": msg,
            "report": report,
        })
        _trace_log(f"detach fail [{err}] {msg}, report={report}")

    def run(self, ctx=None):
        if self.action_status in (ActionStatus.FINISHED, ActionStatus.FAILED):
            return

        if not self.init:
            self.init = True
            self.action_status = ActionStatus.RUNNING
            if not self.motor_name:
                self.action_status = ActionStatus.FAILED
                return
            if not self._init_release_monitors():
                self.action_status = ActionStatus.FAILED
                self.cancel()
                return
            self.phase = "release"
            self.back_laser_key = self._resolve_back_laser_key()
            self.search_start_time = time.time()
            self.start_height = Motor.getMotorPos(ConfigParams.fork_motor_name)
            try:
                Motor.resetMotor(ConfigParams.fork_motor_name)
            except Exception:
                pass
            self._set_motor_down_speed(slow=False)

        weight_ok, di_ok, all_ok = self._update_release_condition()
        if all_ok:
            _trace_log(
                f"release condition met, weight_ok={weight_ok}, di_ok={di_ok}, "
                f"current_height={Motor.getMotorPos(ConfigParams.fork_motor_name)}"
            )
            if not self.post_release_down_done:
                self.post_release_down_done = True
                self.post_release_down_start_time = time.time()
                self._set_motor_down_speed(slow=True)
                return
            if self.post_release_down_start_time > 0:
                extra_dist = max(0.001, float(self.RELEASE_EXTRA_DOWN_STEP))
                slow_speed = max(0.001, abs(float(getattr(self.cfg, "releaseSlowDownSpeed", self.max_speed))))
                if (time.time() - self.post_release_down_start_time) < (extra_dist / slow_speed):
                    return
            try:
                Motor.resetMotor(ConfigParams.fork_motor_name)
            except Exception:
                pass
            self._cleanup_monitors()
            self.action_status = ActionStatus.FINISHED
            return

        if time.time() - self.search_start_time > self.RELEASE_DETECT_TIMEOUT:
            self._fail_with_report(
                "ReleaseDetectTimeout",
                f"release timeout>{self.RELEASE_DETECT_TIMEOUT}s, weight_ok={weight_ok}, di_ok={di_ok}",
            )
            Navigation.setTaskError("ReleaseDetectTimeout", f"release timeout>{self.RELEASE_DETECT_TIMEOUT}s")
            self.action_status = ActionStatus.FAILED
            self.cancel()
            return

        cur_height = Motor.getMotorPos(ConfigParams.fork_motor_name)
        if cur_height <= self.end_height + max(self.cfg.reach_down_dist, self.RELEASE_NEAR_END_HEIGHT):
            if self.speed_mode != "slow":
                self._set_motor_down_speed(slow=True)
        if cur_height <= self.cfg.min_height + max(self.cfg.reach_down_dist, self.RELEASE_NEAR_MIN_HEIGHT) and not all_ok:
            self._fail_with_report(
                "ReleaseForkProtection",
                f"fork reached lower protection limit, current_height={cur_height:.3f}, "
                f"min_height={self.cfg.min_height:.3f}, weight_ok={weight_ok}, di_ok={di_ok}",
            )
            Navigation.setTaskError("ReleaseForkProtection", "fork reached lower protection limit, release failed")
            self.action_status = ActionStatus.FAILED
            self.cancel()

    def reset(self):
        self.action_status = ActionStatus.RUNNING

    def cancel(self):
        self._cleanup_monitors()
        if self.motor_name:
            try:
                Motor.resetMotor(self.motor_name)
            except Exception:
                pass
        self.action_status = ActionStatus.FAILED

    def _trace_state(self) -> dict:
        return {
            "action_status": int(self.action_status),
            "weight_required": self.weight_required,
            "di_required": self.di_required,
            "speed_mode": self.speed_mode,
        }


class DMRecCheck(ActionBase):
    def __init__(
            self,
            rec_file: str,
            expected_goods_name: str,
            timeout: float,
            extract_good_name_fn: Callable[[Dict[str, Any]], str] = _extract_good_name_from_rec_results,
    ):
        super().__init__("DMRecCheck")
        _init_action_runtime(self)
        self.rec_file = (rec_file or "").strip()
        self.expected_goods_name = (expected_goods_name or "").strip()
        self.timeout = float(timeout)
        self.good_name = ""
        self.fail_reason = ""
        self.extract_good_name_fn = extract_good_name_fn
        self.dm_device_name = ""
        self.dm_tag_size = None
        self.selected_result = {}
        self.candidate_count = 0
        self.action_status = ActionStatus.INIT

    def _do_rec(self):
        Recognize.resetRec()
        Recognize.doRec(self.rec_file, "", "")

    def _report_dm_fail(self, reason: str):
        msg_map = {
            "NO_REC_FILE": "dm recognize recfile missing",
            "EMPTY_QR": "dm recognize success but empty content",
            "MISMATCH": "dm goods name mismatch",
            "REC_FAILED": "dm recognize task failed",
            "TIMEOUT": "dm recognize timeout",
        }
        Navigation.setTaskError("qrRecFailed", msg_map.get(reason, "dm recognize failed"))

    def run(self, ctx=None):
        if self.action_status in (ActionStatus.FINISHED, ActionStatus.FAILED):
            return

        if not self.init:
            self.init = True
            self.action_status = ActionStatus.RUNNING
            self.fail_reason = ""
            if not self.rec_file:
                self.fail_reason = "NO_REC_FILE"
                self._report_dm_fail(self.fail_reason)
                self.action_status = ActionStatus.FAILED
                return
            dm_config = _load_dm_code_recognition_config(self.rec_file)
            self.dm_device_name = str(dm_config.get("deviceName", "") or "")
            self.dm_tag_size = dm_config.get("tagSize")
            _trace_log(
                f"dm rec config: rec_file={self.rec_file}, "
                f"deviceName={self.dm_device_name}, tagSize={self.dm_tag_size}",
                name="fork.cfg",
            )
            self._do_rec()

        rec_status = Recognize.getRecStatus()
        if rec_status == 2:
            results = Recognize.getRecResults() or {}
            self.candidate_count = len(_get_dm_rec_candidates(results))
            self.selected_result = _select_dm_rec_result(results) or {}
            try:
                self.good_name = self.extract_good_name_fn(results)
            except Exception as exc:
                _trace_log(f"dm raw results parse failed, err={exc}, raw={results}")
                self.good_name = ""
            _trace_log(
                f"dm rec result: candidates={self.candidate_count}, "
                f"selected={self.selected_result}, good_name={self.good_name}",
                name="fork.cfg",
            )
            if not self.good_name:
                self.fail_reason = "EMPTY_QR"
                self._report_dm_fail(self.fail_reason)
                self.action_status = ActionStatus.FAILED
                Recognize.resetRec()
                return
            if self.expected_goods_name and self.good_name != self.expected_goods_name:
                self.fail_reason = "MISMATCH"
                self._report_dm_fail(self.fail_reason)
                self.action_status = ActionStatus.FAILED
                Recognize.resetRec()
                return
            self.action_status = ActionStatus.FINISHED
            Recognize.resetRec()
            return

        if rec_status in (-1, 3):
            self.fail_reason = "REC_FAILED"
            self._report_dm_fail(self.fail_reason)
            self.action_status = ActionStatus.FAILED
            Recognize.resetRec()
            return

        if time.time() - self.start_time > self.timeout:
            self.fail_reason = "TIMEOUT"
            self._report_dm_fail(self.fail_reason)
            self.action_status = ActionStatus.FAILED
            Recognize.resetRec()

    def reset(self):
        self.good_name = ""
        self.fail_reason = ""
        self.selected_result = {}
        self.candidate_count = 0
        self.action_status = ActionStatus.RUNNING

    def cancel(self):
        try:
            Recognize.resetRec()
        except Exception:
            pass
        self.selected_result = {}
        self.candidate_count = 0
        self.action_status = ActionStatus.FAILED

    def _trace_state(self) -> dict:
        return {
            "action_status": int(self.action_status),
            "fail_reason": self.fail_reason,
            "good_name": self.good_name,
            "dm_device_name": self.dm_device_name,
            "dm_tag_size": self.dm_tag_size,
            "candidate_count": self.candidate_count,
        }


class GoPathWithContactDi(BaseGoPathWithContactDi):
    def __init__(
            self,
            contact_dis,
            world_pos,
            obs_dist,
            method,
            args,
            check_di=True,
            operation_type="",
            distance_check_length: Optional[float] = None,
            recfile: str = "",
    ):
        super().__init__(
            contact_dis,
            world_pos,
            obs_dist,
            method,
            args,
            check_di,
            operation_type,
            recfile=recfile,
            initial_policy_name="policy",
        )
        self.distance_check_length = max(0.0, float(distance_check_length or 0.0))
        self.distance_check_enabled = (
            self.operation_type == "load"
            and self.method == "bezier"
            and self.distance_check_length > EPS
        )
        self.distance_check_done = not self.distance_check_enabled
        self.distance_check_aligned = not self.distance_check_enabled
        self.distance_check_align_long_thresh = ConfigParams.tail
        self.distance_sensor_device_keys = []
        self.latest_distance_sensor_dist = None
        self.last_distance_sensor_log_dist = None
        self.last_distance_sensor_log_time = 0.0
        self.distance_sensor_no_data_logged = False
        if self.distance_check_enabled:
            _trace_log(
                f"enable softbag distance check, motion target:{self.motion_target}, "
                f"pallet_length:{self.distance_check_length}"
            )

    def _load_distance_sensor_config(self) -> bool:
        if Distance is None:
            Navigation.setTaskError("DistanceSensorUnavailable", "distance sensor api is unavailable")
            self.action_status = ActionStatus.FAILED
            return False
        sensor_keys = [
            str(sensor_key).strip()
            for sensor_key in (ConfigParams.fork_tip_distance_sensors or [])
            if str(sensor_key).strip()
        ]
        if not sensor_keys:
            Navigation.setTaskError("DistanceSensorNotConfigured", "fork_tip_distance_sensors is not configured")
            self.action_status = ActionStatus.FAILED
            return False
        self.distance_sensor_device_keys = sensor_keys
        return True

    def _read_distance_sensor_dist(self) -> Optional[float]:
        if Distance is None:
            return None
        try:
            data = Distance.getData(["node"])
        except Exception as exc:
            _trace_log(f"read distance sensor failed: {exc}")
            return None

        nodes = data.get("node", []) if isinstance(data, dict) else []
        if not isinstance(nodes, list):
            return None

        matched_distances = []
        for node in nodes:
            if not isinstance(node, dict):
                continue
            node_key = str(node.get("key") or node.get("name") or "").strip()
            if node_key not in self.distance_sensor_device_keys:
                continue
            if not bool(node.get("valid", False)):
                continue
            try:
                dist = float(node.get("dist"))
            except (TypeError, ValueError):
                continue
            if dist <= 0.0:
                continue
            matched_distances.append(dist)
        if not matched_distances:
            return None
        return min(matched_distances)

    def _is_fork_aligned_with_pallet_front(self) -> bool:
        offset = pos2Base(get_r_loc(), self.target_pos)
        return offset[0] <= self.distance_check_align_long_thresh

    def _fail_pallet_back_distance_insufficient(self, dist: float, source: str) -> bool:
        Navigation.setTaskError(
            "PalletBackDistanceInsufficient",
            f"{source}: distance sensor {self.distance_sensor_device_keys} dist={dist:.3f}m < "
            f"pallet_length={self.distance_check_length:.3f}m",
        )
        self.action_status = ActionStatus.FAILED
        _trace_log(
            f"{source}: pallet back distance insufficient, dist={dist}, "
            f"pallet_length={self.distance_check_length}"
        )
        return False

    def _pass_distance_sensor_no_valid_data(self, source: str) -> Optional[bool]:
        if not self.distance_sensor_no_data_logged:
            _trace_log(
                f"{source}: distance sensor no valid data, "
                f"keep waiting for contact di fallback, sensors={self.distance_sensor_device_keys}"
            )
            self.distance_sensor_no_data_logged = True
        return None

    def _check_distance_sensor_once(self) -> Optional[bool]:
        if not self.distance_check_enabled:
            return True
        if not self.distance_sensor_device_keys and not self._load_distance_sensor_config():
            return False

        dist = self._read_distance_sensor_dist()
        if dist is None:
            return self._pass_distance_sensor_no_valid_data("distance sensor one-shot")

        self.distance_sensor_no_data_logged = False
        self.latest_distance_sensor_dist = dist
        _trace_log(
            f"distance sensor one-shot read, sensors={self.distance_sensor_device_keys}, "
            f"dist={dist}, pallet_length={self.distance_check_length}"
        )

        if dist < self.distance_check_length:
            return self._fail_pallet_back_distance_insufficient(dist, "distance sensor one-shot")
        return True

    def _handle_contact_di_fallback(self) -> bool:
        if not self.check_di:
            return False
        self.di_status = [Di.getDi(d) for d in self.contact_di]
        if not any(self.di_status):
            return False
        _trace_log(
            f"contact di fallback triggered during distance check, di_status:{self.di_status}, "
            f"distance_check_done:{self.distance_check_done}"
        )
        if self.stop_robot():
            self.action_status = ActionStatus.FINISHED
            return True
        return False

    def _sync_motion_policy(self) -> None:
        vx = NavSpeed.getSpeeds()[0]
        if vx > 0.005 and not self.clear_policy:
            Navigation.clearPolicy()
            self.clear_policy = True
            self.set_policy = False
            emit_event(
                "policyCleared",
                channel=CH_POLICY,
                ctx=self,
                policyName="policy",
                trigger=f"operation:{self.operation_type or 'unknown'}|vx:{round(float(vx), 4)}",
            )
            return
        if vx <= 0 and not self.set_policy:
            before = {
                key: _policy_effective_value(key) for key in self.policy
            }
            Navigation.appendCustomPolicy("policy", self.policy)
            time.sleep(0.5)
            Navigation.goPathParam(dict())
            self.clear_policy = False
            self.set_policy = True
            emit_policy(
                "policy",
                before=before,
                after=dict(self.policy),
                ctx=self,
                trigger=f"operation:{self.operation_type or 'unknown'}|vx:{round(float(vx), 4)}",
                resetPath=True,
            )

    def _handle_motion_extensions(self) -> bool:
        if not self.distance_check_enabled or self.distance_check_done:
            return False

        if not self.distance_check_aligned and self._is_fork_aligned_with_pallet_front():
            self.distance_check_aligned = True
            _trace_log("reach pallet front align point, start one-shot distance sensor check before inserting")

        if self.distance_check_aligned:
            distance_check_result = self._check_distance_sensor_once()
            if distance_check_result is False:
                return True
            if distance_check_result is True:
                self.distance_check_done = True

        if self._handle_contact_di_fallback():
            return True

        if self.back_action.action_status in [ScriptStatus.FINISHED, ActionStatus.FINISHED]:
            self.distance_check_done = True
        return False

    def _handle_contact_di_completion(self) -> None:
        if self.distance_check_enabled and not self.distance_check_done:
            return
        super()._handle_contact_di_completion()

    def _trace_extra_state(self) -> Dict[str, object]:
        return {
            "distance_check_enabled": self.distance_check_enabled,
            "distance_check_done": self.distance_check_done,
            "distance_check_aligned": self.distance_check_aligned,
            "latest_distance_sensor_dist": self.latest_distance_sensor_dist or 0.0,
            "collision_model_count": len(self.fork_root_collision_models or []),
        }


class SoftbagFork(Fork):
    recognition_height_default = True
    camera_moves_with_fork = False
    supports_cam_lift_with_fork = True
    use_current_height_when_start_omitted = False
    requires_explicit_start_height = True
    cam_lift_with_fork_default = True
    adaptive_pallet_stack_unstack_default = False
    config_builder_hook = staticmethod(_softbag_config_builder)
    config_reload_hook = staticmethod(_softbag_config_reload)
    rec_input_params_hook = staticmethod(_softbag_recognize_on_params)
    period_run_hook = staticmethod(_softbag_period_run)

    @staticmethod
    def extend_custom_operation_inputs(_input_cls, builder, min_height: float, max_height: float):
        with builder.CHILD(key="unstack", name=_TR("Pallet Unstack"), desc=_TR("Pick a pallet from the selected recognition layer")):
            builder.TYPE(ParamType.ARRAY)
            with builder.CHILDREN():
                create_start_height_param(builder, min_height, max_height)
                with builder.CHILD(key="recfile", name=_TR("Recognition File"), desc=_TR("Recognition file name")):
                    builder.TYPE(ParamType.STRING)
                    builder.DEFAULTVALUE("default.srec")
                with builder.CHILD(key="recSide", name=_TR("Recognition Side"), desc=_TR("Recognition Side")):
                    builder.TYPE(ParamType.STRING)
                    builder.DEFAULTVALUE("A")
                with builder.CHILD(key="recHeight", name=_TR("Rec Height"), desc=_TR("Fork height during recognition")):
                    builder.TYPE(ParamType.FLOAT)
                    builder.UNIT("m")
                    builder.SINGLESTEP(0.01)
                    builder.DEFAULTVALUE(0.1)
                _softbag_recognize_on_params(_input_cls, builder)
                with builder.CHILD(key="goodsLayer", name=_TR("Goods Layer"), desc=_TR("Pallet layer to load; 1 is the highest layer")):
                    builder.TYPE(ParamType.INT)
                    builder.DEFAULTVALUE(1, min_value=1)
                with builder.CHILD(key="leaveLocHeight", name=_TR("Leave Loc Height"),
                                   desc=_TR("The fork height after leave loc")):
                    builder.TYPE(ParamType.FLOAT)
                    builder.UNIT("m")
                    builder.SINGLESTEP(0.01)
                    builder.DEFAULTVALUE(-1)
                with builder.CHILD(key="leaveLoc", name=_TR("Leave Loc"),
                                   desc=_TR("Return to the source location after unstack")):
                    builder.TYPE(ParamType.BOOL)
                    builder.DEFAULTVALUE(False)

    @classmethod
    def custom_action_templates(cls):
        return [
            {"action_name": _TR("Pallet Unstack"), "operation": "unstack", "stage": 3},
        ]

    def custom_operations(self):
        return {
            "unstack": self.unstack,
        }

    def _reset_extra_task_state(self):
        self.qr_recfile = ""
        self.goods_name = ""
        self.goods_layer = 1
        self.qr_good_name = ""
        self.unload_start_back_laser_blocked = False

    def _init_extra_args(self):
        self.qr_recfile = self.task_args.get("qrRecFile", "")
        self.goods_name = self.task_args.get("goodsName", "")
        if self.opt == "unstack":
            default_layer = max(1, int(getattr(ConfigParams, "loadPalletLayer", 1)))
            try:
                goods_layer = int(self.task_args.get("goodsLayer", default_layer))
            except (TypeError, ValueError):
                goods_layer = default_layer
        else:
            goods_layer = 1
        self.goods_layer = max(1, goods_layer)
        self.qr_good_name = ""
        self.unload_start_back_laser_blocked = False

    def unstack(self):
        if not getattr(ConfigParams, "adaptivePalletStackUnstack", False):
            Navigation.setTaskError(
                "UnstackDisabled",
                "adaptive pallet stack/unstack is disabled, cannot unstack",
            )
            self.set_status(ScriptStatus.FAILED)
            return

        # 解垛始终依赖多结果识别；路径、进叉、顶升和离库流程复用通用 load。
        self.recognize = True
        yield from super().load()

    def _resolve_back_laser_key(self) -> str:
        raw = ConfigParams.fork_root_2D_lasers
        parts = [part.strip() for part in str(raw or "").split(",")]
        for part in parts:
            if part:
                return part
        return ""

    def _has_back_laser(self) -> bool:
        return bool(self._resolve_back_laser_key())

    def _read_back_laser_blocked(self) -> bool:
        """
        放货起始前读取一次后2D激光，若货叉宽度范围内存在近距离有效点，则认为后激光被阻挡。
        优先使用 collisionDetection 判断；若现场未配置碰撞检测区域，则退回旧的距离口径。
        """
        if not self._has_back_laser():
            return False
        try:
            probe = RunMotorWithLaserMonitor(
                ConfigParams.fork_motor_name,
                Motor.getMotorPos(ConfigParams.fork_motor_name),
                0.001,
                action_name="UnloadLaserProbe",
            )
            collision_blocked = probe._read_back_laser_collision()
        except Exception as exc:
            _trace_log(f"read unload start back laser failed: {exc}")
            return False
        if collision_blocked is not None:
            _trace_log(f"unload start back laser probe: collision_blocked={collision_blocked}")
            return bool(collision_blocked)
        dist = probe._read_back_laser_dist()
        if dist is None:
            _trace_log("unload start back laser probe: no valid distance")
            return False
        blocked = dist <= 2.5
        _trace_log(f"unload start back laser probe: dist={dist:.3f}m, blocked={blocked}")
        return blocked

    def _need_unload_laser_monitor(self) -> bool:
        need = bool(getattr(self, "unload_start_back_laser_blocked", False))
        _trace_log(
            f"need unload laser monitor={need}, "
            f"start_back_laser_blocked={self.unload_start_back_laser_blocked}"
        )
        return need

    def _get_load_end_height(self) -> float:
        fork_cur_height = Motor.getMotorPos(ConfigParams.fork_motor_name)
        target_height = fork_cur_height + float(getattr(ConfigParams, "loadEndHeightExtra", 0.0))
        _trace_log(
            f"current fork height: {fork_cur_height:.3f}m, target end height: {target_height:.3f}m"
        )
        return target_height

    def _build_load_transport_lift_action(self):
        # 基类生成器在进叉批跑完后才调用本方法，故 _get_load_end_height 读到的是进叉后真实高度
        if (
                not self.start_height_provided
                and self.move_task.get("skillName", "") == "Action"
        ):
            target_height = self.end_height
        else:
            target_height = self._get_load_end_height()
        return RunMotorByPosition(
            ConfigParams.fork_motor_name,
            target_height,
            ConfigParams.fork_max_speed,
            "upFork",
        )

    def _build_load_no_rec_approach_batch(self, target_pos, tcp_name):
        actions = [RunMotorByPosition(ConfigParams.fork_motor_name, self.start_height)]
        resolved_target_pos = target_pos
        if tcp_name:
            resolved_target_pos = apply_tcp_target(target_pos, tcp_name)
            method, args = build_path_adjust_plan(
                back_dist=0,
                min_ahead_dist=ConfigParams.tail + ConfigParams.module_x,
                adjust_dist=ConfigParams.aheadDist,
            )
        else:
            method = "goPath"
            args = {}

        actions.append(
            GoPathWithContactDi(
                ConfigParams.contact_ids,
                resolved_target_pos,
                None,
                method,
                args,
                self.check_di,
                "load",
                recfile=self.recfile,
            )
        )
        return actions

    def _create_load_recognition_action(self, rec_center2robot):
        return RecPalletSelect(
            self.recfile,
            goods_layer=self.goods_layer,
            rec_base_height=float(getattr(ConfigParams, "camCalibMotorHeight", 0.0)),
            rec_center_x=rec_center2robot[0],
            rec_center_y=rec_center2robot[1],
            rec_radius=ConfigParams.recRadius,
            height_offset=load_pallet_z_offset(
                self.recfile,
                self.rec_info.get("side_value")
                if isinstance(getattr(self, "rec_info", None), dict)
                else getattr(self, "recSide", None),
            ),
            z_max=ConfigParams.zMax,
            min_height=ConfigParams.min_height,
            max_height=ConfigParams.max_height,
            clamp_fn=clamp,
        )

    def _build_load_entry_batch(self, rec_action):
        rec_height = self.rec_height if self.rec_height >= 0 else self.start_height
        return [
            RunMotorByPosition(ConfigParams.fork_motor_name, rec_height),
            rec_action,
        ]

    def _resolve_load_recognition_pose(self, rec_action):
        results = rec_action.results_list
        rec_result_dict = results[0]
        world_result = rec_result_dict.get("worldResult", {})
        robot_result = rec_result_dict.get("robotResult", {})
        rec_world_pos = rec_action.selected_world_pos or [
            world_result.get("x", 0.0),
            world_result.get("y", 0.0),
            world_result.get("yaw", 0.0),
        ]
        rec_robot_pos = rec_action.selected_robot_pos or [
            robot_result.get("x", 0.0),
            robot_result.get("y", 0.0),
            robot_result.get("yaw", 0.0),
        ]
        return results, rec_result_dict, rec_world_pos, rec_robot_pos

    def _build_load_approach_batch(self, rec_action, rec_world_pos, method, args):
        actions = []
        if self.load_recognition_pick_height is not None:
            actions.append(RunMotorByPosition(
                ConfigParams.fork_motor_name,
                self.load_recognition_pick_height,
                ConfigParams.fork_max_speed,
                "pickHeight",
            ))
        actions.append(GoPathWithContactDi(
                ConfigParams.contact_ids,
                rec_world_pos,
                None,
                method,
                args,
                self.check_di,
                "load",
                distance_check_length=self.carrier_length,
                recfile=self.recfile,
            ))
        return actions

    def _build_unload_target_approach(self, target_pos, tcp_name):
        resolved_target_pos = target_pos
        if tcp_name:
            resolved_target_pos = apply_tcp_target(target_pos, tcp_name)
        method, args = build_path_adjust_plan(
            back_dist=0,
            min_ahead_dist=ConfigParams.tail + ConfigParams.module_x - ConfigParams.base_shift_length,
            adjust_dist=ConfigParams.aheadDist,
            enabled=bool(tcp_name),
        )
        if ConfigParams.base_shift and (ConfigParams.max_height - self.fork_height) < EPS:
            resolved_target_pos = pos2World([-ConfigParams.base_shift_length, 0, 0], resolved_target_pos)

        actions = [
            self._build_unload_prepare_lift_action(self.start_height),
            GoPathWithContactDi(
                ConfigParams.contact_ids,
                resolved_target_pos,
                None,
                method,
                args,
                False,
                "unload",
                recfile=self.recfile,
            ),
        ]
        return actions, bool(tcp_name)

    def _build_unload_approach_batch(self, rec_action, rec_world_pos, method, args):
        return [
            GoPathWithContactDi(
                ConfigParams.contact_ids,
                rec_world_pos,
                None,
                method,
                args,
                False,
                "unload",
                recfile=self.recfile,
            ),
        ]

    def _on_unload_actions_build(self):
        # 放货动作构建前：读后激光屏蔽状态（供 _need_unload_laser_monitor 用）
        self.unload_start_back_laser_blocked = self._read_back_laser_blocked()

    def _build_unload_prepare_lift_action(self, target_height):
        if self._need_unload_laser_monitor():
            return RunMotorWithLaserMonitor(
                ConfigParams.fork_motor_name,
                target_height,
                ConfigParams.fork_max_speed,
            )
        return super()._build_unload_prepare_lift_action(target_height)

    def _build_unload_release_action(self):
        return UnloadReleaseCheckAction(
            motor_name=ConfigParams.fork_motor_name,
            end_height=self.end_height,
            max_speed=ConfigParams.downMaxSpeedWithGoods,
            cfg=ConfigParams,
            clamp_fn=clamp,
        )

    def _build_unload_no_target_prepare_batch(self):
        # UnloadReleaseCheckAction 落叉前需先抬到起始高度（原 _build_unload_no_target_actions 逻辑）
        if (
                not self.start_height_provided
                and self.move_task.get("skillName", "") == "Action"
        ):
            return []
        if isinstance(self._build_unload_release_action(), RunMotorByPosition):
            return []
        return [self._build_unload_prepare_lift_action(self.start_height)]


robot = SoftbagFork(__file__)


if __name__ == "__main__":
    robot.main()
