import json
import os
import time

# 定义共享文件路径
RBK_INFO_FILE = "/tmp/rbk_version_info.json"

def read_rbk_version_from_file(max_retries=30, retry_interval=1):
    """
    从共享文件中读取RBK版本信息
    脚本可以调用此函数获取版本信息

    Args:
        max_retries (int): 最大重试次数
        retry_interval (float): 重试间隔（秒）

    Returns:
        tuple: (rbk_version, rbk_full_version)
    """
    for attempt in range(max_retries):
        try:
            if os.path.exists(RBK_INFO_FILE):
                with open(RBK_INFO_FILE, 'r') as f:
                    info = json.load(f)
                rbk_version = info.get("rbk_version")
                rbk_full_version = info.get("rbk_full_version")
                # 检查是否获取到有效的版本信息
                if rbk_version is not None and rbk_full_version is not None:
                    return rbk_version, rbk_full_version
        except json.JSONDecodeError:
            print(f"Attempt {attempt + 1}: JSON decode error")
        except Exception as e:
            print(f"Attempt {attempt + 1}: Error reading file: {e}")

        print(f"Attempt {attempt + 1}: Get the RBK version")
        # 如果不是最后一次尝试，则等待后重试
        if attempt < max_retries - 1:
            time.sleep(retry_interval)

    print(f"Failed to get valid RBK version info after {max_retries} attempts")
    return 0, "v0"


RBK_VERSION, RBK_FULL_VERSION = read_rbk_version_from_file(30, 1)
print(f"{RBK_VERSION=}")
print(f"{RBK_FULL_VERSION=}")