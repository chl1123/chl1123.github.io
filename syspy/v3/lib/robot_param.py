from typing import Any, List, Dict, Callable
from syspy.core.rbk_rpc import default_plugin, call_service, Service
from syspy.lib.robot_param import RobotParamInterface


@default_plugin("NetProtocol")
class RobotParamV3(RobotParamInterface):
    device_change_callBack: Callable[[List[str]], None] = None

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

    @classmethod
    def setDeviceChangeCallBack(cls, callback: Callable[[List[str]], None]):
        cls.device_change_callBack = callback
        Service.server().register_function(cls.device_change_callBack, "device_changed_subscriber", True)

    def getCloneValues(self, name: str, param_path: str, clone_keys: List[str]) -> List[Dict[str, Any]]:
        param_size = self.getConfigCloneSize(name, param_path)
        values = []
        if param_size:
            for i in range(param_size):
                values.append(
                    {
                        clone_key: self.getConfig(name, f"{param_path}._{i}.{clone_key}")
                        for clone_key in clone_keys
                    }
                )
        return values

    def getCollisionModel(self) -> Dict[str, List[Dict[str, str]]]:
        """获取碰撞检测模型"""
        name = "navigation"
        param_path = "collisionDetection.collisionModel"
        clone_keys = ["collisionDevice", "collisionShape"]
        return {
            f"{name}.{param_path}": self.getCloneValues(name, param_path, clone_keys)
        }

    def getDeductModel(self) -> Dict[str, List[Dict[str, Any]]]:
        """获取扣除模型"""
        name = "navigation"
        param_path = "collisionDetection.deductModel"
        clone_keys = ["deductDevice", "deductShape", "ignoreZ", "zMax", "zMin"]
        return {
            f"{name}.{param_path}": self.getCloneValues(name, param_path, clone_keys)
        }

    def getDoRegion(self) -> Dict[str, List[Dict[str, Any]]]:
        """获取DO区域"""
        name = "navigation"
        param_path = "collisionDetection.doRegion"
        clone_keys = ["shape", "do", "filterNum"]
        return {
            f"{name}.{param_path}": self.getCloneValues(name, param_path, clone_keys)
        }