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


def parse_rbk_version(full_version: str) -> Tuple[int, int, int, int]:
    """把完整版本号拆成 ``product_version.h`` 里的四段。

    ``PRODUCT_FULL_VERSION`` 形如 ``"3.6.0.0030"``，对应
    ``MAJOR`` / ``MINOR`` / ``PATCH`` / ``BUILD``。缺段或含非数字后缀
    （如构建机上的 ``"3.5.4.0051tmp"``）的段按 0 处理。

    Args:
        full_version (str): 如 ``"3.5.4.0210"``、``"3.6.0.0033"``。

    Returns:
        (Tuple[int, int, int, int]): ``(major, minor, patch, build)``。
    """
    parts = (full_version or "").split(".")
    digits = []
    for part in parts[:4]:
        # 只取前导数字，容忍 "0051tmp" 这类构建后缀
        head = ""
        for ch in part:
            if not ch.isdigit():
                break
            head += ch
        digits.append(int(head) if head else 0)
    while len(digits) < 4:
        digits.append(0)
    return tuple(digits)  # type: ignore[return-value]


RBK_VERSION_MAJOR, RBK_VERSION_MINOR, RBK_VERSION_PATCH, RBK_VERSION_BUILD = \
    parse_rbk_version(RBK_FULL_VERSION)

#: 当前运行环境是否为 RBK 3.5。
#:
#: 这两个版本在“订阅方式”上不同：3.5 用 topic， 3.6 改用 channel。
#: 订阅路径、消息装载等需要分支的地方统一用这个标志，
#: 不要在各自的实现模块里重新判版本。
IS_RBK_VERSION_35 = RBK_VERSION_MAJOR == 3 and RBK_VERSION_MINOR <= 5

#: 当前运行环境是否为 RBK 3.6。
IS_RBK_VERSION_36 = RBK_VERSION_MAJOR == 3 and RBK_VERSION_MINOR >= 6

print(f"[syspy] RBK_VERSION={RBK_VERSION}, RBK_FULL_VERSION={RBK_FULL_VERSION}, "
      f"RBK_SIMULATION={RBK_SIMULATION}")
