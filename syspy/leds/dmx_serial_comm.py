import time

import serial

from syspy.comms.serial_comm import SerialComm


class DmxSerialComm(SerialComm):
    def __init__(self, port, baudrate=256000):
        super().__init__(port, baudrate)

    def open(self):
        if super().open():
            self.serial.stopbits = serial.STOPBITS_TWO
            self.serial.timeout = 1
            self.serial.write_timeout = 1
            return True
        return False

    def send(self, data):
        if self.serial is None or not self.serial.isOpen():
            print("Port is not open")
            return
        try:
            self.serial.break_condition = True  # TIOCSBRK equivalent
            time.sleep(0.005)
            self.serial.break_condition = False  # TIOCCBRK equivalent
            time.sleep(0.001)
            bytes_written = self.serial.write(data)
            if bytes_written == len(data):
                return
            else:
                self.serial.reset_output_buffer()
                return
        except serial.SerialException as e:
            print(f"Error writing to serial port: {e}")

    def close(self):
        super().close()


if __name__ == "__main__":
    dmx = DmxSerialComm("/dev/ttyS5", 32000)
    if dmx.open():  # Replace with your serial port
        print("open ok")
        while True:
            data = [0, 0, 0, 0, 255, 0, 0, 0, 255, 0, 0, 0, 255, 0, 0, 0, 255]  # Example data
            print("data=", data)
            dmx.send(bytearray(data))
            time.sleep(0.1)
    dmx.close()
