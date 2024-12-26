from typing import Optional
from .py_ipc import Status


class Battery(Status):
    """
    Attributes:
      _TOPIC (str): 消息名
      _PLUGIN (str): 插件名
      _key_to_attribute (dict):
        key: 原始proto转json的属性名
        value: 封装的Python类属性名
    """

    _TOPIC = "rbk.protocol.Message_Battery"
    _PLUGIN = "DSPChassis"
    _key_to_attribute = {
        'charge_current': 'charge_current',
        'charge_voltage': 'charge_voltage',
        'cycle': 'cycle',
        'extra': 'extra',
        'is_charging': 'is_charging',
        'is_manually_connected': 'is_manually_connected',
        'max_charge_current': 'max_charge_current',
        'max_charge_voltage': 'max_charge_voltage',
        'percetage': 'percentage',
        'temperature': 'temperature',
        'user_data': 'user_data'
    }

    # 显式声明属性
    charge_current: Optional[int] = 0
    percentage: Optional[int] = 0
    charge_voltage: Optional[int] = 0
    cycle: Optional[int] = 0
    extra: Optional[str] = None
    is_charging: Optional[bool] = False
    is_manually_connected: Optional[bool] = False
    max_charge_current: Optional[int] = 0
    max_charge_voltage: Optional[int] = 0
    temperature: Optional[int] = 0
    user_data: Optional[str] = None