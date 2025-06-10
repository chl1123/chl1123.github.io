from .lib.py_rpc import Service, default_plugin, call_service


@default_plugin("DSPChassis")
class Led(Service):
    """灯带类"""
    
    @classmethod
    @call_service()
    def sendX86DmxInfo(cls, dmx512_info: str) -> int:
        """X86发送DMX数据控制灯亮

        Args:
            dmx512_info (str): Message_Dmx512转换的str

        Returns:
            int: 0: 成功
        """
        pass

    @classmethod
    @call_service()
    def sendArmDmxInfo(cls, dmx512_info: str) -> int:
        """Arm发送DMX数据控制灯亮

        Args:
            dmx512_info: (str): Message_Dmx512转换的str

        Returns:
            int: 0: 成功
        """
        pass

    @classmethod
    @call_service()
    def getLedExternalControlInfo(cls) -> str:
        """todo

        Returns:

        """
        pass
