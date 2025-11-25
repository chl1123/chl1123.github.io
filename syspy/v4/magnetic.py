import typing
from syspy.magnetic import MagneticInterface


class MagneticV4(MagneticInterface):
    """磁传感器类"""

    _TOPIC = ""  # todo RBK4
    _MODEL_CLASS = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from syspy.v4.protobuf.message.messageV4_magnetic_pb2 import MessageV4_Magnetic
            cls._MODEL_CLASS = MessageV4_Magnetic

    def getMagnetics(self) -> typing.List["MessageV4_MagneticNode"]:
        """获取磁节点列表

        Returns:
            typing.List[MessageV4_MagneticNode]: 包含所有磁节点信息的列表
        """
        if self.update():
            return self.data.magnetic_nodes