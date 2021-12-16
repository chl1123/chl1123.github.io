# -*- coding: utf-8 -*-
# @Time : 2021/12/16  16: 56
# @Author : zhong
# @Version : 2.1.3
# @Update: add user error code

import json
import time
import syspy.goPath as goPath
from syspy.rbkSim import SimModule
from syspy.rbk import MoveStatus, BasicModule, ParamServer
from pickingRobot import ModeType, Hairou, BinOpType, BinType, BinModel, LocationType, Action, StopType, ErrorMessage

"""
####BEGIN DEFAULT ARGS####
{
    "operation": {
        "value": "reset",
        "default_value": ["preaction", "external_opt", "internal_opt", "robot_reset", "param_set", "switch_mode", "task_resume", "task_stop"],
        "tips": "动作指令",
        "type": "complex"
    },
    "mode": {
        "value": "task",
        "default_value": ["task", "module"],
        "tips": "交互模式",
        "type": "complex"
    },
    "robotId": {
        "value": "",
        "tips": "",
        "type": "string"
    },
    "opType": {
        "value": "inspect",
        "default_value": ["put", "take", "move", "inspect"],
        "tips": "操作类型",
        "type": "complex"
    },
    "binId": {
        "value": "reserve",
        "tips": "预留参数",
        "type": "string"
    },
    "binType": {
        "value": "dm_market",
        "default_value": ["dm_market", "markerless", "barcode"],
        "tips": "货物识别类型",
        "type": "complex"
    },
    "binModel": {
        "value": "carton",
        "default_value": ["carton", "plasticbox"],
        "tips": "料箱种类",
        "type": "complex"
    },
    "srcTray": {
        "value": {
            "id": 0,
            "type": 0 
        },
        "tips": "源托盘, 托盘id, 托盘类型",
        "type": "json"
    },
    "dstTray": {
        "value": {
            "id": 3,
            "type": 1 
        },
        "tips": "目标托盘, 托盘id, 托盘类型",
        "type": "json"
    },
    "targetTray": {
        "value": {
            "id": 0,
            "type": 0 
        },
        "tips": "扫描对象托盘, 托盘id, 托盘类型",
        "type": "json"
    },
    "targetPosition": {
        "value": {
            "x": 0,
            "y": 0,
            "theta": 0
        },
        "tips": "位置定义",
        "type": "json"
    },
    "targetHeight": {
        "value": 0,
        "tips": "库位高度",
        "unit": "",
        "type": "double"
    },
    "locationType": {
        "value": "storage_shelf",
        "default_value": ["storage_shelf", "storage_shelf_deep", "conveyor"],
        "tips": "库位类型",
        "type": "complex"
    },
    "preconditions": {
        "value": {
            "liftPositionMax": 0.0,
            "liftPositionMin": 0.0,
            "forkRotationPositionMax": 0.0,
            "forkRotationPositionMin": 0.0,
            "fingerPosition": 0
        },
        "tips": "预备动作前置目标",
        "type": "json"
    },
    "box_width": {
        "value": 0,
        "tips": "货箱宽度配置值",
        "unit": "m",
        "type": "double"
    },
    "box_height": {
        "value": 0,
        "tips": "货箱高度配置值",
        "unit": "m",
        "type": "double"
    },
    "box_depth": {
        "value": 0,
        "tips": "货箱深度配置值",
        "unit": "m",
        "type": "double"
    },
    "box_tag_height": {
        "value": 0,
        "tips": "货箱底部与货箱码下边沿的高度差",
        "unit": "m",
        "type": "double"
    },
    "box_tag_depth": {
        "value": 0,
        "tips": "货箱码到货箱表面的贴码深度",
        "unit": "m",
        "type": "double"
    },
    "shelf_tag_height": {
        "value": 0,
        "tips": "货架放货平面与货架码上边沿的高度差",
        "unit": "m",
        "type": "double"
    },
    "conveyor_tag_height": {
        "value": 0,
        "tips": "输送线放货平面(滚轮面)与货架码上边沿的高度差",
        "unit": "m",
        "type": "double"
    },
    "gap_between_box": {
        "value": 0,
        "tips": "货架上箱子之间的距离",
        "unit": "m",
        "type": "double"
    }
}
####END DEFAULT ARGS##### 
"""


