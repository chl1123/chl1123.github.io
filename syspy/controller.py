from typing import Optional
from syspy.py_ipc import Status


class Controller(Status):
    """
    Attributes:
      _TOPIC (str): 消息名
      _PLUGIN (str): 插件名
      _key_to_attribute (dict):
        key: 原始proto转json的属性名
        value: 封装的Python类属性名
    """


    _TOPIC = "rbk.protocol.Message_Controller"
    _PLUGIN = "DSPChassis"
    _key_to_attribute = {
        # 'temp': 'temperature',
        # 'humi': 'humidity',
        # 'voltage': 'voltage',
        'emc': 'emc',
        # 'brake': 'brake_active',
        # 'driverEmc': 'driver_emergency_stop',
        # 'manualCharge': 'manual_charging',
        # 'autoCharge': 'auto_charging',
        # 'electric': 'electric_mode',
        # 'softEMC': 'soft_emergency_stop',
        # 'isExternalControl': 'external_control',
        # 'isIMUCalibrating': 'imu_calibrating',
        # 'voltagebyAdc': 'voltage_by_adc'
    }

    # 显式声明属性
    # temperature: Optional[float] = None
    # humidity: Optional[float] = None
    # voltage: Optional[float] = None
    emc: Optional[bool] = None
    # brake_active: Optional[bool] = None
    # driver_emergency_stop: Optional[bool] = None
    # manual_charging: Optional[bool] = None
    # auto_charging: Optional[bool] = None
    # electric_mode: Optional[bool] = None
    # soft_emergency_stop: Optional[bool] = None
    # external_control: Optional[bool] = None
    # imu_calibrating: Optional[bool] = None
    # voltage_by_adc: Optional[float] = None