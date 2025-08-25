import typing
from abc import ABC
from syspy.core.rbk_rpc import Message, RBKVersionError


class LocInterface(ABC, Message):
    """定位类"""

    @classmethod
    def get_pose(cls) -> typing.Dict[str, float]:
        """获取机器人位姿（位置和姿态）

        Returns:
            typing.Dict[str, float]: 包含以下键值对的字典：
                - x (float): x坐标
                - y (float): y坐标
                - z (float): z坐标
                - yaw (float): 偏航角（角度制）
                - roll (float): 翻滚角（角度制）
                - pitch (float): 俯仰角（角度制）
        """
        raise RBKVersionError()

    @classmethod
    def get_confidence(cls) -> float:
        """获取定位置信度

        Returns:
            float: 返回定位置信度数值
        """
        raise RBKVersionError()

    @classmethod
    def get_loc_state(cls) -> int:
        """获取定位状态

        Returns:
            int: 返回定位状态值：
                - 0为更新配置中
                - 1为更新地图中
                - 2为等待传感器数据中
                - 3为重定位中
                - 4为定位中
        """
        raise RBKVersionError()

    @classmethod
    def get_loc_method(cls) -> int:
        """获取定位方法

        Returns:
            int: 返回定位方法值，
                - 0为里程计模式
                - 1为自然轮廓定位
                - 2为反光柱定位
                - 3为二维码定位
                - 4为3D定位 (NDT)
                - 5为天码定位
                - 6为特征定位
                - 7为3D特征定位
                - 8为3D KF定位
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
