# -*- coding: utf-8 -*-
# @Date: 2026/02/04
# @Project: 3.5版本电机控制任务脚本
import json
import math
import time
from typing import Any, Dict

from syspy import (
    ActionBase,
    ActionStatus,
    ActionTask,
    Container,
    Module,
    ModuleBase,
    Motor,
    Navigation,
    Odometer,
    ParamType,
    RobotParam,
    ScriptParam,
    ScriptStatus,
    Trace,
)
from syspy.core.rbk_rpc import Service
from syspy.utils import ScriptType


MOD = "motor"
start_time = time.time()
script_param = ScriptParam(__file__)




class ParamError(Exception):
    pass


def required(req: Dict[str, Any], param_name: str) -> Any:
    if param_name not in req:
        raise ParamError(f"Missing required parameter: {param_name}")
    return req[param_name]


class MotorControlAction(ActionBase):

    _POSITION_STABLE_DURATION = 0.1

    def __init__(self, args: Dict[str, Any]):
        super().__init__("MotorControl")
        self.args = dict(args)
        self.operation = self.args.get("type", "")
        self.key = ""
        self.motor_type = ""
        self._started = False
        self._deadline = 0.0
        self._remaining = 0.0
        self._can_id = 0
        self._pos = 0.0
        self._speed = 0.0
        self._max_speed = 0.0
        self._stop_di = ""
        self._linear_position_mode = False
        self._rotate_position_mode = False
        self._min_length = 0.0
        self._max_length = 0.0
        self._min_angle = 0.0
        self._max_angle = 0.0
        self._last_motor_pos = None
        self._position_stable_since = None

    def args_summary(self) -> dict:
        return {
            "operation": self.operation,
            "key": self.args.get("key", ""),
            "name": self.args.get("name", ""),
            "motorType": self.args.get("motorType", ""),
        }

    def reset(self):
        super().reset()
        self._started = False
        self._last_motor_pos = None
        self._position_stable_since = None

    def _resolve_key(self) -> str:
        key = self.args.get("key")
        if key:
            return key

        name = self.args.get("name")
        if not name:
            raise ParamError("need key or name")

        key = RobotParam.getDeviceKeyByName(name)
        Trace.log(f"getDeviceKeyByName({name}) => {key}", name=f"{MOD}.cfg")
        if not key:
            raise ParamError(f"Device name '{name}' not found")
        return key

    def _get_can_id(self) -> int:
        can_id = RobotParam.getDevice(self.key, "basic.canID")
        if can_id is None:
            raise ParamError(f"Motor '{self.key}' CAN ID not found")
        return int(can_id)

    def _check_motor_type(self, expected_type: str):
        func = RobotParam.getDevice(self.key, "func")
        if func is not None and func != expected_type:
            raise ParamError(
                f"Motor '{self.key}' type mismatch: expected '{expected_type}', got '{func}'"
            )

    def _get_motor_calib_state(self):
        try:
            for motor in Odometer.getData().get("motorInfo", []):
                if motor.get("key") == self.key:
                    return motor.get("calib")
        except Exception as exc:
            Trace.log(
                f"read motor {self.key} calib failed error={exc}",
                name=f"{MOD}.err",
            )
        return None

    def _set_deadline(self, duration: float):
        self._remaining = max(0.0, float(duration))
        self._deadline = time.monotonic() + self._remaining

    def _speed_limit_reached(self, min_pos: float, max_pos: float) -> bool:
        if self._stop_di and Motor.isMotorReached(self.key):
            return True

        current_pos = float(Motor.getMotorPos(self.key))
        if self._speed > 0:
            target_pos = max_pos
            if current_pos >= target_pos:
                return True
        elif self._speed < 0:
            target_pos = min_pos
            if current_pos <= target_pos:
                return True

        tolerance = max(0.0, max_pos - min_pos) * 0.001
        if abs(current_pos - target_pos) > tolerance:
            self._last_motor_pos = current_pos
            self._position_stable_since = None
            return False

        now = time.monotonic()
        if self._last_motor_pos != current_pos:
            self._last_motor_pos = current_pos
            self._position_stable_since = now
            return False
        if self._position_stable_since is None:
            self._position_stable_since = now
            return False
        return now - self._position_stable_since >= self._POSITION_STABLE_DURATION

    def _stop_motor(self):
        if not self.key:
            return
        try:
            Motor.resetMotor(self.key)
        except Exception as exc:
            Trace.log(
                f"reset motor failed key={self.key} error={exc}",
                name=f"{MOD}.err",
            )

    def _finish(self):
        self._stop_motor()
        self.action_status = ActionStatus.FINISHED

    def _fail(self, exc: Exception):
        self._stop_motor()
        self.fail_reason = str(exc)
        self.action_status = ActionStatus.FAILED
        Trace.log(f"motor control failed error={exc}", name=f"{MOD}.err")

    def _start(self):
        self._started = True
        self.operation = required(self.args, "type")
        self.key = self._resolve_key()

        if self.operation == "setEnable":
            enable = required(self.args, "enable")
            if enable:
                Motor.enableMotor(self.key)
            else:
                Motor.disableMotor(self.key)
            self.action_status = ActionStatus.FINISHED
            return

        if self.operation == "clearEncoder":
            Service.client().call_service("DSPChassis", "clearMotorEncoder", self.key)
            self.action_status = ActionStatus.FINISHED
            return

        if self.operation == "clearFault":
            Service.client().call_service("DSPChassis", "clearMotorFault", self.key)
            self.action_status = ActionStatus.FINISHED
            return

        if self.operation == "setHoming":
            timeout = float(required(self.args, "timeout"))
            if timeout <= 0:
                raise ParamError("'timeout' must be greater than 0")
            Trace.log(f"setHoming key={self.key} timeout={timeout}", name=MOD)
            Motor.motorCalib(self.key)
            time.sleep(0.05)
            self._set_deadline(timeout)
            return

        if self.operation != "motorControl":
            raise ParamError(f"type {self.operation} not support")

        self.motor_type = required(self.args, "motorType")

        if self.motor_type == "rotate":
            self._check_motor_type("rotation")
            position = self.args.get("position")
            speed = self.args.get("speed")
            self._max_speed = float(self.args.get("maxSpeed", 0.0))
            self._stop_di = self.args.get("stopDI", "")
            operation_time = self.args.get("operationTime")

            if position is None and speed is None:
                raise ParamError("'position' and 'speed' are both None for rotate motor")
            if operation_time is not None:
                self._set_deadline(operation_time)
            self._max_angle = math.radians(float(
                RobotParam.getDevice(self.key, "func.rotation.maxAngle")
            ))
            self._min_angle = math.radians(float(
                RobotParam.getDevice(self.key, "func.rotation.minAngle")
            ))

            if position is not None:
                self._rotate_position_mode = True
                self._pos = math.radians(float(position))
                self._max_speed = math.radians(self._max_speed)
                if self._pos < self._min_angle or self._pos > self._max_angle:
                    raise ParamError(
                        f"Rotate motor position {self._pos} out of range "
                        f"[{self._min_angle}, {self._max_angle}]"
                    )

                Motor.resetMotor(self.key)
                Motor.setMotorPosition(
                    self.key, self._pos, self._max_speed, self._stop_di
                )
            else:
                self._speed = math.radians(float(speed))
                if operation_time is not None:
                    move_angle = self._speed * float(operation_time)
                    if math.fabs(move_angle) > self._max_angle - self._min_angle:
                        raise ParamError(
                            f"Rotate motor speed {self._speed} * operationTime "
                            f"{operation_time} out of range "
                            f"[{self._min_angle}, {self._max_angle}]"
                        )
                Motor.resetMotor(self.key)
            return

        Motor.resetMotor(self.key)

        if self.motor_type == "walk":
            self._check_motor_type("walk")
            self._can_id = self._get_can_id()
            self._speed = float(required(self.args, "speed"))
            self._set_deadline(required(self.args, "operationTime"))
            Trace.log(
                f"motorControl walk key={self.key} canId={self._can_id} speed={self._speed}",
                name=MOD,
            )
            return

        if self.motor_type == "steer":
            self._check_motor_type("steer")
            self._can_id = self._get_can_id()
            self._pos = float(self.args.get("pos", 0.0))
            self._set_deadline(required(self.args, "timeout"))
            Service.client().call_service(
                "DSPChassis", "setMotorPosition", self._can_id, self.motor_type, self._pos
            )
            return

        if self.motor_type == "spin":
            self._check_motor_type("spin")
            self._pos = float(self.args.get("angle", 0.0))
            Navigation.setRobotSpinAngle(math.radians(self._pos), 0)
            return

        if self.motor_type != "linear":
            raise ParamError(
                f"motorType '{self.motor_type}' not supported, expected: walk/steer/spin/rotate/linear"
            )

        self._check_motor_type("linear")
        pos = self.args.get("pos")
        speed = self.args.get("speed")
        self._max_speed = float(self.args.get("maxSpeed", 0.0))
        self._stop_di = self.args.get("stopDi", "")
        operation_time = float(required(self.args, "operationTime"))
        self._max_length = float(RobotParam.getDevice(self.key, "func.linear.maxLength"))
        self._min_length = float(RobotParam.getDevice(self.key, "func.linear.minLength"))

        if pos is None and speed is None:
            raise ParamError("'pos' and 'speed' are both None for linear motor")

        if speed is not None and abs(float(speed) * operation_time) > self._max_length:
            raise ParamError(
                f"Linear motor speed {speed} * operationTime {operation_time} out of range "
                f"[{self._min_length}, {self._max_length}]"
            )

        self._set_deadline(operation_time)
        if pos is not None:
            self._linear_position_mode = True
            self._pos = float(pos)
            if self._pos < self._min_length or self._pos > self._max_length:
                raise ParamError(
                    f"Linear motor position {self._pos} out of range "
                    f"[{self._min_length}, {self._max_length}]"
                )
            current_pos = Motor.getMotorPos(self.key)
            if current_pos >= 0 and self._max_speed > 0:
                self._pos = min(
                    self._pos,
                    current_pos + operation_time * self._max_speed,
                )
            Motor.setMotorPosition(
                self.key, self._pos, self._max_speed, self._stop_di
            )
        else:
            self._speed = float(speed)

    def _step(self):
        if self.operation == "setHoming":
            if self._get_motor_calib_state() == 2:
                self._finish()
            elif time.monotonic() > self._deadline:
                raise TimeoutError(
                    f"setHoming: key={self.key}, timeout after {self._remaining}s"
                )
            return

        if self.motor_type == "walk":
            if time.monotonic() >= self._deadline:
                self._finish()
            else:
                Service.client().call_service(
                    "DSPChassis", "setMotorSpeed", self._can_id, self.motor_type, self._speed
                )
            return

        if self.motor_type == "steer":
            if Motor.isMotorPositionReached(self.key, self._pos):
                self._finish()
            elif time.monotonic() > self._deadline:
                Trace.log(
                    f"steer timeout current={Motor.getMotorPos(self.key)} target={self._pos}",
                    name=MOD,
                )
                Navigation.setSteerAngle(self.key, math.radians(self._pos))
                self._finish()
            return

        if self.motor_type == "spin":
            if Navigation.spinRun():
                self._finish()
            return

        if self.motor_type == "rotate":
            if self._rotate_position_mode:
                if Motor.isMotorReached(self.key):
                    self._finish()
                elif self._deadline and time.monotonic() > self._deadline:
                    raise TimeoutError(
                        f"rotate: key={self.key}, timeout after {self._remaining}s"
                    )
                return

            reached_limit = self._speed_limit_reached(
                self._min_angle, self._max_angle
            )
            if reached_limit or (
                self._deadline and time.monotonic() >= self._deadline
            ):
                self._finish()


            else:
                Motor.setMotorSpeed(self.key, self._speed, self._stop_di)
            return

        if self._linear_position_mode:
            if Motor.isMotorReached(self.key) or time.monotonic() > self._deadline:
                self._finish()
            return

        reached_limit = self._speed_limit_reached(
            self._min_length, self._max_length
        )
        if reached_limit or time.monotonic() >= self._deadline:
            self._finish()
        else:
            Motor.setMotorSpeed(self.key, self._speed, self._stop_di)

    def run(self, ctx):
        if self.action_status != ActionStatus.RUNNING:
            return
        try:
            if not self._started:
                self._start()
            if self.action_status == ActionStatus.RUNNING:
                self._step()
        except Exception as exc:
            self._fail(exc)

    def suspend(self):
        if self.action_status != ActionStatus.RUNNING:
            return
        if self._deadline:
            self._remaining = max(0.0, self._deadline - time.monotonic())
        self._stop_motor()
        super().suspend()

    def resume(self):
        if self.action_status != ActionStatus.SUSPENDED:
            return
        super().resume()
        self._last_motor_pos = None
        self._position_stable_since = None
        try:
            if self._deadline:
                self._deadline = time.monotonic() + self._remaining
            if self.operation == "setHoming":
                Motor.motorCalib(self.key)
            elif self.motor_type == "steer":
                Service.client().call_service(
                    "DSPChassis", "setMotorPosition", self._can_id, self.motor_type, self._pos
                )
            elif self.motor_type == "spin":
                Navigation.setRobotSpinAngle(math.radians(self._pos), 0)
            elif self.motor_type == "linear" and self._linear_position_mode:
                Motor.setMotorPosition(
                    self.key, self._pos, self._max_speed, self._stop_di
                )
            elif self.motor_type == "rotate" and self._rotate_position_mode:
                Motor.setMotorPosition(
                    self.key, self._pos, self._max_speed, self._stop_di
                )
        except Exception as exc:
            self._fail(exc)

    def cancel(self):
        self._stop_motor()
        super().cancel()


