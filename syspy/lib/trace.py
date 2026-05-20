from abc import ABC
from typing import Union

from syspy.core.rbk_rpc import Service, RBKVersionError


class TraceInterface(ABC, Service):

    @classmethod
    def chart(cls, msg: dict, output_console: bool = False, output_time: bool = False, *, name: str = "", debug: bool = False):
        """记录图表数据

        Args:
            msg (dict): 数据内容。根据字典的key value绘制图表。
            output_console (bool): 是否开启控制台输出。默认不开启。
            output_time (bool): 是否在控制台打印时间。默认不开启。
            name (str): 图表名称。缺省为"chart", 否则 f"chart.{name}"
            debug (bool): 是否为 debug 日志。True 表示 debug 模式下才落盘
        """
        raise RBKVersionError()

    @classmethod
    def log(cls, msg: Union[str, dict], output_console: bool = True, output_time: bool = False, *, name: str = "", debug: bool = False):
        """记录日志

        Args:
            msg (str): 日志内容。
            output_console (bool): 是否开启控制台输出。默认开启。
            output_time (bool): 是否在控制台打印时间。默认不开启。
            name (str): 日志名称。默认为"log", 否则 f"log.{name}"
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
