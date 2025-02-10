import zmq, json, threading
from syspy.lib.logger import log

class zmqSub(object):
    def __init__(self):
        self.funs = {}
        self.script_name = ""

        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect("ipc:///tmp/cpp2pythonSDK_rpc.ipc")
        self.socket.setsockopt(zmq.SUBSCRIBE, b'')
        self.data = None
        self.__should_close = threading.Event()  # 线程关闭标志
        self.__lock = threading.Lock()  # 创建锁对象
        self.msg_thread = threading.Thread(target=self.__loop, name="zmqSub", daemon=True)
        self.msg_thread.start()

    def close(self):
        log.info("zmqSub close the socket")
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
                log.info(f"zmqSub recv: {self.data}")
                res = {}
                if "method" not in self.data:
                    log.error("zmqSub recv: method not found")
                    continue
                method_name = self.data['method']
                if method_name in ["suspend", "resume", "cancel"]:
                    for func_name, func in self.funs.items():
                        # 如果func_name以method_name结尾，则调用
                        if func_name.endswith(method_name):
                            res = func()
                elif ("name" in self.data and self.data["name"] == self.script_name):
                    if self.data["name"] == "":
                        register_name = method_name
                    else:
                        register_name = self.data['name'] + '.' + method_name
                    if register_name in self.funs:
                        func = self.funs[register_name]
                        args = self.data['args']
                        if args is None:
                            res = func()
                        else:
                            res = func(args)
                    else:
                        continue
                else:
                    continue
                data = {"res": res, "code": 0}
                log.info(f"zmqSub data: {data}")
            except zmq.ZMQError as e:
                if self.__should_close.is_set():
                    break  # 关闭线程时会触发 ZMQError，结束循环
                log.error(f"zmqSub loop error, zmq.ZMQError: {e}")
            except Exception as e:
                log.error(f"zmqSub loop error, Exception: {e}")
                break


class rpcSub(zmqSub):
    def __init__(self):
        zmqSub.__init__(self)

    def registerFunction(self, function, method_name="", script_name=""):
        """注册python方法，以便RBK调用
        Args:
            function (): 方法
            method_name (str): 方法名
            script_name (str): 脚本名
        """
        self.script_name = script_name
        # 参数name 为空，则取函数名
        if method_name == "":
            method_name = function.__name__
        # 如果 script_name 为空，则取函数名
        if script_name == "":
            register_name = method_name
        else:  # 否则，取脚本名.函数名
            register_name = script_name + '.' + method_name
        self.funs[register_name] = function
        log.info(f"registerFunction: {self.funs}")


if __name__ == '__main__':
    class Test:
        def setChargeStateOn(self, args):
            self.need_charge = True
            print("setChargeStateOn: ", args)


    a = Test()
    test = rpcSub()
    test.registerFunction(a.setChargeStateOn)
    import time
    time.sleep(60)