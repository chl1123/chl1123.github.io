import json
import time
from rbk import MoveStatus, BasicModule

class Module(BasicModule):
    def __init__(self, r, args):
        super(Module, self).__init__()
    def run(self, r,args):
        di = r.Di()
        print(r.navSpeed())
        for (ind,node) in enumerate(di['node']):
            print("di:" , ind, node)
        self.status = MoveStatus.FINISHED
        r.resetLocalShelfArea()
        return self.status.value
