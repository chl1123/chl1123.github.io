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
    def chart(cls, msg: dict, is_print: bool = False):
        """记录图表数据

        Args:
            msg (dict): 数据内容。根据字典的key value绘制图表。
            is_print (bool): 是否开启print打印。默认不开启。
        """
        if is_print:
            print("chart:", msg)
        cls.client().call_service("Trace", "traceChart", msg)

    @classmethod
    def log(cls, msg: str, is_print: bool = True):
        """记录日志

        Args:
            msg (str): 日志内容。
            is_print (bool): 是否开启print打印。默认开启。
        """
        if is_print:
            print("log:", msg)
        cls.client().call_service("Trace", "traceLog", msg)
