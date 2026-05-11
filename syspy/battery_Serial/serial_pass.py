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
        battery_msg = msgBattery()
        if RBK_VERSION == 3:
            battery_msg.userData = bytes("0000000000000000", encoding='utf-8')
        else:
            battery_msg.user_data = bytes("0000000000000000", encoding='utf-8')
        return battery_msg

    def send(self, msg: list):
        if isinstance(msg, list):
            self.__pass.send(bytes(msg))
        else:
            Trace.log("Write msg format error. please send a list")

    def createSerial(self, name, baudrate):
        Trace.log(f"NOTICE: Creating serial port in passThrough mode is not supported. Port: {name}, Baudrate: {baudrate}")

    def closeSerial(self):
        Trace.log("NOTICE: Closing serial port in passThrough mode is not supported.")

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
