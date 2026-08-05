from syspy.core.rbk_rpc import call_service, default_plugin
from syspy.map import MapInterface


@default_plugin("MoveFactory")
class MapV3(MapInterface):
    """地图类"""

    _TOPIC = "rbk.protocol.msgMap"
    _PLUGIN = "BlockMapLoader"
    _MODEL_CLASS = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf.message.message_map_pb2 import msgMap
            cls._MODEL_CLASS = msgMap

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
