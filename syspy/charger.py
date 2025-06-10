from .lib.py_rpc import Service, call_service, default_plugin


@default_plugin("ChargerAdapter")
class Charger(Service):
    """充电桩类"""

    @classmethod
    @call_service()
    def connectCharger(cls, recFile: str, flag: bool):
        """与充电桩建立通信连接

        Args:
            recFile: 充电桩识别文件名称
            flag: 是否此次连接用于查询
        """
        pass

    @classmethod
    @call_service()
    def disconnectCharger(cls, recFile: str) -> bool:
        """与充电桩断开通信连接

        Args:
            recFile: 充电桩识别文件名称

        Returns:
            bool:
                True: 断连成功
                False: 断连失败
        """
        pass

    @classmethod
    @call_service()
    def getChargeStatus(cls, recFile: str) -> int:
        """获取机器人充电状态

        Args:
            recFile: 充电桩识别文件名称

        Returns:
            int: 充电桩状态
                默认 -100; 充电硬件错误 -2; 充电网络错误 -1; 充电等待中 0; 将要充电 1; 充电中 2
        """
        pass

    @classmethod
    @call_service()
    def setChargerOn(cls, recFile: str):
        """开始充电

        Args:
            recFile: 充电桩识别文件名称

        Notice:
            调用前需判断充电状态是 0 或 -1
        """
        pass

    @classmethod
    @call_service()
    def setChargerOff(cls, recFile: str):
        """取消充电

        Args:
            recFile: 充电桩识别文件名称

        Notice:
            调用前需判断充电状态是 0 或 -1
        """
        pass
