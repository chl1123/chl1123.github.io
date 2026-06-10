# -*- coding: utf-8 -*-
# @Date: 2026/02/04
# @Project: 3.5版本电机控制任务脚本
import json
import time
from typing import Union, Dict, Optional, Any, TYPE_CHECKING
from abc import ABC

from syspy.core.rbk_rpc import Message, RBKVersionError

start_time = time.time()
from typing import List
from syspy import Module, ScriptStatus, Trace, RobotParam, ScriptParam, RBK_VERSION
from syspy.utils.param_server import ParamType
from syspy.utils import ScriptType
from syspy.core.rbk_rpc import Service

if hasattr(ScriptParam, '_instance'):
    ScriptParam._instance = None 
    ScriptParam._initialized = False
    ScriptParam.config_change_callback = None
    ScriptParam.event_task_config = False
# 实例化脚本参数，用于创建和加载脚本配置参数和任务参数
script_param = ScriptParam(__file__)


class ConfigParams:
    """脚本配置参数定义"""
    device_name_key_map = None
    simulation = None

    @classmethod
    def init(cls):
        builder = script_param.builderConfig()
        with builder.GROUPS():
            with builder.GROUP(key="motor_config", name="电机配置", desc="电机控制相关配置"):
                builder.TYPE(ParamType.ARRAY)

                with builder.CHILDREN():
                    with builder.CHILD(key="simulation", name="仿真模式", 
                                       desc="是否启用仿真模式，True为仿真，False为真实控制"):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(False)


                    with builder.CHILD(key="device_name_key_map", name="电机名称映射",
                                       desc="电机名称到设备key的映射，JSON格式"):
                        builder.TYPE(ParamType.STRING)
                        builder.DEFAULTVALUE('{"motor_name_001": "motor__001", "motor_name_002": "motor_002"}')

        # 保存配置参数，和原参数文件合并
        builder.save(merge=True)
        cls.load_config()

    @classmethod
    def load_config(cls):
        """重新加载配置参数"""
        config = script_param.loadConfig()
        Trace.log(f"Loaded motor config: {config}")
        cls.simulation = config.get("simulation", False)
        try:
            cls.device_name_key_map = json.loads(config.get("device_name_key_map", "{}"))
            print(cls.device_name_key_map)
        except json.JSONDecodeError:
            cls.device_name_key_map = {"motor_name_001": "motor__001", "motor_name_002": "motor_002"}
            Trace.log("解析电机名称映射配置失败，使用默认值")



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

if TYPE_CHECKING:
    if RBK_VERSION == 3:
        from syspy.v3.protobuf.message.message_motorinfos_pb2 import msgMotorInfo
    elif RBK_VERSION == 4:
        from v4.protobuf.message.messageV4_movetask_pb2 import MessageV4_MInfo as msgMotorInfo

