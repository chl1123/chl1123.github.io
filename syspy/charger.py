from abc import ABC
from syspy.core.rbk_rpc import Service, RBKVersionError

class ChargerInterface(ABC, Service):
    """充电桩类"""

    @classmethod
    def connectCharger(cls, name: str, flag: bool):
        """与充电桩建立通信连接

        Args:
            name: 充电桩名称
            flag: 是否此次连接用于查询
        """
        pass

    @classmethod
    def disconnectCharger(cls, name: str) -> bool:
        """与充电桩断开通信连接

        Args:
            name: 充电桩名称

        Returns:
            (bool):
                True: 断连成功
                False: 断连失败
        """
        raise RBKVersionError()

    @classmethod
    def getChargeStatus(cls, name: str) -> int:
        """获取机器人充电状态

        Args:
            name: 充电桩名称

        Returns:
            (int): 充电桩状态
                默认 -100; 充电硬件错误 -2; 充电网络错误 -1; 充电等待中 0; 将要充电 1; 充电中 2
        """
        raise RBKVersionError()

    @classmethod
    def setChargerOn(cls, name: str):
        """开始充电

        Args:
            name: 充电桩名称

        Notice:
            调用前需判断充电状态是 0 或 -1
        """
        raise RBKVersionError()

    @classmethod
    def setChargerOff(cls, name: str):
        """取消充电

        Args:
            name: 充电桩名称

        Notice:
            调用前需判断充电状态是 0 或 -1
        """
        raise RBKVersionError()


from syspy import RBK_VERSION
if RBK_VERSION == 3:
    from syspy.v3.charger import ChargerV3
    Charger: ChargerInterface = ChargerV3()
elif RBK_VERSION == 4:
    from syspy.v4.charger import ChargerV4
    Charger: ChargerInterface = ChargerV4()
else:
    raise ValueError(f"Unsupported RBK version: {RBK_VERSION}")
