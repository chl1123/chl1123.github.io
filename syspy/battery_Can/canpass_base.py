import json
import logging
import os
import platform
import subprocess
import sys
from typing import Union

from google.protobuf.json_format import MessageToJson

import syspy.lib.rpc.server as rs
from syspy import Abnormal, RBK_VERSION
from syspy import Battery, Di, Do

if RBK_VERSION == 3:
    from syspy.v3.protobuf.message.message_battery_pb2 import msgBattery
if RBK_VERSION == 4:
    from syspy.v4.protobuf.message.messageV4_battery_pb2 import MessageV4_Battery  as msgBattery
    from syspy.v4.lib.rbk import core, service

log = logging.getLogger("rbk.script")


class canPassBase:
    def __init__(self):
        log.info("canPassBase __init__")
        self.__rpc_server = rs.RpcServer("battery")
        self.__rpc_server.registerFunction(self.setChargeStateOn)
        self.__rpc_server.registerFunction(self.setChargeStateOff)
        self.__rpc_server.start()

        command = "cat /etc/srcname"
        output = subprocess.check_output(command, shell=True)
        output = output.decode("utf-8").strip()
        log.info(f"{output=}")

        # 只有 SRC2000 控制器是 CAN 透传形式
        if platform.machine() == 'x86_64' and "SRC2000" in output:
            log.info("platform: x86_64")
            import syspy.battery_Can.canpass_x86 as x86
            self.child = x86.canPassX86()
        # TODO: 这里的派生类及判断需要优化
        elif platform.machine() == 'aarch64'or "SRC5000" in output:
            log.info("platform: aarch64")
            import syspy.battery_Can.canpass_aarch64 as aarch64
            self.child = aarch64.canPassAarch64()

        if RBK_VERSION == 4:
            name="pyBatteryServer"
            core.Init(name)
            service.addService(name, "serviceDispatcher", self.serviceDispatcher)

        self.setCallBack()
        self.need_charge = False


    def serviceDispatcher(self,route_json: str):
        request = json.loads(route_json)
        print(f"request={request}")
        response = dict()
        func_name = request["func_name"]
        if func_name == "getBatteryMsg":
            response["result"] = self.get_battery_msg()
            return json.dumps(response)
    
    
    def get_battery_msg(self) -> dict:
        return json.loads(self.msg)
        

    def setCallBack(self):
        self.child.setCallBack(self.handleData)

    def createBatteryMessage(self):
        return msgBattery()

    def createCanBus(self, channel, bitrate):
        self.child.createCanBus(channel, bitrate)

    def recCanframe(self, msg):
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
        log.info(f"{srcname=}, {ports=}")

        port = Battery.getCanPort()
        port = int(port.replace("port","")) # "port1" ---> 1 "port2"---> 2
        log.info(f"{port=}")
        if port in (1, 2, 3):
            selected_port = ports[port - 1]  # 根据端口号获取对应的端口
            log.info(f"{selected_port=}")
        else:
            log.error(f"Invalid port number: {port}")
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

    def publish(self, battery_info: msgBattery) -> int:
        msg = MessageToJson(battery_info)
        return Battery.publish(msg)

    def getDIStates(self, index):
        return Di.get_di(index)

    def getDOStates(self, index):
        return Do.get_do(index)

    def setTimeout(self):
        Abnormal.setConnect(57040, "Battery response time out", "No data response",
                           "Check the battery or wiring","robot.model","battery","Battery-000")

    def clearTimeout(self):
        Abnormal.clear(57040)

    def setError(self, errNum, errMessage, reason='battery', method='check out', filename='btCanPass_xx.py'):
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

    def close(self):
        self.child.close()

    def __del__(self):
        self.close()


if __name__ == "__main__":
    pass
