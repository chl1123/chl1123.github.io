import os.path
import sys
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../")

from syspy.v4.include.rbk import core, service


name = "Navigation"
core.Init(name)

# Navigation
def setMotorPosition(args):
    print("args=", args)
    args_dict = json.loads(args)
    motor_name = args_dict.get("motor_name", "")
    pos = args_dict.get("pos", 0.0)
    maxVel = args_dict.get("maxVel", 0.0)
    stopDI = args_dict.get("stopDI", "")
    print("setMotorPosition", motor_name, pos, maxVel, stopDI)
    response = [
        True, "ok"
    ]
    return json.dumps(response)


def runOdoMove(params):
    """执行按里程运动的任务"""
    print("runOdoMove", params)
    # todo 需要4.0 SDK适配没有返回值，否则报错如下
    """
    [250717 152310.155][586335317][ServiceExampleClient][e] [ServiceManager][CallService|Navigation::runOdoMove|Unable to cast Python instance of type <class 'NoneType'> to C++ type '?' (#define PYBIND11_DETAILED_ERROR_MESSAGES or compile in debug mode for details)]
    """


service.addService(name, "setMotorPosition", setMotorPosition)
service.addService(name, "runOdoMove", runOdoMove)
core.WaitForShutdown()
