import json
import logging
import os
import time
from typing import Tuple

# 本模块在 syspy/__init__.py 第 1 行被导入，早于 Trace 绑定，且此时 RBK_VERSION 尚未
# 对外可用（syspy 包处于 partial 状态），因此不能使用 Trace.log，统一走标准库 logging。
log = logging.getLogger("rbk.script")

RBK_INFO_FILE = "/opt/.data/rbk/private/version/robokit.json"
RBK_NETWORK_FILE = "/opt/.data/rbk/resources/network/default.ssys"
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
            log.warning("Attempt %s: JSON decode error", attempt + 1)
        except Exception as e:
            log.warning("Attempt %s: Error reading file: %s", attempt + 1, e)

        log.debug("Attempt %s: Get the RBK version", attempt + 1)
        # 如果不是最后一次尝试，则等待后重试
        if attempt < max_retries - 1:
            time.sleep(retry_interval)

    log.error("Failed to get valid RBK version info after %s attempts", max_retries)
    return DEFAULT_RBK_VERSION, "x"


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
        log.warning("read simulation flag failed: %s", e)
    return default


RBK_VERSION, RBK_FULL_VERSION = read_rbk_version_from_file(MAX_RETRIES, RETRY_INTERVAL)
RBK_SIMULATION = read_simulation_from_file(False)
os.environ["RBK_SIMULATION"] = "1" if RBK_SIMULATION else "0"
log.debug("RBK_VERSION=%s RBK_FULL_VERSION=%s RBK_SIMULATION=%s",
          RBK_VERSION, RBK_FULL_VERSION, RBK_SIMULATION)
