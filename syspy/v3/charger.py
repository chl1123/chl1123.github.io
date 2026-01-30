from syspy.core.rbk_rpc import call_service, default_plugin
from syspy.charger import ChargerInterface

@default_plugin("ChargerAdapter")
class ChargerV3(ChargerInterface):
    """充电桩类"""

    @classmethod
    @call_service()
    def connectCharger(cls, name: str, flag: bool):
        pass

    @classmethod
    @call_service()
    def disconnectCharger(cls, name: str) -> bool:
        pass

    @classmethod
    @call_service()
    def getChargeStatus(cls, name: str) -> int:
        pass

    @classmethod
    @call_service()
    def setChargerOn(cls, name: str):
        pass

    @classmethod
    @call_service()
    def setChargerOff(cls, name: str):
        pass
