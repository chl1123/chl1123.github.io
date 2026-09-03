# -*- coding: utf-8 -*-
import math
import time

from syspy import Container, Di, Laser, Motor, Navigation, NavStatus, RobotParam, ScriptStatus, Trace, _TR
from syspy.lib.action_task import ActionBase
from syspy.lib.module import pos2Base, pos2World
from syspy.utils.param_server import BindType, ParamType

from standard.fork import ConfigParams, Fork, ReachFork
from standard.fork_utils import (
    ActionStatus,
    GoPathWithContactDi,
    ReachAwareForkMotorByPosition,
    RunReachMotorsByPosition,
    _fork_apply_loaded_speed_limit,
    _fork_check_back_laser_collision,
    _fork_prepare_target_position,
    clamp,
    get_r_loc,
    is_do_motor_key,
)
from standard.goPath import GoPath


def _type_e_config_builder(_config_cls, builder):
    with builder.GROUP(key="typeELift", name=_TR("Type E Lift"), desc=_TR("Type E scissor lift settings")):
        builder.TYPE(ParamType.ARRAY)
        with builder.CHILDREN():
            params = (
                ("liftVelocity", -1.0, ParamType.FLOAT, "m/s", _TR("Optional lift motor speed limit")),
                ("liftZeroPosition", 0.0, ParamType.FLOAT, "m", _TR("Fork zero height")),
                ("liftMotorSlowRange", 0.01, ParamType.FLOAT, "m", _TR("Low-speed range near zero")),
                ("liftMotorActualZero1", -0.005, ParamType.FLOAT, "m", _TR("First lift motor actual zero")),
                ("liftMotorActualZero2", -0.005, ParamType.FLOAT, "m", _TR("Second lift motor actual zero")),
                ("liftMotorActualZeroOffset1", 0.0, ParamType.FLOAT, "m", _TR("First lift motor zero offset")),
                ("liftMotorActualZeroOffset2", 0.0, ParamType.FLOAT, "m", _TR("Second lift motor zero offset")),
                ("liftMotorSyncTolerance", 0.008, ParamType.FLOAT, "m", _TR("Lift motor synchronization tolerance")),
                ("liftOperationTimeout", 20.0, ParamType.FLOAT, "s", _TR("Lift operation timeout")),
                ("motorCalibTimeout", 30.0, ParamType.FLOAT, "s", _TR("Motor calibration timeout")),
                ("link1Length", 0.185, ParamType.FLOAT, "m", _TR("Scissor long link length")),
                ("link2Length", 0.05, ParamType.FLOAT, "m", _TR("Scissor short link length")),
                ("joint2Bottom", 0.03, ParamType.FLOAT, "m", _TR("Lower joint to fork bottom distance")),
                ("joint2Top", 0.05, ParamType.FLOAT, "m", _TR("Upper joint to fork top distance")),
                ("joint2MiddleMaxDist", 0.18497, ParamType.FLOAT, "m", _TR("Maximum joint-to-center distance")),
                ("joint2MiddleMinDist", 0.052, ParamType.FLOAT, "m", _TR("Minimum joint-to-center distance")),
                ("typeELoadConfirmDistance", 0.15, ParamType.FLOAT, "m", _TR("Reverse distance used to confirm load contact DI")),
                ("typeEChassisSyncSpeed", 0.05, ParamType.FLOAT, "m/s", _TR("Chassis speed while synchronizing the reach motor")),
                ("typeEPolicyDelay", 0.1, ParamType.FLOAT, "s", _TR("Wait after changing Type E collision policy")),
                ("typeEBackLaserWidth", 0.3, ParamType.FLOAT, "m", _TR("Back laser detection width while moving the chassis under a stationary fork")),
                ("typeEHookAlignSpeed", 0.02, ParamType.FLOAT, "m/s", _TR("Reach motor speed while aligning the hook")),
                ("typeEHookAlignTravel", 0.02, ParamType.FLOAT, "m", _TR("重连前为货叉对齐预留的前移距离")),
                ("typeEHookAlignTimeout", 5.0, ParamType.FLOAT, "s", _TR("货叉对齐超时时间")),
                ("typeEHookReconnectSpeed", 0.07, ParamType.FLOAT, "m/s", _TR("重连扫描时的前移电机速度")),
                ("typeEHookReconnectLimitMargin", 0.001, ParamType.FLOAT, "m", _TR("重连扫描时距离前移限位的安全距离")),
                ("stretchUnloadLength", 1.22, ParamType.FLOAT, "m", _TR("放货时 Motor-005 拉线编码器目标位置")),
                ("stretchWirePositionTolerance", 0.02, ParamType.FLOAT, "m", _TR("放货时 Motor-005 位置误差阈值")),
                ("stretchWireMotor", "Motor-005", ParamType.STRING, "", _TR("前移机构拉线编码器电机名称")),
            )
            for key, default, param_type, unit, desc in params:
                with builder.CHILD(key=key, name=_TR(key), desc=desc):
                    builder.TYPE(param_type)
                    builder.DEFAULTVALUE(default)
                    if unit:
                        builder.UNIT(unit)
            with builder.CHILD(key="typeEHookAlignDi", name=_TR("Type E Hook Align DI"),
                               desc=_TR("货叉挂钩与U形槽对齐到位 DI")):
                builder.TYPE(ParamType.BIND_TYPE)
                builder.BINDTYPE(BindType.Device.DI, multiple=True)
            with builder.CHILD(key="typeEHookReconnectDi", name=_TR("Type E Hook Reconnect DI"),
                               desc=_TR("取货后货叉挂钩重连确认 DI")):
                builder.TYPE(ParamType.BIND_TYPE)
                builder.BINDTYPE(BindType.Device.DI, multiple=True)


def _config_keys(value):
    if isinstance(value, (list, tuple)):
        values = value
    else:
        values = str(value or "").split(",")
    return [str(item).strip() for item in values if str(item).strip()]


def _motor_float(config_cls, motor_name, key, default=None):
    if not motor_name:
        return default
    motor_func = RobotParam.getDevice(motor_name, "func") or ""
    value = RobotParam.getDevice(motor_name, f"func.{motor_func}.{key}") if motor_func else None
    if value is None:
        value = RobotParam.getDevice(motor_name, f"basic.{key}")
    if value is None:
        return default
    return config_cls._safe_float(value, default)


def _type_e_height_from_motor_position(config_cls, motor_position):
    link1 = config_cls.type_e_link1
    span = config_cls.type_e_link1 + config_cls.type_e_link2
    horizontal = config_cls.type_e_joint_middle_max - max(0.0, motor_position)
    horizontal = clamp(
        horizontal,
        config_cls.type_e_joint_middle_min,
        config_cls.type_e_joint_middle_max,
    )
    ratio = clamp(horizontal / link1, -1.0, 1.0)
    height = span * math.sqrt(max(0.0, 1.0 - ratio * ratio))
    height += config_cls.type_e_joint_bottom + config_cls.type_e_joint_top
    return max(config_cls.type_e_zero_height, height)


