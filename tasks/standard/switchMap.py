from syspy import ScriptStatus, Abnormal, Map
from typing import Optional
import logging
log = logging.getLogger("rbk.script")
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
    }
}
####END DEFAULT ARGS####
"""
class Module:
    """让音乐响起来,默认只播放一遍
    """
    def __init__(self):
        self.init = True
        self.status = ScriptStatus.NONE
        self.map = ""
        self.switchPoint = ""
    def run(self, args: Optional[dict] = None):
        """主函数，每个运行周期都会执行run函数

        Args:
            args ([type]): 输入参数，是个json类

        Returns:
            [type]: 返回运行状态，ScriptStatus,用于表明脚本的运行状态
        """
        if self.status == ScriptStatus.FINISHED:
            return self.status
        self.status = ScriptStatus.RUNNING
        if self.init:
            self.map = args.get("map","")
            self.switchPoint = args.get("switchPoint","")
            self.init = False
        if self.map is not "":
            map_status = Map.switchMap(self.map, self.switchPoint)
            if map_status is 0:
                self.status = ScriptStatus.FINISHED
            elif map_status is -1:
                Abnormal.setTask(53900,"switchMap Fail! no map {}".format(self.map),"","","switchMap")
                self.status = ScriptStatus.FAILED
            elif map_status is -2:
                Abnormal.setTask(53900,"switchMap Fail! {}".format(self.map),"","","switchMap")
                self.status = ScriptStatus.FAILED
            else:
                self.status = ScriptStatus.RUNNING
        else:
            log.debug("no map name!",self.map)
            self.status = ScriptStatus.FINISHED
        return self.status

if __name__ == '__main__':
    m = Module()
    data = {"map":"hello", "switchPoint":"LM1"}
    print(m.run(data))