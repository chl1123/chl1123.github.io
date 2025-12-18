from syspy import RBK_VERSION
if RBK_VERSION == 3:
    from syspy.v3.protobuf.message.message_battery_pb2 import msgBattery
elif RBK_VERSION == 4:
    from syspy.v4.protobuf.message.messageV4_battery_pb2 import MessageV4_Battery as msgBattery


class BatteryInterface:
    """电池模块接口定义"""

    def __init__(self):
        if RBK_VERSION == 3:
            from syspy.v3.battery import BatteryV3
            self.child = BatteryV3()
        elif RBK_VERSION == 4:
            from syspy.v4.battery import BatteryV4
            self.child = BatteryV4()
        else:
            raise ValueError(f"Unsupported RBK version: {RBK_VERSION}")

    def getPercentage(self, *, topic: str = "Battery-000") -> float:
        """获取电池电量百分比

        Returns:
            (float): 返回电池电量百分比数值
        """
        return self.child.getPercentage(topic=topic)

    def getChargeCurrent(self, *, topic: str = "Battery-000") -> float:
        """获取充电电流

        Returns:
            (float): 返回充电电流数值
        """
        return self.child.getChargeCurrent(topic=topic)

    def getChargeVoltage(self, *, topic: str = "Battery-000") -> float:
        """获取充电电压

        Returns:
            (float): 返回充电电压数值
        """
        return self.child.getChargeVoltage(topic=topic)

    def getIsCharging(self, *, topic: str = "Battery-000") -> bool:
        """获取是否正在充电状态

        Returns:
            (bool): True表示正在充电，False表示未充电
        """
        return self.child.getIsCharging(topic=topic)

    def getTemperature(self, *, topic: str = "Battery-000") -> float:
        """获取电池温度

        Returns:
            (float): 返回电池温度数值
        """
        return self.child.getTemperature(topic=topic)

    def getCycle(self, *, topic: str = "Battery-000") -> int:
        """获取电池循环次数

        Returns:
            (int): 返回电池循环次数数值
        """
        return self.child.getCycle(topic=topic)

    def getMaxChargeCurrent(self, *, topic: str = "Battery-000") -> float:
        """获取最大充电电流

        Returns:
            (float): 返回最大充电电流数值
        """
        return self.child.getMaxChargeCurrent(topic=topic)

    def getMaxChargeVoltage(self, *, topic: str = "Battery-000") -> float:
        """获取最大充电电压

        Returns:
            (float): 返回最大充电电压数值
        """
        return self.child.getMaxChargeVoltage(topic=topic)

    def getExtra(self, *, topic: str = "Battery-000") -> str:
        """获取额外信息

        Returns:
            (str): 返回额外信息字符串
        """
        return self.child.getExtra(topic=topic)

    def getIsManuallyConnected(self, *, topic: str = "Battery-000") -> bool:
        """获取是否手动连接状态

        Returns:
            (bool): True表示手动连接，False表示非手动连接

        Compatibility:
            该接口仅在 RBK 版本 3 中可用。
        """
        return self.child.getIsManuallyConnected(topic=topic)

    def getUserData(self, *, topic: str = "Battery-000") -> bytes:
        """获取用户数据

        Returns:
            (bytes): 返回用户数据字节流
        """
        return self.child.getUserData(topic=topic)

    def getSoh(self, *, topic: str = "Battery-000") -> int:
        """获取电池健康度

        Returns:
            (int): 健康度。-1 表示无效。

        Compatibility:
            该接口仅在 RBK 版本 3 中可用。
        """
        return self.child.getSoh(topic=topic)

    def getAlarmPercentage(self, *, topic: str = "Battery-000") -> int:
        """获取配置项中电池告警、电池错误和关掉电池的百分比的最大值

        Returns:
            (int): 电池告警、电池错误和关掉电池的百分比的最大值
        """
        return self.child.getAlarmPercentage(topic=topic)

    def publish(self, battery_info: "msgBattery", *, topic: str = "Battery-000") -> int:
        """发布电池信息

        Args:
            battery_info ("msgBattery"): proto消息

        Returns:
            (int): -1: 发布失败; 0: 发布成功
        """
        return self.child.publish(battery_info, topic=topic)

    def getCanPort(self, *, topic: str = "Battery-000") -> str:
        """获取CAN端口

        Returns:
            (int): CAN端口
        """
        return self.child.getCanPort(topic=topic)


Battery: BatteryInterface = BatteryInterface()