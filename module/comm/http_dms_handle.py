# -*- coding: utf-8 -*-
# @Date : 2022/11/21
# @Author : zhong
# @File :http_dms_handle.py
# @Version : 2.8
# @Project : 轩田料箱车项目，光通信处理主程序
# @Update1 : 解决网络通信断连问题
import time
import requests
from http_dms_server import Log, ParamServer
from requests.exceptions import ReadTimeout, ConnectTimeout, ConnectionError


class URL:
    def __init__(self):
        p = ParamServer(__file__)
        dms1 = p.loadParam("dms1", param_type="str", default="http://192.167.64.25:8088/", comment="库内DMS-1")
        dms2 = p.loadParam("dms2", param_type="str", default="http://192.167.64.29:8088/", comment="库内DMS-2")
        dms3 = p.loadParam("dms3", param_type="str", default="http://192.167.64.26:8088/", comment="库外DMS-1")
        dms4 = p.loadParam("dms4", param_type="str", default="http://192.167.64.27:8088/", comment="库外DMS-2")
        dms5 = p.loadParam("dms5", param_type="str", default="http://192.167.64.28:8088/", comment="库外DMS-3")
        dms6 = p.loadParam("dms6", param_type="str", default="http://192.167.64.31:8088/", comment="库外DMS-4")
        dms7 = p.loadParam("dms7", param_type="str", default="http://192.167.64.32:8088/", comment="库外DMS-5")
        dms8 = p.loadParam("dms8", param_type="str", default="http://192.167.64.33:8088/", comment="库外DMS-6")
        agv_core1 = p.loadParam("agv-core-1", param_type="str", default="http://10.10.10.72:8088/",
                                comment="库内 AGV WiFi模式  IP ")
        agv_core2 = p.loadParam("agv-core-2", param_type="str", default="http://10.10.10.70:8088/",
                                comment="库外 AGV-1 WiFi模式 IP")
        agv_core3 = p.loadParam("agv-core-3", param_type="str", default="http://10.10.10.71:8088/",
                                comment="库外 AGV-2 WiFi模式 IP")
        self.server_core = p.loadParam("server-core", param_type="str", default="http://10.10.10.200:8088/",
                                       comment="WiFi模式服务器 Core IP")
        self.dms_server = p.loadParam("dms-server", param_type="str", default="http://192.169.202.4:8885/",
                                      comment="订单缓存服务器")
        self.task_call_back = p.loadParam("call-back-server", param_type="str",
                                          default="http://192.169.202.2:80/api/AVG/TaskCallBack",
                                          comment="订单回调服务器")
        self.door_server = p.loadParam("door-server", param_type="str",
                                       default="http://192.167.1.161:7070/api/Wms/GetCTUDoorStatus",
                                       comment="库内门控服务器")
        self.door_service = p.loadParam("door-service", param_type="int", default=1,
                                        comment="是否启用门控服务:  0代表关闭, 1代表开启")
        self.internal_dms = [dms1, dms2]  # 库内DMS
        self.external_dms = [dms3, dms4, dms5, dms6, dms7, dms8]  # 库外DMS
        self.internal_wifi = [agv_core1]  # wifi 模式库内Core
        self.external_wifi = [agv_core2, agv_core3]  # wifi 模式库外Core


