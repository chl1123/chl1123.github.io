import json
import os

from . import SCRIPTS_DIR

PY_SUFFIX = ".py"
CONFIG_SUFFIX = "_config.json"


class ParamServer:
    """
    参数服务:构建的参数以json的格式保存在params的文件夹下，参数文件名为脚本名称，后缀为json。
    如果默认数据没有，则创建。否则用文件中的数据
    目前支持的数据格式为str, float, int, bool, list
    使用方式:
    p = ParamServer(__file__)
    param = p.loadParam("motor_name", "str", default = "motor1")
    """

    def __init__(self, file):
        if not file.startswith(SCRIPTS_DIR):
            raise ValueError("script path error. It must be in the 'scripts' path")

        script_dir = file.replace(SCRIPTS_DIR, '')
        if not script_dir.endswith(PY_SUFFIX):
            raise ValueError(f"script file error. It must be in the {PY_SUFFIX} file")

        script_right_dir, script_file_name = script_dir.rsplit('/', 1)
        config_dir = SCRIPTS_DIR + "/params" + script_right_dir
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        self.file = config_dir + '/' + script_file_name.replace(PY_SUFFIX, '') + CONFIG_SUFFIX
        self.data = {}
        if os.path.exists(self.file) and os.path.getsize(self.file):
            try:
                with open(self.file, 'r', encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception as e:
                raise IOError(f"read file error. {e}")

    def loadParam(self, name: str, type: str = "", group: str = "", default=None, **kw):
        def updateKey(data, key, value):
            if (key not in data) or (key in data and data[key] != value):
                return True
            else:
                return False

        update_file = False
        if type == "float" or type == "str" or type == "int" or type == "bool" or type == "list":
            if default is not None:
                if name not in self.data:
                    update_file = True
                    self.data[name] = {}
                if "value" not in self.data[name]:
                    update_file = True
                    self.data[name]["value"] = eval(type)(default)
                if "group" not in self.data[name]:
                    update_file = True
                    self.data[name]["group"] = group
                if "type" not in self.data[name]:
                    update_file = True
                    self.data[name]["type"] = type
                if updateKey(self.data[name], "default", default):
                    update_file = True
                    self.data[name]["default"] = default
                if type == "float" or type == "int":
                    if "maxValue" in kw and updateKey(self.data[name], "maxValue", kw["maxValue"]):
                        update_file = True
                        self.data[name]["maxValue"] = kw["maxValue"]
                    if "minValue" in kw and updateKey(self.data[name], "minValue", kw["minValue"]):
                        update_file = True
                        self.data[name]["minValue"] = kw["minValue"]
                if "comment" in kw and updateKey(self.data[name], "comment", kw["comment"]):
                    update_file = True
                    self.data[name]["comment"] = kw["comment"]
                if "type" in kw and updateKey(self.data[name], "type", kw["type"]):
                    update_file = True
                    self.data[name]["type"] = kw["type"]
                if "group" in kw and updateKey(self.data[name], "group", kw["group"]):
                    update_file = True
                    self.data[name]["group"] = kw["group"]
                if "unit" in kw and updateKey(self.data[name], "unit", kw["unit"]):
                    update_file = True
                    self.data[name]["unit"] = kw["unit"]
                if update_file:
                    with open(self.file, 'w', encoding="utf-8") as f:
                        json.dump(self.data, f, indent=4, ensure_ascii=False)
                return self.data[name]["value"]
            else:
                raise ValueError("loadParam no 'default' key")
        else:
            raise TypeError(f"loadParam Type (str, int, float, bool, list) Error. {type=}")

    def read(self, name: str):
        if name in self.data:
            return self.data[name]["value"]
