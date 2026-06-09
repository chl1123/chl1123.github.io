import json
import platform
import logging
import threading
import time
import syspy.v3.lib.rpc.client as rc
import syspy.lib.rpc.server as rs

from google.protobuf.json_format import MessageToDict
from syspy import Battery, Di, Do
from syspy import  RBK_VERSION
from syspy import Trace
import subprocess
if RBK_VERSION == 3:
    from syspy.v3.protobuf.message.message_battery_pb2 import msgBattery
if RBK_VERSION == 4:
    from syspy.v4.protobuf.message.messageV4_battery_pb2 import MessageV4_Battery  as msgBattery

DEFAULT_RPC_ADDR = "ipc:///tmp/python2dsp_rpc.ipc"
log = logging.getLogger("rbk.script")

class batteryBase:
    def __init__(self):
        command = "cat /etc/srcname"
        output = subprocess.check_output(command, shell=True)
        output = output.decode("utf-8").strip()
        Trace.log(f"{output=}")
        if "SRC2000" in output: #passthrough
            Trace.log("Serial Type: passThrough")
            import syspy.battery_Serial.serial_pass as serial_pass
            self.child = serial_pass.SerialPass()
        else:
            Trace.log("Serial Type: native")
            import syspy.battery_Serial.serial_native as serial_native
            self.child = serial_native.SerialNative()
        self.__rpc_client = rc.RpcClient()
        self.__rpc_server = rs.RpcServer("battery")
        self.__rpc_server.registerFunction(self.setChargeStateOn)
        self.__rpc_server.registerFunction(self.setChargeStateOff)
        self.__rpc_server.start()
        self.setCallBack()
        self.need_charge = False
        self._last_battery_msg = self.createBatteryMessage()
        self._status_lock = threading.Lock()
        self._rpc_lock = threading.Lock()
        self._stop_heartbeat = threading.Event()
        self._set_status_init()
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, name="batterySerialHeartbeat", daemon=True)
        self._heartbeat_thread.start()

    def setCallBack(self):
        self.child.setCallBack(self.handleData)

    def createBatteryMessage(self):
        return self.child.createBatteryMessage()

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

    def _publish_raw(self, battery_msg: msgBattery):
        payload = self._build_battery_payload(battery_msg)
        with self._rpc_lock:
            self.__rpc_client.call_service("DSPChassis", "publishBattery", json.dumps(payload))

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

    def createSerial(self, name, baudrate):
        self.child.createSerial(name, baudrate)
    def closeSerial(self):
        self.child.closeSerial()

    def send(self, msg: list):
        self.child.send(msg)

    def publish(self, battery_msg: msgBattery):
        self._promote_status_for_data_publish()
        with self._status_lock:
            self._last_battery_msg.CopyFrom(battery_msg)
        self._publish_raw(battery_msg)

    def getDIStates(self, index):
        return Di.get_di(index)

    def getDOStates(self, index):
        return Do.get_do(index)

    def setModbusData(self, type: str, addr: int, data: list) -> bool:
        is_ok: bool = self.__rpc_client.setModbusData(type, addr, data)
        return is_ok

    def getModbusData(self, type: str, addr: int, size: int) -> list:
        msg: list = self.__rpc_client.getModbusData(type, addr, size)
        return msg

    def setTimeout(self):
        self._set_status_connect_error()
        self._publish_cached()

    def clearTimeout(self):
        self._set_status_running()

    def setError(self, errNum, errMessage, reason='battery', method='check out', filename='net2Serial_xx.py'):
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

    def close(self):
        self._stop_heartbeat.set()
        if self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=1.0)
        self.__rpc_server.close()
        self.__rpc_client.close()
        close = getattr(self.child, "close", None)
        if callable(close):
            close()
        else:
            self.closeSerial()

    def __del__(self):
        self.close()


if __name__ == "__main__":
    pass
