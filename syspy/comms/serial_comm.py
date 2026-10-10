import fcntl
import subprocess

import serial

from syspy.comms.comm import Communication
from syspy.lib.trace import Trace


class SerialComm(Communication):
    def __init__(self, port, baudrate):
        self.port = port
        self.baudrate = baudrate
        self.serial = None

    def __del__(self):
        self.close()

    def open(self):
        if self.serial is not None and self.serial.isOpen():
            return True
        try:
            Trace.log(f"Opening serial port {self.port}, {self.baudrate}", name="syspy.serial")
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,  # 波特率
                bytesize=serial.EIGHTBITS,  # 数据位
                parity=serial.PARITY_NONE,  # 奇偶校验
                stopbits=serial.STOPBITS_ONE  # 停止位
            )
            command = "cat /etc/srcname"
            output = subprocess.check_output(command, shell=True)
            output = output.decode("utf-8").strip()
            Trace.log(f"SRC name: {output}", name="syspy.serial")
            if output in ['SRC800', 'SRC3000']:
                fcntl.ioctl(self.serial, 0)  # 这行决定了485模式
            Trace.log(f"Serial port {self.port} opened successfully.", name="syspy.serial")
            return True
        except serial.SerialException as e:
            Trace.log(f"Error opening serial port: {e}", name="syspy.serial.err")
            return False

    def close(self):
        if self.serial is not None and self.serial.isOpen():
            try:
                self.serial.close()
            except serial.SerialException as e:
                Trace.log(f"Error closing serial port: {e}", name="syspy.serial.err")
                return False
        return True

    def send(self, message: list):
        if self.serial is not None and self.serial.isOpen():
            self.serial.write(message)

    def recv(self):
        if self.serial is not None and self.serial.isOpen():
            return self.serial.read()
        return None
