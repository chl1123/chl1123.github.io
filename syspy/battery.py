from typing import Optional
from syspy.py_ipc import Status


class Battery(Status):
    """
    Attributes:
      _TOPIC (dict): 消息名
      _key_to_attribute (dict):
        key: 原始proto转json的属性名
        value: 封装的Python类属性名
    """

    _TOPIC = "rbk.protocol.Message_Battery"

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
    charge_current: Optional[int] = None
    percentage: Optional[int] = None
    charge_voltage: Optional[int] = None
    cycle: Optional[int] = None
    extra: Optional[str] = None
    is_charging: Optional[bool] = None
    is_manually_connected: Optional[bool] = None
    max_charge_current: Optional[int] = None
    max_charge_voltage: Optional[int] = None
    temperature: Optional[int] = None
    user_data: Optional[str] = None

    def __init__(self):  # noqa: E501
        super().__init__(Battery._TOPIC, "DSPChassis")
