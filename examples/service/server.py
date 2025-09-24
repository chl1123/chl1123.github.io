from syspy.v4.lib.rbk import core, service
import json
import time


# str -> None
def service1(arg: str) -> None:
    time.sleep(2)
    result = f"[{service1.__name__}|{arg}]"
    print(result)


# str -> str
def service2(route_json: str) -> str:
    request = json.loads(route_json)
    motor_name = request.get("motor_name", "")
    pos = request.get("pos", 0.0)
    maxVel = request.get("maxVel", 0.0)
    stopDI = request.get("stopDI", "")
    result = f"[{service2.__name__}|{motor_name}|{pos}|{maxVel}|{stopDI}]"
    print(result)
    response = [True, result]
    return json.dumps(response)


# str -> (str, str)
def serviceDispatcher(route_json: str) -> tuple[str, str]:
    def func1(arg: str) -> str:
        result = f"[{func1.__name__}|{arg}]"
        print(result)
        return result

    def func2(arg: str) -> str:
        result = f"[{func2.__name__}|{arg}]"
        print(result)
        return result

    request = json.loads(route_json)
    response = None
    func_name = request.get("func_name", "")
    if func_name == "func1":
        response = [True, func1(request.get("arg", ""))]
    elif func_name == "func2":
        response = [True, func2(request.get("arg", ""))]
    return "", json.dumps(response)


server_name = "pyServiceExampleServer"
core.Init(server_name)

service.addService(server_name, service1.__name__, service1, no_return=True)
service.addService(server_name, service2.__name__, service2)
service.addService(
    server_name, serviceDispatcher.__name__, serviceDispatcher, dispatcher=True
)

core.WaitForShutdown()
