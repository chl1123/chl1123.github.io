# -*- coding: utf-8 -*-
# @Date: 2026/02/04
# @Project: 3.5版本任务脚本模板
import time
from enum import IntEnum
from typing import List

start_time = time.time()

from syspy import Module, ModuleBase, ScriptStatus, Trace, RobotParam, ScriptParam
from syspy.lib.module import SafeMoveStatus
from syspy.utils.param_server import ParamType

# 模块标识，用作 Trace 通道后缀：log.tmpl / log.tmpl.cfg / log.tmpl.action / log.tmpl.err
MOD = "tmpl"

# 实例化脚本参数，用于创建和加载脚本配置参数和任务参数
script_param = ScriptParam(__file__)


class ConfigParams:
    """脚本配置参数定义"""
    param11 = None
    param12 = None
    param21 = None

    @classmethod
    def init(cls):
        builder = script_param.builderConfig()
        with builder.GROUPS():
            # 配置组1
            with builder.GROUP(key="group1", name="Group1 name", desc="Group1 desc"):
                builder.TYPE(ParamType.ARRAY)

                with builder.CHILDREN():
                    # 参数11
                    with builder.CHILD(key="param11", name="Param11 name",
                                       desc="param11 desc"):
                        builder.TYPE(ParamType.STRING)

                    # 参数12
                    with builder.CHILD(key="param12", name="Param12 name",
                                       desc="param12 desc"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.015, min_value=0.001, max_value=0.1)
                        builder.UNIT("m/s")
                        builder.SINGLESTEP(0.001)

            # 配置组2
            with builder.GROUP(key="group2", name="Group2 name", desc="Group2 desc"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    # 参数11
                    with builder.CHILD(key="param21", name="Param21 name",
                                       desc="Param21 desc"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(6, min_value=0, max_value=31)
            # 保存配置参数，和原参数文件合并
            """
            合并策略：
            如果参数已经存在，则更新属性（名称、描述、类型等）
            如果参数不存在，则增加
            """
            builder.save(merge=True)

            cls.load_config()

    @classmethod
    def load_config(cls):
        """重新加载配置参数"""
        config = script_param.loadConfig()
        Trace.log(
            f"config loaded param11={config.get('param11')} "
            f"param12={config.get('param12')} param21={config.get('param21')}",
            name=f"{MOD}.cfg",
        )
        cls.param11 = config.get("param11")
        cls.param12 = config.get("param12")
        cls.param21 = config.get("param21")


'''参数创建必须在全局作用域中'''
ConfigParams.init()


def script_config_callback():
    """脚本配置参数修改回调，脚本配置修改时会调用"""
    Trace.log("config change detected", name=f"{MOD}.cfg")
    ConfigParams.load_config()


def robot_device_callback(change_devices: List[str]):
    """机器人设备参数修改回调，设备参数修改时会调用

    Args:
        change_devices: 被修改的设备类型
    """
    Trace.log(f"device change detected, {change_devices=}", name=f"{MOD}.cfg")
    for device in change_devices:
        if device == "Model":
            jackMotor = RobotParam.getDevice("Model-000", "moduleType.jackWithSpin.jackMotor")
            Trace.log(f"device reloaded Model-000 jackMotor={jackMotor}", name=f"{MOD}.cfg")
            ConfigParams.load_config()


'''参数创建必须在全局作用域中'''
class InputParams:
    """脚本任务输入参数定义（参数创建必须放到全局作用域中）"""
    builder = script_param.builderInput()

    with builder.GROUPS():
        # COMBO_BOX类型的参数，支持多个operation
        with builder.GROUP(key="operation", name="Operation", desc="Operation"):
            builder.TYPE(ParamType.COMBO_BOX)
            builder.REQUIRED(True)

            with builder.CHILDREN():
                # operation1
                with builder.CHILD(key="operation1", name="Operation1 name", desc="Operation1 desc"):
                    builder.TYPE(ParamType.ARRAY)

                    with builder.CHILDREN():
                        # operation1的参数param11
                        with builder.CHILD(key="param11", name="Param11 name",
                                           desc="Param11 name"):
                            builder.TYPE(ParamType.FLOAT)
                            builder.REQUIRED(True)  # 必填（仅在operation1时必填）
                            builder.MIN_VALUE(0.0)
                            builder.MAX_VALUE(0.06)
                            builder.UNIT("m")
                            builder.SINGLESTEP(0.01)
                            builder.DEFAULTVALUE(0.01)

                # operation2
                with builder.CHILD(key="operation2", name="Operation2 name", desc="Operation2 desc"):
                    builder.TYPE(ParamType.ARRAY)

                    with builder.CHILDREN():
                        # operation2的参数param21
                        with builder.CHILD(key="param21", name="Param21 name",
                                           desc="Param21 name"):
                            builder.TYPE(ParamType.FLOAT)
                            builder.MIN_VALUE(0.0)
                            builder.MAX_VALUE(0.06)
                            builder.UNIT("m")
                            builder.SINGLESTEP(0.01)
                            builder.DEFAULTVALUE(0.01)

                # operation3
                with builder.CHILD(key="operation3", name="Operation3 name", desc="Operation3 desc"):
                    builder.TYPE(ParamType.ARRAY)
    # 保存脚本任务输入参数
    builder.save()


# 添加 "action1" 动作
script_param.addAction(
    action_name="action1",
    policy={"goodsDir": 90},
    args={
        "operation": "operation1",
        "operation.operation1.param11": 0.02,
    },
    config={"group1.param11": "value"}
)

# 添加 "action2" 动作
script_param.addAction(
    action_name="action2",
    policy={"navigation.basic.unload.maxSpeed": 1.0},
    args={
        "operation": "operation2",
        "operation.operation2.param21": 0.04,
    },
    config={"group2.param21": 2}
)

# 保存动作
script_param.saveAction()


# ============================================================================
# Action 基础设施（与 tasks/v3/standard/module/ 下标准脚本保持一致）
# ============================================================================
class ActionStatus(IntEnum):
    """动作运行状态枚举"""
    INIT = 0
    RUNNING = 1
    FINISHED = 3
    FAILED = 4


class BaseAction:
    """动作基类；子类在 run() 中推进 self.action_status 为 FINISHED / FAILED。"""

    def __init__(self, action_name: str = None, args: dict = None):
        self.action_name = action_name or self.__class__.__name__
        self.args = args or {}
        self.action_status = ActionStatus.INIT
        self.fail_reason = ""

    def run(self, m):
        """子类实现具体动作逻辑。"""
        pass

    def reset(self):
        self.action_status = ActionStatus.INIT


class Op1Action(BaseAction):
    """operation1：单动作示例，到 tick 阈值后完成。"""

    def __init__(self, param11: float):
        super().__init__("Op1", {"param11": param11})
        self.param11 = param11
        self._tick = 0

    def run(self, m):
        self.action_status = ActionStatus.RUNNING
        self._tick += 1
        if self._tick >= 100:
            self.action_status = ActionStatus.FINISHED


class Op2PrepareAction(BaseAction):
    """operation2 的前置准备动作。"""

    def __init__(self):
        super().__init__("Op2Prepare")
        self._tick = 0

    def run(self, m):
        self.action_status = ActionStatus.RUNNING
        self._tick += 1
        if self._tick >= 100:
            self.action_status = ActionStatus.FINISHED


class Op2Action(BaseAction):
    """operation2：主动作；与前置动作组成二段队列。"""

    def __init__(self, param21: float):
        super().__init__("Op2", {"param21": param21})
        self.param21 = param21
        self._tick = 0

    def run(self, m):
        self.action_status = ActionStatus.RUNNING
        self._tick += 1
        if self._tick >= 300:
            self.action_status = ActionStatus.FINISHED


class Op3Action(BaseAction):
    """operation3：完成后触发动态追加（见 ModuleXXX.run 中的 queue_extend 分支）。"""

    def __init__(self):
        super().__init__("Op3")
        self._tick = 0

    def run(self, m):
        self.action_status = ActionStatus.RUNNING
        self._tick += 1
        if self._tick >= 200:
            self.action_status = ActionStatus.FINISHED


class Op3FollowUpAction(BaseAction):
    """operation3 动态追加的收尾动作。"""

    def __init__(self):
        super().__init__("Op3FollowUp")
        self._tick = 0

    def run(self, m):
        self.action_status = ActionStatus.RUNNING
        self._tick += 1
        if self._tick >= 100:
            self.action_status = ActionStatus.FINISHED


# ============================================================================
# 脚本任务主类
# ============================================================================
class ModuleXXX(ModuleBase):
    """任务脚本主类，类名可自定义"""

    def __init__(self):
        super().__init__()
        self.count = 0
        self.report_info = {}
        self.args = {}
        self.status = ScriptStatus.NONE

        # 动作队列
        self.opt = None
        self.action_list: List[BaseAction] = []
        self.action_id = 0
        self.operation_init = False

        # 队列事件状态
        self._queue_start_ts = 0.0
        self._action_start_ts = 0.0
        self._last_started_id = -1
        self._queue_done_logged = False
        self._op3_extended = False

    # ----- 参数初始化 -----
    def init_args(self, args):
        """初始化任务参数"""
        self.args = args
        self.opt = args.get("operation")
        if args:
            self.status = ScriptStatus.RUNNING
            Trace.log(
                f"status NONE -> RUNNING taskId={Module.getTaskId()} operation={self.opt}",
                name=MOD,
            )

    # ----- 队列生命周期 -----
    def _reset_queue(self):
        """单次任务结束/取消时清空队列状态，供下一个任务复用。"""
        self.action_list = []
        self.action_id = 0
        self.operation_init = False
        self._last_started_id = -1
        self._queue_done_logged = False
        self._op3_extended = False

    def _emit_queue_build(self):
        """在 action_list 装配完成后调用一次，发 queue_build 事件。"""
        self._queue_start_ts = time.time()
        Trace.log(
            {
                "event":   "queue_build",
                "total":   len(self.action_list),
                "actions": [
                    {"id": i, "name": a.action_name, "args": a.args}
                    for i, a in enumerate(self.action_list)
                ],
            },
            name=f"{MOD}.action",
        )

    def _extend_queue(self, new_actions: List[BaseAction], at: int = None):
        """动态追加/插入动作；默认追加到尾部。"""
        at = len(self.action_list) if at is None else at
        self.action_list[at:at] = new_actions
        Trace.log(
            {
                "event":    "queue_extend",
                "at":       at,
                "appended": [
                    {"id": at + k, "name": a.action_name, "args": a.args}
                    for k, a in enumerate(new_actions)
                ],
                "total":    len(self.action_list),
            },
            name=f"{MOD}.action",
        )

    def _emit_queue_done(self, status_name: str, failed_at: int = None):
        if self._queue_done_logged:
            return
        evt = {
            "event":     "queue_done",
            "total":     len(self.action_list),
            "elapsedMs": int((time.time() - self._queue_start_ts) * 1000),
            "status":    status_name,
        }
        if failed_at is not None:
            evt["failedAt"] = failed_at
        Trace.log(evt, name=f"{MOD}.action")
        self._queue_done_logged = True

    # ----- operation 构建 -----
    def operation1(self, param11: float):
        """operation1：单动作队列。"""
        if not self.operation_init:
            self.operation_init = True
            self.action_list.append(Op1Action(param11))
            self._emit_queue_build()

    def operation2(self, param21: float):
        """operation2：两段式队列，示例多动作队列。"""
        if not self.operation_init:
            self.operation_init = True
            self.action_list.append(Op2PrepareAction())
            self.action_list.append(Op2Action(param21))
            self._emit_queue_build()

    def operation3(self):
        """operation3：初始一个动作，第一个动作完成后动态追加——示例 queue_extend。"""
        if not self.operation_init:
            self.operation_init = True
            self.action_list.append(Op3Action())
            self._emit_queue_build()

    # ----- 分发与推进 -----
    def run(self):
        """分发、执行任务"""
        self.status = ScriptStatus.RUNNING
        self.count += 1
        self.report_info["taskId"] = Module.getTaskId()
        self.report_info["args"] = self.args
        self.report_info["count"] = self.count
        self.report_info["taskTime"] = round(time.time() - start_time, 2)

        # 按 operation 装配队列（第一次进入时）
        if self.opt == "operation1":
            self.operation1(self.args.get("param11", 0.01))
        elif self.opt == "operation2":
            self.operation2(self.args.get("param21", 0.01))
        elif self.opt == "operation3":
            self.operation3()
        else:
            Trace.log(f"unknown operation operation={self.opt}", name=f"{MOD}.err")
            self.status = ScriptStatus.FAILED
            return

        # operation3 专属：第一个动作完成后动态追加收尾动作（示例 queue_extend）
        if self.opt == "operation3" and not self._op3_extended \
                and self.action_list and self.action_list[0].action_status == ActionStatus.FINISHED:
            self._op3_extended = True
            self._extend_queue([Op3FollowUpAction()])

        # 推进队列
        self._execute_actions()

    def _execute_actions(self):
        """统一的队列推进：负责派发 action_start / action_done / action_fail / queue_done。"""
        if self.action_id >= len(self.action_list):
            self._emit_queue_done("FINISHED")
            self.status = ScriptStatus.FINISHED
            return

        cur = self.action_list[self.action_id]

        # 每个 id 在首次进入时发 action_start
        if self._last_started_id != self.action_id:
            self._action_start_ts = time.time()
            Trace.log(
                {
                    "event": "action_start",
                    "id":    self.action_id,
                    "total": len(self.action_list),
                    "name":  cur.action_name,
                    "args":  cur.args,
                },
                name=f"{MOD}.action",
            )
            self._last_started_id = self.action_id

        if cur.action_status == ActionStatus.FINISHED:
            Trace.log(
                {
                    "event":     "action_done",
                    "id":        self.action_id,
                    "total":     len(self.action_list),
                    "name":      cur.action_name,
                    "elapsedMs": int((time.time() - self._action_start_ts) * 1000),
                },
                name=f"{MOD}.action",
            )
            self.action_id += 1
            return

        if cur.action_status == ActionStatus.FAILED:
            Trace.log(
                {
                    "event":     "action_fail",
                    "id":        self.action_id,
                    "total":     len(self.action_list),
                    "name":      cur.action_name,
                    "elapsedMs": int((time.time() - self._action_start_ts) * 1000),
                    "reason":    cur.fail_reason or "unknown",
                },
                name=f"{MOD}.action",
            )
            self._emit_queue_done("FAILED", failed_at=self.action_id)
            self.status = ScriptStatus.FAILED
            return

        cur.run(self)

    # ----- 暂停 / 恢复 / 取消 -----
    def suspend(self):
        """暂停任务方法（必须）：导航暂停时如果脚本任务状态为RUNNING会调用该方法"""
        if Module.getStatus() == ScriptStatus.RUNNING:
            self.status = ScriptStatus.SUSPENDED
            Trace.log("status RUNNING -> SUSPENDED", name=MOD)

    def resume(self):
        """恢复任务方法（必须）：导航恢复时如果脚本任务状态为SUSPENDED会调用该方法"""
        if Module.getStatus() == ScriptStatus.SUSPENDED:
            self.status = ScriptStatus.RUNNING
            Trace.log("status SUSPENDED -> RUNNING", name=MOD)

    def cancel(self):
        """取消任务方法（必须）：导航取消时如果脚本任务状态为RUNNING或SUSPENDED会调用该方法"""
        Trace.log("cancel triggered -> FAILED", name=MOD)
        # 若队列还有未结束动作，补一条 action_fail + queue_done 让分析器状态一致
        if self.action_id < len(self.action_list) and not self._queue_done_logged:
            cur = self.action_list[self.action_id]
            Trace.log(
                {
                    "event":     "action_fail",
                    "id":        self.action_id,
                    "total":     len(self.action_list),
                    "name":      cur.action_name,
                    "elapsedMs": int((time.time() - self._action_start_ts) * 1000),
                    "reason":    "cancelled",
                },
                name=f"{MOD}.action",
            )
            self._emit_queue_done("FAILED", failed_at=self.action_id)
        self.status = ScriptStatus.FAILED

    def safeMoveCheck(self):
        """底盘移动前安全检查（可选）"""
        self.count += 1
        status = SafeMoveStatus.RUNNING
        # 假设当count达到100时，安全检查完成
        if self.count == 100:
            self.count = 0
            status = SafeMoveStatus.FINISHED
        # 上报安全检查状态
        self.setSafeMoveStatus(status)
        # 安全检查结束为边沿事件
        if status == SafeMoveStatus.FAILED or status == SafeMoveStatus.FINISHED:
            Trace.log(f"safe_move_check done status={status.name}", name=MOD)
            self.event_safe_move_check = False


def main():
    # 注册脚本参数变更回调
    ScriptParam.setConfigChangeCallBack(script_config_callback)
    # 注册设备参数变更回调
    RobotParam.setDeviceChangeCallBack(robot_device_callback)

    Module.init()

    # 实例化脚本任务主类
    m = ModuleXXX()

    while True:
        # 脚本任务状态管理
        status = m.status
        # 上报脚本任务状态
        Module.setStatus(status)
        m.report_info["status"] = status
        m.report_info["totalTime"] = round(time.time() - start_time, 2)
        # 上报信息
        Module.reportInfo(m.report_info)

        # 触发安全检查事件（底盘移动时），执行安全检查
        if m.event_safe_move_check:
            m.safeMoveCheck()
        if status == ScriptStatus.NONE:  # 任务状态为NONE时，获取任务参数
            # 获取 3051、3066 API 指令中的 "scriptArgs" 的值
            args = Module.getTaskArgs()
            # 有任务参数时，验证、初始化参数
            if args:
                try:
                    # 校验参数, 解析为不带.的参数
                    args = script_param.loadInput(args)
                    Trace.log(f"task args accepted args={args}", name=MOD)
                    # 初始化参数，成功时设置任务状态为RUNNING
                    m.init_args(args)
                except ValueError as e:
                    # 参数验证失败，比如参数字段、类型、范围错误
                    Trace.log(f"task args invalid error={e} raw={args}", name=f"{MOD}.err")
        elif status == ScriptStatus.RUNNING:  # 任务状态为RUNNING时，执行任务
            m.run()
        elif status == ScriptStatus.SUSPENDED:  # 任务状态为SUSPENDED时，暂停任务
            m.suspend()
        elif status in (ScriptStatus.FAILED, ScriptStatus.FINISHED):  # 任务结束，回到 NONE 等待下一单
            Trace.log(f"status {status.name} -> NONE", name=MOD)
            m._reset_queue()
            m.status = ScriptStatus.NONE

        # tick 级状态走 chart：分析器用 log.tmpl.action 事件重建队列，
        # chart 则给出随时间变化的进度曲线
        Trace.chart(
            {
                "scriptStatus":   int(m.status),
                "actionId":       m.action_id,
                "actionTotal":    len(m.action_list),
                "curActionState": (
                    int(m.action_list[m.action_id].action_status)
                    if 0 <= m.action_id < len(m.action_list) else 0
                ),
            },
            name=f"{MOD}.task",
        )

        """需要增加sleep，如果时间太短控制器增加CPU占用"""
        time.sleep(0.1)


if __name__ == '__main__':
    main()