class MotorInterface(ABC,Message):
    """电机类"""

    @staticmethod
    def getMotorInfos() -> List["msgMotorInfo"]:
        """获取电机信息列表

        Returns:
            (List[msgMotorInfo]): 返回电机信息列表，列表内元素为msgMotorInfo对象

        Examples:
        ```python
        from syspy import Motor
        motorInfos = Motor.getMotorInfos()
        for motorInfo in motorInfos:  # motorInfo为msgMotorInfo的对象
            print(motorInfo.key)
            print(motorInfo.position)
        ```
        """
        raise RBKVersionError()

    @staticmethod
    def getMotorPos(key: str) -> Union[float, int]:
        """获取指定电机的当前位置

        Args:
            key (str): 电机设备的key

        Returns:
            Union[float, int]: 返回电机的当前位置，若电机不存在返回 -1
        """
        raise RBKVersionError()

    @staticmethod
    def getMotorSpeed(key: str) -> Union[float, int]:
        """获取指定电机的当前速度

        Args:
            key (str): 电机设备的key

        Returns:
            Union[float, int]: 返回电机的当前速度，若电机不存在返回 -1
        """
        raise RBKVersionError()

    @classmethod
    def setMotorSpeed(cls, key: str, vel: float, stopDI: str = "") -> bool:
        """让电机以某个速度运行，比如滚筒电机

        Args:
            key (str): 电机设备的key
            vel (float): 电机速度
            stopDI (str): 到位DI。缺省或传""表示没有。

        Returns:
            (bool): 如果不存在这个电机，则返回False
        """
        raise RBKVersionError()

    @classmethod
    def setMotorPosition(cls, key: str, pos: float, maxVel: float, stopDI: str = "") -> bool:
        """控制线性电机到特定位置

        Args:
            key (str): 电机设备的key
            pos (float): 发送目标点位置也可能是角度
            maxVel (float): 运行过程中的最大速度不能超过模型文件中的最大速度
            stopDI (str): 如果这个StopDI触发则表示运动到位。缺省或传""表示没有。

        Returns:
            (bool): 如果不存在这个电机，则返回False
        """
        raise RBKVersionError()

    @classmethod
    def setMotorPositionAdv(cls, name: str, pos: float, maxSpeed: float = None, maxAcc: float = None,
                            maxDec: float = None, jerk: float = None, stopDI: str = "") -> bool:
        """控制线性电机到特定位置（可控制加速度）

        Args:
            key (str): 电机设备的key
            pos (float): 目标点位置
            maxSpeed (float): 最大速度
            maxAcc (float): 最大加速度
            maxDec (float): 最大减速度
            jerk (float): 最大加加速度
            stopDI (str): 停止DI的key。该DI触发则表示运动到位。缺省或传""表示没有。

        Returns:
            (bool): 如果不存在这个电机，则返回False
        """
        raise RBKVersionError()

    @classmethod
    def stopMotor(cls):
        """停止所有非行走的电机"""
        raise RBKVersionError()

    @classmethod
    def resetMotor(cls, key: str) -> bool:
        """将电机重置为不启用状态

        Args:
            key (str): 电机设备的key

        Returns:
            (bool): 如果不存在这个电机则报错
        """
        raise RBKVersionError()

    @classmethod
    def isMotorReached(cls, key: str) -> bool:
        """查看电机是否到位，需要在setMotorPosition或者setMotorSpeed后使用

        Args:
            key (str): 电机设备的key

        Returns:
            (bool): 如果到位则返回True
        """
        raise RBKVersionError()

    @classmethod
    def isMotorPositionReached(cls, key: str, pos: float, stopDI: str = "") -> bool:
        """电机是否到达特定位置

        Args:
            key (str): 电机设备的key
            pos (float): 位置
            stopDI (str): 到位DI。缺省或传""表示没有。

        Returns:
            (bool): 如果到位则返回True
        """
        raise RBKVersionError()

    @classmethod
    def isMotorStop(cls, key: str) -> bool:
        """查询电机是否停止

        Args:
            key (str): 电机设备的key

        Returns:
            (bool): 如果电机不存在则返回False
        """
        raise RBKVersionError()

    @classmethod
    def disableMotor(cls, key: str):
        """电机去使能

        Args:
            key (str): 电机设备的key
        """
        raise RBKVersionError()

    @classmethod
    def enableMotor(cls, key: str):
        """电机使能

        Args:
            key (str): 电机设备的key
        """
        raise RBKVersionError()

    @classmethod
    def motorCalib(cls, key: str):
        """电机标零

        Args:
            key (str): 电机设备的key
        """
        raise RBKVersionError()

    @classmethod
    def motorForceCalib(cls, key: str):
        """

        Args:
            key (str): 电机设备的key
        """
        raise RBKVersionError()

# 根据版本初始化电机实例
try:
    if RBK_VERSION == 3:
        from syspy.v3.motor import MotorV3
        Motor: MotorInterface = MotorV3()
    elif RBK_VERSION == 4:
        from syspy.v4.motor import MotorV4
        Motor: MotorInterface = MotorV4()
    else:
        raise ValueError(f"Unsupported RBK version: {RBK_VERSION}")
except Exception as e:
    Trace.log(f"初始化电机驱动失败: {e}")
    Motor = None


