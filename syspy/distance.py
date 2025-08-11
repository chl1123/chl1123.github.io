from abc import ABC
from syspy.core.rbk_rpc import Message

class DistanceInterface(ABC, Message):
    """距离传感器类"""
    pass


from syspy.config import rbk_version
if rbk_version == 3:
    from syspy.v3.distance import DistanceV3
    Distance: DistanceInterface = DistanceV3()
elif rbk_version == 4:
    from syspy.v4.distance import DistanceV4
    Distance: DistanceInterface = DistanceV4()
else:
    raise ValueError(f"Unsupported RBK version: {rbk_version}")
