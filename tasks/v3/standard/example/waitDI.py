import time
from syspy import ScriptStatus, Abnormal, Di, Sound
from typing import Optional
import logging
log = logging.getLogger("rbk.script")
"""
####BEGIN DEFAULT ARGS####
{
    "soundName": {
        "value": "",
        "tips": "等待DI时，音频名称",
        "unit": "",
        "type": "string"
    }
}
####END DEFAULT ARGS####
"""
class Module:
    """让音乐响起来,默认只播放一遍
    """
    def __init__(self):
        self.init = True    
        self.id = []        
        self.id_status = []
        self.timeout = None
        self.start_time = time.time()
        self.status = ScriptStatus.NONE
        self.soundName = ""
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
            dis = args.get("DI",[])
            self.id = [v.get("id") for v in dis]
            self.id_status = [v.get("status") for v in dis]
            self.timeout = args.get("timeout",None)
            self.soundName = args.get("soundName","")
            self.start_time = time.time()
            self.init = False
        dis = Di.get_dis()
        wait_flag = False
        for tmp_id, tmp_v in zip(self.id, self.id_status):
            nodes = dis.get('node', [])
            for di in nodes:
                cur_id = di.get('id', None)
                cur_status = di.get('status', None)
                if cur_id is None or cur_status is None:
                    continue
                elif tmp_id == cur_id and tmp_v is not cur_status:
                    wait_flag = True
                    break
        if not wait_flag:
            self.status = ScriptStatus.FINISHED
        else:
            if self.timeout is not None:
                dt = time.time() - self.start_time
                if dt > self.timeout:
                    self.status = ScriptStatus.FINISHED
        if self.status is not ScriptStatus.FINISHED:
            Sound.setSound(self.soundName, True)
        return self.status

if __name__ == '__main__':
    m = Module()
    data = {"DI": [{"id":1, "status":True},{"id":2, "status":False}]}
    print(m.run(data))