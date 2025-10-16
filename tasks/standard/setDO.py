from syspy import ScriptStatus, Abnormal, Do
from typing import Optional
"""
####BEGIN DEFAULT ARGS####
{
    "DO": {
        "value": [{"id":1,"status":true}],
        "tips": "DO列表",
        "type": "json"
    }
}
####END DEFAULT ARGS####
"""
class Module:
    """控制多个DO的开关
    """
    def __init__(self):
        self.init = True
        self.id = []        
        self.id_status = []
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
            if type(args) is dict and "DO" in args:
                data = args["DO"]
                self.id = [int(v.get('id')) for v in data]
                self.id_status = [v.get('status') for v in data]
            else:
                Abnormal.setTask(55900," No DO in task !!!","","","setDO")
                self.status = ScriptStatus.FAILED
                return self.status
            self.init = False
        for id, status in zip(self.id, self.id_status):
            Do.setDO(id, status)
        self.status = ScriptStatus.FINISHED
        return self.status

if __name__ == '__main__':
    m = Module()
    data = {"DO": [{"id":1, "status":True},{"id":2, "status":False},{"id":3, "status":False}]}
    print(m.run(data))