from typing import List

from .lib.py_rpc import Message, call_service
from .protobuf.message import Message_AllCameraCloud


class Camera(Message[Message_AllCameraCloud]):
    """相机类"""

    _TOPIC = "rbk.protocol.Message_AllCameraCloud"
    _PLUGIN = "MultiDcamera"
    _MODEL_CLASS = Message_AllCameraCloud

    @classmethod
    @call_service(plugin_name="Perception")
    def addDisableDepthStrName(cls, ids: List[str]):
        """禁用多个指定名字的深度相机

        Args:
            ids (List[str]): 指定的相机id列表
        """
        pass

    @classmethod
    @call_service(plugin_name="Perception")
    def clearDisableDepthStrName(cls):
        """清除禁用的深度相机"""
        pass
