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
        """设置脚本数据

        Args:
            name (str): 脚本名或标识
            data (bool): 脚本数据
        """
        # todo RBK4 修改App
        return self.client().call_service("NetProtocol", "setScriptData", name, json.dumps(data))

    def get(self, name: str) -> Optional[dict]:
        """获取脚本数据

        Args:
            name (str): 脚本名或标识

        Returns:
            (Optional[dict]): 脚本数据
        """
        if self.update():
            return json.loads(self.data.script_data.get(name, "{}"))