def _type_e_config_reload(config_cls, cfg):
    value = config_cls._find_config_value
    number = config_cls._safe_float
    config_cls.type_e_lift_motor2 = getattr(config_cls, "type_e_model_lift_motor2", "")
    lift_motor_speeds = [
        _motor_float(config_cls, motor_name, "maxSpeed")
        for motor_name in (config_cls.fork_motor_name, config_cls.type_e_lift_motor2)
    ]
    lift_motor_speeds = [speed for speed in lift_motor_speeds if speed is not None and speed > 0]
    model_lift_velocity = min(lift_motor_speeds) if len(lift_motor_speeds) == 2 else 0.001
    configured_lift_velocity = number(value(["liftVelocity"], cfg), -1.0)
    config_cls.type_e_lift_velocity = (
        min(model_lift_velocity, configured_lift_velocity)
        if configured_lift_velocity > 0
        else model_lift_velocity
    )
    config_cls.type_e_zero_height = number(value(["liftZeroPosition"], cfg), 0.0)
    config_cls.type_e_slow_range = max(0.0, number(value(["liftMotorSlowRange"], cfg), 0.01))
    config_cls.type_e_actual_zero1 = number(value(["liftMotorActualZero1"], cfg), -0.005)
    config_cls.type_e_actual_zero2 = number(value(["liftMotorActualZero2"], cfg), -0.005)
    config_cls.type_e_zero_offset1 = number(value(["liftMotorActualZeroOffset1"], cfg), 0.0)
    config_cls.type_e_zero_offset2 = number(value(["liftMotorActualZeroOffset2"], cfg), 0.0)
    config_cls.type_e_sync_tolerance = max(0.0, number(value(["liftMotorSyncTolerance"], cfg), 0.008))
    config_cls.type_e_lift_timeout = max(0.1, number(value(["liftOperationTimeout"], cfg), 20.0))
    config_cls.type_e_calib_timeout = max(0.1, number(value(["motorCalibTimeout"], cfg), 30.0))
    config_cls.type_e_link1 = max(0.001, number(value(["link1Length"], cfg), 0.185))
    config_cls.type_e_link2 = max(0.0, number(value(["link2Length"], cfg), 0.05))
    config_cls.type_e_joint_bottom = number(value(["joint2Bottom"], cfg), 0.03)
    config_cls.type_e_joint_top = number(value(["joint2Top"], cfg), 0.05)
    config_cls.type_e_joint_middle_max = number(value(["joint2MiddleMaxDist"], cfg), 0.18497)
    config_cls.type_e_joint_middle_min = number(value(["joint2MiddleMinDist"], cfg), 0.052)
    config_cls.type_e_load_confirm_distance = max(0.0, number(value(["typeELoadConfirmDistance"], cfg), 0.15))
    config_cls.type_e_chassis_sync_speed = max(0.001, number(value(["typeEChassisSyncSpeed"], cfg), 0.05))
    config_cls.type_e_policy_delay = max(0.0, number(value(["typeEPolicyDelay"], cfg), 0.1))
    config_cls.type_e_back_laser_width = max(0.0, number(value(["typeEBackLaserWidth"], cfg), 0.3))
    config_cls.type_e_hook_align_speed = max(0.001, number(value(["typeEHookAlignSpeed"], cfg), 0.02))
    config_cls.type_e_hook_align_travel = max(0.0, number(value(["typeEHookAlignTravel"], cfg), 0.02))
    config_cls.type_e_hook_align_timeout = max(0.1, number(value(["typeEHookAlignTimeout"], cfg), 5.0))
    config_cls.type_e_hook_align_dis = _config_keys(value(["typeEHookAlignDi"], cfg))
    config_cls.type_e_hook_reconnect_speed = max(0.001, number(value(["typeEHookReconnectSpeed"], cfg), 0.07))
    config_cls.type_e_hook_reconnect_dis = _config_keys(value(["typeEHookReconnectDi"], cfg))
    config_cls.type_e_hook_reconnect_limit_margin = max(
        0.001, number(value(["typeEHookReconnectLimitMargin"], cfg), 0.01)
    )
    config_cls.type_e_unload_length = max(
        0.0, number(value(["stretchUnloadLength", "typeEUnloadLength"], cfg), 1.22)
    )
    config_cls.type_e_wire_position_tolerance = max(
        0.0, number(value(["stretchWirePositionTolerance", "typeEWirePositionTolerance"], cfg), 0.02)
    )
    wire_motor = value(["stretchWireMotor", "typeEReachWireMotor"], cfg)
    config_cls.type_e_wire_motor_name = str(wire_motor or "Motor-005").strip()

    lift_motor_max_positions = [
        _motor_float(config_cls, motor_name, "maxLength")
        for motor_name in (config_cls.fork_motor_name, config_cls.type_e_lift_motor2)
    ]
    lift_motor_max_positions = [position for position in lift_motor_max_positions if position is not None]
    config_cls.type_e_lift_model_valid = len(lift_motor_speeds) == 2 and len(lift_motor_max_positions) == 2
    config_cls.type_e_max_height = (
        _type_e_height_from_motor_position(config_cls, min(lift_motor_max_positions))
        if len(lift_motor_max_positions) == 2
        else config_cls.type_e_zero_height
    )

    if not config_cls.reach_motor_name:
        config_cls.reach_motor_name = getattr(config_cls, "type_e_model_reach_motor", "")
    config_cls.reach_motor_names = config_cls._split_motor_names(config_cls.reach_motor_name)
    model_reach_velocity = _motor_float(config_cls, config_cls.reach_motor_name, "maxSpeed")
    if model_reach_velocity is not None and model_reach_velocity > 0:
        config_cls.reachMotorMaxSpeed = min(config_cls.reachMotorMaxSpeed, model_reach_velocity)

    # 通用 Fork 接口使用货叉高度；Type E 电机实际使用剪叉连杆位移。
    # 这里把 Type E 的机构行程换算成通用接口可用的高度范围。
    config_cls.min_height = config_cls.type_e_zero_height
    config_cls.max_height = max(config_cls.min_height, config_cls.type_e_max_height)
    config_cls.fork_max_speed = config_cls.type_e_lift_velocity


class TypeELiftMotorByPosition(ReachAwareForkMotorByPosition):
    """将 Type E 的两个抬升电机作为一个剪叉升降轴同步控制。"""

    def __init__(self, motor_name, position, max_speed=None, action_name="RunMotor", stop_di="", min_safe_height=0.0):
        super().__init__(motor_name, position, max_speed, action_name, stop_di, min_safe_height)
        self.motor_names = [motor_name, ConfigParams.type_e_lift_motor2]
        self.target_motor_positions = []

    @staticmethod
    def _height_from_motor_position(motor_position):
        return _type_e_height_from_motor_position(ConfigParams, motor_position)

    @staticmethod
    def _motor_position_from_height(height):
        height = clamp(height, ConfigParams.min_height, ConfigParams.max_height)
        vertical = max(
            0.0,
            height - ConfigParams.type_e_joint_bottom - ConfigParams.type_e_joint_top,
        )
        span = ConfigParams.type_e_link1 + ConfigParams.type_e_link2
        ratio = clamp(vertical / span, 0.0, 1.0)
        horizontal = ConfigParams.type_e_link1 * math.sqrt(max(0.0, 1.0 - ratio * ratio))
        horizontal = clamp(
            horizontal,
            ConfigParams.type_e_joint_middle_min,
            ConfigParams.type_e_joint_middle_max,
        )
        return ConfigParams.type_e_joint_middle_max - horizontal

    def _current_position(self):
        positions = [Motor.getMotorPos(name) for name in self.motor_names]
        return sum(self._height_from_motor_position(pos) for pos in positions) / len(positions)

    def _start_motion(self):
        self.cur_fork_height = self._current_position()
        _fork_prepare_target_position(self)
        _fork_check_back_laser_collision(self)
        _fork_apply_loaded_speed_limit(self)

        target = self._motor_position_from_height(self.position)
        self.target_motor_positions = [target, target]
        # 电机模型的前移距离使用电机坐标表示。目标变化小于到位判定阈值时，
        # RBK 可能直接返回“已到位”，但机构实际上没有产生可见的抬升动作，
        # 因此这里至少补足一个有效步长。
        motor_positions = [Motor.getMotorPos(name) for name in self.motor_names]
        if self.delta > 0.0:
            min_step = max(0.0, ConfigParams.reach_up_dist) + 0.0001
        elif self.delta < 0.0:
            min_step = max(0.0, ConfigParams.reach_down_dist) + 0.0001
        else:
            min_step = 0.0
        if min_step > 0.0:
            self.target_motor_positions = [
                target if abs(target - current) >= min_step else current + (min_step if self.delta > 0 else -min_step)
                for current in motor_positions
            ]
        speed = self.max_speed
        if self.position <= ConfigParams.min_height + ConfigParams.type_e_slow_range:
            speed = max(0.001, speed / 5.0)
            self.target_motor_positions = [
                ConfigParams.type_e_actual_zero1 + ConfigParams.type_e_zero_offset1,
                ConfigParams.type_e_actual_zero2 + ConfigParams.type_e_zero_offset2,
            ]
        for name in self.motor_names:
            Motor.resetMotor(name)
        rejected_commands = []
        for name, motor_target in zip(self.motor_names, self.target_motor_positions):
            if not Motor.setMotorPosition(name, motor_target, speed, ""):
                rejected_commands.append({"motor": name, "target": motor_target})
        self._motor_reset_done = False
        if rejected_commands:
            self._reset_motor_once()
            Navigation.setTaskError(
                "TypeELiftCommandRejected",
                f"type E lift command rejected, speed:{speed}, commands:{rejected_commands}",
            )
            self.action_status = ActionStatus.FAILED
            return
        Trace.log(
            f"type E lift height:{self.position}, motor targets:{self.target_motor_positions}, speed:{speed}",
            name="fork.task",
        )

    def _reset_motor_once(self):
        if not self._motor_reset_done:
            for name in self.motor_names:
                if name:
                    Motor.resetMotor(name)
            self._motor_reset_done = True

    def _before_reach_check(self):
        super()._before_reach_check()
        motor_positions = [Motor.getMotorPos(name) for name in self.motor_names]
        if max(motor_positions) - min(motor_positions) > ConfigParams.type_e_sync_tolerance:
            self._reset_motor_once()
            Navigation.setTaskError(
                "TypeELiftMotorOutOfSync",
                f"type E lift motors out of sync, positions:{motor_positions}",
            )
            self.action_status = ActionStatus.FAILED
        elif time.time() - self.start_time > ConfigParams.type_e_lift_timeout:
            self._reset_motor_once()
            Navigation.setTaskError(
                "TypeELiftTimeout",
                f"type E lift timeout, target height:{self.position}, positions:{motor_positions}",
            )
            self.action_status = ActionStatus.FAILED

    def run(self, ctx=None):
        if self.action_status in (ActionStatus.FINISHED, ActionStatus.FAILED):
            self._reset_motor_once()
            return
        if not self.init:
            self.action_status = ActionStatus.RUNNING
            self.start_time = time.time()
            if (
                not all(self.motor_names)
                or len(set(self.motor_names)) != len(self.motor_names)
                or not ConfigParams.type_e_lift_model_valid
            ):
                Navigation.setTaskError(
                    "TypeELiftMotorConfigInvalid",
                    f"type E lift motor configuration is invalid: {self.motor_names}; "
                    "check maxSpeed and maxLength",
                )
                self.action_status = ActionStatus.FAILED
                self._reset_motor_once()
                return
            self.cur_fork_height = self._current_position()
            self.cur_fork_height_at_init = self.cur_fork_height
            self.init = True
            self._start_motion()
            self._after_start_motion()
        self.cur_fork_height = self._current_position()
        self._before_reach_check()
        if self.action_status == ActionStatus.FAILED:
            return
        reach_tolerance = max(ConfigParams.reach_up_dist, ConfigParams.reach_down_dist, 0.001) + 0.0001
        positions_reached = all(
            abs(Motor.getMotorPos(name) - target) <= reach_tolerance
            for name, target in zip(self.motor_names, self.target_motor_positions)
        )
        command_reached = all(Motor.isMotorReached(name) for name in self.motor_names)
        self.is_reach = positions_reached and command_reached
        if self.is_reach:
            self._after_reached()
            self.action_status = ActionStatus.FINISHED
            self._reset_motor_once()


