from .py_rpc import Service, default_plugin, call_service


@default_plugin("NetProtocol")
class Param(Service):

    @classmethod
    @call_service(plugin_name="NetProtocol")
    def getParam(cls, app_type: str, key_path: str) -> dict:
        """获取参数
        Args:
            app_type: App类型
            key_path: 参数字段

        Returns:
            str: 参数内容
        """
        pass
