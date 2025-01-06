import sys,platform
import syspy.lib.rpc_client as rc
# import syspy.lib.udp_debug as ud
from enum import Enum

from syspy import Move, NavSpeed, Battery, Controller, Di, Do, Abnormal, Led
from syspy.protobuf.messsage import Message_MoveStatus, Message_NavSpeed, Message_Battery

DEFAULT_RPC_ADDR = "ipc:///tmp/python2dsp_dmx512.ipc"

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
        if platform.machine() == 'x86_64':
            import syspy.dmx512.dmx512_x86 as x86
            self.child = x86.dmx512X86(self.__rpc_client)
        elif platform.machine() == 'aarch64':
            import syspy.dmx512.dmx512_aarch64 as aarch64
            self.child = aarch64.dmx512Aarch64(self.__rpc_client)
        # self.__debug_out = ud.udpDebug()
        # sys.stdout = self.__debug_out
        print("start dmx512")



    ''' genetic '''
    def createMoveStatusMessage(self):
        return self.child.createMoveStatusMessage()

    def createBatteryMessage(self):
        return self.child.createBatteryMessage()

    def createNavSpeedMessage(self):
        return self.child.createNavSpeedMessage()

    def recMoveStatus(self) -> Message_MoveStatus:
        Move.update()
        return Move.data

    def recBattery(self) -> Message_Battery:
        Battery.update()
        return Battery.data

    def recRobotSpeed(self) -> Message_NavSpeed:
        NavSpeed.update()
        return NavSpeed.data

    def getChassisStop(self) -> bool:
        return Move.getChassisStop()

    def getEMCState(self) -> bool:
        Controller.update()
        return Controller.data.emc

    def getDIStates(self, index) -> bool:
        return Di.get_di(index)

    def getDOStates(self, index) -> bool:
        return Do.get_do(index)

    def getBatteryMaxPercentage(self):
        return Battery.getAlarmPercentage()

    def getErrorNum(self):
        return Abnormal.getNum()

    def getFatalNum(self):
        return Abnormal.getNum()

    def warningExists(self, code):
        return Abnormal.exists(code)

    def setCallBack(self):
        self.child.setCallBack(self.handleData)

    def errorExists(self, code):
        return Abnormal.exists(code)

    ''' led '''
    def createDmx512Message(self):
        return self.child.createDmx512Message()

    def sendDmx512(self,dmx512_info):
        self.child.sendDmx512(dmx512_info)

    def getLedExternalControlInfo(self):
        json_string = Led.getLedExternalControlInfo()
        print('getinfo: ',json_string)
        return json_string



    ''' Serial '''
    def createSerial(self, name, baudrate):
        self.child.createSerial(name, baudrate)

    def send(self, msg: list):
        self.child.send(msg)



    ''' can '''
    def createCanBus(self, channel, bitrate):
        self.child.createCanBus(channel, bitrate)

    def recCanframe(self,msg):
        return self.child.recCanframe(msg)

    def attachCanID(self, *args):
        can_ids = [arg for arg in args]
        self.child.attachCanID(*can_ids)

    def sendCanframe(self, channel, can_id, dlc, extend, can_string):
        self.child.sendCanframe(channel, can_id, dlc, extend, can_string)



    def __del__(self):
        self.__rpc_client.close()

if __name__ == "__main__":
    pass