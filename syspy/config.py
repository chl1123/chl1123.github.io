import json
import os
import time
from typing import Tuple

RBK_INFO_FILE = "/opt/.data/rbk/private/version/robokit.json"
# 获取RBK版本参数
DEFAULT_RBK_VERSION = 3  # 获取失败后的默认版本
MAX_RETRIES = 30  # 最大重试次数
RETRY_INTERVAL = 1  # 重试间隔（秒）

def read_rbk_version_from_file(max_retries: int, retry_interval: float) -> Tuple[int, str]:
    """读取RBK版本信息

    Args:
        max_retries (int): 最大重试次数
        retry_interval (float): 重试间隔（秒）

    Returns:
        rbk_version (int): RBK主版本
        rbk_full_version (str): RBK详细版本
    """
    for attempt in range(max_retries):
        try:
            if os.path.exists(RBK_INFO_FILE):
                with open(RBK_INFO_FILE, 'r') as f:
                    info = json.load(f)
                rbk_full_version = info.get("version")
                if rbk_full_version is not None:
                    rbk_version = int(rbk_full_version.split(".")[0])
                    if rbk_version is not None:
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
    return DEFAULT_RBK_VERSION, "x"


RBK_VERSION, RBK_FULL_VERSION = read_rbk_version_from_file(MAX_RETRIES, RETRY_INTERVAL)
print(f"{RBK_VERSION=}")
print(f"{RBK_FULL_VERSION=}")