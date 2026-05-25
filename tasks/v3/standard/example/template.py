# -*- coding: utf-8 -*-
# @Date: 2026/05/24
# @Project: 3.5版本任务脚本模板
"""任务脚本模板（v3.5+）

本模板演示标准任务脚本应当遵循的结构：
  1. 参数模型：ConfigParams（配置参数） / InputParams（任务输入参数） / addAction（调度动作模板）
  2. 任务队列：ActionBase + ActionTask 调度（参考 module/jackWithSpin.py、cartonTransferUnit.py、liftFork.py）
  3. 日志规范：参见 docs/guide/spec/logging.md
       - Trace.log(name="<MOD>[.xxx]")：事件型日志（状态切换、关键决策、异常、配置加载）
       - Trace.log(dict, name="<MOD>.action")：结构化任务队列事件（taskBuild / taskExtend / actionStateChanged / taskFinished / taskFailed）
       - Trace.chart(name="<MOD>.task" / "<MOD>.motor")：tick 级时序采样，主循环末尾集中调用
       - Module.reportInfo：每次必须携带 containers 字段
"""
import json
import time
from typing import List

start_time = time.time()
from syspy import (Module, ModuleBase, ScriptStatus, Trace,
                   RobotParam, ScriptParam, ParamType,
                   ActionBase, ActionStatus, ActionTask,
                   Container)
from syspy.lib.module import SafeMoveStatus

# 业务通道名前缀（按车型替换：jack / ctu / fork / clean / ...；模板示例用 demo）
MOD = "demo"

# 实例化脚本参数
script_param = ScriptParam(__file__)


# ============================================================================
# 调试输出（受 ConfigParams.debug_mode 开关控制；生产代码禁止裸 print）
# ============================================================================
def debug_print(*args, **kwargs):
    """仅在 debug_mode 开启时打印到终端，不落盘。"""
    if ConfigParams.debug_mode:
        print(*args, **kwargs)


