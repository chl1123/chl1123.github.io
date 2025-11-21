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
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import msgBattery
            cls._MODEL_CLASS = msgBattery
    
    def get_percentage(self, *, topic: str = "Battery-000") -> float:
        """获取电池电量百分比

        Returns:
            (float): 返回电池电量百分比数值
        """
        if self.update():
            return self.data.percentage
    
    def get_charge_current(self, *, topic: str = "Battery-000") -> float:
        """获取充电电流

        Returns:
            (float): 返回充电电流数值
        """
        if self.update():
            return self.data.chargeCurrent
    
    def get_charge_voltage(self, *, topic: str = "Battery-000") -> float:
        """获取充电电压

        Returns:
            (float): 返回充电电压数值
        """
        if self.update():
            return self.data.chargeVoltage

    def get_is_charging(self, *, topic: str = "Battery-000") -> bool:
        """获取是否正在充电状态

        Returns:
            (bool): True表示正在充电，False表示未充电
        """
        if self.update():
            return self.data.isCharging

    def get_temperature(self, *, topic: str = "Battery-000") -> float:
        """获取电池温度

        Returns:
            (float): 返回电池温度数值
        """
        if self.update():
            return self.data.temperature
    
    def get_cycle(self, *, topic: str = "Battery-000") -> int:
        """获取电池循环次数

        Returns:
            (int) 返回电池循环次数数值
        """
        if self.update():
            return self.data.cycle
    
    def get_max_charge_current(self, *, topic: str = "Battery-000") -> float:
        """获取最大充电电流

        Returns:
            (float): 返回最大充电电流数值
        """
        if self.update():
            return self.data.maxChargeCurrent

    def get_max_charge_voltage(self, *, topic: str = "Battery-000") -> float:
        """获取最大充电电压

        Returns:
            (float): 返回最大充电电压数值
        """
        if self.update():
            return self.data.maxChargeVoltage
    
    def get_extra(self, *, topic: str = "Battery-000") -> str:
        """获取额外信息

        Returns:
            (str): 返回额外信息字符串
        """
        if self.update():
            return self.data.extra

    def get_is_manually_connected(self, *, topic: str = "Battery-000") -> bool:
        """获取是否手动连接状态

        Returns:
            (bool): True表示手动连接，False表示非手动连接
        """
        if self.update():
            return self.data.isManuallyConnected
    
    def get_user_data(self, *, topic: str = "Battery-000") -> bytes:
        """获取用户数据

        Returns:
            bytes: 返回用户数据字节流
        """
        if self.update():
            return self.data.userData
    
    def getAlarmPercentage(self, *, topic: str = "Battery-000") -> int:
        """获取配置项中电池告警、电池错误和关掉电池的百分比的最大值

        Returns:
            (int)
        """
        return self.client().call_service("DSPChassis", "getBatteryMaxPercentage")
    
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
