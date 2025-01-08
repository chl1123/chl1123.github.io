from .protobuf.messsage import Message_AllLasers
from .lib.py_rpc import Message, call_service


class Laser(Message[Message_AllLasers]):
    """
    Attributes:
      _TOPIC (str): 消息名
      _PLUGIN (str): 插件名
      _MODEL_CLASS (Type[T]): Pydantic模型类
    """

    _TOPIC = "rbk.protocol.Message_AllLasers"
    _PLUGIN = "MultiLaser"
    _MODEL_CLASS = Message_AllLasers

    @classmethod
    @call_service(plugin_name="Perception")
    def addDisableLaserId(cls, ids: list):
        """禁用指定id数组的激光雷达
        Args:
            ids (list): 指定的激光雷达id列表
        """
        pass

    @classmethod
    @call_service(plugin_name="Perception")
    def clearDisableLaserId(cls):
        """清除禁用的激光
        """
        pass

    @classmethod
    @call_service(plugin_name="Perception")
    def setLaserAngle(cls, id: int, min_angle: float, max_angle: float):
        """设置激光角度
        Args:
            id (int):
            min_angle (float):
            max_angle (float):
        """
        pass

    @classmethod
    @call_service(plugin_name="Perception")
    def clearLaserAngle(cls):
        """清除激光角度
        """
        pass

    @classmethod
    @call_service(plugin_name="Perception")
    def setLaserWidth(cls, id: int, width: float):
        """设置激光宽度
        Args:
            id (int):
            width (float):
        """
        pass

    @classmethod
    @call_service(plugin_name="Perception")
    def clearLaserWidth(cls):
        """清除激光宽度
        """
        pass

    @classmethod
    @call_service(plugin_name="Perception")
    def sensorPointCloud(cls) -> dict:
        """获得后视激光点云信息以字典类型返回

        Returns:
            dict: 具体的任务信息
        """
        pass
