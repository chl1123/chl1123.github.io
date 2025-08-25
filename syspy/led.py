from abc import ABC
from syspy.core.rbk_rpc import Service, RBKVersionError


class LedInterface(ABC, Service):
    """灯带类"""
    
    @classmethod
    def sendX86DmxInfo(cls, dmx512_info: str) -> int:
        """X86发送DMX数据控制灯亮

        Args:
            dmx512_info (str): Message_Dmx512转换的str

        Returns:
            int: 0: 成功
        """
        raise RBKVersionError()

    @classmethod
    def sendArmDmxInfo(cls, dmx512_info: str) -> int:
        """Arm发送DMX数据控制灯亮

        Args:
            dmx512_info: (str): Message_Dmx512转换的str

        Returns:
            int: 0: 成功
        """
        raise RBKVersionError()

    @classmethod
    def getLedExternalControlInfo(cls) -> str:
        """todo

        Returns:

        """
        raise RBKVersionError()


from syspy import RBK_VERSION
if RBK_VERSION == 3:
    from syspy.v3.led import LedV3
    Led: LedInterface = LedV3()
elif RBK_VERSION == 4:
    from syspy.v4.led import LedV4
    Led: LedInterface = LedV4()
else:
    raise ValueError(f"Unsupported RBK version: {RBK_VERSION}")
