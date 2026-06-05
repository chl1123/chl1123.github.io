from abc import ABC
from typing import List, TYPE_CHECKING, Union, Optional
from syspy.core.rbk_rpc import Service, Message, RBKVersionError


if TYPE_CHECKING:
    from syspy.v3.protobuf import msgBin  # IDE类型提示


class BinInterface(ABC, Message):
    """库位类"""

    @classmethod
    def getBins(cls) -> Optional[List["msgBin"]]:
        """获取库位列表

        Returns:
            (Optional[List["msgBin"]]): 库位列表

        Examples:
        ```python
        from syspy import Bin
        bins = Bin.getBins()
        for b in bins:  # b为msgBin的对象
            print(b.binId)
            print(b.binStatus)
        ```
        """
        raise RBKVersionError()

    @classmethod
    def binDetection(cls, seq: int):
        """库位检测

        Args:
            seq (int): 时间戳
        """
        raise RBKVersionError()


class ContainerInterface(ABC, Service):
    """容器类，用于管理机器人上的容器及货物状态。

    Compatibility:
        该接口仅在 RBK 版本 3 中可用。
    """

    @staticmethod
    def _emptyContainer():
        return {
            "goodsName": "",
            "desc": "",
            "hasGoods": False
        }

    @classmethod
    def initContainer(cls, max_id: int = 0, self_id: Union[List[str], str]=None):
        """初始化容器 id。

        Args:
            max_id (int): 最大容器 ID。
            self_id (Union[List[str], str]): 自身容器 ID。例如 "999" 或 ["999"]
        """
        raise RBKVersionError()

    @classmethod
    def bindContainer(cls, container_id: str, goods_name: str, desc: str) -> bool:
        """设置车子上库位或者容器货物

        Args:
            container_id (str): 库位或者容器id
            goods_name (str): 货物名
            desc (str): 货物描述

        Returns:
            (bool): 如果没有库位或者容器，则返回false
        """
        raise RBKVersionError()

    @classmethod
    def unbindContainer(cls, container_id: str = "", goods_name: str = "") -> bool:
        """解绑容器和货物（通过容器ID或货物名解绑）

        Args:
            container_id (str): 库位或者容器名称，缺省则全部清除
            goods_name (str): 货物名称，缺省则全部清除

        Returns:
            (bool): 如果没有库位或者容器，则返回false
        """
        raise RBKVersionError()

    @classmethod
    def getContainers(cls) -> list:
        """获取当前车子上库位或者容器货物的状态。

        Returns:
            （list): 包含所有容器状态的列表，每个元素是一个字典，包含 container_id、goods_name、desc 和 has_goods。
        """
        raise RBKVersionError()

    @classmethod
    def hasGoods(cls, container_id: str = '0') -> bool:
        """检查指定容器是否包含货物。

        Args:
            container_id (str): 容器id，默认为 '0'。

        Returns:
            (bool): 如果容器中有货物，则返回True；否则返回False。
        """
        raise RBKVersionError()

    @classmethod
    def goodsExist(cls, goods_name) -> bool:
        """检查指定的货物是否存在。

        Args:
            goods_name (str): 要检查的货物名。

        Returns:
            (bool): 如果存在该货物，则返回True；否则返回False。
        """
        raise RBKVersionError()

    @classmethod
    def getTaskGoods(cls) -> str:
        """从任务参数中获取货物ID。

        Returns:
            (str): 货物ID，如果没有找到则返回空字符串。
        """
        raise RBKVersionError()

    @classmethod
    def getGoodsByContainer(cls, container_id: str = '0') -> str:
        """根据容器名称获取对应的货物ID。

        Args:
            container_id (str): 容器id，默认为 '0'。

        Returns:
            (str): 货物ID，如果找不到则返回空字符串。
        """
        raise RBKVersionError()

    @classmethod
    def getContainerByGoods(cls, goods_name) -> str:
        """根据货物名查找其所在的容器。

        Args:
            goods_name (str): 要查找的货物名。

        Returns:
            (str): 找到的容器名称，如果没有找到或货物未装载，则返回空字符串。
        """
        raise RBKVersionError()

    @classmethod
    def getJsonContainers(cls) -> dict:
        """以原始格式返回所有容器的状态。

        Returns:
            (dict): key为容器名称，值为包含 goods_id、desc 和 has_goods 的字典。
        """
        raise RBKVersionError()


from syspy import RBK_VERSION
if RBK_VERSION == 3:
    from syspy.v3.bin import BinV3, ContainerV3
    Bin: BinInterface = BinV3()
    Container: ContainerInterface = ContainerV3()
elif RBK_VERSION == 4:
    from syspy.v4.bin import BinV4, ContainerV4
    Bin: BinInterface = BinV4()
    Container: ContainerInterface = ContainerV4()
else:
    raise ValueError(f"Unsupported RBK version: {RBK_VERSION}")


if __name__ == '__main__':
    from syspy import RobotParam
    container_num = RobotParam.getDevice("Model-000", "moduleType.cartonTransferUnit.id")
    if isinstance(container_num, int) and container_num > 0:
        Container.initContainer(container_num)
    print("init data", Container.getContainers())
    Container.bindContainer("0", "0", "c0")
    Container.bindContainer("1", "1", "c1")
    Container.bindContainer("2", "2", "c2")
    print("getContainers 0 1 2: ", Container.getContainers())

    Container.unbindContainer("0")
    print("clearContainer 0: ", Container.getContainers())
    Container.unbindContainer()
    print("clearContainer All: ", Container.getContainers())

    Container.bindContainer("0", "0", "c0")
    Container.bindContainer("1", "1", "c1")
    Container.bindContainer("2", "2", "c2")
    print("bindContainer 0 1 2: ", Container.getContainers())

    Container.unbindContainer(goods_name="1")
    print("clearContainerByGoodsId 1: ", Container.getContainers())

    Container.bindContainer("0", "0", "c0")
    Container.bindContainer("1", "1", "c1")
    Container.bindContainer("2", "2", "c2")
    print("bindContainer 0 1 2: ", Container.getContainers())

    print("has_goods() 0", Container.hasGoods("0"))
    print("has_goods() -1", Container.hasGoods("-1"))
    print("goods_id_exist() 0", Container.goodsExist("0"))
    print("goods_id_exist() -1", Container.goodsExist("-1"))
    print("get_task_goodsId()", Container.getTaskGoods())
    print("get_goodsId_by_container()", Container.getGoodsByContainer("0"))
    print("get_goodsId_by_container()", Container.getGoodsByContainer("-1"))
    print("get_container_by_goodsId()", Container.getContainerByGoods("1"))
    print("get_container_by_goodsId()", Container.getContainerByGoods("-1"))
    print("get_json_containers()", Container.getJsonContainers())
