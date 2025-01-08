import zmq, json, threading
import inspect


class zmqSub(object):
    def __init__(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect("ipc:///tmp/cpp2pythonSDK_rpc.ipc")
        self.socket.setsockopt(zmq.SUBSCRIBE, b'')
        self.data = None
        self.__should_close = threading.Event()  # 线程关闭标志
        self.__lock = threading.Lock()  # 创建锁对象
        self.msg_thread = threading.Thread(target=self.__loop, name="loop")
        self.msg_thread.start()

    def close(self):
        print("close the socket")
        self.__should_close.set()  # 通知线程关闭
        self.socket.close()  # 关闭 socket 会终止 recv 的阻塞状态
        self.context.term()  # 终止 context
        self.msg_thread.join()  # 等待线程结束

    def send(self, data):
        with self.__lock:
            self.socket.send(data)

    def recv(self):
        with self.__lock:
            return self.socket.recv()

    def __loop(self):
        while not self.__should_close.is_set():
            try:
                message = self.socket.recv()  # 阻塞等待消息
                self.data = json.loads(message.decode('utf-8'))

                print(f"Sub: {self.data}")
                print("self.script_name, ", self.script_name)
                method_name = self.data['method']
                if method_name in ["suspend", "reset", "cancel"]:
                    for func_name, func in self.funs.items():
                        # 如果func_name以method_name结尾，则调用
                        if func_name.endswith(method_name):
                            res = func()
                elif method_name == "update_cmd" and "name" in self.data and self.data["name"] == self.script_name:
                    # if "name" in self.data and self.data['name'] != "":
                    method_name = self.data['name'] + '.' + method_name
                    if method_name in self.funs:
                        func = self.funs[method_name]
                        args = self.data['args']
                        if args is None:
                            res = func()
                        else:
                            res = func(args)
                        # if isinstance(args, dict):
                        #     res = func(**args)
                        # elif isinstance(args, list):
                        #     res = func(*args)
                        # else:
                        #     res = func(args)
                    else:
                        res = -1
                else:
                    res = -1
                data = {"res": res, "code": 0}
                print(f'data: {data}')
                # self.socket.send(json.dumps(data).encode('utf-8'))
            except zmq.ZMQError as e:
                # self.socket.send(json.dumps({"code": -1}).encode('utf-8'))
                if self.__should_close.is_set():
                    break  # 关闭线程时会触发 ZMQError，结束循环
                print('Sub loop error, zmq.ZMQError: ', e)
            except Exception as e:
                # self.socket.send(json.dumps({"code": -1}).encode('utf-8'))
                print('Sub loop error, Exception: ', e)
                break


class rpcStub(object):
    def __init__(self):
        self.funs = {}
        self.script_name = None

    def registerFunction(self, function, name=None, script_name=None):
        self.script_name = script_name
        print("self.script_name", self.script_name)
        # 获取当前文件名
        if name is None:
            name = function.__name__
        if script_name is None:
            self.script_name = inspect.stack()[1].filename
        script_func_name = self.script_name + '.' + name
        print("registerFunction", script_func_name)
        self.funs[script_func_name] = function
        print("registerFunction", self.funs)


class rpcSub(zmqSub, rpcStub):
    def __init__(self):
        rpcStub.__init__(self)
        zmqSub.__init__(self)


if __name__ == '__main__':
    class Test:
        def setOn(self, args, param):
            print("is me ", args)
            print("is me ", param)
            return 123

        def exit(self):
            print("exit")
            # sys.exit()


    a = Test()
    test = rpcSub()
    test.registerFunction(a.setOn, "setOn")
    test.registerFunction(a.exit, "exit")
