# -*- coding: utf-8 -*-
# @Date : 2025/05/13
# @Author : zengweibin
# @Coding : none
# @Update : 3.5顶升车示例模板

import json
import math
import time
from enum import IntEnum
from syspy.utils.time import Timer
start_time = time.time()

from syspy import Module, ParamServer, Logger, Di, Do, Motor, Navigation, Loc, Abnormal, Recognize, ScriptStatus, Odometer, Pgv
from syspy.lib.module import Pos2Base, Pos2World
import goPath

log = Logger("jack")


# --- Module 类（放在前面） ---
class ConfigParams:
    """生成和定义配置参数的示例"""
    param_server = ParamServer(__file__)
    timeout = param_server.loadParam("timeout", type="int", default=120, maxValue=999, minValue=0, unit="s",
                                     group="", comment="脚本运行超时时间")
    # 是否有识别、二次调整
    is_recognize = param_server.loadParam("is_recognize", type="bool", default=True, comment="取货是否有识别")
    is_secondary_adjust = param_server.loadParam("is_secondary_adjust", type="bool", default=False,
                                                 comment="是否有二次调整")
    is_goods_qrcode = param_server.loadParam("goods_qrcode", type="bool", default=False,
                                             comment="放货时是否需要根据货物在托盘上的位置补偿AP点偏差")

    # 采用什么方式前往AP点
    how_go_site = param_server.loadParam("how_go_site", type="str", default="bezier",
                                         comment="采用直线(straight)、贝塞尔曲线(bezier)、2段直线(polyline)方式前往识别点")

    # 电机相关
    jack_motor_name = param_server.loadParam("jack_motor_name", type="str", default="Motor-003", comment="顶升电机名称")
    jack_motor_speed = param_server.loadParam("jack_motor_speed", type="float", default=0.015,
                                              comment="顶升电机升降速度")
    jack_lift_zero = param_server.loadParam("jack_lift_zero", type="float", default=0.000, comment="顶升升降零位")
    jack_height = param_server.loadParam("jack_height", type="float", default=0.03, comment="顶升抬升指定高度")
    jack_up_di = param_server.loadParam("jack_up_di", type="int", default=6, comment="顶升机构上极限DI")
    jack_zero_di = param_server.loadParam("jack_zero_di", type="int", default=3, comment="顶升机构零位DI")
    spin_motor_name = param_server.loadParam("spin_motor_name", type="str", default="Motor-002",
                                             comment="托盘旋转电机名称")

    # 测试前近距离
    go_distance = param_server.loadParam("go_distance", type="float", default=0.5, comment="测试前进距离")

    log.debug("jack create config params")


