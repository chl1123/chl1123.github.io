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
    def addDisableDepthId(cls, ids: list):
        """禁用指定id的深度相机
        Args:
            ids (list): 指定的相机id列表
        """
        pass

    @classmethod
    @call_service(plugin_name="Perception")
    def clearDisableDepthId(cls):
        """清除禁用的深度相机
        """
        pass
