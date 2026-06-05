from syspy.core.rbk_rpc import default_plugin, call_service
from syspy.map import MapInterface


@default_plugin("MCLoc")  # todo RBK4
class MapV4(MapInterface):
    """地图类"""

    @classmethod
    @call_service()
    def switchMap(
            cls,
            map: str,
            switchPoint: str,
            center_x: float = 0.0,
            center_y: float = 0.0,
            initial_angle: float = 65535.0,
    ) -> int:
        pass
