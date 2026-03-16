# -*- coding: utf-8 -*-
# @Date : 2025/06/10
# @Author : chen
# @Coding : none
# @File : cleanRobotMech.py
#
# 说明:
# - 只负责清洁车机构控制(刷盘/水扒/吸风/喷水/加水排污)
# - 所有"策略 + 调度 + 自动充电/换水/定时任务"等由 cleanRobotManage 负责
# - 本脚本通过 args 中的 operation 和参数来执行一次动作(类似 GoPath)
#
"""
####BEGIN DEFAULT ARGS####
{
  "operation": {
    "value": "WashStart",
    "default_value": [
      "WashStart",
      "WashEnd",
      "DustStart",
      "DustEnd",
      "AddWater",
      "CheckInfo"
    ],
    "tips": "机构操作类型",
    "type": "complex"
  },
  "auto_adjust": {
    "value": 1,
    "tips": "是否启动电机功率自动调节模式, 1: 启动, 0: 不启动, 参数可缺省",
    "type": "int"
  },
  "push_rod_length": {
    "value": 75,
    "tips": "刷盘推杆行程, 取值: 70-100, 刷盘下降的高度,参数可缺省",
    "type": "int"
  },
  "brush_power": {
    "value": 67,
    "tips": "刷盘电机功率, 取值: 0-100, 0即关闭,100即满功率, 参数可缺省",
    "type": "int"
  },
  "suck_power": {
    "value": 50,
    "tips": "吸风电机功率, 取值: 0-100, 0即关闭, 100即满功率, 参数可缺省",
    "type": "int"
  },
  "jet_power": {
    "value": 20,
    "tips": "喷水电机功率, 取值: 0-100, 0即关闭, 100即满功率, 参数可缺省",
    "type": "int"
  }
}
####END DEFAULT ARGS####
"""

import json
import time
from enum import IntEnum
from typing import Optional

from syspy.utils.param_server import ParamType, ScriptParam

param_loader = ScriptParam(__file__)
from syspy.lib.robot_param import RobotParam
import can
import base64
import modbus_tk.defines as cst
from modbus_tk import modbus_tcp

start_time = time.time()
from syspy import Module, Logger, Battery, Do, Navigation, Abnormal, ScriptStatus, Odometer, Controller, Trace, Can, NavStatus, NavSpeed, Loc

log = Logger("clean_robot")


