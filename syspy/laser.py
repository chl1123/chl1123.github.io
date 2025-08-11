import typing
from typing import List
from syspy import rbk_version

if typing.TYPE_CHECKING:
    if rbk_version == 3:
        from syspy.v3.protobuf import Message_Laser3D
    elif rbk_version == 4:
        pass


class LaserInterface:
    """激光类"""

    def __init__(self, topic=None):
        if rbk_version == 3:
            from syspy.v3.laser import LaserV3
            self.child = LaserV3()
        elif rbk_version == 4:
            from syspy.v4.laser import LaserV4
            self.child = LaserV4(topic)
        else:
            raise ValueError(f"Unsupported RBK version: {rbk_version}")

    def addDisableLaser(cls, device_name: str):
        """禁用激光设备

        Args:
            device_name (str): 激光设备名称
        """
        cls.child.addDisableLaser(device_name)

    def eraseDisableLaser(cls, device_name: str):
        """清除已禁用的激光设备

        Args:
            device_name (str): 激光设备名称
        """
        cls.child.eraseDisableLaser(device_name)

    def clearDisableLaserAll(cls):
        """清除所有已禁用的激光设备"""
        cls.child.clearDisableLaserAll()

    def setLaserWidth(cls, device_name: str, width: float):
        """设置激光设备宽度

        Args:
            device_name (str): 激光设备名称
            width (float): 屏蔽宽度，此范围外的点云被屏蔽
        """
        cls.child.setLaserWidth(device_name, width)

    def clearLaserWidth(cls):
        """清除激光设备宽度"""
        cls.child.clearLaserWidth()

    def setLaserAngle(cls, device_name: str, min_angle: float, max_angle: float):
        """设置激光设备角度

        Args:
            device_name (str): 激光设备名称
            min_angle (float): 最小角度（单位：°），小于此角度的点云被屏蔽
            max_angle (float): 最大角度（单位：°），大于此角度的点云被屏蔽
        """
        cls.child.setLaserAngle(device_name, min_angle, max_angle)

    def clearLaserAngle(cls):
        """清除激光设备角度"""
        cls.child.clearLaserAngle()

    def addDisableDepthCamera(cls, device_name: str):
        """禁用深度相机

        Args:
            device_name (str): 深度相机名称
        """
        cls.child.addDisableDepthCamera(device_name)

    def eraseDisableDepthCamera(cls, device_name: str):
        """清除已禁用的深度相机

        Args:
            device_name (str): 深度相机名称
        """
        cls.child.eraseDisableDepthCamera(device_name)

    def clearDisableDepthCameraAll(cls):
        """清除所有已禁用的深度相机"""
        cls.child.clearDisableDepthCameraAll()

    #----------------------------------------------------#


    def sensorPointCloud(cls) -> dict:
        """获得后视激光点云信息以字典类型返回

        Returns:
            dict: 具体的任务信息
        """
        return cls.child.sensorPointCloud()

    def getNearestLaserPoint(cls, laser_id: int) -> List[float]:
        """获取与指定激光距离最近的激光点与激光中心的距离和朝向

        Args:
            laser_id (int): 激光 id 号

        Returns:
            List[float]: 最近激光点与激光中心的距离、最近激光点与激光中心的夹角
        """
        return cls.child.getNearestLaserPoint(laser_id)

    def safeLaserMuteStatus(cls) -> str:
        """

        Returns:
            str:
        """
        return cls.child.safeLaserMuteStatus()

    def setSafeLaserMute(cls, id: int, enable: bool):
        """

        Args:
            id:
            enable:
        """
        cls.child.setSafeLaserMute(id, enable)


class Laser3DInterface:
    """激光类"""

    def __init__(self, topic=None):
        if rbk_version == 3:
            from syspy.v3.laser import Laser3DV3
            self.child = Laser3DV3()
        elif rbk_version == 4:
            from syspy.v4.laser import Laser3DV4
            self.child = Laser3DV4(topic)
        else:
            raise ValueError(f"Unsupported RBK version: {rbk_version}")

    def get_lasers3d(cls) -> List["Message_Laser3D"]:
        """获取所有3D激光数据列表

        Returns:
            List[Message_Laser3D]: 返回所有3D激光数据的列表
        """
        return cls.child.get_lasers3d()

Laser: LaserInterface = LaserInterface()
Laser3D: Laser3DInterface = Laser3DInterface()