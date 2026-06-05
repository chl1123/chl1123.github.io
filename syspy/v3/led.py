from syspy.core.rbk_rpc import default_plugin, call_service
from syspy.led import LedInterface

@default_plugin("DSPChassis")
class LedV3(LedInterface):
    """灯带类"""
    
    @classmethod
    @call_service()
    def sendX86DmxInfo(cls, dmx512_info: str) -> int:
        pass

    @classmethod
    @call_service()
    def sendArmDmxInfo(cls, dmx512_info: str) -> int:
        pass