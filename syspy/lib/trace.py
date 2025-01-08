from .py_rpc import Service, default_plugin, call_service


@default_plugin("Trace")
class Trace(Service):
    @classmethod
    @call_service(func_name="scriptEventInstant")
    def event(cls, msg: str) -> int:
        """
        Args:
            msg (str):

        Returns:
            bool:
        """
        pass

    @classmethod
    @call_service(func_name="scriptLog")
    def log(cls, topic: str, msg: str) -> int:
        """
        Args:
            topic (str):
            msg (str):

        Returns:
            bool:
        """
        pass