def add_motor_identity(builder):
    with builder.CHILD(key="key", name="Motor Key", desc="Motor device key, use with name"):
        builder.TYPE(ParamType.STRING)
        builder.REQUIRED(False)
    with builder.CHILD(key="name", name="Motor Name", desc="Motor device name, use with key"):
        builder.TYPE(ParamType.STRING)
        builder.REQUIRED(False)


class InputParams:
    """脚本任务输入参数定义。"""

    builder = script_param.builderInput()
    with builder.GROUPS():
        with builder.GROUP(key="type", name="Motor Operation", desc="Motor control operation type"):
            builder.TYPE(ParamType.COMBO_BOX)
            builder.REQUIRED(True)
            with builder.CHILDREN():
                with builder.CHILD(key="setEnable", name="Set Enable", desc="Enable/disable motor"):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        add_motor_identity(builder)
                        with builder.CHILD(key="enable", name="Enable", desc="True to enable, False to disable"):
                            builder.TYPE(ParamType.BOOL)
                            builder.REQUIRED(True)
                            builder.DEFAULTVALUE(True)

                with builder.CHILD(key="clearEncoder", name="Clear Encoder", desc="Clear motor encoder value"):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        add_motor_identity(builder)

                with builder.CHILD(key="motorControl", name="Motor Control", desc="Unified motor control interface"):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        with builder.CHILD(key="motorType", name="Motor Type", desc="Motor type"):
                            builder.TYPE(ParamType.COMBO_BOX)
                            builder.REQUIRED(True)
                            with builder.CHILDREN():
                                with builder.CHILD(key="walk", name="Walk Motor", desc="Speed control, m/s"):
                                    builder.TYPE(ParamType.ARRAY)
                                    with builder.CHILDREN():
                                        add_motor_identity(builder)
                                        with builder.CHILD(key="speed", name="Target Speed", desc="Target speed, unit m/s"):
                                            builder.TYPE(ParamType.DOUBLE)
                                            builder.REQUIRED(True)
                                            builder.DEFAULTVALUE(0.5)
                                        with builder.CHILD(key="operationTime", name="Operation Time", desc="Operation time, unit s"):
                                            builder.TYPE(ParamType.DOUBLE)
                                            builder.REQUIRED(True)
                                            builder.DEFAULTVALUE(1.0)

                                with builder.CHILD(key="steer", name="Steer Motor", desc="Position control, deg"):
                                    builder.TYPE(ParamType.ARRAY)
                                    with builder.CHILDREN():
                                        add_motor_identity(builder)
                                        with builder.CHILD(key="pos", name="Target Angle", desc="Target angle, unit deg"):
                                            builder.TYPE(ParamType.DOUBLE)
                                            builder.REQUIRED(False)
                                            builder.DEFAULTVALUE(0.0)
                                        with builder.CHILD(key="timeout", name="Timeout", desc="Timeout, unit s"):
                                            builder.TYPE(ParamType.DOUBLE)
                                            builder.REQUIRED(True)
                                            builder.DEFAULTVALUE(10.0)

                                with builder.CHILD(key="spin", name="Spin Motor", desc="Angle control, deg"):
                                    builder.TYPE(ParamType.ARRAY)
                                    with builder.CHILDREN():
                                        add_motor_identity(builder)
                                        with builder.CHILD(key="angle", name="Target Angle", desc="Target angle, unit deg"):
                                            builder.TYPE(ParamType.DOUBLE)
                                            builder.REQUIRED(False)
                                            builder.DEFAULTVALUE(0.0)

                                with builder.CHILD(key="rotate", name="Rotate Motor", desc="Position/speed control, deg"):
                                    builder.TYPE(ParamType.ARRAY)
                                    with builder.CHILDREN():
                                        add_motor_identity(builder)
                                        with builder.CHILD(key="position", name="Target Angle", desc="Target angle, unit deg"):
                                            builder.TYPE(ParamType.DOUBLE)
                                            builder.REQUIRED(False)
                                        with builder.CHILD(key="speed", name="Target Speed", desc="Target speed, unit deg/s"):
                                            builder.TYPE(ParamType.DOUBLE)
                                            builder.REQUIRED(False)
                                        with builder.CHILD(key="maxSpeed", name="Max Speed", desc="Max speed, unit deg/s"):
                                            builder.TYPE(ParamType.DOUBLE)
                                            builder.REQUIRED(False)
                                            builder.DEFAULTVALUE(0.0)
                                        with builder.CHILD(key="stopDI", name="Stop DI", desc="Stop DI id"):
                                            builder.TYPE(ParamType.STRING)
                                            builder.REQUIRED(False)
                                            builder.DEFAULTVALUE("")
                                        with builder.CHILD(key="operationTime", name="Timeout", desc="Timeout, unit s"):
                                            builder.TYPE(ParamType.DOUBLE)
                                            builder.REQUIRED(False)

                                with builder.CHILD(key="linear", name="Linear Motor", desc="Position/speed control"):
                                    builder.TYPE(ParamType.ARRAY)
                                    with builder.CHILDREN():
                                        add_motor_identity(builder)
                                        with builder.CHILD(key="pos", name="Target Position", desc="Target position, unit m"):
                                            builder.TYPE(ParamType.DOUBLE)
                                            builder.REQUIRED(False)
                                            builder.DEFAULTVALUE(0.0)
                                        with builder.CHILD(key="speed", name="Lift Speed", desc="Speed, unit m/s"):
                                            builder.TYPE(ParamType.DOUBLE)
                                            builder.REQUIRED(False)
                                            builder.DEFAULTVALUE(0.0)
                                        with builder.CHILD(key="stopDi", name="Stop DI", desc="Stop DI id"):
                                            builder.TYPE(ParamType.STRING)
                                            builder.REQUIRED(False)
                                            builder.DEFAULTVALUE("")
                                        with builder.CHILD(key="operationTime", name="Timeout", desc="Timeout, unit s"):
                                            builder.TYPE(ParamType.DOUBLE)
                                            builder.REQUIRED(False)
                                            builder.DEFAULTVALUE(0.0)
                                        with builder.CHILD(key="maxSpeed", name="Max Speed", desc="Max speed, unit m/s"):
                                            builder.TYPE(ParamType.DOUBLE)
                                            builder.REQUIRED(False)
                                            builder.DEFAULTVALUE(0.0)

                with builder.CHILD(key="setHoming", name="Set Homing", desc="Motor homing/calibration"):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        add_motor_identity(builder)
                        with builder.CHILD(key="timeout", name="Timeout", desc="Timeout for homing, unit s"):
                            builder.TYPE(ParamType.DOUBLE)
                            builder.REQUIRED(True)
                            builder.DEFAULTVALUE(60.0)

                with builder.CHILD(key="clearFault", name="Clear Fault", desc="Clear motor fault status"):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        add_motor_identity(builder)
    builder.save()


