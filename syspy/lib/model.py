from .py_rpc import Service, default_plugin, call_service


@default_plugin("NetProtocol")
class Model(Service):

    @classmethod
    @call_service()
    def getRobotFile(cls) -> dict:
        """获得模型文件的原始数据

        Returns:
            dict: 具体数据以字典类型返回
        """
        pass

    @classmethod
    @call_service()
    def updateModel(cls, file_name: str, data: dict) -> str:
        """更新模型文件

        Args:
            file_name:
            data: 机器人模型文件的dict格式，先从Model.getRobotFile()获取

        Returns:
            str:
        """
        pass
