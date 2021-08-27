# -*- coding: utf-8 -*-
import json
import time

from syspy.rbkSim import SimModule
from module.syspy.rbk import MoveStatus, BasicModule, ParamServer
from pickingRobot_v18 import ModeType, Hairou, BinOpType, BinType, BinModel, LocationType

"""
####BEGIN DEFAULT ARGS####
{
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
        "value": "take",
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
            "id": 0,
            "type": 0 
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
        self.robotId = p.loadParam("robotId", type="str", default="12345", comment="")
        self.opType = p.loadParam("opType", type="str", default="put", comment="操作类型")
        self.binId = p.loadParam("binId", type="str", default="reserve", comment="预留参数")
        self.binType = p.loadParam("binType", type="str", default="markerless", comment="货物识别类型")
        self.binModel = p.loadParam("binModel", type="str", default="carton", comment="料箱种类")

        self.srcTray = p.loadParam("srcTray", type="str", default='{"id": 0, "type": 0}', comment="源托盘, 托盘id, 托盘类型")
        self.dstTray = p.loadParam("dstTray", type="str", default='{"id": 0, "type": 0}', comment="目标托盘, 托盘id, 托盘类型")
        self.targetTray = p.loadParam("targetTray", type="str", default='{"id": 0, "type": 0}', comment="扫描对象托盘, 托盘id, 托盘类型")
        self.targetPosition = p.loadParam("targetPosition", type="str", default='{"x": 0, "y": 0, "theta": 0}', comment="位置定义")

        self.targetHeight = p.loadParam("targetHeight", type="float", default=0, comment="库位高度")
        self.locationType = p.loadParam("locationType", type="str", default="storage_shelf", comment="库位类型")
        self.preconditions = p.loadParam("preconditions", type="str", default='{"liftPositionMax": 0.0, "liftPositionMin": 0.0,'
                                                                              ' "forkRotationPositionMax": 0.0, "forkRotationPositionMin": 0.0,'
                                                                              ' "fingerPosition": 0}', comment="预备动作前置目标")
        self.box_width = p.loadParam("box_width", type="float", default=0, comment="货箱宽度配置值")
        self.box_height = p.loadParam("box_height", type="float", default=0, comment="货箱高度配置值")
        self.box_depth = p.loadParam("box_depth", type="float", default=0, comment="货箱深度配置值")
        self.box_tag_height = p.loadParam("box_tag_height", type="float", default=0, comment="货箱底部与货箱码下边沿的高度差")
        self.box_tag_depth = p.loadParam("box_tag_depth", type="float", default=0, comment="货箱码到货箱表面的贴码深度")
        self.shelf_tag_height = p.loadParam("shelf_tag_height", type="float", default=0, comment="货架放货平面与货架码上边沿的高度差")
        self.conveyor_tag_height = p.loadParam("conveyor_tag_height", type="float", default=0, comment="输送线放货平面(滚轮面)与货架码上边沿的高度差")
        self.gap_between_box = p.loadParam("gap_between_box", type="float", default=0, comment="货架上箱子之间的距离")

        self.init = True
        self.state = dict()
        # self.task = dict()
        self.h = Hairou(ip, port)
        self.h.connect()

    def run(self, r: SimModule, args):
        if r.errorExits(52111):
            return MoveStatus.FAILED

        self.status = MoveStatus.RUNNING
        r.setNotice(f"===args=== {json.dumps(args)}")
        if self.init:
            self.init = False
            self.update_param(r, args)

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

        if not self.h.mode == ModeType.TASK:
            r.setWarning("mode error!")
            self.h.switch_mode(r, ModeType.TASK)
            return self.status

        if self.status is not MoveStatus.FINISHED:
            self.state = self.h.getReport(r)
            if "connect_error" in self.state:
                dtime = time.time() - self.start_connect_time
                if dtime > self.max_connect_time:
                    r.setError("ctu connect is overtime: {}".format(self.max_connect_time))
                    self.status = MoveStatus.FAILED
                    str_state = json.dumps(self.state)
                    r.setInfo(str_state)
                    r.logDebug(str_state)
                    return self.status
            else:
                self.start_connect_time = time.time()

                
                
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
        if 'binModel' in args:
            self.binModel = args['binModel']
        if 'srcTray' in args:
            self.srcTray = args['srcTray']
        else:
            self.srcTray = json.loads(self.srcTray)
        if 'dstTray' in args:
            self.dstTray = args['dstTray']
        else:
            self.dstTray = json.loads(self.dstTray)
        if 'targetTray' in args:
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
        if self.locationType == 'storage_shelf_deep':
            self.locationType = LocationType.STORAGE_SHELF_DEEP
        if self.locationType == 'conveyor':
            self.locationType = LocationType.CONVEYOR


if __name__ == "__main__":
    r = SimModule()
    args = dict()
    m = Module(r, args)
    m.run(r, args)





















































