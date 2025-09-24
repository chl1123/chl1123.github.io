from syspy.v4.lib.rbk import core, service
import json


client_name = "pyServiceExampleClient"
core.Init(client_name)

server_name = "pyServiceExampleServer"

# str -> None
service.callService(server_name, "service1", request="test", no_return=True)

# dict -> None
service.callService(server_name, "service1", request={"a": 1, "b": 2}, no_return=True)

# 等待 1000 ms 超时
service.callService(
    server_name, "service1", request={"a": 1}, timeout_ms=1000, no_return=True
)

# dict -> str
ret = service.callService(
    server_name,
    "service2",
    request={
        "motor_name": "Motor-000",
        "pos": 1,
        "maxVel": 0.25,
        "stopDI": "false",
    },
)
print(json.loads(ret.decode()))

# (str, str) -> (str, str)
[bytes_ret, route_ret] = service.callService(
    server_name,
    "serviceDispatcher",
    request={"func_name": "func1", "arg": "test"},
    dispatcher=True,
)
print(json.loads(route_ret.decode()))
[bytes_ret, route_ret] = service.callService(
    server_name,
    "serviceDispatcher",
    request={"func_name": "func2", "arg": "test"},
    dispatcher=True,
)
print(json.loads(route_ret.decode()))
