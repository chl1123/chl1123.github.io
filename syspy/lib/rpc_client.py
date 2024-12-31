import platform
import time
from typing import overload, Optional

import zmq, json, threading, sys, queue, os

sys.path.append('/usr/local/etc/.SeerRobotics/rbk/resources/scripts/site-packages/')
sys.path.append('/opt/.data/rbk/resources/scripts/syspy/protobuf/')

PYTHON_CPP_IPC = "ipc:///tmp/python2cpp_rpc.ipc"

class zmqClient(object):
    def __init__(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)
        self.stop_flag = False
        self.func_json = ""
        self.queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self.worker, name="worker")
        self.worker_thread.start()

    def close(self):
        print("close the socket")
        self.stop_flag = True
        self.worker_thread.join()  # 等待线程结束
        self.socket.close()

    def connect(self, addr):
        self.socket.connect(addr)

    def putQueue(self, data, event):
        # 将请求放入队列，并传入事件对象
        self.queue.put((data, event))

    def recv(self):
        return self.socket.recv()

    def worker(self):
        while not self.stop_flag:
            try:
                data, event = self.queue.get(timeout=1)
                self.socket.send(data)  # 发送数据

                events = dict(self.poller.poll(5000))
                if self.socket in events:
                    response = self.recv()
                    event.result = response
                    # print(f"event.result: {event.result}")
                    event.set()
                else:
                    print("poller Timeout,exit")
                    event.result = None
                    event.set()
                    sys.exit(1)
            except queue.Empty:
                continue
            except Exception as e:
                print(f'worker error:{e},send{self.func_json}')
        print('exit worker')


class rpcStub(object):
    def get_message(self, topic: str, plugin: str) -> str:
        d = {
            "method_name": "NetProtocol::getMessage",
            "method_args": [topic, plugin],
            'method_kwargs': {}
        }
        return self.handle_request(d)

    def report(self, name: str, data) -> str:
        if isinstance(data, dict):
            data = json.dumps(data)
        d = {
            "method_name": "MoveFactory::report",
            "method_args": [name, data],
            'method_kwargs': {}
        }
        print("report", d)
        return self.handle_request(d)

    def call_service(self, plugin, function: str, *args, **kwargs) -> str:
        if args is None:
            args = []
        if plugin is not None:
            function = plugin + "::" + function

        message = {"method_name": function, "method_args": args, "method_kwargs": kwargs}
        print("call_service", message)
        response = self.handle_request(message)
        return response

    def __getattr__(self, function, plugin_name: str):
        def _func(plugin_name: Optional[str], *args, **kwargs):
            bind_function = function
            if plugin_name is not None:
                bind_function = plugin_name + "::" + function
            try:
                d = {'method_name': bind_function, 'method_args': args, 'method_kwargs': kwargs}
                return self.handle_request(d)
            except Exception as e:
                print('rpcStub error', e)

        setattr(self, function, _func)
        return _func

    # 提取公共的部分为方法
    def handle_request(self, d) -> str:
        self.func_json = json.dumps(d).encode('utf-8')
        event = threading.Event()
        self.putQueue(self.func_json, event)
        event.wait()
        if event.result:
            reply = json.loads(event.result.decode())
            return reply["res"]
        else:
            print("poller Timeout or No result")
            os._exit(1)
            return ""


class rpcClient(zmqClient, rpcStub):
    def __init__(self, ipc=PYTHON_CPP_IPC):
        zmqClient.__init__(self)
        rpcStub.__init__(self)
        self.connect(ipc)


if __name__ == "__main__":
    client = rpcClient()
    # print("client.add() ", client.setOn({"a": 1, "b": 2}, 123))
    print("client.sub() ", client.setMotorPosition("doMotor", 1.0, 2.0, 1))

    print("-----------")
    while True:
        print("-----------")
        message = client.get_message("rbk.protocol.Message_DI", "RBKSim")
        print("client.get_message() ", message)
        print("getBattery", client.get_message("rbk.protocol.Message_Battery", "RBKSim"))
        time.sleep(1)