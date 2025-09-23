from lib.rbk import core, service


def main():
    name = "pyServiceExampleClient"
    core.Init(name)

    server = "pyServiceExampleServer"

    # 没有输入参数
    ret = service.callService(server, "func1")
    print(f"ret: {ret}")

    # 输入参数为空字符串
    ret = service.callService(server, "func1", request="")
    print(f"ret: {ret}")

    # 输入参数为字符串
    ret = service.callService(server, "func1", request="test")
    print(f"ret: {ret}")

    # 输入参数为 dict, 内部转化为 json 字符串
    ret = service.callService(server, "func1", request={"a": 1, "b": 2})
    print(f"ret: {ret}")

    # 没有输入参数, 不设置超时等待
    ret = service.callService(server, "func2")
    print(f"ret: {ret}")

    # 没有输入参数, 服务超时等待设置为 1000 ms
    ret = service.callService(server, "func2", timeout_ms=1000)
    print(f"ret: {ret}")

    # serviceDispatcher
    route_json = dict()
    route_json["func_name"] = "func1"
    route_json["arg"] = "test"
    ret = service.callService(server, "serviceDispatcher", request=route_json)
    print(f"ret: {ret}")

    # 没有返回值
    service.callService(
        server,
        "runOdoMove",
        request={"move_dist": 1, "speed_x": 0.25, "action_name": "GoStraightForward"},
    )


if __name__ == "__main__":
    main()
