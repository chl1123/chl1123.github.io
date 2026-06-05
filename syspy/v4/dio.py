from typing import Optional, List
from syspy.dio import DiInterface, DoInterface
from syspy.core.rbk_rpc import call_service, default_plugin


@default_plugin("DSPChassis")  # todo RBK4
class DiV4(DiInterface):
    """数字输入类"""

    _TOPIC = "SystemDI"
    _MODEL_CLASS = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from syspy.v4.protobuf.message.messageV4_sensor_pb2 import MessageV4_DI
            cls._MODEL_CLASS = MessageV4_DI

    @classmethod
    @call_service()
    def setDIValid(cls, name: str, status: bool):
        pass

    @classmethod
    @call_service()
    def setVirtualDI(cls, name: str, status: bool):
        pass

    def getDi(self, name: str) -> bool:
        self.update()
        if self.data:
            for node in self.data.node:
                if node.name == name:
                    return node.status
        return False

    def getDis(self) -> Optional[List["MessageV4_DINode"]]:
        if self.update():
            return self.data.node

    def getMaxDi(self) -> int:
        if self.update():
            return self.data.max_node


# todo RBK4
@default_plugin("DSPChassis")  # todo RBK4
class DoV4(DoInterface):
    """数字输出类"""

    _TOPIC = "SystemDO"
    _MODEL_CLASS = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from syspy.v4.protobuf.message.messageV4_sensor_pb2 import MessageV4_DO
            cls._MODEL_CLASS = MessageV4_DO

    @classmethod
    @call_service(plugin_name="MoveFactory", func_name="setDO")  # todo RBK4
    def setDo(cls, name: str, status: bool) -> bool:
        pass

    def getDo(self, name: str) -> bool:
        self.update()
        if self.data:
            for node in self.data.node:
                if node.name == name:
                    return node.status
        return False

    def getDos(self) -> Optional[List["MessageV4_DONode"]]:
        if self.update():
            return self.data.node

    def getMaxNode(self) -> Optional[int]:
        if self.update():
            return self.data.max_node