import typing
from syspy.dio import DiInterface, DoInterface
from syspy.core.rbk_rpc import call_service, default_plugin


@default_plugin("DSPChassis")  # todo RBK4
class DiV4(DiInterface):
    """数字输入类"""

    _TOPIC = "SystemDI"
    _MODEL_CLASS = None

    @classmethod
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            from syspy.v4.include.protocol.messageV4_sensor_pb2 import MessageV4_DI
            cls._MODEL_CLASS = MessageV4_DI

    @classmethod
    @call_service()
    def setDIValid(cls, name: str, status: bool):
        """设置DI是否生效

        Args:
            name (str): DI名
            status (bool): True表示生效，False表示不生效
        """
        pass

    @classmethod
    @call_service()
    def setVirtualDI(cls, name: str, status: bool):
        """设置虚拟DI状态

        Args:
            name (str): 虚拟DI名
            status (bool):虚拟DI状态
        """
        pass

    def get_di(self, name: str) -> bool:
        """检测单个DI状态信息
        Args:
            name (str): DI名

        Returns:
            bool: 返回指定DI的状态，若DI不存在返回False
        """
        self.update()
        if self.data:
            for node in self.data.node:
                if node.name == name:
                    return node.status
        return False

    def get_dis(self) -> typing.List["Message_DINode"]:
        """获取DI消息中的节点列表

        Returns:
            typing.List[Message_DINode]: DI消息中的节点列表
        """
        if self.update():
            return self.data.node

    def get_max_di(self) -> int:
        """获取DI消息中的最大节点数

        Returns:
            int: DI消息中的最大节点数
        """
        if self.update():
            return self.data.max_node


# todo RBK4
@default_plugin("DSPChassis")  # todo RBK4
class DoV4(DoInterface):
    """数字输出类"""

    _TOPIC = "SystemDO"
    _MODEL_CLASS = None

    @classmethod
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            from syspy.v4.include.protocol.messageV4_sensor_pb2 import MessageV4_DO
            cls._MODEL_CLASS = MessageV4_DO

    @classmethod
    @call_service(plugin_name="MoveFactory")  # todo RBK4
    def setDO(cls, name: str, status: bool) -> bool:
        """控制DO的开关

        Args:
            name (str): DO名
            status (bool): 是否打开这个DO

        Returns:
            bool: 如果不存在这个DO的id，返回False，而且会报错，agv也会停下来
        """
        pass

    def get_do(self, name: str) -> bool:
        """检测单个DO状态信息

        Args:
            name (str): DO名

        Returns:
            bool: 返回指定DO的状态，若DO不存在返回False
        """
        self.update()
        if self.data:
            for node in self.data.node:
                if node.name == name:
                    return node.status
        return False

    def get_dos(self) -> typing.List["Message_DONode"]:
        """获取DO消息中的节点列表

        Returns:
            typing.List[Message_DONode]: DO消息中的节点列表
        """
        if self.update():
            return self.data.node

    def get_max_node(self) -> int:
        """获取DO消息中的最大节点数

        Returns:
            int: DO消息中的最大节点数
        """
        if self.update():
            return self.data.max_node
