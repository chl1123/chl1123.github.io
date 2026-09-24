# -*- coding: utf-8 -*-
import math

from syspy import Laser, Motor, Navigation, RobotParam, ScriptStatus, Trace, _TR
from syspy.lib.action_task import ActionBase
from syspy.lib.module import pos2Base, pos2World
from syspy.utils.param_server import ParamType

from standard.fork import ConfigParams, HeavyFork, cage_stack_config_builder, cage_stack_config_reload
from standard.fork_utils import (
    ActionStatus,
    RunMotorByPosition,
    create_end_height_param,
    create_loc_detect_height_param,
    create_loc_detect_layer_param,
    create_rec_param,
    create_start_height_param,
    get_r_loc,
    has_valid_target_pos,
)


class CheckTargetObsByHeight(ActionBase):
    """使用叉尖 2D 激光在固定窗口内判断当前层是否存在点云。"""

    def __init__(self, probe_height: float, x_min: float, x_max: float, y_half_width: float, expect_present: bool,
                 error_code: str, error_msg: str, action_name: str = "CheckTargetObsByHeight"):
        super().__init__(action_name)
        self.probe_height = float(probe_height)
        self.x_min = float(x_min)
        self.x_max = float(x_max)
        self.y_half_width = float(y_half_width)
        self.expect_present = bool(expect_present)
        self.error_code = error_code
        self.error_msg = error_msg
        self.detected = False
        self.valid_points = 0
        self.checked_lasers = []
        self.match_count = 0
        self.mismatch_count = 0
        self.no_data_count = 0
        self.required_consistent_count = 2
        self.max_no_data_count = 10
        self.preserve_task_error = True

    def _fail(self, error_code=None, error_msg=None):
        Navigation.setTaskError(error_code or self.error_code, error_msg or self.error_msg)
        self.action_status = ActionStatus.FAILED

    def _collect_target_lasers(self, data):
        laser_keys = {str(key).strip() for key in list(ConfigParams.fork_tip_2D_lasers or []) if str(key).strip()}
        self.checked_lasers = sorted(laser_keys)
        if not laser_keys:
            return []

        lasers = data.get("laser", []) if isinstance(data, dict) else list(getattr(data, "laser", []) or [])
        targets = []
        for laser in lasers:
            try:
                if isinstance(laser, dict):
                    key = str((laser.get("deviceInfo", {}) or {}).get("key", "")).strip()
                else:
                    key = str(getattr(getattr(laser, "deviceInfo", None), "key", "")).strip()
            except Exception:
                continue
            if key in laser_keys:
                targets.append(laser)
        return targets

    def _has_obs_in_window(self):
        try:
            data = Laser.getData()
        except Exception as exc:
            Navigation.trace(f"{self.action_name}: read fork tip laser failed: {exc}")
            return None
        if data is None:
            return None

        targets = self._collect_target_lasers(data)
        if not targets:
            return None

        valid_points = 0
        valid_beam_count = 0
        x_match_count = 0
        x_values = []
        y_values = []

        for laser in targets:
            beams = laser.get("beams", []) if isinstance(laser, dict) else list(getattr(laser, "beams", []) or [])
            if isinstance(laser, dict):
                device_info = laser.get("deviceInfo", {}) or {}
                install_info = laser.get("installInfo", {}) or {}
                laser_key = str(device_info.get("key", ""))
                min_range = float(device_info.get("minRange", 0.02) or 0.02)
                install_x = float(install_info.get("x", 0.0) or 0.0)
                install_y = float(install_info.get("y", 0.0) or 0.0)
                install_yaw = float(install_info.get("yaw", 0.0) or 0.0)
            else:
                device_info = getattr(laser, "deviceInfo", None)
                install_info = getattr(laser, "installInfo", None)
                laser_key = str(getattr(device_info, "key", ""))
                min_range = float(getattr(device_info, "minRange", 0.02) or 0.02)
                install_x = float(getattr(install_info, "x", 0.0) or 0.0)
                install_y = float(getattr(install_info, "y", 0.0) or 0.0)
                install_yaw = float(getattr(install_info, "yaw", 0.0) or 0.0)
            install_yaw_rad = math.radians(install_yaw)
            install_cos = math.cos(install_yaw_rad)
            install_sin = math.sin(install_yaw_rad)
            for beam in beams:
                try:
                    if isinstance(beam, dict):
                        valid = bool(beam.get("valid", False))
                        angle = beam.get("angle", 0.0)
                        dist = beam.get("dist", 0.0)
                        is_virtual = bool(beam.get("isVirtual", False))
                    else:
                        valid = bool(getattr(beam, "valid", False))
                        angle = getattr(beam, "angle", 0.0)
                        dist = getattr(beam, "dist", 0.0)
                        is_virtual = bool(getattr(beam, "isVirtual", False))
                except Exception:
                    continue

                if not valid or is_virtual:
                    continue
                try:
                    d = float(dist)
                    angle_rad = math.radians(float(angle))
                except (TypeError, ValueError):
                    continue
                if d <= max(0.02, min_range):
                    continue

                laser_x = d * math.cos(angle_rad)
                laser_y = d * math.sin(angle_rad)
                x = install_x + install_cos * laser_x - install_sin * laser_y
                y = install_y + install_sin * laser_x + install_cos * laser_y
                valid_beam_count += 1
                x_values.append(x)
                y_values.append(y)
                if x < self.x_min or x > self.x_max:
                    continue
                x_match_count += 1
                if abs(y) > self.y_half_width:
                    continue
                valid_points += 1
                if valid_points > 0:
                    self.valid_points = valid_points
                    Trace.log(
                        f"{self.action_name}: location point found, laser={laser_key}, "
                        f"polar=(angle={float(angle):.4f},dist={d:.4f}), "
                        f"laser_point=({laser_x:.4f},{laser_y:.4f}), robot_point=({x:.4f},{y:.4f}), "
                        f"install=({install_x:.4f},{install_y:.4f},{install_yaw:.4f}), "
                        f"roi=x=[{self.x_min:.4f},{self.x_max:.4f}], y=±{self.y_half_width:.4f}",
                        name="fork.task",
                    )
                    return True

        if valid_beam_count == 0:
            Trace.log(
                f"{self.action_name}: fork tip laser has no valid polar point, laser={self.checked_lasers}",
                name="fork.task",
            )
            return None

        self.valid_points = valid_points
        x_range = [min(x_values), max(x_values)] if x_values else []
        y_range = [min(y_values), max(y_values)] if y_values else []
        Trace.log(
            f"{self.action_name}: no location point, laser={self.checked_lasers}, "
            f"valid_beams={valid_beam_count}, x_match={x_match_count}, "
            f"robot_x_range={x_range}, robot_y_range={y_range}, "
            f"roi=x=[{self.x_min:.4f},{self.x_max:.4f}], y=±{self.y_half_width:.4f}",
            name="fork.task",
        )
        return False

    def run(self, ctx=None):
        if self.action_status in [ActionStatus.FINISHED, ActionStatus.FAILED]:
            return

        self.action_status = ActionStatus.RUNNING
        detected = self._has_obs_in_window()
        if detected is None:
            self.no_data_count += 1
            if self.no_data_count >= self.max_no_data_count:
                self._fail("ForkTipLaserNoData", "Fork tip laser has no valid point cloud data")
            return

        self.no_data_count = 0
        self.detected = bool(detected)
        if self.detected == self.expect_present:
            self.match_count += 1
            self.mismatch_count = 0
            if self.match_count >= self.required_consistent_count:
                self.action_status = ActionStatus.FINISHED
        else:
            self.mismatch_count += 1
            self.match_count = 0
            if self.mismatch_count >= self.required_consistent_count:
                self._fail()

    def reset(self):
        self.action_status = ActionStatus.RUNNING
        self.detected = False
        self.valid_points = 0
        self.checked_lasers = []
        self.match_count = 0
        self.mismatch_count = 0
        self.no_data_count = 0

    def _trace_state(self):
        return {
            "action_status": int(self.action_status),
            "probe_height": self.probe_height,
            "x_min": self.x_min,
            "x_max": self.x_max,
            "y_half_width": self.y_half_width,
            "expect_present": self.expect_present,
            "detected": self.detected,
            "valid_points": self.valid_points,
            "match_count": self.match_count,
            "mismatch_count": self.mismatch_count,
            "no_data_count": self.no_data_count,
        }


