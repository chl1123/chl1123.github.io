# -*- coding: utf-8 -*-
# @Date : 2022/9/27
# @Author : zhong
# @File :http_dms_server.py
# @Version : 2.6
# @Project : 轩田料箱车项目，订单处理服务程序

import http
import json
import logging
import os
import socket
import time
from enum import IntEnum
from http.server import HTTPServer, BaseHTTPRequestHandler
from logging.handlers import TimedRotatingFileHandler
from socketserver import ThreadingMixIn


class ServerConstant:
    host = socket.gethostname()
    ip = socket.gethostbyname(host)
    port = 8885


class Order:
    inside_orders = []        # 库内订单
    outside_orders = []    # 库外订单
    pass


class Request(BaseHTTPRequestHandler):
    server_version = "Apache"

    def do_GET(self):
        try:
            log.logger.info(f'url: {self.path.split("?")}')
            log.logger.info(f'path: {self.path.split("?")[0]}')
            if len(self.path.split("?")) > 1:
                log.logger.info(f'params: {self.path.split("?")[1]}')
            log.logger.info(f"server:  {self.server.server_address}")
            log.logger.info(f'client:  {self.client_address}')
            log.logger.info(f'request: {self.request}')
            log.logger.info('*' * 100)
        except Exception as e:
            log.logger.warning(e)
        if self.path == "/getInfo":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            res_data = {"order": Order.inside_orders}
            self.wfile.write(json.dumps(res_data).encode('utf-8'))
        else:
            self.send_response(404)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            res_data = {"msg": "unknown path"}
            self.wfile.write(json.dumps(res_data).encode('utf-8'))
            pass

    def do_POST(self):
        # 获取post提交的数据
        data = self.rfile.read(int(self.headers['content-length']))
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        log.logger.info(f"path: {self.path}")
        log.logger.info(f'client:  {self.client_address}')
        log.logger.info(f"server recv data: {data.decode('utf-8')}")
        if self.path == "/setOrder":                     # 接收 WMS 发送的订单
            if bool(data):
                Order.inside_orders.append(json.loads(data.decode('utf-8')))
            res = {"status": http.HTTPStatus.OK, "type": "HTTP POST"}
            self.wfile.write(json.dumps(res).encode('utf-8'))
            log.logger.info(f"server current orders: {Order.inside_orders}")
            log.logger.info(f"server current orders num: {len(Order.inside_orders)}")
            log.logger.info('*'*160)
        elif self.path == "/getOrder":
            log.logger.info(f"get orders: {len(Order.inside_orders)}-{Order.inside_orders}")
            self.wfile.write(json.dumps(Order.inside_orders).encode('utf-8'))
        elif self.path == "/clearOrder":
            Order.inside_orders.clear()
            log.logger.info(f"clear orders: {Order.inside_orders}")
            self.wfile.write(json.dumps(Order.inside_orders).encode('utf-8'))
        elif self.path == "/updateOrder":
            tmp = json.loads(data.decode('utf-8')) if bool(data) else []
            for i in tmp:
                if i in Order.inside_orders:
                    Order.inside_orders.remove(i)
                else:
                    log.logger.error(f"order not exist: {i}")
            log.logger.info(f"update current orders: {len(Order.inside_orders)}-{Order.inside_orders}")
            self.wfile.write(json.dumps(Order.inside_orders).encode('utf-8'))
        elif self.path == "/":
            self.wfile.write(json.dumps("Access to the server successfully").encode('utf-8'))
        elif self.path == "/openDoor":
            pass
        elif self.path == "/closeDoor":
            pass
        else:
            log.logger.error(f"unknown path")


class ThreadingHttpServer(ThreadingMixIn, HTTPServer):
    pass


