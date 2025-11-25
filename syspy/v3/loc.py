import math
import typing
from syspy.loc import LocInterface

class LocV3(LocInterface):
    """定位类"""

    _TOPIC = "rbk.protocol.msgLocalization"
    _PLUGIN = "MCLoc"
    _MODEL_CLASS = None
    if typing.TYPE_CHECKING:
        from .protobuf import msgLocalization
        data: msgLocalization = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import msgLocalization  # 延迟导入
            cls._MODEL_CLASS = msgLocalization

    def getPose(self) -> typing.Dict[str, float]:
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
        if self.update():
            return {
                "x": self.data.x,
                "y": self.data.y,
                "z": self.data.z,
                "yaw": math.degrees(self.data.angle),
                "roll": math.degrees(self.data.roll),
                "pitch": math.degrees(self.data.pitch),
            }

    def getConfidence(self) -> float:
        """获取定位置信度

        Returns:
            (float): 返回定位置信度数值
        """
        if self.update():
            return self.data.confidence

    def getLocState(self) -> int:
        """获取定位状态

        Returns:
            (int) 返回定位状态值：
                - 0：未初始化
                - 1：重定位成功
                - 2：重定位中
                - 3：地图载入中
        """
        if self.update():
            return self.data.locState

    def getLocMethod(self) -> int:
        """获取定位方法

        Returns:
            (int) 返回定位方法值，
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
        if self.update():
            return self.data.locMethod