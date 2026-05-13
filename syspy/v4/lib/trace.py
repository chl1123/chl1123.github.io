import datetime
from typing import Union

from syspy.core.rbk_rpc import default_plugin
from syspy.lib.trace import TraceInterface


@default_plugin("Trace")  # todo RBK4
class TraceV4(TraceInterface):

    @classmethod
    def chart(cls, msg: dict, output_console: bool = False, output_time: bool = False, *, name: str = ""):
        if output_console:
            if output_time:
                time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                print(f"{time} | chart:", msg)
            else:
                print("chart:", msg)
        trace_name = f"chart.{name}" if name else "chart"
        cls.client().call_service("Trace", "traceLogKV", msg=msg, name=trace_name)

    @classmethod
    def log(cls, msg: Union[str, dict], output_console: bool = True, output_time: bool = False, *, name: str = ""):
        if output_console:
            if output_time:
                time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                print(f"{time} | log:", msg)
            else:
                print("log:", msg)
        trace_name = f"log.{name}" if name else "log"
        if isinstance(msg, str):
            msg = {"log": msg}
        cls.client().call_service("Trace", "traceLogKV", msg=msg, name=trace_name)
