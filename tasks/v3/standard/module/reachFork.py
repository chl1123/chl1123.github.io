# -*- coding: utf-8 -*-

import json
import math
import time

from syspy import Laser, Motor, Navigation, NavStatus, RobotParam, ScriptStatus, Trace, _TR
from syspy.lib.module import CollisionType, SafeMoveStatus
from syspy.utils.param_server import ParamType

from standard.fork import ConfigParams, ReachFork as BaseReachFork
from standard.fork_utils import (
    ActionStatus,
    GoPathWithContactDi,
    Rec,
    RunReachMotorsByPosition,
    RunMotorByPosition,
    calculate_recognition_pick_height,
    clamp,
    extract_recognition_height_z,
    load_pallet_z_offset,
    normalize_recognition_result_metadata,
    pos2World,
)

REACH_LASER_BLOCK_KEY = "ReachForkTipLaserObstacle"
REACH_LASER_NO_DATA_BLOCK_KEY = "ReachForkTipLaserNoData"
REACH_REC_HEIGHT_TOLERANCE = 0.2


class ReachPalletSelect(Rec):
    """识别多层栈板并默认选择最低层，不依赖 goodsLayer。"""

    def __init__(
            self,
            pallet_file,
            rec_height=-1.0,
            rec_center_x=-1.0,
            rec_center_y=0.0,
            rec_radius=0.7,
    ):
        super().__init__(
            pallet_file,
            rec_center_x,
            rec_center_y,
            rec_radius,
            action_name="RecPalletSelect",
            z_max=False,
        )
        self.selected_recognition_z = None
        self.selected_world_pos = None
        self.selected_robot_pos = None
        self.selected_result = {}
        self.total_layers = 0
        try:
            self.rec_height = float(rec_height)
        except (TypeError, ValueError):
            self.rec_height = -1.0
        self.height_tolerance = REACH_REC_HEIGHT_TOLERANCE

    @staticmethod
    def _recognition_z(result):
        if not isinstance(result, dict):
            return None

        hole_info = result.get("holeInfo", [])
        if isinstance(hole_info, list):
            for item in hole_info:
                if not isinstance(item, dict):
                    continue
                value = item.get("z", item.get("robotResultZ"))
                try:
                    if value is not None:
                        return float(value)
                except (TypeError, ValueError):
                    pass

        info_list = result.get("info", [])
        if isinstance(info_list, str):
            try:
                info_list = json.loads(info_list)
            except (TypeError, ValueError, json.JSONDecodeError):
                info_list = []
        if isinstance(info_list, list):
            for item in info_list:
                if isinstance(item, str):
                    try:
                        item = json.loads(item)
                    except (TypeError, ValueError, json.JSONDecodeError):
                        continue
                if not isinstance(item, dict):
                    continue
                try:
                    if item.get("robotResultZ") is not None:
                        return float(item["robotResultZ"])
                except (TypeError, ValueError):
                    pass

        for parent_key in ("robotResult", "worldResult"):
            parent = result.get(parent_key, {})
            if not isinstance(parent, dict):
                continue
            try:
                if parent.get("z") is not None:
                    return float(parent["z"])
            except (TypeError, ValueError):
                pass
        return None

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
        candidates = []
        for result in results_list:
            normalize_recognition_result_metadata(result)
            recognition_z = self._recognition_z(result)
            if recognition_z is not None:
                candidates.append((recognition_z, result))
        if not candidates:
            Navigation.setTaskError(
                "RecLayerMissing",
                "recognition result has no pallet layer height",
            )
            self.action_status = ActionStatus.FAILED
            return

        self.total_layers = len(candidates)
        if self.rec_height >= 0:
            height_candidates = [
                item for item in candidates
                if abs(item[0] - self.rec_height) <= self.height_tolerance + 1e-9
            ]
            if not height_candidates:
                recognized_heights = ", ".join(f"{item[0]:.3f}" for item in candidates)
                Navigation.setTaskError(
                    "RecHeightOutOfRange",
                    f"no recognition result is within {self.height_tolerance:.3f}m of "
                    f"recHeight {self.rec_height:.3f}m; recognized z=[{recognized_heights}]",
                )
                Trace.log(
                    f"reach pallet recognition filtered all layers: recHeight={self.rec_height}, "
                    f"tolerance={self.height_tolerance}, heights=[{recognized_heights}]",
                    name="fork.err",
                )
                self.action_status = ActionStatus.FAILED
                return
            candidates = height_candidates

        candidates.sort(key=lambda item: item[0])
        selected_z, selected = candidates[0]
        self.results_list = [selected]
        self.result = selected
        self.selected_result = selected
        self.selected_recognition_z = selected_z
        self.fork_height_at_recognition = Motor.getMotorPos(ConfigParams.fork_motor_name)

        world_result = selected.get("worldResult", {})
        robot_result = selected.get("robotResult", {})
        world_result = world_result if isinstance(world_result, dict) else {}
        robot_result = robot_result if isinstance(robot_result, dict) else {}
        self.selected_world_pos = [
            float(world_result.get("x", selected.get("x", 0.0))),
            float(world_result.get("y", selected.get("y", 0.0))),
            float(world_result.get("yaw", selected.get("yaw", 0.0))),
        ]
        self.selected_robot_pos = [
            float(robot_result.get("x", selected.get("x", 0.0))),
            float(robot_result.get("y", selected.get("y", 0.0))),
            float(robot_result.get("yaw", selected.get("yaw", 0.0))),
        ]
        Trace.log(
            f"reach pallet selected lowest layer: total={self.total_layers}, "
            f"valid={len(candidates)}, recHeight={self.rec_height}, z={selected_z}",
            name="fork.task",
        )
        self.action_status = ActionStatus.FINISHED


