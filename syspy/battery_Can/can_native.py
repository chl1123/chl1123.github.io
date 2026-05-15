import logging
import can
import syspy.lib.misc_utility as mu
from syspy import Trace
log = logging.getLogger("rbk.script")


class _CanFrameAdapter:
    __slots__ = ('id', 'data')

    def __init__(self, msg):
        self.id = msg.arbitration_id
        self.data = msg.data


class CanNative():
    def __init__(self):
        Trace.log("CanNative start!")
        self.bus = None
        self.__callback = None
        self.can_ids = []
        self.notifier = None
        self.channel = None
        self.bitrate = None
        self.bus_guardT = mu.Timer(1000)

    def setCallBack(self, handleData):
        if callable(handleData):
            self.__callback = handleData
        else:
            Trace.log("Set callback error.")

    def __on_message_received(self, msg):
        log.debug(f"message received: {msg}")
        if msg is not None and self.__callback is not None:
            self.__callback(msg)

    def recCanframe(self, msg):
        return _CanFrameAdapter(msg)

    def createCanBus(self, channel, bitrate):
        self.channel = channel
        self.bitrate = bitrate
        self.bus = can.interface.Bus(bustype='socketcan', channel=self.channel, bitrate=self.bitrate, receive_own_messages=False)
        self.notifier = can.Notifier(self.bus, [self.__on_message_received], timeout=5)
    
    
    def is_bus_off(self):
        import subprocess
        try:
            out = subprocess.check_output(
                ["ip", "-details", "link", "show", self.channel],
                text=True
            )
            return "BUS-OFF" in out
        except Exception:
            return False
    
    def hard_reset_can(self):
        import subprocess, time
        subprocess.call(["ip", "link", "set", self.channel, "down"])
        time.sleep(0.1)
        subprocess.call([
            "ip", "link", "set", self.channel, "up",
            "type", "can", "bitrate", str(self.bitrate)
        ])
    
    def check_and_reset_bus(self):
        if self.bus_guardT.isTimeUp():
            self.bus_guardT.reset()
            if self.is_bus_off():
                Trace.log(f"[CAN] Detected BUS-OFF state on {self.channel}, performing hard reset.")
                self.hard_reset_can()
    # unused filter cuz bus set_filters already done
    #  def can_filter(self, msg):
    #      return msg.arbitration_id in self.can_ids

    def _extract_attach_ids(self, *canid):
        # Accept passthrough-style (channel, id_nums, *ids), unified-style (port_str, id_nums, *ids), and native-style (*ids)
        if len(canid) >= 2 and isinstance(canid[0], int) and canid[0] < 3 and isinstance(canid[1], int) and 1 <= canid[1] <= 5:
            return canid[2:]
        if len(canid) >= 2 and isinstance(canid[0], str) and isinstance(canid[1], int):
            return canid[2:]
        return canid

    def attachCanID(self, *canid):
        ids = self._extract_attach_ids(*canid)
        for raw_id in ids:
            if raw_id != 0 and raw_id not in self.can_ids:
                self.can_ids.append(raw_id)
        filters = []
        for raw_id in self.can_ids:
            is_extended = (raw_id & 0x80000000) != 0
            is_remote = (raw_id & 0x40000000) != 0
            can_id = raw_id & 0x1FFFFFFF
            if can_id == 0:
                continue

            if is_extended or can_id > 0x7FF:
                can_mask = 0xDFFFFFFF if is_remote else 0x9FFFFFFF
                filter_item = {"can_id": can_id | 0x80000000, "can_mask": can_mask, "extended": True}
            else:
                can_mask = 0xC00007FF if is_remote else 0x800007FF
                filter_item = {"can_id": can_id, "can_mask": can_mask, "extended": False}

            if is_remote:
                filter_item["can_id"] |= 0x40000000
            filters.append(filter_item)

        self.bus.set_filters(filters)
        Trace.log(f"Attached CAN IDs: {[hex(raw_id) for raw_id in self.can_ids]}")


    def resetBus(self):
        """重启 CAN 接口并重新创建 bus"""
        try:
            self.close()
        except Exception as e:
             Trace.log("Failed to reset CAN bus: {e}")

        Trace.log("[CAN] Resetting CAN interface due to tx buffer full")
        self.createCanBus(self.channel,self.bitrate)
        self.attachCanID(*tuple(self.can_ids))
        Trace.log(f'[CAN] Config Ok')
        
    def sendCanframe(self, channel, can_id, dlc, extend, can_string):
        if not self.bus:
            Trace.log("please createCanBus first.")
            return
        if isinstance(can_string, str):
            can_string = [int(b, 16) for b in can_string.split()]
        try:
            self.bus.send(can.Message(arbitration_id=can_id, data=can_string, is_extended_id=extend, dlc=dlc))
            Trace.log(f'message send: {channel=}, {hex(can_id)=}, {dlc=}, {extend=}, {can_string=}')
        except can.CanError as e:
            Trace.log(f"Send failed: {e}")
            if "buffer" in str(e).lower():
                self.resetBus()
                Trace.log(f'please check can bus connection, the tx buffer is full due to unsuccess communication')

        

    def close(self):
        if self.notifier:
            self.notifier.stop()  # 停止 Notifier
        if self.bus:
            self.bus.shutdown()

    def __del__(self):
        self.close()  # 确保资源被正确清理


if __name__ == "__main__":
    pass
