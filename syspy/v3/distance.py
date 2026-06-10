from syspy.distance import DistanceInterface

class DistanceV3(DistanceInterface):
    """距离传感器类"""

    _TOPIC = "rbk.protocol.msgDistanceSensor"
    _PLUGIN = "DSPChassis"
    _MODEL_CLASS = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf.message.message_distancesensor_pb2 import msgDistanceSensor
            cls._MODEL_CLASS = msgDistanceSensor
