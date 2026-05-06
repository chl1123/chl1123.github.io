import datetime

from syspy.core.rbk_rpc import default_plugin, call_service
from syspy.lib.trace import TraceInterface


@default_plugin("Trace")
class TraceV3(TraceInterface):

    @classmethod
    def chart(cls, msg: dict, output_console: bool = False, output_time: bool = False, *, name: str = "chart"):
        if output_console:
            if output_time:
                time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                print(f"{time} | chart:", msg)
            else:
                print("chart:", msg)
        cls.client().call_service("Trace", "traceChart", msg, name)

    @classmethod
    def log(cls, msg: str, output_console: bool = True, output_time: bool = False, *, name: str = "log"):
        if output_console:
            if output_time:
                time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                print(f"{time} | log:", msg)
            else:
                print("log:", msg)
        cls.client().call_service("Trace", "traceLog", msg, name)
