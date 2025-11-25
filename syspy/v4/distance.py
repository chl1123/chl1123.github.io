from syspy.distance import DistanceInterface

class DistanceV4(DistanceInterface):
    """距离传感器类"""
    _TOPIC = ""  # todo RBK4
    _MODEL_CLASS = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from syspy.v4.protobuf.message.messageV4_sensor_pb2 import MessageV4_DistanceSensor
            cls._MODEL_CLASS = MessageV4_DistanceSensor
