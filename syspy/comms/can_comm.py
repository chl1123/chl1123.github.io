import threading
import can
from comm import Communication


class CanComm(Communication):
    def __init__(self, channel: str, bitrate: int, can_ids: tuple):
        self.channel = channel
        self.bitrate = bitrate
        self.bus = None
        self.__should_close = threading.Event()
        self.can_ids = []
        self.attach_can_ids(*can_ids)

    def open(self):
        try:
            print(f"Opening CAN bus on {self.channel} with bitrate {self.bitrate}")
            self.bus = can.interface.Bus(bustype='socketcan', channel=self.channel, bitrate=self.bitrate)
            print(f"CAN bus on {self.channel} opened successfully.")
        except can.CanError as e:
            print(f"Error opening CAN bus: {e}")
            return False

    def close(self):
        if self.bus is not None:
            self.__should_close.set()
            self.bus.shutdown()
            print(f"CAN bus on {self.channel} closed.")

    def send(self, message: can.Message):
        if self.bus is not None:
            try:
                self.bus.send(message)
                print(f"Message sent: {message}")
            except can.CanError as e:
                print(f"Error sending message: {e}")

    def recv(self):
        if self.bus is not None:
            msg = self.bus.recv(1.0)  # 设置超时时间为1秒
            if msg and self.can_filter(msg):
                return msg
        return None

    def attach_can_ids(self, *canids):
        for i in range(len(canids)):
            self.can_ids.append(canids[i])
        filters = []
        for id_ in self.can_ids:
            if id_ < 0x800:
                can_mask = 0x7FF
            else:
                can_mask = 0x1FFFFFFF
            filters.append({"can_id": id_, "can_mask": can_mask})
        self.bus.set_filters(filters)
        print('Attached CAN IDs:', end=' ')
        for id_ in self.can_ids:
            print(hex(id_), end=' ')

    def can_filter(self, msg):
        return msg.arbitration_id in self.can_ids