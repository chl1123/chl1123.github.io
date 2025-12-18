import typing
from abc import ABC
from syspy.core.rbk_rpc import Message, RBKVersionError


class LocInterface(ABC, Message):
    """定位类"""

    @classmethod
    def getPose(cls) -> typing.Dict[str, float]:
        """获取机器人位姿（位置和姿态）

        Returns:
            (typing.Dict[str, float]): 包含以下键值对的字典：
                - x (float): x坐标
                - y (float): y坐标
                - z (float): z坐标
                - yaw (float): 偏航角（角度制）
                - roll (float): 翻滚角（角度制）
                - pitch (float): 俯仰角（角度制）
        """
        raise RBKVersionError()

    @classmethod
    def getConfidence(cls) -> float:
        """获取定位置信度

        Returns:
            (float): 返回定位置信度数值
        """
        raise RBKVersionError()

    @classmethod
    def getLocState(cls) -> int:
        """获取定位状态

        Returns:
            (int): 定位状态:

                - 0 = 未初始化\n
                - 1 = 重定位成功\n
                - 2 = 重定位中\n
                - 3 = 地图载入中\n
        """
        raise RBKVersionError()

    @classmethod
    def getLocMethod(cls) -> int:
        """获取定位方法

        Returns:
            (int): 定位方法:

                - 0 = 里程计模式\n
                - 1 = 自然轮廓定位\n
                - 2 = 反光柱定位\n
                - 3 = 二维码定位\n
                - 4 = 3D定位 (NDT)\n
                - 5 = 天码定位\n
                - 6 = 特征定位\n
                - 7 = 3D特征定位\n
                - 8 = 3D KF定位\n
        """
        raise RBKVersionError()


from syspy import RBK_VERSION
if RBK_VERSION == 3:
    from syspy.v3.loc import LocV3
    Loc: LocInterface = LocV3()
elif RBK_VERSION == 4:
    from syspy.v4.loc import LocV4
    Loc: LocInterface = LocV4()
else:
    raise ValueError(f"Unsupported RBK version: {RBK_VERSION}")