import platform

import syspy.lib.rpc.client as rc
import syspy.lib.rpc.server as rs
import syspy.lib.udp_debug as ud
from syspy import Battery, Di, Do

_syslog = ud.syslogDebug("serial_battery")
from google.protobuf.json_format import MessageToJson

DEFAULT_RPC_ADDR = "ipc:///tmp/python2dsp_rpc.ipc"


class batteryBase:
    def __init__(self):
        if platform.machine() == "x86_64":
            import syspy.battery_Serial.serialpass_x86 as x86
            self.child = x86.serialPassX86()
        elif platform.machine() == "aarch64":
            import syspy.battery_Serial.serialpass_aarch64 as aarch64
            self.child = aarch64.serialPassAarch64()
        self.__rpc_client = rc.RpcClient()
        self.__rpc_server = rs.RpcServer()
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

    def publish(self, battery_info):
        msg = MessageToJson(battery_info)
        Battery.publish(msg)

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
        self.__rpc_client.setWarning(54001, "Serail battery response time out")

    def clearTimeout(self):
        self.__rpc_client.clearWarning(54001)

    def setWarning(self, warNum, warMessage):
        self.__rpc_client.setWarning(warNum, warMessage)

    def setError(self, errNum, errMessage):
        self.__rpc_client.setError(errNum, errMessage)

    def warningExists(self, code):
        return self.__rpc_client.warningExists(code)

    def errorExists(self, code):
        return self.__rpc_client.errorExists(code)

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
