from google.protobuf import message
from typing_extensions import Optional

from syspy import rbk_version


class CameraInterface:
    """相机类"""

    def __init__(self, topic=None):
        if rbk_version == 3:
            from syspy.v3.camera import CameraV3
            self.child = CameraV3()
        elif rbk_version == 4:
            from syspy.v4.camera import CameraV4
            self.child = CameraV4(topic)
        else:
            raise ValueError(f"Unsupported RBK version: {rbk_version}")

    def get_data(self) -> Optional[message.Message]:
        """获取当前数据（不触发更新）"""
        return self.child.get_data()

    # def addDisableDepthStrName(cls, ids: List[str]):
    #     """禁用多个指定名字的深度相机
    #
    #     Args:
    #         ids (List[str]): 指定的相机id列表
    #     """
    #     raise RBKVersionError()
    #
    # def clearDisableDepthStrName(cls):
    #     """清除禁用的深度相机"""
    #     raise RBKVersionError()


Camera: CameraInterface = CameraInterface()
