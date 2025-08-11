from abc import ABC

from syspy.core.rbk_rpc import Service, RBKVersionError


class TraceInterface(ABC, Service):
    @classmethod
    def event(cls, msg: dict, is_print: bool = True):
        """记录事件（弃用）

        Args:
            msg (str): 日志内容。
            is_print (bool): 是否开启print打印。默认开启。
        """
        raise RBKVersionError()

    @classmethod
    def chart(cls, msg: dict, is_print: bool = False):
        """记录图表数据

        Args:
            msg (dict): 数据内容。根据字典的key value绘制图表。
            is_print (bool): 是否开启print打印。默认不开启。
        """
        raise RBKVersionError()

    @classmethod
    def log(cls, msg: str, is_print: bool = True):
        """记录日志

        Args:
            msg (str): 日志内容。
            is_print (bool): 是否开启print打印。默认开启。
        """
        raise RBKVersionError()


from syspy.config import rbk_version
if rbk_version == 3:
    from syspy.v3.lib.trace import TraceV3
    Trace: TraceInterface = TraceV3()
elif rbk_version == 4:
    from syspy.v4.lib.trace import TraceV4
    Trace: TraceInterface = TraceV4()
else:
    raise ValueError(f"Unsupported RBK version: {rbk_version}")
