import math
import typing

from .lib.py_rpc import Message

if typing.TYPE_CHECKING:
    from .protobuf import Message_Localization  # IDE类型提示


class Loc(Message["Message_Localization"]):
    """定位类"""

    _TOPIC = "rbk.protocol.Message_Localization"
    _PLUGIN = "MCLoc"
    _MODEL_CLASS = None

    @classmethod
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import Message_Localization  # 延迟导入
            cls._MODEL_CLASS = Message_Localization

    @classmethod
    def get_position(cls) -> typing.Tuple[float, float, float]:
        """获取位置

        Returns:
            float: 返回x坐标值
            float: 返回y坐标值
            float: 返回z坐标
        """
        if cls.update():
            return cls.data.x, cls.data.y, cls.data.z

    @classmethod
    def get_angle(cls) -> typing.Tuple[float, float, float]:
        """获取角度（单位度）

        Returns:
            float: 返回偏航角
            float: 返回横滚角
            float: 返回俯仰角
        """
        if cls.update():
            return math.degrees(cls.data.angle), math.degrees(cls.data.roll), math.degrees(cls.data.pitch)

    @classmethod
    def get_confidence(cls) -> float:
        """获取定位置信度

        Returns:
            float: 返回定位置信度数值
        """
        if cls.update():
            return cls.data.confidence

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
        if cls.update():
            return cls.data.loc_state

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
        if cls.update():
            return cls.data.loc_method
