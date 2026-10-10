import json
import logging
import os
import threading
from typing import Optional, Union

import zmq

from syspy.lib.rpc import DOUBLE_COLON
from syspy.lib.rpc.json_rpc import JSONRPCRequest, JSONRPCResponse

log = logging.getLogger("rbk.script")
PYTHON_CPP_IPC = "ipc:///tmp/python2cpp_rpc.ipc"
PYTHON_CPP_BIN_IPC = "ipc:///tmp/python2cpp_binmsg.ipc"

_RPC_RECV_TIMEOUT_MS = 3000


def _anon_identity() -> str:
    """空身份时的兜底标记。

    原先用 ``str(id(self))``（对象内存地址），同一个进程每次运行都变，在 trace 里
    只能看到一串无法关联到脚本的数字。改用自描述且同进程稳定的 pid 标记。
    """
    return f"anon-pid{os.getpid()}"


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
        return ("py::" + _anon_identity()).encode("utf-8")

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

    def set_identity(self, identity: Optional[str]) -> bool:
        """更新 ZMQ identity 并重建 socket。

        ZMQ 的 identity 只能在 connect 前通过 setsockopt 设置，因此已建好的 socket
        必须重建才能换身份。重建走与 send_recv 相同的锁，避免在途请求拿到已关闭的
        socket（否则抛 ZMQError: Socket operation on non-socket）。

        Returns:
            bool: 是否真的做了重建。
        """
        if not identity or identity == self._identity:
            return False
        with self._lock:
            if self._closed:
                return False
            self._identity = identity
            self._reset_socket()
        return True

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
            self._identity = identity
            self.zmq_client = ZmqClient(identity)
            self.zmq_client.connect(ipc)
            RpcClient._initialized = True
        elif identity and identity != getattr(self, "_identity", None):
            # 单例已由更早的调用（如导入期的配置加载）建立，且当时没有 script_id。
            # 这里在拿到真实身份后回填，否则 trace 里只能看到匿名标记。
            self.rebind_identity(identity)

    def rebind_identity(self, identity: Optional[str]) -> bool:
        """拿到真实 script_id 后回填 ZMQ identity。

        脚本可能在 ``Module.init()`` 之前就因配置加载而首次发出 RPC（如 fork 系列在
        模块级构造实例），当时 ``script_id`` 还是空字符串，单例身份因而被定型成匿名标记。
        回填会重建 socket，因此调用方应选在无并发请求的时间点（例如 ``Module.init``）。

        Returns:
            bool: 是否真的更新了身份。
        """
        if not identity or identity == getattr(self, "_identity", None):
            return False
        self._identity = identity
        return self.zmq_client.set_identity(identity)

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


class BinMsgClient:
    """纯二进制消息通道客户端（独立 ZMQ REQ socket，连 C++ 端独立 binmsg ROUTER）。

    协议：
        请求: [topic_bytes][plugin_bytes]
        响应: [protobuf_binary]   (空 bytes 表示无消息)
    """

    _instance_lock = threading.Lock()
    _instance: "Optional[BinMsgClient]" = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = object.__new__(cls)
        return cls._instance

    def __init__(self, ipc: str = PYTHON_CPP_BIN_IPC, identity: Optional[str] = None):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._lock = threading.Lock()
        self._addr = ipc
        self._identity = identity
        self._closed = False
        self.context = zmq.Context()
        self.socket: Optional[zmq.Socket] = None
        self.poller = zmq.Poller()
        self._open_socket()

    def _identity_bytes(self) -> bytes:
        if self._identity:
            return ("py-bin::" + self._identity).encode("utf-8")
        return ("py-bin::" + _anon_identity()).encode("utf-8")

    def _open_socket(self):
        sock = self.context.socket(zmq.REQ)
        sock.setsockopt(zmq.IDENTITY, self._identity_bytes())
        sock.setsockopt(zmq.LINGER, 0)
        sock.connect(self._addr)
        self.socket = sock
        self.poller.register(sock, zmq.POLLIN)

    def set_identity(self, identity: Optional[str]) -> bool:
        """更新 ZMQ identity 并重建 socket（语义同 ZmqClient.set_identity）。

        与 get_message 共用同一把锁，避免在途请求拿到已关闭的 socket。
        """
        if not identity or identity == self._identity:
            return False
        with self._lock:
            if self._closed:
                return False
            self._identity = identity
            self._reset_socket()
        return True

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

    def close(self):
        with self._lock:
            if self._closed:
                return
            self._closed = True
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

    def get_message(self, topic: str, plugin: str,
                    timeout_ms: int = _RPC_RECV_TIMEOUT_MS) -> Optional[bytes]:
        """返回 protobuf 二进制；无消息返回 b''；超时/异常返回 None。"""
        with self._lock:
            if self._closed or self.socket is None:
                return None
            try:
                self.socket.send(topic.encode("utf-8"), zmq.SNDMORE)
                self.socket.send(plugin.encode("utf-8"))
            except zmq.ZMQError:
                self._reset_socket()
                return None

            events = dict(self.poller.poll(timeout_ms))
            if self.socket not in events:
                self._reset_socket()
                return None
            try:
                return self.socket.recv()
            except zmq.ZMQError:
                self._reset_socket()
                return None


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