class Module(BasicModule):
    def __init__(self, r, args):
        super(Module, self).__init__()
        self.status = MoveStatus.NONE
        p = ParamServer(__file__)
        ip = p.loadParam("ip", type="str", default="192.168.192.20", comment="ip addr")
        port = p.loadParam("port", type="int", default=4172, maxValue=999999, minValue=0, comment="port")
        self.start_connect_time = time.time()
        self.max_connect_time = p.loadParam("max_connect_time", type="int", default=10, maxValue=999999, minValue=0,
                                            comment="链接等待最长时间s")
        self.mode = p.loadParam("mode", type="str", default="task", comment="交互模式")
        self.robotId = p.loadParam("robotId", type="str", default="1", comment="机器人ID")
        self.opType = p.loadParam("opType", type="str", default="inspect", comment="操作类型")
        self.binId = p.loadParam("binId", type="str", default="reserve", comment="预留参数")
        self.binType = p.loadParam("binType", type="str", default="markerless", comment="货物识别类型")
        self.binModel = p.loadParam("binModel", type="str", default="plasticbox", comment="料箱种类")
        self.srcTray = p.loadParam("srcTray", type="str", default='{"id": 0, "type": 0}', comment="源托盘, 托盘id, 托盘类型")
        self.dstTray = p.loadParam("dstTray", type="str", default='{"id": 1, "type": 0}', comment="目标托盘, 托盘id, 托盘类型")
        self.targetTray = p.loadParam("targetTray", type="str", default='{"id": 0, "type": 0}',
                                      comment="扫描对象托盘, 托盘id, 托盘类型")
        self.targetPosition = p.loadParam("targetPosition", type="str",
                                          default='{"x": 71.1, "y": 26.3, "theta": 1.5708}', comment="位置定义")
        self.targetHeight = p.loadParam("targetHeight", type="float", default=0, comment="库位高度")
        self.locationType = p.loadParam("locationType", type="str", default="storage_shelf", comment="库位类型")
        self.preconditions = p.loadParam("preconditions", type="str",
                                         default='{"liftPositionMax": 0.0, "liftPositionMin": 0.0,'
                                                 ' "forkRotationPositionMax": 0.0, "forkRotationPositionMin": 0.0,'
                                                 ' "fingerPosition": 0}', comment="预备动作前置目标")
        self.box_width = p.loadParam("box_width", type="float", default=0, comment="货箱宽度配置值")
        self.box_height = p.loadParam("box_height", type="float", default=0, comment="货箱高度配置值")
        self.box_depth = p.loadParam("box_depth", type="float", default=0, comment="货箱深度配置值")
        self.box_tag_height = p.loadParam("box_tag_height", type="float", default=0, comment="货箱底部与货箱码下边沿的高度差")
        self.box_tag_depth = p.loadParam("box_tag_depth", type="float", default=0, comment="货箱码到货箱表面的贴码深度")
        self.shelf_tag_height = p.loadParam("shelf_tag_height", type="float", default=0, comment="货架放货平面与货架码上边沿的高度差")
        self.conveyor_tag_height = p.loadParam("conveyor_tag_height", type="float", default=0,
                                               comment="输送线放货平面(滚轮面)与货架码上边沿的高度差")
        self.gap_between_box = p.loadParam("gap_between_box", type="float", default=0, comment="货架上箱子之间的距离")
        self.di1 = p.loadParam("di1", type="int", default=2, comment="上限位DI")
        self.di2 = p.loadParam("di2", type="int", default=4, comment="下限位DI")
        self.di3 = p.loadParam("di3", type="int", default=1, comment="升降防坠机械限位DI")

        r.logInfo(f"===init=== {args}")

        self.init = True
        self.state = dict()
        self.msg_send = False
        self.src_ok = False
        self.src_send = False
        self.resume_send = False
        self.go_path = goPath.Module(r, dict())
        self.h = Hairou(ip, port)
        self.h.connect()

    def run(self, r: SimModule, args):
        # 驱动器连接故障，通信超时
        if r.errorExits(52111):
            return MoveStatus.FAILED

        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            r.logInfo(f"before update args:  {json.dumps(args)}")
            self.update_param(r, args)
            r.logInfo(f"after update args:  {json.dumps(args)}")
            self.clear_errors(r)  # 清除用户自定义错误

        if not self.h.isconnect:
            self.state["init"] = self.h.initDevice(r)
            self.state["warning"] = "ctu is connecting!!!!"
            str_state = json.dumps(self.state)
            r.setInfo(str_state)
            r.logDebug(str_state)
            d_time = time.time() - self.start_connect_time
            if d_time > self.max_connect_time:
                r.setError(f"ctu connect is overtime: {self.max_connect_time}")
                self.status = MoveStatus.FAILED
            return self.status

        if self.status is not MoveStatus.FINISHED:
            self.state = self.h.getReport(r)
            r.setInfo(json.dumps(self.state))

            if "connect_error" in self.state:
                d_time = time.time() - self.start_connect_time
                if d_time > self.max_connect_time:
                    r.setError(f"ctu connect is overtime: {self.max_connect_time}")
                    self.status = MoveStatus.FAILED
                    str_state = json.dumps(self.state)
                    r.setInfo(str_state)
                    r.logDebug(str_state)
                    return self.status
            else:
                self.start_connect_time = time.time()

            if self.trigger_di(r):
                # 请求stop指令
                self.h.task_stop(r, StopType.STOP_EMG)
                r.setNotice(json.dumps(self.h.task_stop_res))
                self.state["task_stop_res"] = self.h.task_stop_res
                return MoveStatus.FAILED

            # ======================================动作指令类型========================================================
            # ["switch_mode", "preaction", "robot_reset", "param_set", "internal_opt", "external_opt", "task_resume", "task_stop"]
            if "operation" in args:
                if args['operation'] == 'switch_mode':
                    try:
                        if not self.msg_send:
                            self.h.switch_mode(r, self.mode)
                            self.msg_send = True
                        r.setNotice(json.dumps(self.h.switch_mode_res))
                        self.state['result'] = self.h.switch_mode_res
                        if self.h.switch_mode_res['status'] == Action.FINISHED:
                            # self.msg_send = False
                            self.status = MoveStatus.FINISHED
                        # return self.status
                    except Exception as e:
                        r.setWarning(f"switch_mode exception: {e}")
                        self.h.task_resume(r, self.robotId)

                elif args['operation'] == 'preaction':
                    try:
                        if not self.msg_send:
                            self.h.preaction(r, self.robotId, self.preconditions)
                            self.msg_send = True
                        r.setNotice(json.dumps(self.h.preaction_res))
                        self.state['result'] = self.h.preaction_res
                        if self.h.preaction_res['status'] == Action.FINISHED:
                            self.status = MoveStatus.FINISHED
                    except Exception as e:
                        r.setWarning(f"preaction exception: {e}")
                        self.h.task_resume(r, self.robotId)

                elif args['operation'] == 'robot_reset':
                    r.logInfo(f"robot is resetting...")
                    try:
                        if not self.msg_send:
                            self.h.robot_reset(r)
                            self.msg_send = True
                        r.setNotice(json.dumps(self.h.reset_res))
                        self.state['result'] = self.h.reset_res
                        if self.h.reset_res['status'] == Action.FINISHED:
                            self.status = MoveStatus.FINISHED
                    except Exception as e:
                        r.setWarning(f"robot_reset exception: {e}")
                        self.h.task_resume(r, self.robotId)

                elif args['operation'] == 'param_set':
                    try:
                        if not self.msg_send:
                            self.h.param_set(r, self.robotId, self.box_width, self.box_height, self.box_depth,
                                             self.box_tag_height,
                                             self.box_tag_depth, self.shelf_tag_height, self.conveyor_tag_height,
                                             self.gap_between_box)
                            self.msg_send = True
                        r.setNotice(f"param_set_res: {json.dumps(self.h.param_set_res)}")
                        self.state['result'] = self.h.param_set_res
                        if self.h.param_set_res['status'] == Action.FINISHED:
                            self.status = MoveStatus.FINISHED
                    except Exception as e:
                        r.setWarning(f"param_set exception: {e}")
                        self.h.task_resume(r, self.robotId)

                elif args['operation'] == 'internal_opt':
                    try:
                        if self.state:  # 检查机构状态，并自动进行异常状态恢复
                            finger = self.state['finger'] if "finger" in self.state else None
                            rotate = self.state['rotate']
                            stretch = self.state['stretch']
                            lift = self.state['lift']
                            if (finger and finger['state'] in [4, 0]) or rotate['state'] in [4, 0] or stretch['state'] in [4, 0] or lift['state'] in [4, 0]:
                                if not self.resume_send:
                                    r.setWarning(f"internal_opt: machine abnormality, task is resuming")
                                    self.h.task_resume(r, self.robotId)
                                    self.resume_send = True
                            else:
                                self.resume_send = False

                        if not self.msg_send:
                            self.h.internal_bin_op(r, self.robotId, self.opType, self.binId, self.binType, self.binModel, self.srcTray, self.dstTray, self.targetTray)
                            self.msg_send = True
                        r.setNotice(json.dumps(self.h.internal_bin_op_res))
                        self.state['result'] = self.h.internal_bin_op_res
                        self.check_execution_result(r, self.h.internal_bin_op_res)
                        if self.h.internal_bin_op_res['status'] == Action.FINISHED:
                            self.status = MoveStatus.FINISHED
                    except Exception as e:
                        r.setError(f"internal_opt exception: {e}---{self.h.seqNum_req}")
                        return MoveStatus.FAILED

                elif args['operation'] == 'external_opt':
                    try:
                        if self.state:  # 检查机构状态，并自动进行异常状态恢复
                            finger = self.state['finger'] if "finger" in self.state else None
                            rotate = self.state['rotate']
                            stretch = self.state['stretch']
                            lift = self.state['lift']
                            if (finger and finger['state'] in [4, 0]) or rotate['state'] in [4, 0] or stretch['state'] in [4, 0] or lift['state'] in [4, 0]:
                                if not self.resume_send:
                                    r.setWarning(f"external_opt: machine abnormality--- task is resuming")
                                    self.h.task_resume(r, self.robotId)
                                    self.resume_send = True
                            else:
                                self.resume_send = False

                        if not self.msg_send:
                            self.h.external_bin_op(r, self.robotId, self.opType, self.binId, self.targetPosition,
                                                   self.targetHeight, self.binType, self.binModel, self.locationType)
                            self.msg_send = True
                        r.setNotice(json.dumps(self.h.external_bin_op_res))
                        self.state['result'] = self.h.external_bin_op_res
                        self.check_execution_result(r, self.h.external_bin_op_res)
                        # 监听位置请求 msgType(200), 机器视觉自动校准取放货物位置
                        if self.h.req_position and not self.src_ok:
                            # r.setWarning(f"req_position: {self.h.req_position}")
                            self.src_ok = self.src_pos(r, self.h.req_position)
                            if self.src_ok:
                                self.h.req_position = dict()
                                self.src_ok = False

                        if self.h.external_bin_op_res['status'] == Action.FINISHED:
                            self.status = MoveStatus.FINISHED
                    except Exception as e:
                        r.setError(f"external_opt exception: {e}")
                        return MoveStatus.FAILED

                elif args['operation'] == 'task_resume':
                    r.setWarning(f"task_resume: task is resuming...")
                    try:
                        if not self.msg_send:
                            self.h.task_resume(r, self.robotId)
                            self.msg_send = True
                        r.setNotice(json.dumps(self.h.resume_res))
                        self.state['result'] = self.h.resume_res
                        if self.h.resume_res['status'] == Action.FINISHED:
                            self.status = MoveStatus.FINISHED
                    except Exception as e:
                        r.setWarning(f"task_resume exception: {e}")

                elif args['operation'] == 'task_stop':
                    r.setWarning(f"task stop")
                    try:
                        if not self.msg_send:
                            self.h.task_stop(r, StopType.STOP_EMG)
                            self.msg_send = True
                        r.setNotice(json.dumps(self.h.task_stop_res))
                        self.state['result'] = self.h.task_stop_res
                        if self.h.task_stop_res['status'] == Action.FINISHED:
                            self.status = MoveStatus.FINISHED
                    except Exception as e:
                        r.setWarning(f"task_stop exception: {e}")
            else:
                r.setError("operation must be checked!")
                return MoveStatus.FAILED
            r.setInfo(json.dumps(self.state))
            return self.status

    def suspend(self, r: SimModule):
        self.status = MoveStatus.SUSPENDED
        self.state = self.h.getReport(r)
        self.start_connect_time = time.time()
        r.setInfo(json.dumps(self.state))

    def cancel(self, r: SimModule):
        r.logInfo(f"Task cancel")
        self.h.task_stop(r, StopType.STOP_EMG)
        self.h.disconnect()
        self.status = MoveStatus.NONE

    def update_param(self, r, args):

        # ==============================================================================================================
        # params = ['mode', 'robotId', 'opType', 'binId', 'binType', 'binModel', 'srcTray', 'dstTray', 'targetTray',
        #           'targetPosition', 'targetHeight', 'locationType', 'preconditions', 'box_width', 'box_height', 'box_depth',
        #           'box_tag_height', 'box_tag_depth', 'shelf_tag_height', 'conveyor_tag_height', 'gap_between_box']
        # ========================================= 更新参数 ============================================================
        if 'mode' in args:
            self.mode = args['mode']
        if 'robotId' in args:
            self.robotId = args['robotId']
        if 'opType' in args:
            self.opType = args['opType']
        if 'binId' in args:
            self.binId = args['binId']
        if 'binType' in args:
            self.binType = args['binType']
        else:
            self.binType = None
        if 'binModel' in args:
            self.binModel = args['binModel']
        else:
            self.binModel = None
        if 'srcTray' in args:
            args['srcTray']['id'] = int(args['srcTray']['id'])
            args['srcTray']['type'] = int(args['srcTray']['type'])
            self.srcTray = args['srcTray']
        else:
            self.srcTray = json.loads(self.srcTray)

        if 'dstTray' in args:
            args['dstTray']['id'] = int(args['dstTray']['id'])
            args['dstTray']['type'] = int(args['dstTray']['type'])
            self.dstTray = args['dstTray']
        else:
            self.dstTray = json.loads(self.dstTray)
        if 'targetTray' in args:
            # self.targetTray['id'] = int(self.srcTray['id'])
            # self.targetTray['type'] = int(self.srcTray['type'])
            self.targetTray = args['targetTray']
        else:
            self.targetTray = json.loads(self.targetTray)

        if 'targetPosition' in args:
            self.targetPosition = args['targetPosition']
        else:
            self.targetPosition = json.loads(self.targetPosition)
        if 'targetHeight' in args:
            self.targetHeight = args['targetHeight']
        if 'locationType' in args:
            self.locationType = args['locationType']
        else:
            self.locationType = None
        if 'preconditions' in args:
            self.preconditions = args['preconditions']
        else:
            self.preconditions = json.loads(self.preconditions)
        if 'box_width' in args:
            self.box_width = args['box_width']
        if 'box_height' in args:
            self.box_height = args['box_height']
        if 'box_depth' in args:
            self.box_depth = args['box_depth']
        if 'box_tag_height' in args:
            self.box_tag_height = args['box_tag_height']
        if 'box_tag_depth' in args:
            self.box_tag_depth = args['box_tag_depth']
        if 'shelf_tag_height' in args:
            self.shelf_tag_height = args['shelf_tag_height']
        if 'conveyor_tag_height' in args:
            self.conveyor_tag_height = args['conveyor_tag_height']
        if 'gap_between_box' in args:
            self.gap_between_box = args['gap_between_box']

        # =================更新参数数据格式======================
        if self.mode == 'task':
            self.mode = ModeType.TASK
        elif self.mode == 'module':
            self.mode = ModeType.MODULE

        if self.opType == 'put':
            self.opType = BinOpType.PUT
        elif self.opType == 'take':
            self.opType = BinOpType.TAKE
        elif self.opType == 'move':
            self.opType = BinOpType.MOVE
        elif self.opType == 'inspect':
            self.opType = BinOpType.INSPECT

        if self.binType == 'dm_market':
            self.binType = BinType.DM_MARKED
        elif self.binType == 'markerless':
            self.binType = BinType.MARKERLESS
        elif self.binType == 'barcode':
            self.binType = BinType.BARCODE

        if self.binModel == 'carton':
            self.binModel = BinModel.CARTON
        elif self.binModel == 'plasticbox':
            self.binModel = BinModel.PLASTICBOX

        if self.locationType == 'storage_shelf':
            self.locationType = LocationType.STORAGE_SHELF
        elif self.locationType == 'storage_shelf_deep':
            self.locationType = LocationType.STORAGE_SHELF_DEEP
        elif self.locationType == 'conveyor':
            self.locationType = LocationType.CONVEYOR
        r.logInfo("update args: {args}")

    def src_pos(self, r, req_position):
        req_posi = req_position['position']
        req_posi['coordinate'] = 'robot'
        src_status = self.go_path.status
        if req_posi['x'] < 0:
            req_posi['backMode'] = 1
        if abs(req_posi['x']) < 0.003:
            src_status = MoveStatus.FINISHED
        if src_status != MoveStatus.FINISHED and src_status != MoveStatus.FAILED:
            self.go_path.run(r, req_posi)

        if src_status == MoveStatus.FINISHED:
            self.go_path = goPath.Module(r, dict())
            req_posi['status'] = "finish"
            self.h.src_pos_resp(r, req_posi)
            return True
        return False

    def trigger_di(self, r):  # 触发上、下限位DI，机械限位DI
        dis = r.Di()
        nodes = dis.get('node', list())
        for node in nodes:
            if node['id'] == self.di1 and node['status']:
                r.setError(f"触发上限位DI")
                return True
            if node['id'] == self.di2 and node['status']:
                r.setError(f"触发下限位DI")
                return True
            if node['id'] == self.di3 and node['status']:
                r.setError(f"触发机械限位DI")
                return True
        return False

    @staticmethod
    def clear_errors(r):
        """
        清除用户自定义错误
        :param r: 
        :return: 
        """""
        for i in range(53900, 53905):
            if r.errorExits(i):
                r.clearError(i)

    def check_execution_result(self, r, result):
        """
        检测指令执行结果是否有报错
        :param r:
        :param result:
        """
        if "res" in result:
            try:
                execution_result = result['res']['executionResult']
                if execution_result != 0:
                    error_msg = ErrorMessage.ERROR_CODE[execution_result]
                    if execution_result == 0x80000400:
                        r.setUserError(53900, error_msg)
                    elif execution_result == 0x80000401:
                        r.setUserError(53901, error_msg)
                    elif execution_result == 0x80000400:
                        r.setUserError(53902, error_msg)
                    elif execution_result == 0x80000400:
                        r.setUserError(53903, error_msg)
                    else:
                        r.setError(f"execute failed: {error_msg}")
                    self.status = MoveStatus.FAILED
            except KeyError as e:
                r.logDebug(f"KeyError: {e}")
            except Exception as e:
                r.logDebug(f"error in hairou state: {e}")
                r.setError(f"check_execution_result error: {e}")

