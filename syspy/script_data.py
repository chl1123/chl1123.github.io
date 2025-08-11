from abc import ABC
from syspy.core.rbk_rpc import Message, RBKVersionError


class ScriptDataInterface(ABC, Message):
    """脚本数据"""

    @classmethod
    def set(cls, name: str, data: dict) -> None:
        """设置脚本数据

        Args:
            name (str): 脚本名或标识
            data (bool): 脚本数据
        """
        raise RBKVersionError()

    @classmethod
    def get(cls, name: str) -> dict:
        """获取脚本数据

        Args:
            name (str): 脚本名或标识
        """
        raise RBKVersionError()


from syspy.config import rbk_version
if rbk_version == 3:
    from syspy.v3.script_data import ScriptDataV3
    ScriptData: ScriptDataInterface = ScriptDataV3()
elif rbk_version == 4:
    from syspy.v4.script_data import ScriptDataV4
    ScriptData: ScriptDataInterface = ScriptDataV4()
else:
    raise ValueError(f"Unsupported RBK version: {rbk_version}")
