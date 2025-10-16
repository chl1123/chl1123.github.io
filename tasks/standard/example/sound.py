from syspy import ScriptStatus, Abnormal, Sound
from typing import Optional
import logging
log = logging.getLogger("rbk.script")

"""
####BEGIN DEFAULT ARGS####
{
    "name": {
        "value": "",
        "tips": "音频名称",
        "unit": "",
        "type": "string"
    },
    "loop":{
        "value":1,
        "tips": "1: loop, 0: once",
        "type": "int"
    },
    "stop":{
        "value":1,
        "tips": "1: close, 0: none",
        "type": "int"
    }   
}
####END DEFAULT ARGS####
"""
class Module:
    """让音乐响起来,默认只播放一遍
    """
    def __init__(self):
        self.init = True
        self.name = ""
        self.loop = False
        self.stop = False
        self.status = ScriptStatus.NONE
    def run(self, args: Optional[dict] = None):
        """主函数，每个运行周期都会执行run函数

        Args:
            args ([type]): 输入参数，是个json类

        Returns:
            [type]: 返回运行状态，ScriptStatus,用于表明脚本的运行状态
        """
        if self.status == ScriptStatus.FINISHED:
            return self.status.value
        self.status = ScriptStatus.RUNNING
        if self.init:
            if "name" in args:
                self.name = args["name"]
            if "loop" in args:
                self.loop = args["loop"] > 0
            if "stop" in args:
                self.stop = args["stop"] > 0
            self.init = False
        if self.name is not "" and self.status is not ScriptStatus.FAILED:
            Sound.setSound(self.name, self.loop)
        else:
            log.info("no sound!")
        if self.stop:
            Sound.stopSound(self.stop)
        self.status = ScriptStatus.FINISHED
        return self.status
    def cancel(self):
        Sound.stopSound(True)
        self.status = ScriptStatus.NONE

if __name__ == '__main__':
    m = Module()
    data = dict()
    data["name"] = "hello"
    data["loop"] = 1
    data["stop"] = 1
    print(m.run(data))