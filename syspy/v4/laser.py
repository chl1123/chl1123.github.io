import math
import typing
from typing import List

from syspy.core.rbk_rpc import call_service, Message

if typing.TYPE_CHECKING:
    from syspy.v4.protobuf.message.messageV4_laser_pb2 import MessageV4_Laser, MessageV4_Laser3D


class LaserV4(Message):
    """激光类"""

    _MODEL_CLASS = None

    def __init__(self, topic=None):
        self._TOPIC = topic

    @classmethod
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            cls._MODEL_CLASS = MessageV4_Laser

    @classmethod
    @call_service(plugin_name="SensorFuser")  # todo RBK4 App名
    def set2DLaserWidth(cls, device_name: str, width: float):
        """设置激光设备宽度

        Args:
            device_name (str): 激光设备名称
            width (float): 屏蔽宽度，此范围外的点云被屏蔽
        """
        pass

    @classmethod
    @call_service(plugin_name="SensorFuser")  # todo RBK4 App名
    def clear2DLaserWidth(cls, device_list: List[str]):
        """清除激光设备宽度
        
        Args:
            device_name (str): 激光设备名称列表
        """
        pass

    @classmethod
    def set2DLaserAngle(cls, device_name: str, min_angle: float, max_angle: float):
        """设置激光设备角度

        Args:
            device_name (str): 激光设备名称
            min_angle (float): 最小角度（单位：°），小于此角度的点云被屏蔽
            max_angle (float): 最大角度（单位：°），大于此角度的点云被屏蔽
        """
        # todo RBK4 App名
        cls.client().call_service("SensorFuser", "set2DLaserAngle",
                                  device_name=device_name, min_angle=math.radians(min_angle), max_angle=math.radians(max_angle))

    @classmethod
    @call_service(plugin_name="SensorFuser")  # todo RBK4 App名
    def clear2DLaserAngle(cls, device_list: List[str]):
        """清除激光设备角度
        
        Args:
            device_name (str): 激光设备名称列表
        """
        pass

    #----------------------------------------------------#

    @classmethod
    @call_service(plugin_name="MoveFactory")  # todo RBK4 App名
    def getNearestLaserPoint(cls, laser_key: str) -> List[float]:
        """获取与指定激光距离最近的激光点与激光中心的距离和朝向

        Args:
            laser_key (str): 激光设备的key

        Returns:
            List[float]: 最近激光点与激光中心的距离、最近激光点与激光中心的夹角
        """
        pass

    @classmethod
    @call_service(plugin_name="DSPChassis")  # todo RBK4 App名
    def safeLaserMuteStatus(cls, laser_key: str) -> int:
        """获取激光抑制状态

        Args:
            laser_key (str)：激光设备的key。

        Returns:
            int: 激光状态，1表示启用，0表示禁用
        """
        pass

    @classmethod
    @call_service(plugin_name="MoveFactory")  # todo RBK4 App名
    def setSafeLaserMute(cls, laser_key: str, enable: bool):
        """设置激光抑制(muting)

        Args:
            laser_key (str)：激光设备的key。""表示选择全部激光。
            enable (int)：表示是否启用激光muting，true启用，false禁用
        """
        pass


class Laser3DV4(Message):
    """激光类"""

    _MODEL_CLASS = None
    def __init__(self, topic=None):
        self._TOPIC = topic

    @classmethod
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            cls._MODEL_CLASS = MessageV4_Laser3D

    def get_lasers3d(self) -> List["Message_Laser3D"]:
        """获取所有3D激光数据列表

        Returns:
            List[Message_Laser3D]: 返回所有3D激光数据的列表
        """
        if self.update():
            return self.data.lasers3d

