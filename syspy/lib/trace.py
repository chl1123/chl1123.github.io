from .py_rpc import Service, default_plugin, call_service


@default_plugin("Trace")
class Trace(Service):
    @classmethod
    @call_service(func_name="scriptEventInstant")
    def event(cls, msg: str):
        """记录事件

        Args:
            msg (str):
        """
        pass

    @classmethod
    @call_service(func_name="scriptLog")
    def data(cls, topic: str, msg: str):
        """记录数据

        Args:
            topic (str):
            msg (str):
        """
        pass
