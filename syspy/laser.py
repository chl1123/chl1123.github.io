import math
import typing
from typing import List

from .lib.py_rpc import Message, call_service

if typing.TYPE_CHECKING:
    from .protobuf import Message_Laser3D


class Laser(Message["Message_AllLasers"]):
    """激光类"""

    _TOPIC = "rbk.protocol.Message_AllLasers"
    _PLUGIN = "MultiLaser"
    _MODEL_CLASS = None

    @classmethod
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import Message_AllLasers
            cls._MODEL_CLASS = Message_AllLasers

    @classmethod
    @call_service(plugin_name="Perception")
    def addDisableLaserStrName(cls, ids: list):
        """禁用多个指定名字的激光雷达

        Args:
            ids (List(str)): 指定的激光雷达id列表
        """
        pass

    @classmethod
    @call_service(plugin_name="Perception")
    def clearDisableLaserStrName(cls):
        """清除禁用的激光"""
        pass

    @classmethod
    def setLaserAngle(cls, id: int, min_angle: float, max_angle: float):
        """设置激光角度

        Args:
            id (int):
            min_angle (float): 最小角度（单位：°）
            max_angle (float): 最大角度（单位：°）
        """
        cls.client().call_service("Perception", "setLaserAngle",
                                  (id, math.radians(min_angle), math.radians(max_angle)))

    @classmethod
    @call_service(plugin_name="Perception")
    def clearLaserAngle(cls):
        """清除激光角度"""
        pass

    @classmethod
    @call_service(plugin_name="Perception")
    def setLaserWidth(cls, id: int, width: float):
        """设置激光宽度

        Args:
            id (int):
            width (float):
        """
        pass

    @classmethod
    @call_service(plugin_name="Perception")
    def clearLaserWidth(cls):
        """清除激光宽度"""
        pass

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
    @call_service()
    def safeLaserMuteStatus(cls) -> str:
        """

        Returns:
            str:
        """
        pass

    @classmethod
    @call_service()
    def setSafeLaserMute(cls, id: int, enable: bool):
        """

        Args:
            id:
            enable:
        """
        pass


class Laser3D(Message["Message_AllLasers3D"]):
    """激光类"""

    _TOPIC = "rbk.protocol.Message_AllLasers3D"
    _PLUGIN = "MultiLaser"
    _MODEL_CLASS = None

    @classmethod
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import Message_AllLasers3D
            cls._MODEL_CLASS = Message_AllLasers3D

    @classmethod
    def get_lasers3d(cls) -> List["Message_Laser3D"]:
        """获取所有3D激光数据列表

        Returns:
            List[Message_Laser3D]: 返回所有3D激光数据的列表
        """
        if cls.update():
            return cls.data.lasers3d
