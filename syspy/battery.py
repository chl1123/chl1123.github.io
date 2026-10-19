from typing import Optional

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

    def getPercentage(self, *, device_key: str = "Battery-000") -> Optional[float]:
        """获取电池电量百分比

        Args:
            device_key (str): 电池设备 key，缺省为 ``"Battery-000"``。

        Returns:
            (Optional[float]): 电池电量百分比 (SoC)，单位 %。
        """
        return self.child.getPercentage(device_key=device_key)

    def getChargeCurrent(self, *, device_key: str = "Battery-000") -> Optional[float]:
        """获取充电电流

        Args:
            device_key (str): 电池设备 key，缺省为 ``"Battery-000"``。

        Returns:
            (Optional[float]): 充电电流，单位 A。
        """
        return self.child.getChargeCurrent(device_key=device_key)

    def getChargeVoltage(self, *, device_key: str = "Battery-000") -> Optional[float]:
        """获取充电电压

        Args:
            device_key (str): 电池设备 key，缺省为 ``"Battery-000"``。

        Returns:
            (Optional[float]): 充电电压，单位 V。
        """
        return self.child.getChargeVoltage(device_key=device_key)

    def getIsCharging(self, *, device_key: str = "Battery-000") -> Optional[bool]:
        """获取是否正在充电状态

        Args:
            device_key (str): 电池设备 key，缺省为 ``"Battery-000"``。

        Returns:
            (Optional[bool]): True 表示正在充电，False 表示未充电。
        """
        return self.child.getIsCharging(device_key=device_key)

    def getTemperature(self, *, device_key: str = "Battery-000") -> Optional[float]:
        """获取电池温度

        Args:
            device_key (str): 电池设备 key，缺省为 ``"Battery-000"``。

        Returns:
            (Optional[float]): 电池温度，单位 ℃。
        """
        return self.child.getTemperature(device_key=device_key)

    def getCycle(self, *, device_key: str = "Battery-000") -> Optional[int]:
        """获取电池循环次数

        Args:
            device_key (str): 电池设备 key，缺省为 ``"Battery-000"``。

        Returns:
            (Optional[int]): 电池循环次数，单位 次。
        """
        return self.child.getCycle(device_key=device_key)

    def getMaxChargeCurrent(self, *, device_key: str = "Battery-000") -> Optional[float]:
        """获取最大充电电流

        Args:
            device_key (str): 电池设备 key，缺省为 ``"Battery-000"``。

        Returns:
            (Optional[float]): 最大充电电流，单位 A。
        """
        return self.child.getMaxChargeCurrent(device_key=device_key)

    def getMaxChargeVoltage(self, *, device_key: str = "Battery-000") -> Optional[float]:
        """获取最大充电电压

        Args:
            device_key (str): 电池设备 key，缺省为 ``"Battery-000"``。

        Returns:
            (Optional[float]): 最大充电电压，单位 V。
        """
        return self.child.getMaxChargeVoltage(device_key=device_key)

    def getExtra(self, *, device_key: str = "Battery-000") -> Optional[str]:
        """获取额外信息

        Args:
            device_key (str): 电池设备 key，缺省为 ``"Battery-000"``。

        Returns:
            (Optional[str]): 额外信息字符串。
        """
        return self.child.getExtra(device_key=device_key)

    def getIsManuallyConnected(self, *, device_key: str = "Battery-000") -> Optional[bool]:
        """获取是否手动连接状态

        Args:
            device_key (str): 电池设备 key，缺省为 ``"Battery-000"``。

        Returns:
            (Optional[bool]): True 表示手动连接，False 表示非手动连接。

        Compatibility:
            该接口仅在 RBK 版本 3 中可用。
        """
        return self.child.getIsManuallyConnected(device_key=device_key)

    def getUserData(self, *, device_key: str = "Battery-000") -> Optional[bytes]:
        """获取用户数据

        Args:
            device_key (str): 电池设备 key，缺省为 ``"Battery-000"``。

        Returns:
            (Optional[bytes]): 用户自定义字段字节流。
        """
        return self.child.getUserData(device_key=device_key)

    def getSoh(self, *, device_key: str = "Battery-000") -> Optional[int]:
        """获取电池健康度

        Args:
            device_key (str): 电池设备 key，缺省为 ``"Battery-000"``。

        Returns:
            (Optional[int]): 电池健康度 (SOH)，单位 %；-1 表示无效。

        Compatibility:
            该接口仅在 RBK 版本 3 中可用。
        """
        return self.child.getSoh(device_key=device_key)

    def publish(self, battery_info: "msgBattery", *, device_key: str = "Battery-000") -> int:
        """发布电池信息

        Args:
            battery_info ("msgBattery"): 待发布的电池 proto 消息。
            device_key (str): 电池设备 key，缺省为 ``"Battery-000"``。

        Returns:
            (int): -1: 发布失败; 0: 发布成功。
        """
        return self.child.publish(battery_info, device_key=device_key)

    def getCanPort(self, *, device_key: str = "Battery-000") -> str:
        """获取CAN端口

        Args:
            device_key (str): 电池设备 key，缺省为 ``"Battery-000"``。

        Returns:
            (str): CAN 端口名称。
        """
        return self.child.getCanPort(device_key=device_key)

    def getBaudrate(self, *, device_key: str = "Battery-000") -> Optional[int]:
        """获取CAN波特率

        Args:
            device_key (str): 电池设备 key，缺省为 ``"Battery-000"``。

        Returns:
            (Optional[int]): CAN 波特率，单位 bit/s。
        """
        return self.child.getBaudrate(device_key=device_key)


Battery: BatteryInterface = BatteryInterface()