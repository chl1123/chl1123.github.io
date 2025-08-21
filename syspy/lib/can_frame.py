from abc import ABC
from syspy.core.rbk_rpc import Service, RBKVersionError


class CanInterface(ABC, Service):
    """CAN协议"""

    @classmethod
    def sendPassThroughCanFrame(cls, channel: int, can_id: int, dlc: int, extend: bool, can_string: str):
        """发送CAN帧

        Args:
            channel (int):
            can_id (int):
            dlc (int):
            extend (bool):
            can_string (str):
        """
        raise RBKVersionError()

    @classmethod
    def sendCanFrame(cls, channel: int, can_id: int, dlc: int, extend: bool, can_string: str):
        """发送CAN帧

        Args:
            channel (int):
            can_id (int):
            dlc (int):
            extend (bool):
            can_string (str):
        """
        raise RBKVersionError()

    @classmethod
    def canPassThroughRxId(cls, channel: int, id_nums: int, can_id1: int, can_id2: int, can_id3: int, can_id4: int,
                           can_id5: int) -> int:
        """检查CAN ID是否可以通过指定通道

        Args:
            channel (int):
            id_nums (int):
            can_id1 (int):
            can_id2 (int):
            can_id3 (int):
            can_id4 (int):
            can_id5 (int):

        Returns:
            int:
        """
        raise RBKVersionError()


from syspy.config import RBK_VERSION
if RBK_VERSION == 3:
    from syspy.v3.lib.can_frame import CanV3
    Can: CanInterface = CanV3()
elif RBK_VERSION == 4:
    from syspy.v4.lib.can_frame import CanV4
    Can: CanInterface = CanV4()
else:
    raise ValueError(f"Unsupported RBK version: {RBK_VERSION}")
