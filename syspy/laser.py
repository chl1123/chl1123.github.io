import typing
from typing import List
from syspy import RBK_VERSION

if typing.TYPE_CHECKING:
    if RBK_VERSION == 3:
        from syspy.v3.protobuf import Message_Laser3D
    elif RBK_VERSION == 4:
        pass


class LaserInterface:
    """激光类"""

    def __init__(self, topic=None):
        if RBK_VERSION == 3:
            from syspy.v3.laser import LaserV3
            self.child = LaserV3()
        elif RBK_VERSION == 4:
            from syspy.v4.laser import LaserV4
            self.child = LaserV4(topic)
        else:
            raise ValueError(f"Unsupported RBK version: {RBK_VERSION}")

    def addDisableLaser(self, device_name: str):
        """禁用激光设备

        Args:
            device_name (str): 激光设备名称
        """
        self.child.addDisableLaser(device_name)

    def eraseDisableLaser(self, device_name: str):
        """清除已禁用的激光设备

        Args:
            device_name (str): 激光设备名称
        """
        self.child.eraseDisableLaser(device_name)

    def clearDisableLaserAll(self):
        """清除所有已禁用的激光设备"""
        self.child.clearDisableLaserAll()

    def setLaserWidth(self, device_name: str, width: float):
        """设置激光设备宽度

        Args:
            device_name (str): 激光设备名称
            width (float): 屏蔽宽度，此范围外的点云被屏蔽
        """
        self.child.setLaserWidth(device_name, width)

    def clearLaserWidth(self):
        """清除激光设备宽度"""
        self.child.clearLaserWidth()

    def setLaserAngle(self, device_name: str, min_angle: float, max_angle: float):
        """设置激光设备角度

        Args:
            device_name (str): 激光设备名称
            min_angle (float): 最小角度（单位：°），小于此角度的点云被屏蔽
            max_angle (float): 最大角度（单位：°），大于此角度的点云被屏蔽
        """
        self.child.setLaserAngle(device_name, min_angle, max_angle)

    def clearLaserAngle(self):
        """清除激光设备角度"""
        self.child.clearLaserAngle()

    def addDisableDepthCamera(self, device_name: str):
        """禁用深度相机

        Args:
            device_name (str): 深度相机名称
        """
        self.child.addDisableDepthCamera(device_name)

    def eraseDisableDepthCamera(self, device_name: str):
        """清除已禁用的深度相机

        Args:
            device_name (str): 深度相机名称
        """
        self.child.eraseDisableDepthCamera(device_name)

    def clearDisableDepthCameraAll(self):
        """清除所有已禁用的深度相机"""
        self.child.clearDisableDepthCameraAll()

    #----------------------------------------------------#


    def sensorPointCloud(self) -> dict:
        """获得后视激光点云信息以字典类型返回

        Returns:
            dict: 具体的任务信息
        """
        return self.child.sensorPointCloud()

    def getNearestLaserPoint(self, laser_key: str) -> List[float]:
        """获取与指定激光距离最近的激光点与激光中心的距离和朝向

        Args:
            laser_key (str): 激光设备的key

        Returns:
            List[float]: 最近激光点与激光中心的距离、最近激光点与激光中心的夹角
        """
        return self.child.getNearestLaserPoint(laser_key)

    def safeLaserMuteStatus(self, laser_key: str) -> int:
        """获取激光抑制状态

        Args:
            laser_key (str)：激光设备的key。

        Returns:
            int: 激光状态，1表示启用，0表示禁用
        """
        return self.child.safeLaserMuteStatus(laser_key)

    def setSafeLaserMute(self, laser_key: str, enable: bool):
        """设置激光抑制(muting)

        Args:
            laser_key (str)：激光设备的key。""表示选择全部激光。
            enable (int)：表示是否启用激光muting，true启用，false禁用
        """
        self.child.setSafeLaserMute(laser_key, enable)


class Laser3DInterface:
    """激光类"""

    def __init__(self, topic=None):
        if RBK_VERSION == 3:
            from syspy.v3.laser import Laser3DV3
            self.child = Laser3DV3()
        elif RBK_VERSION == 4:
            from syspy.v4.laser import Laser3DV4
            self.child = Laser3DV4(topic)
        else:
            raise ValueError(f"Unsupported RBK version: {RBK_VERSION}")

    def get_lasers3d(self) -> List["Message_Laser3D"]:
        """获取所有3D激光数据列表

        Returns:
            List[Message_Laser3D]: 返回所有3D激光数据的列表
        """
        return self.child.get_lasers3d()

Laser: LaserInterface = LaserInterface()
Laser3D: Laser3DInterface = Laser3DInterface()