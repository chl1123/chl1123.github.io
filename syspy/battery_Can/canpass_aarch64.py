import logging
import threading

import can

log = logging.getLogger("rbk.script")


class canPassAarch64():
    def __init__(self):
        log.info("canPassAarch64 start!")
        self.bus = None
        self.__callback = None
        self.__should_close = threading.Event()  # 使用事件来控制线程关闭
        self.can_ids = []
        self.__msg_thread = None
        self.bus_dict = {}  # 用于存储不同通道的Bus对象

    def setCallBack(self, handleData):
        if callable(handleData):
            self.__callback = handleData
        else:
            log.error("Set callback error.")

    def createCanBus(self, channel, bitrate):
        self.bus = can.interface.Bus(bustype='socketcan', channel=channel, bitrate=bitrate, receive_own_messages=False)
        self.__msg_thread = threading.Thread(target=self.__run, name="run", daemon=True)
        self.__msg_thread.start()

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

    def sendCanframe(self, channel, can_id, dlc, extend, can_string: list):
        if not self.bus:
            log.warning("please createCanBus first.")
            return
        self.bus.send(can.Message(arbitration_id=can_id, data=can_string, is_extended_id=extend, dlc=dlc))
        log.info(f'message send: {channel=}, {hex(can_id)=}, {dlc=}, {extend=}, {can_string=}')

    def __run(self):
        try:
            while not self.__should_close.is_set():
                msg = self.bus.recv(timeout=5)  # 使用超时来避免阻塞
                if msg is not None and self.__callback is not None:
                    self.__callback(msg)
        except Exception as e:
            print("recvCan exception:", e)
        finally:
            self.bus.shutdown()  # 确保总线关闭

    def close(self):
        self.__should_close.set()  # 设置事件，通知线程关闭
        if self.__msg_thread is not None:
            self.__msg_thread.join()  # 等待线程结束

    def __del__(self):
        self.close()  # 确保资源被正确清理


if __name__ == "__main__":
    pass
