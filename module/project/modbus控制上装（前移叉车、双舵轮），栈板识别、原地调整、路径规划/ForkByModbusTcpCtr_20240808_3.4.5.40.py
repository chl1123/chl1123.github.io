# -*- coding: utf-8 -*-
# @Date: 2023/04/03
# @Author: CXN
# @File: ForkByModbusTcpCtr.py
# @Version: 2.1.5
# @Project:
# @Coding:
# @Update: 智库造车项目，脚本控制上装（modbus tcp），双舵轮,优化计算取货坐标的方法，取货坐标不同于栈板坐标，增加手动控制货叉(1206),增加货物超宽检测并增加超框后先抬起再收叉(1220)
import enum
import json
import math
import struct
import time
from typing import List
import sys
from syspy import goPath

sys.path.append("../modbus_tk")
from syspy.rbkSim import SimModule
from syspy.rbk import MoveStatus, BasicModule, ParamServer
from syspy.robot import ModuleTool

try:
    import modbus_tk.defines as cst
    from modbus_tk import modbus_tcp, modbus_rtu
except ImportError:
    import os

    os.system("pip install modbus_tk")
    SimModule.setError(SimModule(), f"modbus_tk needs to be installed")
    os.system("pip install modbus_tk -i https://pypi.tuna.tsinghua.edu.cn/simple")
    import modbus_tk.defines as cst
    from modbus_tk import modbus_tcp

