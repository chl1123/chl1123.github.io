from syspy.core.rbk_rpc import Message

class CameraV3(Message):
    """相机类"""

    _TOPIC = "rbk.protocol.Message_AllCameraCloud"
    _PLUGIN = "MultiDcamera"
    _MODEL_CLASS = None

    @classmethod
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import Message_AllCameraCloud
            cls._MODEL_CLASS = Message_AllCameraCloud

    # @call_service(plugin_name="Perception")
    # def addDisableDepthStrName(cls, ids: List[str]):
    #     """禁用多个指定名字的深度相机
    #
    #     Args:
    #         ids (List[str]): 指定的相机id列表
    #     """
    #     pass
    #
    # @call_service(plugin_name="Perception")
    # def clearDisableDepthStrName(cls):
    #     """清除禁用的深度相机"""
    #     pass