class RobotMotorController:
    def __init__(self, device_name_key_map: Dict[str, str] = {}):
        if not device_name_key_map:
            device_name_key_map = ConfigParams.device_name_key_map
        self.device_name_key_map = device_name_key_map  
        self.simulation = ConfigParams.simulation  
        self.last_response = {"code": 0, "msg": "success"}
        
    def _get_real_key(self, req: Dict[str, Any]) -> str:
        """获取电机的真实key（从key或name）"""
        if "key" in req:
            return ParamCheck.required("key", req)
        
        if "name" in req:
            name = ParamCheck.required("name", req)
            if name not in self.device_name_key_map:
                raise ParamError(f"Device name {name} not found")
            return self.device_name_key_map[name]
        
        raise ParamError("need key or name")

    def handle_robot_control_request(self, req: Dict[str, Any]) -> Dict[str, Any]:
        """处理电机控制请求"""
        try:
            req_type = ParamCheck.required("type", req)
            
            if req_type == "setEnable":
                real_key = self._get_real_key(req)
                enable = ParamCheck.required("enable", req)
                Trace.log(f"setEnable: {real_key}, enable: {enable}")
                if enable:
                    a=Motor.enableMotor(real_key)

                else:
                    Motor.disableMotor(real_key)
                    
                
            elif req_type == "clearEncoder":
                real_key = self._get_real_key(req)
                
                if not self.simulation:
                    # Trace.log(f"clearMotorEncoder接口未提供")
                    Service.client().call_service("DSPChassis", "clearMotorEncoder",real_key)

                else:
                    Trace.log(f"[SIM] clearMotorEncoder: {real_key}")
                                        
            elif req_type == "setMotion":
                motors = ParamCheck.required("motors", req)
                
                if not isinstance(motors, list):
                    try:
                        motors=motors.replace("'", '"')
                        motors = json.loads(motors)
                    except:
                        msg="'motors' type error, expected array"
                        raise ParamError(msg)
                    finally:

                        if not isinstance(motors, list):
                            msg="'motors' type error, expected array"
                            raise ParamError(msg)
                if not motors:
                    msg="'motors' is empty"
                    raise ParamError(msg)
                    
                for motor in motors:
                    can_id = ParamCheck.optional("canId", motor)
                    if can_id is not None:
                        can_id = int(can_id)
                        id_valid = False
                        listMotor=["Motor-000","Motor-001","Motor-002","Motor-003"]
                        for motor_ in listMotor:
                            motor_can_id = RobotParam.getDevice(motor_,"basic.canID")
                            if motor_can_id == can_id:
                                Trace.log(f"--->set motors: {motor_}")
                                id_valid = True
                                break
                        if not id_valid:
                            msg=f"set motors error, motor: {can_id} is not found"
                            raise ParamError(msg)
                            
                        motor_type = ParamCheck.required("type", motor)
                        speed = ParamCheck.optional("speed", motor)
                        pos = ParamCheck.optional("pos", motor)
                        maxVel = ParamCheck.optional("maxVel", motor, 0.0)

                        if speed is not None:
                            # Motor.setMotorSpeed(motor_, speed)
                            Service.client().call_service("DSPChassis", "setMotorSpeed",can_id,motor_type,speed)

                        elif pos is not None:
                            Motor.setMotorPosition(motor_, pos, maxVel)
                            Service.client().call_service("DSPChassis", "setMotorPosition",can_id,motor_type,pos)

                        else:
                            msg=f"set motors error, motor: {can_id} pos and speed is None"
                            raise ParamError(msg)
                
            elif req_type == "setHoming":
                err_msgs = []
                
                if "keys" in req:
                    keys = ParamCheck.required("keys", req)
                    if type(keys) == str:
                        keys = keys.replace("'", '"')
                        keys = json.loads(keys)
                    for key in keys:
                        Motor.motorCalib(key)
                        
                if "names" in req:
                    names = ParamCheck.required("names", req)
                    if type(names) == str:
                        names = names.replace("'", '"')
                        names = json.loads(names)
                    for name in names:
                        if name in self.device_name_key_map:
                            real_key = self.device_name_key_map[name]
                            Motor.motorCalib(real_key)
                        else:
                            err_msgs.append(f"motor {name} not found")
                
                if err_msgs:
                    msg=";".join(err_msgs)
                    raise ParamError(msg)
                                        
            elif req_type == "clearFault":
                real_key = self._get_real_key(req)   
                # Trace.log(f"clearMotorEncoder接口未提供")
                Service.client().call_service("DSPChassis", "clearMotorFault",real_key)
        
            else:
                msg=f"type {req_type} not support"
                raise ParamError(msg)
                
        except Exception as e:
            Module.setStatus(ScriptStatus.FAILED)
            Trace.log(f"setMotors error: {e}")
            return {"code": -1, "msg": str(e)}
        else:
            Module.setStatus(ScriptStatus.FINISHED)
            return {"code": 0, "msg": "success"}


