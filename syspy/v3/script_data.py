from __future__ import annotations
import json
from typing import Optional, TYPE_CHECKING

from syspy.script_data import ScriptDataInterface
if TYPE_CHECKING:
    from .protobuf.message.message_script_pb2 import msgScript

class ScriptDataV3(ScriptDataInterface):
    """脚本数据"""

    data: msgScript = None

    _TOPIC = "rbk.protocol.msgScript"
    _PLUGIN = "NetProtocol"
    _MODEL_CLASS = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf.message.message_script_pb2 import msgScript
            cls._MODEL_CLASS = msgScript

    def set(self, name: str, data: dict) -> None:
        return self.client().call_service("NetProtocol", "setScriptData", name, json.dumps(data))

    def get(self, name: str) -> Optional[dict]:
        if self.update():
            return json.loads(self.data.scriptData.get(name, "{}"))
