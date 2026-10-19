# -*- coding: utf-8 -*-
"""RBK 3.5 / 3.6 共用的 protobuf 消息包（运行期二选一）。

背景
----
同一个 scripts 仓库 release 分支要同时服务 RBK 3.5 和 3.6。两个版本生成的
pb2 描述符存在**破坏性差异**（msgLaser3D 系列被删、字段号前移等），而
protobuf 的默认描述符池以 **proto 文件名** 为 key 且全局唯一，所以两套
**不能同时**装载在一个进程里：

    TypeError: Couldn't build proto file into descriptor pool!
    Invalid proto descriptor for file "message_battery.proto":
      message_battery.proto: A file with this name is already in the pool.

因此这里按运行期版本把包搜索路径指向 v35/ 或 v36/，进程内只装载一套。
实现层照旧写 ``from .protobuf.message.message_laser_pb2 import ...``，
不需要感知版本。

用法
----
调用方无需改动。本模块在 ``import`` 时根据 ``syspy.config.RBK_FULL_VERSION``
重定向 ``__path__``：

- ``3.5.x``  -> ``v35/``（release 分支生成的 pb2）
- ``3.6.x``  -> ``v36/``（3.6.0 分支生成的 pb2）
- 其他 3.x -> 回退到 v36/，并打印提示（未知小版本时按最新处理）

注意：必须在任何 ``message_xxx_pb2`` 导入之前完成本模块的加载，因此不要在
本文件里 import 任何 pb2 模块。
"""

from __future__ import annotations

import os

from syspy.config import RBK_FULL_VERSION

__all__ = ["MESSAGE_PROTO_DIR", "MESSAGE_PROTO_VERSION"]


def _pick_message_dir(full_version: str) -> tuple:
    """按完整版本号选出 pb2 目录名，返回 (目录名, 版本标签)。

    Args:
        full_version (str): 形如 ``"3.5.4.0210"`` / ``"3.6.0.0033"``。

    Returns:
        (tuple): ``("v35", "3.5")`` 或 ``("v36", "3.6")``。
    """
    parts = (full_version or "").split(".")
    try:
        major, minor = int(parts[0]), int(parts[1])
    except (IndexError, ValueError):
        print("[syspy] 无法解析版本 %r，protobuf 消息目录回退到 v36/" % (full_version,))
        return "v36", "3.6"

    if major == 3 and minor <= 5:
        return "v35", "3.5"
    if major == 3 and minor == 6:
        return "v36", "3.6"

    print("[syspy] 版本 %s 未专门适配，protobuf 消息目录回退到 v36/" % (full_version,))
    return "v36", "3.6"


_SUBDIR, MESSAGE_PROTO_VERSION = _pick_message_dir(RBK_FULL_VERSION)

# 把本包的搜索路径指向选中的子目录：
# 之后 ``from .protobuf.message.message_xxx_pb2 import ...`` 就落到对应版本，
# 且 ``from .protobuf.message import message_xxx_pb2`` 也一样。
MESSAGE_PROTO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), _SUBDIR)
__path__ = [MESSAGE_PROTO_DIR]  # type: ignore[assignment]
