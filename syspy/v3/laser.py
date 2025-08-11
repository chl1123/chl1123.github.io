import math
import typing
from typing import List

from syspy.core.rbk_rpc import call_service, Message
from .. import rbk_version

if typing.TYPE_CHECKING:
    from .protobuf import Message_Laser3D


class LaserV3(Message):
    """激光类"""

    _TOPIC = "rbk.protocol.Message_AllLasers"
    _PLUGIN = "MultiLaser"
    _MODEL_CLASS = None

    if typing.TYPE_CHECKING:
        from .protobuf import Message_AllLasers
        data: Message_AllLasers = None

    @classmethod
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import Message_AllLasers
            cls._MODEL_CLASS = Message_AllLasers

    @classmethod
    @call_service(plugin_name="SensorFuser")
    def addDisableLaser(cls, device_name: str):
        """禁用激光设备

        Args:
            device_name (str): 激光设备名称
        """
        pass

    @classmethod
    @call_service(plugin_name="SensorFuser")
    def eraseDisableLaser(cls, device_name: str):
        """清除已禁用的激光设备

        Args:
            device_name (str): 激光设备名称
        """
        pass

    @classmethod
    @call_service(plugin_name="SensorFuser")
    def clearDisableLaserAll(cls):
        """清除所有已禁用的激光设备"""
        pass

    @classmethod
    @call_service(plugin_name="SensorFuser")
    def setLaserWidth(cls, device_name: str, width: float):
        """设置激光设备宽度

        Args:
            device_name (str): 激光设备名称
            width (float): 屏蔽宽度，此范围外的点云被屏蔽
        """
        pass

    @classmethod
    @call_service(plugin_name="SensorFuser")
    def clearLaserWidth(cls):
        """清除激光设备宽度"""
        pass

    @classmethod
    def setLaserAngle(cls, device_name: str, min_angle: float, max_angle: float):
        """设置激光设备角度

        Args:
            device_name (str): 激光设备名称
            min_angle (float): 最小角度（单位：°），小于此角度的点云被屏蔽
            max_angle (float): 最大角度（单位：°），大于此角度的点云被屏蔽
        """
        cls.client().call_service("SensorFuser", "setLaserAngle",
                                  (id, math.radians(min_angle), math.radians(max_angle)))

    @classmethod
    @call_service(plugin_name="SensorFuser")
    def clearLaserAngle(cls):
        """清除激光设备角度"""
        pass

    @classmethod
    @call_service(plugin_name="SensorFuser")
    def addDisableDepthCamera(cls, device_name: str):
        """禁用深度相机

        Args:
            device_name (str): 深度相机名称
        """
        pass

    @classmethod
    @call_service(plugin_name="SensorFuser")
    def eraseDisableDepthCamera(cls, device_name: str):
        """清除已禁用的深度相机

        Args:
            device_name (str): 深度相机名称
        """
        pass

    @classmethod
    @call_service(plugin_name="SensorFuser")
    def clearDisableDepthCameraAll(cls):
        """清除所有已禁用的深度相机"""
        pass

    #----------------------------------------------------#


    @classmethod
    @call_service(plugin_name="Perception")
    def sensorPointCloud(cls) -> dict:
        """获得后视激光点云信息以字典类型返回

        Returns:
            dict: 具体的任务信息
        """
        pass

    @classmethod
    @call_service(plugin_name="MoveFactory")
    def getNearestLaserPoint(cls, laser_id: int) -> List[float]:
        """获取与指定激光距离最近的激光点与激光中心的距离和朝向

        Args:
            laser_id (int): 激光 id 号

        Returns:
            List[float]: 最近激光点与激光中心的距离、最近激光点与激光中心的夹角
        """
        pass

    @classmethod
    @call_service(plugin_name="MoveFactory")
    def safeLaserMuteStatus(cls) -> str:
        """

        Returns:
            str:
        """
        pass

    @classmethod
    @call_service(plugin_name="MoveFactory")
    def setSafeLaserMute(cls, id: int, enable: bool):
        """

        Args:
            id:
            enable:
        """
        pass


class Laser3DV3(Message):
    """激光类"""

    _TOPIC = "rbk.protocol.Message_AllLasers3D"
    _PLUGIN = "MultiLaser"
    _MODEL_CLASS = None
    if typing.TYPE_CHECKING:
        from .protobuf import Message_AllLasers3D
        data: Message_AllLasers3D = None

    @classmethod
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import Message_AllLasers3D
            cls._MODEL_CLASS = Message_AllLasers3D

    def get_lasers3d(self) -> List["Message_Laser3D"]:
        """获取所有3D激光数据列表

        Returns:
            List[Message_Laser3D]: 返回所有3D激光数据的列表
        """
        if self.update():
            return self.data.lasers3d

