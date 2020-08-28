import json
import time
from rbk import MoveStatus, BasicModule
from rbkSim import SimModule

class Module(BasicModule):
    def __init__(self, r:SimModule, args):
        super(Module, self).__init__()
    def run(self, r:SimModule,args):
        self.status = MoveStatus.FINISHED
        r.resetLocalShelfArea()
        return self.status.value
