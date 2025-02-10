import threading

import zmq
import json

from syspy.lib.logger import log

server_addr = "ipc:///tmp/broker2server.ipc"  # 代理的后端地址
funs = {}
script_name = ""

def start_server(name):
    context = zmq.Context()
    socket = context.socket(zmq.DEALER)  # 使用 DEALER 套接字
    socket.connect(server_addr)
    log.info(f"Server connected to {server_addr}")

    # 发送注册信息到代理
    register_msg = {"name": name}
    log.info(f"Sending registration message: {register_msg}")
    socket.send_multipart([b"", json.dumps(register_msg).encode('utf-8')])

    # 接收注册响应
    response_parts = socket.recv_multipart()
    log.info(f"Received registration response: {response_parts}")
    if len(response_parts) != 2:
        log.info("Invalid registration response format")
        return
    empty, register_response_str = response_parts
    register_response = json.loads(register_response_str.decode('utf-8'))

    if register_response["code"] != 0:
        log.info(f"Registration failed: {register_response['error']}")
        return

    log.info(f"Registered successfully for {name}")

    zmq_server_thread = threading.Thread(target=handle_request, args=(socket,),name="zmq_server_thread", daemon=True)
    zmq_server_thread.start()


def handle_request(socket):
    while True:
        try:
            # 接收请求
            message_parts = socket.recv_multipart()
            for message_part in message_parts:
                log.info(f"Received message part: {message_part}")
            if len(message_parts) != 4:
                log.info("Invalid request format")
                continue
            empty, client_id, empty, request_str = message_parts
            request = json.loads(request_str.decode('utf-8'))

            # 处理请求
            method_name = request.get("method")
            res = {}

            if method_name in ["suspend", "resume", "cancel"]:
                for func_name, func in funs.items():
                    # 如果func_name以method_name结尾，则调用
                    if func_name.endswith(method_name):
                        res = func()
            elif ("name" in request and request["name"] == script_name):
                if request["name"] == "":
                    register_name = method_name
                else:
                    register_name = request['name'] + '.' + method_name
                if register_name in funs:
                    func = funs[register_name]
                    args = request['args']
                    if args is None:
                        res = func()
                    else:
                        res = func(args)
                else:
                    res = -1
            else:
                res = -1
            response = {"res": res, "code": 0}
            # 模拟处理逻辑
            log.info(f"response => {response}")

            # 发送响应
            socket.send_multipart([client_id, b"", json.dumps(response).encode('utf-8')])
        except Exception as e:
            log.info(f"Error handling request: {e}")

class rpcServer:
    def __init__(self, name = ""):
        global script_name
        script_name = name
        start_server(name)

    def registerFunction(self, function, method_name=""):
        # 获取当前文件名
        """注册python方法，以便RBK调用
        Args:
            function (): 方法
            method_name (str): 方法名
        """
        global funs
        # 参数name 为空，则取函数名
        if method_name == "":
            method_name = function.__name__
        # 如果 script_name_name 为空，则取函数名
        if script_name == "":
            register_name = method_name
        else:  # 否则，取脚本名.函数名
            register_name = script_name + '.' + method_name
        funs[register_name] = function
        log.info(f"registerFunction: {funs}")