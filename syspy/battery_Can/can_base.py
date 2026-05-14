import json
import logging
import os
import platform
import subprocess
import sys
import threading
import time
from typing import Union

from google.protobuf.json_format import MessageToDict

import syspy.lib.rpc.server as rs
import syspy.v3.lib.rpc.client as rc
from syspy import  RBK_VERSION
from syspy import Battery, Di, Do
from syspy import Trace
if RBK_VERSION == 3:
    from syspy.v3.protobuf.message.message_battery_pb2 import msgBattery
if RBK_VERSION == 4:
    from syspy.v4.protobuf.message.messageV4_battery_pb2 import MessageV4_Battery  as msgBattery
    from syspy.v4.lib.rbk import core, service

log = logging.getLogger("rbk.script")


class CanBase:
    def __init__(self):
        Trace.log("CanBase __init__")
        self.__rpc_server = rs.RpcServer("battery")
        self.__rpc_server.registerFunction(self.setChargeStateOn)
        self.__rpc_server.registerFunction(self.setChargeStateOff)
        self.__rpc_server.start()
        self.__rpc_client = rc.RpcClient()

        command = "cat /etc/srcname"
        output = subprocess.check_output(command, shell=True)
        output = output.decode("utf-8").strip()
        Trace.log(f"{output=}")

        # 只有 SRC2000 控制器是 CAN 透传形式
        if "SRC2000" in output: #passthrough
            Trace.log("Can Type: passThrough")
            import syspy.battery_Can.can_pass as can_pass
            self.child = can_pass.CanPass()
        else:
            Trace.log("Can Type: native")
            import syspy.battery_Can.can_native as can_native
            self.child = can_native.CanNative()

        if RBK_VERSION == 4:
            name="pyBatteryServer"
            core.Init(name)
            service.addService(name, "serviceDispatcher", self.serviceDispatcher, dispatcher=True)

        self.setCallBack()
        self.need_charge = False
        self.msg_str = "{}"
        self._last_battery_msg = self.createBatteryMessage()
        self._status_lock = threading.Lock()
        self._rpc_lock = threading.Lock()
        self._stop_heartbeat = threading.Event()
        self._set_status_init()
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, name="batteryCanHeartbeat", daemon=True)
        self._heartbeat_thread.start()


    def serviceDispatcher(self,route_json: str):
        request = json.loads(route_json)
        print(f"request={request}")
        response = dict()
        func_name = request["func_name"]
        if func_name == "getBatteryMsg":
            response["result"] = self.get_battery_msg()
            return json.dumps(response), ""
        else:
            response["result"] = "Invalid function name"
            return json.dumps(response), ""


    def get_battery_msg(self) -> dict:
        return json.loads(self.msg_str)


    def setCallBack(self):
        self.child.setCallBack(self.handleData)

    def createBatteryMessage(self):
        battery_msg = msgBattery()
        if RBK_VERSION == 3:
            battery_msg.userData = bytes("0000000000000000", encoding='utf-8')
        else:
            battery_msg.user_data = bytes("0000000000000000", encoding='utf-8')
        return battery_msg

    def _set_status_init(self):
        self._battery_status_category = "INIT"
        self._battery_error_code = 0
        self._battery_error_desc = ""

    def _set_status_running(self):
        self._battery_status_category = "RUNNING"
        self._battery_error_code = 0
        self._battery_error_desc = ""

    def _set_status_connect_error(self):
        self._battery_status_category = "CONNECT_ERROR"
        self._battery_error_code = 57040
        self._battery_error_desc = "Battery response time out"

    def _set_status_device_error(self, error_code: int = 0, error_desc: str = ""):
        self._battery_status_category = "DEVICE_ERROR"
        self._battery_error_code = int(error_code) if error_code is not None else 0
        self._battery_error_desc = str(error_desc) if error_desc is not None else ""

    def _promote_status_for_data_publish(self):
        if self._battery_status_category in ("INIT", "CONNECT_ERROR"):
            self._set_status_running()

    def _build_status_payload(self):
        status_payload = {"statusCategory": self._battery_status_category}
        if self._battery_status_category in ("CONNECT_ERROR", "DEVICE_ERROR") and self._battery_error_code != 0:
            status_payload["errors"] = {
                f"ds@{self._battery_error_code}": {
                    "deviceError": {
                        "deviceType": "battery",
                        "deviceKey": "Battery-000",
                        "param": "",
                        "errorCode": self._battery_error_code
                    },
                    "desc": self._battery_error_desc,
                    "manual": True
                }
            }
        return status_payload

    def _build_battery_payload(self, battery_msg: msgBattery):
        payload = MessageToDict(battery_msg)
        if RBK_VERSION == 3:
            payload["status"] = self._build_status_payload()
        return payload

    def _publish_raw(self, battery_msg: msgBattery) -> int:
        payload = self._build_battery_payload(battery_msg)
        self.msg_str = json.dumps(payload)
        with self._rpc_lock:
            return self.__rpc_client.call_service("DSPChassis", "publishBattery", self.msg_str)

    def _publish_cached(self):
        with self._status_lock:
            battery_msg = self.createBatteryMessage()
            battery_msg.CopyFrom(self._last_battery_msg)
        self._publish_raw(battery_msg)

    def _heartbeat_loop(self):
        while not self._stop_heartbeat.is_set():
            try:
                self._publish_cached()
            except Exception:
                pass
            time.sleep(1.0)

    def createCanBus(self, channel, bitrate):
        self.child.createCanBus(channel, bitrate)

    def recCanframe(self, msg):
        return self.child.recCanframe(msg)

    def attachCanID(self, *args, extended=None, remote=None):
        if isinstance(args[0], int) and args[0] < 3:
            channel = args[0]
            id_nums = args[1]
            can_ids = [arg for arg in args[2:]]
            if extended or remote:
                ext_list = extended or [False] * len(can_ids)
                rtr_list = remote or [False] * len(can_ids)
                for i in range(min(len(can_ids), len(ext_list), len(rtr_list))):
                    if ext_list[i]:
                        can_ids[i] |= 0x80000000
                    if rtr_list[i]:
                        can_ids[i] |= 0x40000000
            self.child.attachCanID(channel, id_nums, *can_ids)
        else:
            can_ids = [arg for arg in args]
            if extended or remote:
                ext_list = extended or [False] * len(can_ids)
                rtr_list = remote or [False] * len(can_ids)
                for i in range(min(len(can_ids), len(ext_list), len(rtr_list))):
                    if ext_list[i]:
                        can_ids[i] |= 0x80000000
                    if rtr_list[i]:
                        can_ids[i] |= 0x40000000
            self.child.attachCanID(*can_ids)

    def sendCanframe(self, channel: int, can_id: int, dlc: int, extend: bool, can_string: Union[list, str]):
        """发送CAN消息

        Args:
            channel (int): CAN通讯通道。1或2
            can_id (int): 帧ID（仲裁ID）
            dlc (int): 数据长度码（Data Length Code）(最大为8)
            extend (bool): 是否为扩展帧ID
            can_string (Union[list, str]): 数据内容。例如:
                arm: [0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
                x86: "01 00 00 00 00 00 00 00"
        """
        self.child.sendCanframe(channel, can_id, dlc, extend, can_string)

    def getBatteryCanPort(self):
        with open('/etc/srcname', 'r') as file:
            srcname = file.readline().strip()

        if 'SRC880' in srcname:
            ports = ('can1', 'can0', 'can2')
        elif 'SRC2000' in srcname:
            ports = (1, 2, 3)
        else:
            ports = ('can0', 'can1', 'can2')
        Trace.log(f"{srcname=}, {ports=}")

        port = Battery.getCanPort()
        port = int(port.replace("port","")) # "port1" ---> 1 "port2"---> 2
        Trace.log(f"{port=}")
        if port in (1, 2, 3):
            selected_port = ports[port - 1]  # 根据端口号获取对应的端口
            Trace.log(f"{selected_port=}")
        else:
            Trace.log(f"Invalid port number: {port}")
            raise ValueError(f"Invalid port number: {port}")

        script_name = os.path.basename(sys.argv[0])
        new_entry = {
            "script_name": script_name,
            "selected_port": selected_port
        }
        current_dir = os.path.dirname(os.path.realpath(__file__))
        output_file = os.path.join(current_dir, 'port_config.json')

        data = []
        data.append(new_entry)
        with open(output_file, 'w') as json_file:
            json.dump(data, json_file, indent=4)

        return selected_port

    def publish(self, battery_msg: msgBattery) -> int:
        self._promote_status_for_data_publish()
        with self._status_lock:
            self._last_battery_msg.CopyFrom(battery_msg)
        return self._publish_raw(battery_msg)

    def getDIStates(self, index):
        return Di.get_di(index)

    def getDOStates(self, index):
        return Do.get_do(index)

    def setTimeout(self):
        self._set_status_connect_error()
        self._publish_cached()

    def clearTimeout(self):
        self._set_status_running()

    def setError(self, errNum, errMessage, reason='battery', method='check out', filename='btCanPass_xx.py'):
        self._set_status_device_error(errNum, errMessage)
        self._publish_cached()

    def isTimeout(self):
        return self._battery_status_category == "CONNECT_ERROR"

    def clearError(self, code):
        self._set_status_running()

    def setChargeStateOn(self):
        self.need_charge = True

    def setChargeStateOff(self):
        self.need_charge = False

    def isNeedCharge(self):
        return self.need_charge
    def resetBus(self):
        self.child.resetBus()
    def close(self):
        self._stop_heartbeat.set()
        self.__rpc_client.close()
        self.child.close()


if __name__ == "__main__":
    pass
