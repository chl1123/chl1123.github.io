from enum import Enum, IntEnum
import time
from rbkSim import SimModule
import math
import os, json

class MoveStatus(IntEnum):
    NONE = 0
    RUNNING = 1
    NEARTOGOAL = 2
    FINISHED = 3
    FAILED = 4
    SUSPENDED = 5

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

class BasicModule:
    def __init__(self):
        self.status = MoveStatus.NONE
        self.start_time = time.time()
    def run(self, r:SimModule, args):
        self.status = MoveStatus.FINISHED
        return self.status.value
    def reset(self, r:SimModule):
        self.status = MoveStatus.RUNNING
        self.start_time = time.time()
        r.logInfo("script reset")
    def suspend(self, r:SimModule):
        self.start_time = time.time()
        r.logInfo("script suspend")
        self.status = MoveStatus.SUSPENDED
    def cancel(self, r:SimModule):
        r.logInfo("script cancel")
        self.status = MoveStatus.NONE

class ParamServer:
    """
    参数服务:构建的参数以json的格式保存在params的文件夹下，参数文件名为脚本名称，后缀为json。
    如果默认数据没有，则创建。否则用文件中的数据
    目前支持的数据格式为str, float 和 int
    使用方式:
    p = ParamServer(__file__)
    param = p.loadParam("motor_name", "str", default = "motor1")
    """
    def __init__(self, file):
        isExists=os.path.exists("params")
        if not isExists:
            os.makedirs("params")
        base_f = os.path.basename(file)
        self.file = "params/"+base_f.split('.')[0] + '.json'
        self.data = dict()
        try:
            with open(self.file, 'r', encoding="utf-8") as f:
                self.data = json.load( f)
        except:
            pass
    def loadParam(self, name:str, type:str, **kw):
        updateFile = True    
        if type is "float" or type is "str" or type is "int":
            if "default" in kw: 
                if type is "str":
                    if name in self.data and "value" in self.data[name]:
                        updateFile = False
                    else:
                        self.data[name] = dict()
                        self.data[name]["value"] = str(kw["default"])
                elif "maxValue" in kw and "minValue" in kw:
                    if name in self.data:
                        updateFile = False
                    else:
                        self.data[name] = dict()
                        self.data[name]["value"] = eval(type)(kw["default"])   
                        self.data[name]["maxValue"] = eval(type)(kw["maxValue"])
                        self.data[name]["minValue"] = eval(type)(kw["minValue"])
                if "comment" in kw:
                    if "comment" in self.data[name] and self.data[name]["comment"] == kw["comment"]:
                        updateFile = False
                    else:
                        updateFile = True
                        self.data[name]["comment"] = kw["comment"]
                if updateFile:
                    with open(self.file, 'w', encoding="utf-8") as f: 
                        json.dump(self.data, f)        
                return self.data[name]["value"]
            else:
                raise Exception("loadParam no default key")
        else:
            raise Exception("loadParam Type (str, int, float) Error. Input Type is {}".format(type))