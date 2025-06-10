from .lib.py_rpc import Message


class Distance(Message["Message_DistanceSensor"]):
    """距离传感器类"""

    _TOPIC = "rbk.protocol.Message_DistanceSensor"
    _PLUGIN = "DSPChassis"
    _MODEL_CLASS = None

    @classmethod
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import Message_DistanceSensor
            cls._MODEL_CLASS = Message_DistanceSensor
