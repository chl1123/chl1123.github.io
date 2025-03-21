import json
import os


class ParamServer:
    """
    参数服务:构建的参数以json的格式保存在params的文件夹下，参数文件名为脚本名称，后缀为json。
    如果默认数据没有，则创建。否则用文件中的数据
    目前支持的数据格式为str, float 和 int
    使用方式:
    p = ParamServer(__file__)
    param = p.loadParam("motor_name", "str", default = "motor1")
    """

    def __init__(self, file):
        param_dir = os.path.dirname(file) + '/params'
        isExists = os.path.exists(param_dir)
        if not isExists:
            os.makedirs(param_dir)
        base_f = os.path.basename(file)
        self.file = param_dir + '/' + base_f.split('.')[0] + '.json'
        self.data = dict()
        try:
            with open(self.file, 'r', encoding="utf-8") as f:
                self.data = json.load(f)
        except:
            pass

    def loadParam(self, name: str, type: str = "", group: str = "", default=None, **kw):
        def updateKey(data, key, value):
            if (key not in data) or (key in data and data[key] != value):
                return True
            else:
                return False

        updateFile = False
        if type is "float" or type is "str" or type is "int" or type is "bool" or type is "list":
            if default is not None:
                if name not in self.data:
                    updateFile = True
                    self.data[name] = dict()
                if "value" not in self.data[name]:
                    updateFile = True
                    self.data[name]["value"] = eval(type)(default)
                if "group" not in self.data[name]:
                    updateFile = True
                    self.data[name]["group"] = group
                if "type" not in self.data[name]:
                    updateFile = True
                    self.data[name]["type"] = type
                if updateKey(self.data[name], "default", default):
                    updateFile = True
                    self.data[name]["default"] = default
                if type is "float" or type is "int":
                    if "maxValue" in kw and updateKey(self.data[name], "maxValue", kw["maxValue"]):
                        updateFile = True
                        self.data[name]["maxValue"] = kw["maxValue"]
                    if "minValue" in kw and updateKey(self.data[name], "minValue", kw["minValue"]):
                        updateFile = True
                        self.data[name]["minValue"] = kw["minValue"]
                if "comment" in kw and updateKey(self.data[name], "comment", kw["comment"]):
                    updateFile = True
                    self.data[name]["comment"] = kw["comment"]
                if "type" in kw and updateKey(self.data[name], "type", kw["type"]):
                    updateFile = True
                    self.data[name]["type"] = kw["type"]
                if "group" in kw and updateKey(self.data[name], "group", kw["group"]):
                    updateFile = True
                    self.data[name]["group"] = kw["group"]
                if "unit" in kw and updateKey(self.data[name], "unit", kw["unit"]):
                    updateFile = True
                    self.data[name]["unit"] = kw["unit"]
                if updateFile:
                    with open(self.file, 'w', encoding="utf-8") as f:
                        json.dump(self.data, f, indent=4, ensure_ascii=False)
                return self.data[name]["value"]
            else:
                raise Exception("loadParam no default key")
        else:
            raise Exception("loadParam Type (str, int, float, bool) Error. Input Type is {}".format(type))

    def read(self, name: str):
        if name in self.data:
            return self.data[name]["value"]
