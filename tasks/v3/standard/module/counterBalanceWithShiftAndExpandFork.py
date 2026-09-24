# -*- coding: utf-8 -*-
from syspy import Di, Motor, Trace, _TR
from syspy.utils.param_server import ParamType
from syspy.lib.action_task import ActionBase

from standard.fork import ConfigParams
from standard.fork_utils import (
    ActionStatus,
    RunMotorByPosition,
    ReachAwareForkMotorByPosition,
)
from standard.fork import HeavyFork


class RunExpandMotorsByPosition(ActionBase):
    """同时控制左右开合电机到指定位置。"""

    def __init__(self, left_motor_name, right_motor_name, left_position, right_position,
                 max_speed=0.1, action_name="RunExpandMotors"):
        super().__init__(action_name)
        self.left_motor_name = left_motor_name
        self.right_motor_name = right_motor_name
        self.left_position = left_position
        self.right_position = right_position
        self.max_speed = max_speed
        self.left_reached = False
        self.right_reached = False
        self.action_status = ActionStatus.INIT

    def run(self, ctx=None):
        if not self.init:
            self.init = True
            self.action_status = ActionStatus.RUNNING
            Trace.log(
                f"RunExpandMotors: left={self.left_motor_name} to {self.left_position}, "
                f"right={self.right_motor_name} to {self.right_position}",
                name="fork.task"
            )
            if self.left_motor_name:
                Motor.setMotorPosition(self.left_motor_name, self.left_position, self.max_speed)
            if self.right_motor_name:
                Motor.setMotorPosition(self.right_motor_name, self.right_position, self.max_speed)

        self.left_reached = Motor.isMotorReached(self.left_motor_name) if self.left_motor_name else True
        self.right_reached = Motor.isMotorReached(self.right_motor_name) if self.right_motor_name else True

        if self.left_reached and self.right_reached:
            self.action_status = ActionStatus.FINISHED
            Trace.log("RunExpandMotors finished", name="fork.task")

    def reset(self):
        if self.left_motor_name:
            Motor.resetMotor(self.left_motor_name)
        if self.right_motor_name:
            Motor.resetMotor(self.right_motor_name)
        self.action_status = ActionStatus.RUNNING
        self.init = False

    def cancel(self):
        if self.left_motor_name:
            Motor.resetMotor(self.left_motor_name)
        if self.right_motor_name:
            Motor.resetMotor(self.right_motor_name)
        self.action_status = ActionStatus.FAILED

    def _trace_state(self):
        return {
            "action_status": int(self.action_status),
            "left_reached": self.left_reached,
            "right_reached": self.right_reached,
        }


class CounterBalanceForkMotorByPosition(ReachAwareForkMotorByPosition):
    position_tolerance = 0.02


class RunPitchToZero(RunMotorByPosition):
    """Pitch 回零以零位 DI 或电机位置到位作为完成条件。"""

    def run(self, ctx=None):
        super().run(ctx)
        if self.action_status == ActionStatus.RUNNING and self.stop_di and Di.getDi(self.stop_di):
            Motor.resetMotor(self.motor_name)
            self._motor_reset_done = True
            self.action_status = ActionStatus.FINISHED
            Trace.log(
                f"pitch motor zero DI reached: motor={self.motor_name}, di={self.stop_di}",
                name="fork.task",
            )


def _expand_config_reload(config_cls, cfg):
    config_cls.pitch_zero_di = config_cls._find_config_value(["pitchZeroDI"], cfg) or ""
    if len(config_cls.expand_motor_items or []) != 2:
        return

    left_key = config_cls._find_config_value(["expandMotorLeft"], cfg) or ""
    right_key = config_cls._find_config_value(["expandMotorRight"], cfg) or ""
    motor_names = [item.get("motorKey", "") for item in list(config_cls.expand_motor_items or []) if item.get("motorKey")]
    if not motor_names:
        return

    left_motor = left_key if left_key in motor_names else config_cls.expand_motor_left
    right_motor = right_key if right_key in motor_names and right_key != left_motor else config_cls.expand_motor_right

    if not right_motor or right_motor == left_motor:
        for motor_name in motor_names:
            if motor_name != left_motor:
                right_motor = motor_name
                break

    if not left_motor or not right_motor or left_motor == right_motor:
        return

    config_cls.expand_motor_left = left_motor
    config_cls.expand_motor_right = right_motor
    config_cls.expand_motor_items = [
        dict(item, side="left" if item.get("motorKey") == left_motor else "right")
        for item in config_cls.expand_motor_items
    ]
    config_cls.expand_motor_left_min, config_cls.expand_motor_left_max = config_cls._get_motor_limits(left_motor)
    config_cls.expand_motor_right_min, config_cls.expand_motor_right_max = config_cls._get_motor_limits(right_motor)