class TypeEMotorCalibAction(ActionBase):
    """校准一组 Type E 电机，并等待本次校准产生的新完成反馈。"""

    def __init__(self, motor_names, action_name="typeEMotorCalib"):
        super().__init__(action_name)
        self.motor_names = list(dict.fromkeys(name for name in motor_names if name))
        self.started_at = 0.0
        self.command_at = 0.0
        self.command_sent = False
        self.calib_started = False

    @staticmethod
    def _motor_info_map():
        result = {}
        for info in Motor.getMotorInfos() or []:
            key = getattr(info, "key", None) or getattr(info, "motor_name", None)
            if key:
                result[str(key)] = info
        return result

    def _fail(self, error_key, message):
        Motor.stopMotor()
        Navigation.setTaskError(error_key, message)
        self.action_status = ActionStatus.FAILED

    def run(self, ctx=None):
        if self.action_status in (ActionStatus.FINISHED, ActionStatus.FAILED):
            return
        if not self.started_at:
            self.action_status = ActionStatus.RUNNING
            self.started_at = time.time()
            if not self.motor_names:
                self._fail("TypeEMotorCalibConfigInvalid", "type E calibration motor list is empty")
                return
            Navigation.stopRobotNow()
            Motor.stopMotor()
            return

        if time.time() - self.started_at > ConfigParams.type_e_calib_timeout:
            self._fail(
                "TypeEMotorCalibTimeout",
                f"type E motor calibration timed out: {self.motor_names}",
            )
            return

        info_map = self._motor_info_map()
        missing = [name for name in self.motor_names if name not in info_map]
        if missing:
            self._fail("TypeEMotorCalibInfoMissing", f"type E motor info is missing: {missing}")
            return

        infos = [info_map[name] for name in self.motor_names]
        if not self.command_sent:
            if (
                not NavStatus.getChassisStop()
                or not all(bool(getattr(info, "stop", False)) for info in infos)
            ):
                return
            self.calib_started = any(int(getattr(info, "calib", 0)) != 2 for info in infos)
            for name in self.motor_names:
                Motor.motorCalib(name)
            self.command_sent = True
            self.command_at = time.time()
            Trace.log(f"type E motor calibration started: {self.motor_names}", name="fork.motor")
            return

        if any(int(getattr(info, "calib", 0)) != 2 or not bool(getattr(info, "stop", False)) for info in infos):
            self.calib_started = True
            return

        # 不能把 motorCalib 下发前遗留的 calib=2 状态误认为本次校准已完成。
        if self.calib_started and time.time() - self.command_at >= 0.2:
            Trace.log(f"type E motor calibration finished: {self.motor_names}", name="fork.motor")
            self.action_status = ActionStatus.FINISHED

    def reset(self):
        self.action_status = ActionStatus.RUNNING
        self.started_at = 0.0
        self.command_at = 0.0
        self.command_sent = False
        self.calib_started = False

    def cancel(self):
        Motor.stopMotor()
        self.action_status = ActionStatus.FAILED

    def suspend(self):
        if self.action_status == ActionStatus.RUNNING:
            Motor.stopMotor()
        super().suspend()

    def resume(self):
        if self.action_status == ActionStatus.SUSPENDED:
            self.started_at = 0.0
            self.command_at = 0.0
            self.command_sent = False
            self.calib_started = False
        super().resume()


class TypeEChassisWithReachAction(ActionBase):
    """底盘运动与 Type E 前移机构同步执行的动作。

    取货时用于“货叉相对底盘保持位置、底盘后退”；放货时用于“底盘前进、
    前移机构同步伸出”。两者必须在同一个动作内完成，否则货叉可能相对底盘
    产生不受控的位移并与地面或栈板摩擦。
    """

    def __init__(
            self,
            distance,
            reach_target=None,
            contact_dis=None,
            check_contact=False,
            action_name="TypeEChassisWithReach",
            wire_target=None,
            wire_tolerance=None,
    ):
        super().__init__(action_name)
        self.distance = float(distance)
        self.requested_distance = float(distance)
        self.reach_target = reach_target
        self.contact_dis = list(contact_dis or [])
        self.check_contact = bool(check_contact)
        self.wire_target = None if wire_target is None else float(wire_target)
        self.wire_tolerance = (
            getattr(ConfigParams, "type_e_wire_position_tolerance", 0.02)
            if wire_tolerance is None else max(0.0, float(wire_tolerance))
        )
        self.wire_start_position = None
        self.wire_position = None
        self.wire_check_enabled = bool(
            self.wire_target is not None and getattr(ConfigParams, "type_e_wire_motor_name", "")
        )
        self.path_action = None
        self.reach_action = None
        self.policy_applied = False
        self.started_at = 0.0

    @staticmethod
    def _distance_sensor_collision_keys():
        # 没有绑定模型时不启用货叉尖端距离传感器，避免误修改现场的碰撞配置。
        return [key for key in (ConfigParams.fork_tip_distance_sensors or []) if key]

    def _apply_policy(self):
        collision_devices = str(RobotParam.getConfig(
            "navigation", "collisionDetection.detectionDevice"
        ) or "").split(",")
        collision_devices = [key.strip() for key in collision_devices if key.strip()]
        for sensor_key in self._distance_sensor_collision_keys():
            while sensor_key in collision_devices:
                collision_devices.remove(sensor_key)
        Navigation.appendCustomPolicy("typeEChassisSync", {
            "navigation.collisionDetection.detectionDevice": ",".join(collision_devices),
        })
        # 3.4 在货叉相对底盘静止、底盘从货物下方进退时，会暂时收窄 Type E
        # 后方激光的检测宽度；否则激光可能把栈板/货物当成底盘后方障碍物。
        for laser_key in getattr(ConfigParams, "type_e_back_lasers", []) or []:
            Laser.set2DLaserWidth(laser_key, ConfigParams.type_e_back_laser_width)
        self.policy_applied = True
        self.started_at = time.time()

    def _cleanup(self):
        if self.policy_applied:
            Laser.clear2DLaserWidth(getattr(ConfigParams, "type_e_back_lasers", []) or [])
            Navigation.clearPolicy()
            self.policy_applied = False

    def _fail(self, error_key, message):
        Navigation.stopRobotNow()
        if self.reach_action is not None:
            self.reach_action.cancel()
        Navigation.setTaskError(error_key, message)
        self.action_status = ActionStatus.FAILED
        self._cleanup()

    def _contact_reached(self):
        if not self.contact_dis:
            return False
        statuses = [bool(Di.getDi(di_key)) for di_key in self.contact_dis]
        return all(statuses)

    def _start_motion(self):
        if self.wire_check_enabled:
            try:
                wire_motor_name = getattr(ConfigParams, "type_e_wire_motor_name", "")
                self.wire_start_position = float(Motor.getMotorPos(wire_motor_name))
                # 与 3.4 一致：只补足尚未达到的前进距离。若 Motor-005 已经
                # 超过目标，3.4 会立即停止底盘而不是反向补走，避免放货时多走。
                # 距离只在动作启动时计算一次，路径完成后不重复规划同一段距离。
                self.distance = max(0.0, self.wire_target - self.wire_start_position)
                Trace.log(
                    f"type E unload wire sync start: motor={wire_motor_name}, "
                    f"start={self.wire_start_position:.4f}, target={self.wire_target:.4f}, "
                    f"chassis_distance={self.distance:.4f}",
                    name="fork.task",
                )
            except Exception as exc:  # noqa: BLE001
                self.wire_check_enabled = False
                Trace.log(
                    f"type E unload wire sync read failed, motor={wire_motor_name}, "
                    f"error={exc}",
                    name="fork.err",
                )
                self._fail(
                    "TypeEUnloadWirePositionMissing",
                    f"cannot read unload wire motor {wire_motor_name}: {exc}",
                )
                return
        path_args = {
            "x": self.distance,
            "y": 0.0,
            "theta": 0.0,
            "coordinate": "robot",
            "backMode": 1 if self.distance < 0 else 0,
            "maxSpeed": ConfigParams.type_e_chassis_sync_speed,
            "maxRot": math.radians(2),
            "reachAngle": math.pi,
            "reachDist": 0.003,
            "useOdo": 0,
        }
        self.path_action = GoPath(path_args)
        if self.reach_target is not None:
            if not ConfigParams.reach_motor_names:
                self._fail("TypeEReachMotorMissing", "type E reach motor is not configured")
                return
            self.reach_action = RunReachMotorsByPosition(
                ConfigParams.reach_motor_names,
                self.reach_target,
                ConfigParams.reachMotorMaxSpeed,
                ConfigParams.reachMotorSyncTolerance,
                action_name="typeESyncReachMotors",
            )

    def run(self, ctx=None):
        if self.action_status in (ActionStatus.FINISHED, ActionStatus.FAILED):
            return
        if not self.policy_applied:
            if self.check_contact and not self.contact_dis:
                self._fail("TypeEContactDiMissing", "type E load confirmation requires contact DI")
                return
            self.action_status = ActionStatus.RUNNING
            self._apply_policy()
            return
        if self.path_action is None:
            if time.time() - self.started_at < ConfigParams.type_e_policy_delay:
                return
            self._start_motion()
            if self.action_status == ActionStatus.FAILED:
                return

        self.path_action.run(ctx)
        if self.reach_action is not None and self.reach_action.action_status not in (ActionStatus.FINISHED, ActionStatus.FAILED):
            self.reach_action.run(ctx)
        if self.path_action.action_status == ActionStatus.FAILED:
            self._fail("TypeEChassisPathFailed", "type E chassis motion failed")
            return
        if self.reach_action is not None and self.reach_action.action_status == ActionStatus.FAILED:
            self._fail("TypeEReachSyncFailed", "type E reach motor failed during chassis synchronization")
            return
        if self.check_contact and self._contact_reached():
            Navigation.stopRobotNow()
            if self.reach_action is not None:
                self.reach_action.cancel()
            self.action_status = ActionStatus.FINISHED
            self._cleanup()
            return
        reach_finished = self.reach_action is None or self.reach_action.action_status == ActionStatus.FINISHED
        if self.path_action.action_status == ActionStatus.FINISHED and reach_finished:
            if self.check_contact:
                self._fail("TypeEContactDiNotTriggered", "type E load confirmation path completed without contact DI")
                return
            if self.wire_check_enabled:
                try:
                    wire_motor_name = getattr(ConfigParams, "type_e_wire_motor_name", "")
                    self.wire_position = float(Motor.getMotorPos(wire_motor_name))
                    Trace.log(
                        f"type E unload wire position before reconnect: "
                        f"motor={wire_motor_name}, position={self.wire_position:.4f}, "
                        f"target={self.wire_target:.4f}, "
                        f"start={self.wire_start_position:.4f}, "
                        f"actual_delta={self.wire_position - self.wire_start_position:.4f}, "
                        f"commanded_delta={self.distance:.4f}",
                        name="fork.task",
                    )
                    # 这里只记录同步结果；是否允许降叉由后续重连动作在 DI-009
                    # 成功后统一判断，避免底盘动作先结束就被当成放货完成。
                except Exception as exc:  # noqa: BLE001
                    Trace.log(f"type E unload wire position read failed before reconnect: {exc}", name="fork.err")
                    self._fail(
                        "TypeEUnloadWirePositionMissing",
                        f"cannot verify unload wire motor {wire_motor_name}: {exc}",
                    )
                    return
            self.action_status = ActionStatus.FINISHED
            self._cleanup()

    def reset(self):
        self.action_status = ActionStatus.RUNNING
        self.distance = self.requested_distance
        self.wire_start_position = None
        self.wire_position = None
        self.wire_check_enabled = bool(
            self.wire_target is not None and getattr(ConfigParams, "type_e_wire_motor_name", "")
        )
        self.path_action = None
        self.reach_action = None
        self.policy_applied = False
        self.started_at = 0.0

    def cancel(self):
        if self.path_action is not None:
            self.path_action.cancel()
        if self.reach_action is not None:
            self.reach_action.cancel()
        self._cleanup()
        self.action_status = ActionStatus.FAILED

    def suspend(self):
        if self.action_status != ActionStatus.RUNNING:
            return
        if self.path_action is not None:
            self.path_action.suspend()
        if self.reach_action is not None:
            self.reach_action.suspend()
        super().suspend()

    def resume(self):
        if self.action_status != ActionStatus.SUSPENDED:
            return
        if self.path_action is not None:
            self.path_action.resume()
        if self.reach_action is not None:
            self.reach_action.resume()
        super().resume()


