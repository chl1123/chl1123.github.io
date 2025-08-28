import typing
from syspy.dio import DiInterface, DoInterface
from syspy.core.rbk_rpc import call_service, default_plugin


@default_plugin("DSPChassis")
class DiV3(DiInterface):
    """数字输入类"""

    _TOPIC = "rbk.protocol.Message_DI"
    _PLUGIN = "DSPChassis"
    _MODEL_CLASS = None
    if typing.TYPE_CHECKING:
        from .protobuf import Message_DI
        data: Message_DI = None

    @classmethod
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import Message_DI
            cls._MODEL_CLASS = Message_DI

    @classmethod
    @call_service(plugin_name="MoveFactory", func_name="setDIValid")
    def setDIValid(cls, key: str, status: bool):
        """设置DI是否生效

        Args:
            key (str): DI key
            status (bool): True表示生效，False表示不生效
        """
        pass

    @classmethod
    @call_service()
    def setVirtualDI(cls, key: str, status: bool):
        """设置虚拟DI状态

        Args:
            key (str): 虚拟DI key
            status (bool):虚拟DI状态
        """
        pass

    def get_di(self, key: str) -> bool:
        """检测单个DI状态信息
        Args:
            key (str): DI key

        Returns:
            bool: 返回指定DI的状态，若DI不存在返回False
        """
        self.update()
        if self.data:
            for node in self.data.node:
                if node.key == key:
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


@default_plugin("DSPChassis")
class DoV3(DoInterface):
    """数字输出类"""

    _TOPIC = "rbk.protocol.Message_DO"
    _PLUGIN = "DSPChassis"
    _MODEL_CLASS = None
    if typing.TYPE_CHECKING:
        from .protobuf import Message_DO
        data: Message_DO = None

    @classmethod
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import Message_DO
            cls._MODEL_CLASS = Message_DO

    @classmethod
    @call_service(plugin_name="MoveFactory")
    def setDO(cls, key: str, status: bool) -> bool:
        """控制DO的开关

        Args:
            key (str): DO key
            status (bool): 是否打开这个DO

        Returns:
            bool: 如果不存在这个DO的id，返回False，而且会报错，agv也会停下来
        """
        pass

    def get_do(self, key: str) -> bool:
        """检测单个DO状态信息

        Args:
            key (str): DO名

        Returns:
            bool: 返回指定DO的状态，若DO不存在返回False
        """
        self.update()
        if self.data:
            for node in self.data.node:
                if node.key == key:
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
