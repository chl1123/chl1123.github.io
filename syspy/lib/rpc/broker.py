import zmq
import json
from syspy.lib.logger import log

def start_broker(frontend_addr, backend_addr):
    context = zmq.Context()

    # 创建 ROUTER 套接字监听客户端请求
    frontend = context.socket(zmq.ROUTER)
    frontend.bind(frontend_addr)

    # 创建 DEALER 套接字连接到服务端
    backend = context.socket(zmq.ROUTER)
    backend.bind(backend_addr)

    log.info(f"Broker started: frontend={frontend_addr}, backend={backend_addr}")

    service_mapping = {}  # 存储服务端地址映射

    poller = zmq.Poller()
    poller.register(frontend, zmq.POLLIN)
    poller.register(backend, zmq.POLLIN)

    while True:
        socks = dict(poller.poll())

        if backend in socks and socks[backend] == zmq.POLLIN:
            # 处理来自服务端的消息
            parts = backend.recv_multipart()
            log.info(f"Request <= {parts}")
            if len(parts) == 3:  # 注册消息
                service_id, empty, service_msg = parts
                register_info = json.loads(service_msg.decode('utf-8'))
                name = register_info.get("name")

                if name is None:
                    log.info("Register message does not contain 'name' field")
                    backend.send_multipart([service_id, b"", json.dumps(
                        {"code": -1, "error": "Register message does not contain 'name' field"}).encode('utf-8')])
                    continue

                # 存储服务端地址映射
                service_mapping[name] = service_id
                response_msg = json.dumps({"code": 0, "message": "Registered successfully"}).encode('utf-8')
                backend.send_multipart([service_id, b"", response_msg])
                log.info(f"Response => {service_id}, {response_msg}")
            elif len(parts) == 4:  # 响应消息
                service_id, client_id, empty, response_msg = parts
                frontend.send_multipart([client_id, b"", response_msg])
                log.info(f"Response => {client_id}, {response_msg}")
            else:
                log.info("Invalid message received")
        if frontend in socks and socks[frontend] == zmq.POLLIN:
            # 处理来自客户端的消息
            client_id, empty, request_msg = frontend.recv_multipart()
            log.info(f"Request <= {client_id}, {request_msg}")
            request = json.loads(request_msg.decode('utf-8'))
            name = request.get("name")

            if name is None:
                log.info("Request message does not contain 'name' field")
                frontend.send_multipart([client_id, b"", json.dumps(
                    {"code": -1, "error": "Request message does not contain 'name' field"}).encode('utf-8')])
                continue

            service_id = service_mapping.get(name)
            if service_id is None:
                log.info(f"No service found for name: {name}")
                frontend.send_multipart([client_id, b"", json.dumps(
                    {"code": -1, "error": f"No service found for name: {name}"}).encode('utf-8')])
                continue

            # 转发请求到指定的服务端
            backend.send_multipart([service_id, b"", client_id, b"", request_msg])
            log.info(f"Response => {service_id}, {client_id}, {request_msg}")

if __name__ == "__main__":
    frontend_addr = "ipc:///tmp/cpp2broker.ipc"  # 客户端连接地址
    backend_addr = "ipc:///tmp/broker2server.ipc"  # 服务端连接地址
    start_broker(frontend_addr, backend_addr)