class HttpHandle:
    """
    提供HTTP协议的GET请求和POST请求接口
    """

    def __init__(self):
        # user_agent_list = [
        #     "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36",
        #     "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36",
        #     "Mozilla/5.0 (Windows NT 10.0; WOW64) Gecko/20100101 Firefox/61.0",
        #     "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36",
        #     "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.62 Safari/537.36",
        #     "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.101 Safari/537.36",
        #     "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0)",
        #     "Mozilla/5.0 (Macintosh; U; PPC Mac OS X 10.5; en-US; rv:1.9.2.15) Gecko/20110303 Firefox/3.6.15",
        # ]
        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
            # 'User-Agent': random.choice(user_agent_list)
        }
        pass

    def http_get(self, url, headers=None, timeout=(5.0, 10.0)):
        if headers is None:
            headers = self.headers
        try:
            res = requests.get(url, headers=headers, timeout=timeout)
        except ConnectTimeout:
            log.logger.warning(f'ConnectTimeout, func: http_get: {url}')
        except ConnectionError as e:
            log.logger.warning(f"ConnectionError {e}:{url}")
        except ReadTimeout:
            log.logger.warning(f'ReadTimeout, func: http_get: {url}')
        except Exception as e:
            log.logger.warning(f"Exception: {e}")
        else:
            log.logger.info(f"conn success: {url}, status_code: {res.status_code}, res text: {res.text}")
            res.close()
            return res
        finally:
            time.sleep(0.5)
            pass

    def http_post(self, url, data=None, headers=None, timeout=(5.0, 10.0)):
        """
        发送一次POST请求， 请求成功返回 response 的 json 数据
        :param headers:
        :param url:
        :param data: 
        :param timeout: 
        :return: json 
        """
        if headers is None:
            headers = self.headers
        try:
            res = requests.post(url, json=data, headers=headers, timeout=timeout)
        except ConnectTimeout:
            log.logger.warning(f'ConnectTimeout: func: http_post: {url}')
        except ReadTimeout:
            log.logger.warning(f'ReadTimeout, func: http_post: {url}')
        except ConnectionError as e:
            log.logger.warning(f"ConnectionError {e}: {url}")
        except Exception as e:
            log.logger.warning(f"Exception: {e}")
        else:
            log.logger.info(f"conn success: {url}, status_code: {res.status_code}, res text: {res.text}")
            res.close()
            return res
        finally:
            time.sleep(0.5)