class TypeEGoPathWithContactDi(GoPathWithContactDi):
    """Type E 分阶段接近动作：前移阶段触发接触 DI 时立即结束。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._reach_contact_latched = False
        self._align_path_started_at = None
        self._align_finish_deferred = False
        self._align_long_start = None

    @staticmethod
    def _normalize_angle(angle):
        return math.atan2(math.sin(angle), math.cos(angle))

    def _alignment_pose(self):
        # 识别结果通常在世界坐标系，先转换到当前底盘坐标系，再分别检查
        # 纵向距离、横向误差和航向角；三项都满足才允许进入前移阶段。
        offset = pos2Base(get_r_loc(), self.target_pos)
        long_target = self.reach_phase_config.get("align_long_target")
        long_tolerance = max(
            0.001,
            float(self.reach_phase_config.get(
                "align_long_tolerance",
                ConfigParams.readjustDistPrecision,
            )),
        )
        lateral_limit = max(0.0, float(ConfigParams.readjustDistPrecision))
        angle_limit = math.radians(max(0.0, float(ConfigParams.readjustAnglePrecision)))
        angle_error = abs(self._normalize_angle(float(offset[2])))
        if long_target is None:
            long_reached = offset[0] <= self.reach_align_long_thresh
        else:
            # Type E 的前移行程明显长于车体 tail。第一段贝塞尔应在
            # “栈板前方预留完整前移行程”的明确位置切段，不能沿用短行程
            # 车型的 offset <= tail，否则车体已经贴近栈板才开始伸叉。
            if self._align_long_start is None:
                self._align_long_start = float(offset[0])
            if self._align_long_start <= float(long_target):
                long_reached = offset[0] >= float(long_target) - long_tolerance
            else:
                long_reached = offset[0] <= float(long_target) + long_tolerance
        return (
            offset,
            long_reached
            and abs(offset[1]) <= lateral_limit
            and angle_error <= angle_limit,
            long_reached,
            long_target,
            long_tolerance,
            lateral_limit,
            angle_limit,
        )

    def _build_reach_phase_action(self):
        if not self.reach_motor_names:
            Navigation.setTaskError("ReachMotorMissing", "reach motor is not configured for staged pathFirst")
            self.action_status = ActionStatus.FAILED
            return None
        return RunReachMotorsByPosition(
            self.reach_motor_names,
            self.reach_target,
            self.reach_max_speed,
            self.reach_sync_tolerance,
            contact_di=self.contact_di if self.check_di else [],
            check_all_di=self.check_all_contact_di,
            action_name="extendReachMotors",
        )

    def _reach_contact_triggered(self):
        if not self.check_di or not self.contact_di:
            return False
        statuses = [bool(Di.getDi(di_id)) for di_id in self.contact_di]
        return all(statuses) if self.check_all_contact_di else any(statuses)

    def _advance_back_action(self):
        path_started_before = bool(getattr(self.back_action, "path_started", False))
        if (
                self.reach_phase_enabled
                and self.reach_phase == "align_path"
                and self._align_path_started_at is not None
                and time.monotonic() - self._align_path_started_at < ConfigParams.type_e_policy_delay
                and self.back_action.action_status == ActionStatus.FINISHED
        ):
            # 保护期内强制下一 tick 再读取一次新路径的到位状态。
            self.back_action.action_status = ActionStatus.RUNNING
        result = super()._advance_back_action()
        path_started_after = bool(getattr(self.back_action, "path_started", False))
        if (
                self.reach_phase_enabled
                and self.reach_phase == "align_path"
                and not path_started_before
                and path_started_after
        ):
            self._align_path_started_at = time.monotonic()
            if self.back_action.action_status == ActionStatus.FINISHED:
                self.back_action.action_status = ActionStatus.RUNNING
            Trace.log(
                "type E align path submitted, ignore same-tick reached state",
                name="fork.task",
            )
        if self.reach_phase == "reach" and self._reach_contact_triggered():
            self._reach_contact_latched = True
        return result

    def reset(self):
        super().reset()
        self._reach_contact_latched = False
        self._align_path_started_at = None
        self._align_finish_deferred = False
        self._align_long_start = None

    def _handle_motion_extensions(self):
        if (
                self.reach_phase_enabled
                and self.reach_phase == "reach"
                and self.reach_action is not None
                and self.reach_action.action_status == ActionStatus.FINISHED
                and (self._reach_contact_latched or self._reach_contact_triggered())
        ):
            Navigation.stopRobotNow()
            self.reach_phase = "contact_finished"
            self.action_status = ActionStatus.FINISHED
            Trace.log(
                "staged reach path contact DI triggered during reach, skip final goPath",
                name="fork.task",
            )
            return True
        if self.reach_phase_enabled and self.reach_phase == "align_path" and self.reach_align_use_geometry:
            pose = self._alignment_pose()
            offset, aligned, long_reached, long_target, long_tolerance, lateral_limit, angle_limit = pose
            if long_reached:
                if aligned:
                    Trace.log(
                        f"type E align position reached: offset={offset}, "
                        f"long_target={long_target}, long_tolerance={long_tolerance:.3f}m, "
                        f"lateral_limit={lateral_limit:.3f}m, "
                        f"angle_limit={math.degrees(angle_limit):.2f}deg",
                        name="fork.task",
                    )
                    self._transition_align_to_reach("longitudinal+lateral+angle thresholds")
                    return True
                # 已经过了纵向安全切段位置但横向或角度仍未收敛时必须立即停车，
                # 不能让贝塞尔继续沿末端直线穿过栈板后再报错。
                Navigation.stopRobotNow()
                Navigation.resetPath()
                Navigation.setTaskError(
                    "TypeEAlignmentNotConverged",
                    f"type E alignment unsafe at reach boundary: offset={offset}, "
                    f"long_target={long_target}, long_tolerance={long_tolerance:.3f}m, "
                    f"lateral_limit={lateral_limit:.3f}m, "
                    f"angle_limit={math.degrees(angle_limit):.2f}deg",
                )
                Trace.log(
                    f"type E alignment unsafe at reach boundary, stop before extending: "
                    f"offset={offset}, long_target={long_target}, "
                    f"long_tolerance={long_tolerance}, lateral_limit={lateral_limit}, "
                    f"angle_limit_deg={math.degrees(angle_limit)}",
                    name="fork.err",
                )
                self.action_status = ActionStatus.FAILED
                return True
            if self.back_action.action_status == ActionStatus.FINISHED:
                Navigation.setTaskError(
                    "TypeEAlignmentNotConverged",
                    f"type E alignment incomplete before reach: offset={offset}, "
                    f"long_target={long_target}, long_tolerance={long_tolerance:.3f}m, "
                    f"lateral_limit={lateral_limit:.3f}m, "
                    f"angle_limit={math.degrees(angle_limit):.2f}deg",
                )
                Trace.log(
                    f"type E alignment incomplete, refuse reach: offset={offset}, "
                    f"long_target={long_target}, long_tolerance={long_tolerance}, "
                    f"lateral_limit={lateral_limit}, angle_limit_deg={math.degrees(angle_limit)}",
                    name="fork.err",
                )
                self.action_status = ActionStatus.FAILED
                return True
        if self.reach_phase_enabled and self.reach_phase == "align_path":
            if self.back_action.action_status == ActionStatus.FINISHED:
                # GoBezier 下发路径后同一 tick 读取到位状态时，可能读到上一条
                # 路径遗留的 True。等待现有策略延时后再切段，避免刚开始规划
                # 就提前伸叉；真实路径完成时只会多等待这一小段时间。
                if (
                        self._align_path_started_at is not None
                        and time.monotonic() - self._align_path_started_at < ConfigParams.type_e_policy_delay
                ):
                    if not self._align_finish_deferred:
                        Trace.log(
                            "type E defer align completion during path startup",
                            name="fork.task",
                        )
                        self._align_finish_deferred = True
                    return True
                self._transition_align_to_reach("align path finished")
                return True
        return super()._handle_motion_extensions()

    def _is_reach_aligned_by_geometry(self):
        if not self.reach_phase_enabled or self.reach_phase != "align_path":
            return False
        if not self.reach_align_use_geometry:
            return False
        offset, aligned, _, long_target, long_tolerance, lateral_limit, angle_limit = self._alignment_pose()
        if aligned:
            Trace.log(
                f"type E align position reached: offset={offset}, "
                f"long_target={long_target}, long_tolerance={long_tolerance:.3f}m, "
                f"lateral_limit={lateral_limit:.3f}m, "
                f"angle_limit={math.degrees(angle_limit):.2f}deg",
                name="fork.task",
            )
        return aligned


class TypeEHookAlignAndLowerAction(ActionBase):
    """使用挂钩对齐 DI 对齐前移机构，然后降叉。

    该动作主要作为未进入 Type E 专用卸货路径时的兼容兜底；标准卸货路径
    使用 TypeEHookReconnectAndLowerAction 执行双向重连扫描。
    """

    def __init__(self, lower_height):
        super().__init__("typeEHookAlignAndLower")
        self.lower_height = lower_height
        self.reach_action = None
        self.lower_action = None
        self.started_at = 0.0

    @staticmethod
    def _hooks_aligned():
        return bool(ConfigParams.type_e_hook_align_dis) and all(
            bool(Di.getDi(di_key)) for di_key in ConfigParams.type_e_hook_align_dis
        )

    @staticmethod
    def _hook_align_target():
        targets = []
        for motor_name in ConfigParams.reach_motor_names:
            min_length, max_length = ConfigParams._get_motor_limits(motor_name)
            targets.append(clamp(max_length, min_length, max_length))
        return targets

    def _fail(self, error_key, message):
        if self.reach_action is not None:
            self.reach_action.cancel()
        Navigation.setTaskError(error_key, message)
        self.action_status = ActionStatus.FAILED

    def run(self, ctx=None):
        if self.action_status in (ActionStatus.FINISHED, ActionStatus.FAILED):
            return
        self.action_status = ActionStatus.RUNNING
        if not ConfigParams.type_e_hook_align_dis:
            self._fail("TypeEHookAlignDiMissing", "type E hook alignment DI is not configured")
            return
        if not ConfigParams.reach_motor_names:
            self._fail("TypeEReachMotorMissing", "type E reach motor is not configured for hook alignment")
            return
        if self.reach_action is None:
            self.started_at = time.time()
            self.reach_action = RunReachMotorsByPosition(
                ConfigParams.reach_motor_names,
                self._hook_align_target(),
                ConfigParams.type_e_hook_align_speed,
                ConfigParams.reachMotorSyncTolerance,
                contact_di=ConfigParams.type_e_hook_align_dis,
                check_all_di=True,
                action_name="typeEHookAlign",
            )
        if self.lower_action is None:
            if time.time() - self.started_at > ConfigParams.type_e_hook_align_timeout:
                self._fail("TypeEHookAlignTimeout", "type E hook alignment timed out")
                return
            if self.reach_action.action_status not in (ActionStatus.FINISHED, ActionStatus.FAILED):
                self.reach_action.run(ctx)
            if self.reach_action.action_status == ActionStatus.FAILED:
                self._fail("TypeEHookAlignFailed", "type E hook alignment motor action failed")
                return
            if self.reach_action.action_status != ActionStatus.FINISHED:
                return
            if not self._hooks_aligned():
                self._fail("TypeEHookNotAligned", "hook alignment DI was not triggered before reach limit")
                return
            self.lower_action = TypeELiftMotorByPosition(
                ConfigParams.fork_motor_name,
                self.lower_height,
                ConfigParams.downMaxSpeedWithGoods,
                "downFork",
            )
        self.lower_action.run(ctx)
        if self.lower_action.action_status == ActionStatus.FAILED:
            self._fail("TypeEUnloadLowerFailed", "type E fork failed while lowering after hook alignment")
        elif self.lower_action.action_status == ActionStatus.FINISHED:
            self.action_status = ActionStatus.FINISHED

    def reset(self):
        self.action_status = ActionStatus.RUNNING
        self.reach_action = None
        self.lower_action = None
        self.started_at = 0.0

    def cancel(self):
        if self.reach_action is not None:
            self.reach_action.cancel()
        if self.lower_action is not None:
            self.lower_action.cancel()
        self.action_status = ActionStatus.FAILED

    def suspend(self):
        if self.action_status != ActionStatus.RUNNING:
            return
        if self.reach_action is not None:
            self.reach_action.suspend()
        if self.lower_action is not None:
            self.lower_action.suspend()
        super().suspend()

    def resume(self):
        if self.action_status != ActionStatus.SUSPENDED:
            return
        if self.reach_action is not None:
            self.reach_action.resume()
        if self.lower_action is not None:
            self.lower_action.resume()
        super().resume()


class TypeEReconnectReachAction(RunReachMotorsByPosition):
    """带重连 DI 锁存的前移扫描动作。

    RunReachMotorsByPosition 在 DI 触发后会先复位电机，再把动作置为完成。
    某些现场 DI 是瞬时信号，父动作随后再次读取时可能已经变为 False，导致
    已经完成的重连被误判为未触发。这里在复位电机前锁存触发结果，仅供 Type E
    重连流程使用，不改变其他车型的通用动作行为。
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.contact_triggered = False

    def _latch_contact_di(self):
        if self._contact_di_triggered():
            self.contact_triggered = True

    def _start_all(self):
        # 3.4 会把 stretchConnectDI 直接交给电机层作为停止 DI。仅靠 Python
        # 每 tick 轮询可能漏掉较窄的接近开关脉冲，因此 Type E 重连在只有一个
        # DI 时也把它随运动命令下发；多 DI 场景仍退回父类的脚本轮询逻辑。
        if len(self.contact_di) != 1:
            return super()._start_all()
        stop_di = self.contact_di[0]
        self.position_motor_names = []
        self.position_targets_reached = True
        for motor_name, target in zip(self.motor_names, self.target_positions):
            current = Motor.getMotorPos(motor_name)
            if abs(target - current) <= 0.005:
                continue
            self.position_targets_reached = False
            Motor.resetMotor(motor_name)
            if is_do_motor_key(motor_name):
                speed = self.max_speed if target > current else -self.max_speed
                Motor.setMotorSpeed(motor_name, speed, stop_di)
                continue
            if not Motor.setMotorPosition(motor_name, target, self.max_speed, stop_di):
                self._stop_all()
                Navigation.setTaskError(
                    "ReachMotorCommandRejected",
                    f"reach motor command rejected: motor:{motor_name}, target:{target}",
                )
                self.action_status = ActionStatus.FAILED
                return False
            self.position_motor_names.append(motor_name)
        Trace.log(
            f"reach motors:{self.motor_names}, targets:{self.target_positions}, "
            f"speed:{self.max_speed}, stop_di:{stop_di}",
            name="fork.task",
        )
        return True

    def _stop_all(self):
        # 父类会在这里复位电机；必须先读取 DI，避免瞬时触发丢失。
        self._latch_contact_di()
        super()._stop_all()

    def run(self, ctx=None):
        self._latch_contact_di()
        super().run(ctx)
        self._latch_contact_di()
        if (
                self.action_status == ActionStatus.FINISHED
                and not self.contact_triggered
                and len(self.contact_di) == 1
                and self.position_motor_names
        ):
            positions = [float(Motor.getMotorPos(name)) for name in self.motor_names]
            early_stop_tolerance = max(
                0.005,
                float(ConfigParams.reach_up_dist),
                float(ConfigParams.reach_down_dist),
            )
            # 底层停止 DI 可能是很短的脉冲，Python 再读取时已经恢复。若本轮
            # 位置命令在明显未到目标处报告完成，可判定为停止 DI 已在电机层触发。
            if any(
                    abs(position - target) > early_stop_tolerance
                    for position, target in zip(positions, self.target_positions)
            ):
                self.contact_triggered = True
                Trace.log(
                    f"type E hook reconnect inferred from motor stop DI: "
                    f"positions={positions}, targets={self.target_positions}, "
                    f"stop_di={self.contact_di[0]}",
                    name="fork.task",
                )

    def _trace_state(self):
        state = super()._trace_state()
        state["contact_triggered"] = self.contact_triggered
        return state

    def reset(self):
        super().reset()
        self.contact_triggered = False

    def cancel(self):
        super().cancel()


