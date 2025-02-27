from .py_rpc import Service, default_plugin, call_service


@default_plugin("NetProtocol")
class Param(Service):

    @classmethod
    @call_service(plugin_name="NetProtocol")
    def getParam(cls, app_type: str, key_path: str) -> str:
        """获取参数
        Args:
            app_type:
            key_path:

        Returns:
            str:
        """
        pass
