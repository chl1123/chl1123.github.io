from typing import Optional
import sys
sys.path.append('/opt/.data/rbk/resources/scripts/')
from syspy.py_ipc import Status

class Move(Status):
    """
    Attributes:
      _TOPIC (str): 消息名
      _PLUGIN (str): 插件名
      _key_to_attribute (dict):
        key: 原始proto转json的属性名
        value: 封装的Python类属性名
    """

    _TOPIC = "rbk.protocol.Message_MoveStatus"
    _PLUGIN = "MoveFactory"
    _key_to_attribute = {
        'blocked': 'blocked',
        'block_x': 'block_x',
        'block_y': 'block_y',
        'block_reason': 'block_reason'
    }

    # 显式声明属性
    blocked: Optional[bool] = None
    block_x: Optional[float] = None
    block_y: Optional[float] = None
    block_reason: Optional[int] = None

    @classmethod
    def getChassisStop(cls) -> bool:
        """底盘是否停止（仅通过walk电机判断）

        Returns:
            bool: 如果行走电机停止则为True
        """
        return cls.rpc_client.getChassisStop()
