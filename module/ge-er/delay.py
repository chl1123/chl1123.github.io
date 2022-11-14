import time
from rbk import MoveStatus, BasicModule
from rbkSim import SimModule


"""
####BEGIN DEFAULT ARGS####
{
    "delay": {
        "value":5.0,
        "tips": "延时时间",
        "type": "float"
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        self.start_time = time.time()
        self.status = MoveStatus.NONE
        self.delay_time = None


    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        self.delay_time = args.get("delay", 5.0)
        if time.time() - self.start_time > self.delay_time:
            r.setNotice(f"Delay Finish")
            self.status = MoveStatus.FINISHED
        return self.status


if __name__ == '__main__':
    import rbkSim
    r = rbkSim.SimModule()
    m = Module(r, None)
    print(m.run(r, {}))
