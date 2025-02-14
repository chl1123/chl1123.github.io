import threading
import zmq
import json

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
        context = zmq.Context()
        self.socket = context.socket(zmq.DEALER)  # 使用 DEALER 套接字
        self.socket.connect(server_addr)
        log.info(f"Server connected to {server_addr}")
        self._register_server(name)

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
        register_msg = {"server": rpcServer.SCRIPT_NAME, "method": method_name}
        log.info(f"Sending registration method message: {register_msg}")
        self.socket.send_multipart([b"", json.dumps(register_msg).encode('utf-8')])

        # 接收注册响应
        response_parts = self.socket.recv_multipart()
        log.info(f"Received registration method response: {response_parts}")
        if len(response_parts) != 2:
            log.error("Invalid registration method response format")
            return
        empty, register_response_str = response_parts
        register_response = json.loads(register_response_str.decode('utf-8'))

        if register_response["code"] != 0:
            log.error(f"Registration failed: {register_response['error']}")
            return

        log.info(f"Registered function: {rpcServer.SCRIPT_NAME}.{method_name}")

    def start(self):
        # 启动请求处理线程
        zmq_server_thread = threading.Thread(
            target=self._handle_request,
            args=(self.socket,),
            name="zmq_server_thread",
            daemon=True
        )
        zmq_server_thread.start()

    def _handle_request(self, socket):
        """处理来自客户端的请求。

        Args:
            socket (zmq.Socket): ZeroMQ 套接字，用于接收和发送消息。
        """
        while True:
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
            except Exception as e:
                log.error(f"Error handling request: {e}")

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
        register_msg = {"server": name}
        log.info(f"Sending registration message: {register_msg}")
        self.socket.send_multipart([b"", json.dumps(register_msg).encode('utf-8')])

        # 接收注册响应
        response_parts = self.socket.recv_multipart()
        log.info(f"Received registration response: {response_parts}")
        if len(response_parts) != 2:
            log.error("Invalid registration response format")
            return
        empty, register_response_str = response_parts
        register_response = json.loads(register_response_str.decode('utf-8'))

        if register_response["code"] != 0:
            log.error(f"Registration failed: {register_response['message']}")
            return

        log.info(f"Registered successfully for {name}")
