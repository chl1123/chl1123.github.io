import typing
from google.protobuf.json_format import MessageToJson
from syspy.core.rbk_rpc import default_plugin, Message


@default_plugin("DSPChassis")
class BatteryV3(Message):
    """RBK3电池实现"""
    _TOPIC = "rbk.protocol.msgBattery"
    _PLUGIN = "DSPChassis"
    _MODEL_CLASS = None
    if typing.TYPE_CHECKING:
        from .protobuf import msgBattery
        data: msgBattery = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import msgBattery
            cls._MODEL_CLASS = msgBattery

    def getPercentage(self, *, topic: str = "Battery-000") -> float:
        """获取电池电量百分比

        Returns:
            (float): 返回电池电量百分比数值
        """
        if self.update():
            return self.data.percentage

    def getChargeCurrent(self, *, topic: str = "Battery-000") -> float:
        """获取充电电流

        Returns:
            (float): 返回充电电流数值
        """
        if self.update():
            return self.data.chargeCurrent

    def getChargeVoltage(self, *, topic: str = "Battery-000") -> float:
        """获取充电电压

        Returns:
            (float): 返回充电电压数值
        """
        if self.update():
            return self.data.chargeVoltage

    def getIsCharging(self, *, topic: str = "Battery-000") -> bool:
        """获取是否正在充电状态

        Returns:
            (bool): True表示正在充电，False表示未充电
        """
        if self.update():
            return self.data.isCharging

    def getTemperature(self, *, topic: str = "Battery-000") -> float:
        """获取电池温度

        Returns:
            (float): 返回电池温度数值
        """
        if self.update():
            return self.data.temperature

    def getCycle(self, *, topic: str = "Battery-000") -> int:
        """获取电池循环次数

        Returns:
            (int) 返回电池循环次数数值
        """
        if self.update():
            return self.data.cycle

    def getMaxChargeCurrent(self, *, topic: str = "Battery-000") -> float:
        """获取最大充电电流

        Returns:
            (float): 返回最大充电电流数值
        """
        if self.update():
            return self.data.maxChargeCurrent

    def getMaxChargeVoltage(self, *, topic: str = "Battery-000") -> float:
        """获取最大充电电压

        Returns:
            (float): 返回最大充电电压数值
        """
        if self.update():
            return self.data.maxChargeVoltage

    def getExtra(self, *, topic: str = "Battery-000") -> str:
        """获取额外信息

        Returns:
            (str): 返回额外信息字符串
        """
        if self.update():
            return self.data.extra

    def getIsManuallyConnected(self, *, topic: str = "Battery-000") -> bool:
        """获取是否手动连接状态

        Returns:
            (bool): True表示手动连接，False表示非手动连接
        """
        if self.update():
            return self.data.isManuallyConnected

    def getUserData(self, *, topic: str = "Battery-000") -> bytes:
        """获取用户数据

        Returns:
            bytes: 返回用户数据字节流
        """
        if self.update():
            return self.data.userData

    def getSoh(self, *, topic: str = "Battery-000") -> int:
        """获取电池健康度

        Returns:
            (int): 健康度。-1 表示无效。
        """
        if self.update():
            return self.data.SOH

    def publish(self, battery_msg: "msgBattery", *, topic: str = "Battery-000") -> int:
        """发布电池信息

        Args:
            battery_msg (msgBattery): msgBattery对象

        Returns:
            (int) -1: 发布失败; 0: 发布成功
        """
        return self.client().call_service("DSPChassis", "publishBattery", MessageToJson(battery_msg))

    def getCanPort(self, *, topic: str = "Battery-000") -> str:
        """获取CAN端口

        Returns:
            (int) CAN端口
        """
        return self.client().call_service("DSPChassis", "getBatteryCanPort")