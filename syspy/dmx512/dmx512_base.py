import logging
import platform
from enum import Enum
from syspy import Abnormal, Battery, Do, Di, Controller, NavStatus, Led
from syspy import RBK_VERSION
from syspy import Trace
if RBK_VERSION == 3:
    from syspy.v3.protobuf.message import message_dmx512_pb2
if RBK_VERSION == 4:
    from syspy.v4.protobuf.message import messageV4_dmx512_pb2 as message_dmx512_pb2

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
    Blink = 0x0A


class dmx512Base:
    def __init__(self):
        if platform.machine() == "x86_64":
            import syspy.dmx512.dmx512_pass_lib as passThough

            self.child = passThough.dmx512PassLib()
        elif platform.machine() == "aarch64":
            import syspy.dmx512.dmx512_native_lib as native

            self.child = native.dmx512NativeLib()
        Trace.log("start dmx512")

    # genetic
    def getChassisStop(self) -> bool:
        return NavStatus.getChassisStop()

    def getEMCState(self) -> bool:
        return Controller.getEmc()

    def getDIStates(self, index) -> bool:
        return Di.get_di(index)

    def getDOStates(self, index) -> bool:
        return Do.get_do(index)

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
        return message_dmx512_pb2.msgDmx512()

    def sendDmx512(self, dmx512_info):
        self.child.sendDmx512(dmx512_info)

    # Serial
    def createSerial(self, name, baudrate):
        self.child.createSerial(name, baudrate)

    def send(self, msg: list):
        self.child.send(msg)

    # can
    def createCanBus(self, channel, bitrate):
        self.child.createCanBus(channel, bitrate)

    def attachCanID(self, *args):
        can_ids = [arg for arg in args]
        self.child.attachCanID(*can_ids)

    def sendCanframe(self, channel, can_id, dlc, extend, can_string):
        self.child.sendCanframe(channel, can_id, dlc, extend, can_string)


if __name__ == "__main__":
    pass
