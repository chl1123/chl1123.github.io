from typing import Any

from syspy.lib.py_rpc import Service, default_plugin, call_service


@default_plugin("NetProtocol")
class RobotParam(Service):
    @classmethod
    @call_service(plugin_name="NetProtocol", func_name="getParam")
    def getConfig(cls, app_name: str, param_path: str) -> Any:
        """获取机器人配置参数
        Args:
            app_name (str): App名
            param_path (str): 参数路径

        Returns:
            Any: 参数值
        """
        pass

    @classmethod
    @call_service(plugin_name="NetProtocol", func_name="getDevice")
    def getDevice(cls, device_name: str, param_path: str) -> Any:
        """获取机器人设备模型参数(devices/robot.model)
        Args:
            device_name (str): 设备名
            param_path (str): 参数路径

        Returns:
            Any: 参数值
        """
        pass

    @classmethod
    @call_service(func_name="getRobotFile")
    def getDeviceFile(cls) -> dict:
        """获得设备模型文件的原始数据

        Returns:
            dict: 具体数据以字典类型返回
        """
        pass

    @classmethod
    @call_service()
    def updateModel(cls, file_name: str, data: dict) -> str:
        """更新模型文件

        Args:
            file_name: 文件名
            data: 机器人模型文件的dict格式，先从RobotParam.getDeviceFile()获取

        Returns:
            str:
        """
        pass


if __name__ == '__main__':
    recognitionObject = RobotParam.getConfig("Recognition", "recognitionObject")
    print(f"{recognitionObject=}")
    shelf = RobotParam.getConfig("Recognition", "recognitionObject.shelf")
    print(f"{shelf=}")
    legWidth = RobotParam.getConfig("Recognition", "recognitionObject.shelf.recognitionParameter.legWidth")
    print(f"{legWidth=}")
    stopConfidenceThd = RobotParam.getConfig("Localization", "localizationType.2D.stopConfidenceThd")
    print(f"{stopConfidenceThd=}")

    moduleType = RobotParam.getDevice("Model-000", "moduleType")
    print(f"{moduleType=}")
    liftMotor = RobotParam.getDevice("Model-000", "moduleType.liftFork.liftMotor")
    print(f"{liftMotor=}")
    x = RobotParam.getDevice("Model-000", "moduleType.liftFork.installPosition.x")
    print(f"{x=}")
