from typing import Optional, List
from .py_ipc import Status


"""
{
    "data": {
        "max_node": 0,
        "node": [
            {
                "forbidden": true,
                "func": "stop",
                "id": 4,
                "maxdist": 0,
                "mindist": 0,
                "posx": [
                    0.4733333333333333,
                    0.46999999999999986
                ],
                "posy": [
                    0.20666666666666667,
                    -0.1866666666666667
                ],
                "range": 0,
                "shape": "vertex",
                "source": "virtual",
                "status": false,
                "type": "collision",
                "x": 0,
                "y": 0,
                "yaw": 0,
                "z": 0
            },
            {
                "forbidden": false,
                "func": "",
                "id": 8,
                "maxdist": 0,
                "mindist": 0,
                "posx": [],
                "posy": [],
                "range": 0,
                "shape": "",
                "source": "virtual",
                "status": false,
                "type": "",
                "x": 0,
                "y": 0,
                "yaw": 0,
                "z": 0
            }
        ]
    },
    "plugin": "RBKSim",
    "topic": "rbk.protocol.Message_DI"
}
"""
class Di(Status):
    """
    Attributes:
      _TOPIC (str): 消息名
      _PLUGIN (str): 插件名
      _key_to_attribute (dict):
        key: 原始proto转json的属性名
        value: 封装的Python类属性名
    """

    _TOPIC = "rbk.protocol.Message_DI"
    _PLUGIN = "DSPChassis"
    _key_to_attribute = {
        'node': 'node',
        'max_node': 'max_node'
    }

    # 显式声明属性
    node: Optional[List[dict]] = None
    max_node: Optional[int] = None

    @classmethod
    def get_di(cls, di: int):
        cls.update()
        """
        检测单个DI状态信息
        :param r: SimModule类对象
        :param di: 需要检测的DI
        :return: 返回指定DI的状态，若DI不存在返回False
        """
        for node in cls.node:
            if node['id'] == di:
                return node['status']
        return False


"""
{
    "data": {
        "max_node": 0,
        "node": [
            {
                "func": "",
                "id": 9,
                "source": "",
                "status": true
            },
            {
                "func": "",
                "id": 8,
                "source": "",
                "status": true
            }
        ]
    },
    "plugin": "RBKSim",
    "topic": "rbk.protocol.Message_DO"
}
"""
class Do(Status):
    """
    Attributes:
      _TOPIC (str): 消息名
      _PLUGIN (str): 插件名
      _key_to_attribute (dict):
        key: 原始proto转json的属性名
        value: 封装的Python类属性名
    """

    _TOPIC = "rbk.protocol.Message_DO"
    _PLUGIN = "DSPChassis"
    _key_to_attribute = {
        'node': 'node',
        'max_node': 'max_node'
    }

    # 显式声明属性
    node: Optional[List[dict]] = None
    max_node: Optional[int] = None

    @classmethod
    def get_do(cls, do: int):
        """
        检测单个DO状态信息
        :param r: SimModule类对象
        :param do: 需要检测的 DO
        :return: 返回指定DO的状态，若DO不存在返回False
        """
        cls.update()
        for node in cls.node:
            if node['id'] == do:
                return node['status']
        return False

    @classmethod
    def setDO(cls, id: int, status: bool) -> bool:
        """控制DO的开关

        Args:
            id (int): DO的id
            status (bool): 是否打开这个DO

        Returns:
            bool: 如果不存在这个DO的id，返回False，而且会报错，agv也会停下来
        """
        return cls.rpc_client.setDO(id, status)