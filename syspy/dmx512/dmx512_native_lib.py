import fcntl
import logging
import subprocess
import threading

import can
import serial
from google.protobuf.json_format import MessageToJson
from syspy import Trace
from syspy import RBK_VERSION
from syspy.led import _send_arm_dmx_info, _send_sim_dmx512_payload
from syspy.sim import sim_only
if RBK_VERSION == 3:
    from syspy.v3.protobuf.message import message_dmx512_pb2
if RBK_VERSION == 4:
    from syspy.v4.protobuf.message import messageV4_dmx512_pb2 as message_dmx512_pb2

log = logging.getLogger("rbk.script")


def _mock_send_dmx512(_self, dmx512_info):
    type_exm = message_dmx512_pb2.msgDmx512()
    if not isinstance(dmx512_info, type(type_exm)):
        return

    payload = (MessageToJson(dmx512_info, preserving_proto_field_name=False) + "\n").encode("utf-8")
    if _send_sim_dmx512_payload(payload):
        Trace.log("mock send dmx512 to simulator", name="DMX512.sim")
    else:
        Trace.log("mock send dmx512 failed: no simulator port", name="DMX512.sim")


class dmx512NativeLib:
    def __init__(self):
        Trace.log("start native dmx512")
        self.ser = None
        self.__callback = None
        self.__should_close = False
        self.__msg_thread = None
        self.bus = None
        self.__should_close = threading.Event()  # 使用事件来控制线程关闭
        self.can_ids = []

    def setCallBack(self, handleData):
        if not handleData:
            Trace.log("Set callback error.It should be implemented the func 'handleData'")
        else:
            self.__callback = handleData

    # LED
    @sim_only(on_sim=_mock_send_dmx512)
    def sendDmx512(self, dmx512_info):
        type_exm = message_dmx512_pb2.msgDmx512()
        if isinstance(dmx512_info, type(type_exm)):
            msg = MessageToJson(dmx512_info)
            _send_arm_dmx_info(msg)

    # Serial
    def createSerial(self, name, baudrate):
        self.ser = serial.Serial(port=name, baudrate=baudrate, bytesize=8, parity="N", stopbits=1)
        command = "cat /etc/srcname"
        output = subprocess.check_output(command, shell=True)
        output = output.decode("utf-8").strip()
        Trace.log(f"{output=}")
        if output in ['SRC800', 'SRC3000']:
            fcntl.ioctl(self.ser, 0)  # 这行决定了485模式
        self.__msg_thread = threading.Thread(target=self.__serialRun, name="__serialRun", daemon=True)
        self.__msg_thread.start()
        Trace.log(f"createSerial  {name=}, {baudrate=}")

    def send(self, msg: list):
        self.ser.write(msg)

    def recv(self):
        data = self.ser.read()
        if not self.__callback is None:
            self.__callback(data)

    def __serialRun(self):
        try:
            while not self.__should_close.is_set():
                self.recv()
        except Exception as e:
            print("exception:", e)
        finally:
            self.ser.close()
            pass

    # CAN
    def createCanBus(self, channel, bitrate):
        self.bus = can.interface.Bus(bustype="socketcan", channel=channel, bitrate=bitrate)
        self.__msg_thread = threading.Thread(target=self.__canRun, name="__canRun", daemon=True)
        self.__msg_thread.start()

    def can_filter(self, msg):
        return msg.arbitration_id in self.can_ids

    def attachCanID(self, *canid):
        for i in range(len(canid)):
            self.can_ids.append(canid[i])
        filters = []
        for id_ in self.can_ids:
            if id_ < 0x800:
                can_mask = 0x7FF
            else:
                can_mask = 0x1FFFFFFF
            filters.append({"can_id": id_, "can_mask": can_mask})
        self.bus.set_filters(filters)
        Trace.log(f"Attached CAN IDs: {[hex(id_) for id_ in self.can_ids]}")

    def sendCanframe(self, channel, can_id, dlc, extend, can_string: list):
        try:
            msg = can.Message(arbitration_id=can_id, data=can_string, is_extended_id=extend, dlc=dlc)
            self.bus.send(msg)
            Trace.log(f"message send: can_id={hex(can_id)}, dlc={dlc}, extend={extend}, can_string={can_string}")
        except Exception as e:
            print(f"Error sending CAN frame: {e}")

    def recvCan(self):
        msg = self.bus.recv(1.0)  # 设置超时时间
        if msg and self.can_filter(msg):
            if not self.__callback is None:
                self.__callback(msg)

    def __canRun(self):
        try:
            while not self.__should_close.is_set():
                self.recvCan()
        except Exception as e:
            print("recvCan exception:", e)
        finally:
            self.bus.shutdown()  # 确保总线关闭

    def __del__(self):
        self.__should_close.set()  # 设置事件，通知线程关闭
        self.__msg_thread.join()  # 等待线程结束


if __name__ == "__main__":
    pass