def script_config_callback():
    """脚本配置参数修改回调"""
    Trace.log("script_config_callback() - 电机配置参数更新")
    ConfigParams.load_config()


def robot_device_callback(change_devices: List[str]):
    Trace.log(f"robot_device_callback({change_devices})")
    for device in change_devices:
        if device == "Motor":
            Trace.log("电机设备参数更新，重新加载配置")
            ConfigParams.load_config()


# 任务输入参数定义
class InputParams:
    """脚本任务输入参数定义"""
    builder = script_param.builderInput()

    with builder.GROUPS():
        # 电机控制操作类型
        with builder.GROUP(key="type", name="电机操作", desc="电机控制操作类型"):
            builder.TYPE(ParamType.COMBO_BOX)
            builder.REQUIRED(True)

            with builder.CHILDREN():
                # 设置使能
                with builder.CHILD(key="setEnable", name="设置电机使能", desc="设置电机使能/去使能"):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        with builder.CHILD(key="key", name="电机Key", desc="电机设备Key，与name二选一"):
                            builder.TYPE(ParamType.STRING)
                            builder.REQUIRED(False)
                        with builder.CHILD(key="name", name="电机名称", desc="电机设备名称，与key二选一"):
                            builder.TYPE(ParamType.STRING)
                            builder.REQUIRED(False)
                        with builder.CHILD(key="enable", name="使能状态", desc="True使能，False去使能"):
                            builder.TYPE(ParamType.BOOL)
                            builder.REQUIRED(True)
                            builder.DEFAULTVALUE(True)

                # 清除编码器
                with builder.CHILD(key="clearEncoder", name="清除编码器", desc="清除电机编码器数值"):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        with builder.CHILD(key="key", name="电机Key", desc="电机设备Key，与name二选一"):
                            builder.TYPE(ParamType.STRING)
                            builder.REQUIRED(False)
                        with builder.CHILD(key="name", name="电机名称", desc="电机设备名称，与key二选一"):
                            builder.TYPE(ParamType.STRING)
                            builder.REQUIRED(False)

                # 设置运动
                with builder.CHILD(key="setMotion", name="设置电机运动", desc="控制电机速度或位置"):
                    builder.TYPE(ParamType.ARRAY)

                    with builder.CHILDREN():
                        with builder.CHILD(key="motors", name="电机列表", desc="待设置的电机数组"):
                            builder.TYPE(ParamType.ARRAY)
                            builder.CLONEABLE(True)
                            builder.REQUIRED(True)
                            with builder.CHILDREN():
                                with builder.CHILD(key="canId", name="电机CAN ID", desc="电机CAN ID"):
                                    builder.TYPE(ParamType.UINT32)
                                    builder.REQUIRED(False)  
                                with builder.CHILD(key="type", name="电机类型", desc='"walk"=行走电机(仅支持speed)，"steer"=舵轮电机(仅支持pos)'):
                                    builder.TYPE(ParamType.STRING)
                                    builder.REQUIRED(True)
                                with builder.CHILD(key="speed", name="电机速度", desc="单位m/s，仅walk电机支持"):
                                    builder.TYPE(ParamType.DOUBLE)
                                    builder.REQUIRED(False)
                                with builder.CHILD(key="pos", name="电机位置", desc="单位deg，仅steer电机支持"):
                                    builder.TYPE(ParamType.DOUBLE)
                                    builder.REQUIRED(False)

                # 电机标零
                with builder.CHILD(key="setHoming", name="电机标零", desc="电机回零/标零操作"):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        with builder.CHILD(key="keys", name="电机Key列表", desc="电机设备Key列表，JSON格式"):
                            builder.TYPE(ParamType.ARRAY)
                            builder.DEFAULTVALUE(["Motor_001"])
                            with builder.CHILDREN():
                                builder.TYPE(ParamType.STRING)
                        
                        with builder.CHILD(key="names", name="电机名称列表", desc="电机名称列表，JSON格式"):
                            builder.TYPE(ParamType.ARRAY)
                            builder.DEFAULTVALUE(["motor_name_001"])
                            with builder.CHILDREN():
                                builder.TYPE(ParamType.STRING)

                # 清除故障
                with builder.CHILD(key="clearFault", name="清除故障", desc="清除电机故障状态"):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        with builder.CHILD(key="key", name="电机Key", desc="电机设备Key"):
                            builder.TYPE(ParamType.STRING)
                            builder.REQUIRED(False)
                        with builder.CHILD(key="name", name="电机名称", desc="电机设备名称"):
                            builder.TYPE(ParamType.STRING)
                            builder.REQUIRED(False)

    builder.save()

