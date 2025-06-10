import fcntl
import logging
import subprocess
import threading

import serial

from syspy.protobuf.message import message_battery_pb2

log = logging.getLogger("rbk.script")


class serialPassAarch64:
    def __init__(self):
        log.info("serialPassAarch64 start!")
        self.ser = None
        self.__callback = None
        self.__should_close = False
        self.__msg_thread = None

    def createSerial(self, name, baudrate):
        self.ser = serial.Serial(port=name, baudrate=baudrate, bytesize=8, parity="N", stopbits=1)
        command = "cat /etc/srcname"
        output = subprocess.check_output(command, shell=True)
        output = output.decode("utf-8").strip()
        log.info(f"{output=}")
        if not output == "SRC880":
            fcntl.ioctl(self.ser, 0)  # 485模式
        self.__msg_thread = threading.Thread(target=self.__run, name="run")
        self.__msg_thread.start()  # FIXME: when to join?
        log.info("createSerial  name:{},baudrate:{}".format(name, baudrate))

    def send(self, msg: list):
        self.ser.write(msg)

    def recv(self):
        data = self.ser.read()
        if not self.__callback is None:
            self.__callback(data)

    def setCallBack(self, handleData):
        if not handleData:
            log.error("Set callback error.It should be implemented the func 'handleData'")
        else:
            self.__callback = handleData

    def createBatteryMessage(self):
        return message_battery_pb2.Message_Battery()

    def __run(self):
        try:
            while not self.__should_close:
                self.recv()
        except Exception as e:
            log.error("exception:", e)
        finally:
            self.ser.close()
            pass

    def stop(self):
        self.__should_close = True
        if self.__msg_thread:
            self.__msg_thread.join()

    def __del__(self):
        self.stop()


if __name__ == "__main__":
    pass
