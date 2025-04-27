import syspy.lib.pass_through as pt
from syspy import Can
from syspy.protobuf.message import CanFrame_pb2, message_battery_pb2

DEFAULT_PASS_ADDR = "ipc:///tmp/CanPass_udp.ipc"
import logging

log = logging.getLogger("rbk.script")


class canPassX86():
    def __init__(self):
        log.info("canPassX86 start!")
        self.__pass = pt.passThrough()
        self.__pass.canConnect(DEFAULT_PASS_ADDR, "ECanFrame_pass_py")

    def setCallBack(self, handleData):
        if not handleData:
            log.error("Set callback error.It should be implemented the func 'handleData'")
        else:
            self.__pass.setCallBack(handleData)

    def createBatteryMessage(self):
        return message_battery_pb2.Message_Battery()

    def recCanframe(self, msg):
        """
        接收信息并转化为can类型
        """
        rec_canframe = CanFrame_pb2.CanFrame()
        rec_canframe.ParseFromString(msg)
        return rec_canframe

    def sendCanframe(self, channel, can_id, dlc, extend, can_string):
        log.info(
            f'message send: {channel=}, {hex(can_id)=}, {dlc=}, {extend=}, {can_string=}')
        Can.sendPassThroughCanFrame(channel, can_id, dlc, extend, can_string)

    def attachCanID(self, channel, id_nums, *canid):
        can_ids = []
        for i in range(min(len(canid), 5)):
            can_ids.append(canid[i])
        can_id1, can_id2, can_id3, can_id4, can_id5 = can_ids + [0] * (5 - len(can_ids))
        log.info(f'{channel=}, {id_nums=}, {hex(can_id1)=}, {hex(can_id2)=}, {hex(can_id3)=}')
        Can.canPassThroughRxId(channel, id_nums, can_id1, can_id2, can_id3, can_id4, can_id5)
        log.info(f"Attached CAN IDs: {[hex(id_) for id_ in can_ids]}")

    def __del__(self):
        if self.__pass:
            try:
                self.__pass.shoutDown()
            except Exception as e:
                log.error(f"Error shutting down passThrough: {e}")


if __name__ == "__main__":
    pass
