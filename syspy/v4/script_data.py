from typing import Optional
import json
from syspy.script_data import ScriptDataInterface


class ScriptDataV4(ScriptDataInterface):
    """脚本数据"""

    _TOPIC = ""  # todo RBK4
    _MODEL_CLASS = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            # todo RBK4
            cls._MODEL_CLASS = None

    def set(self, name: str, data: dict) -> None:
        # todo RBK4 修改App
        return self.client().call_service("NetProtocol", "setScriptData", name, json.dumps(data))

    def get(self, name: str) -> Optional[dict]:
        if self.update():
            return json.loads(self.data.script_data.get(name, "{}"))
