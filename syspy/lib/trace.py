from abc import ABC
from typing import Union

import typing_extensions
import warnings
from syspy.core.rbk_rpc import Service, RBKVersionError


class TraceInterface(ABC, Service):

    @classmethod
    @typing_extensions.deprecated('`Trace.chart()` 已弃用，请改用 `Trace.log()`。数值/图表数据传 dict 即可，按 name 分通道。')
    def chart(cls, msg: dict, output_console: bool = False, output_time: bool = False, *, name: str = "log", debug: bool = False):
        """记录图表数据

        已弃用：请改用 [`Trace.log()`][syspy.lib.trace.TraceInterface.log]。数值/图表数据传 dict
        即可，落盘通道即 name 本身（缺省 `log`）。

        Args:
            msg (dict): 数据内容。根据字典的key value绘制图表。
            output_console (bool): 是否开启控制台输出。默认不开启。
            output_time (bool): 是否在控制台打印时间。默认不开启。
            name (str): 图表名称（落盘通道名）。缺省为"log", 否则为 name 本身。
            debug (bool): 是否为 debug 日志。True 表示 debug 模式下才落盘
        """
        warnings.warn(
            "`Trace.chart()` 已弃用，请改用 `Trace.log()`。数值/图表数据传 dict 即可，按 name 分通道。",
            DeprecationWarning,
            stacklevel=1
        )
        raise RBKVersionError()

    @classmethod
    def log(cls, msg: Union[str, dict], output_console: bool = True, output_time: bool = False, *, name: str = "log", debug: bool = False):
        """记录日志

        Args:
            msg (Union[str, dict]): 日志内容。传 str 时内部包装为 {"log": msg} 落盘；传 dict 时按 key/value 原样落盘。
            output_console (bool): 是否开启控制台输出。默认开启。
            output_time (bool): 是否在控制台打印时间。默认不开启。
            name (str): 日志名称（落盘通道名）。缺省为"log", 否则为 name 本身。
            debug (bool): 是否为 debug 日志。True 表示 debug 模式下才落盘
        """
        raise RBKVersionError()


from syspy import RBK_VERSION
if RBK_VERSION == 3:
    from syspy.v3.lib.trace import TraceV3
    Trace: TraceInterface = TraceV3()
elif RBK_VERSION == 4:
    from syspy.v4.lib.trace import TraceV4
    Trace: TraceInterface = TraceV4()
else:
    raise ValueError(f"Unsupported RBK version: {RBK_VERSION}")
