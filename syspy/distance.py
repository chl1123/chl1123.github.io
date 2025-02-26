from .lib.py_rpc import Message
from .protobuf.message import Message_DistanceSensor


class Distance(Message[Message_DistanceSensor]):
    """距离传感器类"""

    _TOPIC = "rbk.protocol.Message_DistanceSensor"
    _PLUGIN = "DSPChassis"
    _MODEL_CLASS = Message_DistanceSensor