class Jack:
    def __init__(self):
        super().__init__()
        self.action_id = 0
        self.action_list = []
        self.operation_init = False
        # 定义脚本运行相关的成员变量
        self.ap_world_pos = None # 定义ap点在世界坐标系的位置
        self.ap_robot_pos = None # 定义ap点在机器人坐标系的位置
        self.ap_id = None
        self.coordinate = None  # 定义坐标系
        self.spin_angle = None
        self.action_parameters = None  # vda
        self.opt = None
        self.recfile = None
        self.spin_zero = None  # 取货前旋转托盘到零位
        # 取货前调整托盘旋转
        self.global_spin_angle_before_jack = None
        self.increase_spin_angle_before_jack = None
        self.robot_spin_angle_before_jack = None
        self.spin_dir = None

        # 货架识别
        self.rec_result = []
        self.recfile_data = None
        self.shelfLength = None
        # 二维码识别
        self.code_info = dict()

        # 数据打印
        self.report_info = {}
        log.info(f"self.action_list")
        Abnormal.clear(55900)

        self.countcount = 0

    def run(self):
        # 获取输入参数
        """
        "operation": {
        "value": "load",
        "default_value":["jackLoad","jackUnload","goAPSite","jackHeight","jackMinHeight","goDist","recShelf","PGVSecondaryAdjust"],
        "tips":"动作类型",
        "type":"complex"
        }，
        "recfile":{
        "value":"default.srec",
        "tips":"识别文件名称",
        "type":"string"
        },
        "spin_zero":{
        "value":True,
        "tips":"取货前是否将托盘回到零位",
        "type":"bool"
        },
        "robot_spin_angle_before_jack":{
        "value":0.01,
        "tips":"取货前旋转托盘角度,机器人坐标系",
        "type":"float"
        },
        "increase_spin_angle_before_jack":{
        "value":0.01,
        "tips":"取货前旋转托盘角度，增量式",
        "type":"float"
        },
        "global_spin_angle_before_jack":{
        "value":0.01,
        "tips":"取货前旋转托盘角度，世界坐标系",
        "type":"float"
        },
        "spin_direction": {
        "value": "2",
        "tips": "托盘旋转方向,0-ccw,1-cw,2-shortest",
        "type": "int"
        },
        """
        Module.set_status(ScriptStatus.RUNNING)
        # 获取任务参数
        self.ap_id = Module.get_task_args("AP_id", None)
        self.opt = Module.get_task_args("operation", None)
        self.recfile = Module.get_task_args("recfile", None)
        self.spin_zero = Module.get_task_args("spin_zero", True)
        self.robot_spin_angle_before_jack = Module.get_task_args("robot_spin_angle_before_jack", None)
        self.increase_spin_angle_before_jack = Module.get_task_args("increase_spin_angle_before_jack", None)
        self.global_spin_angle_before_jack = Module.get_task_args("global_spin_angle_before_jack", None)
        self.spin_dir = Module.get_task_args("spin_dir", 0)
        self.spin_angle = Module.get_task_args("spin_angle", 0)  # 角度
            # 把spin_angle转为rad
        rad = math.radians(self.spin_angle)
            # 归一化到 (-pi, pi]
        self.spin_angle = (rad + math.pi) % (2 * math.pi) - math.pi
        self.coordinate = Module.get_task_args("coordinate", "world")
        log.info(f"{Module.get_task_args=}")
        log.info(f"Module.get_task_args={Module.get_task_args}")

        self.set_vda_param()

        # 选择执行动作
        if self.opt == "jackLoad":  # 识别/非识别取货
            self.jack_load()
        elif self.opt == "jackUnload":  # 识别/非识别放货
            self.jack_unload()
        elif self.opt == "goAPSite":  # 前往ap点，直线，bezier，两段线
            self.go_ap_site()
        elif self.opt == "goBezier":
            self.go_bezier()
        elif self.opt == "goPolyline":
            self.go_polyline()
        elif self.opt == "jackHeight":  # 控制托盘抬升高度
            self.jack_height()
        elif self.opt == "jackMinHeight":  # 控制托盘高度降到最低
            self.jack_min_height()
        elif self.opt == "spinAngle":  # 托盘旋转指定角度
            self.spin()
        elif self.opt == "spinZero":  # 托盘旋转到0度
            self.spin_zero_deg()
        elif self.opt == "rotateHoldSpin":  # 随动转
            self.rotate_hold_spin()
        elif self.opt == "goMapPath":  # 前进一段距离
            self.go_map_path()
        elif self.opt == "goDist":  # 直线前进一段距离
            self.go_dist()
        elif self.opt == "goPath":  # 直线到达目标点（世界/机器人坐标系）
            self.go_path()
        elif self.opt == "recShelf":  # 识别货架
            self.rec_shelf()
        elif self.opt == "getRec":  # 识别货架
            self.get_recfile_result(object_key="shelf")
        elif self.opt == "PGVSecondaryAdjust":  # 通过pgv二次调整
            self.pgv_adjust()
        else:
            Module.set_status(ScriptStatus.FAILED)

        log.info(f"self.action_list: {self.action_list}")
        self._execute_actions()

    def set_vda_param(self):
        # VDA下发的参数
        self.action_parameters = Module.get_task_args("action_parameters", None)

    def jack_load(self):
        # =====完整：旋转车体调整对准——识别货架——导航——二次调整——顶起 流程=====
        if not self.operation_init:
            self.operation_init = True

            # 获取AP点坐标
            if not self.ap_id:
                self.ap_id = Navigation.moveTask().get("target_name", None)
                self.ap_id = "AP" + str(self.ap_id)
            self.ap_world_pos = Navigation.getLM(self.ap_id, True)  # AP在世界坐标系下的位置
            self.ap_robot_pos = Navigation.getLM(self.ap_id, False)
            robot_loc = [Loc.get_position()[0], Loc.get_position()[1], math.radians(Loc.get_angle()[0])]
            ap_to_robot_angle = math.atan2(self.ap_world_pos[1] - robot_loc[1], self.ap_world_pos[0] - robot_loc[0])
            log.info(f'AP_pos: {self.ap_world_pos}')
            log.info(f'ap_to_robot_angle: {ap_to_robot_angle}')

            self.report_info["jack_load"] = {
                "ap_to_robot_angle": ap_to_robot_angle,
                "robot_loc": robot_loc,
                "ap_world_pos": self.ap_world_pos
            }

            # 第一步转到指向ap点的方向
            self.action_list.append(RobotRotate(ap_to_robot_angle,Coordinate.WORLD,False))

            # 第二步判断是否有识别
                # 如果有识别 # 改为输入参数n
            if ConfigParams.is_recognize:  # 要求启用识别时必须有recfile
                self.recfile_data = self.get_recfile_result()  # 获取识别文件数据放入字典中
                self.shelfLength = self.recfile_data["recognitionParameter"]["shelfLength"]
                # 转到指向ap点的位置
                self.action_list.append(RecShelf(self.recfile,"FirstRec"))  # 识别货架，得到坐标放入j.rec_result

            else:
                # 如果没有识别，直接前进到任务的AP点坐标

                if ConfigParams.how_go_site == "straight":
                    self.action_list.append(GoPath(self.ap_world_pos, Coordinate.WORLD))
                elif ConfigParams.how_go_site == "bezier":
                    self.action_list.append(GoBezier(self.ap_world_pos))
                elif ConfigParams.how_go_site == "polyline":
                    self.action_list.append(GoPolyline(self.ap_world_pos))
                self.jack_load_adjust_and_jack()  # 加入二次调整，取货前托盘调整，抬升托盘动作

        # 动态添加action_list
        if 0 <= self.action_id < len(self.action_list):
            current_action = self.action_list[self.action_id]
            log.info(f'{self.action_id=}, {self.action_list=}')
            log.info(f'{current_action.action_name=}, {current_action.action_status=}')

            if current_action.action_name == "FirstRec" and current_action.action_status == ActionStatus.FINISHED:
                result_world = self.rec_result
                robot_pos = [Loc.get_position()[0], Loc.get_position()[1], math.radians(Loc.get_angle()[0])]
                result_robot = Pos2Base(result_world,robot_pos)

                self.report_info["jack_load"] = {
                    "result_robot": result_robot,
                    "result_world": result_world,
                    "robot_pos": robot_pos
                }

                # 如果离shelf太近，先后退一段距离再第二次识别（离太近可能存在偏差）
                if result_robot[0] < 0.5:
                    log.info(f'{current_action.action_name=}')
                    self.action_list.append(GoPath([-0.3,0,0],Coordinate.ROBOT,0.2,True))
                    self.action_list.append(RecShelf(self.recfile, "SecondRec"))  # 识别货架，得到坐标放入j.rec_result
                else:
                    self.action_list.append(GoBezier(result_world))
                    # self.jack_load_adjust_and_jack()  # 加入二次调整，取货前托盘调整，抬升托盘动作
                    self.action_list.append(JackHeight(ConfigParams.jack_motor_name, ConfigParams.jack_height,
                                                       ConfigParams.jack_motor_speed, ConfigParams.jack_up_di))

            if current_action.action_name == "SecondRec" and current_action.action_status == ActionStatus.FINISHED:
                result_world = self.rec_result
                self.action_list.append(GoBezier(result_world))
                # self.jack_load_adjust_and_jack() # 加入二次调整，取货前托盘调整，抬升托盘动作
                self.action_list.append(JackHeight(ConfigParams.jack_motor_name, ConfigParams.jack_height,
                                                   ConfigParams.jack_motor_speed, ConfigParams.jack_up_di))

    def jack_load_adjust_and_jack(self):
        # 到达货物下方，第三步判断是否有上下视pgv二次调整
        if ConfigParams.is_secondary_adjust:
            self.action_list.append(GetPGVData())
            self.action_list.append(PGVSecondaryAdjust())

        # 第四步在取货前旋转托盘角度，根据输入的参数决定如何调整
        if self.robot_spin_angle_before_jack is not None:
            self.robot_spin_angle_before_jack = math.pi * self.robot_spin_angle_before_jack / 180
            self.action_list.append(
                Spin(self.robot_spin_angle_before_jack, "robot", self.spin_dir))
        if self.increase_spin_angle_before_jack is not None:
            self.increase_spin_angle_before_jack = math.pi * self.increase_spin_angle_before_jack / 180
            self.action_list.append(
                Spin(self.increase_spin_angle_before_jack, "increase", 0))
        if self.global_spin_angle_before_jack is not None:
            self.global_spin_angle_before_jack = math.pi * self.global_spin_angle_before_jack / 180
            self.action_list.append(
                Spin(self.global_spin_angle_before_jack, "world", self.spin_dir))

        # 抬升托盘取货
        self.action_list.append(JackHeight(ConfigParams.jack_motor_name, ConfigParams.jack_height,
                                           ConfigParams.jack_motor_speed, ConfigParams.jack_up_di))
        log.info(f"self.action_list: {self.action_list}")

    def jack_unload(self):
        if not self.operation_init:
            self.operation_init = True

            # 第一步判断是否有识别
            if ConfigParams.is_recognize:  # 要求启用识别时必须有recfile
                self.recfile_data = self.get_recfile_result()  # 获取识别文件数据放入字典中
                self.action_list.append(RecShelf(self.recfile))  # 识别货架，得到坐标放入self.rec_result
            else:
                # 在动作类内部选择直线、贝塞尔+直线、二段直线方式前往识别点
                # 第二步选择是否需要根据货物下方的二维码调整放货位置
                if ConfigParams.is_goods_qrcode:
                    self.action_list.append(GetApPosAdjustedViaPgv())  # 前往识别点,并根据货物二维码调整放货坐标
                else:
                    if not self.ap_id:
                        self.ap_id = Navigation.moveTask().get("target_name", None)
                        self.ap_id = "AP" + str(self.ap_id)
                    self.ap_world_pos = Navigation.getLM(self.ap_id, True)  # AP在世界坐标系下的位置
                    log.info(f'AP_pos: {self.ap_world_pos}')
                    if ConfigParams.how_go_site == "straight":
                        self.action_list.append(GoPath(self.ap_world_pos, Coordinate.WORLD))
                    elif ConfigParams.how_go_site == "bezier":
                        self.action_list.append(GoBezier(self.ap_world_pos))
                    elif ConfigParams.how_go_site == "polyline":
                        self.action_list.append(GoPolyline(self.ap_world_pos))
                # 加入后续动作
                self.jack_unload_adjust_and_jack()

        if 0 <= self.action_id < len(self.action_list):
            current_action = self.action_list[self.action_id]
            if current_action.action_name == "RecShelf" and current_action.action_status == ActionStatus.FINISHED:
                result = self.rec_result
                self.action_list.append(GoBezier(result))
                # 加入后续动作
                self.jack_unload_adjust_and_jack()

    def jack_unload_adjust_and_jack(self):
        # 到达放货点，第三步判断是否有下视pgv二次调整
        if ConfigParams.is_secondary_adjust:
            self.action_list.append(GetPGVData())
            self.action_list.append(PGVSecondaryAdjust())

        # 第四步在放货前旋转托盘角度，根据输入的参数决定如何调整
        if self.robot_spin_angle_before_jack is not None:
            self.robot_spin_angle_before_jack = math.pi * self.robot_spin_angle_before_jack / 180
            self.action_list.append(
                Spin(self.robot_spin_angle_before_jack, "robot", self.spin_dir))
        if self.increase_spin_angle_before_jack is not None:
            self.increase_spin_angle_before_jack = math.pi * self.increase_spin_angle_before_jack / 180
            self.action_list.append(
                Spin(self.increase_spin_angle_before_jack, "increase", 0))
        if self.global_spin_angle_before_jack is not None:
            self.global_spin_angle_before_jack = math.pi * self.global_spin_angle_before_jack / 180
            self.action_list.append(
                Spin(self.global_spin_angle_before_jack, "world", self.spin_dir))

        # 放货
        self.action_list.append(JackMinHeight(ConfigParams.jack_motor_name, ConfigParams.jack_lift_zero,
                                              ConfigParams.jack_motor_speed, ConfigParams.jack_zero_di))


    def go_ap_site(self):
        if not self.operation_init:
            self.operation_init = True
            if not self.ap_id:
                self.ap_id = Navigation.moveTask().get("target_name", None)
                self.ap_id = "AP" + str(self.ap_id)
            self.ap_world_pos = Navigation.getLM(self.ap_id, True)  # AP在世界坐标系下的位置
            log.info(f'AP_pos: {self.ap_world_pos}')
            if ConfigParams.how_go_site == "straight":
                self.action_list.append(GoPath(self.ap_world_pos,Coordinate.WORLD))
            elif ConfigParams.how_go_site == "bezier":
                self.action_list.append(GoBezier(self.ap_world_pos))
            elif ConfigParams.how_go_site == "polyline":
                self.action_list.append(GoPolyline(self.ap_world_pos))

    def go_bezier(self):
        if not self.operation_init:
            self.operation_init = True
            if not self.ap_id:
                self.ap_id = Navigation.moveTask().get("target_name", None)
                self.ap_id = "AP" + str(self.ap_id)
            self.ap_world_pos = Navigation.getLM(self.ap_id, True)  # AP在世界坐标系下的位置
            log.info(f'AP_pos: {self.ap_world_pos}')
            self.action_list.append(GoBezier(self.ap_world_pos, 0, 2, 0,
                                             False, 0.5, 1, 1, 1, 1.5))

    def go_polyline(self):
        if not self.operation_init:
            self.operation_init = True
            if not self.ap_id:
                self.ap_id = Navigation.moveTask().get("target_name", None)
                self.ap_id = "AP" + str(self.ap_id)
            self.ap_world_pos = Navigation.getLM(self.ap_id, True)  # AP在机器人坐标系下的位置
            log.info(f'AP_pos: {self.ap_world_pos}')
            self.action_list.append(GoPolyline(self.ap_world_pos))

    def go_map_path(self):
        if not self.operation_init:
            self.operation_init = True

            self.action_list.append(GoMapPath())

    def jack_height(self):
        """抬升托盘到指定高度"""
        if not self.operation_init:
            self.operation_init = True

            self.action_list.append(JackHeight(ConfigParams.jack_motor_name, ConfigParams.jack_height,
                                               ConfigParams.jack_motor_speed, ConfigParams.jack_up_di))

    def jack_min_height(self):
        """放货至最低点"""
        if not self.operation_init:
            self.operation_init = True

            self.action_list.append(JackMinHeight(ConfigParams.jack_motor_name, ConfigParams.jack_lift_zero,
                                                  ConfigParams.jack_motor_speed, ConfigParams.jack_zero_di))

    def spin(self):
        """旋转托盘"""
        if not self.operation_init:
            self.operation_init = True

            self.action_list.append(Spin(self.spin_angle, self.coordinate, self.spin_dir))

    def spin_zero_deg(self):
        """旋转托盘到0度位置"""
        if not self.operation_init:
            self.operation_init = True

            self.action_list.append(SpinZero())

    def rotate_hold_spin(self):
        """旋转托盘时启动随动"""
        if not self.operation_init:
            self.operation_init = True

            self.action_list.append(RobotRotate(self.spin_angle, self.coordinate))

    def go_dist(self):
        """前进一段距离"""
        if not self.operation_init:
            self.operation_init = True

            self.action_list.append(GoStraightDist(ConfigParams.go_distance))  # 导航到终点

    def go_path(self):
        """前进一段距离"""
        if not self.operation_init:
            self.operation_init = True

            self.action_list.append(GoPath([-1, 0, 0], Coordinate.ROBOT, 0.2, True))

    def rec_shelf(self):
        """识别货架"""
        if not self.operation_init:
            self.operation_init = True
            self.recfile_data = self.get_recfile_result()
            self.action_list.append(RecShelf(self.recfile))  # 导航到终点


    def pgv_adjust(self):
        """二次调整"""
        if not self.operation_init:
            self.operation_init = True
            self.action_list.append(GetPGVData())
            self.action_list.append(PGVSecondaryAdjust())
            # self.action_list.append(PGVSecondaryAdjustTest())

    def get_recfile_result(self, object_key="shelf"):
        """
        读取 recfile，提取 object_key (例如 'shelf' / 'pallet') 下所有 section 的参数。
        返回:
            {
                section_key1: {param_key: value, ...},
                section_key2: { ... },
                ...
            }
        """
        # 读文件得到 JSON 字符串
        rec_str = Recognize.getRecFile(self.recfile)        # ← 你已有的接口
        if not rec_str:
            raise ValueError(f"识别文件 '{self.recfile}' 为空")

        # 解析 JSON
        try:
            data = json.loads(rec_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON 解析失败: {e}")

        stack = [data]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                if node.get("key") == object_key:
                    obj_node = node
                    break
                stack.extend(v for v in node.values() if isinstance(v, (dict, list)))
            elif isinstance(node, list):
                stack.extend(node)
        else:
            raise KeyError(f"对象 '{object_key}' 未找到")

        # ④ 把对象下所有 section → 参数收集
        result = {}
        for section in obj_node.get("children", []):
            s_key = section.get("key")
            params = {}
            for p in section.get("children", []):
                k = p.get("key")
                if k:
                    params[k] = p.get("value", p.get("defaultValue"))
            result[s_key] = params
        log.info(f"result: {result}")
        return result
    '''
    {
    'recognitionParameter': {'deviceName': 'Laser-000',xxx},
    'navigationParameter': {}
    }
    '''


    def _execute_actions(self):
        if self.action_id < len(self.action_list):
            current_action = self.action_list[self.action_id]
            if current_action.action_status == ActionStatus.FINISHED:
                self.action_id += 1
            elif current_action.action_status == ActionStatus.FAILED:
                Abnormal.setTask(53000, f"execute action {current_action} failed!", "", "", "execute_actions")
                self.script_status = ActionStatus.FAILED
                Module.set_status(ScriptStatus.FAILED)
            else:
                current_action.run(self)
        else:
            self.script_status = ActionStatus.FINISHED
            Module.set_status(ScriptStatus.FINISHED)
        log.info(f'{self.action_id=}, {self.action_list=}')
        log.info(f"self.action_list: {self.action_list}")

    def print_info(self):
        # 打印当前任务队列、当前任务、当前任务id、当前任务状态
        log.info(f"{Module.get_task_args()=}")
        log.info(f"{Module.get_task_id()=}")
        log.info(f"{Module.get_status()=}")

    def main(self):
        while True:
            # 脚本任务状态管理
            status = Module.get_status()
            if status is ScriptStatus.RUNNING:
                self.run()
            elif status in (ScriptStatus.FAILED, ScriptStatus.FINISHED, ScriptStatus.NONE):
                Module.set_status(ScriptStatus.NONE)
                return
            self.print_info()
            time.sleep(0.1)

    def suspend(self):
        Module.set_status(ScriptStatus.SUSPENDED)
        log.info("suspend")

    def resume(self):
        Module.set_status(ScriptStatus.RUNNING)
        log.info("resume")

    def cancel(self):
        Module.set_status(ScriptStatus.FINISHED)
        log.info("cancel")

# def main():
#     Module.init()
#     j = Jack()
#     Module.set_suspend_callback(j.suspend)
#     Module.set_resume_callback(j.resume)
#     Module.set_cancel_callback(j.cancel)
#     while True:
#         # 脚本任务状态管理
#         status = Module.get_status()
#         j.report_info["status"] = status
#         j.print_info()
#         if status is ScriptStatus.RUNNING:
#             j.run()
#         elif status in (ScriptStatus.FAILED, ScriptStatus.FINISHED):
#             return
#
#             time.sleep(0.1)


# --- 以下为各个基础动作类（内容保持不变） ---
class BaseAction:
    """定义动作的基类"""

    def __init__(self, action_name: str = None):
        self.action_name = action_name or self.__class__.__name__
        self.start_time = time.time()
        self.action_status = ActionStatus.INIT
        self.action_state = {}

    def run(self, m):
        self.action_state["action_runtime"] = time.time() - self.start_time
        pass

    def reset(self):
        pass

    def __str__(self):
        return json.dumps({
            "class_name": self.__class__.__name__
        })

class SpinZero(BaseAction):
    def __init__(self, direction=2):
        super().__init__("SpinZero")
        self.status = ActionStatus.INIT
        self.init = True
        self.dir = direction  # 0 counterclockwise; 1 clockwise; 2 shortest
        self.spin_pos = 0
        self.angle = 0

    def run(self, j: Jack):
        if self.init:
            self.init = False
            self.status = ActionStatus.RUNNING
            self.spin_pos = Motor.get_motor_pos(ConfigParams.spin_motor_name)

            d180 = math.pi - abs(self.spin_pos)
            d0 = abs(self.spin_pos)
            if d180 > d0:
                self.angle = 0
            else:
                self.angle = math.pi
            Navigation.setRobotSpinAngle(self.angle, self.dir)
        if Navigation.spinRun():
            self.status = ActionStatus.FINISHED

        self.action_state['spin_state'] = self.status
        self.action_state['spin_direction'] = self.dir

    def reset(self):
        self.status = ActionStatus.RUNNING


class Spin(BaseAction):  # 托盘旋转到机器人/世界坐标系下固定角度
    def __init__(self, angle, coordinate="world", direction=2):
        super().__init__("Spin")
        self.action_status = ActionStatus.INIT
        self.init = True
        self.angle = angle
        self.dir = direction  # 0 counterclockwise; 1 clockwise; 2 shortest
        self.coordinate_system = coordinate

    def run(self, j: Jack):
        if self.init:
            self.init = False
            self.action_status = ActionStatus.RUNNING
            if self.coordinate_system == "robot":
                Navigation.setRobotSpinAngle(self.angle, self.dir)
                log.info("setRobotSpinAngle")
            elif self.coordinate_system == "world":
                Navigation.setGlobalSpinAngle(self.angle, self.dir)
                log.info("setGlobalSpinAngle")
            elif self.coordinate_system == "increase":
                Navigation.setIncreaseSpinAngle(self.angle)
                log.info("setIncreaseSpinAngle")
        if Navigation.spinRun():
            self.action_status = ActionStatus.FINISHED
        log.info(f"弧度{self.angle=}")
        log.info(f"坐标系{self.coordinate_system=}")

        self.action_state['spin_state'] = self.action_status
        self.action_state['spin_angle'] = self.angle
        self.action_state['spin_direction'] = self.dir

    def reset(self):
        self.action_status = ActionStatus.RUNNING


class RobotRotate(BaseAction):
    """只转车不转托盘"""

    def __init__(self, angle, coordinate, spin=True, direction=2):
        super().__init__("RobotRotate")
        self.action_status = ActionStatus.INIT
        self.init = True

        self.angle = angle
        self.coordinate = coordinate
        self.spin = spin
        self.direction = direction  # 0 counterclockwise; 1 clockwise; 2 shortest
        self.speed = 0.7
        self.move_args = dict()
        self.robot_ang = []

    def run(self, j: Jack):
        if self.init:
            self.init = False
            self.action_status = ActionStatus.RUNNING
            Navigation.resetOdoMove()
            self.move_args['spin'] = self.spin  # 是否随动
            self.move_args['speed_w'] = self.speed
            if self.coordinate == Coordinate.ROBOT:
                self.move_args['loc_mode'] = 0  # 基于里程定位
                self.move_args['move_angle'] = self.angle
                if self.angle < 0:
                    self.move_args['move_angle'] = -self.angle
                    self.move_args['speed_w'] = -self.speed
            elif self.coordinate == Coordinate.WORLD:
                self.move_args["loc_mode"] = 1        # 激光定位

                # ① 当前朝向：Loc 返回的是度 → 立即转弧度 → 归一化
                cur_angle_rad = self.normalize(math.radians(Loc.get_angle()[0]))

                # ② 目标朝向：假设外部传进来是“度”——> 先转弧度，再归一化
                target_rad = self.normalize(math.radians(self.angle) if abs(self.angle) > math.pi else self.angle)

                # ③ 差值也要再归一化一次，确保 (-π, π]
                rotate_dist = self.normalize(target_rad - cur_angle_rad)      # 就近方向的符号差

                # 默认“就近”   —— 速度正负=方向，幅值必为正
                speed_w = self.speed if rotate_dist >= 0 else -self.speed
                move_ang = abs(rotate_dist)

                # 用户强制指定方向时覆写
                if self.direction == 0:                 # 逆时针
                    speed_w  =  self.speed
                    move_ang =  abs(rotate_dist) if rotate_dist >= 0 else 2 * math.pi - abs(rotate_dist)
                elif self.direction == 1:               # 顺时针
                    speed_w  = -self.speed
                    move_ang =  abs(rotate_dist) if rotate_dist <= 0 else 2 * math.pi - abs(rotate_dist)

                # ④ 最终写回 move_args（注意 move_angle 一律为正幅值）
                self.move_args.update({
                    "spin":      self.spin,
                    "speed_w":   speed_w,
                    "move_angle": move_ang
                })

        status = Navigation.runOdoMove(self.move_args)
        log.info(f"{status=}")
        if status == ActionStatus.FINISHED:
            self.action_status = ActionStatus.FINISHED

        j.report_info["RobotRotate"] = {
            "action_status": self.action_status,
            "is_spin_held": self.move_args['spin'],
            "angle": self.angle,
            "coordinate": self.coordinate,
            "direction": self.direction
        }
        Module.report_info(j.report_info)

    def reset(self):
        Navigation.resetOdoMove()
        log.info("reset RobotRotate")
        self.action_status = ActionStatus.RUNNING

    def normalize(self, rad: float) -> float:
        """把任意弧度角归一化到 (-π, π] 区间"""
        return (rad + math.pi) % (2 * math.pi) - math.pi


class JackHeight(BaseAction):
    """顶升动作，通过设置电机位置实现顶升"""

    def __init__(self, motor_name, target_height, jack_motor_speed, jack_up_di):
        super().__init__("JackHeight")
        self.motor_name = motor_name
        self.target_height = target_height
        self.jack_motor_speed = jack_motor_speed
        self.jack_up_di = jack_up_di
        self.init = False
        Motor.resetMotor(self.motor_name)

    def run(self, j: Jack):
        if not self.init:
            self.init = True
            self.action_status = ActionStatus.RUNNING
            Motor.setMotorPosition(self.motor_name, self.target_height, self.jack_motor_speed, self.jack_up_di)
            Navigation.setGoodsShape(0, 0, 0)
        motor_info = Odometer.get_motor_infos()
        log.info(f"{motor_info=}")
        log.info(f"{self.target_height=}")

        if Motor.isMotorReached(self.motor_name) or Di.get_di(ConfigParams.jack_up_di):
            self.action_status = ActionStatus.FINISHED
            Motor.resetMotor(self.motor_name)

        j.report_info["JackHeight"] = {
            "action_status": self.action_status,
            "motor_name": self.motor_name,
            "target_height": self.target_height,
            "jack_motor_speed": self.jack_motor_speed,
            "jack_up_di": self.jack_up_di
        }
        Module.report_info(j.report_info)


class JackMinHeight(BaseAction):
    """顶升动作，通过设置电机位置实现顶升"""

    def __init__(self, motor_name, jack_lift_zero, jack_motor_speed, jack_zero_di):
        super().__init__("JackMinHeight")
        self.motor_name = motor_name
        self.jack_lift_zero = jack_lift_zero
        self.jack_motor_speed = jack_motor_speed
        self.jack_zero_di = jack_zero_di
        self.init = False
        Motor.resetMotor(self.motor_name)

    def run(self, j: Jack):
        if not self.init:
            self.init = True
            self.action_status = ActionStatus.RUNNING
        Motor.setMotorPosition(self.motor_name, self.jack_lift_zero, self.jack_motor_speed, self.jack_zero_di)
        motor_info = Odometer.get_motor_infos()
        log.info(f"{motor_info=}")
        log.info(f"Lowering tray")

        if Motor.isMotorReached(self.motor_name) or Di.get_di(ConfigParams.jack_zero_di):
            self.action_status = ActionStatus.FINISHED
            Navigation.clearGoodsShape()
            Motor.resetMotor(self.motor_name)

        j.report_info["JackMinHeight"] = {
            "action_status": self.action_status,
            "motor_name": self.motor_name,
            "jack_motor_speed": self.jack_motor_speed,
            "jack_zero_di": self.jack_zero_di
        }
        Module.report_info(j.report_info)


class GoMapPath(BaseAction):
    """前进指定距离"""

    def __init__(self):
        super().__init__("GoMapPath")

        self.init = True
        self.action_status = ActionStatus.INIT
        self.task = Navigation.moveTask()

    def run(self, j: Jack):
        if self.init:
            self.init = False
            self.action_status = ActionStatus.RUNNING
            Navigation.resetGoMapPath()
        finished = Navigation.goMapPath(json.dumps(self.task))
        if finished:
            self.action_status = ActionStatus.FINISHED

        self.action_state['status'] = self.action_status

class GoStraightDist(BaseAction):
    """前进/后退指定距离"""

    def __init__(self, go_dist):
        super().__init__("GoStraightDist")

        self.init = True
        self.action_status = ActionStatus.INIT
        self.go_dist = go_dist

    def run(self, j: Jack):
        if self.init:
            if self.go_dist < 0.0:
                Navigation.setPathBackMode(False)
            else:
                Navigation.setPathBackMode(True)
            self.init = False
            self.action_status = ActionStatus.RUNNING
            Navigation.resetPath()
            Navigation.setPathOnRobot([0, self.go_dist], [0, 0], 0)
        Navigation.goPath()
        finished = Navigation.isPathReached()
        if finished:
            self.action_status = ActionStatus.FINISHED

        Module.report_info({"GoStraightDist": {"status":self.action_status}})
        Module.report_info({"GoStraightDist": {"go_dist":self.go_dist}})


class GoPath(BaseAction):
    """直线走到指定点"""

    def __init__(self, go_pos, coordinate='robot', max_speed=0.5, back_mode=False):
        super().__init__("GoPath")

        self.init = True
        self.action_status = ActionStatus.INIT
        self.go_pos = go_pos
        self.coordinate = coordinate
        self.max_speed = max_speed
        self.back_mode = back_mode
        self.go_path = goPath.GoPath()

    def run(self, j: Jack):

        if self.init:
            self.init = False
            self.action_status = ActionStatus.RUNNING

        args = {
            "x":self.go_pos[0],
            "y":self.go_pos[1],
            "theta":self.go_pos[2],
            "backMode": self.back_mode,
            "maxSpeed": self.max_speed,
            "maxRot": 0.3,
            "coordinate": self.coordinate
        }
        self.action_status = self.go_path.run(args)

        j.report_info["GoPath"] = {
            "action_status": self.action_status,
            "go_pos": self.go_pos,
            "coordinate": self.coordinate,
            "max_speed": self.max_speed,
            "back_mode": self.back_mode
        }
        Module.report_info(j.report_info)


class RecordBezierPath(BaseAction):
    """
        走二阶贝塞尔
    """

    def __init__(self, target_world, back_dist=0, adjust_dist_for_curvature_limit=2, min_ahead_dist=0.5,
                 is_backwards=False, curvature_limit=1.5):
        super().__init__("RecordBezierPath")
        del target_world[3:]
        self.target_world = target_world
        log.info(f"target_world={target_world}")
        self.back_dist = back_dist
        self.end_position_world = [0, 0, 0]
        self.end_position_robot = [0, 0, 0]
        self.end_angle_robot = None

        self.min_ahead_dist = min_ahead_dist
        self.adjust_dist_for_curvature_limit = adjust_dist_for_curvature_limit

        self.is_backwards = is_backwards
        self.curvature_limit = curvature_limit

        self.action_status = ActionStatus.INIT
        self.init = True
        self.target_robot = [0, 0, 0]
        self.control_point = None
        self.param = {}
        self.is_set_min_speed = False

        self.go_path = goPath.GoPath()
        # 第一段线到位标识
        self.is_first_path_reached = False
        self.xs = []
        self.ys = []
        self.xs_ret = []
        self.ys_ret = []
        self.theta_ret = None
        self.offset_dist = 0.0
        self.k_max = 0  # 定义曲率
        self.first_point = []
        self.first_point_return = []
        self.second_path = []
        self.second_path_return = []

    def run(self, j: Jack):
        if self.init:
            self.action_status = ActionStatus.RUNNING
            Navigation.resetPath()
            self.init = False

            # 获取机器人位置（world系）
            loc_data = Loc.get_data()
            robot_loc = [loc_data["x"], loc_data["y"], loc_data["angle"]]

            # 计算终点
            self.end_position_world = Pos2World([self.back_dist, 0, 0], self.target_world)
            self.target_world = Pos2World([-self.min_ahead_dist, 0, 0], self.target_world)

            # 贝塞尔曲线终点 → robot坐标系
            self.target_robot = Pos2Base(self.target_world, robot_loc)
            self.end_position_robot = Pos2Base(self.end_position_world, robot_loc)

            success = False
            max_offset = self.adjust_dist_for_curvature_limit
            offset_step = 0.1
            alpha = 0.35  # 固定控制点比例
            P0_xy = P1 = P2 = P3_xy = [0, 0, 0]

            while self.offset_dist <= max_offset:
                # 起点从(0, 0)往后移，作为新的P0
                if self.is_backwards:
                    P0 = [self.offset_dist, 0, math.pi]
                else:
                    P0 = [-self.offset_dist, 0, 0]
                # P0 = [self.offset_dist, 0, math.pi]
                P3 = self.target_robot

                # 生成贝塞尔曲线控制点与路径
                P0_xy, P1, P2, P3_xy = self.compute_bezier_controls_dir(P0, P3, alpha)
                self.xs, self.ys = self.bezier_points(P0_xy, P1, P2, P3_xy)
                log.info(f"xs={self.xs}, ys={self.ys}")

                # 添加末端直线路径
                self.xs.append(self.end_position_robot[0])
                self.ys.append(self.end_position_robot[1])

                # 判断曲率是否超限
                # self.k_max = self.max_curvature(self.xs, self.ys) #海伦公式
                self.k_max = self.bezier_curvature(P0_xy, P1, P2, P3_xy)  # 二阶导
                if self.k_max <= self.curvature_limit:
                    success = True
                    break

                self.offset_dist += offset_step

            if not success:
                log.info(f"curvature limit exceeded. max_curvature={self.k_max}")
                self.action_status = ActionStatus.FAILED
                return

            # 成功构造路径,需要将路径分为2段，第一段后退至贝塞尔起始点
            self.control_point = [P0_xy, P1, P2, P3_xy]

            # 此处记录xs【0】，ys【0】
            self.first_point = [self.xs[0], self.ys[0]]
            self.first_point_return = [-self.xs[0], -self.ys[0]]

            if self.is_backwards:
                for i in range(len(self.xs)):
                    self.xs[i] -= self.offset_dist
            else:
                for i in range(len(self.xs)):
                    self.xs[i] += self.offset_dist

            self.end_angle_robot = self.end_position_robot[2]
            if self.is_backwards:
                self.end_angle_robot = (self.end_angle_robot + math.pi) % (2 * math.pi)
                if self.end_angle_robot > math.pi:
                    self.end_angle_robot -= 2 * math.pi

            # 此处记录self.xs & self.ys & end_angle_robot
            self.second_path = [self.xs, self.ys, self.end_angle_robot]
            self.xs_ret, self.ys_ret, self.theta_ret = self.generate_return_path(self.xs, self.ys)
            self.second_path_return = [self.xs_ret, self.ys_ret, self.theta_ret]

        self.action_status = ActionStatus.FINISHED

        robot_loc = [Loc.get_position()[0], Loc.get_position()[1], Loc.get_angle()[0]]
        j.report_info["RecordBezierPath"] = {
            "action_status": self.action_status,
            "k_max": self.k_max,
            "xs0,ys0": [self.xs[0], self.ys[0]],
            "xEnd,yEnd": [self.xs[-1], self.ys[-1]],
            "target_robot": self.target_robot,
            "target_pos_world": [self.end_position_world[0], self.end_position_world[1]],
            "robot_loc": robot_loc
        }
        Module.report_info(j.report_info)

        j.first_point = self.first_point
        j.second_path = self.second_path
        j.first_point_return = self.first_point_return
        j.second_path_return = self.second_path_return
        log.info(f"first_point={self.first_point}, second_path={self.second_path}")

    def reset(self):
        self.action_status = ActionStatus.RUNNING

    def compute_bezier_controls_dir(self, p0, p3, alpha=0.3):
        """
        计算三次 Bezier 的 4 个控制点（含端点），支持端点方向。
        :param
        p0, p3 : [x, y, theta]   theta 为弧度，表示该点切线方向
        alpha  : 0~1，控制 P1/P2 到端点的相对距离 (d = alpha * |P3-P0|)
        :return
        [P0_xy, P1, P2, P3_xy]   仅保留 (x, y)
        """
        x0, y0, th0 = p0
        x3, y3, th3 = p3

        # 端点间直线距离
        dist = math.hypot(x3 - x0, y3 - y0)
        d = alpha * dist  # 控制点到端点的绝对距离

        # 控制点
        p1 = [x0 + d * math.cos(th0), y0 + d * math.sin(th0)]
        p2 = [x3 - d * math.cos(th3), y3 - d * math.sin(th3)]

        return [p0, p1, p2, p3]  # 去掉角度，只留坐标

    def bezier_points(self, p0, p1, p2, p3, steps=1000):
        """
        生成 Bezier 曲线采样点
        :param
        p0~p3 : [x, y]
        steps : 采样分段数，返回 steps+1 个点
        :return
        (xs, ys) : 两个长度相等的列表
        """
        xs, ys = [], []
        for i in range(steps + 1):
            t = i / steps
            one_t = 1 - t

            # 三次 Bezier 伯恩斯坦基函数
            b0 = one_t ** 3
            b1 = 3 * one_t ** 2 * t
            b2 = 3 * one_t * t ** 2
            b3 = t ** 3

            x = (b0 * p0[0] + b1 * p1[0] + b2 * p2[0] + b3 * p3[0])
            y = (b0 * p0[1] + b1 * p1[1] + b2 * p2[1] + b3 * p3[1])
            x = round(x, 7)
            y = round(y, 7)
            xs.append(x)
            ys.append(y)
        return xs, ys

    def bezier_curvature(self, p0, p1, p2, p3, steps=500):
        """
        基于导数计算三次贝塞尔曲线最大曲率
        p0~p3: 控制点[x, y]
        返回最大曲率
        """
        k_max = 0.0
        for i in range(steps + 1):
            t = i / steps
            one_t = 1 - t

            # 一阶导数
            dx_dt = 3 * one_t ** 2 * (p1[0] - p0[0]) + \
                    6 * one_t * t * (p2[0] - p1[0]) + \
                    3 * t ** 2 * (p3[0] - p2[0])
            dy_dt = 3 * one_t ** 2 * (p1[1] - p0[1]) + \
                    6 * one_t * t * (p2[1] - p1[1]) + \
                    3 * t ** 2 * (p3[1] - p2[1])

            # 二阶导数
            ddx_dt = 6 * one_t * (p2[0] - 2 * p1[0] + p0[0]) + \
                     6 * t * (p3[0] - 2 * p2[0] + p1[0])
            ddy_dt = 6 * one_t * (p2[1] - 2 * p1[1] + p0[1]) + \
                     6 * t * (p3[1] - 2 * p2[1] + p1[1])

            # 曲率公式
            numerator = abs(dx_dt * ddy_dt - dy_dt * ddx_dt)
            denominator = (dx_dt ** 2 + dy_dt ** 2) ** 1.5
            if denominator == 0:
                continue
            k = numerator / denominator
            k_max = max(k_max, k)
        return k_max

    def generate_return_path(self, xs, ys):
        """
        基于贝塞尔路径，返回原路倒退路径：机器人坐标系为终点局部坐标系，返回格式为 [xs, ys, theta]
        """
        if len(xs) < 2:
            return [], [], 0.0

        # 末段切线方向作为返回路径的正向角度
        dx = xs[-1] - xs[-2]
        dy = ys[-1] - ys[-2]
        theta_end = math.atan2(dy, dx)

        origin_x = xs[-1]
        origin_y = ys[-1]
        world_pts = list(zip(xs, ys))
        world_pts.reverse()

        cos_t = math.cos(theta_end)
        sin_t = math.sin(theta_end)

        xs_ret, ys_ret = [], []
        for wx, wy in world_pts:
            dx = wx - origin_x
            dy = wy - origin_y
            x_r = cos_t * dx + sin_t * dy
            y_r = -sin_t * dx + cos_t * dy
            xs_ret.append(x_r)
            ys_ret.append(y_r)

        return xs_ret, ys_ret, theta_end


class GoRecordedPath(BaseAction):
    """
        走记录过点坐标的路径
    """

    def __init__(self, first_point, second_path, is_backwards=False, max_speed=0.3, max_accele=1, max_decele=0.7,
                 decele_dist=1):
        super().__init__("GoBezier")
        self.end_position_world = [0, 0, 0]
        self.end_position_robot = [0, 0, 0]

        self.first_point = first_point
        self.second_path = second_path
        self.is_backwards = is_backwards
        self.max_speed = max_speed
        self.max_accele = max_accele
        self.max_decele = max_decele
        self.decele_dist = decele_dist

        self.action_status = ActionStatus.INIT
        self.init = True
        self.target_robot = [0, 0, 0]
        self.control_point = None
        self.param = {}
        self.is_set_min_speed = False

        self.go_path = goPath.GoPath()
        # 第一段线到位标识
        self.is_first_path_reached = False

    def run(self, j: Jack):
        if self.init:
            self.action_status = ActionStatus.RUNNING
            Navigation.resetPath()
            self.init = False
            # 规划第一段倒退路线参数
            Navigation.setPathReachAngle(0.05)  # 到位精度
            Navigation.setPathReachDist(0.01)
            Navigation.setPathBackMode(not self.is_backwards)  # 设置正走倒走
            Navigation.setPathMaxSpeed(self.max_speed)
            Navigation.setPathOnRobot([0, self.first_point[0]], [0, self.first_point[1]], 0)
            self.param["maxAcc"] = float(self.max_accele)
            self.param["maxDec"] = float(self.max_decele)
            Navigation.goPathParam(self.param)

        if not self.is_first_path_reached and self.action_status != ActionStatus.FAILED:  # 走第一段路线到曲率合适的贝塞尔起点
            self.is_first_path_reached = Navigation.isPathReached()
            log.info(f"is_first_path_reached:{self.is_first_path_reached}")
            if self.is_first_path_reached:
                Navigation.resetPath()

                Navigation.setPathReachAngle(0.05)
                Navigation.setPathReachDist(0.01)
                Navigation.setPathBackMode(self.is_backwards)
                Navigation.setPathMaxSpeed(self.max_speed)

                Navigation.setPathOnRobot(self.second_path[0], self.second_path[1], self.second_path[2])
                self.param["maxAcc"] = float(self.max_accele)
                self.param["maxDec"] = float(self.max_decele)
                Navigation.goPathParam(self.param)

        if self.is_first_path_reached and self.action_status != ActionStatus.FAILED:  # 走贝塞尔到终点
            # Navigation.goPathParam(self.param)
            is_reached = Navigation.isPathReached()
            log.info(f"is_reached:{is_reached}")
            if is_reached:
                self.action_status = ActionStatus.FINISHED
                # return
            else:
                self.action_status = ActionStatus.RUNNING

            robot_current_loc = list(Loc.get_position())
            dist_cur_loc_end_loc = math.hypot(
                self.end_position_world[0] - robot_current_loc[0],
                self.end_position_world[1] - robot_current_loc[1]
            )
            if dist_cur_loc_end_loc < self.decele_dist and not self.is_set_min_speed:
                self.is_set_min_speed = True
                Navigation.setPathMaxSpeed(0.15)
                # Abnormal.setTask(55900, "has slow the speed", "", "", "")

        robot_loc = [Loc.get_position()[0], Loc.get_position()[1], Loc.get_angle()[0]]
        j.report_info["GoRecordedPath"] = {
            "action_status": self.action_status,
            "is_first_path_reached": self.is_first_path_reached,
            "first_point": self.first_point,
            "second_path": [self.second_path[0][-1], self.second_path[1][-1], self.second_path[2]],
            "target_pos_world": [self.end_position_world[0], self.end_position_world[1]],
            "max_speed": self.max_speed,
            "max_accele": self.max_accele,
            "robot_loc": robot_loc
        }
        Module.report_info(j.report_info)


class GoRecordedPathReturn(BaseAction):
    """
        走记录过点坐标的路径
    """

    def __init__(self, first_point, second_path, is_backwards=True, max_speed=0.3, max_accele=1, max_decele=0.7,
                 decele_dist=1):
        super().__init__("GoBezier")
        self.end_position_world = [0, 0, 0]
        self.end_position_robot = [0, 0, 0]

        self.first_point = first_point
        self.second_path = second_path
        self.is_backwards = is_backwards
        self.max_speed = max_speed
        self.max_accele = max_accele
        self.max_decele = max_decele
        self.decele_dist = decele_dist

        self.action_status = ActionStatus.INIT
        self.init = True
        self.target_robot = [0, 0, 0]
        self.control_point = None
        self.param = {}
        self.is_set_min_speed = False

        self.go_path = goPath.GoPath()
        # 第一段线到位标识
        self.is_first_path_reached = False

    def run(self, j: Jack):
        if self.init:
            self.action_status = ActionStatus.RUNNING
            Navigation.resetPath()
            self.init = False
            # # 规划第一段倒退路线参数
            Navigation.setPathReachAngle(0.05)  # 到位精度
            Navigation.setPathReachDist(0.01)
            Navigation.setPathBackMode(self.is_backwards)  # 设置正走倒走
            Navigation.setPathMaxSpeed(self.max_speed)
            Navigation.setPathOnRobot(self.second_path[0], self.second_path[1], self.second_path[2])
            self.param["maxAcc"] = float(self.max_accele)
            self.param["maxDec"] = float(self.max_decele)
            Navigation.goPathParam(self.param)

        if not self.is_first_path_reached and self.action_status != ActionStatus.FAILED:  # 走第一段路线到曲率合适的贝塞尔起点
            self.is_first_path_reached = Navigation.isPathReached()
            log.info(f"is_first_path_reached:{self.is_first_path_reached}")
            if self.is_first_path_reached:
                Navigation.resetPath()

                Navigation.setPathReachAngle(0.05)
                Navigation.setPathReachDist(0.01)
                Navigation.setPathBackMode(not self.is_backwards)
                Navigation.setPathMaxSpeed(self.max_speed)
                Navigation.setPathOnRobot([0, self.first_point[0]], [0, self.first_point[1]], 0)
                self.param["maxAcc"] = float(self.max_accele)
                self.param["maxDec"] = float(self.max_decele)
                Navigation.goPathParam(self.param)

        if self.is_first_path_reached and self.action_status != ActionStatus.FAILED:  # 走贝塞尔到终点
            # Navigation.goPathParam(self.param)
            is_reached = Navigation.isPathReached()
            log.info(f"is_reached:{is_reached}")
            if is_reached:
                self.action_status = ActionStatus.FINISHED
                # return
            else:
                self.action_status = ActionStatus.RUNNING

            robot_current_loc = list(Loc.get_position())
            dist_cur_loc_end_loc = math.hypot(
                self.end_position_world[0] - robot_current_loc[0],
                self.end_position_world[1] - robot_current_loc[1]
            )
            if dist_cur_loc_end_loc < self.decele_dist and not self.is_set_min_speed:
                self.is_set_min_speed = True
                Navigation.setPathMaxSpeed(0.15)
                # Abnormal.setTask(55900, "has slow the speed", "", "", "")

        robot_loc = [Loc.get_position()[0], Loc.get_position()[1], Loc.get_angle()[0]]
        j.report_info["GoRecordedPath"] = {
            "action_status": self.action_status,
            "is_first_path_reached": self.is_first_path_reached,
            "target_pos_world": [self.end_position_world[0], self.end_position_world[1]],
            "max_speed": self.max_speed,
            "max_accele": self.max_accele,
            "robot_loc": robot_loc
        }
        Module.report_info(j.report_info)


class GoBezier(BaseAction):
    """
        走二阶贝塞尔
    """
    def __init__(self, target_world, back_dist=0, adjust_dist_for_curvature_limit=2, min_ahead_dist=0.5, is_backwards=False,
                 max_speed=0.3, max_accele=1, max_decele=0.7, decele_dist=1, curvature_limit=1.5):
        super().__init__("GoBezier")
        del target_world[3:]
        self.target_world = target_world
        log.info(f"target_world={target_world}")
        self.back_dist = back_dist
        self.end_position_world = [0,0,0]
        self.end_position_robot = [0,0,0]
        self.min_ahead_dist = min_ahead_dist
        self.adjust_dist_for_curvature_limit = adjust_dist_for_curvature_limit

        self.is_backwards = is_backwards
        self.max_speed = max_speed
        self.max_accele = max_accele
        self.max_decele = max_decele
        self.decele_dist = decele_dist
        self.curvature_limit = curvature_limit

        self.action_status = ActionStatus.INIT
        self.init = True
        self.target_robot = [0, 0, 0]
        self.control_point = None
        self.param = {}
        self.is_set_min_speed = False

        self.go_path = goPath.GoPath()
        # 第一段线到位标识
        self.is_first_path_reached = False
        self.xs = []
        self.ys = []
        self.offset_dist = 0.0
        self.k_max = 0 #定义曲率

    def run(self, j: Jack):
        if self.init:
            self.action_status = ActionStatus.RUNNING
            Navigation.resetPath()
            self.init = False

            # 获取机器人位置（world系）
            loc_data = Loc.get_data()
            robot_loc = [loc_data["x"], loc_data["y"], loc_data["angle"]]

            # 计算终点
            self.end_position_world = Pos2World([self.back_dist, 0, 0], self.target_world)
            self.target_world = Pos2World([-self.min_ahead_dist, 0, 0], self.target_world)

            # 贝塞尔曲线终点 → robot坐标系
            self.target_robot = Pos2Base(self.target_world, robot_loc)
            self.end_position_robot = Pos2Base(self.end_position_world, robot_loc)

            success = False
            max_offset = self.adjust_dist_for_curvature_limit
            offset_step = 0.1
            alpha = 0.35  # 固定控制点比例
            P0_xy = P1 = P2 = P3_xy = [0, 0, 0]

            while self.offset_dist <= max_offset:
                # 起点从(0, 0)往后移，作为新的P0
                if self.is_backwards:
                    P0 = [self.offset_dist, 0, math.pi]
                else:
                    P0 = [-self.offset_dist, 0, 0]
                # P0 = [self.offset_dist, 0, math.pi]
                P3 = self.target_robot

                # 生成贝塞尔曲线控制点与路径
                P0_xy, P1, P2, P3_xy = self.compute_bezier_controls_dir(P0, P3, alpha)
                self.xs, self.ys = self.bezier_points(P0_xy, P1, P2, P3_xy)
                log.info(f"xs={self.xs}, ys={self.ys}")

                # 添加末端直线路径
                self.xs.append(self.end_position_robot[0])
                self.ys.append(self.end_position_robot[1])

                # 判断曲率是否超限
                # self.k_max = self.max_curvature(self.xs, self.ys)
                self.k_max = self.bezier_curvature(P0_xy, P1, P2, P3_xy)
                if self.k_max <= self.curvature_limit:
                    success = True
                    break

                self.offset_dist += offset_step

            if not success:
                log.info(f"curvature limit exceeded. max_curvature={self.k_max}")
                self.action_status = ActionStatus.FAILED
                return

            # 成功构造路径,需要将路径分为2段，第一段后退至贝塞尔起始点
            self.control_point = [P0_xy, P1, P2, P3_xy]
            # 规划第一段倒退路线参数
            Navigation.setPathReachAngle(0.05) # 到位精度
            Navigation.setPathReachDist(0.01)
            Navigation.setPathBackMode(not self.is_backwards) #设置正走倒走
            Navigation.setPathMaxSpeed(self.max_speed)
            Navigation.setPathOnRobot([0,self.xs[0]], [0,self.ys[0]],0)
            self.param["maxAcc"] = float(self.max_accele)
            self.param["maxDec"] = float(self.max_decele)
            Navigation.goPathParam(self.param)

        if not self.is_first_path_reached and self.action_status != ActionStatus.FAILED: # 走第一段路线到曲率合适的贝塞尔起点
            # Navigation.goPathParam(self.param)
            self.is_first_path_reached = Navigation.isPathReached()
            log.info(f"is_first_path_reached:{self.is_first_path_reached}")
            if self.is_first_path_reached:
                Navigation.resetPath()
                if self.is_backwards:
                    for i in range(len(self.xs)):
                        self.xs[i] -= self.offset_dist
                else:
                    for i in range(len(self.xs)):
                        self.xs[i] += self.offset_dist

                Navigation.setPathReachAngle(0.05)
                Navigation.setPathReachDist(0.01)
                Navigation.setPathBackMode(self.is_backwards)
                Navigation.setPathMaxSpeed(self.max_speed)

                end_angle_robot = self.end_position_robot[2]
                if self.is_backwards:
                    end_angle_robot = (end_angle_robot + math.pi) % (2 * math.pi)
                    if end_angle_robot > math.pi:
                        end_angle_robot -= 2 * math.pi

                Navigation.setPathOnRobot(self.xs, self.ys, end_angle_robot)
                self.param["maxAcc"] = float(self.max_accele)
                self.param["maxDec"] = float(self.max_decele)
                Navigation.goPathParam(self.param)

        if self.is_first_path_reached and self.action_status != ActionStatus.FAILED: # 走贝塞尔到终点
            # Navigation.goPathParam(self.param)
            is_reached = Navigation.isPathReached()
            log.info(f"is_reached:{is_reached}")
            if is_reached:
                self.action_status = ActionStatus.FINISHED
                # return
            else:
                self.action_status = ActionStatus.RUNNING

            robot_current_loc = list(Loc.get_position())
            dist_cur_loc_end_loc = math.hypot(
                self.end_position_world[0] - robot_current_loc[0],
                self.end_position_world[1] - robot_current_loc[1]
            )
            if dist_cur_loc_end_loc < self.decele_dist and not self.is_set_min_speed:
                self.is_set_min_speed = True
                Navigation.setPathMaxSpeed(0.15)
                # Abnormal.setTask(55900, "has slow the speed", "", "", "")

        robot_loc = [Loc.get_position()[0], Loc.get_position()[1], Loc.get_angle()[0]]
        j.report_info["GoBezier"] = {
            "action_status": self.action_status,
            "k_max": self.k_max,
            "xs0,ys0": [self.xs[0], self.ys[0]],
            "xEnd,yEnd": [self.xs[-1], self.ys[-1]],
            "target_pos_world": [self.end_position_world[0], self.end_position_world[1]],
            "max_speed": self.max_speed,
            "max_accele": self.max_accele,
            "robot_loc": robot_loc
        }
        Module.report_info(j.report_info)

    def reset(self):
        self.action_status = ActionStatus.RUNNING

    def compute_bezier_controls_dir(self, p0, p3, alpha=0.3):
        """
        计算三次 Bezier 的 4 个控制点（含端点），支持端点方向。
        参数
        ----
        p0, p3 : [x, y, theta]   theta 为弧度，表示该点切线方向
        alpha  : 0~1，控制 P1/P2 到端点的相对距离 (d = alpha * |P3-P0|)

        返回
        ----
        [P0_xy, P1, P2, P3_xy]   仅保留 (x, y)
        """
        x0, y0, th0 = p0
        x3, y3, th3 = p3

        # 端点间直线距离
        dist = math.hypot(x3 - x0, y3 - y0)
        d = alpha * dist  # 控制点到端点的绝对距离

        # 控制点
        p1 = [x0 + d * math.cos(th0), y0 + d * math.sin(th0)]
        p2 = [x3 - d * math.cos(th3), y3 - d * math.sin(th3)]

        return [p0, p1, p2, p3]  # 去掉角度，只留坐标

    def bezier_points(self, p0, p1, p2, p3, steps=1000):
        """
        生成 Bezier 曲线采样点
        ----
        p0~p3 : [x, y]
        steps : 采样分段数，返回 steps+1 个点
        返回
        ----
        (xs, ys) : 两个长度相等的列表
        """
        xs, ys = [], []
        for i in range(steps + 1):
            t = i / steps
            one_t = 1 - t

            # 三次 Bezier 伯恩斯坦基函数
            b0 = one_t ** 3
            b1 = 3 * one_t ** 2 * t
            b2 = 3 * one_t * t ** 2
            b3 = t ** 3

            x = (b0 * p0[0] + b1 * p1[0] + b2 * p2[0] + b3 * p3[0])
            y = (b0 * p0[1] + b1 * p1[1] + b2 * p2[1] + b3 * p3[1])
            x = round(x,7)
            y = round(y,7)
            xs.append(x)
            ys.append(y)
        return xs, ys

    def bezier_curvature(self, p0, p1, p2, p3, steps=500):
        """
        基于导数计算三次贝塞尔曲线最大曲率
        p0~p3: 控制点[x, y]
        返回最大曲率
        """
        k_max = 0.0
        for i in range(steps + 1):
            t = i / steps
            one_t = 1 - t

            # 一阶导数
            dx_dt = 3 * one_t ** 2 * (p1[0] - p0[0]) + \
                    6 * one_t * t * (p2[0] - p1[0]) + \
                    3 * t ** 2 * (p3[0] - p2[0])
            dy_dt = 3 * one_t ** 2 * (p1[1] - p0[1]) + \
                    6 * one_t * t * (p2[1] - p1[1]) + \
                    3 * t ** 2 * (p3[1] - p2[1])

            # 二阶导数
            ddx_dt = 6 * one_t * (p2[0] - 2 * p1[0] + p0[0]) + \
                     6 * t * (p3[0] - 2 * p2[0] + p1[0])
            ddy_dt = 6 * one_t * (p2[1] - 2 * p1[1] + p0[1]) + \
                     6 * t * (p3[1] - 2 * p2[1] + p1[1])

            # 曲率公式
            numerator = abs(dx_dt * ddy_dt - dy_dt * ddx_dt)
            denominator = (dx_dt ** 2 + dy_dt ** 2) ** 1.5
            if denominator == 0:
                continue
            k = numerator / denominator
            k_max = max(k_max, k)
        return k_max


class GoPolyline(BaseAction):
    """
        走两段线取放货
    """
    def __init__(self, target_world=None, back_dist=0, ahead_dist=1.5, is_backwards=False, max_speed=1, max_accele=1, max_decele=1, decele_dist=2):
        super().__init__()
        del target_world[3:]
        self.target_world = target_world
        log.info(f"{target_world=}")

        self.back_dist = back_dist
        self.end_position_world = Pos2World([self.back_dist,0,0], target_world)
        self.ahead_dist = ahead_dist
        self.target_world = Pos2World([-self.ahead_dist,0,0], target_world)
        self.is_backwards = is_backwards
        self.max_speed = max_speed
        self.max_accele = max_accele
        self.max_decele = max_decele
        self.decele_dist = decele_dist

        self.action_status = ActionStatus.INIT
        self.init = True
        self.control_point = None
        loc_data = Loc.get_data()
        robot_loc = [loc_data["x"], loc_data["y"], loc_data["angle"]]
        self.target_robot = Pos2Base(self.target_world, robot_loc)
        self.end_position_robot = Pos2Base(self.end_position_world, robot_loc)
        self.param = {}
        self.is_set_min_speed = False
        self.go_path = goPath.GoPath()
        self.is_go_path1 = True
        self.is_go_path2 = False
        self.init_go_path = True #第二次初始化gopath

    def run(self, j: Jack):
        if self.init:
            Navigation.resetPath()
            self.init = False

            xs = [self.target_world[0],self.end_position_world[0]]
            ys = [self.target_world[1],self.end_position_world[1]]

        args1 = {
            "x": self.target_world[0],
            "y": self.target_world[1],
            "theta": self.target_world[2],
            "backMode": self.is_backwards,
            "maxSpeed": self.max_speed,
            "maxRot": 0.3,
            "maxAcc":self.max_accele,
            "maxDec":self.max_decele,
            "coordinate": Coordinate.WORLD
        }

        args2 = {
            "x": self.end_position_world[0],
            "y": self.end_position_world[1],
            "theta": self.end_position_world[2],
            "backMode": self.is_backwards,
            "maxSpeed": self.max_speed,
            "maxRot": 0.3,
            "maxAcc": self.max_accele,
            "maxDec": self.max_decele,
            "coordinate": Coordinate.WORLD
        }
        if self.is_go_path1:
            self.action_status = self.go_path.run(args1)
            if self.action_status == ActionStatus.FINISHED:
                self.is_go_path1 = False
                self.is_go_path2 = True
                self.action_status = ActionStatus.RUNNING
        if self.is_go_path2:
            if self.init_go_path:
                self.init_go_path = False
                self.go_path = goPath.GoPath()
            self.action_status = self.go_path.run(args2)

    def reset(self):
        self.action_status = ActionStatus.RUNNING


class GoPolylineNoStop(BaseAction):
    """
        走 2 段折线（起点→target_world→end_position_world）
    """
    def __init__(self, target_world=None, back_dist=0, min_ahead_dist=1.5, is_backwards=False, max_speed=0.3, max_accele=1, max_decele=1.5, decele_dist=2):
        super().__init__()
        if target_world is not None:
            del target_world[3:]              # 只保留 x,y,yaw
        self.target_world = target_world  # 一会儿可能被识别结果覆盖
        self.back_dist = back_dist
        self.min_ahead_dist = min_ahead_dist

        self.end_position_world = [0, 0, 0]   # 末端（世界坐标）
        self.end_position_robot = [0, 0, 0]   # 末端（机器人坐标）

        self.is_backwards = is_backwards
        self.max_speed = max_speed
        self.max_accele = max_accele
        self.max_decele = max_decele
        self.decele_dist = decele_dist

        self.action_status = ActionStatus.INIT
        self.init = True
        self.param = {}
        self.is_set_min_speed = False

    def run(self, j: Jack):
        # ---------- 第 1 次进来：准备路径 ----------
        if self.init:
            self.action_status = ActionStatus.RUNNING
            self.init = False
            Navigation.resetPath()

            # ● 1) 获取/修正目标位姿 ---------------------------------
            if self.target_world is None:
                rec = j.rec_result
                self.target_world = [rec[0], rec[1], rec[2]]

            self.end_position_world = Pos2World([self.back_dist, 0, 0],
                                                 self.target_world)
            self.target_world = Pos2World([-self.min_ahead_dist, 0, 0],
                                                 self.target_world)

            # ● 2) 坐标系变换：世界 → 机器人 ---------------------------
            loc = Loc.get_data()
            robot_loc = [loc["x"], loc["y"], loc["angle"]]

            target_robot = Pos2Base(self.target_world, robot_loc)
            self.end_position_robot = Pos2Base(self.end_position_world, robot_loc)

            # ● 3) 折线路径（3 个点：起点 + 中点 + 终点）---------------
            xs = [0, target_robot[0], self.end_position_robot[0]]
            ys = [0, target_robot[1], self.end_position_robot[1]]

            Navigation.setPathReachAngle(0.1)    # 到点角度阈值
            Navigation.setPathReachDist(0.1)     # 到点距离阈值
            Navigation.setPathBackMode(self.is_backwards)   # 正/倒
            Navigation.setPathMaxSpeed(self.max_speed)    # 最高速

            # 末端姿态用 end_position_robot 的 yaw
            Navigation.setPathOnRobot(xs, ys, self.end_position_robot[2])
            self.param = {"maxAcc": float(self.max_accele),
                          "maxDec": float(self.max_decele)}

        # ---------- 后续循环：执行 & 监控 ----------
        if self.action_status != ActionStatus.FAILED:
            Navigation.goPathParam(self.param)

            if Navigation.isPathReached():
                self.action_status = ActionStatus.FINISHED
                return
            else:
                self.action_status = ActionStatus.RUNNING

            # 到终点前 decelerate
            curr = list(Loc.get_position())
            dist_to_end = math.hypot(
                self.end_position_world[0] - curr[0],
                self.end_position_world[1] - curr[1]
            )
            if dist_to_end < self.decele_dist and not self.is_set_min_speed:
                self.is_set_min_speed = True
                Navigation.setPathMaxSpeed(0.1)
                Abnormal.setTask(55900, "has slow the speed", "", "", "")

    # 外部强制重置时调用
    def reset(self):
        self.action_status = ActionStatus.RUNNING


class RecShelf(BaseAction):
    """识别货架"""

    def __init__(self, shelf_file, action_name="RecShelf"):
        super().__init__(action_name)
        self.action_status = ActionStatus.INIT
        self.recfile = shelf_file
        self.attempts = 0
        self.max_attempts = 3
        Recognize.resetRec()
        self.report_info = {}

    def run(self, j: Jack):
        self.action_status = ActionStatus.RUNNING
        log.info("recognizing the shelf")
        rec_status = Recognize.getRecStatus()
        log.info(f"{rec_status=}")
        # rec_result = Recognize.getRecFile(self.recfile)  # 读到识别文件原始数据
        # log.info(f"{rec_result=}")
        if rec_status == 2:
            rec_result = Recognize.getRecResults()
            log.info(f"{rec_result=}")
            Recognize.resetRec()
            log.info(f"rec_result={rec_result}")
            rec_x = rec_result['reco_list'][0]['x']
            rec_y = rec_result['reco_list'][0]['y']
            rec_yaw = rec_result['reco_list'][0]['yaw']
            rec_yaw = (rec_yaw + math.pi) % (2 * math.pi)
            if rec_yaw > math.pi:
                rec_yaw -= 2 * math.pi
            rec_x_y_yaw = [rec_x, rec_y, rec_yaw]
            log.info(f"{rec_x_y_yaw=}")
            j.rec_result = rec_x_y_yaw
            self.action_status = ActionStatus.FINISHED
        elif rec_status in (3, -1):
            if Timer.delay(0.05):
                self.attempts += 1
                if self.attempts > self.max_attempts:
                    self.action_status = ActionStatus.FAILED
                    Abnormal.setTask(53900,
                                     "Recognition failed, the maximum number of retries exceeded",
                                     "The recognition distance may be too close or too far, or the sensor used for recognition may be faulty",
                                     "Check whether the recognition distance is too close or too far and whether the sensor used for recognition is normal.",
                                     "Recognize the shelf")
                else:
                    Recognize.resetRec()
        else:
            Recognize.doRec(self.recfile)
            Timer.delay(0.05)
            log.info(f"doRec")

        j.report_info["RecShelf"] = {
            "action_status": self.action_status,
            "rec_result": j.rec_result,
            "recfile": self.recfile,
            "rec_status": rec_status,
            "rec_times": self.attempts
        }
        Module.report_info(j.report_info)


class GetApPosAdjustedViaPgv(BaseAction):
    # 路径导航  导航到站点
    def __init__(self, ap_id=None, dist=0, back_dist=0, ahead_dist=0.7):
        super().__init__("GetApPosAdjustedViaPgv")
        self.pgv_info = []
        self.init = True
        self.action_status = ActionStatus.INIT
        self.go_args = dict()
        self.dist = dist  # 终点前的补偿距离
        self.ap_id = ap_id
        self.target_world_pos = []
        self.back_dist = back_dist
        self.ahead_dist = ahead_dist

    def run(self, j: Jack):

        self.action_status = ActionStatus.RUNNING
        if self.init:
            self.init = False
            # 获取AP点坐标
            if not self.ap_id:
                self.ap_id = Navigation.moveTask().get("target_name", None)
                self.ap_id = "AP" + str(self.ap_id)
            self.target_world_pos = Navigation.getLM(self.ap_id, True)  # AP在世界坐标系下的位置

            # 获取qrcode的偏移数值，并补偿到终点坐标中
            self.pgv_info[0] = j.code_info["tag_diff_x"]  # 上视pgv读到的货架在车体坐标系偏移,用于补偿货架机械偏差
            self.pgv_info[1] = j.code_info["tag_diff_y"]
            self.pgv_info[2] = j.code_info["tag_diff_angle"]
            if abs(self.pgv_info[0]) > 0.02 and abs(self.pgv_info[1]) > 0.02:
                self.action_status = ActionStatus.FAILED
                Abnormal.setTask(55901,
                                 f"PGV diff_x or diff_y out of range:0.02",
                                 "The QR code of the goods is too biased",
                                 "Check whether there is any deviation of goods when picking up",
                                 "Adjust AP point position with goods QR code deviation")

            else:
                # 将车体终点位置，加入二维码的偏差补偿
                self.target_world_pos = Pos2World(self.pgv_info, [self.target_world_pos[0],self.target_world_pos[1],self.target_world_pos[2]])

        return self.target_world_pos

    def reset(self):
        self.action_status = ActionStatus.RUNNING


class GetPGVData(BaseAction):
    """获取二维码资料"""

    def __init__(self):
        super().__init__("GetPGVData")
        self.action_status = ActionStatus.INIT
        self.init = True
        self.is_DMT_detected = False
        self.tag_diff_x = 0
        self.tag_diff_y = 0
        self.tag_diff_angle = 0
        self.tag_value = 0
        self.count = 0
        self.max_rec_num = 15

    def run(self, j: Jack):
        if self.init:
            self.action_status = ActionStatus.RUNNING
            self.init = False

        pgv_data = Pgv.get_pgvs()
        for pgv in pgv_data:
            self.tag_value = pgv.tag_value
            self.tag_diff_x = pgv.tag_diff_x
            self.tag_diff_y = pgv.tag_diff_y
            self.tag_diff_angle = pgv.tag_diff_angle
            self.is_DMT_detected = pgv.is_DMT_detected

        # 将信息传出至j.code_info, 方便后续调用
        j.code_info = {
            "tag_value": self.tag_value,
            "is_DMT_detected": self.is_DMT_detected,
            "tag_diff_x": self.tag_diff_x,
            "tag_diff_y": self.tag_diff_y,
            "tag_diff_angle": self.tag_diff_angle
        }
        if self.is_DMT_detected and self.tag_value != "":  # 当识别二维码成功并且读到的码值不是空值
            log.info(f"read code success: {self.tag_value}")
            self.action_status = ActionStatus.FINISHED
        else:
            # pgv相机未扫描到二维码
            self.count = self.count + 1
            if self.count >= self.max_rec_num:
                Abnormal.setTask(55900,
                                 f"Rec times over max {self.count} NO shelf_code or recognized code fail or shelf_code is Null",
                                 "The pgv camera is faulty or the robot does not move above or below the QR code",
                                 "Check the position of the QRcode and the installation pos of PGV camera ",
                                 "Secondary adjustment with PGV")

        j.report_info["GetPGVData"] = {
            "action_status": self.action_status,
            "code_info": j.code_info
        }
        Module.report_info(j.report_info)


class PGVSecondaryAdjust(BaseAction):  # 二次调整
    def __init__(self):
        super().__init__("PGVSecondaryAdjust")
        self.action_status = ActionStatus.INIT
        self.init = True
        self.adjust_param = dict()

    def run(self, j: Jack):
        if self.init:
            self.init = False
            self.reset()
        self.set_adjust_param(j.code_info["tag_diff_x"], j.code_info["tag_diff_y"])
        self.action_status = Navigation.goPGVRun(self.adjust_param)

        j.report_info["PGVSecondaryAdjust"] = {
            "action_status": self.action_status,
            "code_info": j.code_info
        }
        Module.report_info(j.report_info)

    def set_adjust_param(self, pgv_adjust_cx, pgv_adjust_cy):
        self.adjust_param['use_pgv'] = False  # 使用上视pgv, args里需要增加use_pgv参数
        if self.adjust_param['use_pgv']:
            self.adjust_param['use_down_pgv'] = False  # 使用下视pgv
        else:
            self.adjust_param['use_down_pgv'] = True
        self.adjust_param['pgv_x_adjust'] = True  # 按照x纵方向进行二次调整
        self.adjust_param['pgv_x_angle_adjust'] = False  # 沿着车子方向的偏差进行调整，并且到点后调整角度偏差
        self.adjust_param['pgv_adjust_dist'] = 0.2  # 最大的调整半径,尽量小以二维码中心为圆心
        self.adjust_param['pgv_adjust_cx'] = pgv_adjust_cx  # 调整范围的圆心为二维码坐标系下的坐标x
        self.adjust_param['pgv_adjust_cy'] = pgv_adjust_cy  # 调整范围的圆心为二维码坐标系下的坐标y
        self.adjust_param['PGV_ReachDist'] = 0.02  # pgv二次调整距离精度
        self.adjust_param['PGV_ReachAngle'] = 0.02  # pgv二次调整角度精度

    def reset(self):
        log.info("reset PGV secondary adjustment")
        self.action_status = ActionStatus.RUNNING
        Navigation.resetGoPGV()

class PGVSecondaryAdjustTest(BaseAction):  # 二次调整,需要先调用GetPGVData()动作
    def __init__(self):
        super().__init__("PGVSecondaryAdjust")
        self.action_status = ActionStatus.INIT
        self.init = True
        self.adjust_param = dict()

    def run(self, j: Jack):
        if self.init:
            self.init = False
            self.reset()
        self.set_adjust_param(0.3, -0.3)
        self.action_status = Navigation.goPGVRun(self.adjust_param)

        j.report_info["PGVSecondaryAdjust"] = {
            "action_status": self.action_status,
        }
        Module.report_info(j.report_info)

    def set_adjust_param(self, pgv_adjust_cx, pgv_adjust_cy):
        self.adjust_param['use_pgv'] = False  # 使用上视pgv, args里需要增加use_pgv参数
        if self.adjust_param['use_pgv']:
            self.adjust_param['use_down_pgv'] = False  # 使用下视pgv
        else:
            self.adjust_param['use_down_pgv'] = True
        self.adjust_param['pgv_x_adjust'] = True  # 按照x纵方向进行二次调整
        self.adjust_param['pgv_x_angle_adjust'] = False  # 沿着车子方向的偏差进行调整，并且到点后调整角度偏差
        self.adjust_param['pgv_adjust_dist'] = 0.2  # 最大的调整半径,尽量小以二维码中心为圆心
        self.adjust_param['pgv_adjust_cx'] = pgv_adjust_cx  # 调整范围的圆心为二维码坐标系下的坐标x
        self.adjust_param['pgv_adjust_cy'] = pgv_adjust_cy  # 调整范围的圆心为二维码坐标系下的坐标y
        self.adjust_param['PGV_ReachDist'] = 0.02  # pgv二次调整距离精度
        self.adjust_param['PGV_ReachAngle'] = 0.02  # pgv二次调整角度精度

    def reset(self):
        log.info("reset PGV secondary adjustment")
        self.action_status = ActionStatus.RUNNING
        Navigation.resetGoPGV()


# --- 枚举定义 ---
class Coordinate:
    """ 坐标系枚举 """
    ROBOT = "robot"
    WORLD = "world"
    INCREASE = "increase"


class ActionStatus(IntEnum):
    """ 动作运行状态枚举，对标 ActionStatus """
    INIT = 0
    RUNNING = 1
    FINISHED = 3
    FAILED = 4
    SUSPENDED = 5


class RotateDirection(IntEnum):
    """ 旋转方向枚举 """
    NEARBY = 0
    COUNTERCLOCKWISE = 1
    CLOCKWISE = -1


if __name__ == '__main__':
    Module.init()
    j = Jack()
    j.main()
