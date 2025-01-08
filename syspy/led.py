from .lib.py_rpc import Service, default_plugin, call_service


@default_plugin("DSPChassis")
class Led(Service):
    @classmethod
    @call_service()
    def sendX86DmxInfo(cls, dmx512_info) -> None:
        pass

    @classmethod
    @call_service()
    def sendArmDmxInfo(cls, dmx512_info) -> None:
        pass

    @classmethod
    @call_service()
    def getLedExternalControlInfo(cls) -> str:
        pass
