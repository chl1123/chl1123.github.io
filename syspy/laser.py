import typing
from typing import List
from syspy import RBK_VERSION

if typing.TYPE_CHECKING:
    if RBK_VERSION == 3:
        from syspy.v3.protobuf import msgLaser3D
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

    def get_data(self, args: typing.Optional[List[str]] = None, *, topic: str = None, ) -> typing.Union[tuple, dict]:
        """获取指定topic的当前数据"""
        return self.child.get_data(args, topic=topic)

    def set2DLaserWidth(self, device_name: str, width: float):
        """设置激光设备宽度

        Args:
            device_name (str): 激光设备名称
            width (float): 屏蔽宽度，此范围外的点云被屏蔽
        """
        self.child.set2DLaserWidth(device_name, width)

    def clear2DLaserWidth(self, device_list: List[str]):
        """清除激光设备宽度

        Args:
            device_list (List[str]): 激光设备名称列表
        """
        self.child.clear2DLaserWidth(device_list)

    def set2DLaserAngle(self, device_name: str, min_angle: float, max_angle: float):
        """设置激光设备角度

        Args:
            device_name (str): 激光设备名称
            min_angle (float): 最小角度（单位: °），小于此角度的点云被屏蔽
            max_angle (float): 最大角度（单位: °），大于此角度的点云被屏蔽
        """
        self.child.set2DLaserAngle(device_name, min_angle, max_angle)

    def clear2DLaserAngle(self, device_list: List[str]):
        """清除激光设备角度
        
        Args:
            device_list (List[str]): 激光设备名称列表
        """
        self.child.clear2DLaserAngle(device_list)

    #----------------------------------------------------#

    def getNearestLaserPoint(self, laser_key: str) -> List[float]:
        """获取与指定激光距离最近的激光点与激光中心的距离和朝向

        Args:
            laser_key (str): 激光设备的key

        Returns:
            (List[float]): 最近激光点与激光中心的距离、最近激光点与激光中心的夹角
        """
        return self.child.getNearestLaserPoint(laser_key)

    def safeLaserMuteStatus(self, laser_key: str) -> int:
        """获取激光抑制状态

        Args:
            laser_key (str): 激光设备的key。

        Returns:
            (int): 激光状态，1表示启用，0表示禁用
        """
        return self.child.safeLaserMuteStatus(laser_key)

    def setSafeLaserMute(self, laser_key: str, enable: bool):
        """设置激光抑制(muting)

        Args:
            laser_key (str): 激光设备的key。""表示选择全部激光。
            enable (int): 表示是否启用激光muting，true启用，false禁用
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

    def get_lasers3d(self) -> List["msgLaser3D"]:
        """获取所有3D激光数据列表

        Returns:
            (List[msgLaser3D]): 返回所有3D激光数据的列表

        Examples:
        ```python
        from syspy import Laser3D
        lasers3D = Laser3D.get_lasers3d()
        for laser3D in lasers3D:  # laser3D为msgLaser3D的对象
            print(laser3D.laserType)
            print(laser3D.is3DLocalization)
        ```
        """
        return self.child.get_lasers3d()

Laser: LaserInterface = LaserInterface()
Laser3D: Laser3DInterface = Laser3DInterface()