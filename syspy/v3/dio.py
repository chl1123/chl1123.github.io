from typing import Optional, List, TYPE_CHECKING
from syspy.dio import DiInterface, DoInterface
from syspy.core.rbk_rpc import call_service, default_plugin


@default_plugin("DSPChassis")
class DiV3(DiInterface):
    """数字输入类"""

    _TOPIC = "rbk.protocol.msgDI"
    _PLUGIN = "DSPChassis"
    _MODEL_CLASS = None
    if TYPE_CHECKING:
        from .protobuf import msgDI, msgDINode
        data: msgDI = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import msgDI
            cls._MODEL_CLASS = msgDI

    @classmethod
    @call_service(plugin_name="MoveFactory", func_name="setDIValid")
    def setDIValid(cls, key: str, status: bool):
        pass

    @classmethod
    @call_service()
    def setVirtualDI(cls, key: str, status: bool):
        pass

    def getDi(self, key: str) -> bool:
        self.update()
        if self.data:
            for node in self.data.node:
                if node.key == key:
                    return node.status
        return False

    def getDis(self) -> Optional[List["msgDINode"]]:
        if self.update():
            return self.data.node

    def getMaxDi(self) -> int:
        if self.update():
            return self.data.maxNode


@default_plugin("DSPChassis")
class DoV3(DoInterface):
    """数字输出类"""

    _TOPIC = "rbk.protocol.msgDO"
    _PLUGIN = "DSPChassis"
    _MODEL_CLASS = None
    if TYPE_CHECKING:
        from .protobuf import msgDO, msgDONode
        data: msgDO = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import msgDO
            cls._MODEL_CLASS = msgDO

    @classmethod
    @call_service(plugin_name="MoveFactory", func_name="setDO")
    def setDo(cls, key: str, status: bool) -> bool:
        pass

    def getDo(self, key: str) -> bool:
        self.update()
        if self.data:
            for node in self.data.node:
                if node.key == key:
                    return node.status
        return False

    def getDos(self) -> Optional[List["msgDONode"]]:
        if self.update():
            return self.data.node

    def getMaxNode(self) -> Optional[int]:
        if self.update():
            return self.data.maxNode