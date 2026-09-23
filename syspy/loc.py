from typing import Optional, Dict, List
from abc import ABC
from syspy.core.rbk_rpc import Message, RBKVersionError


class LocInterface(ABC, Message):
    """定位类"""

    def getPose(self) -> Optional[Dict[str, float]]:
        """获取机器人位姿（位置和姿态）

        Returns:
            (Optional[Dict[str, float]]): 包含以下键值对的字典：

                - x (float): x 坐标，单位 m
                - y (float): y 坐标，单位 m
                - z (float): z 坐标，单位 m
                - yaw (float): 偏航角，单位 °
                - roll (float): 翻滚角，单位 °
                - pitch (float): 俯仰角，单位 °
        """
        raise RBKVersionError()

    def getConfidence(self) -> Optional[float]:
        """获取定位置信度

        Returns:
            (Optional[float]): 定位置信度，取值 0.0 ~ 1.0。
        """
        raise RBKVersionError()

    def getLocState(self) -> Optional[int]:
        """获取定位状态

        Returns:
            (Optional[int]): 定位状态:

                - 0 = 初始化中
                - 1 = 加载地图中
                - 2 = 加载地图失败
                - 3 = 重定位中
                - 4 = 定位有效
                - 5 = 定位无效
        """
        raise RBKVersionError()

    def getLocMethod(self) -> Optional[int]:
        """获取定位方法

        Returns:
            (Optional[int]): 定位方法:

                - 0 = 里程计模式
                - 1 = 自然轮廓定位
                - 2 = 反光柱定位
                - 3 = 二维码定位
                - 4 = 3D定位 (NDT)
                - 5 = 天码定位
                - 6 = 特征定位
                - 7 = 3D特征定位
                - 8 = 3D KF定位
        """
        raise RBKVersionError()

    @classmethod
    def relocService(cls, center_x: float, center_y: float, length: float,
                     initial_angle: float, angle_scatter: float) -> str:
        """按中心点和搜索范围执行粒子滤波重定位。

        Args:
            center_x (float): 重定位中心 x 坐标，单位 m，无默认值，必须传入。
            center_y (float): 重定位中心 y 坐标，单位 m，无默认值，必须传入。
            length (float): 重定位搜索范围直径，单位 m，无默认值，必须传入；小于 0.1 时使用系统默认范围。
            initial_angle (float): 重定位中心初始朝向，单位 °，无默认值，必须传入。
            angle_scatter (float): 朝向搜索散布范围，单位 °，无默认值，必须传入。

        Returns:
            (str): JSON 对象字符串，成功时通常为 ``{"err_msg": ""}``。
        """
        raise RBKVersionError()

    @classmethod
    def relocServiceFromPose(cls, home_list: List[str]) -> str:
        """按地图中的起点名称列表执行重定位。

        Args:
            home_list (list[str]): 地图 advancedpointlist 中的起点名称列表，无默认值，必须传入。

        Returns:
            (str): JSON 对象字符串，成功时通常为 ``{"err_msg": ""}``。
        """
        raise RBKVersionError()

    @classmethod
    def autoRelocService(cls, use_pos: bool, x: float, y: float) -> str:
        """执行自动重定位，可指定初始位姿。

        Args:
            use_pos (bool): 是否使用指定的初始位置，无默认值，必须传入。
            x (float): 初始位置 x 坐标，单位 m，无默认值，必须传入；``use_pos=False`` 时忽略。
            y (float): 初始位置 y 坐标，单位 m，无默认值，必须传入；``use_pos=False`` 时忽略。

        Returns:
            (str): JSON 对象字符串，成功时通常为 ``{"err_msg": ""}``。
        """
        raise RBKVersionError()

    @classmethod
    def cancelReloc(cls):
        """取消当前正在进行的重定位。

        Returns:
            (None): RPC 服务无返回值，成功响应的 result 为 null。
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