def _reach_fork_config_builder(_config_cls, builder):
    """前移车型默认值和前移期间的叉尖激光检测参数。"""

    defaults = {
        # 公共配置枚举的历史键名为 strechFirst，对外语义仍是 stretchFirst。
        "adjustMethod": "strechFirst",
        "forkLeaveSafeHeight": 0.4,
    }

    def apply_defaults(nodes):
        for node in nodes:
            if node.key in defaults:
                node.default_value = defaults[node.key]
            apply_defaults(node.children)

    apply_defaults(builder.root["groups"])
    with builder.GROUP(
            key="reachLaserObstacle",
            name=_TR("Reach Laser Obstacle"),
            desc=_TR("Fork tip laser obstacle detection while the reach motors extend"),
    ):
        builder.TYPE(ParamType.ARRAY)
        with builder.CHILDREN():
            with builder.CHILD(
                    key="reachLaserObsExpansion",
                    name=_TR("Reach Laser Obstacle Expansion"),
                    desc=_TR("Additional lateral obstacle expansion while the reach motors extend"),
            ):
                builder.TYPE(ParamType.FLOAT)
                builder.DEFAULTVALUE(0.02, min_value=0, max_value=1)
                builder.UNIT("m")
            with builder.CHILD(
                    key="reachLaserDetectionDebounce",
                    name=_TR("Reach Laser Detection Debounce"),
                    desc=_TR("Consecutive laser samples required to block or resume the reach motors"),
            ):
                builder.TYPE(ParamType.INT)
                builder.DEFAULTVALUE(2, min_value=1, max_value=20)


def _reach_fork_config_reload(config_cls, cfg):
    """stretchFirst 与导航中升降互斥，车型侧直接忽略冲突配置。"""

    config_cls.reachLaserObsExpansion = max(
        0.0,
        config_cls._safe_float(config_cls._find_config_value(["reachLaserObsExpansion"], cfg), 0.02),
    )
    config_cls.reachLaserDetectionDebounce = max(
        1,
        int(config_cls._safe_float(
            config_cls._find_config_value(["reachLaserDetectionDebounce"], cfg), 2
        )),
    )
    if config_cls.adjustMethod not in ("strechFirst", "stretchFirst"):
        return
    ignored = []
    if config_cls.enableNavForkHeight:
        ignored.append("enableNavForkHeight")
    if config_cls.enableLoadNavForkHeight:
        ignored.append("enableLoadNavForkHeight")
    if ignored:
        Trace.log(
            f"stretchFirst ignores navigation fork height config: {ignored}",
            name="fork.cfg",
        )
    config_cls.enableNavForkHeight = False
    config_cls.enableLoadNavForkHeight = False


