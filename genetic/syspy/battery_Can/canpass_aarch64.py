import sys,can,threading
import syspy.lib.udp_debug as ud
sys.path.append('/usr/local/etc/.SeerRobotics/rbk/resources/scripts/genetic/syspy/protobuf')
sys.path.append('/usr/local/etc/.SeerRobotics/rbk/resources/scripts/site-packages')
import message_battery_aarch64_pb2

class canPassAarch64():
    def __init__(self):
        print("canPassAarch64 start!")
        self.bus = None
        self.__callback = None
        self.__should_close = threading.Event()  # 使用事件来控制线程关闭
        self.can_ids = []
        self.__msg_thread = None
        self.__debug_out = ud.udpDebug()
        sys.stdout = self.__debug_out

    def setCallBack(self, handleData):
        if callable(handleData):
            self.__callback = handleData
        else:
            print("Set callback error.")

    def createBatteryMessage(self):
        return message_battery_aarch64_pb2.Message_Battery()

    def createCanBus(self, channel, bitrate):
        self.bus = can.interface.Bus(bustype='socketcan', channel=channel, bitrate=bitrate)
        self.__msg_thread = threading.Thread(target=self.__run, name="run")
        self.__msg_thread.start()  # FIXME: when to join?

    def can_filter(self, msg):
        return msg.arbitration_id in self.can_ids

    def attachCanID(self, *canid):
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
        print('Attached CAN IDs:', end=' ')
        for id_ in self.can_ids:
            print(hex(id_), end=' ')

    def sendCanframe(self, channel, can_id, dlc, extend, can_string: list):
        bus = can.interface.Bus(channel, bustype='socketcan')
        try:
            msg = can.Message(arbitration_id=can_id, data=can_string, is_extended_id=extend, dlc=dlc)
            bus.send(msg)
            print(f'message send: channel={channel}, can_id={hex(can_id)}, dlc={dlc}, extend={extend}, can_string={can_string}')
        finally:
            bus.shutdown()

    def recvCan(self):
        msg = self.bus.recv(1.0)  # 设置超时时间
        if msg and self.can_filter(msg):
            if not self.__callback is None:
                self.__callback(msg)

    def __run(self):
        try:
            while not self.__should_close.is_set():
                self.recvCan()
        except Exception as e:
            print("recvCan exception:", e)
        finally:
            self.bus.shutdown()  # 确保总线关闭

    def close(self):
        self.__should_close.set()  # 设置事件，通知线程关闭
        self.__msg_thread.join()  # 等待线程结束

    def __del__(self):
        self.close()  # 确保资源被正确清理

if __name__ == "__main__":
    pass

