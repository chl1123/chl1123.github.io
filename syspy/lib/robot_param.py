from typing import Any

from syspy.lib.py_rpc import Service, default_plugin, call_service


@default_plugin("NetProtocol")
class RobotParam(Service):
    @classmethod
    @call_service(plugin_name="NetProtocol", func_name="getParam")
    def getConfig(cls, app_name: str, param_path: str, file_name="") -> Any:
        """获取机器人配置参数
        Args:
            app_name (str): App名
            param_path (str): 参数路径
            file_name (str): 文件名。缺省则从默认文件中读取。当前只有识别有多个文件，可传入"xxx.srec"。

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
    # getConfig
    recognitionObject = RobotParam.getConfig("Recognition", "recognitionObject")
    print(f"default.srec {recognitionObject=}")
    recognitionObject = RobotParam.getConfig("Recognition", "recognitionObject", "default(1).srec")
    print(f"default(1).srec {recognitionObject=}")

    goodsHeight = RobotParam.getConfig("Recognition", "recognitionObject.shelf.goodsParameter.goodsHeight")
    print(f"default.srec {goodsHeight=}")
    goodsHeight = RobotParam.getConfig("Recognition", "recognitionObject.shelf.goodsParameter.goodsHeight", "default(1).srec")
    print(f"default(1).srec {goodsHeight=}")

    stopConfidenceThd = RobotParam.getConfig("Localization", "localizationType.2D.stopConfidenceThd")
    print(f"{stopConfidenceThd=}")

    # clone
    charger = RobotParam.getConfig("Recognition", "recognitionObject.charger")
    print(f"{charger=}")

    recognitionSide0 = RobotParam.getConfig("Recognition", "recognitionObject.charger.recognitionSide._0")
    print(f"{recognitionSide0=}")
    deviceName0 = RobotParam.getConfig("Recognition",
                                       "recognitionObject.charger.recognitionSide._0." + recognitionSide0 + ".deviceName")
    print(f"{deviceName0=}")

    recognitionSide1 = RobotParam.getConfig("Recognition", "recognitionObject.charger.recognitionSide._1")
    print(f"{recognitionSide1=}")
    deviceName1 = RobotParam.getConfig("Recognition", "recognitionObject.charger.recognitionSide._1.D.deviceName")
    print(f"{deviceName1=}")

    recognitionSide2 = RobotParam.getConfig("Recognition", "recognitionObject.charger.recognitionSide._2")
    print(f"{recognitionSide2=}")
    deviceName2 = RobotParam.getConfig("Recognition", "recognitionObject.charger.recognitionSide._2.C.deviceName")
    print(f"{deviceName2=}")

    # getDevice
    moduleType = RobotParam.getDevice("Model-000", "moduleType")
    print(f"{moduleType=}")
    liftMotor = RobotParam.getDevice("Model-000", "moduleType.liftFork.liftMotor")
    print(f"{liftMotor=}")
    x = RobotParam.getDevice("Model-000", "moduleType.liftFork.installPosition.x")
    print(f"{x=}")
