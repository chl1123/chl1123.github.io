from lib.rbk import core, service
import json
import time


def func1(arg: str):
    response = f"func1, arg: {arg}"
    print(response)
    return response


def func2(arg: str):
    response = f"func2, arg: {arg}"
    print(response)
    time.sleep(2)
    return response


def serviceDispatcher(route_json: str):
    request = json.loads(route_json)
    response = dict()
    func_name = request["func_name"]
    if func_name == "func1":
        response["result"] = func1(request["arg"])
        return json.dumps(response)
    elif func_name == "func2":
        response["result"] = func2(request["arg"])
        return json.dumps(response)


def setMotorPosition(args):
    print("args=", args)
    request = json.loads(args)
    motor_name = request.get("motor_name", "")
    pos = request.get("pos", 0.0)
    maxVel = request.get("maxVel", 0.0)
    stopDI = request.get("stopDI", "")
    print("setMotorPosition", motor_name, pos, maxVel, stopDI)
    response = [True, "ok"]
    return json.dumps(response)


def runOdoMove(args):
    print("runOdoMove", args)
    # todo 需要4.0 SDK适配没有返回值，否则报错如下
    """
    [250717 152310.155][586335317][ServiceExampleClient][e] [ServiceManager][CallService|Navigation::runOdoMove|Unable to cast Python instance of type <class 'NoneType'> to C++ type '?' (#define PYBIND11_DETAILED_ERROR_MESSAGES or compile in debug mode for details)]
    """


def main():
    name = "pyServiceExampleServer"
    core.Init(name)

    service.addService(name, "func1", func1)
    service.addService(name, "func2", func2)
    service.addService(name, "serviceDispatcher", serviceDispatcher)
    service.addService(name, "setMotorPosition", setMotorPosition)
    service.addService(name, "runOdoMove", runOdoMove)

    core.WaitForShutdown()


if __name__ == "__main__":
    main()
