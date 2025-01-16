from .protobuf.messsage import Message_AllCameraCloud
from .lib.py_rpc import Message, call_service


class Camera(Message[Message_AllCameraCloud]):
    """
    Attributes:
      _TOPIC (str): 消息名
      _PLUGIN (str): 插件名
      _MODEL_CLASS (Type[T]): Pydantic模型类
    """

    _TOPIC = "rbk.protocol.Message_AllCameraCloud"
    _PLUGIN = "MultiDcamera"
    _MODEL_CLASS = Message_AllCameraCloud

    @classmethod
    @call_service(plugin_name="Perception")
    def addDisableDepthStrName(cls, ids: list):
        """禁用多个指定名字的深度相机
        Args:
            ids (List[str]): 指定的相机id列表
        """
        pass

    @classmethod
    @call_service(plugin_name="Perception")
    def clearDisableDepthStrName(cls):
        """清除禁用的深度相机
        """
        pass
