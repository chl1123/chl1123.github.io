import time
from typing import Any, List, Dict, Callable
from syspy.core.rbk_rpc import default_plugin, call_service, Service
from syspy.lib.robot import RobotParamInterface, RobotErrorInterface
from ..protobuf.message.message_error_pb2 import msgError
from google.protobuf import json_format

@default_plugin("NetProtocol")
class RobotParamV3(RobotParamInterface):
    config_change_callBack: Callable[[Dict[str, Any]], None] = None
    device_change_callBack: Callable[[List[str]], None] = None

    @classmethod
    def getConfig(cls, app_name: str, param_path: str, file_name: str="", default: Any=None) -> Any:
        value = cls.client().call_service("NetProtocol", "getParam", app_name, param_path, file_name)
        if value is None:
            return default
        return value

    @classmethod
    def getConfigCloneSize(cls, app_name: str, param_path: str, file_name="") -> int:
        return cls.getConfig(app_name, param_path+"._(size", file_name, 0)

    @classmethod
    def getDevice(cls, device_key: str, param_path: str, default: Any=None) -> Any:
        value = cls.client().call_service("NetProtocol", "getDevice", device_key, param_path)
        if value is None:
            return default
        return value

    @classmethod
    def getDeviceCloneSize(cls, device_key: str, param_path: str) -> int:
        return cls.getDevice(device_key, param_path+"._(size", 0)

    @classmethod
    @call_service(func_name="getRobotFile")
    def getDeviceFile(cls) -> dict:
        pass

    @classmethod
    @call_service()
    def updateModel(cls, file_name: str, data: dict) -> str:
        pass

    @classmethod
    def setConfigChangeCallBack(cls, callback: Callable[[Dict[str, Any]], None]):
        cls.config_change_callBack = callback
        Service.server().register_function(cls.config_change_callBack, "config_changed_subscriber", True)

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


def to_dict(msg):
    """将 protobuf 消息转为 dict，保留原始字段名"""
    return json_format.MessageToDict(msg, preserving_proto_field_name=True)


@default_plugin("Error")
class RobotErrorV3(RobotErrorInterface):

    @classmethod
    def setSystemError(cls, key: str, desc: str, clear: bool) -> None:
        error = msgError()
        error.desc = desc
        error.timeStamp = int(time.time_ns())
        if clear:
            key = f"ms@Module{key}"
        else:
            key = f"ss@Module{key}"
        cls.client().call_service("Error", "setSystemError", key, to_dict(error))
