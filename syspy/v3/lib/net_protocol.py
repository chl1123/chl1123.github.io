from syspy.core.rbk_rpc import default_plugin, call_service
from syspy.lib.net_protocol import NetProtocolInterface


@default_plugin("NetProtocol")
class NetProtocolV3(NetProtocolInterface):

    @classmethod
    @call_service()
    def release(cls) -> int:
        pass

    @classmethod
    @call_service()
    def requireByNickName(cls, nick_name: str) -> int:
        pass

    @classmethod
    @call_service()
    def require(cls) -> int:
        pass

    @classmethod
    @call_service()
    def setModbusData(cls, type: str, addr: int, data: list) -> bool:
        pass

    @classmethod
    @call_service()
    def getModbusData(cls, type: str, addr: int, size: int) -> list:
        pass

    @classmethod
    @call_service()
    def tcpUploadString(cls, jsonStr: str):
        pass

    @classmethod
    @call_service()
    def robotInfo(cls) -> dict:
        pass