class TypeEHookReconnectAction(ActionBase):
    """按 3.4 流程在前移机构两端寻找挂钩重连点。

    扫描顺序为“接近最大行程 -> 接近最小行程”。目标点距离机械限位保留
    ``typeEHookReconnectLimitMargin``，不直接撞击或触发上下限位 DI；只有在
    两个方向都没有触发重连 DI 时才判定重连失败。
    """

    def __init__(self):
        super().__init__("typeEHookReconnect")
        self.phase = "extend"
        self.reach_action = None

    @staticmethod
    def _hook_reconnected():
        return bool(ConfigParams.type_e_hook_reconnect_dis) and any(
            bool(Di.getDi(di_key)) for di_key in ConfigParams.type_e_hook_reconnect_dis
        )

    def _fail(self, error_key, message):
        self._trace_scan_state(f"failure:{error_key}")
        if self.reach_action is not None:
            self.reach_action.cancel()
        Navigation.setTaskError(error_key, message)
        self.action_status = ActionStatus.FAILED

    def _trace_scan_state(self, reason):
        positions = []
        for motor_name in ConfigParams.reach_motor_names:
            try:
                positions.append({"motor": motor_name, "position": Motor.getMotorPos(motor_name)})
            except Exception as exc:  # noqa: BLE001
                positions.append({"motor": motor_name, "position_error": str(exc)})
        di_status = []
        for di_id in ConfigParams.type_e_hook_reconnect_dis:
            try:
                di_status.append({"di": di_id, "active": bool(Di.getDi(di_id))})
            except Exception as exc:  # noqa: BLE001
                di_status.append({"di": di_id, "read_error": str(exc)})
        reach_state = getattr(self.reach_action, "_trace_state", None)
        reach_state = reach_state() if callable(reach_state) else {}
        Trace.log(
            f"type E hook reconnect scan state: reason={reason}, phase={self.phase}, "
            f"motor_positions={positions}, reconnect_di={di_status}, reach_state={reach_state}",
            name="fork.err",
        )

    def _build_scan_action(self, target):
        # 不向电机下发字面量 max/min，避免触发 Motor-004 的硬限位 DI。
        # 每个电机按自己的行程计算安全目标，兼容多电机行程不完全一致的情况。
        motor_target = self._safe_target_positions(target)
        Trace.log(
            f"type E hook reconnect {target} safe target:{motor_target}, "
            f"limit margin:{ConfigParams.type_e_hook_reconnect_limit_margin:.3f}m",
            name="fork.task",
        )
        return TypeEReconnectReachAction(
            ConfigParams.reach_motor_names,
            motor_target,
            ConfigParams.type_e_hook_reconnect_speed,
            ConfigParams.reachMotorSyncTolerance,
            contact_di=ConfigParams.type_e_hook_reconnect_dis,
            check_all_di=False,
            action_name=f"typeEHookReconnect{target.title()}",
        )

    @staticmethod
    def _safe_target_positions(target):
        """根据扫描方向计算距离机械上下限的安全目标位置。"""
        motor_target = []
        for motor_name in ConfigParams.reach_motor_names:
            min_length, max_length = ConfigParams._get_motor_limits(motor_name)
            margin = ConfigParams.type_e_hook_reconnect_limit_margin
            if target == "extend":
                motor_target.append(clamp(max_length - margin, min_length, max_length))
            else:
                motor_target.append(clamp(min_length + margin, min_length, max_length))
        return motor_target

    def run(self, ctx=None):
        if self.action_status in (ActionStatus.FINISHED, ActionStatus.FAILED):
            return
        self.action_status = ActionStatus.RUNNING
        if not ConfigParams.type_e_hook_reconnect_dis:
            self._fail("TypeEHookReconnectDiMissing", "type E hook reconnect DI is not configured")
            return
        if not ConfigParams.reach_motor_names:
            self._fail("TypeEReachMotorMissing", "type E reach motor is not configured for hook reconnect")
            return
        if self.reach_action is None:
            self.reach_action = self._build_scan_action(self.phase)
        if self.reach_action.action_status not in (ActionStatus.FINISHED, ActionStatus.FAILED):
            self.reach_action.run(ctx)
        if self.reach_action.action_status == ActionStatus.FAILED:
            self._fail("TypeEHookReconnectFailed", f"type E hook reconnect {self.phase} scan failed")
            return
        if self.reach_action.action_status != ActionStatus.FINISHED:
            return
        self._trace_scan_state(f"scan_finished:{self.phase}")
        if self._hook_reconnected() or getattr(self.reach_action, "contact_triggered", False):
            Trace.log(
                f"type E hook reconnect DI latched, phase={self.phase}",
                name="fork.task",
            )
            self.action_status = ActionStatus.FINISHED
            return
        if self.phase == "extend":
            # 最大端未找到挂钩时，必须完整扫描到最小安全位置；不能只在当前
            # 位置再次判断 DI，否则会漏掉挂钩在回程方向才能接上的情况。
            self.phase = "retract"
            self.reach_action = self._build_scan_action(self.phase)
            return
        self._fail("TypeEHookReconnectNotFound", "type E hook reconnect DI was not triggered at either reach limit")

    def reset(self):
        self.action_status = ActionStatus.RUNNING
        self.phase = "extend"
        self.reach_action = None

    def cancel(self):
        if self.reach_action is not None:
            self.reach_action.cancel()
        self.action_status = ActionStatus.FAILED

    def suspend(self):
        if self.action_status == ActionStatus.RUNNING and self.reach_action is not None:
            self.reach_action.suspend()
        super().suspend()

    def resume(self):
        if self.action_status == ActionStatus.SUSPENDED and self.reach_action is not None:
            self.reach_action.resume()
        super().resume()


