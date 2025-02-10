import sys,platform,os,json

import syspy.lib.rpc.server as rs
from syspy.protobuf.messsage import Message_Battery
from syspy import Battery, Di, Do

import syspy.lib.udp_debug as ud
print("import syspy.lib.udp_debug as ud after")
from syspy import Abnormal
# _syslog = ud.syslogDebug("can_battery")
from google.protobuf.json_format import MessageToJson
DEFAULT_RPC_ADDR = "ipc:///tmp/CanPass_rpc.ipc"

class canPassBase:
    def __init__(self):
        print("canPassBase __init__")
        self.__rpc_server = rs.rpcServer()
        self.__rpc_server.registerFunction(self.setChargeStateOn)
        self.__rpc_server.registerFunction(self.setChargeStateOff)
        if platform.machine() == 'x86_64':
            print("platform: x86_64")
            import syspy.battery_Can.canpass_x86 as x86
            self.child = x86.canPassX86()
        elif platform.machine() == 'aarch64':
            print("platform: aarch64")
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

    def getBatteryCanPort(self):
        with open('/etc/srcname', 'r') as file:
            srcname = file.readline().strip()

        if 'SRC880' in srcname:
            ports = ('can1', 'can0', 'can2')
        elif 'SRC2000' in srcname:
            ports = (1, 2, 3)
        else:
            ports = ('can0', 'can1', 'can2')
        print(f'name: {srcname}, ports:{ports}')

        port = Battery.getCanPort()
        print(f'port: {port}')
        if port in (1, 2, 3):
            selected_port = ports[port - 1]  # 根据端口号获取对应的端口
            print(f'selected_port: {selected_port}')
        else:
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

    def publish(self, battery_info: Message_Battery) -> int:
        msg = MessageToJson(battery_info)
        return Battery.publish(msg)

    def getDIStates(self,index):
        return Di.get_di(index)

    def getDOStates(self,index):
        return Do.get_do(index)

    def setTimeout(self):
        Abnormal.setDevice(54001,"Can battery response time out")

    def clearTimeout(self):
        Abnormal.clear(54001)

    def setError(self, errNum, errMessage,reason='battery',method='check out',filename='btCanPass_xx.py'):
        Abnormal.setDevice(errNum,errMessage,reason,method,filename)

    def errorExists(self,code):
        return Abnormal.exists(code)

    def setChargeStateOn(self):
        self.need_charge = True

    def setChargeStateOff(self):
        self.need_charge = False

    def isNeedCharge(self):
        return self.need_charge

    def close(self):
        self.child.close()

    def __del__(self):
        self.close()

if __name__ == "__main__":
    pass

