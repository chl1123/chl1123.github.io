import datetime

from syspy.core.rbk_rpc import default_plugin
from syspy.lib.trace import TraceInterface


@default_plugin("Trace")  # todo RBK4
class TraceV4(TraceInterface):
    @classmethod
    def event(cls, msg: dict, is_print: bool = True):
        """记录事件（弃用）

        Args:
            msg (str): 日志内容。
            is_print (bool): 是否开启print打印。默认开启。
        """
        if is_print:
            print("event:", msg)
        cls.client().call_service("Trace", "traceLog", msg)

    @classmethod
    def chart(cls, msg: dict, output_console: bool = False, output_time: bool = False):
        """记录图表数据

        Args:
            output_console (bool): 是否开启控制台输出。默认不开启。
            output_time (bool): 是否在控制台打印时间。默认不开启。
        """
        if output_console:
            if output_time:
                time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                print(f"{time} | chart:", msg)
            else:
                print("chart:", msg)
        cls.client().call_service("Trace", "traceChart", msg)

    @classmethod
    def log(cls, msg: str, output_console: bool = True, output_time: bool = False):
        """记录日志

        Args:
            msg (str): 日志内容。
            output_console (bool): 是否开启控制台输出。默认开启。
            output_time (bool): 是否在控制台打印时间。默认不开启。
        """
        if output_console:
            if output_time:
                time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                print(f"{time} | log:", msg)
            else:
                print("log:", msg)
        cls.client().call_service("Trace", "traceLog", msg)
