import fcntl
import logging
import subprocess
import threading

import serial
from syspy import Trace
from syspy import RBK_VERSION
if RBK_VERSION == 3:
    from syspy.v3.protobuf.message.message_battery_pb2 import msgBattery
if RBK_VERSION == 4:
    from syspy.v4.protobuf.message.messageV4_battery_pb2 import MessageV4_Battery  as msgBattery

log = logging.getLogger("rbk.script")


class SerialNative:
    def __init__(self):
        Trace.log("SerialNative start!")
        self.ser = None
        self.__callback = None
        self.__should_close = False
        self.__msg_thread = None

    def createSerial(self, name, baudrate):
        self.ser = serial.Serial(port=name, baudrate=baudrate, bytesize=8, parity="N", stopbits=1)
        command = "cat /etc/srcname"
        output = subprocess.check_output(command, shell=True)
        output = output.decode("utf-8").strip()
        Trace.log(f"{output=}")
        if output in ['SRC800', 'SRC3000']:
            fcntl.ioctl(self.ser, 0)  # 这行决定了485模式
        self.__msg_thread = threading.Thread(target=self.__run, name="run")
        self.__msg_thread.start()
        Trace.log("createSerial  name:{},baudrate:{}".format(name, baudrate))
        
    def closeSerial(self):
        Trace.log("closeSerial")
        # if hasattr(self, 'ser') and self.ser and self.ser.is_open:
        try:
            self.stop()
            self.ser.close()
            Trace.log("serial port closed successfully.")
        except Exception as e:
            #Trace.log(f"exception: {e}")
            pass

        Trace.log("closeSerial done.")


    def send(self, msg: list):
        self.ser.write(msg)

    def recv(self):
        data = self.ser.read()
        if not self.__callback is None:
            self.__callback(data)

    def setCallBack(self, handleData):
        if not handleData:
            Trace.log("Set callback error.It should be implemented the func 'handleData'")
        else:
            self.__callback = handleData

    def createBatteryMessage(self):
        return msgBattery()

    def __run(self):
        try:
            while not self.__should_close:
                self.recv()
        except Exception as e:
            Trace.log("exception:", e)
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
