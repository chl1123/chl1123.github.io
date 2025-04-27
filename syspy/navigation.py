import math
import typing
from typing import Tuple

from .lib.py_rpc import Service, Message, call_service, default_plugin

if typing.TYPE_CHECKING:
    from .protobuf import Message_MotorCmd


@default_plugin("MoveFactory")
class Navigation(Service):
    """导航类"""

    @classmethod
    @call_service()
    def resetPath(cls):
        """让agv沿着规划的线路行驶"""
        pass

    @classmethod
    @call_service()
    def goPathParam(cls, params: dict):
        """ """
        pass

    @classmethod
    @call_service()
    def getLM(cls, name: str, flag: bool) -> list:
        """获取点位坐标

        Args:
            name (str): 站点或者库位名称
            flag (bool): True 返回的坐标是地图坐标系， False返回的坐标是机器人坐标系

        Returns:
            list: 0-> x (m); 1->y (m); 2->theta (rad); 3-> id (-1 表示不存在)
        """
        pass

    @classmethod
    @call_service()
    def runOdoMove(cls, params: dict):
        """执行按里程运动的任务

        Args:
            params (dict):
        """
        pass

    @classmethod
    @call_service()
    def clearGoodsShape(cls):
        """去除agv身上的状态"""
        pass

    @classmethod
    @call_service()
    def getCurrentAdvancedArea(cls) -> dict:
        """机器人运行时，当前所在高级区域的属性

        Returns:
            dict:
        """
        pass

    @classmethod
    @call_service()
    def getCurrentPathProperty(cls) -> dict:
        """机器人运行时，当前路线上的属性

        Returns:
            dict:
        """
        pass

    @classmethod
    @call_service()
    def getGoodsName(cls) -> str:
        """

        Returns:
        """
        pass

    @classmethod
    @call_service()
    def getMinDynamicObs(cls) -> list:
        """获得离机器最近的一个动态障碍物坐标。 如果没有障碍物反馈0.,0.

        Returns:
            list: 两个元素，分别为x,y。单位为m
        """
        pass

    @classmethod
    @call_service()
    def getTargetPGVParam(cls) -> dict:
        """

        Returns:
            dict:
        """
        pass

    @classmethod
    @call_service()
    def goForkPath(cls):
        """叉车依据规划的路径导航，需要先调用 resetGoForkPath"""
        pass

    @classmethod
    @call_service()
    def goForkUseStraightLine(cls):
        """ """
        pass

    @classmethod
    @call_service()
    def goMapPath(cls) -> int:
        """按地图路线行走"""
        pass

    @classmethod
    @call_service()
    def goPath(cls):
        """控制AGV移动"""
        pass

    @classmethod
    @call_service()
    def goPGVRun(cls, params: dict) -> int:
        """按地图路线行走

        Args:
            params (dict):

        Returns:
            int:
        """
        pass

    @classmethod
    @call_service()
    def hasGoods(cls) -> bool:
        """获取身上是否有货物的状态

        Returns:
            bool: 是否有货物
        """
        pass

    @classmethod
    @call_service()
    def inSpin(cls) -> bool:
        """是否在随动"""
        pass

    @classmethod
    @call_service()
    def isPathReached(cls) -> bool:
        """agv是否完成线路

        Returns:
            bool: 如果完成则返回True
        """
        pass

    @classmethod
    @call_service()
    def laserCollision(cls, ids: list) -> bool:
        """检测激光点是否和自身碰撞

        Returns:
            bool: 激光点是否和自身碰撞
        """
        pass

    @classmethod
    @call_service()
    def moveTask(cls) -> dict:
        """获得任务信息以字典类型返回

        Returns:
            dict: 具体的任务信息
        """
        pass

    @classmethod
    @call_service()
    def openSpeed(cls, vx: float, vy: float, vw: float):
        """让agv按vx,vy,vw行走，此函数考虑了碰撞检测"""
        pass

    @classmethod
    @call_service()
    def resetGoForkPath(
            cls,
            x: float,
            y: float,
            yaw: float,
            back_dist: float,
            min_ahead_dist: float,
            ahead_dist: float,
    ):
        """重置叉车去往识别点的路径规划

        Args:
            x (float): 终点x坐标 m
            y (float): 终点y坐标 m
            yaw (float): 终点角度坐标 rad
            back_dist (float): 到终点后的后退距离
            min_ahead_dist (float): 栈板前直线距离 m
            ahead_dist (float): 到终点前的直线距离
        """
        pass

    @classmethod
    @call_service()
    def resetGoMapPath(cls):
        """行走的动作"""
        pass

    @classmethod
    @call_service()
    def resetGoPGV(cls):
        """ """
        pass

    @classmethod
    @call_service()
    def resetLocalShelfArea(cls):
        """取消顶升上的货架"""
        pass

    @classmethod
    @call_service()
    def resetOdoMove(cls):
        """ """
        pass

    @classmethod
    @call_service()
    def setBlockReason(cls, collision_type: int, x: float, y: float, id: int):
        """设置阻挡原因

        Args:
            collision_type (int): 阻挡原因见rbk.py脚本中的CollisionType类
            x (float): 障碍物位置
            y (float): 障碍物位置
            id (float): 障碍物id
        """
        pass

    @classmethod
    @call_service()
    def setGlobalSpinAngle(cls, angle: float, direction: int):
        """

        Args:
            angle (float):
            direction (int):
        """
        pass

    @classmethod
    @call_service()
    def setGoForkForkPos(cls, x: float, y: float, theta: float, hold_dir: float):
        """重置叉车去往识别点的路径规划

        Args:
            x (float): 货叉相对于里程中心的 x 轴坐标 m
            y (float): 货叉相对于里程中心的 y 轴坐标 m
            theta (float): 是货叉相对于里程中心的偏移角度 rad
            hold_dir (float): 是车体的横移角度 单位：°

        """
        pass

    @classmethod
    @call_service()
    def setGoodsShape(cls, head: float, tail: float, width: float):
        """设置货物形状，并且告诉rbk车上装载有货物了。
           如果head,tail, width都小于等于0，则没有货物形状。
           货物的0，0点与小车的0，0点一样

        Args:
            head (float): 货物头部长度
            tail (float): 货物的尾部长度
            width (float): 货物的宽度
        """
        pass

    @classmethod
    @call_service()
    def setGoodsShapeWithName(
            cls, head: float, tail: float, width: float, recfile: str
    ):
        """设置货物形状时传入识别文件路径

        Args:
            head (float):
            tail (float):
            width (float):
            recfile (str):
        """
        pass

    @classmethod
    @call_service()
    def setIncreaseSpinAngle(cls, angle: float):
        """设置货物形状时传入识别文件路径

        Args:
            angle (float):
        """
        pass

    @classmethod
    @call_service()
    def setLocalShelfArea(cls, object_model_path: str) -> bool:
        """加载顶升上的货物模型

        Args:
            object_model_path (str): 货架模型文件名称

        Returns:
            bool: 如果不存在这个货架模型则报错
        """
        pass

    @classmethod
    @call_service()
    def setObsStopDist(cls, dist: float):
        """设置避障距离

        Args:
            dist (float): 避障距离，单位 m
        """
        pass

    @classmethod
    @call_service()
    def setPathBackMode(cls, a: bool) -> None:
        """路径导航是否倒走

        Args:
            a (bool): 如果倒走则为True

        """
        pass

    @classmethod
    @call_service()
    def setPathHoldDir(cls, a: float):
        """路径导航的 hold_dir

        Args:
            a (float): 单位度

        """
        pass

    @classmethod
    @call_service()
    def setPathMaxRot(cls, a: float):
        """路径导航的最大角速度

        Args:
            a (float): 单位rad/s

        """
        pass

    @classmethod
    @call_service()
    def setPathMaxSpeed(cls, a: float):
        """路径导航的最大速度

        Args:
            a (float): 单位m/s

        """
        pass

    @classmethod
    @call_service()
    def setPathOnRobot(cls, x: list, y: list, angle: float):
        """让agv在agv坐标系下以特定线路行走

        Args:
            x (list): 线路的x坐标
            y (list): 线路的y坐标
            angle (float): 终点的朝向
        """
        pass

    @classmethod
    @call_service()
    def setPathOnWorld(cls, x: list, y: list, angle: float):
        """让agv在世界坐标系下以特定线路行走

        Args:
            x (list): 线路的x坐标
            y (list): 线路的y坐标
            angle (float): 终点的朝向
        """
        pass

    @classmethod
    @call_service()
    def setPathReachAngle(cls, a: float):
        """路径导航的到点角度精度

        Args:
            a (float): 单位rad

        """
        pass

    @classmethod
    @call_service()
    def setPathReachDist(cls, a: float) -> None:
        """路径导航的到点精度

        Args:
            a (float): 单位m
        """
        pass

    @classmethod
    @call_service()
    def setPathUseOdo(cls, a: bool):
        """路径导航是否用里程定位

        Args:
            a (bool): 如果用里程定位则为True
        """
        pass

    @classmethod
    @call_service()
    def setRobotSpinAngle(cls, angle: float, direction: int):
        """

        Args:
            angle (float):
            direction (int):
        """
        pass

    @classmethod
    @call_service()
    def setSafeOssdSwitch(cls, id: int, ossdRegion: int):
        """

        Args:
            id:
            ossdRegion:
        """
        pass

    @classmethod
    @call_service()
    def setSafeZone(
            cls,
            zoneType: int,
            maxSpeed: float,
            autoRestart: bool,
            muteAudio: bool,
            muteEnable: bool,
    ):
        """

        Args:
            zoneType:
            maxSpeed:
            autoRestart:
            muteAudio:
            muteEnable:
        """
        pass

    @classmethod
    @call_service()
    def setSteerAngle(cls, name: str, angle: float) -> bool:
        """转动舵角

        Args:
            name (str): 舵机名称
            angle (float): 角度位置, 单位rad

        Returns:
            bool: 如果为True电机到位
        """
        pass

    @classmethod
    @call_service()
    def spinRun(cls) -> bool:
        """

        Returns:
            bool:
        """
        pass

    @classmethod
    @call_service()
    def stopRobot(cls, flag: bool):
        """让agv停下来

        Args:
            flag (bool): 如果是True就是急停，如果是False则以StopAcc停下来
        """
        pass


