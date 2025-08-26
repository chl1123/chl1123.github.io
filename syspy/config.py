import json
import os

# 定义共享文件路径
RBK_INFO_FILE = "/tmp/rbk_version_info.json"

def read_rbk_version_from_file():
    """
    从共享文件中读取RBK版本信息
    脚本可以调用此函数获取版本信息
    """
    try:
        if os.path.exists(RBK_INFO_FILE):
            with open(RBK_INFO_FILE, 'r') as f:
                info = json.load(f)
            return info.get("rbk_version"), info.get("rbk_full_version")
        else:
            return 0, "v0"
    except Exception as e:
        return 0, "v0"


RBK_VERSION, RBK_FULL_VERSION = read_rbk_version_from_file()
print(f"{RBK_VERSION=}")
print(f"{RBK_FULL_VERSION=}")