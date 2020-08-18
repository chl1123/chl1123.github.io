from enum import Enum
import time
class MoveStatus(Enum):
    NONE = 0
    RUNNING = 1
    NEARTOGOAL = 2
    FINISHED = 3
    FAILED = 4
    SUSPENDED = 5

class BasicModule:
    def __init__(self):
        self.status = MoveStatus.NONE
        self.start_time = time.time()
    def run(self, r, args):
        self.status = MoveStatus.FINISHED
        return self.status.value
    def suspend(self, r):
        self.start_time = time.time()
        r.logInfo("script suspend")
        self.status = MoveStatus.SUSPENDED
    def cancel(self, r):
        r.logInfo("script cancel")
        self.status = MoveStatus.NONE