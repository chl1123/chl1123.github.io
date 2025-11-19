import math
import typing
from typing import List

from syspy.core.rbk_rpc import call_service, Message

if typing.TYPE_CHECKING:
    from .protobuf import msgLaser3D


class LaserV3(Message):
    """激光类"""

    _TOPIC = "rbk.protocol.msgAllLasers"
    _PLUGIN = "MultiLaser"
    _MODEL_CLASS = None

    if typing.TYPE_CHECKING:
        from .protobuf import msgAllLasers
        data: msgAllLasers = None

    @classmethod
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import msgAllLasers
            cls._MODEL_CLASS = msgAllLasers

    @classmethod
    @call_service(plugin_name="SensorFuser")
    def set2DLaserWidth(cls, device_name: str, width: float):
        """设置激光设备宽度

        Args:
            device_name (str): 激光设备名称
            width (float): 屏蔽宽度，此范围外的点云被屏蔽
        """
        pass

    @classmethod
    @call_service(plugin_name="SensorFuser")
    def clear2DLaserWidth(cls, device_list: List[str]):
        """清除激光设备宽度
        
        Args:
            device_list (List[str]): 激光设备名称列表
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
        cls.client().call_service("SensorFuser", "set2DLaserAngle",
                                  device_name, math.radians(min_angle), math.radians(max_angle))

    @classmethod
    @call_service(plugin_name="SensorFuser")
    def clear2DLaserAngle(cls, device_list: List[str]):
        """清除激光设备角度
        
        Args:
            device_list (List[str]): 激光设备名称列表
        """
        pass

    #----------------------------------------------------#

    @classmethod
    @call_service(plugin_name="MoveFactory")
    def getNearestLaserPoint(cls, laser_key: str) -> List[float]:
        """获取与指定激光距离最近的激光点与激光中心的距离和朝向

        Args:
            laser_key (str): 激光设备的key

        Returns:
            List[float]: 最近激光点与激光中心的距离、最近激光点与激光中心的夹角
        """
        pass

    @classmethod
    @call_service(plugin_name="DSPChassis")
    def safeLaserMuteStatus(cls, laser_key: str) -> int:
        """获取激光抑制状态

        Args:
            laser_key (str)：激光设备的key。

        Returns:
            int: 激光状态，1表示启用，0表示禁用
        """
        pass

    @classmethod
    @call_service(plugin_name="MoveFactory")
    def setSafeLaserMute(cls, laser_key: str, enable: bool):
        """设置激光抑制(muting)

        Args:
            laser_key (str)：激光设备的key。""表示选择全部激光。
            enable (int)：表示是否启用激光muting，true启用，false禁用
        """
        pass


class Laser3DV3(Message):
    """激光类"""

    _TOPIC = "rbk.protocol.msgAllLasers3D"
    _PLUGIN = "MultiLaser"
    _MODEL_CLASS = None
    if typing.TYPE_CHECKING:
        from .protobuf import msgAllLasers3D, msgLaser3D
        data: msgAllLasers3D = None

    @classmethod
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import msgAllLasers3D
            cls._MODEL_CLASS = msgAllLasers3D

    def get_lasers3d(self) -> List["msgLaser3D"]:
        """获取所有3D激光数据列表

        Returns:
            List[msgLaser3D]: 返回所有3D激光数据的列表
        """
        if self.update():
            return self.data.lasers3D

