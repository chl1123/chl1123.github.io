import json
from syspy.rbk import MoveStatus, BasicModule
from syspy.rbkSim import SimModule

""" 
####BEGIN DEFAULT ARGS####
{
    "vx": {
        "value": 0.0,
        "type": "double"
    },
    "vy": {
        "value": 0.0,
        "type": "double"
    },
    "rot":{
        "value": 0.0,
        "type": "double"
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        self.status = MoveStatus.RUNNING
        self.vx = 0
        self.vy = 0
        self.rot = 0
        r.logInfo(f"init args: {args}")

    def run(self, r: SimModule, args):
        nav = r.getNextSpeed()
        if self.status is not MoveStatus.FINISHED:
            if "vx" in args:
                self.vx = args["vx"]["value"]
            if "vy" in args:
                self.vy = args["vy"]["value"]
            if "rot" in args:
                self.rot = args["rot"]["value"]
            nav["x"] = self.vx
            nav["y"] = self.vy
            nav["rotate"] = self.rot
            r.setNextSpeed(json.dumps(nav))
            nav_str = r.speedDecomposition(json.dumps(nav))
            nav = json.loads(nav_str)
        if r.getCount() > 1000:
            self.status = MoveStatus.FINISHED
        nav["count"] = r.getCount()
        r.setInfo(json.dumps(nav))
        return self.status.value


if __name__ == '__main__':
    r = SimModule()
    m = Module(r, None)
    data = dict()
    data["vx"] = dict()
    data["vx"]["value"] = 0.3
    m.run(r, data)
