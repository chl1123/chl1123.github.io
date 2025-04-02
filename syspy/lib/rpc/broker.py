import importlib
import json
import os
import sys

import zmq

from syspy.lib.logger import Logger
from syspy.lib.rpc import DOUBLE_COLON
from syspy.lib.rpc.json_rpc import JSONRPCRequest, JSONRPCResponse, MethodNotFound, InvalidRequest

log = Logger(log_prefix="broker", console=True).get_logger()


class RegistryServer:
    """服务注册"""

    def __init__(self):
        self._services = {}

    def register_service(self, service_name, service_id):
        if service_name in self._services:
            log.warning(f"Service with name '{service_name}' already registered. Overwriting old service.")
        self._services[service_name] = {
            'id': service_id,
            'methods': set()
        }

    def unregister_service(self, service_name):
        if service_name in self._services:
            del self._services[service_name]
            log.info(f"Service with name '{service_name}' unregistered.")
        else:
            log.warning(f"Service with name '{service_name}' not found. Cannot unregister.")

    def add_method(self, service_name, method_name):
        if service_name not in self._services:
            log.warning(f"Service with name '{service_name}' not found. Cannot register method.")
            return False
        self._services[service_name]["methods"].add(method_name)
        log.info(f"{self._services=}")
        return True

    def get_services(self):
        return self._services

    def get_service_id(self, service_name) -> int:
        return self._services.get(service_name, {}).get("id", -1)

    def get_service_methods(self, service_name):
        return self._services.get(service_name, {}).get("methods", set())


class MessageDispatcher:
    """消息分发器"""

    def __init__(self, frontend: zmq.Socket, backend: zmq.Socket):
        self.frontend = frontend
        self.backend = backend
        self.registry_server = RegistryServer()

    def handle_frontend(self, msg: list):
        try:
            client_id, _, request_msg = msg
            log.info(f"Request <= {client_id=}, {request_msg=}")
            request_dict = json.loads(request_msg.decode('utf-8'))
            # 解析 request_dict 到 JSONRPCRequest 模型
            try:
                request = JSONRPCRequest.parse(request_dict)
            except InvalidRequest as error:
                log.error(f"Invalid JSON-RPC request: {error}")
                response = JSONRPCResponse()
                response.set_error(error)
                self.frontend.send_multipart([client_id, b"", response.to_json().encode('utf-8')])
                return
            bind_name = request.get_method()

            if DOUBLE_COLON in bind_name:
                # 取出脚本名，方法名
                script_name, method = bind_name.rsplit(DOUBLE_COLON, 1)
                if script_name == "broker" and method == "import":
                    response = JSONRPCResponse(request.get_id())
                    response.set_result(create_params(*request.get_params()))
                    self.frontend.send_multipart([client_id, b"", response.to_json().encode('utf-8')])
                    log.info(f"Response => {client_id=}, {response.to_json()=}")
                    return
                service_id = self.registry_server.get_service_id(script_name)
                request.set_method(method)
                if service_id == -1:
                    log.warning(f"No service found for name: {script_name}")
                    response = JSONRPCResponse(request.get_id())
                    response.set_error(MethodNotFound(f"No service found for name: {script_name}"))
                    self.frontend.send_multipart([client_id, b"", response.to_json().encode('utf-8')])
                    return
                # 转发请求到指定的服务端
                self.backend.send_multipart([service_id, b"", client_id, b"", request.to_json().encode('utf-8')])
                log.info(f"Response => {service_id=}, {client_id=}, {request_msg=}")
            else:
                service_methods = {
                    service_name: self.registry_server.get_service_methods(service_name)
                    for service_name in self.registry_server.get_services()
                }
                has_method = any(bind_name in methods for methods in service_methods.values())
                # 转发请求到多个服务端
                for service_id, methods in service_methods:
                    if bind_name in methods:
                        self.backend.send_multipart([service_id, b"", client_id, b"", request_msg])
                        log.info(f"Response => {service_id=}, {client_id=}, {request_msg=}")
                if not has_method:
                    log.warning(f"No method found for name: {bind_name}")
                    response = JSONRPCResponse(request.get_id())
                    response.set_error(MethodNotFound())
                    self.frontend.send_multipart([client_id, b"", response.to_json().encode('utf-8')])
        except Exception as e:
            log.error(f"Error handling frontend message: {e}")

    def handle_backend(self, msg: list):
        try:
            log.info(f"Request <= {msg}")
            if len(msg) == 3:  # 注册消息
                service_id, _, service_msg = msg
                register_info = json.loads(service_msg.decode('utf-8'))
                request = JSONRPCRequest.parse(register_info)
                method = request.get_method()
                params = request.get_params()
                response = JSONRPCResponse(request.get_id())

                if method == "register_service":  # 注册服务
                    self.registry_server.register_service(*params, service_id)
                    response.set_result(True)
                elif method == "add_method":  # 注册方法
                    add_method_flag = self.registry_server.add_method(*params)
                    if add_method_flag:
                        response.set_result(True)
                    else:
                        response.set_error(MethodNotFound(f"Service '{params}' not found. Cannot register method."))
                elif method == "unregister_service":  # 销毁服务
                    self.registry_server.unregister_service(*params)
                    response.set_result(True)
                else:
                    response.set_error(MethodNotFound(f"method: {method} not found"))
                self.backend.send_multipart([service_id, b"", response.to_json().encode('utf-8')])
                log.info(f"Response => {service_id=}, {response.to_json()=}")
            elif len(msg) == 4:  # 响应消息
                service_id, client_id, _, response_msg = msg
                self.frontend.send_multipart([client_id, b"", response_msg])
                log.info(f"Response => {client_id=}, {response_msg=}")
            else:
                log.error("Invalid message received")
        except Exception as e:
            log.error(f"Error handling backend message: {e}")


