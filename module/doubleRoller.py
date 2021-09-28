# -*- coding: utf-8 -*-
import json
from rbk import MoveStatus, BasicModule
from rbkSim import SimModule
import SchneiderV3


""" 
####BEGIN DEFAULT ARGS####
{
    "roller_high": {
        "value": "",
        "default_value": [
            "load", "unload", "stop"
        ],
        "tips": "上层滚筒操作",
        "type": "complex"
    },
    "roller_low": {
        "value": "",
        "default_value": [
            "load", "unload", "stop"
        ],
        "tips": "下层滚筒操作",
        "type": "complex"
    },
    "roller_high_direction": {
        "value": "",
        "default_value": [
            "left", "right"
        ],
        "tips": "方向",
        "type": "complex"
    },
    "roller_low_direction": {
        "value": "",
        "default_value": [
            "left", "right"
        ],
        "tips": "方向",
        "type": "complex"
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        self.m1 = SchneiderV3.Module(r, dict())
        self.m2 = SchneiderV3.Module(r, dict())
        self.roller_high = None
        self.roller_low = None
        self.m1_args = dict()
        self.m2_args = dict()
        self.m1_status = MoveStatus.NONE
        self.m2_status = MoveStatus.NONE
        self.status = MoveStatus.NONE
        self.state = dict()
        self.init = True
        r.logInfo(f"init args: {args}")


    def run(self, r: SimModule, args):
        if self.init:
            self.init = False
            if "roller_high" not in args or "roller_low" not in args or "roller_high_direction" not in args or "roller_low_direction" not in args:
                r.setError(f"missing args! check the args: {args}")
                self.status = MoveStatus.FAILED
            else:
                self.roller_high = args["roller_high"]
                self.roller_low = args["roller_low"]

        self.m1_args["direction"] = args["roller_high_direction"]
        self.m2_args["direction"] = args["roller_low_direction"]
        self.m1_args["jackHeight"] = 0.0
        self.m2_args["jackHeight"] = 0.0
        if self.roller_high == "load":
            self.m1_args["operation"] = "roller_high_load"
        elif self.roller_high == "unload":
            self.m1_args["operation"] = "roller_high_unload"
        elif self.roller_high == "stop":
            self.m1_args["operation"] = "RollerStop"
        elif self.roller_high == "pre":
            self.m1_args["operation"] = "pre_roller_high"
        else:
            r.setError(f"roller_high args error!")
            self.status = MoveStatus.FAILED

        if self.roller_low == "load":
            self.m2_args["operation"] = "roller_low_load"
        elif self.roller_low == "unload":
            self.m2_args["operation"] = "roller_low_unload"
        elif self.roller_low == "stop":
            self.m2_args["operation"] = "RollerStop"
        elif self.roller_low == "pre":
            self.m2_args["operation"] = "pre_roller_high"
        else:
            r.setError(f"roller_low args error!")
            self.status = MoveStatus.FAILED

        if self.status is MoveStatus.FAILED:
            return self.status

        self.status = MoveStatus.RUNNING

        self.m1.run(r, self.m1_args)
        self.m2.run(r, self.m2_args)
        self.m1_status = self.m1.status
        self.m2_status = self.m2.status
        if self.m1_status == MoveStatus.FINISHED and self.m2_status == MoveStatus.FINISHED:
            self.status = MoveStatus.FINISHED
        if self.m1_status == MoveStatus.FAILED or self.m2_status == MoveStatus.FAILED:
            self.status = MoveStatus.FAILED

        self.state["status"] = self.status
        self.state["roller_high"] = self.m1_args
        self.state["roller_low"] = self.m2_args
        r.setInfo(json.dumps(self.state))
        return self.status
