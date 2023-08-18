from enum import Enum, IntEnum
import time
from rbkSim import SimModule
import math
import os, json
import math


class MoveStatus(IntEnum):
    NONE = 0
    RUNNING = 1
    NEARTOGOAL = 2
    FINISHED = 3
    FAILED = 4
    SUSPENDED = 5

class CollisionType(IntEnum):
    Ultrasonic = 0
    Laser = 1
    Fallingdown = 2
    Collision = 3
    Infrared = 4
    VirtualPoint = 5
    APIObstacle = 6
    ReservedPoint = 7
    DiUltrasonic = 8
    DepthCamera = 9
    ReservedDepthCamera = 10
    DistanceNode = 11

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
    pos2world = [0.,0.,0.]
    x = pos2base[0] * math.cos(base2world[2]) - pos2base[1] * math.sin(base2world[2])
    y = pos2base[0] * math.sin(base2world[2]) + pos2base[1] * math.cos(base2world[2])
    pos2world[0] = x + base2world[0]
    pos2world[1] = y + base2world[1]
    pos2world[2] = normalize_theta(pos2base[2] + base2world[2])
    return pos2world


def Pos2Base(pos2world, base2world):
    """将基于世界坐标系的两个位姿，转换为基于base的位姿

    Args:
        pos2world ([3]): 被转换的位姿，基于世界坐标系,0:x, 1:y, 2: theta
        base2world ([3]): 基准，基于世界坐标系,0:x, 1:y, 2: theta
    Returns:
        [3]: pos2base
    """
    pos2base = [0.,0.,0.]
    x = pos2world[0] - base2world[0]
    y = pos2world[1] - base2world[1]
    pos2base[0] = x * math.cos(base2world[2]) + y * math.sin(base2world[2])
    pos2base[1] = -x * math.sin(base2world[2]) + y * math.cos(base2world[2])
    pos2base[2] = normalize_theta(pos2world[2] - base2world[2])
    return pos2base


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
        # r.logInfo("script reset")

    def suspend(self, r:SimModule):
        self.start_time = time.time()
        # r.logInfo("script suspend")
        self.status = MoveStatus.SUSPENDED

    def cancel(self, r:SimModule):
        # r.logInfo("script cancel")
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
        param_dir = os.path.dirname(file) + '/params'
        isExists=os.path.exists(param_dir)
        if not isExists:
            os.makedirs(param_dir)
        base_f = os.path.basename(file)
        self.file = param_dir + '/'+base_f.split('.')[0] + '.json'
        self.data = dict()
        try:
            with open(self.file, 'r', encoding="utf-8") as f:
                self.data = json.load( f)
        except:
            pass

    def loadParam(self, name:str, type:str = "", default = None, **kw):
        def updateKey(data, key, value):
            if (key not in data)  or (key in data and data[key] != value):
                return True
            else:
                return False

        updateFile = False    
        if type is "float" or type is "str" or type is "int":
            if default is not None: 
                if name not in self.data:
                    updateFile = True
                    self.data[name] = dict()
                if "value" not in self.data[name]:
                    updateFile = True
                    self.data[name]["value"] = eval(type)(default)
                if updateKey(self.data[name], "default", default):
                    updateFile = True
                    self.data[name]["default"] = default
                if type is "float" or type is "int":
                    if "maxValue" in kw and updateKey(self.data[name], "maxValue", kw["maxValue"]):
                        updateFile = True
                        self.data[name]["maxValue"] = kw["maxValue"]
                    if "minValue" in kw and updateKey(self.data[name], "minValue", kw["minValue"]):
                        updateFile = True
                        self.data[name]["minValue"] = kw["minValue"]                    
                if "comment" in kw and updateKey(self.data[name], "comment", kw["comment"]):
                        updateFile = True
                        self.data[name]["comment"] = kw["comment"]
                if "unit" in kw and updateKey(self.data[name], "unit", kw["unit"]):
                        updateFile = True
                        self.data[name]["unit"] = kw["unit"]
                if updateFile:
                    with open(self.file, 'w', encoding="utf-8") as f: 
                        json.dump(self.data, f, indent=4, ensure_ascii=False)        
                return self.data[name]["value"]
            else:
                raise Exception("loadParam no default key")
        else:
            raise Exception("loadParam Type (str, int, float) Error. Input Type is {}".format(type))
