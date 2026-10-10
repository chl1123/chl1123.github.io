import threading
import can
from comm import Communication

from syspy.lib.trace import Trace


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
            Trace.log(f"Opening CAN bus on {self.channel} with bitrate {self.bitrate}", name="syspy.can")
            self.bus = can.interface.Bus(bustype='socketcan', channel=self.channel, bitrate=self.bitrate)
            Trace.log(f"CAN bus on {self.channel} opened successfully.", name="syspy.can")
        except can.CanError as e:
            Trace.log(f"Error opening CAN bus: {e}", name="syspy.can.err")
            return False

    def close(self):
        if self.bus is not None:
            self.__should_close.set()
            self.bus.shutdown()
            Trace.log(f"CAN bus on {self.channel} closed.", name="syspy.can")

    def send(self, message: can.Message):
        if self.bus is not None:
            try:
                self.bus.send(message)
                Trace.log(f"Message sent: {message}", name="syspy.can")
            except can.CanError as e:
                Trace.log(f"Error sending message: {e}", name="syspy.can.err")

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
        Trace.log(f"Attached CAN IDs: {[hex(id_) for id_ in self.can_ids]}", name="syspy.can")

    def can_filter(self, msg):
        return msg.arbitration_id in self.can_ids