from .protobuf.messsage import Message_Battery
from .py_ipc import Message
from .service_utils import call_service, default_plugin


@default_plugin("DSPChassis")
class Battery(Message[Message_Battery]):
    """
    Attributes:
      _TOPIC (str): 消息名
      _PLUGIN (str): 插件名
      _MODEL_CLASS (Type[T]): Pydantic模型类
    """

    _TOPIC = "rbk.protocol.Message_Battery"
    _PLUGIN = "DSPChassis"
    _MODEL_CLASS = Message_Battery


    @classmethod
    @call_service(func_name="getBatteryMaxPercentage")
    def getAlarmPercentage(cls) -> int:
        """获取配置项中电池告警、电池错误和关掉电池的百分比的最大值
        Args:

        Returns:
            bool: 返回指定DI的状态，若DI不存在返回False
        """
        pass

    @classmethod
    @call_service(func_name="publishBattery")
    def publish(cls, battery_info) -> None:
        pass

    @classmethod
    @call_service(func_name="getBatteryCanPort")
    def getCanPort(cls) -> int:
        pass