def _expand_config_builder(_config_cls, builder):
    if ConfigParams.pitch_motor_name:
        with builder.GROUP(key="pitchScene", name=_TR("Pitch Scene"), desc=_TR("Pitch motor settings")):
            builder.TYPE(ParamType.ARRAY)
            with builder.CHILDREN():
                with builder.CHILD(key="pitchZeroDI", name=_TR("Pitch Zero DI"),
                                   desc=_TR("Pitch zero position DI; configured in script instead of device model")):
                    builder.TYPE(ParamType.STRING)
                    builder.DEFAULTVALUE("")

    if ConfigParams.expand_motor_names:
        with builder.GROUP(key="expandScene", name=_TR("Expand Scene"), desc=_TR("Expand motor binding settings")):
            builder.TYPE(ParamType.ARRAY)
            with builder.CHILDREN():
                if ConfigParams.expand_motor_left:
                    with builder.CHILD(key="expandMotorLeft", name=_TR("Expand Motor Left"),
                                       desc=_TR("Left expand motor binding; overrides automatic detection")):
                        builder.TYPE(ParamType.STRING)
                        builder.DEFAULTVALUE(ConfigParams.expand_motor_left)
                if ConfigParams.expand_motor_right:
                    with builder.CHILD(key="expandMotorRight", name=_TR("Expand Motor Right"),
                                       desc=_TR("Right expand motor binding; overrides automatic detection")):
                        builder.TYPE(ParamType.STRING)
                        builder.DEFAULTVALUE(ConfigParams.expand_motor_right)


def _expand_operation_input(_input_cls, builder, _min_height, _max_height):
    if ConfigParams.expand_motor_left:
        with builder.CHILD(key="expand_left", name=_TR("Expand Motor Left"), desc=_TR("Left expand motor jog or move")):
            builder.TYPE(ParamType.ARRAY)
            with builder.CHILDREN():
                with builder.CHILD(key="jogStep", name=_TR("Jog Step"), desc=_TR("Jog step for left expand motor")):
                    builder.TYPE(ParamType.FLOAT)
                    builder.UNIT("m")
                    builder.SINGLESTEP(0.01)
                    builder.DEFAULTVALUE(0.1)
                with builder.CHILD(key="position", name=_TR("Position"), desc=_TR("Target position for left expand motor")):
                    builder.TYPE(ParamType.FLOAT)
                    builder.UNIT("m")
                    builder.SINGLESTEP(0.01)
                    builder.DEFAULTVALUE(-1)

    if ConfigParams.expand_motor_right:
        with builder.CHILD(key="expand_right", name=_TR("Expand Motor Right"), desc=_TR("Right expand motor jog or move")):
            builder.TYPE(ParamType.ARRAY)
            with builder.CHILDREN():
                with builder.CHILD(key="jogStep", name=_TR("Jog Step"), desc=_TR("Jog step for right expand motor")):
                    builder.TYPE(ParamType.FLOAT)
                    builder.UNIT("m")
                    builder.SINGLESTEP(0.01)
                    builder.DEFAULTVALUE(0.1)
                with builder.CHILD(key="position", name=_TR("Position"), desc=_TR("Target position for right expand motor")):
                    builder.TYPE(ParamType.FLOAT)
                    builder.UNIT("m")
                    builder.SINGLESTEP(0.01)
                    builder.DEFAULTVALUE(-1)


class CounterBalanceWithShiftAndExpandFork(HeavyFork):
    fork_motor_action_class = CounterBalanceForkMotorByPosition
    config_builder_hook = staticmethod(_expand_config_builder)
    config_reload_hook = staticmethod(_expand_config_reload)
    operation_input_hook = staticmethod(_expand_operation_input)

    def _build_expand_motor_action(self, rec_action):
        if not getattr(rec_action, "hole_positions", None):
            return None

        left_motor = ConfigParams.expand_motor_left
        right_motor = ConfigParams.expand_motor_right
        if not left_motor or not right_motor:
            return None

        left_pos = None
        right_pos = None
        for hole in rec_action.hole_positions:
            hole_y = float(hole.get("holeY", 0.0))
            if hole_y > 0 and left_pos is None:
                left_pos = hole_y
            elif hole_y < 0 and right_pos is None:
                right_pos = -hole_y

        if left_pos is None:
            left_pos = Motor.getMotorPos(left_motor)
        if right_pos is None:
            right_pos = Motor.getMotorPos(right_motor)

        Trace.log(f"Expand motor target: left={left_pos:.4f}, right={right_pos:.4f}", name="fork.task")
        return RunExpandMotorsByPosition(left_motor, right_motor, left_pos, right_pos)

    def _build_load_approach_batch(self, rec_action, rec_world_pos, method, args):
        actions = super()._build_load_approach_batch(rec_action, rec_world_pos, method, args)
        if ConfigParams.pitch_motor_name and ConfigParams.pitch_motor_max > 0:
            actions.insert(0, RunMotorByPosition(
                ConfigParams.pitch_motor_name,
                ConfigParams.pitch_motor_max,
                action_name="pitchToMax",
            ))
        return actions

    def _build_post_unload_actions(self):
        if ConfigParams.pitch_motor_name:
            return [
                RunPitchToZero(
                    ConfigParams.pitch_motor_name,
                    ConfigParams.pitch_motor_min,
                    action_name="pitchToMin",
                    stop_di=getattr(ConfigParams, "pitch_zero_di", ""),
                )
            ]
        return []


robot = CounterBalanceWithShiftAndExpandFork(__file__)


if __name__ == "__main__":
    robot.main()
