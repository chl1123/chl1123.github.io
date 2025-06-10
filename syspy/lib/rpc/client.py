import json
import logging
import queue
import threading
from typing import Union

import zmq

from syspy.lib.rpc import DOUBLE_COLON
from syspy.lib.rpc.json_rpc import JSONRPCRequest, JSONRPCResponse

log = logging.getLogger("rbk.script")
PYTHON_CPP_IPC = "ipc:///tmp/python2cpp_rpc.ipc"


class ResultEvent(threading.Event):
    def __init__(self):
        super().__init__()
        self.result = None  # 添加 result 属性


class ZmqClient:
    def __init__(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)

        self.stop_flag = threading.Event()  # 线程关闭标志
        self.queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self.worker, name="ZmqClient", daemon=True)
        self.worker_thread.start()
        self.addr = PYTHON_CPP_IPC

    def __del__(self):
        self.close()

    def close(self):
        log.debug("ZmqClient close the socket")
        self.stop_flag.set()
        self.queue.put((None, None))
        if self.socket:
            self.socket.close()
        self.context.term()

    def connect(self, addr: str):
        self.socket.connect(addr)

    def putQueue(self, data: JSONRPCRequest, event: ResultEvent):
        # 将请求放入队列，并传入事件对象
        self.queue.put((data, event))

    def recv(self):
        return self.socket.recv()

    def worker(self):
        while not self.stop_flag.is_set():
            try:
                data, event = self.queue.get(timeout=1)
                self.socket.send(data.to_json().encode('utf-8'))  # 发送数据
                # 利用 self.poller.poll(5000) 对发送的数据进行轮询，等待最多 5000 毫秒
                events = dict(self.poller.poll(3000))
                # 如果 socket 在从 poll 返回的事件中，则表示收到了响应
                if self.socket in events:
                    response = self.recv()
                    event.result = response
                else:  # 5秒内没有收到响应（即 socket 不在从 poll 返回的事件中）
                    event.result = None
                    event.set()
                    self.stop_flag.set()
                event.set()
            except queue.Empty:
                continue
        log.debug("ZmqClient worker exit")


class RpcClient:
    _instance_lock = threading.Lock()
    _initialized = False  # 是否初始化完成

    def __new__(cls, *args, **kwargs):
        if not hasattr(RpcClient, "_instance"):
            with RpcClient._instance_lock:
                if not hasattr(RpcClient, "_instance"):
                    RpcClient._instance = object.__new__(cls)
        return RpcClient._instance

    def __init__(self, ipc=PYTHON_CPP_IPC):
        if not RpcClient._initialized:
            self.zmq_client = ZmqClient()
            self.zmq_client.connect(ipc)
            RpcClient._initialized = True

    def __del__(self):
        self.close()

    def close(self):
        self.zmq_client.close()

    def get_message(self, topic: str, plugin: str) -> str:
        return self.handle_request("NetProtocol::getMessage", [topic, plugin])

    def report(self, name: str, data) -> str:
        return self.handle_request("MoveFactory::scriptReport", [name, data])

    def set_info(self, info: str):
        return self.handle_request("MoveFactory::setInfo", [info])

    def call_service(self, plugin: str, function: str, /, *args, **kwargs):
        if args is None:
            args = []
        if plugin is not None:
            function = plugin + DOUBLE_COLON + function
        return self.handle_request(function, args)

    def __getattr__(self, function):
        def _func(*args, **kwargs):
            return self.handle_request(function, list(args))

        setattr(self, function, _func)
        return _func

    # 提取公共的部分为方法
    def handle_request(self, method: str, params: Union[list, dict]):
        request = JSONRPCRequest(method, params)
        event = ResultEvent()
        # 将请求放入队列，并传入事件对象
        self.zmq_client.putQueue(request, event)
        log.debug("req => %s", request.to_json())
        # 阻塞等待，直到工作线程处理完成并调用 event.set() 或 超时，避免无限等待
        if not event.wait(timeout=5):  # 设置适当的超时时间
            raise TimeoutError("Event wait timeout")
        # event.result 不为空，表示收到响应
        if event.result:
            response_json = json.loads(event.result.decode())
            response = JSONRPCResponse.parse(response_json)
            if response.has_error():
                raise Exception(response_json)
            log.debug("res <= %s", response.get_print())
            return response.get_result()
        else:  # event.result 为 None
            raise TimeoutError("poller Timeout")


if __name__ == "__main__":
    # client = RpcClient()
    #
    # print("client.setMotorPosition() ", client.call_service("MoveFactory", "setMotorPosition", "doMotor", 1.0, 2.0, 1))
    # import time
    #
    # while True:
    #     print("-----------")
    #     print("Message_DI ", client.get_message("rbk.protocol.Message_DI", "RBKSim"))
    #     print("Message_Battery ", client.get_message("rbk.protocol.Message_Battery", "RBKSim"))
    #     time.sleep(1)

    # 模拟RBK RPC Client
    client = RpcClient("ipc:///tmp/cpp2broker.ipc")

    print("client.update_cmd() ", client.call_service("broker", "import", "tasks/jack/jack.py"))

    # print("client.start() ", client.call_service("broker", "start", "tasks/chl/get_script_data.py"))
    # print("client.stop() ", client.call_service("broker", "stop", "tasks/chl/get_script_data.py"))
    # print("client.update_cmd() ", client.call_service("tasks/jack/jack.py", "update_cmd", {"operation": "getLM"}))
    # print("client.update_cmd() ",
    #       client.call_service("tasks/jack/jack.py", "update_cmd", {"operation": "odo"}))

    # print("client.update_cmd() ", client.call_service("tasks/jack/go_path.py", "update_cmd", {"operation": "odo"}))

    # print("client.update_cmd() ", client.call_service(
    #     "tasks/jack/go_path.py",
    #     "update_cmd",
    #     {"operation": "getCurrentPathProperty"}))

    # print("client.update_cmd() ",
    #       client.call_service("tasks/chl/get_script_data.py", "update_cmd", {"taskId": 1}))

    # print("client.suspend() ", client.call_service("tasks/jack/jack.py", "suspend"))
    # print("client.resume() ", client.call_service("tasks/jack/jack.py", "resume"))
    # print("client.cancel() ", client.call_service("tasks/jack/jack.py", "cancel"))

    # print("client.suspend() ", client.call_service(None, "suspend"))
    # print("client.resume() ", client.call_service(None, "resume"))
    # print("client.cancel() ", client.call_service(None, "cancel"))
