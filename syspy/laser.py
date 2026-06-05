from typing import List, Dict, Optional, Any, TYPE_CHECKING
import json
import time
from syspy import Module, ScriptStatus, Trace, RobotParam, ScriptParam, RBK_VERSION
from syspy.core.rbk_rpc import Service
from syspy.utils.param_server import ParamType
from syspy.utils import ScriptType
if hasattr(ScriptParam, '_instance'):
    ScriptParam._instance = None 
    ScriptParam._initialized = False
    ScriptParam.config_change_callback = None
    ScriptParam.event_task_config = False

start_time = time.time()
script_param = ScriptParam(__file__)

class ConfigParams:
    """脚本配置参数定义"""
    device_name_key_map = None
    simulation = None

    @classmethod
    def init(cls):
        builder = script_param.builderConfig()
        with builder.GROUPS():
            with builder.GROUP(key="laser_config", name="激光配置", desc="激光控制相关配置"):
                builder.TYPE(ParamType.ARRAY)

                with builder.CHILDREN():
                    with builder.CHILD(key="device_name_key_map", name="激光名称映射",
                                       desc="激光名称到设备key的映射，JSON格式"):
                        builder.TYPE(ParamType.STRING)
                        builder.DEFAULTVALUE('{"laser_name_001": "laser__001", "laser_name_002": "laser_002"}')

        # 保存配置参数，和原参数文件合并
        builder.save(merge=True)
        cls.load_config()

    @classmethod
    def load_config(cls):
        """重新加载配置参数"""
        config = script_param.loadConfig()
        Trace.log(f"Loaded laser config: {config}")
        cls.simulation = config.get("simulation", False)
        try:
            cls.device_name_key_map = json.loads(config.get("device_name_key_map", "{}"))
            print(cls.device_name_key_map)
        except json.JSONDecodeError:
            cls.device_name_key_map = {"laser_name_001": "laser__001", "laser_name_002": "laser_002"}
            Trace.log("解析激光名称映射配置失败，使用默认值")






# 任务输入参数定义
class InputParams:
    """脚本任务输入参数定义"""
    builder = script_param.builderInput()

    with builder.GROUPS():
        with builder.CHILD(key="key", name="激光Key", desc="激光（Laser）设备的 name。""表示选择全部激光。"):
            builder.TYPE(ParamType.STRING)
            builder.REQUIRED(False)
        with builder.CHILD(key="name", name="激光名称", desc="激光设备的key。""表示选择全部激光。"):
            builder.TYPE(ParamType.STRING)
            builder.REQUIRED(False)
        with builder.CHILD(key="enable", name="使能激光", desc="是否启用激光muting："):
            builder.TYPE(ParamType.BOOL)
            builder.REQUIRED(True)
            builder.DEFAULTVALUE(True)



    builder.save()

if TYPE_CHECKING:
    if RBK_VERSION == 3:
        from syspy.v3.protobuf import msgLaser3D
    elif RBK_VERSION == 4:
        pass


class LaserInterface:
    """激光类"""

    def __init__(self, topic=None):
        if RBK_VERSION == 3:
            from syspy.v3.laser import LaserV3
            self.child = LaserV3()
        elif RBK_VERSION == 4:
            from syspy.v4.laser import LaserV4
            self.child = LaserV4(topic)
        else:
            raise ValueError(f"Unsupported RBK version: {RBK_VERSION}")

    def getData(self, fields: Optional[List[str]] = None, *, topic: str = None) -> dict:
        """通用获取消息接口

        Args:
            fields (Optional[List[str]]): 需要的字段列表。缺省或 None 返回全部字段。
            topic (str): 指定消息话题。

        Returns:
            (dict): 包含请求字段的字典数据。
        """
        return self.child.getData(fields, topic=topic)

    def set2DLaserWidth(self, key: str, width: float):
        """设置激光设备宽度

        Args:
            key (str): 激光设备的key
            width (float): 屏蔽宽度，此范围外的点云被屏蔽
        """
        self.child.set2DLaserWidth(key, width)

    def clear2DLaserWidth(self, keys: List[str]):
        """清除激光设备宽度

        Args:
            keys (List[str]): 激光设备的key列表
        """
        self.child.clear2DLaserWidth(keys)

    def set2DLaserAngle(self, key: str, min_angle: float, max_angle: float):
        """设置激光设备角度

        Args:
            key (str): 激光设备的key
            min_angle (float): 最小角度（单位: °），小于此角度的点云被屏蔽
            max_angle (float): 最大角度（单位: °），大于此角度的点云被屏蔽
        """
        self.child.set2DLaserAngle(key, min_angle, max_angle)

    def clear2DLaserAngle(self, keys: List[str]):
        """清除激光设备角度
        
        Args:
            keys (List[str]): 激光设备的key列表
        """
        self.child.clear2DLaserAngle(keys)

    #----------------------------------------------------#

    def getNearestLaserPoint(self, key: str) -> List[float]:
        """获取与指定激光距离最近的激光点与激光中心的距离和朝向

        Args:
            key (str): 激光设备的key

        Returns:
            (List[float]): 最近激光点与激光中心的距离、最近激光点与激光中心的夹角
        """
        return self.child.getNearestLaserPoint(key)

    def safeLaserMuteStatus(self, key: str) -> int:
        """获取激光抑制状态

        Args:
            key (str): 激光设备的key。

        Returns:
            (int): 激光状态，1表示启用，0表示禁用
        """
        return self.child.safeLaserMuteStatus(key)

    def setSafeLaserMute(self, key: str, enable: bool):
        """设置激光抑制(muting)

        Args:
            key (str): 激光设备的key。""表示选择全部激光。
            enable (int): 表示是否启用激光muting，true启用，false禁用
        """
        self.child.setSafeLaserMute(key, enable)


