# -*- coding: utf-8 -*-
# @Date: 2025/10/22
# @Project: 3.5版本脚本配置参数和任务参数示例
import json
import time
from typing import List

start_time = time.time()

from syspy import Module, ModuleBase, ScriptStatus, Navigation, Trace, RobotParam
from syspy.utils.param_server import ParamType, ScriptParam
param_loader = ScriptParam(__file__)


class ConfigParams:
    config = {}
    """配置管理器，用于管理动态配置参数"""
    jack_motor_name = None
    jack_motor_speed = None
    jack_lift_zero = None

    jack_up_di = None
    jack_zero_di = None

    def __init__(self):
        self._build_and_load_config()

    @classmethod
    def _build_and_load_config(cls):
        """构建并加载配置参数"""
        builder = param_loader.builder_config()

        with builder.GROUPS():
            # 电机配置组
            with builder.GROUP(key="motorConfig", name="Motor Configuration",
                               desc="Motor related configuration parameters"):
                builder.TYPE(ParamType.ARRAY)

                with builder.CHILDREN():
                    # 顶升电机名称
                    with builder.CHILD(key="jackMotorName", name="Jack Motor Name",
                                       desc="Name of the jack motor"):
                        builder.TYPE(ParamType.STRING)
                        builder.DEFAULTVALUE("Motor_001")
                        builder.REQUIRED(True)

                    # 顶升电机速度
                    with builder.CHILD(key="jackMotorSpeed", name="Jack Motor Speed",
                                       desc="Speed of the jack motor"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.015, min_value=0.001, max_value=0.1)
                        builder.UNIT("m/s")
                        builder.SINGLESTEP(0.001)

                    # 顶升零位
                    with builder.CHILD(key="jackLiftZero", name="Jack Lift Zero",
                                       desc="Zero position for jack lift"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.000)
                        builder.UNIT("m")

            # DI配置组
            with builder.GROUP(key="diConfig", name="DI Configuration", desc="Digital input configuration parameters"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    # 上极限DI
                    with builder.CHILD(key="jackUpDi", name="Jack Up DI",
                                       desc="Upper limit digital input for jack"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(6, min_value=0, max_value=31)

                    # 零位DI
                    with builder.CHILD(key="jackZeroDi", name="Jack Zero DI",
                                       desc="Zero position digital input for jack"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(3, min_value=0, max_value=31)

        builder.save(merge=True)
        cls.reload_config()

    @classmethod
    def reload_config(cls):
        """重新加载配置参数"""
        Trace.log("Reloading config parameters")
        cls.config = param_loader.load_config()
        Trace.log(f"Loaded config: {cls.config}")
        cls.jack_motor_name = cls.config.get("jackMotorName")
        cls.jack_motor_speed = cls.config.get("jackMotorSpeed")
        cls.jack_lift_zero = cls.config.get("jackLiftZero")

        cls.jack_up_di = cls.config.get("jackUpDi")
        cls.jack_zero_di = cls.config.get("jackZeroDi")
        Trace.log(f"Updated config: {cls.config}")


# 创建全局配置管理器实例
config_params = ConfigParams()

def script_config_callback():
    Trace.log("Reloading script config parameters")
    config_params.reload_config()


def params_callback(device_change_set: List[str]):
    Trace.log(f"{device_change_set=}")
    for device in device_change_set:
        if device == "Model":
            config_params.reload_config()


# 创建可复用的 jack_height 参数
def create_jack_height_param(builder):
    """创建顶升高度参数（可复用）"""
    with builder.CHILD(key="height", name="Jacking height",
                       desc="The height for lift operations"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(True)
        builder.MIN_VALUE(0.0)
        builder.MAX_VALUE(0.06)
        builder.UNIT("m")
        builder.SINGLESTEP(0.01)
        builder.DEFAULTVALUE(0.01)


class InputParams:
    builder = param_loader.builder_input()

    with builder.GROUPS():
        create_jack_height_param(builder)
        # 顶升操作组合框
        with builder.GROUP(key="operation", name="Lift Operations", desc="Lift Task script input parameters"):
            builder.TYPE(ParamType.COMBO_BOX)
            builder.REQUIRED(True)

            with builder.CHILDREN():
                # load操作
                with builder.CHILD(key="load", name="Load Operation", desc="Lift the robot tray"):
                    builder.TYPE(ParamType.ARRAY)

                    with builder.CHILDREN():
                        # 顶升高度参数
                        create_jack_height_param(builder)

                # unload操作
                with builder.CHILD(key="unload", name="Unload Operation",
                                   desc="Lower the robot tray"):
                    builder.TYPE(ParamType.ARRAY)

                    with builder.CHILDREN():
                        # 顶升高度参数
                        with builder.CHILD(key="unloadHeight", name="Jacking height",
                                           desc="The height for lift operations"):
                            builder.TYPE(ParamType.FLOAT)
                            builder.REQUIRED(True)
                            builder.MIN_VALUE(0.0)
                            builder.MAX_VALUE(0.06)
                            builder.UNIT("m")
                            builder.SINGLESTEP(0.01)
                            builder.DEFAULTVALUE(0.01)

                # spin
                with builder.CHILD(key="spin", name="Spin Operation", desc="Spin the robot"):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        with builder.CHILD(key="spinAngle", name="Spin Angle",
                                           desc="Spin angle"):
                            builder.TYPE(ParamType.FLOAT)
                            # builder.REQUIRED(True)
                            builder.UNIT("度")
                            builder.SINGLESTEP(1)

                        # COMBO_BOX参数
                        with builder.CHILD(key="spinType", name="Load type"):
                            builder.TYPE(ParamType.COMBO_BOX)
                            # builder.REQUIRED(True)

                            with builder.CHILDREN():
                                with builder.CHILD(key="loadType1", name="Load Type 1"):
                                    builder.TYPE(ParamType.ARRAY)
                                    with builder.CHILDREN():
                                        with builder.CHILD(key="loadType11", name="Load Type 11"):
                                            builder.TYPE(ParamType.STRING_COMBO_LIST)
                                            builder.DEFAULTVALUE("Option 1")

                                            with builder.CHILDREN():
                                                with builder.CHILD(key="Option 1", name="Option 1"):
                                                    builder.TYPE(ParamType.STRING)

                                                with builder.CHILD(key="Option 2", name="Option 2"):
                                                    builder.TYPE(ParamType.STRING)

                                with builder.CHILD(key="loadType2", name="Load Type 2"):
                                    builder.TYPE(ParamType.ARRAY)
                                    with builder.CHILDREN():
                                        # 使用外部IMU组合框
                                        with builder.CHILD(key="useExternIMU", name="Using Extern IMU",
                                                           desc="using Extern IMU"):
                                            builder.TYPE(ParamType.COMBO_BOX_BOOL)
                                            builder.DEFAULTVALUE(0)

                                            with builder.CHILDREN():
                                                # OFF选项
                                                with builder.CHILD(key="OFF", name="Using SRC IMU",
                                                                   desc="using SRC IMU"):
                                                    builder.TYPE(ParamType.ARRAY)

                                                    with builder.CHILDREN():
                                                        # IMU字符串测试
                                                        with builder.CHILD(key="IMU", name="IMU string test",
                                                                           desc="IMU test"):
                                                            builder.TYPE(ParamType.STRING)
                                                            builder.REQUIRED(True)
                                                            builder.DEFAULTVALUE("test")

                                                # ON选项
                                                with builder.CHILD(key="ON", name="Using Extern IMU",
                                                                   desc="using extern IMU"):
                                                    builder.TYPE(ParamType.ARRAY)

                        with builder.CHILD("spinList", name="Spin list", desc="Spin list"):
                            builder.TYPE(ParamType.STRING_COMBO_LIST)
                            builder.DEFAULTVALUE(0)

                            with builder.CHILDREN():
                                with builder.CHILD("a0", "Name a0", "name a0"):
                                    builder.TYPE(ParamType.STRING)
                                with builder.CHILD("b1", "Name b0", "name b0"):
                                    builder.TYPE(ParamType.STRING)
                                with builder.CHILD("c2", "Name c0", "name c0"):
                                    builder.TYPE(ParamType.STRING)

                with builder.CHILD(key="getCurrentPathProperty", name="Get Current Path Property",
                                   desc="Get current path property"):
                    builder.TYPE(ParamType.ARRAY)
    builder.save()


class Jack(ModuleBase):
    def __init__(self):
        super().__init__()
        self.opt = None
        self.height = 0.03
        self.spin_angle = 0
        self.init_path = True
        self.init_odo = True
        self.go_path_x = 0
        self.go_path_y = 0
        self.go_path_a = 0
        self.count = 0
        self.report_info = {}
        self.args = {}
        self.status = ScriptStatus.NONE

    def reset(self):
        self.spin_angle = 0
        self.init_path = True
        self.init_odo = True
        self.go_path_x = 0
        self.go_path_y = 0
        self.go_path_a = 0

    def init_args(self, args):
        self.args = args
        if args:
            self.status = ScriptStatus.RUNNING
        ...

    def run(self):
        self.status = ScriptStatus.RUNNING
        self.count += 1
        self.report_info["args"] = self.args
        self.report_info["count"] = self.count
        self.report_info["run_time"] = round(time.time() - start_time, 2)
        self.opt = self.args.get('operation', None)
        self.height = self.args.get('height', None)
        Trace.log(f"{self.opt}")
        if self.opt == "load":
            self.load()
        elif self.opt == "spin":
            self.spin_angle = self.args.get('spinAngle', None)
            self.spin()
        elif self.opt == "getCurrentPathProperty":
            self.getCurrentPathProperty()
        else:
            self.status = ScriptStatus.FAILED

    def load(self):
        Trace.log("load start")
        if self.count == 500:
            self.status = ScriptStatus.FINISHED
            self.count = 0

    def spin(self):
        Trace.log(f"spin: {self.spin_angle}")
        Navigation.setRobotSpinAngle(self.spin_angle, 0)
        finished = Navigation.spinRun()
        if finished:
            Trace.log("spin finish")
            self.status = ScriptStatus.FINISHED
        return Module.get_status()

    def getCurrentPathProperty(self):
        Trace.log("getCurrentPathProperty")
        if self.count == 100000:
            self.status = ScriptStatus.FINISHED
            self.count = 0

    def print_info(self):
        # 打印当前任务id、任务状态、任务指令
        Trace.log(f"task_id={Module.get_task_id()}, status={Module.get_status()}, args={self.args}")
        print(f"{config_params.jack_motor_name=}")
        print(f"{config_params.jack_motor_speed=}")
        print(f"{config_params.jack_lift_zero=}")
        print(f"{config_params.jack_zero_di=}")
        print(f"{config_params.jack_up_di=}")
        Module.report_info(self.report_info)

    def suspend(self):
        self.status = ScriptStatus.SUSPENDED
        Trace.log("suspend")

    def resume(self):
        if Module.get_status() == ScriptStatus.SUSPENDED:
            self.status = ScriptStatus.RUNNING
        Trace.log("resume")

    def cancel(self):
        self.status = ScriptStatus.FAILED
        Trace.log("cancel")


def main():
    # 注册脚本参数变更回调
    ScriptParam.setConfigChangeCallBack(script_config_callback)
    # 注册设备参数变更回调
    RobotParam.setDeviceChangeCallBack(params_callback)

    print(1)
    Module.init()
    print("main")

    j = Jack()

    while True:
        # 脚本任务状态管理
        status = j.status
        print("status", status)
        Module.set_status(status)
        j.report_info["status"] = status
        j.print_info()
        if status == ScriptStatus.NONE:
            args = Module.get_task_args()
            if args:
                try:
                    # 验证参数
                    print("args", args)
                    args = param_loader.load_input(args)
                    print("check ok, args:", json.dumps(args, indent=2))
                except ValueError as e:
                    print("check error:", e)
            j.init_args(args)
        elif status == ScriptStatus.RUNNING:
            j.run()
        elif status == ScriptStatus.SUSPENDED:
            j.suspend()
        elif status in (ScriptStatus.FAILED, ScriptStatus.FINISHED):
            j.status = ScriptStatus.NONE

        time.sleep(5)


if __name__ == '__main__':
    main()
