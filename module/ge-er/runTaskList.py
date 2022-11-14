import json
import time
import uuid

import addMoveTaskList
from rbk import MoveStatus, BasicModule
from rbkSim import SimModule
"""
####BEGIN DEFAULT ARGS####
{
    "move_task_list": {
		"value": [],
		"type": "json"
	}
}
####END DEFAULT ARGS####
"""
class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        self.start_time = time.time()
        self.status = MoveStatus.NONE
        self.task_list = None
        self.init = True
        self.run_task = addMoveTaskList.Module(r, args)
        r.logDebug(str(args))

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.task_list = args.get("move_task_list", None)
            r.setNotice(f"armExe running: {r.getCount()}")
            r.setWarning(f"task_list: {self.task_list}")

        if self.task_list:
            for task in self.task_list:
                task["task_id"] = ''.join(str(uuid.uuid4()).split('-'))
        data = {"move_task_list": self.task_list}
        self.run_task.run(r, data)
        self.status = MoveStatus.FINISHED
        r.setInfo(json.dumps(args))
        return self.status


if __name__ == '__main__':
    pass
