from enum import Enum
import time
from rbkSim import SimModule
import math
class MoveStatus(Enum):
    NONE = 0
    RUNNING = 1
    NEARTOGOAL = 2
    FINISHED = 3
    FAILED = 4
    SUSPENDED = 5

def normalize_theta(theta):
    if theta >= -math.pi and theta < math.pi:
        return theta
    multiplier = math.floor(theta / (2 * math.pi))
    theta = theta - multiplier * 2 * math.pi
    if theta >= math.pi:
        theta = theta - 2 * math.pi
    if theta < -math.pi:
        theta = theta + 2 * math.pi
    return theta

class BasicModule:
    def __init__(self):
        self.status = MoveStatus.NONE
        self.start_time = time.time()
    def run(self, r:SimModule, args):
        self.status = MoveStatus.FINISHED
        return self.status.value
    def suspend(self, r:SimModule):
        self.start_time = time.time()
        r.logInfo("script suspend")
        self.status = MoveStatus.SUSPENDED
    def cancel(self, r:SimModule):
        r.logInfo("script cancel")
        self.status = MoveStatus.NONE