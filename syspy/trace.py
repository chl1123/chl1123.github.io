from .py_ipc import Service
from .service_utils import default_plugin, call_service

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