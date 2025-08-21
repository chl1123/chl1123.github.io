from abc import ABC
from syspy.core.rbk_rpc import Service, RBKVersionError

class MapInterface(ABC, Service):
    """地图类"""

    @classmethod
    def switchMap(
            cls,
            map: str,
            switchPoint: str,
            center_x: float = 0.0,
            center_y: float = 0.0,
            initial_angle: float = 65535.0,
    ) -> int:
        """切换地图

        Args:
            map (str): 地图名称
            switchPoint (str): 重定位点位
            center_x (float): 重定位中心点 x 坐标 单位 m
            center_y (float): 重定位中心点 y 坐标 单位 m
            initial_angle (float): 重定位中心朝向 单位 degree

        Returns:
            int: 2没有进行切换，1切换中，0切换成功，-1不存在地图，-2切换失败
        """
        raise RBKVersionError()


from syspy.config import RBK_VERSION
if RBK_VERSION == 3:
    from syspy.v3.map import MapV3
    Map: MapInterface = MapV3()
elif RBK_VERSION == 4:
    from syspy.v4.map import MapV4
    Map: MapInterface = MapV4()
else:
    raise ValueError(f"Unsupported RBK version: {RBK_VERSION}")