class Broker:
    """消息代理"""

    def __init__(self, frontend_addr: str, backend_addr: str):
        """初始化代理服务器
        
        Args:
            frontend_addr (str): 前端地址（客户端连接）
            backend_addr (str): 后端地址（服务端连接）
        """
        self.context = zmq.Context()
        self.frontend_addr = frontend_addr
        self.backend_addr = backend_addr
        self.frontend = self._setup_socket(zmq.ROUTER, frontend_addr)
        self.backend = self._setup_socket(zmq.ROUTER, backend_addr)
        self.dispatcher = MessageDispatcher(self.frontend, self.backend)
        self._setup_poller()

    def _setup_socket(self, sock_type: int, addr: str) -> zmq.Socket:
        sock = self.context.socket(sock_type)
        sock.bind(addr)
        return sock

    def _setup_poller(self):
        self.poller = zmq.Poller()
        self.poller.register(self.frontend, zmq.POLLIN)
        self.poller.register(self.backend, zmq.POLLIN)

    def start(self):
        log.info(f"Broker started: frontend={self.frontend_addr}, backend={self.backend_addr}")
        try:
            while True:
                socks = dict(self.poller.poll())
                if self.backend in socks and socks[self.backend] == zmq.POLLIN:
                    self.dispatcher.handle_backend(self.backend.recv_multipart())
                if self.frontend in socks and socks[self.frontend] == zmq.POLLIN:
                    self.dispatcher.handle_frontend(self.frontend.recv_multipart())
        except Exception as e:
            log.error(f"Broker encountered an error: {e}")
        finally:
            self._cleanup()

    def _cleanup(self):
        self.frontend.close()
        self.backend.close()
        self.context.term()


scripts_path = "/opt/.data/rbk/resources/scripts/"


def create_params(script_name: str):
    script_full_directory = scripts_path + script_name
    sys.path.append(scripts_path)
    module_name = os.path.splitext(os.path.basename(script_full_directory))[0]
    spec = importlib.util.spec_from_file_location(module_name, script_full_directory)
    foo = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(foo)
    except Exception as e:
        return -1, f"import module error: {e}"
    return 0, "success"


if __name__ == "__main__":
    frontend_addr = "ipc:///tmp/cpp2broker.ipc"  # 客户端连接地址
    backend_addr = "ipc:///tmp/broker2server.ipc"  # 服务端连接地址
    broker = Broker(frontend_addr, backend_addr)
    broker.start()
