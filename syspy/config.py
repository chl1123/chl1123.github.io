import json
import os
import time
from typing import Tuple

RBK_INFO_FILE = "/opt/.data/rbk/private/version/robokit.json"
RBK_NETWORK_FILE = "/opt/.data/rbk/resources/network/default.ssys"
# 获取RBK版本参数
MAX_RETRIES = 30  # 最大重试次数
RETRY_INTERVAL = 1  # 重试间隔（秒）


def read_rbk_version_from_file(max_retries: int, retry_interval: float) -> Tuple[int, str]:
    """读取RBK版本信息，失败时抛异常

    RBK 启动到写出 robokit.json 有约 30s 间隙（实测进程启动 13:16:58、文件 13:17:27），
    脚本先于它启动时只能等待，故保留重试。等待耗尽仍拿不到版本则直接抛错：返回兜底版本
    会让 v3/v4 的分支判断静默走错，不如尽早失败。

    Args:
        max_retries (int): 最大重试次数
        retry_interval (float): 重试间隔（秒）

    Returns:
        rbk_version (int): RBK主版本
        rbk_full_version (str): RBK详细版本

    Raises:
        RuntimeError: 重试耗尽仍未能读到有效版本信息。
    """
    for attempt in range(max_retries):
        try:
            if os.path.exists(RBK_INFO_FILE):
                with open(RBK_INFO_FILE, 'r') as f:
                    info = json.load(f)
                rbk_full_version = info.get("version")
                if rbk_full_version is not None:
                    return int(rbk_full_version.split(".")[0]), rbk_full_version
        except Exception as e:
            print(f"[syspy] read rbk version error: {e}")

        if attempt < max_retries - 1:
            time.sleep(retry_interval)

    raise RuntimeError(
        f"Failed to read RBK version from {RBK_INFO_FILE} "
        f"after {max_retries} attempts"
    )


def read_simulation_from_file(default: bool = False) -> bool:
    """读取 network/default.ssys 中的 simulation 字段"""
    try:
        if os.path.exists(RBK_NETWORK_FILE):
            with open(RBK_NETWORK_FILE, "r") as f:
                info = json.load(f)
            value = info.get("simulation", default)
            if isinstance(value, str):
                return value.strip().lower() in ("1", "true", "yes", "on")
            return bool(value)
    except Exception as e:
        print(f"[syspy] read simulation flag failed: {e}")
    return default


RBK_VERSION, RBK_FULL_VERSION = read_rbk_version_from_file(MAX_RETRIES, RETRY_INTERVAL)
RBK_SIMULATION = read_simulation_from_file(False)
os.environ["RBK_SIMULATION"] = "1" if RBK_SIMULATION else "0"
print(f"[syspy] RBK_VERSION={RBK_VERSION}, RBK_FULL_VERSION={RBK_FULL_VERSION}, "
      f"RBK_SIMULATION={RBK_SIMULATION}")
