import fcntl
import logging
import subprocess
import threading

import can
import serial
from google.protobuf.json_format import MessageToJson

from syspy import Led
from syspy.protobuf.message import message_dmx512_pb2

log = logging.getLogger("rbk.script")


class dmx512Aarch64:
    def __init__(self):
        log.info("start arm dmx512")
        self.ser = None
        self.__callback = None
        self.__should_close = False
        self.__msg_thread = None
        self.bus = None
        self.__should_close = threading.Event()  # 使用事件来控制线程关闭
        self.can_ids = []

    def setCallBack(self, handleData):
        if not handleData:
            log.error("Set callback error.It should be implemented the func 'handleData'")
        else:
            self.__callback = handleData

    # LED
    def createDmx512Message(self):
        return message_dmx512_pb2.Message_Dmx512()

    def sendDmx512(self, dmx512_info):
        type_exm = message_dmx512_pb2.Message_Dmx512()
        if isinstance(dmx512_info, type(type_exm)):
            msg = MessageToJson(dmx512_info)
            Led.sendArmDmxInfo(msg)

    # Serial
    def createSerial(self, name, baudrate):
        self.ser = serial.Serial(port=name, baudrate=baudrate, bytesize=8, parity="N", stopbits=1)
        command = "cat /etc/srcname"
        output = subprocess.check_output(command, shell=True)
        output = output.decode("utf-8").strip()
        log.info(f"{output=}")
        if not output == "SRC880":
            fcntl.ioctl(self.ser, 0)  # 这行决定了485模式
        self.__msg_thread = threading.Thread(target=self.__serialRun, name="__serialRun", daemon=True)
        self.__msg_thread.start()
        log.info(f"createSerial  {name=}, {baudrate=}")

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
        log.info(f"Attached CAN IDs: {[hex(id_) for id_ in self.can_ids]}")

    def sendCanframe(self, channel, can_id, dlc, extend, can_string: list):
        try:
            msg = can.Message(arbitration_id=can_id, data=can_string, is_extended_id=extend, dlc=dlc)
            self.bus.send(msg)
            log.info(f"message send: can_id={hex(can_id)}, dlc={dlc}, extend={extend}, can_string={can_string}")
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