# ============================================================================
# 配置参数定义
# ============================================================================
class ConfigParams:
    """脚本配置参数定义"""
    param11 = None
    param12 = None
    param21 = None
    debug_mode = False

    @classmethod
    def init(cls):
        builder = script_param.builderConfig()
        with builder.GROUPS():
            with builder.GROUP(key="group1", name="Group1 name", desc="Group1 desc"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    with builder.CHILD(key="param11", name="Param11 name", desc="param11 desc"):
                        builder.TYPE(ParamType.STRING)

                    with builder.CHILD(key="param12", name="Param12 name", desc="param12 desc"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.015, min_value=0.0, max_value=0.1)
                        builder.UNIT("m/s")
                        builder.SINGLESTEP(0.001)

            with builder.GROUP(key="group2", name="Group2 name", desc="Group2 desc"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    with builder.CHILD(key="param21", name="Param21 name", desc="Param21 desc"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(6, min_value=0, max_value=31)

            with builder.GROUP(key="debug", name="Debug", desc="Debug switches"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    with builder.CHILD(key="debug_mode", name="Debug mode",
                                       desc="Enable debug_print() and Trace.log(debug=True) channels"):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(False)

            # 合并保存：已存在则更新属性，不存在则新增
            builder.save(merge=True)
            cls.load_config()

    @classmethod
    def load_config(cls):
        """加载/重载配置参数。"""
        config = script_param.loadConfig()
        cls.param11 = config.get("param11")
        cls.param12 = config.get("param12")
        cls.param21 = config.get("param21")
        cls.debug_mode = bool(config.get("debug_mode", False))
        Trace.log(
            f"config loaded param11={cls.param11} param12={cls.param12} param21={cls.param21} debug_mode={cls.debug_mode}",
            name=f"{MOD}.cfg",
        )


'''参数创建必须在全局作用域中'''
ConfigParams.init()


def script_config_callback():
    """脚本配置参数变更回调。"""
    Trace.log("script config changed", name=f"{MOD}.cfg")
    ConfigParams.load_config()


def robot_device_callback(change_devices: List[str]):
    """机器人设备参数变更回调。"""
    Trace.log(f"robot device changed devices={change_devices}", name=f"{MOD}.cfg")
    for device in change_devices:
        if device == "Model":
            jack_motor = RobotParam.getDevice("Model-000", "moduleType.jackWithSpin.jackMotor")
            Trace.log(f"device Model.jackMotor={jack_motor}", name=f"{MOD}.cfg", debug=True)
            ConfigParams.load_config()


# ============================================================================
# 任务输入参数定义（创建必须在全局作用域）
# ============================================================================
class InputParams:
    """脚本任务输入参数定义"""
    builder = script_param.builderInput()

    with builder.GROUPS():
        with builder.GROUP(key="operation", name="Operation", desc="Operation"):
            builder.TYPE(ParamType.COMBO_BOX)
            builder.REQUIRED(True)

            with builder.CHILDREN():
                with builder.CHILD(key="operation1", name="Operation1 name", desc="Operation1 desc"):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        with builder.CHILD(key="param11", name="Param11 name", desc="Param11 desc"):
                            builder.TYPE(ParamType.FLOAT)
                            builder.REQUIRED(True)
                            builder.MIN_VALUE(0.0)
                            builder.MAX_VALUE(0.06)
                            builder.UNIT("m")
                            builder.SINGLESTEP(0.01)
                            builder.DEFAULTVALUE(0.01)

                with builder.CHILD(key="operation2", name="Operation2 name", desc="Operation2 desc"):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        with builder.CHILD(key="param21", name="Param21 name", desc="Param21 desc"):
                            builder.TYPE(ParamType.FLOAT)
                            builder.MIN_VALUE(0.0)
                            builder.MAX_VALUE(0.06)
                            builder.UNIT("m")
                            builder.SINGLESTEP(0.01)
                            builder.DEFAULTVALUE(0.01)

                with builder.CHILD(key="operation3", name="Operation3 name", desc="Operation3 desc"):
                    builder.TYPE(ParamType.ARRAY)
    builder.save()


# ============================================================================
# 调度动作模板（addAction）
# ============================================================================
script_param.addAction(
    action_name="action1",
    policy={"goodsDir": 90},
    args={
        "operation": "operation1",
        "operation.operation1.param11": 0.02,
    },
    config={"group1.param11": "value"},
)

script_param.addAction(
    action_name="action2",
    policy={"navigation.basic.unload.maxSpeed": 1.0},
    args={
        "operation": "operation2",
        "operation.operation2.param21": 0.04,
    },
    config={"group2.param21": 2},
)

script_param.saveAction()


# ============================================================================
# 示例 Action：模板任务的三个 operation 各对应一个 Action
# ============================================================================
class Operation1Action(ActionBase):
    """演示型 Action：模拟取货动作，50 tick 后完成。
    actionParameters 自动产出 {"param11": ...}（由 ActionBase 基于 __init__ 形参名捕获）。"""

    def __init__(self, param11: float):
        super().__init__()
        self.param11 = float(param11)
        self.target_value = float(param11)
        self.cur_value = 0.0
        self._tick = 0

    def run(self, m):
        self._tick += 1
        # 数值变化只走 chart（在主循环末尾），这里只在边沿事件落 log
        self.cur_value = min(self.target_value, self._tick * self.target_value / 100.0)
        if self._tick >= 50:
            self.cur_value = self.target_value
            self.action_status = ActionStatus.FINISHED

    def result_description(self) -> dict:
        return {"actualValue": self.cur_value}


class Operation2Action(ActionBase):
    """演示型 Action：100 tick 后完成。
    actionParameters 自动产出 {"param21": ...}。"""

    def __init__(self, param21: float):
        super().__init__()
        self.param21 = float(param21)
        self._tick = 0

    def run(self, m):
        self._tick += 1
        if self._tick >= 100:
            self.action_status = ActionStatus.FINISHED


class Operation3Action(ActionBase):
    """演示型 Action：150 tick 后完成，无入参。
    actionParameters 自动产出 {}。"""

    def __init__(self):
        super().__init__()
        self._tick = 0

    def run(self, m):
        self._tick += 1
        if self._tick >= 150:
            self.action_status = ActionStatus.FINISHED


# ============================================================================
# 任务主类
# ============================================================================
class ModuleXXX(ModuleBase):
    """任务脚本主类（按车型重命名，如 Jack / ContainerRobot / Fork ...）。

    与 module/* 的差异：队列状态/事件日志统一委托给 ActionTask，主类只负责：
      - 根据任务参数 _dispatch 出 action 列表
      - 把 self 作为 ctx 传给 queue.step()，供 action 访问模块字段（如 report_info）
      - 主循环末尾统一上报（reportInfo + Trace.chart）
    """

    def __init__(self):
        super().__init__()
        self.args: dict = {}
        self.status = ScriptStatus.NONE
        self.report_info: dict = {}

        # 可复用的 Action 队列（事件日志与队列状态都封装在内部）
        self.action_task = ActionTask(mod=MOD)

        # safeMoveCheck 演示计数
        self._safe_count = 0

        # 初始化单容器位（按车型调整：背篓多容器请按位递增）
        Container.initContainer(1)

    # ----------------------------------------------------------------
    # 参数初始化 & 队列装配
    # ----------------------------------------------------------------
    def init_args(self, args: dict):
        """收到合法任务参数后调用：装配队列并切到 RUNNING。"""
        self.args = args
        operation = args.get("operation")
        Trace.log(f"task start operation={operation} task_id={Module.getTaskId()}", name=MOD)

        actions = []
        """根据 operation 派发：返回该 operation 对应的 action 列表。"""
        if operation == "operation1":
            # 混合装配：Operation1Action 与 Operation3Action 可并行执行
            # 用 (action, "NONE") 元组形式逐项指派 blocking_type，覆盖批默认 HARD
            actions = [
                (Operation1Action(args.get("param11", 0.01)), "NONE"),
                (Operation3Action(), "NONE"),
            ]
        if operation == "operation2":
            actions =  [Operation2Action(args.get("param21", 0.01))]
        if operation == "operation3":
            actions =  [Operation3Action()]

        if not actions:
            Trace.log(f"unsupported operation={operation}", name=f"{MOD}.err")
            self.set_status(ScriptStatus.FAILED)
            return

        self.action_task.build(actions)
        self.set_status(ScriptStatus.RUNNING)

    # ----------------------------------------------------------------
    # 主循环驱动
    # ----------------------------------------------------------------
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

    # ----------------------------------------------------------------
    # 必须实现的回调
    # ----------------------------------------------------------------
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

    # ----------------------------------------------------------------
    # 主循环末尾上报：reportInfo + 集中 Trace.chart
    # ----------------------------------------------------------------
    def tick_report(self):
        """每 tick 调用一次：合并一次 reportInfo + 集中 chart 上报。"""
        cur = self.action_task.current
        counts = self.action_task.status_counts()

        # 调度/Roboshop 上报（合并一次；containers 必须携带）
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

        # ===== Trace.chart：时序采样（参考 docs/guide/spec/logging.md §4.8） =====
        # <MOD>.task：任务级状态分布（key 类型必须稳定）
        Trace.chart(
            {
                "scriptStatus":   int(self.status),
                "total":          int(self.action_task.total),
                "runningCount":   int(counts["running"]),
                "waitingCount":   int(counts["init"]),
                "finishedCount":  int(counts["finished"]),
                "failedCount":    int(counts["failed"]),
                "suspendedCount": int(counts["suspended"]),
            },
            name=f"{MOD}.task",
        )

        # <MOD>.motor：机构状态（按车型替换字段名前缀，如 jack* / ctu* / fork* / clean*）
        cur_value = float(getattr(cur, "cur_value", 0.0) or 0.0)
        target_value = float(getattr(cur, "target_value", 0.0) or 0.0)
        Trace.chart(
            {
                "demoCurrent": cur_value,
                "demoTarget": target_value,
                "demoInPlace": bool(cur and cur.action_status == ActionStatus.FINISHED),
            },
            name=f"{MOD}.motor",
        )


# ============================================================================
# 主入口
# ============================================================================
def main():
    # 注册参数变更回调
    ScriptParam.setConfigChangeCallBack(script_config_callback)
    RobotParam.setDeviceChangeCallBack(robot_device_callback)

    Module.init()
    m = ModuleXXX()

    while True:
        # 1) 同步本地状态到 Module
        Module.setStatus(m.status)

        # 2) 每 tick 上报（reportInfo + Trace.chart）
        m.tick_report()

        # 3) 安全检查事件
        if m.event_safe_move_check:
            m.safeMoveCheck()

        # 4) 状态机驱动
        status = m.status
        if status == ScriptStatus.NONE:
            args = Module.getTaskArgs()
            if args:
                try:
                    args = script_param.loadInput(args)
                    debug_print(f"task args validated: {json.dumps(args, indent=2, ensure_ascii=False)}")
                    m.init_args(args)
                except ValueError as e:
                    # 同一异常只记录一次，含完整上下文
                    Trace.log(f"input params validate failed error={e}", name=f"{MOD}.err")
        elif status == ScriptStatus.RUNNING:
            m.run()
        elif status == ScriptStatus.SUSPENDED:
            m.suspend()
        elif status in (ScriptStatus.FAILED, ScriptStatus.FINISHED):
            # 任务结束：重置队列状态，回到 NONE 等待下一次任务
            m.action_task.reset()
            m.set_status(ScriptStatus.NONE)

        # 控制循环节奏，避免 CPU 飙升
        time.sleep(0.1)


if __name__ == "__main__":
    main()