def dic2lis(flat_data):
    result = {}
    lis = []
    dic1 = {}
    statu = False
    next_lis_name = None
    lis_name = None
    next_key = None
    keys = list(flat_data.keys())
    idx = 0
    while idx < len(keys):
        path_str = keys[idx]
        value = flat_data[path_str]
        paths = path_str.split('.')
        if not statu:
            if value is None:
                last_key = paths[-1]
                if last_key.startswith('_') and last_key[1:].isdigit():
                    statu = True
                    lis_name = paths[-2]
                    next_key = paths
                    if next_lis_name == lis_name:
                        idx += 1
                        continue
                    else:
                        if next_lis_name is not None:
                            result[lis_name] = lis
                            next_lis_name = None
                        next_lis_name = lis_name
                        idx += 1
                        continue
            else:
                result[path_str] = value
                idx += 1
                continue
        else:
            if paths[:-1] == next_key:
                next_len = len(next_key)
                now_str = '.'.join(paths[next_len:])
                dic1[now_str] = value
                idx += 1
                continue
            else:
                statu = False
                if dic1:
                    lis.append(dic1.copy())
                    dic1.clear()
                continue
        idx += 1
    if statu and dic1:
        lis.append(dic1)
    if next_lis_name:
        result[next_lis_name] = lis

    return result
                



              


def main():
    ConfigParams.init()
    ScriptParam.setConfigChangeCallBack(script_config_callback)
    Module.init(script_type=ScriptType.TASK)

    RobotParam.setDeviceChangeCallBack(robot_device_callback)
    motor_controller = RobotMotorController()

    while True:
        status = Module.getStatus()          
        if status in (ScriptStatus.RUNNING, ScriptStatus.NONE):
            args = Module.getTaskArgs()

            print(f'===================================={args}')
            print(status)
            validated_params={}
            # args={
            #         "type": "setEnable",
            #         "type.key": "motor-001",
            #         "type.enable": True,
            #     }
            if args:
                try:
                    Trace.log(f"接收到电机控制任务: {json.dumps(args, indent=2)}")
                    validated_params = script_param.loadInput(args)
                    print(validated_params)
                except ValueError as e:
                    Trace.log(f"参数验证失败: {e},尝试修护")
                    try:
                        a=dic2lis(args)
                        print("修护后参数:",a)
                    except Exception as e:
                        Trace.log(f"修护失败: {e}")
                        return
                    try:
                        validated_params = script_param.loadInput(a)
                    except ValueError as e:
                        Trace.log(f"修护后参数验证失败: {e}")
                        return
            motor_controller.handle_robot_control_request(validated_params)
        elif status in (ScriptStatus.FAILED, ScriptStatus.FINISHED):
            if status == ScriptStatus.FAILED:
                Trace.log(f"电机控制任务 {Module.getStatus()} 失败")
            else:
                Trace.log(f"电机控制任务 {Module.getStatus()} 完成")
            Module.setStatus(ScriptStatus.NONE)
            break

        # 防止CPU占用过高
        time.sleep(0.1)


if __name__ == '__main__':
    main()





    # {'motors': [{'canId': 2, 'speed': 0.3, 'type': 'walk'}, {'canId': 1, 'speed': 0.3, 'type': 'walk'}], 'type': 'setMotion'}
    # {'type': 'setMotion', 'type.setMotion.motors': [{'canId': 1, 'speed': 0.3, 'type': 'walk'}, {'canId': 2, 'speed': 0.3, 'type': 'walk'}]}