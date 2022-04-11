# -*- coding: utf-8 -*-
# @Time : 2022/4/11
# @Author : qiangsheng
# @File : armTask.py
# @Request : issue_pool#3020 荣成拼合单 roboview#1358
# @Version: 0.5

import json
import time
import sys

sys.path.append("..")
sys.path.append("../syspy")
from syspy.rbkSim import SimModule
from syspy.rbk import MoveStatus, BasicModule, Pos2World, normalize_theta, ParamServer
import math
import syspy.goPath as goPath
import os
"""
####BEGIN DEFAULT ARGS####
{
    "operation":{
        "value": "load",
        "default_value":[
        "unload","load"
        ],
        "tips": "tips",
        "type": "complex"        
    },
    "container": {
        "value": 0,
        "tips": "背篓号，如果缺省将自动放在对应的背篓中",
        "type": "int",
        "unit": ""
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    """这个文件是控制机械臂机构的脚本
    用户运行脚本前需要提前准备一个armData.json。这个json文件是用来给出不同库位对于load和unload的具体操作。
    下面这个例子是库位1,2,3的load和unload基本格式，其中每个库位的load, unload三个关键字必填, 如果goodsType不填，则默认goodsType为0：
    {
        "1": {
            "load": [],
            "unload": []
        },
        "2": {
            "load": [],
            "unload": []
        },
        "3": {
            "load": [],
            "unload": []
        }
    }
    """    
    def __init__(self, r:SimModule, args):
        super(Module, self).__init__()
        param_dir = os.path.dirname(__file__)
        self.armFile = os.path.join(param_dir, "armData.json")
        self.armData = None

        with open(self.armFile) as fp:
            self.armData = json.load(fp)

        for k,v in self.armData.items():
            if "load" not in v:
                r.setError("container {} load is missing.".format(k))
                self.type2c = dict()
                break
            if "unload" not in v:
                r.setError("container {} unload is missing.".format(k))
                self.type2c = dict()
                break

        self.operation = None
        self.goodsId = None
        self.container = None

        self.cmd = None
        self.init = True
        self.start_time = None
        self.armArgs = None
        self.taskid = None

    def reset(self, r:SimModule) -> MoveStatus:
        self.status = MoveStatus.RUNNING
        self.init = True

    def failTask(self, r:SimModule):
        r.stopRobot(True)
        self.status = MoveStatus.FAILED
        return self.status
    def run(self, r:SimModule,args):
        if self.status == MoveStatus.SUSPENDED:
            r.armResume()
        self.status = MoveStatus.RUNNING
        if self.armData == None:
            r.setError("cannot load {}".format(self.armFile))
            return self.failTask(r)
        armInfo = r.getArmInfo()
        if self.init:
            self.init = False
            self.start_time = time.time()
            self.operation = args.get("operation",None)
            self.container = args.get("container",None)
            self.getArmArgsAndGoodsId(r)
            if self.armArgs is None:
                r.setError("armArgs is missing.")
                return self.failTask(r)
            self.taskid = armInfo["taskId"] + 1
            if self.operation == "load" or self.operation == "unload":
                if not isinstance(self.armArgs, list):
                    r.setError("armArgs should be list. {}".format(self.armArgs))
                scriptInsert_num = 0
                for a in self.armArgs:
                    if "type" in a:
                        if a["type"] == "ScriptInsert":
                            scriptInsert_num += 1
                if scriptInsert_num != 1:
                    r.setError("armArgs should have only one ScriptInsert. {}".format(self.armArgs))
                    return self.failTask(r)

                # 加载货物没有给goodsId
                if self.goodsId == "" and self.goodsId is None and self.operation == "load":
                    r.setError("goodsId is wrong {}.".format(self.goodsId))
                    return self.failTask(r)

                # 获取背篓信息
                cur_containers = r.getContainers()
                cur_cs = dict()
                for v in cur_containers:
                    cur_cs[v["container_name"]] = v

                # find the container
                if self.operation == "load":
                    for cn in cur_cs:
                        cur_c = cur_cs[cn]
                        if cur_c["has_goods"] == False:
                            self.container = cn
                            break
                    #load again error
                    if self.container is None:
                        r.setError("all {} containers {} have goods, cannot load again.".format(self.goodsType, str(cs)))
                        return self.failTask(r)
                    #背篓名称错误
                    if self.container not in self.armData:
                        r.setError("container is wrong {} is not in the {}.".format(self.container, self.armFile))
                        return self.failTask(r)
                    
                    c = self.armData[self.container]
                    # operation 错误  
                    if self.operation not in c:
                        r.setError("container {} and operation {} is mismatch.".format(self.container, self.operation))
                        return self.failTask(r)    

                    self.cmd= c[self.operation]

                elif self.operation == "unload":

                    if self.goodsId is None:
                        r.setError("goodsId is missing in unload.")
                        return self.failTask(r)         

                    for k, v in cur_cs.items():
                        if v["goods_id"] == self.goodsId:
                            self.container = k
                            break
                    #没有对应的货物
                    if self.container is None:
                        r.setError("No container has goodId {}, cannot unload.".format(self.goodsId))
                        return self.failTask(r)                  
                    #背篓名称错误
                    if self.container not in self.armData:
                        r.setError("container is wrong {} is not in the {}.".format(self.container, self.armFile))
                        return self.failTask(r)

                    c = self.armData[self.container]
                    # operation 错误  
                    if self.operation not in c:
                        r.setError("container {} and operation {} is mismatch.".format(self.container, self.operation))
                        return self.failTask(r)    

                    self.cmd= c[self.operation]

                # armBinTask这个函数可能会有变化
                # TODO 拼一下识别的字符串
                replace_num = -1
                for n, a in enumerate(self.armArgs):
                    if "type" in a:
                        if a["type"] == "ScriptInsert":
                            replace_num = n
                if replace_num >= 0:
                    out_args = self.armArgs
                    out_args = out_args[0:replace_num] + self.cmd + out_args[replace_num+1::]
                    r.armBinTask(self.taskid, json.dumps(out_args))
            else:
                r.armBinTask(self.taskid, json.dumps(self.armArgs))
            r.logDebug("ArmInitS][{}|{}|{}|{}|{}".format(self.container, self.operation, self.goodsId, self.taskid, self.cmd))      
        if armInfo["taskId"] == self.taskid:
            if armInfo["task_status"] == 2:
                if self.operation == "load":
                    if isinstance(self.container, str) and isinstance(self.goodsId, str):
                        r.setContainer(self.container, self.goodsId, "")
                    else:
                        r.setError("type error. container {}, goodsId {}".format(type(self.container), type(self.goodsId)))
                        return self.failTask(r)
                elif self.operation == "unload":
                    if isinstance(self.container, str):
                        r.clearContainer(self.container)
                    else:
                        r.setError("type error. container {}, goodsId {}".format(type(self.container), type(self.goodsId)))
                        return self.failTask(r)
                self.status = MoveStatus.FINISHED
            elif armInfo["task_status"] == 3:
                r.setError("arm task is failed {}")
                self.status = MoveStatus.FAILED
        r.logDebug("ArmS][{}|{}|{}|{}".format(armInfo["taskId"], armInfo["task_status"], self.status, time.time()-self.start_time));        
        return self.status
    def getArmArgsAndGoodsId(self, r:SimModule):
        moveTask = r.moveTask()
        if "params" in moveTask:
            for p in moveTask["params"]:
                if p["key"] == "armArgs":
                    cmd_str = p["string_value"]
                    self.armArgs = json.loads(cmd_str)
                if p['key'] == 'goodsId':
                    self.goodsId = p['string_value']

    def suspend(self, r:SimModule):
        if self.status is not MoveStatus.SUSPENDED:
            r.armPause()
            self.status = MoveStatus.SUSPENDED
        r.logInfo("task suspend")
    def cancel(self, r:SimModule):
        r.armStop()
        self.status = MoveStatus.NONE
        r.logInfo("task cancel")


if __name__ == '__main__':
    sim = SimModule()
    print("********load********")
    args = {
        "operation":"load",
    }
    print(args)
    m = Module(sim, args)
    m.run(sim,args)
    print("********unload********")
    args = {
        "operation":"unload"
    }
    print(args)
    m = Module(sim, args)
    m.run(sim,args)

    print("********no, op********")
    args = {
    }
    print(args)
    m = Module(sim, args)
    m.run(sim,args)

    m.suspend(sim)
    m.cancel(sim)