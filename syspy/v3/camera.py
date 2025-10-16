from typing import List

from syspy.core.rbk_rpc import Service
from syspy.core.rbk_rpc import call_service

class CameraV3(Service):
    """相机类"""

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
