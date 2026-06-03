import datetime
from typing import Union

import typing_extensions

from syspy.core.rbk_rpc import default_plugin
from syspy.lib.trace import TraceInterface


@default_plugin("Trace")
class TraceV3(TraceInterface):

    @classmethod
    @typing_extensions.deprecated('`Trace.chart()` 已弃用，请改用 `Trace.log()`。数值/图表数据传 dict 即可，按 name 分通道。')
    def chart(cls, msg: dict, output_console: bool = False, output_time: bool = False, *, name: str = "log", debug: bool = False):
        if output_console:
            if output_time:
                time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                print(f"{time} | chart:", msg)
            else:
                print("chart:", msg)
        trace_name = name
        if debug:
            cls.client().call_service("Trace", "traceLogD", msg, trace_name)
        else:
            cls.client().call_service("Trace", "traceLog", msg, trace_name)

    @classmethod
    def log(cls, msg: Union[str, dict], output_console: bool = True, output_time: bool = False, *, name: str = "log", debug: bool = False):
        if output_console:
            if output_time:
                time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                print(f"{time} | log:", msg)
            else:
                print("log:", msg)
        trace_name = name
        if isinstance(msg, str):
            msg = {"log": msg}
        if debug:
            cls.client().call_service("Trace", "traceLogD", msg, trace_name)
        else:
            cls.client().call_service("Trace", "traceLog", msg, trace_name)