class MotorController(ModuleBase):
    """电机调试任务主类。"""

    def __init__(self):
        super().__init__()
        self.args: Dict[str, Any] = {}
        self.status = ScriptStatus.NONE
        self.report_info: Dict[str, Any] = {}
        self.action_task = ActionTask(mod=MOD)
        self._last_report_time = 0.0
        Container.initContainer(0)

    def set_status(self, new_status: ScriptStatus):
        Module.setStatus(new_status)
        if self.status == new_status:
            return
        Trace.log(
            f"status {ScriptStatus(self.status).name} -> {ScriptStatus(new_status).name}",
            name=MOD,
        )
        self.status = new_status

    def init_args(self, args: Dict[str, Any]):
        self.args = dict(args)
        Trace.log(
            f"task start operation={self.args.get('type')} task_id={Module.getTaskId()}",
            name=MOD,
        )
        self.action_task.build([MotorControlAction(self.args)])
        self.set_status(ScriptStatus.RUNNING)

    def run(self):
        self.action_task.step(self)
        if self.action_task.is_done:
            status = (
                ScriptStatus.FAILED
                if self.action_task.status == ActionStatus.FAILED
                else ScriptStatus.FINISHED
            )
            self.set_status(status)

    def suspend(self):
        if Module.getStatus() == ScriptStatus.RUNNING:
            self.action_task.suspend()
            self.set_status(ScriptStatus.SUSPENDED)

    def resume(self):
        if Module.getStatus() == ScriptStatus.SUSPENDED:
            self.action_task.resume()
            self.set_status(ScriptStatus.RUNNING)

    def cancel(self):
        Trace.log(
            f"task cancelled active={len(self.action_task.active)}/{self.action_task.total}",
            name=MOD,
        )
        self.action_task.cancel()
        self.set_status(ScriptStatus.FAILED)

    def tick_report(self):
        now = time.monotonic()
        if now - self._last_report_time < 0.1:
            return
        self._last_report_time = now
        current = self.action_task.current
        self.report_info.update(
            {
                "taskId": Module.getTaskId(),
                "args": self.args,
                "status": self.status,
                "action": current.action_type if current else "",
                "actionStatus": int(current.action_status) if current else 0,
                "totalTime": round(time.time() - start_time, 2),
                "containers": Container.getContainers(),
            }
        )
        Module.reportInfo(self.report_info)


def main():
    Module.init(script_type=ScriptType.TASK)
    controller = MotorController()

    while True:
        Module.setStatus(controller.status)
        controller.tick_report()

        if controller.status == ScriptStatus.NONE:
            args = Module.getTaskArgs()
            if args:
                try:
                    validated_args = script_param.loadInput(args)
                    Trace.log(
                        f"task args validated args={json.dumps(validated_args, ensure_ascii=False)}",
                        name=MOD,
                    )
                    controller.init_args(validated_args)
                except ValueError as exc:
                    Trace.log(
                        f"input params validate failed error={exc}",
                        name=f"{MOD}.err",
                    )
                    controller.set_status(ScriptStatus.FAILED)
        elif controller.status == ScriptStatus.RUNNING:
            controller.run()
        elif controller.status in (ScriptStatus.FAILED, ScriptStatus.FINISHED):
            controller.set_status(ScriptStatus.NONE)
            return

        time.sleep(0.01)


if __name__ == "__main__":
    main()
