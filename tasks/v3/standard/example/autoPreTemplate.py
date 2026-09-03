# -*- coding: utf-8 -*-
# @Date: 2026/07/23
# @Project: AutoPre（边走边动）任务脚本示例
"""AutoPre（边走边动）任务脚本示例（v3.5+）

演示同一业务流程在普通模式和 AutoPre 模式下的不同调度方式：
  1. 普通模式在正式阶段依次执行顶升和原地旋转
  2. AutoPre 模式只把可与导航并行的顶升前移，底盘旋转仍留在正式阶段
  3. `stage=2` 到达目标点后，正式旋转只在顶升完成并收到 `startAction` 后启动

`required_time` 生产代码应改为 `Motor.estimatePositionMoveDuration()` 的
估算结果；本示例使用覆盖当前电机参数的保守固定预算。

日志规范参见 docs/guide/spec/logging.md，与 template.py 保持一致。
"""
import math
import time

start_time = time.time()
from syspy import (Module, ModuleBase, ScriptStatus, Trace,
                   ScriptParam, ParamType,
                   ActionBase, ActionStatus, ActionTask,
                   Container, Navigation, Motor, AutoPreInterface, AutoPreSequenceAction)
from syspy.lib.module import SafeMoveStatus

MOD = "autoPreDemo"
DEMO_REQUIRED_TIME_SECONDS = 15.0
FORMAL_ROTATE_DEGREES = 90.0
FORMAL_ROTATE_SPEED = 0.5
LIFT_MOTOR_NAME = "Motor-002"
LIFT_TARGET_POSITION = 0.062
LIFT_SPEED = 0.005
LIFT_TIMEOUT_SECONDS = 30.0

script_param = ScriptParam(__file__)


