from typing import Optional
from .py_ipc import Status


class NavSpeed(Status):
    """
    Attributes:
      _TOPIC (str): 消息名
      _PLUGIN (str): 插件名
      _key_to_attribute (dict):
        key: 原始proto转json的属性名
        value: 封装的Python类属性名
    """

    _TOPIC = "rbk.protocol.Message_NavSpeed"
    _PLUGIN = "MoveFactory"
    _key_to_attribute = {
        'x': 'x',
        'y': 'y',
        'rotate': 'rotate'
    }

    # 显式声明属性
    x: Optional[float] = None
    y: Optional[float] = None
    rotate: Optional[float] = None