class CounterBalanceWithShiftFork(HeavyFork):
    falling_down_detect_default = True
    recognition_height_default = True
    supports_loc_detection = True
    use_current_height_when_start_omitted = True
    config_builder_hook = staticmethod(cage_stack_config_builder)
    config_reload_hook = staticmethod(cage_stack_config_reload)

    @staticmethod
    def extend_custom_operation_inputs(input_cls, builder, min_height: float, max_height: float):
        with builder.CHILD(key="cageStack", name=_TR("Cage Stack"), desc=_TR("Stack the cage")):
            builder.TYPE(ParamType.ARRAY)
            with builder.CHILDREN():
                create_start_height_param(builder, min_height, max_height)
                create_end_height_param(builder, min_height, max_height)
                create_loc_detect_height_param(builder, min_height, max_height)
                create_loc_detect_layer_param(builder)
                create_rec_param(builder, input_cls.extend_recognize_on_params)

    @classmethod
    def custom_action_templates(cls):
        return [
            {"action_name": _TR("Cage Stack"), "operation": "cageStack", "stage": 3},
        ]

    def custom_operations(self):
        return {
            "cageStack": self.cage_stack,
        }

    def custom_cleanup_operations(self):
        return {"cageStack"}

    @staticmethod
    def _get_expand_motor_key():
        for motor_name in ConfigParams.expand_motor_names:
            if str(motor_name).strip():
                return str(motor_name).strip()
        return str(ConfigParams.expand_motor_name or "").strip()

    @staticmethod
    def _resolve_expand_target_position(rec_action, motor_key):
        hole_offsets = []
        for hole in getattr(rec_action, "hole_positions", None) or []:
            try:
                hole_y = abs(float(hole.get("holeY", 0.0) or 0.0))
            except (TypeError, ValueError):
                continue
            if hole_y > 0:
                hole_offsets.append(hole_y)
        if not hole_offsets:
            return float(Motor.getMotorPos(motor_key))
        return sum(hole_offsets)

    def _build_expand_motor_action(self, rec_action):
        motor_key = self._get_expand_motor_key()
        if not motor_key or not getattr(rec_action, "hole_positions", None):
            return None
        target_pos = self._resolve_expand_target_position(rec_action, motor_key)
        Trace.log(
            f"Expand motor target: motor={motor_key}, target={target_pos:.4f}, "
            f"hole_positions={getattr(rec_action, 'hole_positions', [])}",
            name="fork.task",
        )
        return RunMotorByPosition(motor_key, target_pos, 0.1, action_name="RunExpandMotor")

    def _build_height_probe_action(self, probe_height: float, x_min: float,
                                   x_max: float, y_half_width: float,
                                   expect_present: bool, error_code: str, error_msg: str, action_name: str):
        return CheckTargetObsByHeight(
            probe_height=probe_height,
            x_min=x_min,
            x_max=x_max,
            y_half_width=y_half_width,
            expect_present=expect_present,
            error_code=error_code,
            error_msg=error_msg,
            action_name=action_name,
        )

    @staticmethod
    def _optional_number(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _resolve_loc_detect_height(self):
        height = self._optional_number(self.loc_detect_height)
        layer = self._optional_number(self.loc_detect_layer)
        height_enabled = height is not None and height >= 0
        layer_enabled = layer is not None and layer >= 0

        if height_enabled and layer_enabled:
            self._fail_loc_detection_setup(
                "LocDetectParamConflict",
                "locDetectHeight and locDetectLayer cannot both be enabled",
            )
            return True, None
        if height_enabled:
            return True, height
        if not layer_enabled:
            return False, None
        if layer < 1 or not layer.is_integer():
            self._fail_loc_detection_setup(
                "LocDetectLayerInvalid",
                "locDetectLayer must be an integer greater than or equal to 1",
            )
            return True, None

        try:
            carrier_length = float(self.carrier_length)
        except (TypeError, ValueError):
            carrier_length = 0.0
        if carrier_length <= 0:
            carrier_recfile = self.recfile or "default.srec"
            try:
                carrier_length = float(RobotParam.getConfig(
                    "recognition",
                    "recognitionObject.pallet.carrierParameter.carrierLength",
                    carrier_recfile,
                ) or 0)
            except (TypeError, ValueError):
                carrier_length = 0.0
            self.carrier_length = carrier_length
        if carrier_length <= 0:
            self._fail_loc_detection_setup(
                "LocDetectCarrierLengthMissing",
                "locDetectLayer conversion requires a valid carrierLength",
            )
            return True, None

        probe_height = layer * carrier_length - 0.5
        if probe_height < 0:
            self._fail_loc_detection_setup(
                "LocDetectHeightOutOfRange",
                f"locDetectLayer converted to an invalid detection height: {probe_height}",
            )
            return True, None
        Trace.log(
            f"location detection layer converted: layer={int(layer)}, "
            f"carrierLength={carrier_length}, height={probe_height}",
            name="fork.task",
        )
        return True, probe_height

    def _fail_loc_detection_setup(self, error_code, error_msg):
        Navigation.setTaskError(error_code, error_msg)
        self.set_status(ScriptStatus.FAILED)

    def _resolve_loc_detection_roi(self):
        if not has_valid_target_pos(self.target_pos):
            self._fail_loc_detection_setup("LocDetectTargetMissing", "Location detection requires a valid AP point")
            return None
        ap_in_robot = pos2Base(self.target_pos[:3], get_r_loc())
        area_width = float(ConfigParams.width)
        if area_width <= 0:
            self._fail_loc_detection_setup("LocDetectRoiInvalid", "Location detection requires a valid robot width")
            return None
        module_point = pos2World([ConfigParams.module_x, 0, 0], ap_in_robot)
        back_point = pos2World([-0.3, 0, 0], module_point)
        x_min = float(back_point[0])
        x_max = -0.2
        y_half_width = area_width / 2.0
        if x_min >= x_max:
            self._fail_loc_detection_setup(
                "LocDetectRoiInvalid",
                f"Invalid location detection ROI: x_min={x_min}, x_max={x_max}",
            )
            return None
        Trace.log(
            f"location detection roi: ap_in_robot={ap_in_robot}, module_point={module_point}, "
            f"back_point={back_point}, x_min={x_min}, x_max={x_max}, "
            f"y_min={-y_half_width}, y_max={y_half_width}",
            name="fork.task",
        )
        return x_min, x_max, y_half_width

    def _prepare_loc_detection(self, *, move_to_loc_detect_height):
        loc_detect_requested, probe_height = self._resolve_loc_detect_height()
        if loc_detect_requested and probe_height is None:
            return None
        if loc_detect_requested and not self.start_height_provided:
            self._fail_loc_detection_setup(
                "StartHeightRequired",
                "startHeight is required when locDetectHeight or locDetectLayer is enabled",
            )
            return None
        # Preserve the legacy endHeight-only operation: an omitted startHeight is
        # not an implicit request to move to the runtime default and inspect it.
        if not self.start_height_provided and not loc_detect_requested:
            return False, None, None, None, None
        if not ConfigParams.fork_tip_2D_lasers:
            if loc_detect_requested:
                self._fail_loc_detection_setup(
                    "ForkTipLaserMissing",
                    "Fork tip 2D laser is not configured for location detection; configure "
                    f"Model-000.moduleType.{ConfigParams.module_type}.forkTip2DLasers",
                )
                return None
            # startHeight alone enables detection only on vehicles that actually
            # have a fork-tip 2D laser.  Other vehicles keep the legacy flow.
            return False, None, None, None, None
        if move_to_loc_detect_height and loc_detect_requested and probe_height > ConfigParams.max_height:
            self._fail_loc_detection_setup(
                "LocDetectHeightOutOfRange",
                f"Location detection height {probe_height} exceeds fork max height {ConfigParams.max_height}",
            )
            return None
        roi = self._resolve_loc_detection_roi()
        if roi is None:
            return None
        return loc_detect_requested, probe_height, roi[0], roi[1], roi[2]

    def _build_load_guard_actions(self):
        prepared = self._prepare_loc_detection(move_to_loc_detect_height=True)
        if prepared is None:
            return []
        loc_detect_requested, probe_height, x_min, x_max, y_half_width = prepared
        if not self.start_height_provided and not loc_detect_requested:
            return []
        if x_min is None:
            return []
        if not loc_detect_requested:
            return [
                RunMotorByPosition(ConfigParams.fork_motor_name, self.start_height, action_name="loadProbeStartHeight"),
                self._build_height_probe_action(
                    self.start_height,
                    x_min,
                    x_max,
                    y_half_width,
                    True,
                    "LoadLayerNoGoods",
                    "No goods at load start height",
                    "checkLoadStartHeightGoods",
                ),
            ]
        return [
            RunMotorByPosition(ConfigParams.fork_motor_name, probe_height, action_name="loadProbeLocation"),
            self._build_height_probe_action(
                probe_height,
                x_min,
                x_max,
                y_half_width,
                False,
                "LocDetectHeightHasGoods",
                "Location detection height has goods",
                "checkLoadLocDetectHeightEmpty",
            ),
            RunMotorByPosition(ConfigParams.fork_motor_name, self.start_height, action_name="loadBackToStartHeight"),
            self._build_height_probe_action(
                self.start_height,
                x_min,
                x_max,
                y_half_width,
                True,
                "LoadLayerNoGoods",
                "No goods at load start height",
                "checkLoadStartHeightGoods",
            ),
        ]

    def _build_unload_guard_actions(self):
        height = self._optional_number(self.loc_detect_height)
        layer = self._optional_number(self.loc_detect_layer)
        if (height is not None and height >= 0) or (layer is not None and layer >= 0):
            self._fail_loc_detection_setup(
                "UnloadLocDetectUnsupported",
                "unload does not support locDetectHeight or locDetectLayer",
            )
            return []
        prepared = self._prepare_loc_detection(move_to_loc_detect_height=False)
        if prepared is None:
            return []
        loc_detect_requested, _, x_min, x_max, y_half_width = prepared
        if not self.start_height_provided and not loc_detect_requested:
            return []
        if x_min is None:
            return []
        return [
            RunMotorByPosition(ConfigParams.fork_motor_name, self.start_height, action_name="unloadProbeStartHeight"),
            self._build_height_probe_action(
                self.start_height,
                x_min,
                x_max,
                y_half_width,
                False,
                "UnloadLocationHasGoods",
                "Unload location has goods",
                "checkUnloadStartHeightEmpty",
            ),
        ]

    def _build_cage_stack_guard_actions(self):
        prepared = self._prepare_loc_detection(move_to_loc_detect_height=True)
        if prepared is None:
            return []
        loc_detect_requested, probe_height, x_min, x_max, y_half_width = prepared
        if not self.start_height_provided and not loc_detect_requested:
            return []
        if x_min is None:
            return []
        if not loc_detect_requested:
            if self.recognize:
                return []
            return [
                RunMotorByPosition(
                    ConfigParams.fork_motor_name,
                    self.start_height,
                    action_name="cageStackProbeStartHeight",
                ),
                self._build_height_probe_action(
                    self.start_height,
                    x_min,
                    x_max,
                    y_half_width,
                    False,
                    "CageStackTargetHasGoods",
                    "Cage stack target has goods",
                    "checkCageStackStartHeightEmpty",
                ),
            ]
        actions = [
            RunMotorByPosition(ConfigParams.fork_motor_name, probe_height, action_name="cageStackProbeLocation"),
            self._build_height_probe_action(
                probe_height,
                x_min,
                x_max,
                y_half_width,
                True,
                "CageStackSourceNoGoods",
                "No goods at cage stack detection height",
                "checkCageStackLocDetectHeightGoods",
            ),
            RunMotorByPosition(ConfigParams.fork_motor_name, self.start_height, action_name="cageStackBackToStartHeight"),
        ]
        if not self.recognize:
            actions.append(self._build_height_probe_action(
                self.start_height,
                x_min,
                x_max,
                y_half_width,
                False,
                "CageStackTargetHasGoods",
                "Cage stack target has goods",
                "checkCageStackStartHeightEmpty",
            ))
        return actions

    def _build_cage_stack_pre_insert_guard_actions(self):
        if not self.recognize:
            return []
        prepared = self._prepare_loc_detection(move_to_loc_detect_height=False)
        if prepared is None:
            return []
        loc_detect_requested, _, x_min, x_max, y_half_width = prepared
        if not self.start_height_provided and not loc_detect_requested:
            return []
        if x_min is None:
            return []
        return [self._build_height_probe_action(
            self.rec_height,
            x_min,
            x_max,
            y_half_width,
            False,
            "CageStackTargetHasGoods",
            "Cage stack target has goods",
            "checkCageStackRecHeightEmpty",
        )]


robot = CounterBalanceWithShiftFork(__file__)


if __name__ == "__main__":
    robot.main()