"""
####BEGIN DEFAULT ARGS####
{
    "operation": {
        "value": "core",
        "default_value": [
            "man_lift",
            "man_stretch",
            "forklift",
            "pick",
            "drop",
            "pallet_code_rec",
            "switch_mode",
            "weigh",
            "stretch_go",
            "stretch_back",
            "translate",
            "angle",
            "ready",
            "safeCheck",
            "rec_pallet",
            "adjust",
            "startCharging",
            "stopCharging"
        ],
        "tips": "选择操作",
        "type": "complex"
    },
    "mode": {
        "value": "1",
        "default_value": [
            "1",
            "0"
        ],
        "tips": "选择模式",
        "type": "complex"
    },
    "action_parameters": {
        "value": "",
        "tips": "actionParameters",
        "type": "json"
    },
    "pallet_code": {
        "value": "",
        "tips": "托盤碼",
        "type": "string"
    },
    "blocking_type": {
        "value": "",
        "tips": "動作是否同步",
        "type": "string"
    },
    "rec_file": {
        "value": "",
        "tips": "識別文件",
        "type": "string"
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        # 脚本輸入參數初始化

        self.fork_len = 0.94  # 里程中心到叉尖距离，4米五车子0.905，6米车子0.94
        self.contact_di_to_odo = 0.99  # 叉齿伸出后到位开关到里程中心的距离，4米五车子0.965，6米车子0.99

        self.y_dist = 0.005  # 栈板识别左右偏差精度
        self.yaw_dist = 0.01  # 栈板识别角度偏移精度

        self.speed_adjust_max = 0.1  # 栈板识别后，在前置点调整对准栈板的最大速度
        self.y_adjust_max = 0.1  # 栈板允許的左右偏差最大值，米
        self.yaw_adjust_max = 0.26  # 栈板允許的角度偏差最大值，弧度
        self.safe_check_need = None
        self.fork2base = [0.0, 0.0, -math.pi / 2]  # 叉尺相对里程中心坐标
        self.pallet2world = [0., 0., 0.]  # 栈板世界坐标系
        self.target2world = [0., 0., 0.]  # 前置点坐标系
        self.pallet2robot = [0., 0., 0.]  # 前置点坐标系,相对与机器人坐标系
        self.switch_model = None
        self.action_parameters = None
        self.blocking_type = None
        self.angle = None
        self.recognize = None
        self.endPoint = None
        self.startPoint = None
        self.depth = None
        self.loadId = None
        self.weight = None
        self.mode = None
        self.height = None
        self.robot_pos = [0., 0., 0.]  # 栈板识别前的机器人位置
        self.is_palletWidth = False  # 是否超宽
        p = ParamServer(__file__)
        self.timeout_PalletCodeRec = p.loadParam("timeout_PalletCodeRec", type="int", default=10,
                                                 comment="托盘码识别超时时间")
        self.palletWidth_height = p.loadParam("palletWidth_height", type="int", default=1100,
                                              comment="栈板超框后，取货先抬起到的目标位置")
        self.palletWidth = p.loadParam("palletWidth", type="float", default=1.0,
                                       comment="最大货物宽度")
        self.depth_dist = p.loadParam("depth_dist", type="float", default=0.0,
                                      comment="平移指定距离后，执行pick时，继续平移距离")
        # 这两个距离需要很具实际车型配置，解析见 https://seer-group.yuque.com/pf4yvd/cnme5y/fz1ze1
        self.back_dist = p.loadParam("back_dist", type="float", default=0.3, comment="展板后退距离")
        self.ahead_dist = p.loadParam("ahead_dist", type="float", default=0.1, comment="展板前置距离距离")

        self.forklift_micro_height_drop = p.loadParam("forklift_micro_height_drop", type="int", default=120,
                                                      comment="放货，到位后货叉下降高度")
        self.forklift_micro_height_pick = p.loadParam("forklift_micro_height_pick", type="int", default=120,
                                                      comment="取货，到位后货叉抬升高度")
        self.rec_file = p.loadParam("rec_file", type="str", default="multi/m0002.multi", comment="展板識別文件")
        self.ip = p.loadParam("ip", type="str", default="192.168.192.106", comment="PLC的ip地址")
        self.port = p.loadParam("port", type="int", default=502, comment="PLC的端口")
        self.slave_id = p.loadParam("slave_id", type="int", default=1, comment="PLC的 id")
        self.timeout = p.loadParam("timeout", type="int", default=180, comment="整个任务的超时时间")
        self.safe_height = p.loadParam("safe_height", type="int", default=1100, comment="货叉安全高度")
        self.safe_length = p.loadParam("safe_length", type="int", default=100, comment="货叉前移安全距离")
        self.min_fork_height = p.loadParam("min_fork_height", type="int", default=80, comment="货叉最低高度")
        self.lifi_height_dist = p.loadParam("lifi_height_dist", type="int", default=20, comment="升降误差阈值")
        self.changer_DO = p.loadParam("changer_DO", type="int", default=5, comment="充电DO")
        self.Translate_speed_max_go = p.loadParam("Translate_speed_max_go", type="float", default=0.2,
                                                  comment="平移最大速度——前半段")
        self.Translate_speed_max_back = p.loadParam("Translate_speed_max_back", type="float", default=0.2,
                                                    comment="平移最大速度——后半段")

        # 手动控制上装的DI 配置，共4个
        self.man_up_lift = p.loadParam("man_up_lift", type="int", default=1, comment="手动控制货叉上升")
        self.man_down_lift = p.loadParam("man_down_lift", type="int", default=2, comment="手动控制货叉下降")
        self.man_out_stretch = p.loadParam("man_out_stretch", type="int", default=3, comment="手动控制货叉伸出")
        self.man_back_stretch = p.loadParam("man_back_stretch", type="int", default=4, comment="手动控制货叉缩回")
        self.man_lift_speed_up = p.loadParam("man_lift_speed_up", type="int", default=50,
                                             comment="手动控制货叉上升速度")
        self.man_lift_speed_down = p.loadParam("man_lift_speed_down", type="int", default=-50,
                                               comment="手动控制货下降降速度")

        self.init = True
        self.result = None
        self.need_y = 0
        self.init_operation = True
        self.status = MoveStatus.NONE
        self.operation_status = MoveStatus.NONE
        self.start_t = time.time()
        self.modbus_tcp = None
        self.go_path = goPath.Module(r, dict())
        self.task_id = 0
        self.task_list = list()
        self.report_data = dict()  # serInfo的信息，这个信息调度可以拿到
        self.operation = None
        self.PLC = Gantry()  # 保存了PLC的所有状态信息
        # plc address INFO，地址是连续的，实际上只用了起始地址，其他只是做个记录
        self.gantry_sensor_status_addr = 0x000A
        self.cargo_weight_addr = 0x000B  # 当前叉齿上货物的重量值:单位：0.1kg 范围0~13000
        self.stretch_position_addr = 0x000C  # 当前伸叉位置值:单位：mm 范围-1300~1300
        self.lift_position_addr = 0x000D  # 当前升降位置值:单位：mm 范围-500~6000
        self.stretch_speed_addr = 0x000E  # 单位：mm/s 伸出为正值，收回为负值
        self.lift_speed_addr = 0x000F  # 单位：mm/s 伸出为正值，收回为负值
        self.stretch_status_addr = 0x0010  # 0：停止中 1：伸叉中2、收叉中 3、运行完成
        self.lift_status_addr = 0x0011  # 0：停止中 1：上升中2、下降中 3、运行完成
        self.ready_addr = 0x0012  # 0：未就绪 1：就绪可接收新任务
        self.gantry_error_addr = 0x0013  # 门架故障报警信息
        self.gantry_fault_addr = 0x0014  # 门架故障警告信息.bit0:识别到的托盘码与下发信息不一致 bit1:识别不到托盘码 bit2：重量对比错误
        self.pallet_code_addr = 0x0015  # 读取到的托盘码,0x0015~0x002D
        self.mode_status_addr = 0x002F  # 当前模式状态 0：手动 1：自动

        # PLC control address
        self.stretch_action_command = 0x0100  # 0：无 1：收叉
        self.stretch_back_command = 0x0101  # 0：无 1：收叉
        self.gantry_init_command = 0x0102  # 0：无 1：系统初始化（复位故障并回原点/伸叉和升降） 2：复位（清除故障）
        self.gantry_EMC_command = 0x0103  # 0：无 1：急停
        self.lift_action_command = 0x0104  # 0：无 1：升降
        self.lift_target_height_command = 0x0105  # 取放货时目标高度值:单位：mm 范围-500~6000
        self.lift__height_speed_action_command = 0x0106  # 升降速度动作指令,0：无 1：开启升降-速度模式

        self.lift__height_speed_command = 0x0107  # 升降速度,-300~300

        self.switch_model_command = 0x0108  # 0：手动 1：自动
        self.pallet_start_weighing_command = 0x0109  # 0：无 1：开始称重
        self.goods_weight_load_command = 0x010A  # 上位机下发的重量值:单位：0.1kg 范围0~13000
        self.pallet_code_recognize_command = 0x010B  # 0：无 1：开始识别
        self.pallet_code_send_command = 0x010C  # 0x010A~0x0122
        # opt
        self.pallet_rec_action_opt = [False] * 2
        self.weigh_action_opt = [False] * 2
        self.stretch_action_opt = [False] * 2
        self.lift_action_opt = [False] * 4
        self.get_plc_info_opt = [False] * 12
        self.check_ready = False
        self.man_handel = False

        r.logInfo(f"init args: {args}")

    def cancel(self, r: SimModule):
        """导航任务取消"""
        r.clearWarning(55999)
        self.status = MoveStatus.NONE

    def periodRun(self, r: SimModule) -> bool:
        if self.modbus_tcp is None:
            # 建立PLC连接
            self.modbus_tcp = modbus_tcp.TcpMaster(host=self.ip, port=self.port, timeout_in_sec=5.0)
        # 获取 plc 信息
        if self.get_plc_info(r):
            report_data = {"PLC": self.PLC.__str__()}
            r.setInfo(json.dumps(report_data))

        return True

    def run(self, r: SimModule, args: dict):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            self.operation = args.get("operation", None)
            if self.modbus_tcp is None:
                self.modbus_tcp = modbus_tcp.TcpMaster(host=self.ip, port=self.port, timeout_in_sec=5.0)
            self.action_parameters = args.get("action_parameters", None)
            if self.action_parameters:
                for a_p in self.action_parameters:
                    if a_p["key"] == "loadId":
                        self.loadId = a_p['value']
                    elif a_p["key"] == "weight":
                        self.weight = a_p['value']
                    elif a_p["key"] == "depht":
                        self.depth = a_p['value']
                    elif a_p["key"] == "depth":
                        self.depth = a_p['value']
                    elif a_p["key"] == "startPoint":
                        self.startPoint = a_p['value']
                    elif a_p["key"] == "endPoint":
                        self.endPoint = a_p['value']
                    elif a_p["key"] == "recognize":
                        self.recognize = a_p['value']
                    elif a_p["key"] == "angle":
                        self.angle = a_p['value']
                    elif a_p["key"] == "height":
                        self.height = a_p['value']
                    elif a_p["key"] == "heightPick":
                        self.forklift_micro_height_pick = a_p['value']
                    elif a_p["key"] == "heightDrop":
                        self.forklift_micro_height_drop = a_p['value']
                    elif a_p["key"] == "safeCheck":
                        self.safe_check_need = a_p['value']
            self.blocking_type = args.get("blocking_type", None)
            self.mode = args.get("mode", None)
            if args.get("rec_file", None):
                self.rec_file = args.get("rec_file", None)
        if self.status != MoveStatus.FINISHED and not self.init:
            # 获取 plc 信息
            if self.get_plc_info(r):
                self.report_data["PLC"] = self.PLC.__str__()
                s = self.check_error(r)
                # 货叉 叉尖传感器检测
                if s != MoveStatus.FAILED:
                    if not self.check_ready:
                        if self.PLC.ready:
                            self.check_ready = True
                    else:
                        r.setUserWarning(55999, "PLC running ...")
                        self.handle_run(r)
                if s == MoveStatus.FAILED:
                    self.status = MoveStatus.FAILED
                    return self.status

        if time.time() - self.start_time > self.timeout:
            r.setError(f"运行超时 {self.timeout} s")
            self.status = MoveStatus.FAILED

        if self.status == MoveStatus.FINISHED:
            r.clearWarning(55999)
        self.log_PLC(r)
        # r.setInfo(json.dumps(self.report_data))
        r.logInfo(json.dumps(self.report_data))

        return self.status

    def run_tak_list(self, r):
        if self.task_id < len(self.task_list):
            if self.task_list[self.task_id].status == MoveStatus.NONE:
                self.task_list[self.task_id].reset(self)
            elif self.task_list[self.task_id].status == MoveStatus.FINISHED:
                self.task_id = self.task_id + 1
            elif self.task_list[self.task_id].status == MoveStatus.FAILED:
                self.operation_status = MoveStatus.FAILED
            else:
                self.task_list[self.task_id].run(r, self)
        else:
            self.operation_status = MoveStatus.FINISHED

    def handle(self, r: SimModule):
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
        else:
            self.status = self.operation_status
            self.run_tak_list(r)

    def get_plc_info(self, r):
        c = self.modbus_tcp.execute(1, cst.READ_HOLDING_REGISTERS, self.gantry_sensor_status_addr, 38)
        r.logDebug(f"PLC_data:{c},{len(c)}")
        self.PLC.gantry_sensor_status.update(c[0])
        self.PLC.cargo_weight = c[1]
        self.PLC.stretch_position = c[2]
        self.PLC.lift_position = c[3]
        self.PLC.stretch_speed = struct.unpack('h', struct.pack('H', c[4]))[0]
        self.PLC.lift_speed = struct.unpack('h', struct.pack('H', c[5]))[0]
        self.PLC.stretch_status = c[6]
        self.PLC.lift_status = c[7]
        self.PLC.ready = c[8]
        self.PLC.gantry_error.update(c[9])
        self.PLC.gantry_fault.update(c[10])
        self.PLC.mode_status = c[37]

        r.logDebug(f"code:{c[11:35]}")
        bytes_representation = bytearray()
        for value in c[11:35]:
            byte1 = (value & 0xFF00) >> 8  # 获取高字节
            byte2 = value & 0x00FF  # 获取低字节
            bytes_representation.append(byte2)
            bytes_representation.append(byte1)

        # self.PLC.pallet_code = int_array_convert_to_string(c[9:35])
        self.PLC.pallet_code = bytes_representation.decode("ascii").rstrip('\0')

        return True

    def handle_run(self, r: SimModule):
        if self.operation == "forklift":
            self.forklift(r)
        elif self.operation == "pick":

            self.pick(r)
        elif self.operation == "drop":
            self.drop(r)
        elif self.operation == "man_stretch":
            self.man_stretch(r)
        elif self.operation == "man_lift":
            self.man_lift(r)
        elif self.operation == "stretch_go":
            self.stretch_go(r)
        elif self.operation == "stretch_back":
            self.stretch_back(r)
        elif self.operation == "pallet_code_rec":
            self.pallet_rec(r)
        elif self.operation == "switch_mode":
            self.switch_mode(r)
        elif self.operation == "weigh":
            if self.weight:
                self.weigh(r)
            else:
                r.setError("没有输入重量")
                self.status = MoveStatus.FAILED
        elif self.operation == "translate":
            self.translate(r)
        elif self.operation == "angle":
            self.angle_action(r)
        elif self.operation == "ready":
            self.is_ready(r)
        elif self.operation == "safeCheck":
            self.safe_check(r)
        elif self.operation == "rec_pallet":
            self.rec_pallet(r)
        elif self.operation == "adjust":
            self.adjust(r)
        elif self.operation == "startCharging":
            self.start_changer(r)
        elif self.operation == "stopCharging":
            self.stop_changer(r)
        else:
            r.setError(f"operation 参数错误:{self.operation}")
            self.status = MoveStatus.FAILED

    def forklift(self, r):
        if self.init_operation:
            if self.safe_check_need:
                self.task_list.append(SafeCheck())
            if self.height:
                self.task_list = [ForkLift(self.height)]
                self.init_operation = False
            else:
                self.status = MoveStatus.FAILED
                r.setError(f"没有输入高度")
        else:

            self.handle(r)

    def pallet_rec(self, r):
        if self.init_operation:
            if self.loadId:
                self.task_list = [PalletCodeRec(self.loadId)]
                self.init_operation = False
            else:
                r.setError(f"没有 loadId ")
                self.status = MoveStatus.FAILED
        else:
            self.handle(r)

    def pick(self, r):
        if self.init_operation:
            self.depth += self.depth_dist
            if self.safe_check_need:
                self.task_list.append(SafeCheck())
            self.task_list.append(CheckGoods("pick", "before"))
            # 升到指定高度
            if self.height:
                self.task_list.append(ForkLift(self.height))
            # 获取位置
            self.task_list.append(GetRobotPos())
            # 栈板识别，获取识别结果
            if self.recognize:
                self.task_list.append(AdjustPos(r, self.rec_file))
            if self.loadId:
                self.task_list.append(PalletCodeRec(self.loadId, self.timeout_PalletCodeRec))
            # 边走边伸叉，停下来条件 1、已经超过预定距离，2、已经叉到货
            if self.recognize:
                self.task_list.append(TranslateStretchByPos(r, "go"))
            else:
                self.task_list.append(TranslateStretch(r, self.angle, self.depth, "go"))
            # 抬叉
            self.task_list.append(MiniForklift(self.operation))
            # 称重
            if self.weight:
                self.task_list.append(Weigh(self.weight))
            # 返回前置点，同时收叉
            if self.recognize:
                self.task_list.append(TranslateStretchByPos(r, "back"))
            else:
                self.task_list.append(TranslateStretch(r, 0 - self.angle, self.depth, "back"))
            # 检查货物
            self.task_list.append(CheckGoods("pick", "after"))
            # 加载货物模型
            self.task_list.append(SetGoodsModule("pick"))
            self.init_operation = False
        else:
            self.handle(r)

    def switch_mode(self, r):
        if self.init_operation:
            if self.safe_check_need:
                self.task_list.append(SafeCheck())
            self.task_list = [
                SwitchMode(self.mode),
            ]
            self.init_operation = False
        else:
            self.handle(r)

    def weigh(self, r):
        if self.init_operation:
            if self.safe_check_need:
                self.task_list.append(SafeCheck())
            self.task_list = [
                Weigh(self.weight)
            ]
            self.init_operation = False
        else:
            self.handle(r)

    def drop(self, r):
        if self.init_operation:
            if self.safe_check_need:
                self.task_list.append(SafeCheck())
            self.task_list.append(CheckGoods("drop", "before"))
            # 边走边伸叉，停下来条件 1、已经超过预定距离，2、已经叉到货
            self.init_operation = False
            # 升到指定高度
            if self.height:
                self.task_list.append(ForkLift(self.height))
            self.task_list.append(TranslateStretch(r, self.angle, self.depth, "go"))
            self.task_list.append(MiniForklift(self.operation))
            self.task_list.append(TranslateStretch(r, 0 - self.angle, self.depth, "back"))
            # 检查货物
            self.task_list.append(CheckGoods("drop", "after"))
            # 清除货物状态
            self.task_list.append(SetGoodsModule("drop"))

        else:
            self.handle(r)

    def lift_action(self, r: SimModule, height, safe_check: bool = False):
        if all(self.lift_action_opt):
            return True
        if height <= self.min_fork_height:
            height = self.min_fork_height
        if not self.lift_action_opt[0]:
            self.modbus_tcp.execute(1, cst.WRITE_SINGLE_REGISTER, self.lift_target_height_command, output_value=height)
            self.lift_action_opt[0] = True
        elif not self.lift_action_opt[1] and self.lift_action_opt[0]:
            self.modbus_tcp.execute(1, cst.WRITE_SINGLE_REGISTER, self.lift_action_command,
                                    output_value=ActionCommand.RESET)
            self.lift_action_opt[1] = True
        elif not self.lift_action_opt[2] and self.lift_action_opt[1]:
            self.modbus_tcp.execute(1, cst.WRITE_SINGLE_REGISTER, self.lift_action_command,
                                    output_value=ActionCommand.ACTION)
            self.lift_action_opt[2] = True
            if safe_check:
                self.lift_action_opt[3] = True
        elif not self.lift_action_opt[3] and self.lift_action_opt[2]:
            if self.PLC.lift_status == 3 and (
                    (height - self.lifi_height_dist) <= self.PLC.lift_position <= (height + self.lifi_height_dist)):
                lift_status = self.modbus_tcp.execute(1, cst.READ_HOLDING_REGISTERS, self.lift_status_addr, 1)[0]
                if lift_status == 3:
                    self.lift_action_opt[3] = True
        r.setNotice(f"lift_action_opt:{self.lift_action_opt}")
        if all(self.lift_action_opt):
            return True
        return False

    def stretch_go(self, r):
        if self.init_operation:
            if self.safe_check_need:
                self.task_list.append(SafeCheck())
            self.task_list = [
                Stretch("go")
            ]
            self.init_operation = False
        else:
            self.handle(r)

    def stretch_back(self, r):
        if self.init_operation:
            if self.safe_check_need:
                self.task_list.append(SafeCheck())
            self.task_list = [
                Stretch("back")
            ]
            self.init_operation = False
        else:
            self.handle(r)

    # 伸叉
    def stretch_go_action(self):
        if all(self.stretch_action_opt):
            return True
        if not self.stretch_action_opt[0]:
            self.modbus_tcp.execute(1, cst.WRITE_SINGLE_REGISTER, self.stretch_action_command,
                                    output_value=ActionCommand.RESET)
            self.stretch_action_opt[0] = True
        elif not self.stretch_action_opt[1] and self.stretch_action_opt[0]:
            self.modbus_tcp.execute(1, cst.WRITE_SINGLE_REGISTER, self.stretch_action_command,
                                    output_value=ActionCommand.ACTION)
            self.stretch_action_opt[1] = True
        return False

    # 收叉
    def stretch_back_action(self):
        if all(self.stretch_action_opt):
            return True
        if not self.stretch_action_opt[0]:
            self.modbus_tcp.execute(1, cst.WRITE_SINGLE_REGISTER, self.stretch_back_command,
                                    output_value=ActionCommand.RESET)
            self.stretch_action_opt[0] = True
        elif not self.stretch_action_opt[1] and self.stretch_action_opt[0]:
            self.modbus_tcp.execute(1, cst.WRITE_SINGLE_REGISTER, self.stretch_back_command,
                                    output_value=ActionCommand.ACTION)
            self.stretch_action_opt[1] = True

        return False

    def pallet_rec_action(self, r, pallet_code):
        if pallet_code is None:
            self.status = MoveStatus.FAILED
            r.setError(f"pallet_code is None")
            return
        code = string_convert_to_int_array(pallet_code)
        r.setNotice(f"plc pallet code rec:{code}")
        r.logDebug(f"string_convert_to_int_array:{code}")
        # 寫入托盘码
        if not self.pallet_rec_action_opt[0]:
            if self.pallet_rec_send(code):
                self.pallet_rec_action_opt[0] = True
        elif not self.pallet_rec_action_opt[1] and self.pallet_rec_action_opt[0]:
            if self.PLC.gantry_fault.readNoEqualByOrder:
                r.logDebug("readNoEqualByOrder!!!")
                r.setNotice("readNoEqualByOrder!!!")
            if self.PLC.gantry_fault.readCodeFault:
                r.logDebug("readCodeFault!!!")
                r.setNotice("readCodeFault!!!")
            if self.PLC.pallet_code == pallet_code:
                self.pallet_rec_action_opt[1] = True

        r.logDebug(f"pallet_rec_action_opt:{self.pallet_rec_action_opt},{self.PLC.pallet_code} -- {code}")
        if all(self.pallet_rec_action_opt):
            return True
        return False

    def pallet_rec_send(self, code):
        self.modbus_tcp.execute(1, cst.WRITE_MULTIPLE_REGISTERS, self.pallet_code_send_command, output_value=code)
        # 復位
        self.modbus_tcp.execute(1, cst.WRITE_SINGLE_REGISTER, self.pallet_code_recognize_command,
                                output_value=ActionCommand.RESET)
        # 開始識別
        self.modbus_tcp.execute(1, cst.WRITE_SINGLE_REGISTER, self.pallet_code_recognize_command,
                                output_value=ActionCommand.ACTION)
        return True

    def switch_mode_action(self, r, mode_type):
        res = self.modbus_tcp.execute(1, cst.WRITE_SINGLE_REGISTER, self.switch_model_command, output_value=mode_type)
        r.logDebug(f"switch_mode_action res:{res}")
        return True

    def weigh_action(self, r, w):
        r.logDebug(f"weigh_action:{w}")
        # 下发称重指令
        if not self.weigh_action_opt[0]:
            res = self.modbus_tcp.execute(1, cst.WRITE_SINGLE_REGISTER, self.goods_weight_load_command,
                                          output_value=w)
            self.modbus_tcp.execute(1, cst.WRITE_SINGLE_REGISTER, self.pallet_start_weighing_command,
                                    output_value=ActionCommand.RESET)
            self.modbus_tcp.execute(1, cst.WRITE_SINGLE_REGISTER, self.pallet_start_weighing_command,
                                    output_value=ActionCommand.ACTION)
            self.weigh_action_opt[0] = True
            return True
        # 检查称重结果
        if not self.weigh_action_opt[1] and self.weigh_action_opt[0]:
            if self.PLC.gantry_fault.weightComparisonError:
                r.logDebug(f"weightComparisonError,weight:{self.PLC.cargo_weight}")
                r.setError(f"weightComparisonError,weight:{self.PLC.cargo_weight}")
                self.status = MoveStatus.FAILED
            else:
                if self.PLC.cargo_weight > 0 and not self.PLC.gantry_fault.weightComparisonError:
                    self.weigh_action_opt[1] = True
                else:
                    r.setError(f"weightComparisonError:{self.PLC.gantry_fault.weightComparisonError},"
                               f"PLC cargo_weight:{self.PLC.cargo_weight},"
                               f"order cargo_weight:{w}")
                    self.status = MoveStatus.FAILED
            r.setNotice(f"weight ComparisonError,PLC weight:{self.PLC.cargo_weight},target:{w}")
        if all(self.weigh_action_opt):
            return True
        return False

    def check_error(self, r):
        # bit0：前限位报警
        if self.PLC.gantry_error.beforeLimitAlarm:
            self.status = MoveStatus.FAILED
            r.setUserError(53900, "前限位报警")
            return self.status
        # bit1：后限位报警
        if self.PLC.gantry_error.afterLimitAlarm:
            self.status = MoveStatus.FAILED
            r.setUserError(53901, "后限位报警")
            return self.status
        # bit2：初始化失败
        if self.PLC.gantry_error.initFail:
            self.status = MoveStatus.FAILED
            r.setUserError(53902, "初始化失败")
            return self.status

        # bit3：伸叉运行超时
        if self.PLC.gantry_error.stretchRunTimeout:
            self.status = MoveStatus.FAILED
            r.setUserError(53903, "伸叉运行超时")
            return self.status

        # bit4：伸叉同步异常
        if self.PLC.gantry_error.stretchSyncErr:
            self.status = MoveStatus.FAILED
            r.setUserError(53904, "伸叉同步异常")
            return self.status

        # bit5：伸叉驱动报警
        if self.PLC.gantry_error.stretchDriveAlarm:
            self.status = MoveStatus.FAILED
            r.setUserError(53905, "伸叉驱动报警")
            return self.status

        # bit6：上限位报警
        if self.PLC.gantry_error.upLimitAlarm:
            self.status = MoveStatus.FAILED
            r.setUserError(53906, "上限位报警")
            return self.status

        # bit7：下限位报警
        if self.PLC.gantry_error.downLimitAlarm:
            self.status = MoveStatus.FAILED
            r.setUserError(53907, "下限位报警")
            return self.status

        # bit8：升降运行超时
        if self.PLC.gantry_error.liftRunTimeout:
            self.status = MoveStatus.FAILED
            r.setUserError(53908, "升降运行超时")
            return self.status

        # bit9：液压系统异常
        if self.PLC.gantry_error.HydraulicSystemErr:
            self.status = MoveStatus.FAILED
            r.setUserError(53909, "液压系统异常")
            return self.status

        # bit10：提升驱动报警
        if self.PLC.gantry_error.liftDriveAlarm:
            self.status = MoveStatus.FAILED
            r.setUserError(53910, "提升驱动报警")
            return self.status

        # bit11:提升编码器数据异常
        if self.PLC.gantry_error.liftEncoderDataErr:
            self.status = MoveStatus.FAILED
            r.setUserError(53911, "提升编码器数据异常")
            return self.status

        #  bit12:超重
        if self.PLC.gantry_error.overWeight:
            self.status = MoveStatus.FAILED
            r.setUserError(53912, "超重")
            return self.status

        if self.PLC.gantry_error.prong:
            self.status = MoveStatus.FAILED
            r.setUserError(53913, "叉尖报警")
            return self.status

        if self.PLC.gantry_error.noGoodsStretch:
            self.status = MoveStatus.FAILED
            r.setUserError(53914, "仰起无货伸叉报警")
            return self.status

        if self.PLC.gantry_error.widthCheckFirmError:
            self.status = MoveStatus.FAILED
            r.setUserError(53915, "超宽检测装置硬件异常")
            return self.status

        ############################################################

        return self.status

    def translate(self, r):
        if self.init_operation:
            if self.safe_check_need:
                self.task_list.append(SafeCheck())
            self.task_list = [
                Translate(r, self.angle, self.depth)
            ]
            self.init_operation = False
        else:
            self.handle(r)

    def angle_action(self, r):
        if self.init_operation:
            if self.safe_check_need:
                self.task_list.append(SafeCheck())
            self.task_list = [
                AngleAction(r, self.angle)
            ]
            self.init_operation = False
        else:
            self.handle(r)

    def is_ready(self, r):
        self.get_plc_info(r)
        if self.PLC.ready:
            self.status = MoveStatus.FINISHED
            r.setNotice(f"PLC is ready !!!")

    def safe_check(self, r):
        if self.init_operation:
            self.task_list = [
                SafeCheck()
            ]
            self.init_operation = False
        else:
            self.handle(r)

    def rec_pallet(self, r):
        if self.init_operation:
            self.task_list.append(Rec(self.rec_file))
            self.init_operation = False
        else:
            self.handle(r)

    def adjust(self, r):
        """識別展板並調整"""
        if self.init_operation:
            if self.safe_check_need:
                self.task_list.append(SafeCheck())
            self.task_list.append(AdjustPos(r, self.rec_file))
            self.init_operation = False
        else:
            self.handle(r)

    def start_changer(self, r):
        """打开充电DO"""
        if self.init_operation:
            self.task_list.append(OpenDO([self.changer_DO]))
            self.init_operation = False
        else:
            self.handle(r)

    def stop_changer(self, r):
        """打开充电DO"""
        if self.init_operation:
            self.task_list.append(CloseDO([self.changer_DO]))
            self.init_operation = False
        else:
            self.handle(r)

    def log_PLC(self, r: SimModule):
        gss = self.PLC.gantry_sensor_status
        ge = self.PLC.gantry_error
        gf = self.PLC.gantry_fault
        r.logDebug(f"[PLC]["
                   f"{gss.StockOnTheFork}|{gss.forkTipDetection1}|{gss.forkTipDetection2}|{gss.forkHomePosition}|"
                   f"{gss.frontLimit}|{gss.backLimit}|{gss.reachOutInPlace}|{gss.withdrawInPlace}|{gss.liftInPlace}|"
                   f"{gss.liftHomePosition}|"
                   f"{ge.prong}|{ge.initFail}|{ge.overWeight}|{ge.liftDriveAlarm}|{ge.HydraulicSystemErr}|{ge.liftRunTimeout}|"
                   f"{ge.downLimitAlarm}|{ge.upLimitAlarm}|{ge.stretchDriveAlarm}|{ge.stretchSyncErr}|{ge.stretchRunTimeout}|"
                   f"{ge.afterLimitAlarm}|{ge.beforeLimitAlarm}|{ge.liftEncoderDataErr}|{ge.noGoodsStretch}|{ge.widthCheckFirmError}"
                   f"{self.PLC.ready}|{self.PLC.stretch_status}|{self.PLC.stretch_position}|{self.PLC.stretch_speed}|"
                   f"{self.PLC.lift_status}|{self.PLC.lift_position}|{self.PLC.lift_speed}|{self.PLC.mode_status}|"
                   f"{gf.weightComparisonError}|{gf.readCodeFault}|{gf.readNoEqualByOrder}|{self.PLC.cargo_weight}]")

    def man_stretch(self, r):
        if ModuleTool.check_DI(r, self.man_out_stretch):
            if self.PLC.ready and not self.man_handel:
                self.man_handel = True
                self.modbus_tcp.execute(1, cst.WRITE_SINGLE_REGISTER, self.stretch_action_command,
                                        output_value=ActionCommand.RESET)
                self.modbus_tcp.execute(1, cst.WRITE_SINGLE_REGISTER, self.stretch_action_command,
                                        output_value=ActionCommand.ACTION)
                self.status = MoveStatus.FINISHED
        elif ModuleTool.check_DI(r, self.man_back_stretch):
            if self.PLC.ready and not self.man_handel:
                self.man_handel = True
                self.modbus_tcp.execute(1, cst.WRITE_SINGLE_REGISTER, self.stretch_back_command,
                                        output_value=ActionCommand.RESET)
                self.modbus_tcp.execute(1, cst.WRITE_SINGLE_REGISTER, self.stretch_back_command,
                                        output_value=ActionCommand.ACTION)
                self.status = MoveStatus.FINISHED

    def man_lift(self, r):
        if ModuleTool.check_DI(r, self.man_up_lift) and not ModuleTool.check_DI(r, self.man_down_lift):
            if self.PLC.ready and not self.man_handel:
                self.man_handel = True
                self.modbus_tcp.execute(1, cst.WRITE_SINGLE_REGISTER, self.lift__height_speed_command,
                                        output_value=self.man_lift_speed_up)
                self.modbus_tcp.execute(1, cst.WRITE_SINGLE_REGISTER, self.lift__height_speed_action_command,
                                        output_value=ActionCommand.ACTION)
        elif ModuleTool.check_DI(r, self.man_down_lift) and not ModuleTool.check_DI(r, self.man_up_lift):
            if self.PLC.ready and not self.man_handel:
                self.man_handel = True
                self.modbus_tcp.execute(1, cst.WRITE_SINGLE_REGISTER, self.lift__height_speed_command,
                                        output_value=self.man_lift_speed_down)
                self.modbus_tcp.execute(1, cst.WRITE_SINGLE_REGISTER, self.lift__height_speed_action_command,
                                        output_value=ActionCommand.ACTION)
        else:
            self.modbus_tcp.execute(1, cst.WRITE_SINGLE_REGISTER, self.lift__height_speed_command,
                                    output_value=0)
            self.modbus_tcp.execute(1, cst.WRITE_SINGLE_REGISTER, self.lift__height_speed_action_command,
                                    output_value=ActionCommand.RESET)
            self.status = MoveStatus.FINISHED
        self.report_data["man_up_lift"] = ModuleTool.check_DI(r, self.man_up_lift)
        self.report_data["man_down_lift"] = ModuleTool.check_DI(r, self.man_down_lift)


class SafeCheck:
    def __init__(self):
        self.status = MoveStatus.NONE
        self.init = False
        self.load = True

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, m: Module):
        task_state = dict()

        if not self.init:
            self.init = True
            m.get_plc_info(r)
            self.load = m.PLC.gantry_sensor_status.StockOnTheFork
        if self.status != MoveStatus.FINISHED and self.init:
            if m.PLC.lift_position >= m.safe_height:
                if self.load:
                    if m.PLC.lift_position >= m.safe_height:
                        if m.lift_action(r, m.safe_height):
                            self.status = MoveStatus.FINISHED
                else:
                    if m.PLC.lift_position >= m.safe_height:
                        if m.lift_action(r, m.safe_height, True):
                            self.status = MoveStatus.FINISHED
            '''
            自动模式下，货叉伸出位置大于安全距离，限制x方向运动和原地旋转
            '''
            if m.PLC.mode_status == 1 and m.PLC.stretch_position >= m.safe_length:
                speed_dict = r.getNextSpeed()  # 获取导航下发的速度指令
                speed_x = speed_dict.get("x", 0.0)  # X方向线速度
                speed_rotate = speed_dict.get("rotate", 0.0)  # 旋转角速度
                if speed_x != 0 and speed_rotate == 0:  # X方向直线行走，不允许
                    r.setUserWarning(55900, f"伸叉状态下不允许前进/后退（x方向）运动")
                elif speed_x == 0 and speed_rotate != 0:
                    r.setUserWarning(55901, f"伸叉状态下不允许原地旋转")
                elif speed_x != 0 and speed_rotate != 0:
                    r.setUserWarning(55902, f"伸叉状态下不允许前进/后退（x方向）运动、原地旋转")
                elif speed_x == 0.0 and speed_rotate == 0.0:
                    r.clearWarning(55900)
                    r.clearWarning(55901)
                    r.clearWarning(55902)
                    self.status = MoveStatus.FINISHED
            else:
                r.clearWarning(55900)
                r.clearWarning(55901)
                r.clearWarning(55902)
                self.status = MoveStatus.FINISHED
        if self.status == MoveStatus.FAILED:
            r.setError(f"安全检查失败")
        task_state["status"] = self.status
        r.logDebug(json.dumps(task_state))


class Execute:

    def __init__(self, task: dict):
        self.status = MoveStatus.NONE
        self.task = task

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, m: Module):
        task_state = dict()
        task_state["task"] = self.task
        task_state["status"] = self.status
        r.logDebug(json.dumps(task_state))


class CheckGoods:
    def __init__(self, operation, time_s):
        self.status = MoveStatus.NONE
        self.time_s = time_s
        self.operation = operation

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, m: Module):
        self.status = MoveStatus.RUNNING
        task_state = dict()
        if self.operation == "pick" and self.time_s == "before":
            if m.PLC.gantry_sensor_status.StockOnTheFork:
                self.status = MoveStatus.FAILED
                r.setError("取货时有货")
            else:
                self.status = MoveStatus.FINISHED
        if self.operation == "pick" and self.time_s == "after":
            if m.PLC.gantry_sensor_status.StockOnTheFork:
                self.status = MoveStatus.FINISHED
            else:
                self.status = MoveStatus.FAILED
                r.setError("取货完成时无货")
        if self.operation == "drop" and self.time_s == "before":
            if not m.PLC.gantry_sensor_status.StockOnTheFork:
                self.status = MoveStatus.FAILED
                r.setError("放货时无货")
            else:
                self.status = MoveStatus.FINISHED
        if self.operation == "drop" and self.time_s == "after":
            if not m.PLC.gantry_sensor_status.StockOnTheFork:
                self.status = MoveStatus.FINISHED
            else:
                self.status = MoveStatus.FAILED
                r.setError("放货完成后还是有货")
        task_state["operation"] = self.operation
        task_state["status"] = self.status
        r.logDebug(json.dumps(task_state))


class Gantry:
    """
        门架传感器状态

    """

    def __init__(self):
        self.gantry_sensor_status = GantrySensorStatus()
        self.cargo_weight = None  # 当前叉齿上货物的重量值:单位：0.1kg 范围0~13000
        self.stretch_position = None  # 当前伸叉位置值:单位：mm 范围-1300~1300
        self.lift_position = None  # 当前升降位置值:单位：mm 范围-500~6000
        self.stretch_speed = None  # 单位：mm/s 伸出为正值，收回为负值
        self.lift_speed = None  # 单位：mm/s 伸出为正值，收回为负值
        self.stretch_status = None  # 0：停止中 1：伸叉中2、收叉中 3、运行完成
        self.lift_status = None  # 0：停止中 1：上升中2、下降中 3、运行完成
        self.ready = None  # 0：未就绪 1：就绪可接收新任务
        self.gantry_error = GantryError()  # 门架故障报警信息
        self.gantry_fault = GantryFault()  # 门架故障警告信息.bit0:识别到的托盘码与下发信息不一致 bit1:识别不到托盘码 bit2：重量对比错误
        self.pallet_code = None  # 读取到的托盘码
        self.mode_status = None  # 当前模式状态 0：手动 1：自动

    def to_dict(self):
        gantry_dict = {
            'gantry_sensor_status': self.gantry_sensor_status.to_json(),
            'cargo_weight': self.cargo_weight,
            'stretch_position': self.stretch_position,
            'lift_position': self.lift_position,
            'stretch_speed': self.stretch_speed,
            'lift_speed': self.lift_speed,
            'stretch_status': self.stretch_status,
            'lift_status': self.lift_status,
            'ready': self.ready,
            'gantry_error': self.gantry_error.to_json(),
            'gantry_fault': self.gantry_fault.to_json(),
            'pallet_code': self.pallet_code,
            'mode_status': self.mode_status
        }
        return gantry_dict

    def __str__(self):
        return self.to_dict()


class GantrySensorStatus:
    reachOutInPlace: int = 0
    withdrawInPlace: int = 0
    forkHomePosition: int = 0
    frontLimit: int = 0
    backLimit: int = 0
    StockOnTheFork: int = 0
    forkTipDetection1: int = 0
    forkTipDetection2: int = 0
    liftInPlace: int = 0
    liftHomePosition: int = 0
    upperLimit: int = 0
    lowerLimit: int = 0

    def update(self, sensor):
        self.reachOutInPlace = (sensor >> 0) & 1
        self.withdrawInPlace = (sensor >> 1) & 1
        self.forkHomePosition = (sensor >> 2) & 1
        self.frontLimit = (sensor >> 3) & 1
        self.backLimit = (sensor >> 4) & 1
        self.StockOnTheFork = (sensor >> 5) & 1
        self.forkTipDetection1 = (sensor >> 6) & 1
        self.forkTipDetection2 = (sensor >> 7) & 1
        self.liftInPlace = (sensor >> 8) & 1
        self.liftHomePosition = (sensor >> 9) & 1
        self.upperLimit = (sensor >> 10) & 1
        self.lowerLimit = (sensor >> 11) & 1

    def to_json(self):
        sensor_dict = {
            "reachOutInPlace": self.reachOutInPlace,
            "withdrawInPlace": self.withdrawInPlace,
            "forkHomePosition": self.forkHomePosition,
            "frontLimit": self.frontLimit,
            "backLimit": self.backLimit,
            "StockOnTheFork": self.StockOnTheFork,
            "forkTipDetection1": self.forkTipDetection1,
            "forkTipDetection2": self.forkTipDetection2,
            "liftInPlace": self.liftInPlace,
            "liftHomePosition": self.liftHomePosition,
            "upperLimit": self.upperLimit,
            "lowerLimit": self.lowerLimit
        }
        return sensor_dict


class GantryError:
    """
    """
    beforeLimitAlarm: int
    afterLimitAlarm: int
    initFail: int
    stretchRunTimeout: int
    stretchSyncErr: int
    stretchDriveAlarm: int
    upLimitAlarm: int
    downLimitAlarm: int
    liftRunTimeout: int
    HydraulicSystemErr: int
    liftDriveAlarm: int
    liftEncoderDataErr: int
    overWeight: int
    prong: int
    noGoodsStretch: int
    widthCheckFirmError: int

    def update(self, value):
        self.beforeLimitAlarm = (value >> 0) & 1
        self.afterLimitAlarm = (value >> 1) & 1
        self.initFail = (value >> 2) & 1
        self.stretchRunTimeout = (value >> 3) & 1
        self.stretchSyncErr = (value >> 4) & 1
        self.stretchDriveAlarm = (value >> 5) & 1
        self.upLimitAlarm = (value >> 6) & 1
        self.downLimitAlarm = (value >> 7) & 1
        self.liftRunTimeout = (value >> 8) & 1
        self.HydraulicSystemErr = (value >> 9) & 1
        self.liftDriveAlarm = (value >> 10) & 1
        self.liftEncoderDataErr = (value >> 11) & 1
        self.overWeight = (value >> 12) & 1
        self.prong = (value >> 13) & 1
        self.noGoodsStretch = (value >> 14) & 1
        self.widthCheckFirmError = (value >> 15) & 1

    def to_json(self):
        error_dict = {
            "beforeLimitAlarm": self.beforeLimitAlarm,
            "afterLimitAlarm": self.afterLimitAlarm,
            "initFail": self.initFail,
            "stretchRunTimeout": self.stretchRunTimeout,
            "stretchSyncErr": self.stretchSyncErr,
            "stretchDriveAlarm": self.stretchDriveAlarm,
            "upLimitAlarm": self.upLimitAlarm,
            "downLimitAlarm": self.downLimitAlarm,
            "liftRunTimeout": self.liftRunTimeout,
            "HydraulicSystemErr": self.HydraulicSystemErr,
            "liftDriveAlarm": self.liftDriveAlarm,
            "LiftEncoderDataErr": self.liftEncoderDataErr,
            "overWeight": self.overWeight,
            "prong": self.prong,
            "noGoodsStretch": self.noGoodsStretch,
            "widthCheckFirmError": self.widthCheckFirmError
        }
        return error_dict


class GantryFault:
    """
        bit0:识别到的托盘码与下发信息不一致
        bit1:识别不到托盘码
        bit2：重量对比错误
    """
    readNoEqualByOrder: int
    readCodeFault: int
    weightComparisonError: int

    def update(self, value):
        self.readNoEqualByOrder = (value >> 0) & 1
        self.readCodeFault = (value >> 1) & 1
        self.weightComparisonError = (value >> 2) & 1

    def to_json(self):
        fault_dict = {
            "readNoEqualByOrder": self.readNoEqualByOrder,
            "readCodeFault": self.readCodeFault,
            "weightComparisonError": self.weightComparisonError
        }
        return fault_dict

    def __str__(self):
        return self.to_json()


class MotorStatus(enum.IntEnum):
    PAUSE = 0
    STRETCH = 1
    BACK = 2
    FINISH = 3


class ActionCommand(enum.IntEnum):
    RESET = 0
    ACTION = 1


class Mode(enum.IntEnum):
    MANUAL = 0
    AUTO = 1


class BlockingType:
    NODE = "node"
    EDGE = "edge"


class ForkLift:
    def __init__(self, height):
        self.status = MoveStatus.NONE
        self.init = True
        self.height = height
        self.depth = None

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, m: Module):
        if self.init:
            if m.PLC.ready:
                m.lift_action_opt = [False] * 4
                self.init = False

        if self.status != MoveStatus.FINISHED and not self.init:
            r.setNotice("ForkLift running---")
            if m.lift_action(r, self.height):
                self.status = MoveStatus.FINISHED
        task_state = dict()
        task_state["status"] = self.status
        task_state["height"] = self.height
        task_state["PLC_lift_status"] = m.PLC.lift_status
        task_state["PLC_lift_position"] = m.PLC.lift_position
        r.logDebug(json.dumps(task_state))
        m.report_data["ForkLift"] = task_state


class PalletCodeRec:
    """
    PLC 二維碼識別
    """

    def __init__(self, load_id, timeout=20):
        self.status = MoveStatus.NONE
        self.load_id = load_id
        self.init = True
        self.start_time = time.time()
        self.timeout = timeout  # 超时时间

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, m: Module):
        self.status = MoveStatus.RUNNING

        r.logDebug(f"--------------PalletCodeRec running-----------------")
        task_state = dict()
        if self.init:
            if m.PLC.ready:
                self.init = False
                self.start_time = time.time()
        if self.status != MoveStatus.FINISHED and not self.init:
            if m.pallet_rec_action(r, self.load_id):
                self.status = MoveStatus.FINISHED
            else:
                if m.PLC.pallet_code == '' or m.PLC.pallet_code == 'NG':
                    if time.time() - self.start_time > self.timeout:
                        r.setError(
                            f"二維碼識別 超时 {self.timeout}，pallet_rec_action error:PLC.pallet_code:{m.PLC.pallet_code},pallet_code:{self.load_id}")
                        self.status = MoveStatus.FAILED
                else:
                    if time.time() - self.start_time > 2:
                        if m.PLC.pallet_code != self.load_id:
                            r.setError(
                                f"栈板码不一致 {self.timeout}，pallet_rec_action error:PLC.pallet_code:{m.PLC.pallet_code},pallet_code:{self.load_id}")

        task_state["status"] = self.status
        task_state["load_id"] = self.load_id
        task_state["PLC_code"] = m.PLC.pallet_code
        r.logDebug(json.dumps(task_state))
        m.report_data["PalletCodeRec"] = task_state


class PreLiftHeightAdjust:

    def __init__(self, task: dict):
        self.status = MoveStatus.NONE
        self.task = task
        self.height = None
        self.init = True

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, m: Module):
        task_state = dict()
        if self.init:
            self.height = self.task.get("height", None)
            if self.height is None:
                self.status = MoveStatus.FAILED
                r.logDebug(f"action parameters height is: {self.height}")
            self.init = False
        if self.status != MoveStatus.FINISHED:
            if m.lift_action(r, self.height):
                self.status = MoveStatus.FINISHED
        task_state["task"] = self.task
        task_state["height"] = self.height
        task_state["status"] = self.status
        r.logDebug(json.dumps(task_state))


class Rec:
    def __init__(self, filename):
        self.yaw = None
        self.y = None
        self.status = MoveStatus.NONE
        self.filename = filename
        self.rec_times = 0
        self.max_rec_times = 10
        self.result = dict()
        self.is_palletWidth = False

    def run(self, r: SimModule, m: Module):
        self.status = MoveStatus.RUNNING
        task_state = dict()
        rec_status = r.getRecStatus()  # 获取识别状态 0: 初始化, 1: 识别中, 2: 获得结果, 3：识别出错, -1: 未知错误
        if rec_status == 3 or rec_status == -1:  # 识别失败的状态
            r.setNotice("rec failed:{}".format(self.result))
            if ModuleTool.delay(0.5):
                self.rec_times = self.rec_times + 1
                if self.rec_times > self.max_rec_times:
                    r.setError("栈板识别失败次数太多了 {}".format(self.max_rec_times))
                    self.status = MoveStatus.FAILED
                else:
                    r.resetRec()

        elif rec_status == 2:  # 识别成功,获得结果
            self.result: dict = r.getRecResult()
            self.result.pop("resultImg")
            if self.result:
                palletWidth = None
                if "palletWidth" in self.result:
                    palletWidth = self.result["palletWidth"]
                if "pallet_width" in self.result:
                    palletWidth = self.result["pallet_width"]
                if palletWidth and palletWidth >= m.palletWidth:
                    r.setNotice(f"栈板识别，货物超宽,识别为{palletWidth}m,超 {palletWidth - m.palletWidth} m")
                    self.is_palletWidth = True
                    m.is_palletWidth = self.is_palletWidth
                m.result = self.result
                self.y = self.result["y"]
                self.yaw = self.result["yaw"]
                r.resetRec()
                if abs(self.y) >= m.y_adjust_max:
                    r.setError(f"栈板识别，左右偏差太大，偏差{self.y * 100}cm")
                    self.status = MoveStatus.FAILED
                    return
                if abs(self.yaw) >= m.yaw_adjust_max:
                    r.setError(f"栈板识别，角度偏差太大，偏差{180 / math.pi * self.yaw}°")
                    self.status = MoveStatus.FAILED
                    return
                # 开始计算目标点的世界坐标系
                robot2world = [r.loc().get("x"), r.loc().get("y"), r.loc().get("angle")]  # 小车在世界坐标系的位置

                pallet_rec_dist = [self.result['x'] + m.back_dist, self.result['y'], self.result['yaw']]  # 栈板识别的坐标补偿

                """计算栈板世界坐标系"""
                fork2base = [0.0, m.fork_len, -math.pi / 2]  # 叉尖相对里程中心坐标

                pallet2base_dist = Pos2World(pallet_rec_dist, fork2base)  # 栈板相对里程中心的坐标

                pallet2world = Pos2World(pallet2base_dist, robot2world)  # 栈板的世界坐标系
                m.pallet2world = pallet2world

                """计算栈板前置点坐标系"""
                pallet_rec = [self.result['x'], self.result['y'], self.result['yaw']]  # 栈板识别的坐标

                pallet2base = Pos2World(pallet_rec, fork2base)  # 栈板相对里程中心的坐标

                pallet2world = Pos2World(pallet2base, robot2world)  # 栈板的世界坐标系

                robot2pallet = Pos2Base(robot2world, pallet2world)  # 机器人相对于栈板的坐标

                target2pallet = [robot2pallet[0], 0, 0]  # 计算 目标点 相对于栈板的坐标

                pallet2robot = Pos2Base(target2pallet, robot2pallet)  # 目标点 相对于机器人的坐标

                target2world = Pos2World(pallet2robot, robot2world)  # 将目标点转为世界坐标系

                m.target2world = target2world
                m.pallet2robot = pallet2robot

                task_state['target2world'] = target2world
                task_state['pallet_world'] = pallet2world

                self.status = MoveStatus.FINISHED
                r.setNotice(f"rec success: {self.status.name} {self.result}")
        else:
            r.setNotice(f"--------------- doRec ----------------")
            r.doRecWithAngle(self.filename, 0.0)

        task_state['rec_result'] = self.result
        task_state['rec_count'] = self.rec_times
        task_state['rec_task_status'] = self.status
        task_state['rec_status'] = rec_status
        task_state['file'] = self.filename
        task_state['m.target2world'] = m.target2world
        m.report_data['rec_info'] = task_state
        task_state["status"] = self.status
        r.logDebug(json.dumps(task_state))

    def reset(self, r):
        # r.resetRec()
        self.status = MoveStatus.RUNNING


class AdjustPos:
    def __init__(self, r, rec_file):
        self.task_id = 0
        self.task_list = [Rec(rec_file), GoTargetPre(r)]
        self.status = MoveStatus.NONE
        self.state = dict()
        self.x = None
        self.y = None
        self.yaw = None
        self.init = False

    def run(self, r: SimModule, m: Module):
        self.status = MoveStatus.RUNNING
        if m.result and not self.init:  # 成功获取识别结果
            # r.resetRec()           # 重置识别模块
            self.init = True

        if self.task_id < len(self.task_list):
            if self.task_list[self.task_id].status == MoveStatus.NONE:
                self.task_list[self.task_id].reset(m)
            elif self.task_list[self.task_id].status == MoveStatus.FINISHED:
                self.task_id = self.task_id + 1
            else:
                self.task_list[self.task_id].run(r, m)
        else:
            self.status = MoveStatus.FINISHED
        self.state['status'] = self.status
        self.state['len(self.task_list)'] = len(self.task_list)
        self.state['task_id'] = self.task_id

        m.report_data["AdjustPos"] = self.state

    def reset(self, r):
        self.status = MoveStatus.RUNNING


def int_array_convert_to_string(datas):
    data = datas
    print(data)
    chars = [chr(d & 0xFF) for d in data]
    print(''.join(chars))
    return ''.join(chars)


def string_convert_to_int_array(string: str) -> List[int]:
    # 将字符串的每个字符转换为对应的 ASCII 码，并存储到整型数组中
    int_array = [ord(char) for char in string]
    return int_array


def Pos2Base(pos2world, base2world):
    """将基于世界坐标系的两个位姿，转换为基于base的位姿

    Args:
        pos2world ([3]): 被转换的位姿，基于世界坐标系,0:x, 1:y, 2: theta
        base2world ([3]): 基准，基于世界坐标系,0:x, 1:y, 2: theta
    Returns:
        [3]: pos2base
    """
    pos2base = [0., 0., 0.]
    x = pos2world[0] - base2world[0]
    y = pos2world[1] - base2world[1]
    pos2base[0] = x * math.cos(base2world[2]) + y * math.sin(base2world[2])
    pos2base[1] = -x * math.sin(base2world[2]) + y * math.cos(base2world[2])
    pos2base[2] = normalize_theta(pos2world[2] - base2world[2])
    return pos2base


def normalize_theta(theta):
    if theta >= -math.pi and theta < math.pi:
        return theta
    multiplier = math.floor(theta / (2 * math.pi))
    theta = theta - multiplier * 2 * math.pi
    if theta >= math.pi:
        theta = theta - 2 * math.pi
    if theta < -math.pi:
        theta = theta + 2 * math.pi
    return theta


def Pos2World(pos2base, base2world):
    """将位姿转换为世界坐标系

    Args:
        pos2base ([3]): 被转换的位姿，基于base. 0:x, 1:y, 2: theta
        base2world ([3]): 基准位姿. 0:x, 1:y, 2: theta

    Returns:
        [type]: pos2world
    """
    pos2world = [0., 0., 0.]
    x = pos2base[0] * math.cos(base2world[2]) - pos2base[1] * math.sin(base2world[2])
    y = pos2base[0] * math.sin(base2world[2]) + pos2base[1] * math.cos(base2world[2])
    pos2world[0] = x + base2world[0]
    pos2world[1] = y + base2world[1]
    pos2world[2] = normalize_theta(pos2base[2] + base2world[2])
    return pos2world


class SwitchMode:
    """切换模式 """

    def __init__(self, task: int):
        self.status = MoveStatus.NONE
        self.mode = task
        self.height = None
        self.init = True

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, m: Module):
        task_state = dict()
        if self.init:
            if self.mode is None:
                self.status = MoveStatus.FAILED
                r.logDebug(f"action parameters mode is: {self.mode}")
            self.init = False
        if self.status != MoveStatus.FINISHED:
            if m.switch_mode_action(r, self.mode):
                self.status = MoveStatus.FINISHED
        task_state["task"] = self.mode
        task_state["height"] = self.height
        task_state["status"] = self.status
        m.report_data["SwitchMode"] = task_state
        r.logDebug(json.dumps(task_state))


class Weigh:
    """称重"""

    def __init__(self, weight):
        self.status = MoveStatus.NONE
        self.weight = weight
        self.weigh_opt = [False] * 2
        self.init = True
        self.start_time = time.time()
        self.timeout = 60  # 超时时间

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, m: Module):
        self.status = MoveStatus.RUNNING
        task_state = dict()
        if self.init:
            # 等待PLC 就绪
            if m.PLC.ready:
                self.init = False
        if self.status != MoveStatus.FINISHED and not self.init:
            if not self.weigh_opt[0]:
                if m.weigh_action(r, self.weight):
                    self.weigh_opt[0] = True
            elif not self.weigh_opt[1] and self.weigh_opt[0]:
                r.setNotice(
                    f"PLC.cargo_weight {m.PLC.cargo_weight},weight:{self.weight},{m.PLC.cargo_weight == self.weight}")
                if m.PLC.cargo_weight:

                    if m.PLC.cargo_weight <= self.weight:
                        r.setNotice("PLC  weigh ok")
                        self.weigh_opt[1] = True
                    if m.PLC.cargo_weight >= self.weight:
                        r.setError(f" 超重")
                        self.status = MoveStatus.FAILED
            if all(self.weigh_opt):
                self.status = MoveStatus.FINISHED
        if time.time() - self.start_time > self.timeout:
            r.setError(f"称重超时： {self.timeout}")
            self.status = MoveStatus.FAILED
        task_state["weigh"] = self.weight
        task_state["PLC_weigh"] = m.PLC.cargo_weight
        task_state["status"] = self.status
        m.report_data["Weigh"] = task_state
        r.logDebug(json.dumps(task_state))


class MiniForklift:
    """微抬升 ，抬起，下降"""

    def __init__(self, operation: str):
        self.operation = operation
        self.status = MoveStatus.NONE
        self.position = None
        self.init = True

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, m: Module):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.position = m.PLC.lift_position
            m.lift_action_opt = [False] * 4
            if m.is_palletWidth:
                if m.PLC.lift_position < m.palletWidth_height:
                    self.position = m.palletWidth_height
                else:
                    if self.operation == "pick":
                        self.position += m.forklift_micro_height_pick
                    if self.operation == "drop":
                        self.position -= m.forklift_micro_height_drop
            else:
                if self.operation == "pick":
                    self.position += m.forklift_micro_height_pick
                if self.operation == "drop":
                    self.position -= m.forklift_micro_height_drop
            self.init = False
        task_state = dict()
        if not self.init and self.status != MoveStatus.FINISHED:
            if self.operation == "pick":
                # 抬起时检测是否有货，没有货则报错
                if m.PLC.gantry_sensor_status.StockOnTheFork:
                    if m.lift_action(r, self.position):
                        self.status = MoveStatus.FINISHED
                else:
                    r.setError(f"抬货叉时没有检测到位")
                    self.status = MoveStatus.FAILED
            if self.operation == "drop":
                if m.lift_action(r, self.position):
                    self.status = MoveStatus.FINISHED

        task_state["operation"] = self.operation
        task_state["status"] = self.status
        m.report_data["MiniForklift"] = task_state


class Stretch:
    """根据输入，判断是伸叉还是收叉

    """

    def __init__(self, action: str):
        self.stretch_action_opt = [False] * 2
        self.action = action
        self.status = MoveStatus.NONE
        self.is_action = False
        self.init = False

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, m: Module):
        task_state = dict()
        self.status = MoveStatus.RUNNING
        if not self.init:
            self.init = True
            m.stretch_action_opt = [False] * 2
        if self.status != MoveStatus.FINISHED:
            if self.action == "go":
                if m.stretch_go_action():
                    m.get_plc_info(r)
                    self.is_action = True

            elif self.action == "back":
                if m.stretch_back_action():
                    m.get_plc_info(r)
                    self.is_action = True
            if self.is_action:
                stretch_status = m.modbus_tcp.execute(1, cst.READ_HOLDING_REGISTERS, m.stretch_status_addr, 1)[0]
                m.get_plc_info(r)
                if self.action == "back":
                    if stretch_status == 3 and m.PLC.gantry_sensor_status.withdrawInPlace:
                        self.status = MoveStatus.FINISHED
                if self.action == "go":
                    if stretch_status == 3 and m.PLC.gantry_sensor_status.reachOutInPlace:
                        self.status = MoveStatus.FINISHED
        if self.action == "go":
            if m.PLC.gantry_sensor_status.forkTipDetection1 or m.PLC.gantry_sensor_status.forkTipDetection2:
                r.setError(f"货叉碰到东西了,{m.PLC.gantry_sensor_status.forkTipDetection1},"
                           f"{m.PLC.gantry_sensor_status.forkTipDetection2}")
                self.status = MoveStatus.FAILED
        task_state["status"] = self.status
        task_state["stretch_status"] = m.PLC.stretch_status
        task_state["action"] = self.action
        task_state["is_action"] = self.is_action
        task_state["reachOutInPlace"] = m.PLC.gantry_sensor_status.reachOutInPlace
        task_state["withdrawInPlace"] = m.PLC.gantry_sensor_status.withdrawInPlace
        m.report_data["Stretch"] = task_state


class GoTargetPre:
    """导航到与栈板对正的位置
    """

    def __init__(self, r, speed=0.08):
        self.goPath = goPath.Module(r, dict())
        self.init = False
        self.status = MoveStatus.NONE
        self.go_args = dict()
        self.speed = speed
        self.x = None
        self.y = None
        self.theta = None

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, m: Module):
        self.status = MoveStatus.RUNNING
        task_state = dict()

        if not self.init:
            self.init = True
            self.x = m.target2world[0]
            self.y = m.target2world[1]
            self.theta = m.result['yaw'] + m.robot_pos[2]
            self.go_args["coordinate"] = "world"
            self.go_args["x"] = self.x
            self.go_args["y"] = self.y
            self.go_args["theta"] = self.theta
            self.go_args["reachDist"] = 0.003
            self.go_args["reachAngle"] = 0.002
            self.go_args["useOdo"] = 1
            self.go_args["maxSpeed"] = m.speed_adjust_max
            self.go_args["hold_dir"] = (180 / math.pi) * (r.loc().get("angle", 0))

            self.status = MoveStatus.RUNNING
            self.goPath.status = MoveStatus.RUNNING
            if abs(m.result["y"]) <= m.y_dist and abs(m.result["yaw"]) <= m.yaw_dist:
                self.status = MoveStatus.FINISHED
                return

        if self.goPath.status != MoveStatus.FINISHED or self.goPath.status != MoveStatus.FAILED:
            self.goPath.run(r, self.go_args)
        if self.goPath.status == MoveStatus.FINISHED:
            self.status = MoveStatus.FINISHED

        task_state["status"] = self.status
        task_state["init"] = self.init
        task_state["go_args"] = self.go_args
        m.report_data["GoTargetPre"] = task_state


class GoTargetPreByRobot:
    """导航到与栈板对正的位置
    """

    def __init__(self, r, speed=0.08):
        self.goPath = goPath.Module(r, dict())
        self.init = False
        self.status = MoveStatus.NONE
        self.go_args = dict()
        self.speed = speed
        self.x = None
        self.y = None
        self.theta = None

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, m: Module):
        self.status = MoveStatus.RUNNING
        task_state = dict()
        if not self.init:
            self.init = True

            def move(dx, dy, yaw):
                if abs(yaw) >= 3.0916:
                    return dy
                if yaw < 0:
                    return dy - dx * math.tan(math.pi + yaw)
                else:
                    return dy + dx * math.tan(math.pi - yaw)

            code2camera = [m.result['x'], m.result['y'], m.result['z'],
                           m.result['yaw']]  # 目标点在相机坐标系的位置
            task_state["code2camera"] = code2camera
            self.go_args["coordinate"] = "robot"
            # 根据下发货叉的角度，判断行走方向
            self.go_args["x"] = move(m.result['x'] - 0.8, m.result['y'], m.result['yaw'])
            self.go_args["y"] = 0
            self.go_args["theta"] = m.result['yaw'] * 1.03
            self.go_args["reachAngle"] = 0.01
            self.go_args["useOdo"] = 1
            self.go_args["reachDist"] = 0.002
            if self.go_args["x"] < 0:
                self.go_args["backMode"] = 1
            if abs(m.result["y"]) <= m.y_dist and abs(m.result["yaw"]) <= m.yaw_dist:
                self.status = MoveStatus.FINISHED
                return
        if self.goPath.status != MoveStatus.FINISHED or self.goPath.status != MoveStatus.FAILED:
            self.goPath.run(r, self.go_args)
        if self.goPath.status == MoveStatus.FINISHED:
            self.status = MoveStatus.FINISHED

        task_state["status"] = self.status
        task_state["go_args"] = self.go_args
        m.report_data["GoTargetPreByRobot"] = task_state


class Translate:
    """平移
    接受两个参数，平移距离 dist，和平移的方向 angle。
    两个参数都有正负，一般通过 angle 控制方向
    """

    def __init__(self, r: SimModule, angle, dist, speed=0.5):
        self.goPath = goPath.Module(r, dict())
        self.init = False
        self.dist = dist
        self.angle = angle
        self.status = MoveStatus.NONE
        self.go_args = dict()
        self.speed = speed
        radians = math.radians(self.angle)
        self.x = self.dist * math.cos(radians)
        self.y = self.dist * math.sin(radians)
        self.t2world = None

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, m: Module):
        self.status = MoveStatus.RUNNING
        task_state = dict()
        if not self.init:
            self.init = True
            robot2world = [r.loc().get("x", None), r.loc().get("y", None), r.loc().get("angle", 0)]
            t = [self.x, self.y, 0]
            self.t2world = Pos2World(t, robot2world)  # 栈板的世界坐标系
            self.status = MoveStatus.RUNNING
            self.goPath.status = MoveStatus.RUNNING
        if self.goPath.status != MoveStatus.FINISHED or self.goPath.status != MoveStatus.FAILED:
            if self.t2world:
                self.go_args["coordinate"] = "world"
                self.go_args["x"] = self.t2world[0]
                self.go_args["y"] = self.t2world[1]
                self.go_args["reachDist"] = 0.003
                self.go_args["reachAngle"] = math.pi
                self.go_args["useOdo"] = 1
                self.go_args["maxSpeed"] = self.speed
                self.go_args["hold_dir"] = (180 / math.pi) * (r.loc().get("angle", 0))
                task_state["go_args"] = self.go_args
                self.goPath.run(r, self.go_args)
        if self.goPath.status == MoveStatus.FINISHED:
            self.status = MoveStatus.FINISHED

        task_state["status"] = self.status
        task_state["init"] = self.init
        task_state["go_args"] = self.go_args
        task_state["angle"] = self.angle
        task_state["dist"] = self.dist
        m.report_data["Translate"] = task_state


class TranslateByRobot:
    def __init__(self, r: SimModule, speed=0.8):
        self.goPath = goPath.Module(r, dict())
        self.init = False
        self.status = MoveStatus.NONE
        self.go_args = dict()
        self.speed = speed
        self.t2world = None

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, m: Module):
        m.PLC.gantry_sensor_status.StockOnTheFork
        self.status = MoveStatus.RUNNING
        task_state = dict()
        if not self.init:
            self.init = True
            self.goPath.status = MoveStatus.RUNNING
            self.go_args["coordinate"] = "robot"
            self.go_args["x"] = 0
            l = math.sqrt((m.pallet2world[0] - m.target2world[0]) ** 2 + (m.pallet2world[1] - m.target2world[1]) ** 2)
            self.go_args["y"] = l - m.contact_di_to_odo
            # self.go_args["y"] = 1.06/(m.result["yaw"]+1.06)*math.sqrt((m.pallet2world[0] - m.target2world[0]) ** 2 + (m.pallet2world[1] - m.target2world[1]) ** 2)
            self.go_args["reachDist"] = 0.003
            self.go_args["reachAngle"] = math.pi
            self.go_args["useOdo"] = 1
            self.go_args["maxSpeed"] = self.speed
            self.go_args["hold_dir"] = (180 / math.pi) * (r.loc().get("angle", 0))
        if self.goPath.status != MoveStatus.FINISHED or self.goPath.status != MoveStatus.FAILED:
            self.goPath.run(r, self.go_args)
        if self.goPath.status == MoveStatus.FINISHED:
            self.status = MoveStatus.FINISHED

        task_state["status"] = self.status
        task_state["init"] = self.init
        task_state["go_args"] = self.go_args
        m.report_data["Translate"] = task_state


class TranslateByPos:
    """移动到栈板是世界坐标
    """

    def __init__(self, r: SimModule, speed=0.1):
        self.goPath = goPath.Module(r, dict())
        self.init = False
        self.status = MoveStatus.NONE
        self.go_args = dict()
        self.speed = speed
        self.target_pos = []  # [x,y,yaw]
        self.angel = 0
        self.reachAngle = 0.0005

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, m: Module):
        self.status = MoveStatus.RUNNING
        task_state = dict()
        if not self.init:
            self.init = True
            self.go_args["coordinate"] = "world"
            if self.target_pos:
                self.go_args["x"] = self.target_pos[0]
                self.go_args["y"] = self.target_pos[1]
                self.go_args["theta"] = self.target_pos[2] + self.angel
            else:
                r.setError(f"NO target_pos:{self.target_pos}")
            self.go_args["reachDist"] = 0.0005
            self.go_args["reachAngle"] = self.reachAngle
            self.go_args["useOdo"] = 1
            self.go_args["maxSpeed"] = self.speed
            self.go_args["hold_dir"] = (180 / math.pi) * (r.loc().get("angle", 0))
            self.status = MoveStatus.RUNNING
            self.goPath.status = MoveStatus.RUNNING
        if self.goPath.status != MoveStatus.FINISHED or self.goPath.status != MoveStatus.FAILED:
            self.goPath.run(r, self.go_args)
        if self.goPath.status == MoveStatus.FINISHED:
            self.status = MoveStatus.FINISHED
        if self.status == MoveStatus.FAILED:
            r.setError(f"平移失败")
        task_state["status"] = self.status
        task_state["target_pos"] = self.target_pos
        task_state["init"] = self.init
        task_state["go_args"] = self.go_args
        m.report_data["TranslateByPos"] = task_state


class AngleAction:
    """让车体转到某个角度

    """

    def __init__(self, r: SimModule, angle):
        self.goPath = goPath.Module(r, dict())
        self.init = True
        self.angle = angle
        self.status = MoveStatus.NONE
        self.go_args = dict()

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, m: Module):
        task_state = dict()
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            radians = math.radians(self.angle)
            self.go_args["coordinate"] = "robot"
            self.go_args["x"] = 0.001
            self.go_args["reachDist"] = 0.003
            self.go_args["y"] = 0.00
            self.go_args["theta"] = radians
            self.go_args["reachAngle"] = 0.001

        self.status = self.goPath.run(r, self.go_args)


class TranslateStretch:
    """
    边平移边伸叉
    """

    def __init__(self, r: SimModule, angle, dist, action):
        self.Translate = Translate(r, angle, dist)
        self.Stretch = Stretch(action)
        self.action = action
        self.dist = dist
        self.angle = angle
        self.init = True
        self.status = MoveStatus.NONE

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, m: Module):
        task_state = dict()
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            self.Translate.reset(m)
            self.Stretch.reset(m)
            if self.action == "go":
                self.Translate.speed = m.Translate_speed_max_go
            if self.action == "back":
                self.Translate.speed = m.Translate_speed_max_back
        if self.status != MoveStatus.FINISHED and not self.init:
            if self.Translate.status != MoveStatus.FINISHED:
                self.Translate.run(r, m)
            if self.Stretch.status != MoveStatus.FINISHED:
                self.Stretch.run(r, m)
            if self.Translate.status == MoveStatus.FINISHED and self.Stretch.status == MoveStatus.FINISHED:
                self.status = MoveStatus.FINISHED
            if self.Translate.status == MoveStatus.FAILED or self.Stretch.status == MoveStatus.FAILED:
                self.status = MoveStatus.FAILED
                r.setError(f"边走边伸叉任务失败")
        if m.operation == "pick" and self.action == "go":
            if m.PLC.gantry_sensor_status.StockOnTheFork:
                self.Translate.status = MoveStatus.FINISHED
        task_state["status"] = self.status
        task_state["m.robot_pos"] = m.robot_pos
        task_state["action"] = self.action
        task_state["angle"] = self.angle
        task_state["dist"] = self.dist
        task_state["init"] = self.init
        m.report_data["TranslateStretch"] = task_state


class SetGoodsModule:
    """设置货物模型"""

    def __init__(self, operation):
        self.operation = operation
        self.status = MoveStatus.NONE
        self.init = True

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, m: Module):
        task_state = dict()
        if self.init:
            self.init = False
            if not self.operation:
                r.setError(f"设置货物模型 operation error:{self.operation}")
                self.status = MoveStatus.FAILED
        self.status = MoveStatus.RUNNING
        if self.status != MoveStatus.FINISHED:
            if self.operation == "pick":
                r.setLocalShelfArea(m.rec_file)
                self.status = MoveStatus.FINISHED
            if self.operation == "drop":
                r.clearGoodsShape()
                self.status = MoveStatus.FINISHED
        task_state["operation"] = self.operation
        task_state["status"] = self.status
        m.report_data["SetGoodsModule"] = task_state


class GetRobotPos:
    """记录当前位置
    """

    def __init__(self):
        self.y = None
        self.yaw = None
        self.x = None
        self.status = MoveStatus.NONE

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, m: Module):
        task_state = dict()
        self.status = MoveStatus.RUNNING
        self.x = r.loc().get('x', None)
        self.y = r.loc().get('y', None)
        self.yaw = r.loc().get("angle", 0)
        m.robot_pos = [self.x, self.y, self.yaw]
        self.status = MoveStatus.FINISHED
        task_state["status"] = self.status
        task_state["init_robot_pos"] = m.robot_pos
        m.report_data["SetGoodsModule"] = task_state


class SlowTranslate:
    """缓慢平移小段距离
    """

    def __init__(self, r):
        self.goPath = goPath.Module(r, dict())
        self.init = False
        self.status = MoveStatus.NONE
        self.go_args = dict()
        self.t2world = None

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, m: Module):
        self.status = MoveStatus.RUNNING
        task_state = dict()
        if not self.init:
            self.init = True
            robot2world = [r.loc().get("x", None), r.loc().get("y", None), r.loc().get("angle", 0)]
            x = m.back_dist * math.cos(math.radians(m.angle)) * 2
            y = m.back_dist * math.sin(math.radians(m.angle)) * 2
            t = [x, y, 0]
            self.t2world = Pos2World(t, robot2world)  # 栈板的世界坐标系
            self.goPath.status = MoveStatus.RUNNING
        if self.goPath.status != MoveStatus.FINISHED or self.goPath.status != MoveStatus.FAILED:
            if self.t2world:
                self.go_args["coordinate"] = "world"
                self.go_args["x"] = self.t2world[0]
                self.go_args["y"] = self.t2world[1]
                self.go_args["reachDist"] = 0.01
                self.go_args["reachAngle"] = math.pi
                self.go_args["useOdo"] = 1
                self.go_args["maxSpeed"] = 0.03     #缓慢速度4米五是0.05-0.06，6米是0.03
                self.go_args["hold_dir"] = (180 / math.pi) * (r.loc().get("angle", 0))
                task_state["status"] = self.go_args["hold_dir"]
                self.goPath.run(r, self.go_args)
        if self.goPath.status == MoveStatus.FINISHED:
            self.status = MoveStatus.FINISHED
        task_state["status"] = self.status
        task_state["go_args"] = self.go_args
        m.report_data["SlowTranslate"] = task_state


class TranslateStretchByPos:
    """
    边平移边伸叉
    """

    def __init__(self, r: SimModule, action):
        if action == 'go':
            self.Translate = TranslateByRobot(r)
        if action == 'back':
            self.Translate = TranslateByPos(r)
        self.Stretch = Stretch(action)
        self.action = action
        self.init = True
        self.status = MoveStatus.NONE
        self.SlowTranslate = SlowTranslate(r)

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, m: Module):
        task_state = dict()
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            self.Translate.reset(m)
            self.Stretch.reset(m)
            if self.action == "go":
                self.Translate.target_pos = m.pallet2world
                self.Translate.angel = math.pi / 2
                self.Translate.reachAngle = math.pi
            if self.action == "back":
                self.Translate.speed = m.Translate_speed_max_back
                self.Translate.angel = 0.005
                self.Translate.reachAngle = math.pi
                if m.robot_pos:
                    self.Translate.target_pos = m.robot_pos
                else:
                    r.setError(f"没有获取到机器人坐标{m.robot_pos} ")
        if self.status != MoveStatus.FINISHED and not self.init:
            if self.Translate.status != MoveStatus.FINISHED:
                self.Translate.run(r, m)
            if self.Stretch.status != MoveStatus.FINISHED:
                self.Stretch.run(r, m)

            if self.Translate.status == MoveStatus.FAILED or self.Stretch.status == MoveStatus.FAILED:
                self.status = MoveStatus.FAILED
        if m.operation == "pick" and self.action == "go":
            if m.PLC.gantry_sensor_status.StockOnTheFork:
                self.Translate.status = MoveStatus.FINISHED
                self.SlowTranslate.status = MoveStatus.FINISHED
                if self.Stretch.status == MoveStatus.FINISHED:
                    self.status = MoveStatus.FINISHED
            if self.Translate.status == MoveStatus.FINISHED and not m.PLC.gantry_sensor_status.StockOnTheFork:
                if self.SlowTranslate.status != MoveStatus.FINISHED:
                    self.SlowTranslate.run(r, m)
        if self.action == "back":
            if self.Translate.status == MoveStatus.FINISHED and self.Stretch.status == MoveStatus.FINISHED:
                self.status = MoveStatus.FINISHED
        task_state["status"] = self.status
        task_state["m.robot_pos"] = m.robot_pos
        task_state["action"] = self.action
        task_state["init"] = self.init
        m.report_data["TranslateStretchByPos"] = task_state


class OpenDO:
    """打开DO"""

    def __init__(self, task: list):
        super().__init__()
        self.status = MoveStatus.NONE
        self.task = task
        self.opt = [False] * len(self.task)

    def run(self, r: SimModule, m: Module):
        self.status = MoveStatus.RUNNING
        task_state = dict()
        if self.status != MoveStatus.FINISHED:
            for i, t in enumerate(self.task):
                r.setDO(t, True)
                self.opt[i] = True
        if all(self.opt):
            self.status = MoveStatus.FINISHED
        task_state["task"] = self.task
        task_state["status"] = self.status
        m.report_data["OpenDO"] = task_state

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING


class CloseDO:
    """关闭DO"""

    def __init__(self, task: list):
        super().__init__()
        self.status = MoveStatus.NONE
        self.task = task
        self.opt = [False] * len(self.task)

    def run(self, r: SimModule, m: Module):
        self.status = MoveStatus.RUNNING
        task_state = dict()
        if self.status != MoveStatus.FINISHED:
            for i, t in enumerate(self.task):
                r.setDO(t, False)
                self.opt[i] = True
        if all(self.opt):
            self.status = MoveStatus.FINISHED
        task_state["task"] = self.task
        task_state["status"] = self.status
        m.report_data["CloseDO"] = task_state

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING


