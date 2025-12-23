import logging
import can
import syspy.lib.misc_utility as mu
log = logging.getLogger("rbk.script")


class CanNative():
    def __init__(self):
        log.info("CanNative start!")
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
            log.error("Set callback error.")

    def __on_message_received(self, msg):
        log.debug(f"message received: {msg}")
        if msg is not None and self.__callback is not None:
            self.__callback(msg)

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
                log.warning(f"[CAN] Detected BUS-OFF state on {self.channel}, performing hard reset.")
                self.hard_reset_can()
    # unused filter cuz bus set_filters already done
    #  def can_filter(self, msg):
    #      return msg.arbitration_id in self.can_ids

    def attachCanID(self, *canid):
        self.can_ids.clear()
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
        log.info(f"Attached CAN IDs: {[hex(id) for id in self.can_ids]}")

    def resetBus(self):
        """重启 CAN 接口并重新创建 bus"""
        try:
            self.close()
        except Exception as e:
            log.warning("Failed to reset CAN bus: {e}")

        log.warning("[CAN] Resetting CAN interface due to tx buffer full")
        self.createCanBus(self.channel,self.bitrate)
        self.attachCanID(*self.can_ids)
        log.info(f'[CAN] Config Ok')
        
    def sendCanframe(self, channel, can_id, dlc, extend, can_string: list):
        if not self.bus:
            log.warning("please createCanBus first.")
            return
        try:
            self.bus.send(can.Message(arbitration_id=can_id, data=can_string, is_extended_id=extend, dlc=dlc))
            log.info(f'message send: {channel=}, {hex(can_id)=}, {dlc=}, {extend=}, {can_string=}')
        except can.CanError as e:
            log.error(f"Send failed: {e}")
            if "buffer" in str(e).lower():
                self.resetBus()
                log.info(f'please check can bus connection, the tx buffer is full due to unsuccess communication')

        

    def close(self):
        if self.notifier:
            self.notifier.stop()  # 停止 Notifier
        if self.bus:
            self.bus.shutdown()

    def __del__(self):
        self.close()  # 确保资源被正确清理


if __name__ == "__main__":
    pass
