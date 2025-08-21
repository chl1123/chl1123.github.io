from typing import List
from syspy.core.rbk_rpc import Message
from syspy.core.rbk_rpc import call_service

class CameraV4(Message):
    """相机类"""
    def __init__(self, topic=None):
        self._TOPIC = topic

    @classmethod
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            # todo RBK4: 增加Bin proto
            from syspy.v4.include.protocol.messageV4_3dcameradata_pb2 import MessageV4_CameraData
            cls._MODEL_CLASS = MessageV4_CameraData

    @call_service(plugin_name="Perception")
    def addDisableDepthStrName(cls, ids: List[str]):
        """禁用多个指定名字的深度相机

        Args:
            ids (List[str]): 指定的相机id列表
        """
        pass

    @call_service(plugin_name="Perception")
    def clearDisableDepthStrName(cls):
        """清除禁用的深度相机"""
        pass
