import json
import logging
import threading
from typing import Optional, Union

import zmq

from syspy.lib.rpc import DOUBLE_COLON
from syspy.lib.rpc.json_rpc import JSONRPCRequest, JSONRPCResponse

log = logging.getLogger("rbk.script")
PYTHON_CPP_IPC = "ipc:///tmp/python2cpp_rpc.ipc"

_RPC_RECV_TIMEOUT_MS = 3000


class ZmqClient:
    """同步 ZMQ REQ 客户端（线程安全）。

    REQ socket 同步往返，用 lock 串行；超时后自动重建 socket。
    """

    def __init__(self, identity: Optional[str] = None):
        self._identity = identity
        self._addr: Optional[str] = None
        self._lock = threading.Lock()
        self._closed = False

        self.context = zmq.Context()
        self.socket: Optional[zmq.Socket] = None
        self.poller = zmq.Poller()
        self._open_socket()

    def _identity_bytes(self) -> bytes:
        if self._identity:
            return ("py::" + self._identity).encode("utf-8")
        return ("py::" + str(id(self))).encode("utf-8")

    def _open_socket(self):
        sock = self.context.socket(zmq.REQ)
        sock.setsockopt(zmq.IDENTITY, self._identity_bytes())
        sock.setsockopt(zmq.LINGER, 0)
        self.socket = sock
        self.poller.register(sock, zmq.POLLIN)
        if self._addr:
            sock.connect(self._addr)

    def _reset_socket(self):
        if self.socket is not None:
            try:
                self.poller.unregister(self.socket)
            except Exception:
                pass
            try:
                self.socket.close(linger=0)
            except Exception:
                pass
            self.socket = None
        self._open_socket()

    def connect(self, addr: str):
        with self._lock:
            self._addr = addr
            self.socket.connect(addr)

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def close(self):
        with self._lock:
            if self._closed:
                return
            self._closed = True
            log.debug("ZmqClient close the socket")
            if self.socket is not None:
                try:
                    self.poller.unregister(self.socket)
                except Exception:
                    pass
                try:
                    self.socket.close(linger=0)
                except Exception:
                    pass
                self.socket = None
            try:
                self.context.term()
            except Exception:
                pass

    def send_recv(self, payload: bytes, timeout_ms: int = _RPC_RECV_TIMEOUT_MS) -> Optional[bytes]:
        """同步发送并接收响应。超时或 socket 异常时返回 None 并重建 socket。"""
        with self._lock:
            if self._closed or self.socket is None:
                return None
            try:
                self.socket.send(payload)
            except zmq.ZMQError:
                self._reset_socket()
                return None

            events = dict(self.poller.poll(timeout_ms))
            if self.socket in events:
                try:
                    return self.socket.recv()
                except zmq.ZMQError:
                    self._reset_socket()
                    return None
            # 超时：REQ socket 已进入坏状态，必须重建以恢复后续调用
            self._reset_socket()
            return None


class RpcClient:
    _instance_lock = threading.Lock()
    _initialized = False  # 是否初始化完成

    def __new__(cls, *args, **kwargs):
        if not hasattr(RpcClient, "_instance"):
            with RpcClient._instance_lock:
                if not hasattr(RpcClient, "_instance"):
                    RpcClient._instance = object.__new__(cls)
        return RpcClient._instance

    def __init__(self, ipc=PYTHON_CPP_IPC, identity=None):
        if not RpcClient._initialized:
            self.zmq_client = ZmqClient(identity)
            self.zmq_client.connect(ipc)
            RpcClient._initialized = True

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

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

    def handle_request(self, method: str, params: Union[list, dict]):
        request = JSONRPCRequest(method, params)
        payload = request.to_json().encode("utf-8")
        result = self.zmq_client.send_recv(payload)
        if result is None:
            raise TimeoutError(
                f"Call RBK timeout, check whether RBK is running, {request.to_json()=}"
            )
        response_json = json.loads(result.decode())
        response = JSONRPCResponse.parse(response_json)
        if response.has_error():
            raise Exception(response_json)
        if log.isEnabledFor(logging.DEBUG):
            log.debug("res <= %s", response.get_print())
        return response.get_result()


if __name__ == "__main__":
    # client = RpcClient()
    #
    # print("client.setMotorPosition() ", client.call_service("MoveFactory", "setMotorPosition", "doMotor", 1.0, 2.0, 1))
    # import time
    #
    # while True:
    #     print("-----------")
    #     print("msgDI ", client.get_message("rbk.protocol.msgDI", "RBKSim"))
    #     print("msgBattery ", client.get_message("rbk.protocol.msgBattery", "RBKSim"))
    #     time.sleep(1)

    # 模拟 RBK RPC Client
    client = RpcClient("ipc:///tmp/cpp2broker.ipc")

    # print("client.start() ", client.call_service("broker", "start", "tasks/chl/get_script_data.py"))
    # print("client.stop() ", client.call_service("broker", "stop", "tasks/chl/get_script_data.py"))
    print("client.update_cmd() ", client.call_service(
        "tasks/v3/standard/example/jack_params.py",
        "update_cmd",
        {
            "args": {
                "operation": "load",
                "height": 0.03,
            },
            "configs": {
                'motorConfig.jackMotorName': 'Motor-001',
                'motorConfig.jackMotorSpeed': 0.025,
                'motorConfig.jackLiftZero': 0.1,
                'diConfig.jackUpDi': 7,
                'diConfig.jackZeroDi': 4
            },
            "taskId": 1
        }
    ))

    # print("client.suspend() ", client.call_service("tasks/jack/jack.py", "suspend"))
    # print("client.resume() ", client.call_service("tasks/jack/jack.py", "resume"))
    # print("client.cancel() ", client.call_service("tasks/jack/jack.py", "cancel"))

    # print("client.suspend() ", client.call_service(None, "suspend"))
    # print("client.resume() ", client.call_service(None, "resume"))
    # print("client.cancel() ", client.call_service(None, "cancel"))
