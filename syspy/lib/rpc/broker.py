import zmq
import json
from syspy.lib.logger import log


def send_error_response(socket, recipient_id, error_message):
    response = json.dumps({"code": -1, "error": error_message}).encode('utf-8')
    socket.send_multipart([recipient_id, b"", response])


class Broker:
    def __init__(self, frontend_addr, backend_addr):
        self.context = zmq.Context()
        self.frontend = None
        self.frontend_addr = frontend_addr
        self.backend = None
        self.backend_addr = backend_addr
        self.service_mapping = {}
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
            request = json.loads(request_msg.decode('utf-8'))
            name = request.get("name")

            if name is None:
                log.warning("Request message does not contain 'name' field")
                send_error_response(self.frontend, client_id, "Request message does not contain 'name' field")
                return

            service_id = self.service_mapping.get(name)
            if service_id is None:
                log.warning(f"No service found for name: {name}")
                send_error_response(self.frontend, client_id, f"No service found for name: {name}")
                return

            # 转发请求到指定的服务端
            self.backend.send_multipart([service_id, b"", client_id, b"", request_msg])
            log.info(f"Response => {service_id}, {client_id}, {request_msg}")
        except Exception as e:
            log.error(f"Error handling frontend message: {e}")

    def _handle_backend_message(self):
        try:
            parts = self.backend.recv_multipart()
            log.info(f"Request <= {parts}")
            if len(parts) == 3:  # 注册消息
                service_id, empty, service_msg = parts
                register_info = json.loads(service_msg.decode('utf-8'))
                name = register_info.get("name")

                if name is None:
                    log.warning("Register message does not contain 'name' field")
                    send_error_response(self.backend, service_id, "Register message does not contain 'name' field")
                    return

                if name in self.service_mapping:
                    log.warning(f"Service with name '{name}' already registered. Overwriting old service.")

                # 存储服务端地址映射
                self.service_mapping[name] = service_id
                response_msg = json.dumps({"code": 0, "message": "Registered successfully"}).encode('utf-8')
                self.backend.send_multipart([service_id, b"", response_msg])
                log.info(f"Response => {service_id}, {response_msg}")
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
