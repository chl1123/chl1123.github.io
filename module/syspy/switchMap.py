
import json
import time
from rbk import MoveStatus, BasicModule, ParamServer
from rbkSim import SimModule
"""
####BEGIN DEFAULT ARGS####
{
    "map": {
        "value": "",
        "tips": "地图名称，无需后缀",
        "unit": "",
        "type": "string"
    },
    "switchPoint":{
        "value":"",
        "tips":"切换地图后重定位的点位",
        "unit":"",
        "type":"string"
    },
    "center_x": {
        "value": 0.0,
        "tips": "重定位点 x 坐标",
        "unit": "m",
        "type": "float"
    },
    "center_y": {
        "value": 0.0,
        "tips": "重定位点 y 坐标",
        "unit": "m",
        "type": "float"
    },
     "initiate_angle": {
        "value": 0.0,
        "tips": "重定位点朝向",
        "unit": "degree",
        "type": "float"
    }
}
####END DEFAULT ARGS####
"""
class Module(BasicModule):
    """让音乐响起来,默认只播放一遍
    """
    def __init__(self, r:SimModule, args):
        super(Module, self).__init__()
        self.init = True    
        self.status = MoveStatus.NONE
        self.map = ""
        self.switchPoint = ""
        self.center_x = 0.0
        self.center_y = 0.0
        self.initiate_angle = 0.0
    def run(self, r:SimModule,args):
        """主函数，每个运行周期都会执行run函数

        Args:
            r (SimModule): 是MoveFactory的类，包含了基本的电机控制，状态查询，消息查询的功能
            args ([type]): 输入参数，是个json类

        Returns:
            [type]: 返回运行状态，MoveStatus,用于表明脚本的运行状态
        """
        if self.status == MoveStatus.FINISHED:
            return self.status
        self.status = MoveStatus.RUNNING
        if self.init:
            self.map = args.get("map","")
            self.switchPoint = args.get("switchPoint","")
            self.center_x = args.get("center_x",0.0)
            self.center_y = args.get("center_y",0.0)
            # initiate_angle 为 65535 时表示执行原地切换地图动作
            self.initiate_angle = args.get("initiate_angle",0.0)
            self.init = False
        if self.map is not "":
            map_status = r.switchMap(self.map, self.switchPoint, self.center_x,  self.center_y, self.initiate_angle)
            if map_status is 0:
                self.status = MoveStatus.FINISHED
            elif map_status is -1:
                r.setError("switchMap Fail! no map {}".format(self.map))
                self.status = MoveStatus.FAILED
            elif map_status is -2:
                r.setError("switchMap Fail! {}".format(self.map))
                self.status = MoveStatus.FAILED
            else:
                self.status = MoveStatus.RUNNING
        else:
            r.logDebug("no map name!")
            self.status = MoveStatus.FINISHED
        return self.status

if __name__ == '__main__':
    import rbkSim
    r = rbkSim.SimModule()
    m = Module(r,None)
    data = {"map":"hello", "switchPoint":"LM1"}
    print(m.run(r, data))