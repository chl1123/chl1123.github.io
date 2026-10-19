from abc import ABC
from typing import List, Optional

from syspy.core.rbk_rpc import Message, RBKVersionError


class DistanceInterface(ABC, Message):
    """距离传感器类"""

    def getDistances(self, device_key: str = None) -> Optional[List]:
        """获取距离传感器节点列表

        Args:
            device_key (str): 距离传感器设备 key；缺省时合并全部设备。

        Returns:
            (Optional[List]): 距离节点列表；无数据时返回 None。

        Compatibility:
            仅 RBK 3 支持；RBK 4 未实现。
        """
        raise RBKVersionError()

    def getData(self, fields=None, *, device_key: str = None) -> list:
        """兼容式读取：返回距离节点列表（无数据时为空列表）。"""
        raise RBKVersionError()


from syspy import RBK_VERSION
if RBK_VERSION == 3:
    from syspy.v3.distance import DistanceV3
    Distance: DistanceInterface = DistanceV3()
elif RBK_VERSION == 4:
    from syspy.v4.distance import DistanceV4
    Distance: DistanceInterface = DistanceV4()
else:
    raise ValueError(f"Unsupported RBK version: {RBK_VERSION}")
