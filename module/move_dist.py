# -*- coding: utf-8 -*-
# @Date : 2022/9/26
# @Author : zhong
# @File :move_dist.py
# @Version : 1.0
# @Project : 传入移动距离参数，使机器人沿机器人坐标系x方向移动该距离
import sys
import json
import math

sys.path.append("syspy")
from syspy.rbkSim import SimModule
from syspy.rbk import MoveStatus, BasicModule
from syspy import goPath

"""
####BEGIN DEFAULT ARGS####
{
    "dist": {
        "value": 0.,
        "type": "double",
        "unit": "m"
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        self.goPath = goPath.Module(r, dict())
        self.init = True
        self.dist = 0
        self.status = MoveStatus.NONE
        self.go_args = dict()
        self.state = dict()
        self.init_loc_x = r.loc().get('x', None)
        self.init_odo_x = r.odo().get('x', None)

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            if "dist" in args:
                self.dist = args['dist']
            else:
                r.setError(f"args error: {args}")
            self.go_args["coordinate"] = "robot"
            self.go_args["x"] = self.dist
            self.go_args["y"] = 0
            self.go_args["theta"] = 0
            self.go_args["reachDist"] = 0.003
            self.go_args["reachAngle"] = math.pi
            self.go_args["useOdo"] = 1
            if self.go_args["x"] < 0:
                self.go_args["backMode"] = 1
            self.status = MoveStatus.RUNNING
        if self.goPath.status != MoveStatus.FINISHED and self.goPath.status != MoveStatus.FAILED:
            self.goPath.run(r, self.go_args)
        if self.goPath.status == 3:
            actual_move_dist = r.odo().get('x', None) - self.init_odo_x
            r.setNotice(f"actual_move_dist: {actual_move_dist}")

        self.state["move dist"] = args['dist']
        self.state["init_loc_x"] = self.init_loc_x
        self.state["init_odo_x"] = self.init_odo_x
        self.state["current_loc_x"] = r.loc().get('x', None)
        self.state["current_odo_x"] = r.odo().get('x', None)
        self.state["actual_move_dist_loc"] = r.loc().get('x', None) - self.init_loc_x
        r.setInfo(json.dumps(self.state))

        self.status = self.goPath.status
        return self.status