class Log:
    """输出脚本日志"""
    def __init__(self, filename, level=logging.INFO, when='H', interval=3, backupCount=40):
        log_dir = os.getcwd() + "/scripts-logs/"
        os.makedirs(log_dir, exist_ok=True)
        log_format = logging.Formatter('%(asctime)s - %(module)s - %(levelname)s: %(message)s')
        stream_handle = logging.StreamHandler()
        file_handle = TimedRotatingFileHandler(filename=log_dir+filename, when=when, interval=interval, backupCount=backupCount, encoding='utf-8')
        file_handle.setFormatter(log_format)
        if when == 'S':
            file_handle.suffix = "%Y-%m-%d_%H-%M-%S.log"
        elif when == 'M':
            file_handle.suffix = "%Y-%m-%d_%H-%M.log"
        elif when == 'H':
            file_handle.suffix = "%Y-%m-%d_%H.log"
        elif when == 'D' or when == 'MIDNIGHT':
            file_handle.suffix = "%Y-%m-%d.log"
        self.logger = logging.getLogger(filename)
        self.logger.setLevel(level)
        self.logger.addHandler(stream_handle)
        self.logger.addHandler(file_handle)


class ParamServer:
    """
    参数服务:构建的参数以json的格式保存在params的文件夹下，参数文件名为脚本名称，后缀为json。
    目前支持的数据格式为str, float 和 int
    使用方式:
    p = ParamServer(__file__)
    param = p.loadParam("motor_name", "str", default = "motor1")
    """

    def __init__(self, file):
        param_dir = os.getcwd() + '/config'
        if not os.path.exists(param_dir):
            os.makedirs(param_dir)
        base_f = os.path.basename(file)
        self.file = param_dir + '/' + base_f.split('.')[0] + '.json'
        self.data = dict()
        try:
            with open(self.file, 'r', encoding="utf-8") as f:
                self.data = json.load(f)
        except Exception as e:
            print(f"error: {e}")

    def loadParam(self, name: str, param_type: str = "", default=None, **kw):
        def updateKey(data, key, value):
            if (key not in data) or (key in data and data[key] != value):
                return True
            else:
                return False

        updateFile = False
        if param_type is "float" or param_type is "str" or param_type is "int":
            if default is not None:
                if name not in self.data:
                    updateFile = True
                    self.data[name] = dict()
                if "value" not in self.data[name]:
                    updateFile = True
                    self.data[name]["value"] = eval(param_type)(default)
                if updateKey(self.data[name], "default", default):
                    updateFile = True
                    self.data[name]["default"] = default
                if param_type is "float" or param_type is "int":
                    if "maxValue" in kw and updateKey(self.data[name], "maxValue", kw["maxValue"]):
                        updateFile = True
                        self.data[name]["maxValue"] = kw["maxValue"]
                    if "minValue" in kw and updateKey(self.data[name], "minValue", kw["minValue"]):
                        updateFile = True
                        self.data[name]["minValue"] = kw["minValue"]
                if "comment" in kw and updateKey(self.data[name], "comment", kw["comment"]):
                    updateFile = True
                    self.data[name]["comment"] = kw["comment"]
                if "unit" in kw and updateKey(self.data[name], "unit", kw["unit"]):
                    updateFile = True
                    self.data[name]["unit"] = kw["unit"]
                if updateFile:
                    with open(self.file, 'w', encoding="utf-8") as f:
                        json.dump(self.data, f, indent=4, ensure_ascii=False)
                return self.data[name]["value"]
            else:
                raise Exception("loadParam no default key")
        else:
            raise Exception("loadParam Type (str, int, float) Error. Input Type is {}".format(param_type))


class RunningMode(IntEnum):
    DMS = 0
    WIFI = 1


if __name__ == '__main__':
    # server = HTTPServer((ServerConstant.ip, ServerConstant.port), Request)
    server = ThreadingHttpServer((ServerConstant.ip, ServerConstant.port), Request)
    log = Log("dms-server")
    log.logger.info(f"{time.strftime('%Y-%m-%d %H:%M:%S')} Starting server, listen at: {ServerConstant.ip}:{ServerConstant.port}")
    server.serve_forever()
