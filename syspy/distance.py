from abc import ABC
from syspy.core.rbk_rpc import Message

class DistanceInterface(ABC, Message):
    """距离传感器类"""
    pass


from syspy import RBK_VERSION
if RBK_VERSION == 3:
    from syspy.v3.distance import DistanceV3
    Distance: DistanceInterface = DistanceV3()
elif RBK_VERSION == 4:
    from syspy.v4.distance import DistanceV4
    Distance: DistanceInterface = DistanceV4()
else:
    raise ValueError(f"Unsupported RBK version: {RBK_VERSION}")
