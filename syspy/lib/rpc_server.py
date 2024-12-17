import os

import zmq, json, threading
import inspect

class zmqServer(object):
    def __init__(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind("ipc:///tmp/cpp2python_rpc.ipc")
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
                print(f"server: {self.data}")
                method_name = self.data['method']
                if method_name in ["suspend", "reset", "cancel"]:
                    for func_name, func in self.funs.items():
                        # 如果func_name以method_name结尾，则调用
                        if func_name.endswith(method_name):
                            res = func()
                elif method_name == "update_cmd":
                    if "name" in self.data and self.data['name'] != "":
                        method_name = self.data['name'] + '.' + method_name
                    if method_name in self.funs:
                        func = self.funs[method_name]
                        args = self.data['args']
                        print(f'method_name: {method_name}')
                        if args is None:
                            res = func()
                        if isinstance(args, dict):
                            res = func(**args)
                        elif isinstance(args, list):
                            res = func(*args)
                        else:
                            res = func(args)
                    else:
                        res = -1
                else:
                    res = -1
                data = {"res": res, "code": 0}
                print(f'data: {data}')
                self.socket.send(json.dumps(data).encode('utf-8'))
            except zmq.ZMQError as e:
                #self.socket.send(json.dumps({"code": -1}).encode('utf-8'))
                if self.__should_close.is_set():
                    break  # 关闭线程时会触发 ZMQError，结束循环
                print('server loop error, zmq.ZMQError: ', e)
            except Exception as e:
                self.socket.send(json.dumps({"code": -1}).encode('utf-8'))
                print('server loop error, Exception: ', e)
                break


class rpcStub(object):
    def __init__(self):
        self.funs = {}

    def registerFunction(self, function, name=None, script_name=None):
        # 获取当前文件名
        if name is None:
            name = function.__name__
        if script_name is None:
            script_name = inspect.stack()[1].filename
        name = script_name + '.' + name
        print("registerFunction", name)
        self.funs[name] = function
        print("registerFunction", self.funs)


class rpcServer(zmqServer, rpcStub):
    def __init__(self):
        zmqServer.__init__(self)
        rpcStub.__init__(self)


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
    test = rpcServer()
    test.registerFunction(a.setOn, "setOn")
    test.registerFunction(a.exit, "exit")