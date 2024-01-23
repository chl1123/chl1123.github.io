import json
import sys
from google.protobuf.json_format import MessageToJson, Parse
import syspy.lib.rpc_client as rc
import syspy.lib.udp_debug as ud
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
        self.__debug_out = ud.udpDebug()
        sys.stdout = self.__debug_out
        print("start dmx512")

    def sendDmx512(self, dmx512_info):
        type_exm = message_dmx512_pb2.Message_Dmx512()
        if (isinstance(dmx512_info, type(type_exm))):
            msg = MessageToJson(dmx512_info)
            self.__rpc_client.receivePython(msg)

    def recMoveStatus(self):
        str = self.__rpc_client.getMoveStatus()
        movestatus = Parse(str, message_movetask_pb2.Message_MoveStatus())
        return movestatus

    def recBattery(self):
        str = self.__rpc_client.getBatterToPython()
        batter_ = Parse(str, message_battery_pb2.Message_Battery())
        return batter_

    def recRobotSpeed(self):
        str = self.__rpc_client.getNavSpeed()
        robotSpeed = Parse(str, message_navigation_pb2.Message_NavSpeed())
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
        return self.__rpc_client.modelDeviceEnable(str)

    def getChassisStop(self):
        return self.__rpc_client.getChassisStop()

    def getShowCharging(self):
        return self.__rpc_client.getShowCharging()

    def getEMCState(self):
        return self.__rpc_client.getEMCState()

    def getShowBattery(self):
        return self.__rpc_client.getShowBattery()

    def getDIStates(self,index):
        return self.__rpc_client.getDIStates(index)

    def getDOStates(self,index):
        return self.__rpc_client.getDOStates(index)

    def getBatteryMaxPercentage(self):
        maxPer = self.__rpc_client.getBatteryMaxPercentage()
        return maxPer

    def getErrorNum(self):
        return self.__rpc_client.errorNum()

    def getFatalNum(self):
        return self.__rpc_client.fatalNum()
#
    def warningExists(self,code):
        return self.__rpc_client.warningExists(code)

    def errorExists(self,code):
        return self.__rpc_client.errorExists(code)

    def __del__(self):
        self.__rpc_client.close()

if __name__ == "__main__":
    pass