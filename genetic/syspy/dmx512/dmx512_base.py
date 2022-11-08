import json
import sys
from google.protobuf.json_format import MessageToJson, Parse
import syspy.lib.rpc_client as rc
from enum import Enum

sys.path.append('/usr/local/etc/.SeerRobotics/rbk/resources/scripts/site-packages')
sys.path.append('/usr/local/etc/.SeerRobotics/rbk/resources/scripts/genetic/syspy/dmx512')
DEFAULT_RPC_ADDR = "ipc:///tmp/python2dsp_dmx512.ipc"

import message_dmx512_pb2
import message_movetask_pb2
import message_battery_pb2
import message_navigation_pb2

class LightType(Enum):
    Battery = 0x02
    ConstantLight = 0x04
    Errofatal = 0x01
    MutableBreath = 0x03
    Charging = 0x05
    MutableHorseRace = 0x06
    FlowCalculator = 0x07
    Rainbow = 0x08


class dmx512Base:
    def __init__(self):
        self.__rpc_client = rc.rpcClient()
        self.__rpc_client.connect(DEFAULT_RPC_ADDR)

    def send_dmx512(self, dmx512_info):
        print("send_dmx512")
        type_exm = message_dmx512_pb2.Message_Dmx512()
        if (isinstance(dmx512_info, type(type_exm))):
            msg = MessageToJson(dmx512_info)
            print(msg)
            self.__rpc_client.receivePython(msg)

    def rec_moveStatus(self):
        print("rec_moveStatus")
        str = self.__rpc_client.getMoveStatus()
        movestatus = Parse(str, message_movetask_pb2.Message_MoveStatus())
        print(movestatus)
        return movestatus

    def rec_battery(self):
        print("rec_battery")
        str = self.__rpc_client.getBatterToPython()
        batter_ = Parse(str, message_battery_pb2.Message_Battery())
        print(batter_)
        return batter_

    def rec_robotSpeed(self):
        print("rec_robotSpeed")
        str = self.__rpc_client.getNavSpeed()
        robotSpeed = Parse(str, message_navigation_pb2.Message_NavSpeed())
        print(robotSpeed)
        return robotSpeed

    def createDmx512Message(self):
        return message_dmx512_pb2.Message_Dmx512()

    def createMoveStatusMessage(self):
        return message_movetask_pb2.Message_MoveStatus()

    def createBatteryMessage(self):
        return message_battery_pb2.Message_Battery()

    def createNavSpeedMessage(self):
        return message_navigation_pb2.Message_NavSpeed()

    def modelDeviceEnable(self,str):
        print("modelDeviceEnable")
        print(self.__rpc_client.modelDeviceEnable(str))
        return self.__rpc_client.modelDeviceEnable(str)

    def getBatteryMaxPercentage(self):
        print("getBatteryMaxPercentage")
        maxPer = self.__rpc_client.getBatteryMaxPercentage()
        print(maxPer)
        return maxPer

    def getErrorNum(self):
        print("getErrorNum")
        print(self.__rpc_client.errorNum())
        return self.__rpc_client.errorNum()

    def getFatalNum(self):
        print("getFatalNum")
        print(self.__rpc_client.fatalNum())
        return self.__rpc_client.fatalNum()
#
    def warningExists(self,code):
        print("warningExists")
        return self.__rpc_client.warningExists(code)

    def errorExists(self,code):
        print("errorExists")
        return self.__rpc_client.errorExists(code)

    def __del__(self):
        self.__rpc_client.close()

if __name__ == "__main__":
    pass