import platform
import time

import zmq, json, threading, sys, queue, os

sys.path.append('/usr/local/etc/.SeerRobotics/rbk/resources/scripts/site-packages/')
from google.protobuf.json_format import MessageToJson

sys.path.append('/opt/.data/rbk/resources/scripts/syspy/protobuf/')
if platform.machine() == 'x86_64':
    import message_battery_pb2
    import message_dmx512_pb2
elif platform.machine() == 'aarch64':
    import message_dmx512_arm_pb2 as message_dmx512_pb2
    import message_battery_aarch64_pb2 as message_battery_pb2

PYTHON_CPP_IPC = "ipc:///tmp/python2cpp_rpc.ipc"


# CPP_PYTHON_IPC = "ipc:///tmp/cpp2python_rpc.ipc"

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
    def get_message(self, topic: str, plugin: str):
        d = {
            "method_name": "NetProtocol::getMessage",
            "method_args": [topic, plugin],
            'method_kwargs': {}
        }
        return self.handle_request(d)

    # def put_message(self, name: str, data):
    #     dmx512 = message_dmx512_pb2.Message_Dmx512()
    #     battery = message_battery_pb2.Message_Battery()
    #     if (isinstance(data, type(dmx512)) or isinstance(data, type(battery))):
    #         data = MessageToJson(data)
    #     d = {
    #         "method_name": "putMessage",
    #         "method_args": [name, data],
    #         'method_kwargs': {}
    #     }
    #     print("put_message", d)
    #     return self.handle_request(d)

    def report(self, name: str, data):
        # 如果后缀有.py，去除
        # if name.endswith(".py"):
        #     name = name[:-3]
        dmx512 = message_dmx512_pb2.Message_Dmx512()
        battery = message_battery_pb2.Message_Battery()
        if (isinstance(data["report"], type(dmx512)) or isinstance(data["report"], type(battery))):
            data = MessageToJson(data["report"])
        if isinstance(data, dict):
            data = json.dumps(data)
        d = {
            "method_name": "report",
            "method_args": [name, data],
            'method_kwargs': {}
        }
        print("report", d)
        return self.handle_request(d)

    def call_service(self, plugin, function: str, *args, **kwargs):
        if args is None:
            args = {}
        if plugin is not None:
            function = plugin + "::" + function

        message = {"method_name": function, "method_args": args, "method_kwargs": kwargs}
        print("call_service", message)
        response = self.handle_request(message)
        return response

    def __getattr__(self, function):
        def _func(*args, **kwargs):
            try:
                d = {'method_name': function, 'method_args': args, 'method_kwargs': kwargs}
                return self.handle_request(d)
            except Exception as e:
                print('rpcStub error', e)

        setattr(self, function, _func)
        return _func

    # 提取公共的部分为方法
    def handle_request(self, d):
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
            return None


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
        message_battery = message_battery_pb2.Message_Battery()
        message_battery.percetage = 80
        message_battery.charge_current = 1.5
        print("client.put_message() ", message_battery)
        client.report("battery.py", message_battery)
        print("-----------")
        message = client.get_message("rbk.protocol.Message_DI", "RBKSim")
        print("client.get_message() ", message)
        print("getBattery", client.get_message("rbk.protocol.Message_Battery", "RBKSim"))
        time.sleep(1)