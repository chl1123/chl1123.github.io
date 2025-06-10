import fcntl
import subprocess

import serial

from syspy.comms.comm import Communication


class SerialComm(Communication):
    def __init__(self, port, baudrate):
        self.port = port
        self.baudrate = baudrate
        self.serial = None

    def __del__(self):
        print("SerialComm.__del__")
        self.close()

    def open(self):
        if self.serial is not None and self.serial.isOpen():
            return True
        try:
            print(f"Opening serial port {self.port}, {self.baudrate}")
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
            print("SRC name: ", output)
            if output not in ['SRC880', 'SRC1000', "SRC1100", "SRCF10", "SRCR10"]:
                fcntl.ioctl(self.serial, 0)  # 这行决定了485模式
            print(f"Serial port {self.port} opened successfully.")
            return True
        except serial.SerialException as e:
            print(f"Error opening serial port: {e}")
            return False

    def close(self):
        if self.serial is not None and self.serial.isOpen():
            try:
                self.serial.close()
            except serial.SerialException as e:
                print(f"Error closing serial port: {e}")
                return False
        return True

    def send(self, message: list):
        if self.serial is not None and self.serial.isOpen():
            self.serial.write(message)

    def recv(self):
        if self.serial is not None and self.serial.isOpen():
            return self.serial.read()
        return None
