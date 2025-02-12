import time
import uuid

from syspy.lib.logger import log
import zmq, json, threading, queue

PYTHON_CPP_IPC = "ipc:///tmp/python2cpp_rpc.ipc"


class zmqClient(object):
    def __init__(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)
        self.stop_flag = threading.Event()  # 线程关闭标志
        self.func_json = ""
        self.queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self.worker, name="zmqClient", daemon=True)
        self.worker_thread.start()

    def __del__(self):
        self.close()

    def close(self):
        log.info("zmqClient close the socket")
        self.stop_flag.set()
        self.queue.put((None, None))
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
        while not self.stop_flag.is_set():
            try:
                data, event = self.queue.get(timeout=1)
                self.socket.send(json.dumps(data).encode('utf-8'))  # 发送数据
                # 利用 self.poller.poll(5000) 对发送的数据进行轮询，等待最多 5000 毫秒
                events = dict(self.poller.poll(5000))
                # 如果 socket 在从 poll 返回的事件中，则表示收到了响应
                if self.socket in events:
                    response = self.recv()
                    event.result = response
                else:  # 5秒内没有收到响应（即 socket 不在从 poll 返回的事件中）
                    event.result = None
                event.set()
            except queue.Empty:
                continue
            except Exception as e:
                if self.stop_flag.is_set():
                    break
                log.error(f"worker error:{e}, send{self.func_json}")
        log.info("zmqClient worker exit")


class rpcStub(object):
    def get_message(self, topic: str, plugin: str) -> str:
        return self.handle_request("NetProtocol::getMessage", [topic, plugin])

    def report(self, name: str, data) -> str:
        if isinstance(data, dict):
            data = json.dumps(data)
        return self.handle_request("MoveFactory::report", [name, data])

    def call_service(self, plugin, function: str, /, *args, **kwargs):
        if args is None:
            args = []
        if plugin is not None:
            function = plugin + "::" + function
        return self.handle_request(function, list(args))

    def __getattr__(self, function):
        def _func(*args, **kwargs):
            try:
                return self.handle_request(function, list(args))
            except Exception as e:
                log.error(f"rpcStub error:{e}")

        setattr(self, function, _func)
        return _func

    # 提取公共的部分为方法
    def handle_request(self, method: str, params: list):
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": str(uuid.uuid4())
        }
        event = threading.Event()
        # 将请求放入队列，并传入事件对象
        self.putQueue(request, event)
        log.info(f"req => {request}")
        # 阻塞等待，直到工作线程处理完成并调用 event.set() 通知结果已经返回
        event.wait()
        # 如果 event.result 不为空，则表示收到了响应
        if event.result:
            response = json.loads(event.result.decode())
            if "error" in response:
                log.error(f"res <= {response}")
            else:
                log.info(f"res <= {response}")
                return response["result"]
        else:  #  event.result 为 None
            log.error("poller Timeout")
            return ""


class rpcClient(zmqClient, rpcStub):
    def __init__(self, ipc=PYTHON_CPP_IPC):
        zmqClient.__init__(self)
        rpcStub.__init__(self)
        self.connect(ipc)


if __name__ == "__main__":
    client = rpcClient()
    # print("client.add() ", client.setOn({"a": 1, "b": 2}, 123))
    print("client.setMotorPosition() ", client.setMotorPosition(plugin="MoveFactory", params=("doMotor", 1.0, 2.0, 1)))

    print("-----------")
    while True:
        print("-----------")
        message = client.get_message("rbk.protocol.Message_DI", "RBKSim")
        print("client.get_message() ", message)
        print("getBattery", client.get_message("rbk.protocol.Message_Battery", "RBKSim"))
        time.sleep(1)