class TypeEHookReconnectAndLowerAction(ActionBase):
    """放货释放动作：先完成挂钩重连扫描，再把货叉降到目标高度。

    该类不再额外驱动底盘后退或执行单向重连 nudge；底盘前进/回退由前一个
    同步动作完成。当前测试阶段重连成功后直接降叉，暂不执行
    typeEUnloadEnsureReach 兜底伸出。
    """

    def __init__(self, lower_height):
        super().__init__("typeEHookReconnectAndLower")
        self.lower_height = lower_height
        self.reconnect_action = TypeEHookReconnectAction()
        self.ensure_extend_action = None
        self.lower_action = None

    @staticmethod
    def _check_unload_wire_position():
        """重连成功后校验 Motor-005，识别打滑、定位漂移或货叉卡住。"""
        motor_name = getattr(ConfigParams, "type_e_wire_motor_name", "")
        target = getattr(ConfigParams, "type_e_unload_length", None)
        tolerance = getattr(ConfigParams, "type_e_wire_position_tolerance", 0.02)
        if not motor_name or target is None:
            return True
        try:
            position = float(Motor.getMotorPos(motor_name))
        except Exception as exc:  # noqa: BLE001
            Navigation.setTaskError(
                "TypeEUnloadWirePositionMissing",
                f"cannot verify unload wire motor {motor_name}: {exc}",
            )
            return False
        error = abs(position - float(target))
        Trace.log(
            f"type E unload wire position after reconnect: motor={motor_name}, "
            f"position={position:.4f}, target={float(target):.4f}, "
            f"error={error:.4f}, tolerance={float(tolerance):.4f}",
            name="fork.task",
        )
        if error > float(tolerance):
            Navigation.setTaskError(
                "TypeEUnloadWirePositionAbnormal",
                f"type E unload wire position {position:.4f} differs from "
                f"target {float(target):.4f} by {error:.4f}m",
            )
            return False
        return True

    @staticmethod
    def _trace_positions_before_lower():
        """记录重连完成、降叉开始前两个相关电机的实际反馈位置。"""
        positions = {}
        for motor_name in ("Motor-004", "Motor-005"):
            try:
                positions[motor_name] = Motor.getMotorPos(motor_name)
            except Exception as exc:  # noqa: BLE001
                # Motor-005 可能未绑定或暂时没有状态，日志失败不能影响放货动作。
                positions[motor_name] = f"read_error:{exc}"
        Trace.log(
            "type E unload before lower motor positions: "
            f"Motor-004={positions['Motor-004']}, Motor-005={positions['Motor-005']}",
            output_console=True,
            output_time=True,
            name="fork.task",
        )

    def run(self, ctx=None):
        if self.action_status in (ActionStatus.FINISHED, ActionStatus.FAILED):
            return
        self.action_status = ActionStatus.RUNNING
        # 重连必须先完成。货叉仍处于抬升状态时不能直接降叉，否则挂钩可能
        # 处于脱钩状态，导致货叉或栈板受力异常。
        self.reconnect_action.run(ctx)
        if self.reconnect_action.action_status == ActionStatus.FAILED:
            self.action_status = ActionStatus.FAILED
            return
        if self.reconnect_action.action_status != ActionStatus.FINISHED:
            return
        if self.lower_action is None and not self._check_unload_wire_position():
            self.action_status = ActionStatus.FAILED
            return
        # 临时停用重连后的 typeEUnloadEnsureReach 兜底动作，先验证“重连后直接降叉”。
        # 保留 ensure_extend_action 字段及取消/挂起处理，后续确认机械状态后可恢复。
        if self.lower_action is None:
            Trace.log(
                "type E unload ensure reach disabled, lower directly after hook reconnect",
                name="fork.task",
            )
            self._trace_positions_before_lower()
            self.lower_action = TypeELiftMotorByPosition(
                ConfigParams.fork_motor_name,
                self.lower_height,
                ConfigParams.downMaxSpeedWithGoods,
                "downFork",
            )
        if self.lower_action.action_status not in (ActionStatus.FINISHED, ActionStatus.FAILED):
            self.lower_action.run(ctx)
        if self.lower_action.action_status == ActionStatus.FAILED:
            Navigation.setTaskError("TypeEUnloadLowerFailed", "type E fork failed after hook reconnect")
            self.action_status = ActionStatus.FAILED
            return
        if self.lower_action.action_status != ActionStatus.FINISHED:
            return
        Trace.log("type E unload fork lowered after hook reconnect", name="fork.task")
        self.action_status = ActionStatus.FINISHED

    def reset(self):
        self.reconnect_action.reset()
        self.ensure_extend_action = None
        self.lower_action = None
        self.action_status = ActionStatus.RUNNING

    def cancel(self):
        self.reconnect_action.cancel()
        if self.ensure_extend_action is not None:
            self.ensure_extend_action.cancel()
        if self.lower_action is not None:
            self.lower_action.cancel()
        self.action_status = ActionStatus.FAILED

    def suspend(self):
        if self.action_status != ActionStatus.RUNNING:
            return
        self.reconnect_action.suspend()
        if self.ensure_extend_action is not None:
            self.ensure_extend_action.suspend()
        if self.lower_action is not None:
            self.lower_action.suspend()
        super().suspend()

    def resume(self):
        if self.action_status != ActionStatus.SUSPENDED:
            return
        self.reconnect_action.resume()
        if self.ensure_extend_action is not None:
            self.ensure_extend_action.resume()
        if self.lower_action is not None:
            self.lower_action.resume()
        super().resume()