@default_plugin("MoveFactory")
class NavStatus(Message["Message_MoveStatus"]):
    """导航状态类"""

    _TOPIC = "rbk.protocol.Message_MoveStatus"
    _PLUGIN = "MoveFactory"
    _MODEL_CLASS = None
    not_stop_counts = 0

    @classmethod
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import Message_MoveStatus
            cls._MODEL_CLASS = Message_MoveStatus

    @classmethod
    @call_service("DSPChassis")
    def getChassisStop(cls) -> bool:
        """底盘是否停止（仅通过walk电机判断）

        Returns:
            bool: 如果行走电机停止则为True
        """
        is_stop = cls.client().call_service("DSPChassis", "getChassisStop")
        if is_stop:
            is_stop = True
        else:
            if cls.not_stop_counts >= 1:
                is_stop = False
                cls.not_stop_counts = 0
            else:
                # 非停止状态计数
                cls.not_stop_counts += 1
        return is_stop

    @classmethod
    def get_block(cls):
        if cls.update():
            return cls.data.blocked

    @classmethod
    def get_turn(cls, v_x, v_w):
        turn = 0
        if v_w >= math.radians(1) * 3:
            '''机身左旋'''
            if v_x > 0.0:
                '''机身左旋+前进'''
                turn = 1
            elif v_x < 0.0:
                '''机身左旋+后退'''
                turn = 2
            else:
                """机身原地左旋"""
                turn = 3
        elif v_w <= math.radians(-1) * 3:
            """机身右旋"""
            if v_x > 0.0:
                """机身右旋+前进"""
                turn = 2
            elif v_x < 0.0:
                """机身右旋+后退"""
                turn = 1
            else:
                """机身原地右旋"""
                turn = 3
        return turn


class NavSpeed(Message["Message_NavSpeed"]):
    """导航速度类"""

    _TOPIC = "rbk.protocol.Message_NavSpeed"
    _PLUGIN = "MoveFactory"
    _MODEL_CLASS = None

    @classmethod
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import Message_NavSpeed
            cls._MODEL_CLASS = Message_NavSpeed

    @classmethod
    def get_speeds(cls) -> Tuple[float, float, float]:
        if cls.update():
            return cls.data.x, cls.data.y, cls.data.rotate

    @classmethod
    def get_motor_cmd(cls) -> typing.List["Message_MotorCmd"]:
        """获取电机指令列表

        Returns:
            typing.List[Message_MotorCmd]: 返回电机指令列表
        """
        if cls.update():
            return cls.data.motor_cmd

    @classmethod
    def get_is2move(cls) -> bool:
        """获取是否准备移动的标志位

        Returns:
            bool: True表示准备移动，False表示未准备移动
        """
        if cls.update():
            return cls.data.is2move
