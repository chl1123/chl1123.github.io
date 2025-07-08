import json
import time
start_time = time.time()
from syspy import Logger, Module, ScriptStatus
from syspy.utils.param_server import ParamBuilder, ParamType, ParamValidator, ParamServer

log = Logger("example_input_param")


class ConfigParams:
    param_server = ParamServer(__file__)
    jack_motor_name = param_server.loadParam("jack_motor_name", type="str", default="Motor-003", comment="顶升电机名称")
    jack_motor_speed = param_server.loadParam("jack_motor_speed", type="float", default=0.015,
                                              comment="顶升电机升降速度")
    jack_lift_zero = param_server.loadParam("jack_lift_zero", type="float", default=0.000, comment="顶升升降零位")

    jack_up_di = param_server.loadParam("jack_up_di", type="int", default=6, comment="顶升机构上极限DI")
    jack_zero_di = param_server.loadParam("jack_zero_di", type="int", default=3, comment="顶升机构零位DI")
    log.debug(f"{param_server.data=}")


# 创建可复用的 jack_height 参数
def create_jack_height_param(builder: ParamBuilder):
    """创建顶升高度参数（可复用）"""
    with builder.CHILD(key="jack_height", name="Jacking height",
                      desc="The height for lift operations"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(True)
        builder.MIN_VALUE(0.0)
        builder.MAX_VALUE(0.06)
        builder.UNIT("m")
        builder.SINGLESTEP(0.01)
        builder.DEFAULTVALUE(0.01)

# 生成指定的JSON配置
class InputParams:
    builder = ParamBuilder(__file__, desc="Input Params Config")

    with builder.GROUPS():
        # 公共参数:
        # 使用PGV参数
        with builder.CHILD(key="use_pgv", name="Use PGV", desc="Use PGV for position adjustment"):
            builder.TYPE(ParamType.BOOL)
            builder.DEFAULTVALUE(False)

        # Modbus IP参数
        with builder.CHILD(key="modbus_ip", name="Modbus IP", desc="Modbus TCP IP"):
            builder.TYPE(ParamType.IP)
            builder.DEFAULTVALUE("192.168.192.6")

        # 顶升操作组合框
        with builder.GROUP(key="operation", name="Lift Operations", desc="Lift Task script input parameters"):
            builder.TYPE(ParamType.COMBO_BOX)

            with builder.CHILDREN():
                # JackLoad操作
                with builder.CHILD(key="JackLoad", name="Load Operation", desc="Lift the robot tray"):
                    builder.TYPE(ParamType.ARRAY)

                    with builder.CHILDREN():
                        # 顶升高度参数
                        create_jack_height_param(builder)

                        # 识别参数
                        with builder.CHILD(key="recognize", name="Shelf leg identification",
                                           desc="Enable shelf leg recognition"):
                            builder.TYPE(ParamType.BOOL)
                            builder.DEFAULTVALUE(False)

                # JackUnload操作
                with builder.CHILD(key="JackUnload", name="Unload Operation",
                                   desc="Lower the robot tray"):
                    builder.TYPE(ParamType.ARRAY)

                    with builder.CHILDREN():
                        # 复用顶升高度参数
                        create_jack_height_param(builder)

                        # 使用向下PGV参数
                        with builder.CHILD(key="use_down_pgv", name="Use Down PGV",
                                           desc="Use downward-facing PGV for position adjustment"):
                            builder.TYPE(ParamType.BOOL)
                            builder.DEFAULTVALUE(False)

                # JackSpin操作
                with builder.CHILD(key="JackSpin", name="Spin Operation",
                                   desc="Spin the robot"):
                    builder.TYPE(ParamType.ARRAY)

                    with builder.CHILDREN():
                        # 旋转角度参数
                        with builder.CHILD(key="spin_angle", name="angle",
                                           desc="机器人原地旋转角度，正值为逆时针，负值为顺时针"):
                            builder.MIN_VALUE(-360)
                            builder.MAX_VALUE(360)
                            builder.TYPE(ParamType.INT)
                            builder.REQUIRED(True)
                            builder.UNIT("度")
                            builder.DEFAULTVALUE(0)

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

                        with builder.CHILD("spin_type", name="Spin Type", desc="Spin Type"):
                            builder.TYPE(ParamType.STRING_COMBO_LIST)
                            builder.DEFAULTVALUE(0)

                            with builder.CHILDREN():
                                with builder.CHILD("0", "0", "0"):
                                    builder.TYPE(ParamType.STRING)
                                with builder.CHILD("1", "1", "1"):
                                    builder.TYPE(ParamType.STRING)
                                with builder.CHILD("2", "2", "2"):
                                    builder.TYPE(ParamType.STRING)
    builder.save_to_file()

class Jack:
    def __init__(self, args):
        self.opt = None
        self.height = 0.03
        self.spin_angle = 0
        self.count = 0
        self.args = args
        self.report_info = {}
        self.report_info["args"] = args

    def run(self):
        self.count += 1
        Module.set_status(ScriptStatus.RUNNING)
        self.report_info["count"] = self.count
        self.report_info["run_time"] = round(time.time() - start_time, 2)
        self.opt = self.args.get('operation', None)
        self.height = self.args.get('height', None)
        if self.count == 100:
            Module.set_status(ScriptStatus.FINISHED)
        ...

    def print_info(self):
        # 打印当前任务队列、当前任务、当前任务id、当前任务状态
        log.info(f"{Module.get_task_id()=}, {Module.get_status()=}, {self.args=}")
        Module.report_info(self.report_info)

    def suspend(self):
        Module.set_status(ScriptStatus.SUSPENDED)
        log.info("suspend")

    def resume(self):
        Module.set_status(ScriptStatus.RUNNING)
        log.info("resume")

    def cancel(self):
        Module.set_status(ScriptStatus.FINISHED)
        log.info("cancel")


def main():
    Module.init()

    # 平铺格式
    # input_params = {
    #     "use_pgv": True,
    #     "modbus_ip": "192.168.192.6",
    #     "operation": "JackSpin",
    #     "spin_angle": 4,
    #     "useExternIMU": False,
    #     "IMU": "0"
    # }

    # 平铺"."拼接格式
    # input_params = {
    #     "modbus_ip": "192.168.192.6",
    #     "use_pgv": True,
    #     "operation.JackSpin": 2,
    #     "operation.JackSpin.spin_angle": 4,
    #     "operation.JackSpin.useExternIMU.OFF": 0,
    #     "operation.JackSpin.useExternIMU.OFF.IMU": "0",
    #     "operation.JackSpin.spin_type": "1"
    # }

    validator = ParamValidator(InputParams.builder.to_dict())
    input_params = Module.get_task_args()
    print("task args:", json.dumps(input_params, indent=2))
    validated_params = {}
    try:
        # 验证参数
        validated_params = validator.validate(input_params)
        print("check ok, args:", json.dumps(validated_params, indent=2))
    except ValueError as e:
        print("check error:", e)

    j = Jack(validated_params)
    Module.set_suspend_callback(j.suspend)
    Module.set_resume_callback(j.resume)
    Module.set_cancel_callback(j.cancel)

    while True:
        # 脚本任务状态管理
        status = Module.get_status()
        j.report_info["status"] = status
        j.print_info()
        if status is ScriptStatus.RUNNING:
            j.run()
        elif status in (ScriptStatus.FAILED, ScriptStatus.FINISHED):
            return

        time.sleep(0.1)

# 主程序
if __name__ == "__main__":
    main()
