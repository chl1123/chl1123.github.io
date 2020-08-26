import json
import time
from rbk import MoveStatus, BasicModule

class Module(BasicModule):
    def __init__(self, r, args):
        super(Module, self).__init__()
    def run(self, r,args):
        self.status = MoveStatus.FINISHED
        r.resetLocalShelfArea()
        return self.status.value
