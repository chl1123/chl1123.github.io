import json
from typing import TYPE_CHECKING, Optional
from syspy.script_data import ScriptDataInterface

class ScriptDataV3(ScriptDataInterface):
    """脚本数据"""

    _TOPIC = "rbk.protocol.msgScript"
    _PLUGIN = "NetProtocol"
    _MODEL_CLASS = None
    if TYPE_CHECKING:
        from .protobuf import msgScript
        data: msgScript = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import msgScript
            cls._MODEL_CLASS = msgScript

    def set(self, name: str, data: dict) -> None:
        return self.client().call_service("NetProtocol", "setScriptData", name, json.dumps(data))

    def get(self, name: str) -> Optional[dict]:
        if self.update():
            return json.loads(self.data.scriptData.get(name, "{}"))