class RobotTypeE(ReachFork):
    fork_motor_action_class = TypeELiftMotorByPosition
    # Type E 取货和放货必须明确限制货叉运动方向。若未传 endHeight，通用流程
    # 默认可能使用 0.2m；对于上限约 0.289m 的机构，这个默认值存在越界风险。
    type_e_default_height_margin = 0.01
    config_builder_hook = staticmethod(_type_e_config_builder)
    config_reload_hook = staticmethod(_type_e_config_reload)

    @staticmethod
    def extend_custom_operation_inputs(_input_cls, builder, _min_height, _max_height):
        with builder.CHILD(key="zero", name=_TR("Type E Zero"),
                           desc=_TR("Move the Type E lift and reach mechanisms to their configured zero positions")):
            builder.TYPE(ParamType.ARRAY)

    @classmethod
    def custom_action_templates(cls):
        return [
            {"action_name": _TR("Type E Zero"), "operation": "zero"},
        ]

    def custom_operations(self):
        return {
            "zero": self.type_e_zero,
        }

    def _init_extra_args(self):
        super()._init_extra_args()
        self._type_e_unload_reconnect_before_lower = False
        if self.opt not in ("load", "unload"):
            return

        if "endHeight" not in self.task_args:
            self.end_height = (
                clamp(
                    ConfigParams.max_height - self.type_e_default_height_margin,
                    ConfigParams.min_height,
                    ConfigParams.max_height,
                )
                if self.opt == "load"
                else ConfigParams.min_height
            )

        valid_direction = (
            self.end_height > self.start_height
            if self.opt == "load"
            else self.end_height < self.start_height
        )
        if not valid_direction:
            Navigation.setTaskError(
                "TypeEHeightDirectionInvalid",
                f"type E {self.opt} requires endHeight {'>' if self.opt == 'load' else '<'} "
                f"startHeight, start:{self.start_height}, end:{self.end_height}",
            )
            self.set_status(ScriptStatus.FAILED)

    def _build_type_e_zero_actions(self):
        """先校准 Type E 电机编码器，再执行货叉和前移机构的机械回零。"""
        lift_motor_names = [ConfigParams.fork_motor_name, ConfigParams.type_e_lift_motor2]
        actions = [
            TypeEMotorCalibAction(lift_motor_names, "typeEZeroLiftCalib"),
        ]
        if ConfigParams.reach_motor_names:
            actions.append(TypeEMotorCalibAction(
                ConfigParams.reach_motor_names,
                "typeEZeroReachCalib",
            ))
        actions.append(
            TypeELiftMotorByPosition(
                ConfigParams.fork_motor_name,
                ConfigParams.min_height,
                ConfigParams.fork_max_speed,
                "typeEZeroLift",
            )
        )
        if ConfigParams.reach_motor_names:
            actions.append(self._build_reach_action("min", action_name="typeEZeroReach"))
        return actions

    def type_e_zero(self):
        if Container.hasGoods("0"):
            Navigation.setTaskError("ForkHasGoods", "fork has goods, cannot zero")
            self.set_status(ScriptStatus.FAILED)
            return
        yield self._build_type_e_zero_actions()

    def _build_type_e_load_confirm_action(self):
        return TypeEChassisWithReachAction(
            -ConfigParams.type_e_load_confirm_distance,
            contact_dis=ConfigParams.contact_ids if self.check_di else [],
            check_contact=self.check_di,
            action_name="typeELoadConfirm",
        )

    def _build_load_entry_batch(self, rec_action):
        return Fork._build_load_entry_batch(self, rec_action)

    def _build_path_first_load_actions(self, rec_world_pos, method, args):
        """构造 pathFirst 取货路径，并在前移货叉前停到配置的纵向预对齐位置。"""
        reach_distance = self._reach_extension_distance()
        # Type E 的前移机构是第二阶段的进叉动作，不能把它的最大行程叠加到
        # 第一段贝塞尔距离中。minAheadDist 是贝塞尔完成横向/角度对齐的前置点；
        # 同时不允许该点比车体 tail 更靠近栈板，避免零位货叉先碰到栈板。
        align_distance = max(float(ConfigParams.minAheadDist), float(ConfigParams.tail))
        if method == "goPath":
            # 与 GoBezier 的 target + min_ahead_dist 保持同一几何方向。
            align_world_pos = pos2World([align_distance, 0.0, 0.0], rec_world_pos)
            align_method = "goPath"
            align_args = {}
        else:
            robot_in_target = pos2Base(get_r_loc(), rec_world_pos)
            if robot_in_target[0] < align_distance:
                # 与 3.4 adjustGo 的“调整距离不足先前移”一致。机器人已经比
                # 安全预对齐位更靠近栈板时，强行生成贝塞尔会先折返再穿过栈板，
                # 曲率也会异常增大；此时直接走到明确的预对齐位更安全。
                align_world_pos = pos2World([align_distance, 0.0, 0.0], rec_world_pos)
                align_method = "goPath"
                align_args = {}
                Trace.log(
                    f"type E align space insufficient for {method}, use explicit pre-align goPath: "
                    f"robot_in_target={robot_in_target}, align_distance={align_distance:.3f}",
                    name="fork.task",
                )
            else:
                align_world_pos = rec_world_pos
                align_method = method
                align_args = dict(args or {})
                # 保留识别文件的 back_dist：它只定义贝塞尔后的直线段终点。
                # Type E 会在 minAheadDist 前置对齐点切换到 Motor-004，因此不能
                # 用前移电机行程覆盖 back_dist，也不能把曲线终点推到 2m 之外。
                align_args["min_ahead_dist"] = align_distance
        final_target = pos2World(
            [reach_distance - float(self.back_dist), 0.0, 0.0],
            rec_world_pos,
        )
        return [
            TypeEGoPathWithContactDi(
                ConfigParams.contact_ids,
                align_world_pos,
                ConfigParams.loadObsStopDist,
                align_method,
                align_args,
                self.check_di,
                "load",
                reach_phase_config={
                    "align_world_pos": align_world_pos,
                    "align_method": align_method,
                    "align_args": align_args,
                    # 第一段在 target + minAheadDist 结束，之后才由 Motor-004
                    # 完成进叉。使用明确纵向目标和穿越判断，防止控制周期跨过
                    # 容差窗口后继续沿直线顶向栈板。
                    "align_long_thresh": align_distance,
                    "align_long_target": align_distance,
                    "align_long_tolerance": ConfigParams.readjustDistPrecision,
                    "align_use_geometry": align_method != "goPath",
                    "final_world_pos": final_target,
                    "final_back_mode": 1,
                    "motor_names": ConfigParams.reach_motor_names,
                    "target": "max",
                    "max_speed": ConfigParams.reachMotorMaxSpeed,
                    "sync_tolerance": ConfigParams.reachMotorSyncTolerance,
                },
            ),
        ]

    def _build_load_approach_batch(self, rec_action, rec_world_pos, method, args):
        # 复用 ReachFork 的识别结果和任务编排；Type E 专用的 pathFirst 动作会
        # 先让底盘到 minAheadDist 前置对齐点，再允许 Motor-004 朝栈板伸出。
        if not ConfigParams.reach_motor_names:
            return ReachFork._build_load_approach_batch(self, rec_action, rec_world_pos, method, args)
        # 前移过程中保持货物接触 DI 有效；DI 触发后立即停止，并跳过最后一段
        # goPath，避免已经进叉后底盘再次调整位姿。
        return list(ReachFork._build_load_approach_batch(
            self, rec_action, rec_world_pos, method, args
        ))

    def _build_load_no_rec_approach_batch(self, target_pos, tcp_name):
        if not ConfigParams.reach_motor_names:
            return ReachFork._build_load_no_rec_approach_batch(self, target_pos, tcp_name)
        actions = list(ReachFork._build_load_no_rec_approach_batch(self, target_pos, tcp_name))
        path_action = actions.pop()
        resolved_target = getattr(path_action, "target_pos", None) or target_pos
        if ConfigParams.adjustMethod == "pathFirst":
            reach_distance = self._reach_extension_distance()
            front_dist = ConfigParams.minAheadDist + reach_distance
            front_target = pos2World(
                [-front_dist, 0.0, 0.0],
                resolved_target,
            )
            actions.append(TypeEGoPathWithContactDi(
                ConfigParams.contact_ids,
                front_target,
                ConfigParams.loadObsStopDist,
                "goPath",
                {},
                self.check_di,
                "load",
                reach_phase_config={
                    "align_world_pos": front_target,
                    "align_method": "goPath",
                    "align_args": {},
                    # 与识别取货相同：tail 用作实际纵向对齐阈值，避免
                    # 把“贝塞尔预留总行程”误当成提前切段距离。
                    "align_long_thresh": ConfigParams.tail,
                    "align_use_geometry": False,
                    "final_world_pos": self._shift_path_target_for_reach(resolved_target),
                    "final_back_mode": 1,
                    "motor_names": ConfigParams.reach_motor_names,
                    "target": "max",
                    "max_speed": ConfigParams.reachMotorMaxSpeed,
                    "sync_tolerance": ConfigParams.reachMotorSyncTolerance,
                },
            ))
            return actions
        actions.extend([
            self._build_reach_action("max", action_name="extendReachMotors"),
            GoPathWithContactDi(
                ConfigParams.contact_ids,
                self._shift_path_target_for_reach(resolved_target),
                ConfigParams.loadObsStopDist,
                "goPath",
                {},
                self.check_di,
                "load",
            ),
        ])
        return actions

    def _build_post_load_actions(self):
        if not ConfigParams.reach_motor_names:
            return []
        # 抬叉后栈板随货叉保持不动，底盘先后退并收回前移机构；对齐 3.4：
        # 底盘回到货叉位置后先执行重连扫描，再降叉到 0。
        return [
            TypeEChassisWithReachAction(
                -self._reach_extension_distance(),
                reach_target="min",
                action_name="typeELoadChassisBack",
            ),
            TypeEHookReconnectAction(),
            TypeELiftMotorByPosition(
                ConfigParams.fork_motor_name,
                ConfigParams.min_height,
                ConfigParams.fork_max_speed,
                "typeELoadLowerToZero",
            ),
        ]

    def _build_leave_loc_followup_actions(self, allow_same_path_return=False):
        # Type E 在这里已经完成 Motor-004 回收、降叉和挂钩重连。
        # 离开库位时只执行回程并遵守显式 leaveLocHeight，不能再套用 ReachFork
        # 的额外抬叉/回收流程，否则可能重复动作并把机构推到上限。
        return Fork._build_leave_loc_followup_actions(
            self,
            allow_same_path_return=(
                allow_same_path_return and ConfigParams.adjustMethod != "pathFirst"
            ),
        )

    def _build_unload_approach_batch(self, rec_action, rec_world_pos, method, args):
        if not ConfigParams.reach_motor_names:
            return super()._build_unload_approach_batch(rec_action, rec_world_pos, method, args)
        self._type_e_unload_reconnect_before_lower = True
        # 先到放货预对齐位置；最终放置由底盘前进完成，前移货叉保持在预定位置。
        actions = [
            GoPathWithContactDi(
                ConfigParams.contact_ids,
                self._shift_path_target_for_reach(rec_world_pos),
                None,
                "goPath",
                {},
                False,
                "unload",
            ),
            self._build_unload_prepare_lift_action(self.start_height),
            TypeEChassisWithReachAction(
                self._reach_extension_distance(),
                # 对齐行程不再截断前移；先走到距离机械限位的安全最大位，
                # 再由 TypeEHookReconnectAction 做双向重连扫描。
                reach_target=self._type_e_hook_reconnect_max_target(),
                wire_target=getattr(ConfigParams, "type_e_unload_length", 1.22),
                action_name="typeEUnloadChassisForward",
            ),
        ]
        return actions

    def _build_unload_target_approach(self, target_pos, tcp_name):
        if not ConfigParams.reach_motor_names:
            return super()._build_unload_target_approach(target_pos, tcp_name)
        self._type_e_unload_reconnect_before_lower = True
        resolved_target = self._shift_path_target_for_reach(target_pos)
        actions = [
            GoPathWithContactDi(
                ConfigParams.contact_ids,
                resolved_target,
                None,
                "goPath",
                {},
                False,
                "unload",
            ),
            self._build_unload_prepare_lift_action(self.start_height),
            TypeEChassisWithReachAction(
                self._reach_extension_distance(),
                reach_target=self._type_e_hook_reconnect_max_target(),
                wire_target=getattr(ConfigParams, "type_e_unload_length", 1.22),
                action_name="typeEUnloadChassisForward",
            ),
        ]
        return actions, bool(tcp_name)

    def _build_unload_no_target_prepare_batch(self):
        self._type_e_unload_reconnect_before_lower = bool(ConfigParams.reach_motor_names)
        if not ConfigParams.reach_motor_names:
            return [self._build_unload_prepare_lift_action(self.start_height)]
        return [
            self._build_unload_prepare_lift_action(self.start_height),
            TypeEChassisWithReachAction(
                self._reach_extension_distance(),
                reach_target=self._type_e_hook_reconnect_max_target(),
                wire_target=getattr(ConfigParams, "type_e_unload_length", 1.22),
                action_name="typeEUnloadChassisForward",
            ),
        ]

    @staticmethod
    def _type_e_hook_align_start_target():
        """兼容旧调用名；放货前不再使用 typeEHookAlignTravel 截断行程。"""
        return RobotTypeE._type_e_hook_reconnect_max_target()

    @staticmethod
    def _type_e_hook_reconnect_max_target():
        """返回重连前的最大安全位置，不使用 typeEHookAlignTravel 截断行程。"""
        targets = []
        margin = ConfigParams.type_e_hook_reconnect_limit_margin
        for motor_name in ConfigParams.reach_motor_names:
            min_length, max_length = ConfigParams._get_motor_limits(motor_name)
            targets.append(clamp(max_length - margin, min_length, max_length))
        return targets

    def _build_unload_release_action(self):
        # 只要配置了前移机构，目标点放货和原地放货都使用同一套释放顺序：
        # 重连扫描 -> 降叉。两者的差别仅在于原地放货不执行导航到目标点。
        if getattr(self, "_type_e_unload_reconnect_before_lower", False):
            return TypeEHookReconnectAndLowerAction(self.end_height)
        return TypeEHookAlignAndLowerAction(self.end_height)

    def _build_post_unload_actions(self):
        if not ConfigParams.reach_motor_names:
            return []
        return [self._build_reach_action("min", action_name="typeERetractReach")]

    @staticmethod
    def on_device_model_param_loaded(cfg):
        model_root = f"moduleType.{cfg.module_type}"
        cfg.type_e_model_lift_motor2 = RobotParam.getDevice("Model-000", f"{model_root}.liftMotor2") or ""
        cfg.type_e_model_reach_motor = (
            RobotParam.getDevice("Model-000", f"{model_root}.reachMotor")
            or RobotParam.getDevice("Model-000", f"{model_root}.stretchMotor")
            or ""
        )
        cfg.type_e_back_lasers = _config_keys(
            RobotParam.getDevice("Model-000", f"{model_root}.backLasers")
        )
        if not cfg.fork_motor_name:
            cfg.fork_motor_name = RobotParam.getDevice("Model-000", f"{model_root}.liftMotor1") or ""


robot = RobotTypeE(__file__)


if __name__ == "__main__":
    robot.main()
