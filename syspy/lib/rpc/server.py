import json
import logging
import threading
from typing import Any

import zmq

from syspy.lib.rpc.json_rpc import JSONRPCRequest, JSONRPCResponse, MethodNotFound, InternalError
from ...utils import ScriptType

log = logging.getLogger("rbk.script")
server_addr = "ipc:///tmp/broker2server.ipc"  # 代理的后端地址


class RpcServer:
    FUNCS = {}  # 存储注册的函数
    SCRIPT_NAME = ""  # 当前脚本名称

    def __init__(self, name="", script_type: ScriptType = ScriptType.GENERAL):
        """初始化 RPC 服务器，并启动服务线程。

        Args:
            name (str): 脚本名称，用于注册到代理。
        """
        RpcServer.SCRIPT_NAME = name
        self.script_type = script_type
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.DEALER)  # 使用 DEALER 套接字
        self.socket.connect(server_addr)
        log.debug("Server connected to %s", server_addr)

        self.stop_flag = threading.Event()
        # 启动请求处理线程
        self.zmq_server_thread = threading.Thread(
            target=self._handle_request,
            args=(self.socket,),
            name="zmq_server_thread",
            daemon=True
        )

    def __del__(self):
        self.close()

    def registerFunction(self, function, method_name=""):
        """注册 Python 方法，以便远程调用。

        Args:
            function (callable): 要注册的函数。
            method_name (str): 方法名称，默认为函数名。
        """
        if not method_name:
            method_name = function.__name__
        RpcServer.FUNCS[method_name] = function

    def start(self):
        self._register_server(RpcServer.SCRIPT_NAME)
        self.zmq_server_thread.start()

    def _handle_request(self, socket):
        """处理来自客户端的请求。

        Args:
            socket (zmq.Socket): ZeroMQ 套接字，用于接收和发送消息。
        """
        while not self.stop_flag.is_set():
            try:
                # 接收请求
                message_parts = socket.recv_multipart()
                log.debug("Received message part: %s", message_parts)
                if len(message_parts) != 4:
                    log.debug("Invalid request format: %s", message_parts)
                    continue
                _, client_id, _, request_str = message_parts
                request_dict = json.loads(request_str.decode('utf-8'))
                request = JSONRPCRequest(**request_dict)

                # 处理请求
                method_name = request.get_method()
                response = JSONRPCResponse(request.get_id())
                if method_name in RpcServer.FUNCS:
                    try:
                        res = self._process_request(request)
                        response.set_result(res)
                    except Exception as e:
                        response.set_error(InternalError(e))
                else:
                    response.set_error(
                        MethodNotFound(f"{self.SCRIPT_NAME=}, Registered methods:{RpcServer.FUNCS.keys()}"))
                # 构造响应
                log.debug("Response => %s", response.to_json())

                # 发送响应
                socket.send_multipart([client_id, b"", response.to_json().encode('utf-8')])
            except zmq.ZMQError as e:
                if self.stop_flag.is_set():
                    break  # 关闭线程时会触发 ZMQError，结束循环
                log.error("zmqServer loop error, zmq.ZMQError: %s", e)
            except Exception as e:
                log.error("Error handling request: %s", e)
                break

    def _process_request(self, request: JSONRPCRequest) -> Any:
        """根据请求的方法名称和参数处理请求。

        Args:
            request (JSONRPCRequest): 请求的完整数据。

        Returns:
            方法返回值
        """
        func = RpcServer.FUNCS[request.get_method()]
        args = request.get_params()
        if args is None:
            res = func()
        elif isinstance(args, dict):
            res = func(**args)
        elif isinstance(args, list):
            res = func(*args)
        else:
            res = func(args)
        return res

    def _register_server(self, name):
        """注册服务到代理

        Args:
            name (str): 脚本名称，用于注册到代理。
        """

        # 发送注册信息到代理
        # register_msg = {"server": name}
        methods_name = list(RpcServer.FUNCS.keys())
        request = JSONRPCRequest("register_service", [name, methods_name, self.script_type])
        log.debug("Sending registration message: %s", request.to_json())
        self.socket.send_multipart([b"", request.to_json().encode('utf-8')])

        # 接收注册响应
        response_parts = self.socket.recv_multipart()
        log.debug("Received registration response: %s", response_parts)
        if len(response_parts) != 2:
            raise Exception("Invalid registration response format, check broker status")
        _, register_response_str = response_parts
        register_response = json.loads(register_response_str.decode('utf-8'))
        response = JSONRPCResponse.parse(register_response)
        if response.has_error():
            raise Exception(f"Registration failed: {response.get_error()}")
        log.debug("Registered successfully for %s", name)

    def close(self):
        log.debug("Closing RpcServer resources...")
        self.stop_flag.set()
        self.socket.close()  # 关闭 socket 会终止 recv 的阻塞状态
        self.context.term()  # 终止 context
        log.warning("context close")
