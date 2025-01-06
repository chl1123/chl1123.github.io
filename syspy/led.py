from .py_ipc import Service
from .service_utils import default_plugin, call_service

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