class ConfigParams:
    """生成和定义配置参数"""
    config = {}

    def __init__(self):
        self._build_and_load_config()

    @classmethod
    def _build_and_load_config(cls):
        """构建并加载配置参数"""
        module_type = RobotParam.getDevice("Model-000", "moduleType")
        builder = param_loader.builderConfig()

        with builder.GROUPS():
            # 基础配置组
            with builder.GROUP(key="basicConfig", name="Basic Configuration", desc="Basic configuration parameters"):
                builder.TYPE(ParamType.ARRAY)

                with builder.CHILDREN():
                    with builder.CHILD(key="timeout", name="timeout", desc="脚本运行超时时间"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(120, min_value=0.000, max_value=999)
                        builder.UNIT("s")
                        builder.SINGLESTEP(0.001)

                    with builder.CHILD(key="min_clean_water_level", name="min_clean_water_level",
                                       desc="清水液位最小值,达到此值机器人停止工作去加水"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(5.0)
                        builder.SINGLESTEP(0.001)

                    with builder.CHILD(key="max_clean_water_level", name="max_clean_water_level",
                                       desc="清水液位最大值,达到此值机器人停止加水"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(95.0)
                        builder.SINGLESTEP(0.001)

                    with builder.CHILD(key="min_waste_water_level", name="min_waste_water_level",
                                       desc="污水液位最小值,达到此值机器人停止排污"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(1.0)
                        builder.SINGLESTEP(0.001)

                    with builder.CHILD(key="max_waste_water_level", name="max_waste_water_level",
                                       desc="污水液位最大值,达到此值机器人停止工作去排污"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(90.0)
                        builder.SINGLESTEP(0.001)

                    with builder.CHILD(key="add_water_do", name="add_water_do", desc="加水DO"):
                        builder.TYPE(ParamType.STRING)
                        builder.DEFAULTVALUE("DO-004")
                        builder.SINGLESTEP(1)

                    with builder.CHILD(key="brush_power", name="brush_power", desc="刷盘电机默认功率"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(67)
                        builder.SINGLESTEP(1)

                    with builder.CHILD(key="suck_power", name="suck_power", desc="吸风电机默认功率"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(50)
                        builder.SINGLESTEP(1)

                    with builder.CHILD(key="jet_power", name="jet_power", desc="喷水泵电机默认功率"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(20)
                        builder.SINGLESTEP(1)

                    with builder.CHILD(key="auto_adjust_power", name="auto_adjust_power",
                                       desc="是否启动电机功率自动调节模式, 1: 启动, 0: 不启动"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(1)
                        builder.SINGLESTEP(1)

                    with builder.CHILD(key="add_water_delay_time", name="add_water_delay_time",
                                       desc="加水延时关闭时间"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(5.0)
                        builder.SINGLESTEP(1.0)

                    with builder.CHILD(key="close_jet_delay_time", name="close_jet_delay_time",
                                       desc="关闭喷水电机后延时停止清洁工作的时间"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(8.0)
                        builder.SINGLESTEP(1.0)

                    with builder.CHILD(key="high_mode_x_speed", name="high_mode_x_speed",
                                       desc="x速度大于该值时, 清洁机构以高功率工作"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.8)
                        builder.SINGLESTEP(0.1)

                    with builder.CHILD(key="std_mode_x_speed", name="std_mode_x_speed",
                                       desc="x速度大于该值时, 清洁机构以标准功率工作"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.4)
                        builder.SINGLESTEP(0.1)

                    with builder.CHILD(key="stop_x_speed", name="stop_x_speed",
                                       desc="x速度大于该值时, 清洁机构以低功率工作, x速度小于该值时, 清洁机构停止工作"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.05)
                        builder.SINGLESTEP(0.1)

                    with builder.CHILD(key="push_rod_length", name="push_rod_length",
                                       desc="推杆电机下压距离"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(75)
                        builder.SINGLESTEP(1)

        builder.save(merge=True)
        cls.reload_config()

    @classmethod
    def reload_config(cls):
        """重新加载配置参数"""
        Trace.log("Reloading config parameters")
        cls.config = param_loader.loadConfig()
        Trace.log(f"Loaded config: {cls.config}")
        cls.timeout = cls.config.get("timeout")
        cls.min_clean_water_level = cls.config.get("min_clean_water_level")
        cls.max_clean_water_level = cls.config.get("max_clean_water_level")
        cls.min_waste_water_level = cls.config.get("min_waste_water_level")
        cls.max_waste_water_level = cls.config.get("max_waste_water_level")
        cls.add_water_do = cls.config.get("add_water_do")
        cls.brush_power = cls.config.get("brush_power")
        cls.suck_power = cls.config.get("suck_power")
        cls.jet_power = cls.config.get("jet_power")
        cls.auto_adjust_power = cls.config.get("auto_adjust_power")
        cls.add_water_delay_time = cls.config.get("add_water_delay_time")
        cls.close_jet_delay_time = cls.config.get("close_jet_delay_time")
        cls.high_mode_x_speed = cls.config.get("high_mode_x_speed")
        cls.std_mode_x_speed = cls.config.get("std_mode_x_speed")
        cls.stop_x_speed = cls.config.get("stop_x_speed")
        cls.push_rod_length = cls.config.get("push_rod_length")

config_params = ConfigParams()

def script_config_callback():
    """配置参数更改回调"""
    Trace.log("Reloading script config parameters")
    config_params.reload_config()


class CleanRobot:
    """清洁机器人主控制类"""

    def __init__(self):
        # 加载配置

        # Modbus TCP 连接
        self.ip = "127.0.0.1"
        self.port = 502
        self.modbus_tcp = modbus_tcp.TcpMaster(self.ip, self.port, 1)
        self.is_connected = False
        self.rbk_addr = 110  # rbk寄存器清水液位数据地址

        # 清洁机构工作状态
        self.brush_status = None
        self.jet_status = None
        self.suck_status = None
        self.brush_lift_status = None
        self.push_rod_status = None
        self.mop_lift_status = None
        self.clean_valve_status = None
        self.waste_valve_status = None
        self.clean_robot_working = None  # 所有机构全部工作
        self.clean_robot_closed = None  # 所有机构全部停止
        self.work_mode = WorkMode.STD

        # 计数器和时间戳
        self.period_run_start = time.time()
        self.task_update_start = time.time()
        self.period_run_counter = 0
        self.opt_run_counter = 0

        # 上报信息
        self.report_info = {}
        self.action_status = ScriptStatus.NONE
        self.operation = None
        self.init = False
        self.args = {}

        # 时间戳
        self.wash_start_time = None
        self.add_water_time_start = None
        self.close_jet_pump_start = None
        self.add_water_opt_start = False

        # 清洁机器人硬件接口
        self.clean_robot_hw = CleanRobotHardware(self)

        # 液位数据
        self.clean_water_level = -1
        self.waste_water_level = -1
        self.clean_filter = MeanValue(1000)  # 清水液位滤波
        self.waste_filter = MeanValue(1000)  # 污水液位滤波

        # 从args获取的参数
        self.auto_adjust_power = config_params.auto_adjust_power
        self.jet_power = config_params.jet_power
        self.brush_power = config_params.brush_power
        self.suck_power = config_params.suck_power
        self.push_rod_length = config_params.push_rod_length

        log.info(f"CleanRobot initialized")

    def period_run(self):
        """周期性运行函数"""
        self.period_run_counter += 1

        # 等待机器人开机缓冲,等待时间为100次循环(2s)
        if self.period_run_counter < 100:
            return True

        # 刚开机时,复位机构
        if (self.args == {} or self.args == [""]) and self.period_run_counter == 100:
            self.reset()

        self.update_report_info()  # 更新上报数据
        self.update_all_info()  # 同步清洁机器人各机构的工作状态

        if not self.is_connected:
            self.connect()

        # 0.2秒更新一次
        if time.time() - self.task_update_start > 0.2:
            self.task_update_start = time.time()
            self.save_to_rbk()  # 同步液位数据到RBK
            self.update_by_task_status()  # 根据任务状态处理业务逻辑

            # data = Navigation.moveTask()
            # if data is not None:
            #     log.info(json.dumps(data))

        # 0.5秒更新一次
        if time.time() - self.period_run_start > 0.5:
            self.period_run_start = time.time()
            Module.reportInfo(self.report_info)  # 数据上报
            # log.info(json.dumps(self.report_info))  # 日志打印

        return True

    def run(self, args: dict):
        """主运行函数"""
        self.opt_run_counter += 1
        self.action_status = ScriptStatus.RUNNING

        if not self.init:
            self.init = True
            self.update_all_info()  # 同步清洁机器人各机构的工作状态
            self.operation = args.get("operation", None)
            self.auto_adjust_power = args.get("auto_adjust", config_params.auto_adjust_power)
            self.jet_power = int(args.get("jet_power", config_params.jet_power))
            self.brush_power = int(args.get("brush_power", config_params.brush_power))
            self.suck_power = int(args.get("suck_power", config_params.suck_power))
            self.push_rod_length = int(args.get("push_rod_length", config_params.push_rod_length))

        if self.operation == "WashStart":
            self.wash_start()
        elif self.operation == "WashEnd":
            self.wash_end()
        elif self.operation == "DustStart":
            self.dust_start()
        elif self.operation == "DustEnd":
            self.dust_end()
        elif self.operation == "AddWater":
            self.add_water()
        elif self.operation == "CheckInfo":
            self.update_all_info()
        else:
            Abnormal.setTask(53910, f"args error: {self.operation}", "参数错误", "检查operation参数", "run")
            self.action_status = ScriptStatus.FAILED

        self.update_all_info()  # 同步清洁机器人各机构的工作状态
        self.report_info['args'] = args
        self.report_info['operation'] = self.operation
        log.info(f"clean robot info: {json.dumps(self.report_info)}")
        return self.action_status

    def update_by_task_status(self):
        """根据任务状态更新清洁机构状态"""
        task_status = NavStatus.getTaskStatus()

        if task_status == 2:  # Running
            if self.operation == "WashStart" and self.action_status == ScriptStatus.FINISHED:
                # self.update_power_by_speed()
                self.wash_open()
        elif task_status == 3:  # Suspended
            self.wash_suspend()
        elif task_status == 5:  # Failed
            self.wash_end()
        elif task_status == 6:  # Canceled
            self.wash_suspend()

        # 急停信号检测
        if Controller.getEmc():
            self.wash_end()

        # 水位检测,清水空了或者污水满了,结束清洁任务
        loc_state = Loc.getLocState()
        if self.filter_waste_water_level() > config_params.max_waste_water_level:
            Abnormal.setTask(53980, "Waste water is full!", "污水满", "去排水", "update_by_task_status")
            if self.operation != "AddWater" and loc_state == 1:  # 终止任务,过滤加水任务,且已完成重定位
                self.wash_end()
        elif self.filter_clean_water_level() < config_params.min_clean_water_level and self.filter_clean_water_level() != -1:
            Abnormal.setTask(53980, "Clean water is empty!", "清水空", "去加水", "update_by_task_status")
            if self.operation != "AddWater" and loc_state == 1:
                self.wash_end()
        else:
            if Abnormal.exists(53980):
                Abnormal.clear(53980)

    def update_power_by_speed(self):
        """根据车速自动调节电机功率"""
        agv_speed = NavSpeed.getSpeeds()

        if bool(self.auto_adjust_power):
            if agv_speed[0] > config_params.high_mode_x_speed:
                self.work_mode = WorkMode.HIGH
                self.suck_power, self.jet_power, self.brush_power = (70, 50, 67)
            elif config_params.std_mode_x_speed < agv_speed[0] < config_params.high_mode_x_speed:
                self.work_mode = WorkMode.STD
                self.suck_power, self.jet_power, self.brush_power = (50, 20, 67)
            elif config_params.stop_x_speed < agv_speed[0] < config_params.std_mode_x_speed or agv_speed[0] < agv_speed[
                2]:
                self.work_mode = WorkMode.LOW
                self.suck_power, self.jet_power, self.brush_power = (40, 10, 50)

        if agv_speed[0] < config_params.stop_x_speed:
            self.wash_suspend()
        else:
            self.wash_open()

    def connect(self):
        """连接Modbus TCP"""
        try:
            self.modbus_tcp.open()
        except Exception as e:
            log.info(f"connect error: {e}")
        else:
            self.is_connected = True

    def save_to_rbk(self):
        """保存液位数据到RBK"""
        try:
            self.modbus_tcp.execute(1, cst.WRITE_MULTIPLE_REGISTERS, self.rbk_addr,
                                    output_value=[round(self.filter_clean_water_level()),
                                                  round(self.filter_waste_water_level())])
        except Exception as e:
            log.info(f"save_to_rbk error: {e}")

    def update_report_info(self):
        """更新上报信息"""
        clean_robot = dict()
        clean_robot["cleanWaterLevel"] = self.filter_clean_water_level()
        clean_robot["wasteWaterLevel"] = self.filter_waste_water_level()

        agv_speed = dict()
        cur_speed = NavSpeed.getSpeeds()
        agv_speed[0] = round(cur_speed[0], 6)
        agv_speed['y'] = round(cur_speed[1], 6)
        agv_speed['rotate'] = round(cur_speed[2], 6)

        auto_adjust = dict()
        auto_adjust["auto_adjust"] = bool(self.auto_adjust_power)
        auto_adjust["work_mode"] = self.work_mode.name
        auto_adjust["suck_power"] = self.suck_power
        auto_adjust["jet_power"] = self.jet_power
        auto_adjust["brush_power"] = self.brush_power

        # self.report_info["auto_adjust"] = auto_adjust
        # self.report_info["cleanRobot"] = clean_robot
        # self.report_info["connected"] = self.is_connected
        # self.report_info["push_rod_length"] = self.push_rod_length
        # self.report_info["script_status"] = self.action_status
        # self.report_info["agv_speed"] = agv_speed
        # self.report_info["operation"] = self.operation
        # self.report_info["period_run_counter"] = self.period_run_counter
        # self.report_info["task_status"] = NavStatus.getTaskStatus()
        # self.report_info["time"] = time.strftime('%Y-%m-%d %H:%M:%S')
        self.report_info["update_report_info"] = {
            "auto_adjust":auto_adjust,
            "cleanRobot":clean_robot,
            "connected":self.is_connected,
            "push_rod_length": self.push_rod_length,
            "script_status":self.action_status,
            "agv_speed": agv_speed,
            "operation": self.operation,
            "period_run_counter": self.period_run_counter,
            "task_status": NavStatus.getTaskStatus(),
            "time": time.strftime('%Y-%m-%d %H:%M:%S')
        }
        Module.reportInfo(self.report_info)

    def wash_open(self):
        """打开清洁机构"""
        self.is_fit_push_rod() # 检查推杆下降距离是否合法

        if self.brush_lift_status != WorkingStatus.RUNNING:
            self.clean_robot_hw.ctrl_brush_lift(WorkState.OPEN)

        if self.mop_lift_status != WorkingStatus.RUNNING:
            self.clean_robot_hw.ctrl_mop_lift(WorkState.OPEN)
        elif self.clean_valve_status == WorkingStatus.RUNNING:
            self.clean_robot_hw.ctrl_clean_valve(WorkState.CLOSE)  # 关阀
        elif self.suck_status != WorkingStatus.RUNNING:
            self.clean_robot_hw.ctrl_suck(self.suck_power)
        elif self.brush_status != WorkingStatus.RUNNING:
            self.clean_robot_hw.ctrl_brush(self.brush_power)
        elif self.jet_status != WorkingStatus.RUNNING:
            self.clean_robot_hw.ctrl_jet_pump(self.jet_power)  # 开泵

    def is_fit_push_rod(self):
        """检查推杆下降距离是否合法"""
        if int(self.push_rod_length) < 70 or int(self.push_rod_length) > 100:
            Abnormal.setTask(53901,
                             f"Exceeding the length limit, Please be greater than 70 or less than 100, length: {self.push_rod_length}",
                             "推杆长度超限", "调整push_rod_length参数", "is_fit_push_rod")
            self.wash_end()
        else:
            self.clean_robot_hw.ctrl_pod_length(self.push_rod_length)

    def wash_start(self):
        """开始清洗"""
        self.operation = "WashStart"
        self.wash_open()
        if self.clean_robot_working:
            self.action_status = ScriptStatus.FINISHED

    def wash_water(self):
        """把水管中的水排空"""
        if self.operation == "WashEnd":
            if self.jet_status != WorkingStatus.RUNNING:
                self.clean_robot_hw.ctrl_jet_pump(self.jet_power)  # 开泵
            if self.clean_valve_status != WorkingStatus.RUNNING:
                self.clean_robot_hw.ctrl_clean_valve(WorkState.OPEN)  # 开阀

    def wash_end(self):
        """结束清洗"""
        self.operation = "WashEnd"
        Do.setDo(config_params.add_water_do, False)

        if self.waste_valve_status == WorkingStatus.RUNNING:
            self.clean_robot_hw.ctrl_waste_valve(WorkState.CLOSE)

        if not self.close_jet_pump_start:
            self.close_jet_pump_start = time.time()

        if not self.clean_robot_closed:
            if self.close_jet_pump_start and time.time() - self.close_jet_pump_start < 3:
                self.wash_water()

        # 延迟 close_jet_delay_time * 0.7 秒关闭水泵、水阀、刷盘电机和刷盘高度
        if self.close_jet_pump_start and time.time() - self.close_jet_pump_start > config_params.close_jet_delay_time * 0.7:
            if self.brush_status == WorkingStatus.RUNNING:
                self.clean_robot_hw.ctrl_brush(0)
            if self.jet_status == WorkingStatus.RUNNING:
                self.clean_robot_hw.ctrl_jet_pump(0)  # 关泵
            if self.clean_valve_status == WorkingStatus.RUNNING:
                self.clean_robot_hw.ctrl_clean_valve(WorkState.CLOSE)  # 关阀
            if self.brush_lift_status != WorkingStatus.INIT:
                self.clean_robot_hw.ctrl_brush_lift(WorkState.CLOSE)

        # 延迟 close_jet_delay_time 秒之后关闭吸风电机和水扒
        if self.close_jet_pump_start and time.time() - self.close_jet_pump_start > config_params.close_jet_delay_time:
            if self.mop_lift_status != WorkingStatus.INIT:
                self.clean_robot_hw.ctrl_mop_lift(WorkState.CLOSE)
            if self.suck_status == WorkingStatus.RUNNING:
                self.clean_robot_hw.ctrl_suck(0)

        if self.clean_robot_closed:
            self.close_jet_pump_start = None
            self.action_status = ScriptStatus.FINISHED

    def wash_suspend(self):
        """暂停清洗(开阀关泵)"""
        if self.brush_status == WorkingStatus.RUNNING:
            self.clean_robot_hw.ctrl_brush(0)
        if self.jet_status == WorkingStatus.RUNNING:
            self.clean_robot_hw.ctrl_jet_pump(0)  # 关泵
        if self.clean_valve_status != WorkingStatus.RUNNING:
            self.clean_robot_hw.ctrl_clean_valve(WorkState.OPEN)  # 开阀
        if self.waste_valve_status == WorkingStatus.RUNNING:
            self.clean_robot_hw.ctrl_waste_valve(WorkState.CLOSE)

        if bool(self.auto_adjust_power):
            self.work_mode = WorkMode.STOP
            self.suck_power, self.jet_power, self.brush_power = (0, 0, 0)

        # 延时 close_jet_delay_time 秒关闭吸风电机
        if not self.close_jet_pump_start:
            self.close_jet_pump_start = time.time()
        if self.close_jet_pump_start and time.time() - self.close_jet_pump_start > config_params.close_jet_delay_time:
            if self.suck_status == WorkingStatus.RUNNING:
                self.clean_robot_hw.ctrl_suck(0)

    def reset(self):
        """复位清洁机构"""
        if self.jet_status == WorkingStatus.RUNNING:
            self.clean_robot_hw.ctrl_jet_pump(0)  # 关泵
        if self.clean_valve_status == WorkingStatus.RUNNING:
            self.clean_robot_hw.ctrl_clean_valve(WorkState.CLOSE)  # 关阀

    def dust_start(self):
        """开始吸尘"""
        if self.mop_lift_status != WorkingStatus.RUNNING:
            self.clean_robot_hw.ctrl_mop_lift(WorkState.OPEN)
        if self.suck_status != WorkingStatus.RUNNING:
            self.clean_robot_hw.ctrl_suck(self.suck_power)
        else:
            self.action_status = ScriptStatus.FINISHED

    def dust_end(self):
        """结束吸尘"""
        if self.mop_lift_status != WorkingStatus.INIT:
            self.clean_robot_hw.ctrl_mop_lift(WorkState.CLOSE)
        if self.suck_status != WorkingStatus.INIT:
            self.clean_robot_hw.ctrl_suck(0)
        else:
            self.action_status = ScriptStatus.FINISHED

    def add_water(self):
        """加水排污"""
        is_charging = Battery.getIsCharging()

        if not is_charging:
            Do.setDo(config_params.add_water_do, False)
            self.clean_robot_hw.ctrl_waste_valve(WorkState.CLOSE)
            Abnormal.setTask(53900, "Not in charging state!", "未在充电状态", "移动到充电桩", "add_water")
            self.action_status = ScriptStatus.FAILED
        else:
            if not self.add_water_opt_start:
                Do.setDo(config_params.add_water_do, True)
                self.clean_robot_hw.ctrl_waste_valve(WorkState.OPEN)

        # 加水排污已处于工作状态
        if Do.getDo(config_params.add_water_do) and self.waste_valve_status == WorkingStatus.RUNNING:
            self.add_water_opt_start = True

        # 停止加水
        if self.clean_water_level >= config_params.max_clean_water_level:
            Do.setDo(config_params.add_water_do, False)

        # 停止排污
        if self.waste_water_level <= config_params.min_waste_water_level:
            self.clean_robot_hw.ctrl_waste_valve(WorkState.CLOSE)

        # 加水排污任务延时 add_water_delay_time 秒结束
        if self.waste_water_level <= config_params.min_waste_water_level and self.clean_water_level >= config_params.max_clean_water_level:
            if not self.add_water_time_start:
                self.add_water_time_start = time.time()
            if time.time() - self.add_water_time_start > config_params.add_water_delay_time:
                self.add_water_time_start = None
                self.add_water_opt_start = False
                self.action_status = ScriptStatus.FINISHED

        self.report_info["add_water_opt_start"] = self.add_water_opt_start
        self.report_info["is_charging"] = is_charging

    def filter_clean_water_level(self):
        """清水液位滤波"""
        if self.clean_water_level >= 0:
            self.clean_filter.add_value(self.clean_water_level)
            return self.clean_filter.get_mean_value()
        return self.clean_water_level

    def filter_waste_water_level(self):
        """污水液位滤波"""
        if self.waste_water_level >= 0:
            self.waste_filter.add_value(self.waste_water_level)
            return self.waste_filter.get_mean_value()
        return self.waste_water_level

    def update_all_info(self):
        """
        CAN报文数据解析:
        Bit0-7:   清水液位(类型:uint8 范围:0-100)
        Bit8-15:  污水液位(类型:uint8 范围:0-100)
        Bit16:    刷盘位置状态(类型:bit, 0:收起状态 1:工作状态,默认0)
        Bit17:    水扒位置状态(类型:bit, 0:收起状态 1:工作状态,默认0)
        Bit18:    清水阀门状态(类型:bit, 0:关闭状态 1:打开状态,默认0)
        Bit19:    污水阀门状态(类型:bit, 0:关闭状态 1:打开状态,默认0)
        Bit20:    吸风开关状态(类型:bit, 0:关闭状态 1:工作状态,默认0)
        Bit21:    刷盘开关状态(类型:bit, 0:关闭状态 1:工作状态,默认0)
        Bit22:    喷水电机状态(类型:bit, 0:关闭状态 1:工作状态,默认0)
        Bit23:    预留
        Bit24-31: 清洁组件高度状态(类型:uint8 范围:0-160对应真实值0-1600)
        """
        info = {}
        recv_data = self.clean_robot_hw.query_all_info()
        print(f"recv_data:{recv_data}")

        if self.clean_robot_hw.query_all_cmd_status == WorkingStatus.FINISHED:
            self.clean_robot_hw.query_all_cmd_status = WorkingStatus.INIT
            # 报文数据解析
            state = bin(int(recv_data[12:14], 16))[2:].zfill(8)  # 状态数据变为8位2进制
            self.clean_water_level = int(recv_data[8:10], 16)  # 清水液位
            self.waste_water_level = int(recv_data[10:12], 16)  # 污水液位
            self.push_rod_status = int(recv_data[14:16], 16)  # 解析并读取清洁组件高度状态
            self.jet_status = WorkingStatus(int(state[1:2]))
            self.brush_status = WorkingStatus(int(state[2:3]))
            self.suck_status = WorkingStatus(int(state[3:4]))
            self.waste_valve_status = WorkingStatus(int(state[4:5]))
            self.clean_valve_status = WorkingStatus(int(state[5:6]))
            self.mop_lift_status = WorkingStatus(int(state[6:7]))
            self.brush_lift_status = WorkingStatus(int(state[7:8]))
            self.clean_robot_working = all(list(map(int, state[1:4] + state[6:8])))  # 全工作时为True
            self.clean_robot_closed = not bool(max(list(map(int, state[1:4] + state[5:8]))))  # 全关闭时为True

        info['suck_state'] = self.suck_status
        info['brush_state'] = self.brush_status
        info['jet_pump_state'] = self.jet_status
        info['mop_lift_state'] = self.mop_lift_status
        info['brush_lift_state'] = self.brush_lift_status
        info['waste_valve_state'] = self.waste_valve_status
        info['clean_valve_state'] = self.clean_valve_status
        info['push_rod_state'] = self.push_rod_status
        self.report_info["work_status"] = info

    def cancel(self):
        """取消操作"""
        Trace.log("script cancel")
        Do.setDo(config_params.add_water_do, False)
        config_params.close_jet_delay_time = 5
        self.wash_end()
        self.action_status = ScriptStatus.FAILED


class CleanRobotHardware:
    """清洁机器人硬件控制接口"""

    def __init__(self, module_obj: CleanRobot):
        self.chanel = 2
        self.can_id = 0x605
        self.dlc = 8
        self.extend = False
        self.agv = module_obj
        self.brush_start_time = None
        self.default_data = '0' * 16
        self.has_send = False
        self.send_start = None
        self.send_wait_time = 0.01
        self.query_all_cmd_status = WorkingStatus.INIT

    def ctrl_suck(self, power=0):
        """控制吸风电机"""
        cmd = Cmd.SUCK
        cmd = cmd[:12] + hex(power)[2:].zfill(2) + cmd[14:]
        self.send_cmd(cmd)

    def ctrl_brush(self, power=0):
        """控制刷盘电机"""
        cmd = Cmd.BRUSH
        cmd = cmd[:12] + hex(power)[2:].zfill(2) + cmd[14:]
        self.send_cmd(cmd)

    def ctrl_jet_pump(self, power=0):
        """控制喷水泵"""
        cmd = Cmd.JET_PUMP
        cmd = cmd[:12] + hex(power)[2:].zfill(2) + cmd[14:]
        self.send_cmd(cmd)

    def ctrl_pod_length(self, power=0):
        """控制推杆长度"""
        cmd = Cmd.BRUSH_POD_DOWN
        cmd = cmd[:12] + hex(power)[2:].zfill(2) + cmd[14:]
        self.send_cmd(cmd)

    def ctrl_brush_lift(self, state):
        """控制刷盘升降"""
        if state is WorkState.OPEN:
            cmd = Cmd.BRUSH_LIFT_DOWN
        else:
            cmd = Cmd.BRUSH_LIFT_UP
        self.send_cmd(cmd)

    def ctrl_mop_lift(self, state):
        """控制水扒升降"""
        if state is WorkState.OPEN:
            cmd = Cmd.MOP_LIFT_DOWN
        else:
            cmd = Cmd.MOP_LIFT_UP
        self.send_cmd(cmd)

    def ctrl_clean_valve(self, state):
        """控制清水阀门"""
        if state is WorkState.OPEN:
            cmd = Cmd.WATER_VALVE_OPEN
        else:
            cmd = Cmd.WATER_VALVE_CLOSE
        self.send_cmd(cmd)

    def ctrl_waste_valve(self, state):
        """控制污水阀门"""
        if state is WorkState.OPEN:
            cmd = Cmd.BRAIN_BALL_VALVE_OPEN
        else:
            cmd = Cmd.BRAIN_BALL_VALVE_CLOSE
        self.send_cmd(cmd)

    def ctrl_open_all(self, mode):
        """打开所有机构"""
        cmd = Cmd.SET_ALL_STD
        if mode == WorkMode.STD:
            cmd = Cmd.SET_ALL_STD  # 标准功率打开
        elif mode == WorkMode.LOW:
            cmd = Cmd.SET_ALL_LOW  # 低功率打开
        elif mode == WorkMode.HIGH:
            cmd = Cmd.SET_ALL_HIGH  # 高功率打开
        elif mode == WorkMode.STOP:
            cmd = Cmd.SET_ALL_CLOSED  # 关闭
        self.agv.report_info['ctrl_open_all'] = cmd
        self.send_cmd(cmd)

    def ctrl_close_all(self):
        """关闭所有机构"""
        cmd = Cmd.SET_ALL_CLOSED
        self.send_cmd(cmd)

    def query_all_info(self):
        """查询所有机构状态"""
        self.query_all_cmd_status = WorkingStatus.RUNNING
        recv_data = self.send_cmd(Cmd.QUERY_ALL_INFO)
        # print(f"recv_data:{recv_data[:8]}")
        if recv_data[:8] == "43034000":  # 报文地址匹配
            self.query_all_cmd_status = WorkingStatus.FINISHED
            self.agv.report_info['query_all_info'] = recv_data
            return recv_data
        return self.default_data

    def send_cmd(self, cmd):
        """发送CAN指令"""
        Can.sendCanFrame(self.chanel, self.can_id, self.dlc, self.extend, cmd)
        data = Can.getData()
        # print(f"data:{data}")
        b64_str = data.get('data', '')
        can_id = data.get('id', 0)
        hex_str = base64.b64decode(b64_str).hex().upper()
        # print(f"hex_str:{hex_str}")
        if can_id + 128 == self.can_id:
            return hex_str
        return self.default_data


# --- 枚举定义 ---

class WorkingStatus(IntEnum):
    """工作状态枚举"""
    INIT = 0
    RUNNING = 1
    FINISHED = 2


class WorkState(IntEnum):
    """工作状态(开/关)枚举"""
    CLOSE = 0
    OPEN = 1


class WorkMode(IntEnum):
    """工作模式枚举"""
    LOW = 0
    STD = 1
    HIGH = 2
    STOP = 3


# --- 通用类 ---

class Cmd:
    """
    电机控制指令格式   "2B 80 30 " + "addr" + "power" + " 00 00 00"
    电机查询指令格式   "40 80 30 " + "addr" + " 00 00 00 00"
    """
    SUCK = "2B 80 30 01 00 00 00 00"  # 吸风电机
    BRUSH = "2B 80 30 02 00 00 00 00"  # 刷盘电机
    JET_PUMP = "2B 80 30 03 00 00 00 00"  # 清水喷水泵
    BRUSH_LIFT_UP = "2B 80 30 04 64 00 00 00"  # 刷盘升降推杆上升
    BRUSH_LIFT_DOWN = "2B 80 30 04 FF 9C 00 00"  # 刷盘升降推杆下降
    BRUSH_POD_DOWN = "2B 86 30 01 00 00 00 00"  # 刷盘推杆下降
    MOP_LIFT_UP = "2B 80 30 05 FF 9C 00 00"  # 水扒升降推杆上升
    MOP_LIFT_DOWN = "2B 80 30 05 64 00 00 00"  # 水扒升降推杆下降
    WATER_VALVE_OPEN = "2B 80 30 06 64 00 00 00"  # 喷水阀开
    WATER_VALVE_CLOSE = "2B 80 30 06 00 00 00 00"  # 喷水阀关
    BRAIN_BALL_VALVE_OPEN = "2B 80 30 07 64 00 00 00"  # 排水球阀开
    BRAIN_BALL_VALVE_CLOSE = "2B 80 30 07 00 00 00 00"  # 排水球阀关

    QUERY_SUCK = "40 80 30 01 00 00 00 00"  # 查询吸风电机信息
    QUERY_BRUSH = "40 80 30 02 00 00 00 00"  # 查询刷盘电机信息
    QUERY_JET_PUMP = "40 80 30 03 00 00 00 00"  # 查询喷水泵电机信息
    QUERY_BRUSH_LIFT = "40 80 30 04 00 00 00 00"  # 查询刷盘推杆电机信息
    QUERY_MOP_LIFT = "40 80 30 05 00 00 00 00"  # 查询水扒升降信息
    QUERY_WATER_VALVE = "40 80 30 06 00 00 00 00"  # 查询喷水阀信息
    QUERY_BALL_VALVE = "40 80 30 07 00 00 00 00"  # 查询排水球阀信息

    QUERY_CLEAN_WATER_LEVEL = "40 8B 30 03 00 00 00 00"  # 查询清水液位计
    QUERY_WASTE_WATER_LEVEL = "40 8B 30 04 00 00 00 00"  # 查询污水液位计

    SET_CAN_TIMEOUT = "2B 01 40 00 00 00 00 00"  # 设置CAN通信超时时间, 2字节
    SET_ALL_STD = "23 02 40 00 32 43 1E 07"  # 以标准功率设定全部机构
    SET_ALL_LOW = "23 02 40 00 28 32 14 07"  # 以低档模式设定全部机构
    SET_ALL_HIGH = "23 02 40 00 46 50 32 07"  # 以高档模式设定全部机构
    SET_ALL_CLOSED = "23 02 40 00 00 00 00 00"  # 设定全部机构关闭
    QUERY_ALL_INFO = "40 03 40 00 00 00 00 00"  # 查询所有机构的运行状态


class MeanValue:
    """均值滤波"""

    def __init__(self, window_size=1000):
        self.window_size = window_size
        self.data = []
        self.threshold = 10

    def add_value(self, v):
        """添加数值"""
        self.data.append(v)
        while len(self.data) > self.window_size:
            self.data.pop(0)

    def get_mean_value(self) -> float:
        """获取均值"""
        return round(sum(self.data) / len(self.data), 3)


if __name__ == '__main__':
    ScriptParam.setConfigChangeCallBack(script_config_callback)

    Module.init()
    c = CleanRobot()
    c.action_status = ScriptStatus.NONE
    while True:
        c.period_run()
        if c.action_status != ScriptStatus.FINISHED:
            c.run({"operation": "WashEnd"})
            print(f"-------11-------{c.action_status}---------------")
            time.sleep(0.2)
        print(f"--------22------{c.action_status}---------------")
    # c.period_run()
