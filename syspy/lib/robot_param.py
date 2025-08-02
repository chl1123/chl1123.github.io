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
    def getConfigCloneSize(cls, app_name: str, param_path: str, file_name="") -> int:
        """获取机器人配置-克隆类型参数个数
        Args:
            app_name (str): App名
            param_path (str): 参数路径
            file_name (str): 文件名。缺省则从默认文件中读取。当前只有识别有多个文件，可传入"xxx.srec"。

        Returns:
            int: 参数个数
        """
        return cls.getConfig(app_name, param_path+"._(size", file_name)

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
    def getDeviceCloneSize(cls, device_name: str, param_path: str) -> int:
        """获取机器人设备模型-克隆类型参数个数(devices/robot.model)
        Args:
            device_name (str): 设备名
            param_path (str): 参数路径

        Returns:
            int: 参数个数
        """
        return cls.getDevice(device_name, param_path+"._(size")

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

    # config clone
    recognitionSide_key = "recognitionObject.charger.recognitionSide"
    recognitionSide_size = RobotParam.getConfigCloneSize("Recognition", recognitionSide_key, "default.srec")
    print(f"{recognitionSide_size=}")

    for i in range(recognitionSide_size):
        r_value = RobotParam.getConfig("Recognition", f"{recognitionSide_key}._{i}", "default.srec")
        print(f"{recognitionSide_key}._{i}={r_value}")
        d_value = RobotParam.getConfig("Recognition", f"{recognitionSide_key}._{i}.{r_value}.deviceName", "default.srec")
        print(f"{recognitionSide_key}._{i}.{r_value}.deviceName={d_value}")

    # getDevice
    moduleType = RobotParam.getDevice("Model-000", "moduleType")
    print(f"{moduleType=}")
    liftMotor = RobotParam.getDevice("Model-000", "moduleType.liftFork.liftMotor")
    print(f"{liftMotor=}")
    x = RobotParam.getDevice("Model-000", "moduleType.liftFork.installPosition.x")
    print(f"{x=}")

    # device clone
    liftFork_id_key = "moduleType.liftFork.id"
    liftFork_id_size = RobotParam.getDeviceCloneSize("Model-000", liftFork_id_key)
    print(f"{liftFork_id_size=}")
    for i in range(liftFork_id_size):
        liftFork_id = RobotParam.getDevice("Model-000", f"{liftFork_id_key}._{i}")
        print(f"liftFork.id._{i}={liftFork_id}")
