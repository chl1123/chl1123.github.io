# -*- coding: utf-8 -*-
# @Date: 2026/02/04
# @Project: 3.5版本任务脚本模板
import json
import time

start_time = time.time()
from typing import List
from syspy import Module, ModuleBase, ScriptStatus, Trace, RobotParam, ScriptParam
from syspy.lib.module import SafeMoveStatus
from syspy.utils.param_server import ParamType

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
                        builder.REQUIRED(True)

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
        Trace.log(f"Loaded config: {config}")
        cls.param11 = config.get("param11")
        cls.param12 = config.get("param12")
        cls.param21 = config.get("param21")


'''参数创建必须在全局作用域中'''
ConfigParams.init()


def script_config_callback():
    """脚本配置参数修改回调，脚本配置修改时会调用"""
    Trace.log("script_config_callback()")
    ConfigParams.load_config()


def robot_device_callback(change_devices: List[str]):
    """机器人设备参数修改回调，设备参数修改时会调用

    Args:
        change_devices: 被修改的设备类型
    """
    Trace.log(f"robot_device_callback({change_devices})")
    for device in change_devices:
        if device == "Model":
            jackMotor = RobotParam.getDevice("Model-000", "moduleType.jackWithSpin.jackMotor")
            Trace.log(f"{jackMotor=}")
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


class ModuleXXX(ModuleBase):
    """任务脚本主类，类名可自定义"""

    def __init__(self):
        super().__init__()
        self.count = 0
        self.report_info = {}
        self.args = {}
        self.status = ScriptStatus.NONE

    def init_args(self, args):
        """初始化任务参数"""
        self.args = args
        if args:
            self.status = ScriptStatus.RUNNING
        ...

    def run(self):
        """分发、执行任务"""
        self.status = ScriptStatus.RUNNING
        self.count += 1
        self.report_info["taskId"] = Module.getTaskId()
        self.report_info["args"] = self.args
        self.report_info["count"] = self.count
        self.report_info["taskTime"] = round(time.time() - start_time, 2)
        operation = self.args.get('operation', None)
        if operation == "operation1":
            param11 = self.args.get('param11', 0.01)
            self.operation1(param11)
        elif operation == "operation2":
            param21 = self.args.get('param21', 0.01)
            self.operation2(param21)
        elif operation == "operation3":
            self.operation3()
        else:
            self.status = ScriptStatus.FAILED

    def operation1(self, param11: float):
        """任务操作1"""
        Trace.log(f"operation1({param11})")
        # 假设当count达到100时，任务完成
        if self.count == 100:
            self.status = ScriptStatus.FINISHED
            Trace.log("operation1 finished")
            self.count = 0
        ...

    def operation2(self, param21: float = 0.01):
        """任务操作2"""
        Trace.log(f"operation2({param21})")
        # 假设当count达到400时，任务完成
        if self.count == 400:
            self.status = ScriptStatus.FINISHED
            Trace.log("operation2 finished")
            self.count = 0
        ...

    def operation3(self):
        """任务操作3"""
        Trace.log("operation3()")
        # 假设当count达到500时，任务完成
        if self.count == 500:
            self.status = ScriptStatus.FINISHED
            self.count = 0
        ...

    def suspend(self):
        """暂停任务方法（必须）：导航暂停时如果脚本任务状态为RUNNING会调用该方法"""
        if Module.getStatus() == ScriptStatus.RUNNING:
            self.status = ScriptStatus.SUSPENDED
        Trace.log("suspend")

    def resume(self):
        """恢复任务方法（必须）：导航恢复时如果脚本任务状态为SUSPENDED会调用该方法"""
        if Module.getStatus() == ScriptStatus.SUSPENDED:
            self.status = ScriptStatus.RUNNING
        Trace.log("resume")

    def cancel(self):
        """取消任务方法（必须）：导航取消时如果脚本任务状态为RUNNING或SUSPENDED会调用该方法"""
        self.status = ScriptStatus.FAILED
        Trace.log("cancel")

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
        Trace.log(f"safe_move_check {Module.getSafeMoveCheck()}")
        # 安全检查结束，恢复事件状态event_safe_move_check
        if status == SafeMoveStatus.FAILED or status == SafeMoveStatus.FINISHED:
            self.event_safe_move_check = False


def main():
    Module.init()

    # 注册脚本参数变更回调
    ScriptParam.setConfigChangeCallBack(script_config_callback)
    # 注册设备参数变更回调
    RobotParam.setDeviceChangeCallBack(robot_device_callback)

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
                    print("args", args)
                    # 校验参数, 解析为不带.的参数
                    args = script_param.loadInput(args)
                    print("check ok, args:", json.dumps(args, indent=2))
                    # 初始化参数，成功时设置任务状态为RUNNING
                    m.init_args(args)
                except ValueError as e:
                    # 参数验证失败，比如参数字段、类型、范围错误
                    print("check error:", e)
        elif status == ScriptStatus.RUNNING:  # 任务状态为RUNNING时，执行任务
            m.run()
        elif status == ScriptStatus.SUSPENDED:  # 任务状态为SUSPENDED时，暂停任务
            m.suspend()
        elif status in (ScriptStatus.FAILED, ScriptStatus.FINISHED):  # 任务状态为FAILED或FINISHED时，任务结束，设置任务状态为NONE
            m.status = ScriptStatus.NONE

        """需要增加sleep，如果时间太短控制器增加CPU占用"""
        time.sleep(0.1)


if __name__ == '__main__':
    main()
