import sys,platform
import syspy.lib.rpc_client as rc
import syspy.lib.rpc_server as rs
from google.protobuf.json_format import MessageToJson
sys.path.append('/usr/local/etc/.SeerRobotics/rbk/resources/scripts/genetic/syspy/battery_Serial/')
DEFAULT_RPC_ADDR = "ipc:///tmp/python2dsp_rpc.ipc"

class batteryBase:
    def __init__(self):
        if platform.machine() == 'x86_64':
            import syspy.battery_Serial.serialpass_x86 as x86
            self.child = x86.serialPassX86()
        elif platform.machine() == 'aarch64':
            import syspy.battery_Serial.serialpass_aarch64 as aarch64
            self.child = aarch64.serialPassAarch64()
        self.__rpc_client = rc.rpcClient()
        self.__rpc_client.connect(DEFAULT_RPC_ADDR)
        self.__rpc_server = rs.rpcServer()
        self.__rpc_server.registerFunction(self.setChargeStateOn)
        self.__rpc_server.registerFunction(self.setChargeStateOff)
        self.setCallBack()
        self.need_charge = False

    def setCallBack(self):
        self.child.setCallBack(self.handleData)

    def createBatteryMessage(self):
        return self.child.createBatteryMessage()

    def createSerial(self, name, baudrate):
        self.child.createSerial(name, baudrate)

    def send(self, msg:list):
        self.child.send(msg)

    def publish(self, battery_info):
        msg = MessageToJson(battery_info)
        self.__rpc_client.publishBattery(msg)
        print("publishBattery.")

    def getDIStates(self,index):
        return self.__rpc_client.getDIStates(index)

    def getDOStates(self,index):
        return self.__rpc_client.getDOStates(index)

    def setTimeout(self):
        print("Serail battery response time out")
        self.__rpc_client.setWarning(54001, "Serail battery response time out")

    def clearTimeout(self):
        print("Clear timeout")
        self.__rpc_client.clearWarning(54001)

    def setWarning(self, warNum, warMessage):
        self.__rpc_client.setWarning(warNum, warMessage)

    def setError(self, errNum, errMessage):
        self.__rpc_client.setError(errNum, errMessage)

    def warningExists(self,code):
        return self.__rpc_client.warningExists(code)

    def errorExists(self,code):
        return self.__rpc_client.errorExists(code)

    def setChargeStateOn(self):
        self.need_charge = True

    def setChargeStateOff(self):
        self.need_charge = False

    def isNeedCharge(self):
        return self.need_charge

    def __del__(self):
        self.__rpc_server.close()
        self.__rpc_client.close()

if __name__ == "__main__":
    pass

