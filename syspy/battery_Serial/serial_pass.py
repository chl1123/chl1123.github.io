import syspy.lib.pass_through as pt
from syspy import RBK_VERSION
from syspy import Trace
DEFAULT_PASS_ADDR = "ipc:///tmp/python2dsp_udp.ipc"

if RBK_VERSION == 3:
    from syspy.v3.protobuf.message.message_battery_pb2 import msgBattery
if RBK_VERSION == 4:
    from syspy.v4.protobuf.message.messageV4_battery_pb2 import MessageV4_Battery  as msgBattery

import logging

log = logging.getLogger("rbk.script")


class SerialPass:
    def __init__(self):
        Trace.log("SerialPass start!")
        self.__pass = pt.passThrough("serial")
        self.__pass.serialConnect(DEFAULT_PASS_ADDR)

    def createBatteryMessage(self):
        return msgBattery()

    def send(self, msg: list):
        if isinstance(msg, list):
            self.__pass.send(bytes(msg))
        else:
            Trace.log("Write msg format error. please send a list")

    def setCallBack(self, handleData):
        if not handleData:
            Trace.log("Set callback error.It should be implemented the func 'handleData'")
        else:
            self.__pass.setCallBack(handleData)

    def shutdown(self):
        try:
            if self.__pass:
                self.__pass.shoutDown()  # Assuming typo in original code is fixed here
        except Exception as e:
            Trace.log(f"Failed to shutdown properly: {e}")

    def __del__(self):
        self.shutdown()


if __name__ == "__main__":
    pass
