import sys,platform
import syspy.lib.rpc_client as rc
import syspy.lib.rpc_server as rs
import syspy.lib.udp_debug as ud
_syslog = ud.syslogDebug("can_battery")
from google.protobuf.json_format import MessageToJson
sys.path.append('/usr/local/etc/.SeerRobotics/rbk/resources/scripts/genetic/syspy/battery_Can/')
DEFAULT_RPC_ADDR = "ipc:///tmp/CanPass_rpc.ipc"
class canPassBase:
    def __init__(self):
        self.__rpc_client = rc.rpcClient()
        self.__rpc_client.connect(DEFAULT_RPC_ADDR)
        self.__rpc_server = rs.rpcServer()
        self.__rpc_server.registerFunction(self.setChargeStateOn)
        self.__rpc_server.registerFunction(self.setChargeStateOff)
        if platform.machine() == 'x86_64':
            import syspy.battery_Can.canpass_x86 as x86
            self.child = x86.canPassX86(self.__rpc_client)
        elif platform.machine() == 'aarch64':
            import syspy.battery_Can.canpass_aarch64 as aarch64
            self.child = aarch64.canPassAarch64()
        self.setCallBack()
        self.need_charge = False

    def setCallBack(self):
        self.child.setCallBack(self.handleData)

    def createBatteryMessage(self):
        return self.child.createBatteryMessage()

    def createCanBus(self, channel, bitrate):
        self.child.createCanBus(channel, bitrate)

    def recCanframe(self,msg):
        return self.child.recCanframe(msg)

    def attachCanID(self, *args):
        if isinstance(args[0], int) and args[0] < 3:
            channel = args[0]
            id_nums = args[1]
            can_ids = [arg for arg in args[2:]]
            self.child.attachCanID(channel, id_nums, *can_ids)
        else:
            can_ids = [arg for arg in args]
            self.child.attachCanID(*can_ids)

    def sendCanframe(self, channel, can_id, dlc, extend, can_string):
        self.child.sendCanframe(channel, can_id, dlc, extend, can_string)

    def publish(self, battery_info):
        msg = MessageToJson(battery_info)
        self.__rpc_client.publishBattery(msg)

    def getDIStates(self,index):
        return self.__rpc_client.getDIStates(index)

    def getDOStates(self,index):
        return self.__rpc_client.getDOStates(index)

    def setTimeout(self):
        self.__rpc_client.setWarning(54001, "Can battery response time out")

    def clearTimeout(self):
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

