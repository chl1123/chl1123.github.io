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

    def set(self, name: str, data: dict) -> None:
        """设置脚本数据

        Args:
            name (str): 脚本名或标识
            data (bool): 脚本数据
        """
        return self.client().call_service("NetProtocol", "setScriptData", name, json.dumps(data))

    def get(self, name: str) -> dict:
        """获取脚本数据

        Args:
            name (str): 脚本名或标识
        """
        if self.update():
            return json.loads(self.data.script_data.get(name, "{}"))
