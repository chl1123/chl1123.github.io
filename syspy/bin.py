from abc import ABC
from typing import List, TYPE_CHECKING
from syspy.core.rbk_rpc import Service, Message, RBKVersionError


if TYPE_CHECKING:
    from syspy.v3.protobuf import msgBin  # IDE类型提示


class BinInterface(ABC, Message):
    """库位类"""

    @classmethod
    def get_bins(cls) -> List["msgBin"]:
        """获取库位列表

        Returns:
            (List["msgBin"]): 库位列表

        Examples:
        ```python
        from syspy import Bin
        bins = Bin.get_bins()
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
    """背篓类，用于管理机器人上的背篓及货物状态。

    Compatibility:
        该接口仅在 RBK 版本 3 中可用。
    """

    @staticmethod
    def _empty_container():
        return {
            "goodsName": "",
            "desc": "",
            "hasGoods": False
        }

    @classmethod
    def init_container(cls, number: int = 7):
        """初始化背篓数据。

        Args:
            number (str): 背篓数量。从模型中的moduleType.cartonTransferUnit.id参数获取
        """
        raise RBKVersionError()

    @classmethod
    def setContainer(cls, container_id: str, goods_name: str, desc: str) -> bool:
        """设置车子上库位或者背篓货物

        Args:
            container_id (str): 库位或者背篓id
            goods_name (str): 货物名
            desc (str): 货物描述

        Returns:
            (bool): 如果没有库位或者背篓，则返回false
        """
        raise RBKVersionError()

    @classmethod
    def clearContainer(cls, container_id: str) -> bool:
        """清除车上特定库位或者背篓的状态

        Args:
            container_id (str): 库位或者背篓id，container_id如果为"All"则全部清除

        Returns:
            (bool): 如果没有库位或者背篓，则返回false
        """
        raise RBKVersionError()

    @classmethod
    def clearContainerByGoods(cls, goods_name: str) -> bool:
        """清除车上特定库位或者背篓的状态

        Args:
            goods_name (str): 货物名称，货物名称如果为All则全部清除

        Returns:
            (bool): 如果没有库位或者背篓，则返回false
        """
        raise RBKVersionError()

    @classmethod
    def getContainers(cls) -> list:
        """获取当前车子上库位或者背篓货物的状态。

        Returns:
            （list): 包含所有背篓状态的列表，每个元素是一个字典，包含 container_id、goods_name、desc 和 has_goods。
        """
        raise RBKVersionError()

    @classmethod
    def has_goods(cls, container_id: str = '0') -> bool:
        """检查指定背篓是否包含货物。

        Args:
            container_id (str): 背篓id，默认为 '0'。

        Returns:
            (bool): 如果背篓中有货物，则返回True；否则返回False。
        """
        raise RBKVersionError()

    @classmethod
    def goods_exist(cls, goods_name) -> bool:
        """检查指定的货物是否存在。

        Args:
            goods_name (str): 要检查的货物名。

        Returns:
            (bool): 如果存在该货物，则返回True；否则返回False。
        """
        raise RBKVersionError()

    @classmethod
    def get_task_goods(cls) -> str:
        """从任务参数中获取货物ID。

        Returns:
            (str): 货物ID，如果没有找到则返回空字符串。
        """
        raise RBKVersionError()

    @classmethod
    def get_goods_by_container(cls, container_id: str = '0') -> str:
        """根据背篓名称获取对应的货物ID。

        Args:
            container_id (str): 背篓id，默认为 '0'。

        Returns:
            (str): 货物ID，如果找不到则返回空字符串。
        """
        raise RBKVersionError()

    @classmethod
    def get_container_by_goods(cls, goods_name) -> str:
        """根据货物名查找其所在的背篓。

        Args:
            goods_name (str): 要查找的货物名。

        Returns:
            (str): 找到的背篓名称，如果没有找到或货物未装载，则返回空字符串。
        """
        raise RBKVersionError()

    @classmethod
    def get_json_containers(cls) -> dict:
        """以原始格式返回所有背篓的状态。

        Returns:
            (dict): key为背篓名称，值为包含 goods_id、desc 和 has_goods 的字典。
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
        Container.init_container(container_num)
    print("init data", Container.getContainers())
    Container.setContainer("0", "0", "c0")
    Container.setContainer("1", "1", "c1")
    Container.setContainer("2", "2", "c2")
    print("getContainers 0 1 2: ", Container.getContainers())

    Container.clearContainer("0")
    print("clearContainer 0: ", Container.getContainers())
    Container.clearContainer("All")
    print("clearContainer All: ", Container.getContainers())

    Container.setContainer("0", "0", "c0")
    Container.setContainer("1", "1", "c1")
    Container.setContainer("2", "2", "c2")
    print("setContainer 0 1 2: ", Container.getContainers())

    Container.clearContainerByGoods("1")
    print("clearContainerByGoodsId 1: ", Container.getContainers())

    Container.clearContainerByGoods("All")
    print("clearContainerByGoodsId All: ", Container.getContainers())

    Container.setContainer("0", "0", "c0")
    Container.setContainer("1", "1", "c1")
    Container.setContainer("2", "2", "c2")
    print("setContainer 0 1 2: ", Container.getContainers())

    print("has_goods() 0", Container.has_goods("0"))
    print("has_goods() -1", Container.has_goods("-1"))
    print("goods_id_exist() 0", Container.goods_exist("0"))
    print("goods_id_exist() -1", Container.goods_exist("-1"))
    print("get_task_goodsId()", Container.get_task_goods())
    print("get_goodsId_by_container()", Container.get_goods_by_container("0"))
    print("get_goodsId_by_container()", Container.get_goods_by_container("-1"))
    print("get_container_by_goodsId()", Container.get_container_by_goods("1"))
    print("get_container_by_goodsId()", Container.get_container_by_goods("-1"))
    print("get_json_containers()", Container.get_json_containers())
