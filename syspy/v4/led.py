from syspy.core.rbk_rpc import default_plugin, call_service
from syspy.led import LedInterface


@default_plugin("DSPChassis")  # todo RBK4
class LedV4(LedInterface):
    """灯带类"""
    
    @classmethod
    @call_service()
    def sendX86DmxInfo(cls, dmx512_info: str) -> int:
        """X86发送DMX数据控制灯亮

        Args:
            dmx512_info (str): Message_Dmx512转换的str

        Returns:
            (int): 0: 成功
        """
        pass

    @classmethod
    @call_service()
    def sendArmDmxInfo(cls, dmx512_info: str) -> int:
        """Arm发送DMX数据控制灯亮

        Args:
            dmx512_info: (str): Message_Dmx512转换的str

        Returns:
            (int): 0: 成功
        """
        pass
