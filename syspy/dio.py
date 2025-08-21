import typing
from abc import ABC
from syspy.core.rbk_rpc import Message, RBKVersionError
from syspy import RBK_VERSION

if typing.TYPE_CHECKING:
    if RBK_VERSION == 3:
        from syspy.v3.protobuf import Message_DINode
        from syspy.v3.protobuf import Message_DONode
    elif RBK_VERSION == 4:
        pass


class DiInterface(ABC, Message):
    """数字输入类"""

    @classmethod
    def setDIValid(cls, name: str, status: bool):
        """设置DI是否生效

        Args:
            name (str): DI名
            status (bool): True表示生效，False表示不生效
        """
        raise RBKVersionError()

    @classmethod
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
        raise RBKVersionError()

    @classmethod
    def get_dis(cls) -> typing.List["Message_DINode"]:
        """获取DI消息中的节点列表

        Returns:
            typing.List[Message_DINode]: DI消息中的节点列表
        """
        raise RBKVersionError()

    @classmethod
    def get_max_di(cls) -> int:
        """获取DI消息中的最大节点数

        Returns:
            int: DI消息中的最大节点数
        """
        raise RBKVersionError()


class DoInterface(ABC, Message):
    """数字输出类"""

    @classmethod
    def setDO(cls, name: str, status: bool) -> bool:
        """控制DO的开关

        Args:
            name (str): DO名
            status (bool): 是否打开这个DO

        Returns:
            bool: 如果不存在这个DO的id，返回False，而且会报错，agv也会停下来
        """
        raise RBKVersionError()

    @classmethod
    def get_do(cls, name: str) -> bool:
        """检测单个DO状态信息

        Args:
            name (str): DO名

        Returns:
            bool: 返回指定DO的状态，若DO不存在返回False
        """
        raise RBKVersionError()

    @classmethod
    def get_dos(cls) -> typing.List["Message_DONode"]:
        """获取DO消息中的节点列表

        Returns:
            typing.List[Message_DONode]: DO消息中的节点列表
        """
        raise RBKVersionError()

    @classmethod
    def get_max_node(cls) -> int:
        """获取DO消息中的最大节点数

        Returns:
            int: DO消息中的最大节点数
        """
        raise RBKVersionError()


from syspy.config import RBK_VERSION
if RBK_VERSION == 3:
    from syspy.v3.dio import DiV3, DoV3
    Di: DiInterface = DiV3()
    Do: DoInterface = DoV3()
elif RBK_VERSION == 4:
    from syspy.v4.dio import DiV4, DoV4
    Di: DiInterface = DiV4()
    Do: DoInterface = DoV4()
else:
    raise ValueError(f"Unsupported RBK version: {RBK_VERSION}")
