import json
import typing
from syspy.script_data import ScriptDataInterface

class ScriptDataV3(ScriptDataInterface):
    """脚本数据"""

    _TOPIC = "rbk.protocol.Message_Script"
    _PLUGIN = "NetProtocol"
    _MODEL_CLASS = None
    if typing.TYPE_CHECKING:
        from .protobuf import Message_Script
        data: Message_Script = None

    @classmethod
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import Message_Script
            cls._MODEL_CLASS = Message_Script

    @classmethod
    def set(cls, name: str, data: dict) -> None:
        """设置脚本数据

        Args:
            name (str): 脚本名或标识
            data (bool): 脚本数据
        """
        return cls.client().call_service("NetProtocol", "setScriptData", name, json.dumps(data))

    @classmethod
    def get(cls, name: str) -> dict:
        """获取脚本数据

        Args:
            name (str): 脚本名或标识
        """
        if cls.update():
            return json.loads(cls.data.script_data.get(name, "{}"))