# ============================================================================
# 配置参数定义
# ============================================================================
class ConfigParams:
    """脚本配置参数定义。"""
    demo_required_time = DEMO_REQUIRED_TIME_SECONDS
    debug_mode = False

    @classmethod
    def init(cls):
        builder = script_param.builderConfig()
        with builder.GROUPS():
            with builder.GROUP(key="autoPre", name="AutoPre", desc="AutoPre demo params"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    with builder.CHILD(
                            key="demo_required_time", name="Demo required time",
                            desc="顶升预动作的保守预算（生产代码应使用 Motor.estimatePositionMoveDuration）",
                    ):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(DEMO_REQUIRED_TIME_SECONDS, min_value=0.0, max_value=30.0)
                        builder.UNIT("s")
                        builder.SINGLESTEP(0.1)

            with builder.GROUP(key="debug", name="Debug", desc="Debug switches"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    with builder.CHILD(key="debug_mode", name="Debug mode",
                                       desc="Enable debug_print() and Trace.log(debug=True) channels"):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(False)

            builder.save(merge=True)
            cls.load_config()

    @classmethod
    def load_config(cls):
        """加载/重载配置参数。"""
        config = script_param.loadConfig()
        cls.demo_required_time = float(config.get("demo_required_time", DEMO_REQUIRED_TIME_SECONDS))
        cls.debug_mode = bool(config.get("debug_mode", False))
        Trace.log(
            f"config loaded demo_required_time={cls.demo_required_time} debug_mode={cls.debug_mode}",
            name=f"{MOD}.cfg",
        )


ConfigParams.init()


def script_config_callback():
    """脚本配置参数变更回调。"""
    Trace.log("script config changed", name=f"{MOD}.cfg")
    ConfigParams.load_config()


# ============================================================================
# 任务输入参数定义
# ============================================================================
class InputParams:
    """脚本任务输入参数定义。"""
    builder = script_param.builderInput()

    with builder.GROUPS():
        with builder.GROUP(key="operation", name="Operation", desc="Operation"):
            builder.TYPE(ParamType.COMBO_BOX)
            builder.REQUIRED(True)

            with builder.CHILDREN():
                with builder.CHILD(key="autoPreDemo", name="AutoPre demo", desc="AutoPre demo desc"):
                    builder.TYPE(ParamType.ARRAY)
    builder.save()


script_param.addAction(
    action_name="autoPreDemo",
    policy={"navigation.basic.autoPre": True},
    args={"operation": "autoPreDemo"},
    config={"autoPre.demo_required_time": DEMO_REQUIRED_TIME_SECONDS},
)
script_param.saveAction()


# ============================================================================
# 预动作：只执行可与导航并行的顶升
# ============================================================================
class DemoLiftAction(ActionBase):
    """演示型预动作：控制顶升电机到目标位置。"""

    def __init__(self, motor_name, target_position, speed, timeout):
        super().__init__()
        self.motor_name = motor_name
        self.target_position = float(target_position)
        self.speed = float(speed)
        self.timeout = float(timeout)
        self._command_sent = False
        self._started_at = None

    def reset(self):
        super().reset()
        self._command_sent = False
        self._started_at = None
        if not math.isfinite(self.target_position):
            self.fail_reason = "demo lift target position must be finite"
            self.action_status = ActionStatus.FAILED
        elif not math.isfinite(self.speed) or self.speed <= 0.0:
            self.fail_reason = "demo lift speed must be finite and positive"
            self.action_status = ActionStatus.FAILED
        elif not math.isfinite(self.timeout) or self.timeout <= 0.0:
            self.fail_reason = "demo lift timeout must be finite and positive"
            self.action_status = ActionStatus.FAILED

    def _fail(self, reason, reset_motor=True):
        if reset_motor:
            Motor.resetMotor(self.motor_name)
        self.fail_reason = reason
        self.action_status = ActionStatus.FAILED
        Trace.log(reason, name=f"{MOD}.err")

    def run(self, ctx):
        if not self._command_sent:
            Trace.log(
                "DemoLiftAction motor start name={} target_position={} speed={}".format(
                    self.motor_name, self.target_position, self.speed
                ),
                name=f"{MOD}.action",
            )
            if not Motor.resetMotor(self.motor_name):
                self._fail(
                    f"demo lift motor reset failed name={self.motor_name}",
                    reset_motor=False,
                )
                return
            if not Motor.setMotorPosition(self.motor_name, self.target_position, self.speed):
                self._fail(f"demo lift motor command failed name={self.motor_name}")
                return
            self._command_sent = True
            self._started_at = time.monotonic()

        if Motor.isMotorReached(self.motor_name):
            Trace.log(
                "DemoLiftAction motor reached name={} target_position={}".format(
                    self.motor_name, self.target_position
                ),
                name=f"{MOD}.action",
            )
            Motor.resetMotor(self.motor_name)
            self.action_status = ActionStatus.FINISHED
            return

        if time.monotonic() - self._started_at >= self.timeout:
            self._fail(
                "demo lift motor timeout name={} target_position={} timeout={}".format(
                    self.motor_name, self.target_position, self.timeout
                )
            )

    def cancel(self):
        Motor.resetMotor(self.motor_name)
        super().cancel()


# ============================================================================
# 正式动作：AutoPreSequenceAction 完成后才会被调度
# ============================================================================
class DemoRotateAction(ActionBase):
    """演示型正式动作：收到正式阶段通知后执行原地旋转。"""

    def __init__(self, rotate_degrees, speed_w):
        super().__init__()
        self.rotate_degrees = float(rotate_degrees)
        self.speed_w = float(speed_w)
        self.move_args = None

    def reset(self):
        super().reset()
        if not math.isfinite(self.rotate_degrees) or self.rotate_degrees == 0.0:
            self.fail_reason = "demo rotate angle must be finite and non-zero"
            self.action_status = ActionStatus.FAILED
            return
        if not math.isfinite(self.speed_w) or self.speed_w <= 0.0:
            self.fail_reason = "demo rotate speed must be finite and positive"
            self.action_status = ActionStatus.FAILED
            return

        Navigation.resetOdoMove()
        self.move_args = {
            "locMode": 0,
            "moveAngle": abs(math.radians(self.rotate_degrees)),
            "speedW": self.speed_w if self.rotate_degrees > 0.0 else -self.speed_w,
            "actionName": "DemoRotateAction",
        }
        Trace.log(
            f"DemoRotateAction start degrees={self.rotate_degrees} args={self.move_args}",
            name=f"{MOD}.action",
        )

    def run(self, ctx):
        try:
            status = int(Navigation.runOdoMove(self.move_args))
        except (TypeError, ValueError) as e:
            self.fail_reason = f"demo rotate returned invalid status error={e}"
            self.action_status = ActionStatus.FAILED
            Navigation.resetOdoMove()
            return

        if status in (int(ActionStatus.INIT), int(ActionStatus.RUNNING)):
            return
        if status == int(ActionStatus.FINISHED):
            self.action_status = ActionStatus.FINISHED
            Navigation.resetOdoMove()
            Trace.log("DemoRotateAction finished", name=f"{MOD}.action")
            return

        self.fail_reason = f"demo rotate failed status={status}"
        self.action_status = ActionStatus.FAILED
        Navigation.resetOdoMove()

    def cancel(self):
        Navigation.resetOdoMove()
        super().cancel()


# ============================================================================
# 任务主类
# ============================================================================
class ModuleAutoPreDemo(ModuleBase):
    """AutoPre 示例任务脚本主类。

    普通模式装配为 `[DemoLiftAction, DemoRotateAction]`；AutoPre 模式装配为
    `[AutoPreSequenceAction(pre_actions=[DemoLiftAction]), DemoRotateAction]`。
    两种模式完成相同动作，只改变顶升动作的启动时机。
    """

    def __init__(self):
        super().__init__()
        self.args: dict = {}
        self.status = ScriptStatus.NONE
        self.report_info: dict = {}
        self.action_task = ActionTask(mod=MOD)
        self._safe_count = 0
        Container.initContainer(0)

    @staticmethod
    def _new_lift_action():
        return DemoLiftAction(
            LIFT_MOTOR_NAME,
            LIFT_TARGET_POSITION,
            LIFT_SPEED,
            LIFT_TIMEOUT_SECONDS,
        )

    @staticmethod
    def _new_formal_action():
        return DemoRotateAction(FORMAL_ROTATE_DEGREES, FORMAL_ROTATE_SPEED)

    def _build_actions(self, auto_pre_enabled):
        lift_action = self._new_lift_action()
        formal_action = self._new_formal_action()
        if not auto_pre_enabled:
            return [lift_action, formal_action]

        auto_pre_action = AutoPreSequenceAction(
            pre_actions=[lift_action],
            required_time=ConfigParams.demo_required_time,
            advance_time=1.0,
            station="targetStation",
            include_rotation=True,
            must_stop_at_pre_station=False,
        )
        return [auto_pre_action, formal_action]

    def init_args(self, args: dict):
        """收到合法任务参数后调用：装配队列并切到 RUNNING。"""
        auto_pre_enabled = Module.getAutoPre()
        self.args = args
        operation = args.get("operation")
        stage = Module.getTaskParams("stage", 2)
        Trace.log(
            "task start operation={} task_id={} autoPre={} stage={}".format(
                operation, Module.getTaskId(), auto_pre_enabled, stage
            ),
            name=MOD,
        )

        if operation != "autoPreDemo":
            Trace.log(f"unsupported operation={operation}", name=f"{MOD}.err")
            self.set_status(ScriptStatus.FAILED)
            return

        if stage != 2:
            Trace.log(f"unsupported script.stage={stage}, expected 2", name=f"{MOD}.err")
            self.set_status(ScriptStatus.FAILED)
            return

        Trace.log(
            "workflow mode={} lift_target={} lift_speed={} required_time={} "
            "deadline=targetStation formal_rotate_degrees={}".format(
                "autoPre" if auto_pre_enabled else "normal",
                LIFT_TARGET_POSITION,
                LIFT_SPEED,
                ConfigParams.demo_required_time,
                FORMAL_ROTATE_DEGREES,
            ),
            name=f"{MOD}.autoPre",
        )
        self.action_task.build(self._build_actions(auto_pre_enabled))
        self.set_status(ScriptStatus.RUNNING)

    def run(self):
        """状态为 RUNNING 时由主循环调用，推进队列；队列终态时同步脚本状态。"""
        self.action_task.step(self)
        if self.action_task.is_done:
            self.set_status(
                ScriptStatus.FAILED if self.action_task.status == ActionStatus.FAILED else ScriptStatus.FINISHED
            )

    def set_status(self, new_status):
        """统一的状态切换入口：保证一次切换只落一条日志（去重）。"""
        if self.status == new_status:
            return
        Trace.log(f"status {ScriptStatus(self.status).name} -> {ScriptStatus(new_status).name}", name=MOD)
        self.status = new_status

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
            f"task cancelled active={len(self.action_task.active)}/{self.action_task.total}", name=MOD
        )
        self.action_task.cancel()
        self.set_status(ScriptStatus.FAILED)

    def safeMoveCheck(self):
        """底盘移动前安全检查（可选）。"""
        self._safe_count += 1
        status = SafeMoveStatus.RUNNING
        if self._safe_count >= 100:
            self._safe_count = 0
            status = SafeMoveStatus.FINISHED
        self.setSafeMoveStatus(status)
        if status in (SafeMoveStatus.FAILED, SafeMoveStatus.FINISHED):
            Trace.log(f"safe move check done status={status}", name=MOD)
            self.event_safe_move_check = False

    def tick_report(self):
        """每 tick 调用一次：合并一次 reportInfo + 集中数值时序上报。"""
        cur = self.action_task.current
        counts = self.action_task.status_counts()

        self.report_info.update({
            "taskId": Module.getTaskId(),
            "args": self.args,
            "status": self.status,
            "action": cur.action_type if cur else "",
            "actionId": cur.action_id if cur else "",
            "actionTotal": self.action_task.total,
            "totalTime": round(time.time() - start_time, 2),
            "containers": Container.getContainers(),
        })
        Module.reportInfo(self.report_info)

        Trace.log(
            {
                "scriptStatus":   int(self.status),
                "total":          int(self.action_task.total),
                "runningCount":   int(counts["running"]),
                "waitingCount":   int(counts["init"]),
                "finishedCount":  int(counts["finished"]),
                "failedCount":    int(counts["failed"]),
                "suspendedCount": int(counts["suspended"]),
            },
            False,
            name=f"{MOD}.task",
        )
        Trace.log(
            {"startActionLatched": bool(AutoPreInterface.isStartActionLatched())},
            False,
            name=f"{MOD}.autoPre",
        )


# ============================================================================
# 主入口
# ============================================================================
def main():
    ScriptParam.setConfigChangeCallBack(script_config_callback)

    Module.init()
    m = ModuleAutoPreDemo()

    while True:
        Module.setStatus(m.status)
        m.tick_report()

        if m.event_safe_move_check:
            m.safeMoveCheck()

        status = m.status
        if status == ScriptStatus.NONE:
            args = Module.getTaskArgs()
            if args:
                try:
                    args = script_param.loadInput(args)
                    m.init_args(args)
                except ValueError as e:
                    Trace.log(f"input params validate failed error={e}", name=f"{MOD}.err")
        elif status == ScriptStatus.RUNNING:
            m.run()
        elif status == ScriptStatus.SUSPENDED:
            m.suspend()
        elif status in (ScriptStatus.FAILED, ScriptStatus.FINISHED):
            m.action_task.reset()
            m.set_status(ScriptStatus.NONE)

        time.sleep(0.1)


if __name__ == "__main__":
    main()
