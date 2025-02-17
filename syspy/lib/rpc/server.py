import threading
import zmq
import json
import atexit

from syspy.lib.logger import log
from syspy.lib.rpc.json_rpc import JSONRPCRequest, JSONRPCResponse, MethodNotFound, InternalError

# 全局变量
server_addr = "ipc:///tmp/broker2server.ipc"  # 代理的后端地址


class rpcServer:
    FUNCS = {}  # 存储注册的函数
    SCRIPT_NAME = ""  # 当前脚本名称

    def __init__(self, name=""):
        """初始化 RPC 服务器，并启动服务线程。

        Args:
            name (str): 脚本名称，用于注册到代理。
        """
        rpcServer.SCRIPT_NAME = name
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.DEALER)  # 使用 DEALER 套接字
        self.socket.connect(server_addr)
        log.info(f"Server connected to {server_addr}")
        self._register_server(name)
        self.stop_flag = threading.Event()
        # 启动请求处理线程
        self.zmq_server_thread = threading.Thread(
            target=self._handle_request,
            args=(self.socket,),
            name="zmq_server_thread",
            daemon=True
        )
        # 注册退出函数，rpcServer结束时自动调用 unregister_server
        atexit.register(self.close)

    def registerFunction(self, function, method_name=""):
        """注册 Python 方法，以便远程调用。

        Args:
            function (callable): 要注册的函数。
            method_name (str): 方法名称，默认为函数名。
        """
        if not method_name:
            method_name = function.__name__
        rpcServer.FUNCS[method_name] = function

        # 发送注册信息到代理
        request = JSONRPCRequest("register_method", [rpcServer.SCRIPT_NAME, method_name])
        log.info(f"Sending registration method message: {request.to_json()}")

        self.socket.send_multipart([b"", request.to_json().encode('utf-8')])

        # 接收注册响应
        response_parts = self.socket.recv_multipart()
        log.info(f"Received registration method response: {response_parts}")
        if len(response_parts) != 2:
            log.error("Invalid registration method response format")
            return
        empty, register_response_str = response_parts
        register_response = json.loads(register_response_str.decode('utf-8'))

        response = JSONRPCResponse.parse(register_response)
        if response.has_error():
            log.error(f"Unregister failed: {response.get_error()}")
            return
        log.info(f"Registered function: {rpcServer.SCRIPT_NAME}.{method_name}")

    def start(self):
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
                log.info(f"Received message part: {message_parts}")
                if len(message_parts) != 4:
                    log.warning(f"Invalid request format: {message_parts}")
                    continue
                empty, client_id, empty, request_str = message_parts
                request_dict = json.loads(request_str.decode('utf-8'))
                request = JSONRPCRequest(**request_dict)

                # 处理请求
                method_name = request.get_method()
                response = JSONRPCResponse(request.get_id())
                if method_name in rpcServer.FUNCS:
                    try:
                        res = self._process_request(request)
                        response.set_result(res)
                    except Exception as e:
                        response.set_error(InternalError())
                else:
                    response.set_error(MethodNotFound())
                # 构造响应
                log.info(f"Response => {response.to_json()}")

                # 发送响应
                socket.send_multipart([client_id, b"", response.to_json().encode('utf-8')])
            except zmq.ZMQError as e:
                if self.stop_flag.is_set():
                    break  # 关闭线程时会触发 ZMQError，结束循环
                log.error(f"zmqServer loop error, zmq.ZMQError: {e}")
            except Exception as e:
                log.error(f"Error handling request: {e}")
                break

    def _process_request(self, request: JSONRPCRequest):
        """根据请求的方法名称和参数处理请求。

        Args:
            request (JSONRPCRequest): 请求的完整数据。

        Returns:
            方法返回值
        """
        func = rpcServer.FUNCS[request.get_method()]
        args = request.get_params()
        if args:
            return func(args)
        else:
            return func()

    def _register_server(self, name):
        """启动服务器，连接到代理并注册服务。

        Args:
            name (str): 脚本名称，用于注册到代理。
        """

        # 发送注册信息到代理
        # register_msg = {"server": name}
        request = JSONRPCRequest("register_service", [name])
        log.info(f"Sending registration message: {request.to_json()}")
        self.socket.send_multipart([b"", request.to_json().encode('utf-8')])

        # 接收注册响应
        response_parts = self.socket.recv_multipart()
        log.info(f"Received registration response: {response_parts}")
        if len(response_parts) != 2:
            log.error("Invalid registration response format")
            return
        empty, register_response_str = response_parts
        register_response = json.loads(register_response_str.decode('utf-8'))
        response = JSONRPCResponse.parse(register_response)
        if response.has_error():
            log.error(f"Registration failed: {response.get_error()}")
            return

        log.info(f"Registered successfully for {name}")

    def _unregister_server(self, name):
        """注销服务，断开与代理的连接。
        """
        request = JSONRPCRequest("unregister_service", [name])
        self.socket.send_multipart([b"", request.to_json().encode('utf-8')])

        # 接收注册响应
        response_parts = self.socket.recv_multipart()
        if len(response_parts) != 2:
            return
        empty, register_response_str = response_parts
        register_response = json.loads(register_response_str.decode('utf-8'))
        response = JSONRPCResponse.parse(register_response)
        if response.has_error():
            log.error(f"Unregister failed: {response.get_error()}")
            return
        log.info(f"Unregistered successfully for {name}")

    def close(self):
        log.info("Closing rpcServer resources...")
        self.stop_flag.set()
        self.socket.close()  # 关闭 socket 会终止 recv 的阻塞状态
        self.context.term()  # 终止 context
        log.error(f"context close")
        self.zmq_server_thread.join(timeout=2)  # 设置超时时间为2秒，确保线程尽快退出

        try:
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.DEALER)  # 使用 DEALER 套接字
            self.socket.connect(server_addr)
            self._unregister_server(rpcServer.SCRIPT_NAME)
        except Exception as e:
            log.error(f"Error during unregister: {e}")
