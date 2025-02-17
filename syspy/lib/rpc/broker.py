import zmq
import json

from syspy.lib.logger import log
from syspy.lib.rpc import DOUBLE_COLON
from syspy.lib.rpc.json_rpc import JSONRPCRequest, JSONRPCResponse, JSONRPCError, MethodNotFound, InvalidRequest


class ServiceMap:
    def __init__(self):
        self.service_mapping = {}

    def register_service(self, service_name, service_id):
        if service_name in self.service_mapping:
            log.warning(f"Service with name '{service_name}' already registered. Overwriting old service.")
        self.service_mapping[service_name] = {}
        self.service_mapping[service_name]["id"] = service_id

    def unregister_service(self, service_name):
        if service_name in self.service_mapping:
            del self.service_mapping[service_name]
            log.info(f"Service with name '{service_name}' unregistered.")
        else:
            log.warning(f"Service with name '{service_name}' not found. Cannot unregister.")

    def register_method(self, service_name, method_name):
        log.info(f"self.service_mapping: {self.service_mapping}")
        if service_name not in self.service_mapping:
            log.warning(f"Service with name '{service_name}' not found. Cannot register method.")
            return False
        if "method" not in self.service_mapping[service_name]:
            self.service_mapping[service_name]["method"] = []
        self.service_mapping[service_name]["method"].append(method_name)
        log.info(f"self.service_mapping: {self.service_mapping}")
        return True

    def get_services(self):
        return self.service_mapping

    def get_service_id(self, service_name):
        return self.service_mapping.get(service_name).get("id", None)

    def get_service_methods(self, service_name):
        return self.service_mapping.get(service_name, {}).get("method", [])


class Broker:
    def __init__(self, frontend_addr, backend_addr):
        self.context = zmq.Context()
        self.frontend = None
        self.frontend_addr = frontend_addr
        self.backend = None
        self.backend_addr = backend_addr
        self.service_mapping = ServiceMap()
        self._setup_sockets()
        self._setup_poller()

    def _setup_sockets(self):
        try:
            # 创建 ROUTER 套接字监听客户端请求
            self.frontend = self.context.socket(zmq.ROUTER)
            self.frontend.bind(self.frontend_addr)

            # 创建 ROUTER 套接字连接到服务端
            self.backend = self.context.socket(zmq.ROUTER)
            self.backend.bind(self.backend_addr)
        except zmq.ZMQError as e:
            log.error(f"Failed to setup sockets: {e}")
            raise

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
                    self._handle_backend_message()
                if self.frontend in socks and socks[self.frontend] == zmq.POLLIN:
                    self._handle_frontend_message()
        except Exception as e:
            log.error(f"Broker encountered an error: {e}")
        finally:
            self._cleanup()

    def _handle_frontend_message(self):

        try:
            client_id, empty, request_msg = self.frontend.recv_multipart()
            log.info(f"Request <= {client_id}, {request_msg}")
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
                service_id = self.service_mapping.get_service_id(script_name)
                if service_id is None:
                    log.warning(f"No service found for name: {script_name}")
                    response = JSONRPCResponse(request.get_id())
                    response.set_error(MethodNotFound(f"No service found for name: {script_name}"))
                    self.frontend.send_multipart([client_id, b"", response.to_json().encode('utf-8')])
                    return
                request.set_method(method)
                # 转发请求到指定的服务端
                self.backend.send_multipart([service_id, b"", client_id, b"", request.to_json().encode('utf-8')])
                log.info(f"Response => {service_id}, {client_id}, {request_msg}")
            else:
                has_method = False
                # 转发请求到多个服务端
                for service_id in self.service_mapping.get_services().keys():
                    methods = self.service_mapping.get_service_methods(service_id)
                    if bind_name in methods:
                        has_method = True
                        self.backend.send_multipart([service_id, b"", client_id, b"", request_msg])
                        log.info(f"Response => {service_id}, {client_id}, {request_msg}")
                if not has_method:
                    log.warning(f"No method found for name: {bind_name}")
                    response = JSONRPCResponse(request.get_id())
                    response.set_error(MethodNotFound())
                    self.frontend.send_multipart([client_id, b"", response.to_json().encode('utf-8')])
        except Exception as e:
            log.error(f"Error handling frontend message: {e}")

    def _handle_backend_message(self):
        try:
            parts = self.backend.recv_multipart()
            log.info(f"Request <= {parts}")
            if len(parts) == 3:  # 注册消息
                service_id, empty, service_msg = parts
                register_info = json.loads(service_msg.decode('utf-8'))
                request = JSONRPCRequest.parse(register_info)
                method = request.get_method()
                params = request.get_params()
                response = JSONRPCResponse(request.get_id())

                if method == "register_service":  # 注册服务
                    self.service_mapping.register_service(*params, service_id)
                    response.set_result(True)
                elif method == "register_method":  # 注册方法
                    register_method_flag = self.service_mapping.register_method(*params)
                    if register_method_flag:
                        response.set_result(True)
                    else:
                        response.set_error(MethodNotFound(f"Service '{params}' not found. Cannot register method."))
                elif method == "unregister_service":  # 销毁服务
                    self.service_mapping.unregister_service(*params)
                    response.set_result(True)
                else:
                    response.set_error(MethodNotFound(f"method: {method} not found"))
                self.backend.send_multipart([service_id, b"", response.to_json().encode('utf-8')])
                log.info(f"Response => {service_id}, {response.to_json()}")
            elif len(parts) == 4:  # 响应消息
                service_id, client_id, empty, response_msg = parts
                self.frontend.send_multipart([client_id, b"", response_msg])
                log.info(f"Response => {client_id}, {response_msg}")
            else:
                log.error("Invalid message received")
        except Exception as e:
            log.error(f"Error handling backend message: {e}")

    def _cleanup(self):
        self.frontend.close()
        self.backend.close()
        self.context.term()


if __name__ == "__main__":
    frontend_addr = "ipc:///tmp/cpp2broker.ipc"  # 客户端连接地址
    backend_addr = "ipc:///tmp/broker2server.ipc"  # 服务端连接地址
    broker = Broker(frontend_addr, backend_addr)
    broker.start()
