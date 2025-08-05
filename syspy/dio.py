import typing

from syspy.lib.py_rpc import Message, call_service, default_plugin

if typing.TYPE_CHECKING:
    from .protobuf import Message_DINode, Message_DONode  # IDE类型提示


@default_plugin("DSPChassis")
class Di(Message["Message_DI"]):
    """数字输入类"""

    _TOPIC = "rbk.protocol.Message_DI"
    _PLUGIN = "DSPChassis"
    _MODEL_CLASS = None

    @classmethod
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import Message_DI
            cls._MODEL_CLASS = Message_DI

    @classmethod
    @call_service(plugin_name="MoveFactory", func_name="setDIValid")
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

    @classmethod
    def get_di(cls, name: str) -> bool:
        """检测单个DI状态信息
        Args:
            name (str): DI名

        Returns:
            bool: 返回指定DI的状态，若DI不存在返回False
        """
        cls.update()
        if cls.data:
            for node in cls.data.node:
                if node.name == name:
                    return node.status
        return False

    @classmethod
    def get_dis(cls) -> typing.List["Message_DINode"]:
        """获取DI消息中的节点列表

        Returns:
            typing.List[Message_DINode]: DI消息中的节点列表
        """
        if cls.update():
            return cls.data.node

    @classmethod
    def get_max_di(cls) -> int:
        """获取DI消息中的最大节点数

        Returns:
            int: DI消息中的最大节点数
        """
        if cls.update():
            return cls.data.max_node


@default_plugin("DSPChassis")
class Do(Message["Message_DO"]):
    """数字输出类"""

    _TOPIC = "rbk.protocol.Message_DO"
    _PLUGIN = "DSPChassis"
    _MODEL_CLASS = None

    @classmethod
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import Message_DO
            cls._MODEL_CLASS = Message_DO

    @classmethod
    @call_service(plugin_name="MoveFactory")
    def setDO(cls, name: str, status: bool) -> bool:
        """控制DO的开关

        Args:
            name (str): DO名
            status (bool): 是否打开这个DO

        Returns:
            bool: 如果不存在这个DO的id，返回False，而且会报错，agv也会停下来
        """
        pass

    @classmethod
    def get_do(cls, name: str) -> bool:
        """检测单个DO状态信息

        Args:
            name (str): DO名

        Returns:
            bool: 返回指定DO的状态，若DO不存在返回False
        """
        cls.update()
        if cls.data:
            for node in cls.data.node:
                if node.name == name:
                    return node.status
        return False

    @classmethod
    def get_dos(cls) -> typing.List["Message_DONode"]:
        """获取DO消息中的节点列表

        Returns:
            typing.List[Message_DONode]: DO消息中的节点列表
        """
        if cls.update():
            return cls.data.node

    @classmethod
    def get_max_node(cls) -> int:
        """获取DO消息中的最大节点数

        Returns:
            int: DO消息中的最大节点数
        """
        if cls.update():
            return cls.data.max_node