class Laser3DInterface:
    """激光类"""

    def __init__(self, topic=None):
        if RBK_VERSION == 3:
            from syspy.v3.laser import Laser3DV3
            self.child = Laser3DV3()
        elif RBK_VERSION == 4:
            from syspy.v4.laser import Laser3DV4
            self.child = Laser3DV4(topic)
        else:
            raise ValueError(f"Unsupported RBK version: {RBK_VERSION}")

    def getLasers3d(self) -> List["msgLaser3D"]:
        """获取所有3D激光数据列表

        Returns:
            (List[msgLaser3D]): 返回所有3D激光数据的列表

        Examples:
        ```python
        from syspy import Laser3D
        lasers3D = Laser3D.getLasers3d()
        for laser3D in lasers3D:  # laser3D为msgLaser3D的对象
            print(laser3D.laserType)
            print(laser3D.is3DLocalization)
        ```
        """
        return self.child.getLasers3d()

Laser: LaserInterface = LaserInterface()
Laser3D: Laser3DInterface = Laser3DInterface()



class ParamError(Exception):
    """参数错误异常"""
    pass



class ParamCheck:
    @staticmethod
    def required(param_name: str, req: Dict[str, Any]) -> Any:
        """检查必填参数"""
        if param_name not in req:
            raise ParamError(f"Missing required parameter: {param_name}")
        return req[param_name]
    
    @staticmethod
    def optional(param_name: str, req: Dict[str, Any],default: Optional[Any] = None) -> Optional[Any]:
        return req.get(param_name, default)



class LaserSafeController:
    def __init__(self, device_name_key_map: Dict[str, str] = {}):
        self.device_name_key_map: Dict[str, str] = device_name_key_map  
    def _get_real_key(self, req: Dict[str, Any]) -> str:
        if "key" in req:
            return ParamCheck.required("key", req)
        
        if "name" in req:
            name = ParamCheck.required("name", req)
            if name not in self.device_name_key_map:
                raise ParamError(f"Device name {name} not found")
            return self.device_name_key_map[name]
        
        raise ParamError("need key or name")
    def handle_robot_control_request(self, req: Dict[str, Any]) -> Dict[str, Any]:
        try:
            realKey= self._get_real_key(req)
            cheackEnable= ParamCheck.required("enable", req)
                # a=Laser.setSafeLaserMute(realKey, cheackEnable)
            Service.client().call_service("DSPChassis", "setSafeLaserMute",realKey,cheackEnable)
        except Exception as e:
            Module.setStatus(ScriptStatus.FAILED)
            Trace.log(f"setSafeLaserMute error: {str(e)}")
            return {"code": -2, "msg": f"system error: {str(e)}"}

        else:
            Module.setStatus(ScriptStatus.FINISHED)
            return {"code": 0, "msg": "success"}


def script_config_callback():
    """脚本配置参数修改回调"""
    Trace.log("script_config_callback() - 激光配置参数更新")
    ConfigParams.load_config()


def robot_device_callback(change_devices: List[str]):
    Trace.log(f"robot_device_callback({change_devices})")
    for device in change_devices:
        if device == "Laser":
            Trace.log("激光设备参数更新，重新加载配置")
            ConfigParams.load_config()



def main():
    ConfigParams.init()
    ScriptParam.setConfigChangeCallBack(script_config_callback)
    Module.init(script_type=ScriptType.TASK)

    RobotParam.setDeviceChangeCallBack(robot_device_callback)
    laser_controller = LaserSafeController()
    count=0
    while True:
        status = Module.getStatus()          
        if status in (ScriptStatus.RUNNING, ScriptStatus.NONE):
            args = Module.getTaskArgs()

            validated_params={}
            # args={
            #         "key": "Laser-001",
            #         "enable": True,
            #     }
            if args:
                try:
                    Trace.log(f"接收到激光控制任务: {json.dumps(args, indent=2)}")
                    validated_params = script_param.loadInput(args)
                    print(validated_params)
                except ValueError as e:
                    Trace.log(f"参数验证失败: {e}")
                    break
                laser_controller.handle_robot_control_request(validated_params)
            else:
                Trace.log(f"激光参数为空")
                count+=1
                if count>10:
                    Trace.log(f"激光参数为空，超过10次未收到任务,")
                    break
        elif status in (ScriptStatus.FAILED, ScriptStatus.FINISHED):
            if status == ScriptStatus.FAILED:
                Trace.log(f"激光控制任务 {Module.getStatus()} 失败")
            else:
                Trace.log(f"激光控制任务 {Module.getStatus()} 完成")
            Module.setStatus(ScriptStatus.NONE)
            break

        # 防止CPU占用过高
        time.sleep(0.1)


if __name__ == '__main__':
    main()