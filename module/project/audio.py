import math
import time

from rbk import BasicModule, MoveStatus
from rbkSim import SimModule

"""
####BEGIN DEFAULT ARGS####
{
    "location_name" :{
        "value": ["LM498", "", "", "", "", ""
        ],
        "tips": "站点名称",
        "type": "json"
    },
    "loop":{
        "value": 1,
        "tips": "循环播放次数",
        "type": "int"
    },
    "radius":{
        "value": 1,
        "default_value": 2,
        "tips": "区域半径",
        "type": "float",
        "uint": "m"
    }   
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        self.init = True
        self.status = MoveStatus.NONE
        self.state = dict()
        self.audio_name = None
        self.location = list()
        self.radius_num = None
        self.t = time.time()
        self.loop = None
        r.logInfo(f"init args: {args}")

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            args_state = False
            if "audio_name" not in args:
                r.setError("not filled in audio_name")
                args_state = True
            else:
                self.audio_name = args["audio_name"]

            if "location_name" not in args:
                r.setError("not filled in location_name")
                args_state = True
            else:
                name = args.get("location_name")
                for key in name:
                    if key != "":
                        self.location.append(key)

            if "loop" not in args:
                self.loop = 0
            elif args["loop"] <= 0:
                self.loop = 0
            else:
                self.loop = args["loop"]

            if "radius" not in args:
                r.setError("not filled in radius")
                args_state = True
            elif args["radius"] <= 0:
                r.setError("radius is negative num")
                args_state = True
            else:
                self.radius_num = args["radius"]

            if args_state:
                if not r.errorExits(53000):
                    r.setError(f"args error: {args}")
                return MoveStatus.FAILED

            if not self.check_pos(r):
                return MoveStatus.FINISHED

        # 获取小车位置信息
        loc_x = r.loc().get("x")
        loc_y = r.loc().get("y")

        data = self.check_in_area(loc_x, loc_y, r)
        if data[0]:
            self.play_sound(r, data[1])
        else:
            r.stopSound(True)
            self.status = MoveStatus.FINISHED

        self.state["args"] = args
        self.state["location"] = self.location
        self.state["loc_x"] = loc_x
        self.state["loc_y"] = loc_y
        r.logInfo(f"{self.state}")
        r.setInfo(f"{args}")
        return self.status

    def check_in_area(self, x, y, r: SimModule):
        """
        检查小车是否在播放区域
        return：tuple
            1：True：小车在播放区域内；False：小车不在播放区域
            2：库位名称
        """
        for i in self.location:
            distance = math.sqrt((r.getLM(i, True)[0] - x) ** 2 + (r.getLM(i, True)[1] - y) ** 2)
            if distance <= self.radius_num:
                return True, i
        return False, None

    def play_sound(self, r, audio_name):
        """
        播放指定音频
        return：
        """
        if (r.sound().get("status") == 0 or r.sound().get("status") == 1) and \
                self.loop > -1:
            r.setSound(audio_name, False)
            self.loop -= 1
        elif r.sound().get("status") == 2:
            self.status = MoveStatus.RUNNING
        if r.sound().get("status") == 0 and self.loop <= 0:
            t = time.time()
            r.setNotice(f"start: {self.t}, end: {t}, %d" % (t - self.t))
            self.status = MoveStatus.FINISHED

    def check_pos(self, r: SimModule):
        """
        检查地图中是否存在库位
        return：bool
             True：有效库位大于 0；False：无有效库位
        """
        for i in self.location:
            if r.getLM(i, True)[3] == -1:
                r.logWarn(f"do not exist {i}")
                self.location.remove(i)
        if not self.location:
            r.logInfo("location is empty")
            return False
        else:
            return True

    def cancel(self, r: SimModule):
        r.stopSound(True)
        self.status = MoveStatus.NONE