class OrdersHandle:
    def __init__(self):
        self.http_handle = HttpHandle()
        self.failed_orders = dict()  # 记录因不在当前 RDSCore 场景中而发送失败的订单
        self.cur_inside_handle_order = list()  # 记录库内正在处理中的订单
        self.cur_outside_handle_order = list()  # 记录库外正在处理中的订单
        self.sent_order = list()  # 单次连接成功后，成功发送的订单列表
        self.sent_order_num = 0  # 连接成功后，成功发送的订单计数
        self.url = URL()
        self.token_str = "Bearer eyJhbGciOiJIUzUxMiIsImlhdCI6MTY0NzI0NDQ1MSwiZXhwIjoyMzM4NDQ0NDUxfQ.eyJOYW1lIjoiYWRtaW4ifQ.65Tog8m-OCgaYqXL-ROUSZlWAwJlpN0LUwsoBZM1HhMuEOXOLoC9yfJTKpDJH7d7qoSCEubZQCKA8dmu0IafJQ"

    def handle_orders(self, core_url: str, order_data: list):
        """
        处理服务器缓存的订单
        :param core_url: 当前连接的Core
        :param order_data: 服务器当前缓存订单
        :return:
        """
        log.logger.info(f"{'=' * 20}order sending{'=' * 20}")
        for order in order_data[:]:  # 遍历缓存订单，处理和发送订单
            try:
                if self.bin_check(core_url, order):  # 判断该订单的库位是否位于 RDSCore 的地图场景中
                    set_order_res = self.http_handle.http_post(core_url + "setOrder", order)
                    if bool(set_order_res) and set_order_res.status_code == 200 and set_order_res.json().get("code",
                                                                                                             -1) == 0:  # 派发订单成功
                        if core_url in self.url.internal_dms or core_url in self.url.internal_wifi:
                            self.cur_inside_handle_order.append(order)
                        elif core_url in self.url.external_dms or core_url in self.url.external_wifi:
                            self.cur_outside_handle_order.append(order)
                        else:
                            log.logger.error(f"unknown core or dms - 1: {core_url}")
                        order_data.remove(order)
                        self.sent_order.append(order)
                        self.failed_orders.pop(order['id'], 0)
                        self.sent_order_num += 1
                        log.logger.info(
                            f"send orders success: {order.get('id', order)}, send order num: {self.sent_order_num}")
                    else:
                        log.logger.warning(f"send orders failed: {order}")
                else:
                    # 订单库位不在小车的地图场景中，则不发送该订单，并计算失败次数
                    self.fail_order_counter(order)
            except Exception as e:
                log.logger.error(f"handle_orders error: {order.get('id', order)}, {e}")
            else:
                # 单次连接，最多只成功发送4个订单
                if self.sent_order_num >= 4:
                    break

        # 订单数据更新
        self.update_order_data(order_data)

    def callback_order(self, core_url):
        """
        处理 DMS 订单回调
        :param core_url: 当前连接的Core
        :return:
        """
        log.logger.info(f"{'=' * 20} order callback{'=' * 20}")
        headers = {"Authorization": self.token_str}
        agv_task_info_list = list()
        if core_url in self.url.internal_dms or core_url in self.url.internal_wifi:
            cur_handle_order = self.cur_inside_handle_order
        elif core_url in self.url.external_dms or core_url in self.url.external_wifi:
            cur_handle_order = self.cur_outside_handle_order
        else:
            cur_handle_order = []
            log.logger.error(f"unknown core or dms - 2: {core_url}")
        log.logger.info(f"current inside orders: {len(self.cur_inside_handle_order)}-{self.cur_inside_handle_order}")
        log.logger.info(f"current outside orders: {len(self.cur_outside_handle_order)}-{self.cur_outside_handle_order}")
        if len(cur_handle_order) > 0:
            for order in cur_handle_order[:]:
                order_detail_res = self.http_handle.http_get(core_url + "orderDetails/" + f"{order['id']}",
                                                             timeout=(3.0, 10.0))                 # 查询订单信息
                if order_detail_res and order_detail_res.status_code == 200 \
                        and order_detail_res.json().get("id", None) == order['id']:
                    agv_task_info_list.extend(self.return_agv_task_info(order_detail_res.json(), order, core_url))             # 生成回调订单数据
                else:
                    log.logger.error(f"cannot get order details, order {order['id']} not in the core")

            # 回调订单数据不为空时，上报回调订单数据
            if len(agv_task_info_list) > 0:
                callback_data = {
                    "$id": "0",
                    "$type": "Nkd.Custom.BusinessOrchestration.AGVManagement.InputObjects.TaskCallBackInput, Nkd.Custom.BusinessOrchestration ",
                    "AGVTaskInfos": agv_task_info_list
                }
                self.http_handle.http_post(self.url.task_call_back, data=callback_data, headers=headers, timeout=20)
                log.logger.info(f"callback_order_list: {agv_task_info_list}")
        else:
            log.logger.info(f"There are no orders currently being processed")

    def return_agv_task_info(self, order_detail, order, core_url):
        """
        封装订单回调数据格式
        :param core_url:
        :param order_detail:
        :param order:
        :return:
        """
        order_id = order_detail.get('id', '')  # 拼合单id
        load_order_id = order_detail.get('loadOrderId', '')  # 拼合单 loadOrderId
        # state = order_detail.get('state', '')                                     # 拼合单状态
        load_state = order_detail.get('loadState', '')  # 拼合单取货状态
        unload_state = order_detail.get('unloadState', '')  # 拼合单放货状态
        vehicle = order_detail.get('vehicle', '')
        load_msg = order_detail.get('errMsg', '')
        unload_msg = order_detail.get('errMsg', '')

        # 订单进入终态，则清除订单
        if load_state in ["FINISHED", "FAILED", "STOPPED"] and unload_state in ["FINISHED", "FAILED", "STOPPED"]:
            if core_url in self.url.internal_dms or core_url in self.url.internal_wifi:
                self.cur_inside_handle_order.remove(order)
            elif core_url in self.url.external_dms or core_url in self.url.external_wifi:
                self.cur_outside_handle_order.remove(order)
            else:
                log.logger.error(f"unknown core or dms - 3: {core_url}")

        if load_state == "FINISHED":
            load_msg = ''
            load_state = "LOAD_FINISHED"
        elif load_state == "FAILED" or load_state == "STOPPED":
            load_state = "LOAD_FAILED"

        if unload_state == "FINISHED":
            unload_msg = ''
            unload_state = "UNLOAD_FINISHED"
        elif unload_state == "FAILED" or unload_state == "STOPPED":
            unload_state = "UNLOAD_FAILED"

        # 修复 RDSCore 的 orderDetails 接口返回数据没有 id 的 bug
        if load_order_id and not order_id:
            order_id = load_order_id.strip("_load")

        data = [
            {
                "$id": 1,
                "$type": "Nkd.Custom.BusinessObjects.AGVTaskInfo,Nkd.Custom.BusinessObjects",
                "taskId": order_id,
                "vehicle": vehicle,
                "message": load_msg,
                "status": load_state
            },
            {
                "$id": 1,
                "$type": "Nkd.Custom.BusinessObjects.AGVTaskInfo,Nkd.Custom.BusinessObjects",
                "taskId": order_id,
                "vehicle": vehicle,
                "message": unload_msg,
                "status": unload_state
            }
        ]
        return data

    def bin_check(self, core_url: str, order: dict) -> bool:
        """
        检查订单的起点和终点库位是否在场景中
        :param core_url:
        :param order:
        :return:
        """
        bins_tobe_checked = {"bins": [order.get('fromLoc', ''), order.get('toLoc', '')]}
        bin_check_res = self.http_handle.http_post(core_url + "binCheck", bins_tobe_checked, timeout=(5.0, 30.0))
        if bin_check_res and bin_check_res.status_code == 200:
            if "bins" not in bin_check_res.json():
                return False
            bins = bin_check_res.json().get('bins', list())
            for b in bins:
                if not b.get('exist', False):
                    return False
            return True
        else:  # 当 bin_check 接口异常时，手动库位检测
            if core_url in self.url.internal_dms and not str(order['fromLoc'][0]).isdigit() and not str(
                    order['toLoc'][0]).isdigit() or \
                    core_url in self.url.external_dms and (
                    str(order['fromLoc'][0]).isdigit() or str(order['toLoc'][0]).isdigit()):
                log.logger.info(f"bin_check by isdigit finished")
                return True
            return False

    def fail_order_counter(self, order):
        """
        计算发送订单失败次数
        :param order:
        :return:
        """
        self.failed_orders[order['id']] = self.failed_orders.get(order['id'], 0) + 1
        log.logger.error(f"The order '{order['id']}' bin check failed, order details: {order}")
        if self.failed_orders.get(order['id'], 0) >= 100:
            self.failed_orders.pop(order['id'], 0)

    def update_order_data(self, order_list):
        """
        更新 DMS 服务器订单数据
        :param order_list:
        :return:
        """
        update_order_res = self.http_handle.http_post(self.url.dms_server + "updateOrder", self.sent_order)
        if update_order_res and update_order_res.status_code == 200:
            log.logger.info(f"update server orders success, sent_order_num: {self.sent_order_num}")
            log.logger.info(f"failed orders: {len(self.failed_orders)}-{self.failed_orders}")
            log.logger.info(f"surplus orders: {len(order_list)}-{order_list}")
            self.sent_order_num = 0
            self.sent_order.clear()
        else:
            log.logger.error(f"update server orders failed, orders: {order_list}")


