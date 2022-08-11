import json
import sys
sys.path.append("syspy")
from syspy.rbkSim import SimModule
from syspy.rbk import MoveStatus, BasicModule
from module.pickRobot.ctuNoBlock import Module as ctu
"""
####BEGIN DEFAULT ARGS####
{
    "task": {
        "value": "",
        "tips": "任务",
        "unit": "",
        "type": "string"
    }
}
####END DEFAULT ARGS####
"""
class Module(BasicModule):
    """执行任务前会先执行海柔车的标零任务
    """
    def __init__(self, r:SimModule, args):
        super(Module, self).__init__()
        self.status = MoveStatus.RUNNING
        self.ctu = ctu(r, args)
        self.init = True
        self.task = None
    def run(self, r:SimModule,args):
        if self.status == MoveStatus.FINISHED:
            return self.status
        self.status = MoveStatus.RUNNING
        if self.init:
            self.task = args.get("task",None)
            self.init = False
        self.status = self.ctu.status
        if self.ctu.status == MoveStatus.RUNNING \
            or self.ctu.status == MoveStatus.NONE:
            ctu_args = dict()
            ctu_args["operation"] = "zero"
            self.ctu.run(r, ctu_args)
        elif self.ctu.status == MoveStatus.FINISHED:
            self.status = MoveStatus.RUNNING
            if type(self.task) == str:
                r.logDebug('str')
                r.addMoveTask(str(self.task))
            elif type(self.task) == dict:
                r.logDebug('dict')
                r.addMoveTask(json.dumps(self.task))
            else:
                r.setError('args error {}'.format(json.dumps(args)))
            self.status = MoveStatus.FINISHED
        return self.status
    def suspend(self, r:SimModule):
        self.ctu.suspend(r)
        self.status = MoveStatus.SUSPENDED
    def cancel(self, r:SimModule):
        self.ctu.cancel(r)
        self.status = MoveStatus.NONE

if __name__ == '__main__':
    import syspy.rbkSim
    r = syspy.rbkSim.SimModule()
    data = {"task":{"id":"LM1"}}
    m = Module(r,data)
    m.run(r,data)
    print(m.status, m.ctu.status)