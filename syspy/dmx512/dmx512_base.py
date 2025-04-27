import logging
import platform
from enum import Enum

from syspy import NavStatus, NavSpeed, Battery, Controller, Di, Do, Abnormal, Led
from syspy.protobuf import Message_MoveStatus, Message_Battery, Message_NavSpeed

log = logging.getLogger("rbk.script")


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
        if platform.machine() == "x86_64":
            import syspy.dmx512.dmx512_x86 as x86

            self.child = x86.dmx512X86()
        elif platform.machine() == "aarch64":
            import syspy.dmx512.dmx512_aarch64 as aarch64

            self.child = aarch64.dmx512Aarch64()
        log.info("start dmx512")

    # genetic
    def createMoveStatusMessage(self):
        return Message_MoveStatus()

    def createBatteryMessage(self):
        return Message_Battery()

    def createNavSpeedMessage(self):
        return Message_NavSpeed()

    def recMoveStatus(self) -> Message_MoveStatus:
        NavStatus.update()
        return NavStatus.get_data()

    def recBattery(self) -> Message_Battery:
        Battery.update()
        return Battery.get_data()

    def recRobotSpeed(self) -> Message_NavSpeed:
        NavSpeed.update()
        return NavSpeed.get_data()

    def getChassisStop(self) -> bool:
        return NavStatus.getChassisStop()

    def getEMCState(self) -> bool:
        Controller.update()
        return Controller.get_emc()

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

    # led
    def createDmx512Message(self):
        return self.child.createDmx512Message()

    def sendDmx512(self, dmx512_info):
        self.child.sendDmx512(dmx512_info)

    def getLedExternalControlInfo(self):
        json_string = Led.getLedExternalControlInfo()
        log.info("getinfo: ", json_string)
        return json_string

    # Serial
    def createSerial(self, name, baudrate):
        self.child.createSerial(name, baudrate)

    def send(self, msg: list):
        self.child.send(msg)

    # can
    def createCanBus(self, channel, bitrate):
        self.child.createCanBus(channel, bitrate)

    def recCanframe(self, msg):
        return self.child.recCanframe(msg)

    def attachCanID(self, *args):
        can_ids = [arg for arg in args]
        self.child.attachCanID(*can_ids)

    def sendCanframe(self, channel, can_id, dlc, extend, can_string):
        self.child.sendCanframe(channel, can_id, dlc, extend, can_string)


if __name__ == "__main__":
    pass