class DMS:
    def __init__(self):
        p = ParamServer(__file__)
        self.dms_interval_time = p.loadParam("dms_interval_time", param_type="float", default=20.0,
                                             comment="光通讯模式任务处理间隔时间")
        self.wifi_interval_time = p.loadParam("wifi_interval_time", param_type="float", default=10.0,
                                              comment="wifi模式任务处理间隔时间")
        self.http_handle = HttpHandle()
        self.order_handle = OrdersHandle()
        self.agv = {"vehicles": []}
        self.url = URL()
        self.dms_core_url = self.url.internal_dms + self.url.external_dms
        self.wifi_core_url = self.url.internal_wifi + self.url.external_wifi
        self.door_status = 0  # 1: 开门状态， 0: 关门状态

    def connect_core(self, core_url):
        """
        轮询 ping 所有 core_url，如果ping通，则返回该 core_url
        :return: core_url: str
        """
        for u in core_url:
            r = self.http_handle.http_get(u + "ping")
            if bool(r) and r.json().get("code", -1) == 0:
                core_url.append(core_url.pop(core_url.index(u)))
                log.logger.info(f"current core_url list: {core_url}")
                return u
        return None

    def get_door_status(self):
        if self.url.door_service == 1:  # 门控服务开启
            get_door_res = self.http_handle.http_get(self.url.door_server)  # 获取自动门信号
            if bool(get_door_res) and get_door_res.status_code == 200:
                self.door_status = int(get_door_res.json().get("Result", 0))
            # return self.door_status
        else:
            log.logger.info(f"door service not open : {self.url.door_service}")
        return self.door_status

    def dms_handle(self):
        """
        主程序，处理 DMS 连接业务
        :return: None
        """
        log.logger.info(f"{time.strftime('%Y-%m-%d %H:%M:%S')} DMS mode wait task ... ...")
        while True:
            try:
                conn_core = self.connect_core(self.dms_core_url)  # 轮询所有DMS, 返回当前连接的Core
                order_data = self.http_handle.http_post(self.url.dms_server + "getOrder")  # 获取服务器缓存订单
                self.door_status = self.get_door_status()  # 获取自动门信号
                if conn_core:
                    pause_agv_res = self.http_handle.http_post(conn_core + "gotoSitePause", self.agv)  # 暂停小车
                    if bool(pause_agv_res) and pause_agv_res.status_code == 200 and pause_agv_res.json().get("code",
                                                                                                             -1) == 0:
                        try:
                            if conn_core in self.url.internal_dms and self.door_status == 0 and order_data:  # AGV在库房内且库房门关闭，则处理订单
                                self.order_handle.handle_orders(conn_core, order_data.json())
                            elif conn_core in self.url.external_dms and order_data:  # 连接的AGV在库房外, 直接处理订单
                                self.order_handle.handle_orders(conn_core, order_data.json())
                            time.sleep(1.0)
                            self.order_handle.callback_order(conn_core)  # 处理订单回调
                        except Exception as e:
                            log.logger.error(f"dms handle error: {e}")
                        finally:
                            if conn_core in self.url.internal_dms and self.door_status == 0:
                                self.http_handle.http_post(conn_core + "gotoSiteResume", self.agv)  # 恢复小车行动
                            elif conn_core in self.url.external_dms:
                                self.http_handle.http_post(conn_core + "gotoSiteResume", self.agv)
                            log.logger.info(f"door status: {self.door_status}, current connect dms: {conn_core}")
                            log.logger.info(
                                f"inside mode: {m.internal_mode}, outside mode: {m.external_mode}")
                            log.logger.info('*' * 160)
                            time.sleep(self.dms_interval_time)
                            log.logger.info(f"{time.strftime('%Y-%m-%d %H:%M:%S')} wait next task ...")
                else:
                    log.logger.warning(f"No robot currently connected")
                    log.logger.info('*' * 160)
                    time.sleep(0.5)
            except Exception as e:
                log.logger.error(f"connect core error: {e}")

    def wifi_handle(self):
        """
        处理 wifi 模式业务
        :return:
        """
        log.logger.info(f"{time.strftime('%Y-%m-%d %H:%M:%S')} wifi mode wait task ... ...")
        while True:
            try:
                conn_core = self.connect_core(self.wifi_core_url)
                order_data = self.http_handle.http_post(self.url.dms_server + "getOrder")  # 获取服务器缓存订单
                self.door_status = self.get_door_status()
                if conn_core:
                    if conn_core in self.url.internal_wifi and self.door_status == 0 and order_data:
                        self.order_handle.handle_orders(conn_core, order_data.json())
                    elif conn_core in self.url.external_wifi and order_data:
                        self.order_handle.handle_orders(conn_core, order_data.json())
                    time.sleep(1.0)
                    self.order_handle.callback_order(conn_core)
                else:
                    log.logger.warning(f"connect core failed with wifi")
                log.logger.info(
                    f"inside mode: {m.internal_mode}, outside mode: {m.external_mode}")
                log.logger.info('*' * 160)
                time.sleep(self.wifi_interval_time)
                log.logger.info(f"{time.strftime('%Y-%m-%d %H:%M:%S')} wait next task ...")
            except Exception as e:
                log.logger.info(f"wife mode error: {e}")

    def mix_mode_handle(self, mode: tuple):
        log.logger.info(f"{time.strftime('%Y-%m-%d %H:%M:%S')} mix mode wait task ... ...")
        if mode == (0, 1):
            self.dms_core_url = self.url.internal_dms
            self.wifi_core_url = self.url.external_wifi
        elif mode == (1, 0):
            self.dms_core_url = self.url.external_dms
            self.wifi_core_url = self.url.internal_wifi
        while True:
            order_data = self.http_handle.http_post(self.url.dms_server + "getOrder")  # 获取服务器缓存订单
            self.door_status = self.get_door_status()
            conn_dms_core = self.connect_core(self.dms_core_url)
            conn_wifi_core = self.connect_core(self.wifi_core_url)
            # 处理 DMS Core 业务
            if conn_dms_core is not None:
                log.logger.info(f"{'$' * 30}mix mode dms handle{'$' * 30}")
                pause_agv_res = self.http_handle.http_post(conn_dms_core + "gotoSitePause", self.agv)  # 暂停小车
                if bool(pause_agv_res) and pause_agv_res.status_code == 200 and pause_agv_res.json().get("code",
                                                                                                         -1) == 0:
                    try:
                        if mode[0] == 0 and bool(order_data) and self.door_status == 0:  # 库内 DMS
                            self.order_handle.handle_orders(conn_dms_core, order_data.json())
                        elif mode[1] == 0 and order_data:  # 库外 DMS
                            self.order_handle.handle_orders(conn_dms_core, order_data.json())
                        # 处理订单回调
                        self.order_handle.callback_order(conn_dms_core)
                    except Exception as e:
                        log.logger.error(f"mix_mode_handle dms error: {e}")
                    finally:
                        if mode[0] == 0 and self.door_status == 0:  # 库内 DMS
                            self.http_handle.http_post(conn_dms_core + "gotoSiteResume", self.agv)
                        if mode[1] == 0:
                            self.http_handle.http_post(conn_dms_core + "gotoSiteResume", self.agv)
                        time.sleep(1.0)
            else:
                log.logger.warning(f"connect dms core failed with mix mode ")

            # 处理 WiFi Core 业务
            if conn_wifi_core is not None:
                log.logger.info(f"{'$' * 30}mix mode wifi handle{'$' * 30}")
                if order_data:
                    self.order_handle.handle_orders(conn_wifi_core, order_data.json())
                time.sleep(1.0)
                self.order_handle.callback_order(conn_wifi_core)
            else:
                log.logger.warning(f"connect wifi core failed with mix mode ")
            log.logger.info(f"inside mode: {m.internal_mode}, outside mode: {m.external_mode}")
            log.logger.info('*' * 160)
            time.sleep(self.wifi_interval_time + 5.0)
            log.logger.info(f"{time.strftime('%Y-%m-%d %H:%M:%S')} wait next task ...")


class MainProcess:
    def __init__(self):
        p = ParamServer(__file__)
        self.internal_mode = p.loadParam("internal_mode", param_type="int", default=0,
                                         comment="库内通信模式:  0代表DMS, 1代表WiFi")
        self.external_mode = p.loadParam("external_mode", param_type="int", default=0,
                                         comment="库外通信模式:  0代表DMS, 1代表WiFi")
        self.dms = DMS()
        log.logger.info(f"inside mode: {self.internal_mode}, outside mode: {self.external_mode}")

    def main(self):
        if self.internal_mode == 0 and self.external_mode == 0:
            self.dms.dms_handle()
        elif self.internal_mode == 0 and self.external_mode == 1:
            self.dms.mix_mode_handle((0, 1))
        elif self.internal_mode == 1 and self.external_mode == 0:
            self.dms.mix_mode_handle((1, 0))
        elif self.internal_mode == 1 and self.external_mode == 1:
            self.dms.wifi_handle()


if __name__ == '__main__':
    # log = Log('dms-handle', when='M', interval=30, backupCount=10)
    log = Log('dms-handle')
    m = MainProcess()
    m.main()
