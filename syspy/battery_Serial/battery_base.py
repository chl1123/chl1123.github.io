import platform
import logging
import syspy.v3.lib.rpc.client as rc
import syspy.lib.rpc.server as rs
import syspy.lib.udp_debug as ud
from syspy import Battery, Di, Do
from syspy import Abnormal, RBK_VERSION
import subprocess
_syslog = ud.syslogDebug("serial_battery")
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
        log.info(f"{output=}")
        if output in ['SRC2000']: #passthrough
            log.info("Serial Type: passThrough")
            import syspy.battery_Serial.serial_pass as serial_pass
            self.child = serial_pass.SerialPass()
        else:
            log.info("Serial Type: native")
            import syspy.battery_Serial.serial_native as serial_native
            self.child = serial_native.SerialNative()
        self.__rpc_client = rc.RpcClient()
        self.__rpc_server = rs.RpcServer("battery")
        self.__rpc_server.registerFunction(self.setChargeStateOn)
        self.__rpc_server.registerFunction(self.setChargeStateOff)
        self.__rpc_server.start()
        self.setCallBack()
        self.need_charge = False

    def setCallBack(self):
        self.child.setCallBack(self.handleData)

    def createBatteryMessage(self):
        return self.child.createBatteryMessage()

    def createSerial(self, name, baudrate):
        self.child.createSerial(name, baudrate)

    def send(self, msg: list):
        self.child.send(msg)

    def publish(self, battery_msg: msgBattery):
        Battery.publish(battery_msg)

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
        Abnormal.setConnect(57040, "Battery response time out", "No data response",
                           "Check the battery or wiring","robot.model","battery","Battery-000")

    def clearTimeout(self):
        Abnormal.clear(57040)


    def setError(self, errNum, errMessage, reason='battery', method='check out', filename='net2Serial_xx.py'):
        Abnormal.setDevice(errNum, errMessage, reason, method, filename)

    def errorExists(self, code):
            return Abnormal.exists(code)

    def clearError(self, code):
        Abnormal.clear(code)

    def setChargeStateOn(self):
        self.need_charge = True

    def setChargeStateOff(self):
        self.need_charge = False

    def isNeedCharge(self):
        return self.need_charge

    def __del__(self):
        self.__rpc_client.close()


if __name__ == "__main__":
    pass
