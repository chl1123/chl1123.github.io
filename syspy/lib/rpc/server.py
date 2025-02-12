import threading
import zmq
import json

from syspy.lib.logger import log

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
        self._start_server(name)

    def registerFunction(self, function, method_name=""):
        """注册 Python 方法，以便远程调用。

        Args:
            function (callable): 要注册的函数。
            method_name (str): 方法名称，默认为函数名。
        """
        if not method_name:
            method_name = function.__name__
        register_name = f"{rpcServer.SCRIPT_NAME}.{method_name}" if rpcServer.SCRIPT_NAME else method_name
        rpcServer.FUNCS[register_name] = function
        log.info(f"Registered function: {register_name}")

    def _start_server(self, name):
        """启动服务器，连接到代理并注册服务。

        Args:
            name (str): 脚本名称，用于注册到代理。
        """
        context = zmq.Context()
        self.socket = context.socket(zmq.DEALER)  # 使用 DEALER 套接字
        self.socket.connect(server_addr)
        log.info(f"Server connected to {server_addr}")

        # 发送注册信息到代理
        register_msg = {"name": name}
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
            log.error(f"Registration failed: {register_response['error']}")
            return

        log.info(f"Registered successfully for {name}")

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
                request = json.loads(request_str.decode('utf-8'))

                # 处理请求
                method_name = request.get("method")
                res = self._process_request(method_name, request)

                # 构造响应
                response = {"res": res, "code": 0}
                log.info(f"Response => {response}")

                # 发送响应
                socket.send_multipart([client_id, b"", json.dumps(response).encode('utf-8')])
            except Exception as e:
                log.error(f"Error handling request: {e}")

    def _process_request(self, method_name, request):
        """根据请求的方法名称和参数处理请求。

        Args:
            method_name (str): 请求的方法名称。
            request (dict): 请求的完整数据。

        Returns:
            Any: 处理结果，如果方法未找到则返回 -1。
        """
        if method_name in ["suspend", "resume", "cancel"]:
            return self._handle_control_methods(method_name)
        elif "name" in request and request["name"] == rpcServer.SCRIPT_NAME:
            register_name = f"{request['name']}.{method_name}" if request["name"] else method_name
            if register_name in rpcServer.FUNCS:
                func = rpcServer.FUNCS[register_name]
                args = request.get("args", [])
                if args:
                    return func(args)
                else:
                    return func()
        return -1

    def _handle_control_methods(self, method_name):
        """处理控制方法（如 suspend、resume、cancel）。

        Args:
            method_name (str): 控制方法名称。

        Returns:
            Any: 处理结果。
        """
        res = {}
        for func_name, func in rpcServer.FUNCS.items():
            if func_name.endswith(method_name):
                res = func()
        return res