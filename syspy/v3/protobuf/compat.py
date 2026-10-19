# -*- coding: utf-8 -*-
"""RBK 3.5 / 3.6 的 protobuf 消息兼容层。

背景
----
release 分支要同时服务 3.5 和 3.6，而两版的消息定义存在**破坏性差异**。
pb2 包本身已经按版本二选一装载（见 ``protobuf/message/__init__.py``），
但少数消息的**模块归属或命名变了**，实现层无法只靠换目录解决：

============================  ==========================  ==========================
消息                          RBK 3.5                       RBK 3.6
============================  ==========================  ==========================
msgMotorCmd                   message_navigation_pb2        message_motorcmd_pb2
msgLaser3d / msgLaser3D       message_laser_pb2 的 msgLaser3D   message_laser_pb2 的 msgLaser3d
msgAllLasers3D                message_laser_pb2 有           已删除（用 msgAllLasers）
msgAutogate / autogateList    message_map_pb2 有             已删除
msgLocalTagLocalization       字段较少（distanceNotFindTag 等）  字段号整体前移
============================  ==========================  ==========================

本模块把这些差异收敛成一个稳定的导入口，实现层统一从这里取：

    from ..protobuf import compat
    MotorCmd = compat.MotorCmd()          # 两版都可用

设计原则
--------
1. **只做名字/位置归一，不改语义**：字段级差异（字段号前移）由 protobuf 的
   按名访问天然吸收，调用方仍按字段名读写；
2. **缺失的消息给 ``None``**，由调用方决定是否降级，避免 import 期就炸；
3. **不在这里 import 具体实现层**，防止循环依赖。
"""

from __future__ import annotations

from syspy.config import RBK_FULL_VERSION

__all__ = [
    "RBK_MESSAGE_VERSION",
    "IS_RBK35",
    "MotorCmd",
    "Laser3d",
    "AllLasers3d",
    "LaserMessage",
    "MapMessage",
    "has_autogate",
    "channel_or_topic",
]


def _parse_version(full_version: str) -> tuple:
    """解析 ``"3.5.4.0210"`` -> ``(3, 5)``；解析失败返回 ``(3, 6)``。"""
    parts = (full_version or "").split(".")
    try:
        return int(parts[0]), int(parts[1])
    except (IndexError, ValueError):
        return 3, 6


_MAJOR, _MINOR = _parse_version(RBK_FULL_VERSION)

#: 消息层适配的版本标签，``"3.5"`` 或 ``"3.6"``。
RBK_MESSAGE_VERSION = "3.5" if (_MAJOR == 3 and _MINOR <= 5) else "3.6"

#: 是否运行在 RBK 3.5 上。
IS_RBK35 = RBK_MESSAGE_VERSION == "3.5"


# --------------------------------------------------------------------------
# msgMotorCmd：3.5 在 message_navigation_pb2，3.6 移到 message_motorcmd_pb2
# --------------------------------------------------------------------------
if IS_RBK35:
    from .message.message_navigation_pb2 import msgMotorCmd as MotorCmd
else:
    from .message.message_motorcmd_pb2 import msgMotorCmd as MotorCmd


# --------------------------------------------------------------------------
# 激光消息：3.5 叫 msgLaser3D/msgAllLasers3D，3.6 改为 msgLaser3d，
# 并删掉了 msgAllLasers3D（3.6 只用聚合消息 msgAllLasers）。
# --------------------------------------------------------------------------
from .message import message_laser_pb2 as LaserMessage

if IS_RBK35:
    from .message.message_laser_pb2 import msgLaser3D as Laser3d
    from .message.message_laser_pb2 import msgAllLasers3D as AllLasers3d
else:
    from .message.message_laser_pb2 import msgLaser3d as Laser3d
    AllLasers3d = None  # 3.6 已删除，调用方需回退到 msgAllLasers


# --------------------------------------------------------------------------
# 地图消息：msgAutogate / msgMap.autogateList 在 3.6 被删除
# --------------------------------------------------------------------------
from .message import message_map_pb2 as MapMessage

#: 3.6 起 ``msgMap`` 不再有 ``autogateList``；调用方用它判断是否需要降级。
has_autogate = IS_RBK35 and hasattr(MapMessage.msgMap(), "autogateList")


# --------------------------------------------------------------------------
# 订阅路径：3.5 走 topic，3.6 走 channel
# --------------------------------------------------------------------------
def channel_or_topic(topic: str = "", channel: str = ""):
    """让实现类按版本自动选用 topic（3.5）或 channel（3.6）。

    RBK 3.5 的设备没有 channel 概念（后端根本没有对应接口），3.6 则全面改为
    按 channel 订阅。为了同一份代码两边都能跑，实现类不再手写 ``_CHANNEL``，
    而是用本装饰器声明两个版本各自的路径：

    .. code-block:: python

        @channel_or_topic(topic="rbk.protocol.msgLocalization",
                          channel=localization.TOPIC_LOCALIZATION_INFO)
        class LocV3(Message):
            ...

    - 3.5：``_CHANNEL = ""``、``_TOPIC = topic``，走旧的 topic 订阅；
    - 3.6：``_CHANNEL = channel``、``_TOPIC = ""``，走 channel。

    ``Message.update()`` 本身已是这个语义：``_CHANNEL`` 为空时回落到 topic。
    所以只需要把两个类属性按版本摆好，实现层的读写代码无需分叉。

    Args:
        topic (str): RBK 3.5 使用的 topic 名。
        channel (str): RBK 3.6 使用的 channel 名。

    Returns:
        (type): 原类，属性已按当前版本设置。
    """

    def decorator(cls):
        if IS_RBK35:
            cls._CHANNEL = ""
            cls._TOPIC = topic
        else:
            cls._CHANNEL = channel
            cls._TOPIC = ""
        return cls

    return decorator