def _moving_obstacle_device_keys():
    """前移时坐标系会移动的设备；距离节点只屏蔽，不再参与脚本判断。"""
    return list(dict.fromkeys(
        str(key).strip()
        for key in list(ConfigParams.fork_tip_2D_lasers or []) + list(ConfigParams.fork_tip_distance_sensors or [])
        if str(key).strip()
    ))


def _policy_collision_devices(config_key):
    value = RobotParam.getConfig("navigation", config_key)
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def _extension_distance(motor_names, *, current=False):
    distances = []
    for motor_name in motor_names:
        minimum, maximum = ConfigParams._get_motor_limits(motor_name)
        if current:
            try:
                distances.append(max(0.0, float(Motor.getMotorPos(motor_name)) - minimum))
                continue
            except Exception:
                pass
        distances.append(max(0.0, maximum - minimum))
    return max(distances, default=0.0)


class ReachTipLaserObstacleMonitor:
    """将车体系前移检测矩形实时投影到每只叉尖激光的原始坐标系。"""

    def __init__(self, motor_names, stop_dist, obs_expansion):
        self.motor_names = list(motor_names or [])
        self.stop_dist = max(0.0, float(stop_dist or 0.0))
        self.obs_expansion = max(0.0, float(obs_expansion or 0.0))
        self.laser_keys = {str(key).strip() for key in ConfigParams.fork_tip_2D_lasers if str(key).strip()}
        self.debounce = max(1, int(getattr(ConfigParams, "reachLaserDetectionDebounce", 2) or 2))
        self.blocked = False
        self.detect_count = 0
        self.clear_count = 0
        self.last_obstacle = None
        self.no_data_logged = False
        self.no_data_count = 0
        self.block_reason = ""

    @staticmethod
    def _value(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    def _target_lasers(self, data):
        lasers = self._value(data, "laser", []) or []
        targets = []
        for laser in lasers:
            device_info = self._value(laser, "deviceInfo", {}) or {}
            key = str(self._value(device_info, "key", "")).strip()
            if key in self.laser_keys:
                targets.append((key, laser))
        return targets

    @staticmethod
    def _point_in_polygon(point, polygon):
        x, y = point
        inside = False
        for index, (x1, y1) in enumerate(polygon):
            x2, y2 = polygon[index - 1]
            if (y1 > y) != (y2 > y):
                cross_x = (x2 - x1) * (y - y1) / (y2 - y1) + x1
                if x < cross_x:
                    inside = not inside
        return inside

    @staticmethod
    def _base_to_laser(point, laser_pose):
        dx, dy = point[0] - laser_pose[0], point[1] - laser_pose[1]
        cos_yaw, sin_yaw = math.cos(laser_pose[2]), math.sin(laser_pose[2])
        return [cos_yaw * dx + sin_yaw * dy, -sin_yaw * dx + cos_yaw * dy]

    @staticmethod
    def _laser_to_base(point, laser_pose):
        cos_yaw, sin_yaw = math.cos(laser_pose[2]), math.sin(laser_pose[2])
        return [
            laser_pose[0] + cos_yaw * point[0] - sin_yaw * point[1],
            laser_pose[1] + sin_yaw * point[0] + cos_yaw * point[1],
        ]

    def _laser_pose(self, laser, extension):
        install = self._value(laser, "installInfo", {}) or {}
        install_x = self._value(install, "x", None)
        return [
            float(ConfigParams.module_x if install_x is None else install_x) + extension,
            float(self._value(install, "y", 0.0) or 0.0),
            math.radians(float(self._value(install, "yaw", 0.0) or 0.0)),
        ]

    def _base_rectangle(self, poses):
        # 矩形先在车体系建立，再转换到每只激光坐标系。横向范围包含两根叉齿和策略膨胀。
        x_values = [pose[0] for pose in poses]
        outer_half_width = max(
            float(ConfigParams.laserDetectionWidth or 0.0),
            (float(ConfigParams.center_distance_between_forks) + float(ConfigParams.fork_tip_width)) / 2.0,
        ) + self.obs_expansion
        x_min = min(x_values)
        x_max = max(x_values) + self.stop_dist + self.obs_expansion
        return [
            [x_min, -outer_half_width], [x_max, -outer_half_width],
            [x_max, outer_half_width], [x_min, outer_half_width],
        ]

    def _beam_point(self, beam):
        valid = bool(self._value(beam, "valid", False))
        if not valid or bool(self._value(beam, "isVirtual", False)):
            return None
        try:
            distance = float(self._value(beam, "dist", 0.0) or 0.0)
            angle = float(self._value(beam, "angle", 0.0) or 0.0)
        except (TypeError, ValueError):
            return None
        if distance <= 0.02:
            return None
        angle = math.radians(angle)
        return [distance * math.cos(angle), distance * math.sin(angle)]

    def _find_obstacle(self):
        if not self.laser_keys:
            return None, "no configured fork tip laser"
        try:
            data = Laser.getData()
        except Exception as exc:
            return None, f"read laser failed: {exc}"
        targets = self._target_lasers(data)
        if not targets:
            return None, "fork tip laser data is unavailable"

        extension = _extension_distance(self.motor_names, current=True)
        poses = [self._laser_pose(laser, extension) for _, laser in targets]
        base_rectangle = self._base_rectangle(poses)
        detection_width = max(0.0, float(ConfigParams.laserDetectionWidth or 0.0))
        valid_beams = 0
        for (key, laser), pose in zip(targets, poses):
            laser_rectangle = [self._base_to_laser(point, pose) for point in base_rectangle]
            for beam in self._value(laser, "beams", []) or []:
                point = self._beam_point(beam)
                if point is None:
                    continue
                valid_beams += 1
                # 原始点只保留激光 y 方向的配置带宽，不能使用 MF 已转换的车体系点。
                if abs(point[1]) > detection_width:
                    continue
                if self._point_in_polygon(point, laser_rectangle):
                    base_point = self._laser_to_base(point, pose)
                    return {
                        "key": key,
                        "laser_point": point,
                        "base_point": base_point,
                        "extension": extension,
                        "base_rectangle": base_rectangle,
                    }, ""
        if valid_beams == 0:
            return None, "fork tip laser has no valid raw beams"
        return False, ""

    def poll(self):
        obstacle, reason = self._find_obstacle()
        if obstacle is None:
            # 无数据不是“无障碍物”；连续缺帧也进入 MF block，数据恢复后再按释放去抖清除。
            self.no_data_count += 1
            self.detect_count = 0
            self.clear_count = 0
            if not self.no_data_logged:
                Trace.log(f"reach fork tip laser monitor: {reason}", name="fork.err")
                self.no_data_logged = True
            if not self.blocked and self.no_data_count >= self.debounce:
                Navigation.setBlockReason(
                    CollisionType.APIObstacle, 0.0, 0.0, REACH_LASER_NO_DATA_BLOCK_KEY
                )
                self.blocked = True
                self.block_reason = "no_data"
            return self.blocked
        self.no_data_logged = False
        self.no_data_count = 0
        if obstacle:
            self.last_obstacle = obstacle
            self.detect_count += 1
            self.clear_count = 0
            if not self.blocked and self.detect_count >= self.debounce:
                x, y = obstacle["base_point"]
                Navigation.setBlockReason(CollisionType.Laser, x, y, REACH_LASER_BLOCK_KEY)
                self.blocked = True
                self.block_reason = "obstacle"
                Trace.log(
                    f"reach fork laser blocked: key={obstacle['key']}, x={x:.3f}, y={y:.3f}, "
                    f"description=fork tip raw laser point in reach ROI, extension={obstacle['extension']:.3f}",
                    name="fork.err",
                )
            return self.blocked

        self.detect_count = 0
        self.clear_count += 1
        if self.blocked and self.clear_count >= self.debounce:
            NavStatus.clearBlock()
            self.blocked = False
            self.block_reason = ""
            Trace.log("reach fork laser obstacle cleared after continuous empty samples", name="fork.task")
        return self.blocked

    def clear(self):
        if self.blocked:
            NavStatus.clearBlock()
            self.blocked = False
            self.block_reason = ""


class _ReachMovingDevicePolicy:
    """在前移期间屏蔽随叉尖移动的 MF 避障设备，原始激光仍由脚本读取。"""

    def _begin_reach_moving_device_policy(self):
        if getattr(self, "_reach_device_policy_active", False):
            return
        devices = _moving_obstacle_device_keys()
        self._reach_device_policy_active = True
        self._reach_device_restore_policy = {}
        self._reach_expansion_restore_policy = {}
        for config_key in ("collisionDetection.detectionDevice", "collisionDetection.collisionDevice"):
            policy_key = f"navigation.{config_key}"
            if policy_key in self.policy:
                current = [
                    item.strip()
                    for item in str(self.policy[policy_key] or "").split(",")
                    if item.strip()
                ]
            else:
                current = _policy_collision_devices(config_key)
            self._reach_device_restore_policy[config_key] = current
            remaining = [device for device in current if device not in devices]
            if remaining != current:
                self.policy[policy_key] = ",".join(remaining)
        self._set_obs_stop_dist(float(ConfigParams.loadObsStopDist or 0.0))
        expansion = max(0.0, float(getattr(ConfigParams, "reachLaserObsExpansion", 0.02) or 0.02))
        for policy_key, default in (
                ("navigation.obstacleStop.obsStopUnload.obsExpansion", 0.02),
                ("navigation.obstacleStop.obsStopLoad.loadObsExpansion", 0.01),
        ):
            self._reach_expansion_restore_policy[policy_key] = self.policy.get(policy_key, default)
            self.policy[policy_key] = expansion
        self._apply_policy("reachMovingDeviceShieldPolicy", reset_path=True)
        Trace.log(f"reach moving devices disabled: {devices}", name="fork.task")

    def _finish_reach_moving_device_policy(self, extension):
        if not getattr(self, "_reach_device_policy_active", False):
            return
        for config_key, devices in self._reach_device_restore_policy.items():
            self.policy[f"navigation.{config_key}"] = ",".join(devices)
        self.policy.update(self._reach_expansion_restore_policy)
        self._set_obs_stop_dist(float(ConfigParams.loadObsStopDist or 0.0) + extension)
        self._apply_policy("reachMovingDeviceRestorePolicy", reset_path=True)
        self._reach_device_policy_active = False
        Trace.log(
            f"reach moving devices restored, obsStopDist={float(ConfigParams.loadObsStopDist or 0.0) + extension:.3f}",
            name="fork.task",
        )


class ReachGoPathWithContactDi(_ReachMovingDevicePolicy, GoPathWithContactDi):
    """pathFirst 前移阶段的叉尖原始激光避障包装。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._reach_device_policy_active = False
        self._reach_device_restore_policy = {}
        self.reach_laser_monitor = None

    def _reach_obs_expansion(self):
        return max(0.0, float(getattr(ConfigParams, "reachLaserObsExpansion", 0.02) or 0.02))

    def _ensure_reach_laser_monitor(self):
        if self.reach_laser_monitor is None:
            self.reach_laser_monitor = ReachTipLaserObstacleMonitor(
                self.reach_motor_names,
                ConfigParams.loadObsStopDist,
                self._reach_obs_expansion(),
            )

    def _advance_back_action(self):
        if self.reach_phase_enabled and self.reach_phase == "reach":
            self._begin_reach_moving_device_policy()
            self._ensure_reach_laser_monitor()
            if self.reach_laser_monitor.poll():
                return True
        return super()._advance_back_action()

    def _handle_motion_extensions(self):
        if (self.reach_phase_enabled and self.reach_phase == "reach" and self.reach_action is not None
                and self.reach_action.action_status == ActionStatus.FINISHED):
            extension = _extension_distance(self.reach_motor_names)
            self._finish_reach_moving_device_policy(extension)
            if self.reach_laser_monitor is not None:
                self.reach_laser_monitor.clear()
            # 基类在进入 final_path 时按该补偿写回策略，保证停车距离包含前移行程。
            self.reach_final_obs_dist_compensation = extension
        return super()._handle_motion_extensions()

    def _cleanup_terminal_state(self):
        if self.action_status in [ActionStatus.FINISHED, ActionStatus.FAILED]:
            if self.reach_laser_monitor is not None:
                self.reach_laser_monitor.clear()
            self._finish_reach_moving_device_policy(_extension_distance(self.reach_motor_names))
        super()._cleanup_terminal_state()

    def _build_reach_phase_action(self):
        if not self.reach_motor_names:
            Navigation.setTaskError("ReachMotorMissing", "reach motor is not configured for staged pathFirst")
            self.action_status = ActionStatus.FAILED
            return None
        return ReachRunReachMotorsByPosition(
            self.reach_motor_names, self.reach_target, self.reach_max_speed,
            self.reach_sync_tolerance, contact_di=[], check_all_di=False,
            action_name="extendReachMotors", monitor_owned_by_path=True,
        )


class ReachRunReachMotorsByPosition(RunReachMotorsByPosition):
    """独立前移动作的叉尖原始激光避障。"""

    def __init__(self, motor_names, target="max", max_speed=0.1, sync_tolerance=0.02,
                 contact_di=None, check_all_di=False, action_name="RunReachMotors",
                 monitor_owned_by_path=False):
        super().__init__(motor_names, target=target, max_speed=max_speed,
                         sync_tolerance=sync_tolerance, contact_di=contact_di,
                         check_all_di=check_all_di, action_name=action_name)
        self.monitor_owned_by_path = monitor_owned_by_path
        self.reach_laser_monitor = None
        self._device_policy_active = False
        self._restore_policy = {}
        self._restore_expansion_policy = {}

    def _policy(self, name, values):
        Navigation.appendCustomPolicy(name, values)
        Navigation.goPathParam(dict())

    def _begin_policy(self):
        if self._device_policy_active or self.monitor_owned_by_path:
            return
        moving_devices = _moving_obstacle_device_keys()
        policy = {}
        for config_key in ("collisionDetection.detectionDevice", "collisionDetection.collisionDevice"):
            current = _policy_collision_devices(config_key)
            self._restore_policy[config_key] = current
            remaining = [device for device in current if device not in moving_devices]
            if current != remaining:
                policy[f"navigation.{config_key}"] = ",".join(remaining)
        # 保留临时策略的膨胀宽度，并显式下发停车距离，避免前移动作走默认策略。
        policy["navigation.obstacleStop.obsStopUnload.obsStopDist"] = float(ConfigParams.loadObsStopDist or 0.0)
        policy["navigation.obstacleStop.obsStopLoad.loadObsStopDist"] = float(ConfigParams.loadObsStopDist or 0.0)
        expansion = float(getattr(ConfigParams, "reachLaserObsExpansion", 0.02) or 0.02)
        for config_key, default in (
                ("obstacleStop.obsStopUnload.obsExpansion", 0.02),
                ("obstacleStop.obsStopLoad.loadObsExpansion", 0.01),
        ):
            configured = RobotParam.getConfig("navigation", config_key)
            self._restore_expansion_policy[f"navigation.{config_key}"] = (
                default if configured is None else configured
            )
            policy[f"navigation.{config_key}"] = expansion
        self._policy("reachMotorMovingDeviceShieldPolicy", policy)
        self._device_policy_active = True
        Trace.log(f"reach motor moving devices disabled: {moving_devices}", name="fork.task")

    def _finish_policy(self):
        if not self._device_policy_active:
            return
        extension = _extension_distance(self.motor_names)
        policy = {
            f"navigation.{config_key}": ",".join(devices)
            for config_key, devices in self._restore_policy.items()
        }
        policy.update(self._restore_expansion_policy)
        policy["navigation.obstacleStop.obsStopUnload.obsStopDist"] = float(ConfigParams.loadObsStopDist or 0.0) + extension
        policy["navigation.obstacleStop.obsStopLoad.loadObsStopDist"] = float(ConfigParams.loadObsStopDist or 0.0) + extension
        self._policy("reachMotorMovingDeviceRestorePolicy", policy)
        self._device_policy_active = False
        Trace.log(f"reach motor moving devices restored, extension={extension:.3f}", name="fork.task")

    def run(self, ctx=None):
        if self.action_status in (ActionStatus.FINISHED, ActionStatus.FAILED):
            return
        if self.target == "max" and not self.monitor_owned_by_path:
            self._begin_policy()
            if self.reach_laser_monitor is None:
                self.reach_laser_monitor = ReachTipLaserObstacleMonitor(
                    self.motor_names,
                    ConfigParams.loadObsStopDist,
                    getattr(ConfigParams, "reachLaserObsExpansion", 0.02),
                )
            if self.reach_laser_monitor.poll():
                return
        super().run(ctx)
        if self.action_status in (ActionStatus.FINISHED, ActionStatus.FAILED):
            if self.reach_laser_monitor is not None:
                self.reach_laser_monitor.clear()
            self._finish_policy()

    def cancel(self):
        super().cancel()
        if self.reach_laser_monitor is not None:
            self.reach_laser_monitor.clear()
        self._finish_policy()

    def reset(self):
        if self.reach_laser_monitor is not None:
            self.reach_laser_monitor.clear()
        self._finish_policy()
        super().reset()


class ReachFork(BaseReachFork):
    """带前移机构车型，并在前移期间使用叉尖 2D 激光原始点云避障。"""

    config_builder_hook = staticmethod(_reach_fork_config_builder)
    config_reload_hook = staticmethod(_reach_fork_config_reload)

    @staticmethod
    def _stretch_first_enabled():
        return ConfigParams.adjustMethod in ("strechFirst", "stretchFirst")

    def _create_load_recognition_action(self, rec_center2robot):
        return ReachPalletSelect(
            self.recfile,
            rec_height=self.rec_height,
            rec_center_x=rec_center2robot[0],
            rec_center_y=rec_center2robot[1],
            rec_radius=ConfigParams.recRadius,
        )

    def _prepare_load_recognition_height(self, rec_action):
        """前移车始终根据最低层识别结果计算取货高度。"""
        recognition_z = extract_recognition_height_z(rec_action)
        if recognition_z is None:
            Navigation.setTaskError("RecHeightMissing", "recognition height z is missing")
            self.set_status(ScriptStatus.FAILED)
            return False

        rec_info = getattr(self, "rec_info", None)
        rec_side = rec_info.get("side_value") if isinstance(rec_info, dict) else getattr(self, "recSide", None)
        raw_height = calculate_recognition_pick_height(
            recognition_z,
            load_pallet_z_offset(self.recfile, rec_side),
            camera_moves_with_fork=self.camera_moves_with_fork,
            fork_height_at_recognition=getattr(rec_action, "fork_height_at_recognition", 0.0),
            camera_calibration_fork_height=ConfigParams._safe_float(
                getattr(ConfigParams, "camCalibMotorHeight", 0.0),
                0.0,
            ),
        )
        self.load_recognition_pick_height = clamp(
            raw_height,
            ConfigParams.min_height,
            ConfigParams.max_height,
        )
        Trace.log(
            f"reach selected layer height:{self.load_recognition_pick_height}, "
            f"raw:{raw_height}, rec_z:{recognition_z}",
            name="fork.task",
        )
        return True

    def _build_load_entry_batch(self, rec_action):
        if not ConfigParams.reach_motor_names:
            return super()._build_load_entry_batch(rec_action)
        # 未前移时只允许到识别 startHeight，不能提前下降；recHeight 仅过滤识别结果，
        # 不作为货叉运动目标。
        return self._build_start_height_actions() + [rec_action]

    def _build_load_approach_batch(self, rec_action, rec_world_pos, method, args):
        if not ConfigParams.reach_motor_names:
            return super()._build_load_approach_batch(rec_action, rec_world_pos, method, args)

        # 识别后必须先完成前移，才允许下降到选中层高度；下降后直接进叉，
        # 不再执行 recHeight 或任何二次抬高动作。
        if ConfigParams.adjustMethod == "pathFirst":
            actions = self._build_path_first_load_actions(rec_world_pos, method, args)
            expand_action = self._build_expand_motor_action(rec_action)
            if expand_action is not None:
                actions.insert(-1, expand_action)
            return actions

        actions = [self._build_reach_action("max", action_name="extendReachMotors")]
        if self.load_recognition_pick_height is not None:
            actions.append(RunMotorByPosition(
                ConfigParams.fork_motor_name,
                self.load_recognition_pick_height,
                ConfigParams.fork_max_speed,
                "selectedLayerHeight",
            ))
        expand_action = self._build_expand_motor_action(rec_action)
        if expand_action is not None:
            actions.append(expand_action)
        actions.append(self._build_reach_path_action(
            rec_world_pos,
            method,
            args,
            operation_type="load",
            check_di=self.check_di,
        ))
        return actions

    def safe_move_check(self):
        if not self._stretch_first_enabled():
            return super().safe_move_check()
        self.setSafeMoveStatus(SafeMoveStatus.FINISHED)
        self.event_safe_move_check = False

    def _build_reach_action(self, target, *, stop_on_contact=False, action_name="RunReachMotors"):
        if target == "max" and action_name == "extendReachMotors":
            return ReachRunReachMotorsByPosition(
                ConfigParams.reach_motor_names, target, ConfigParams.reachMotorMaxSpeed,
                ConfigParams.reachMotorSyncTolerance,
                contact_di=ConfigParams.contact_ids if stop_on_contact else [],
                check_all_di=ConfigParams.checkAllContactDis, action_name=action_name,
            )
        return super()._build_reach_action(target, stop_on_contact=stop_on_contact, action_name=action_name)

    def _build_reach_path_action(self, target_pos, method, args, *, operation_type, check_di,
                                 obs_dist_compensation=0.0):
        path_target = target_pos
        path_method, path_args = self._reach_adjusted_plan(method, args)
        if path_method == "goPath":
            path_target = self._shift_path_target_for_reach(target_pos)
        if operation_type == "load":
            obs_dist_compensation = max(
                float(obs_dist_compensation or 0.0),
                self._reach_extension_distance(),
            )
        return ReachGoPathWithContactDi(
            ConfigParams.contact_ids, path_target,
            ConfigParams.loadObsStopDist if operation_type == "load" else None,
            path_method, path_args, check_di, operation_type,
            obs_dist_compensation=obs_dist_compensation,
            recfile=self.recfile,
        )

    def _build_path_first_load_actions(self, rec_world_pos, method, args):
        # pathFirst 保留“底盘先对齐”的差异，但下降仍必须晚于前移。
        reach_distance = self._reach_extension_distance()
        front_dist = ConfigParams.minAheadDist + reach_distance
        if method == "goPath":
            align_world_pos = pos2World([-front_dist, 0.0, 0.0], rec_world_pos)
            align_method, align_args = "goPath", {}
        else:
            align_world_pos, align_method = rec_world_pos, method
            align_args = dict(args or {})
            align_args["back_dist"], align_args["min_ahead_dist"] = front_dist, front_dist
        final_target = pos2World([reach_distance - float(self.back_dist), 0.0, 0.0], rec_world_pos)
        actions = [
            GoPathWithContactDi(
                ConfigParams.contact_ids, align_world_pos, ConfigParams.loadObsStopDist,
                align_method, align_args, self.check_di, "load", recfile=self.recfile,
            ),
            self._build_reach_action("max", action_name="extendReachMotors"),
        ]
        if self.load_recognition_pick_height is not None:
            actions.append(RunMotorByPosition(
                ConfigParams.fork_motor_name,
                self.load_recognition_pick_height,
                ConfigParams.fork_max_speed,
                "selectedLayerHeight",
            ))
        actions.append(ReachGoPathWithContactDi(
            ConfigParams.contact_ids, final_target, ConfigParams.loadObsStopDist,
            "goPath", {}, self.check_di, "load",
            obs_dist_compensation=reach_distance,
            recfile=self.recfile,
        ))
        return actions


robot = ReachFork(__file__)


if __name__ == "__main__":
    robot.main()
