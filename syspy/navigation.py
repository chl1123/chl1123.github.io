import typing
from typing import Tuple, List
from abc import ABC
from syspy.core.rbk_rpc import Service, Message, RBKVersionError
from syspy import RBK_VERSION
from syspy.utils import Coordinate

if typing.TYPE_CHECKING:
    if RBK_VERSION == 3:
        from syspy.v3.protobuf import msgMotorCmd
        from syspy.v3.protobuf import msgMoveStatus
    elif RBK_VERSION == 4:
        pass


class NavigationInterface(ABC, Service):
    """导航类"""

    @classmethod
    def resetPath(cls):
        """让agv沿着规划的线路行驶"""
        raise RBKVersionError()

    @classmethod
    def goPathParam(cls, params: dict):
        """ """
        raise RBKVersionError()

    @classmethod
    def getLM(cls, name: str, flag: bool) -> list:
        """获取点位坐标

        Args:
            name (str): 站点或者库位名称
            flag (bool): True 返回的坐标是地图坐标系， False返回的坐标是机器人坐标系

        Returns:
            （list): 0-> x (m); 1->y (m); 2->theta (rad); 3-> id (-1 表示不存在)
        """
        raise RBKVersionError()

    @classmethod
    def runOdoMove(cls, params: dict):
        """执行按里程运动的任务

        Args:
            params (dict):
        """
        raise RBKVersionError()

    @classmethod
    def clearGoodsShape(cls):
        """去除agv身上的状态"""
        raise RBKVersionError()

    @classmethod
    def getCurrentAdvancedArea(cls) -> dict:
        """机器人运行时，当前所在高级区域的属性

        Returns:
            (dict):
        """
        raise RBKVersionError()

    @classmethod
    def getCurrentPathProperty(cls) -> dict:
        """机器人运行时，当前路线上的属性

        Returns:
            (dict):
        """
        raise RBKVersionError()

    @classmethod
    def getGoodsName(cls) -> str:
        """

        Returns:
        """
        raise RBKVersionError()

    @classmethod
    def getMinDynamicObs(cls) -> list:
        """获得离机器最近的一个动态障碍物坐标。 如果没有障碍物反馈0.,0.

        Returns:
            （list): 两个元素，分别为x,y。单位为m
        """
        raise RBKVersionError()

    @classmethod
    def getTargetPGVParam(cls) -> dict:
        """

        Returns:
            (dict):
        """
        raise RBKVersionError()

    @classmethod
    def goForkPath(cls):
        """叉车依据规划的路径导航，需要先调用 resetGoForkPath"""
        raise RBKVersionError()

    @classmethod
    def goForkUseStraightLine(cls):
        """ """
        raise RBKVersionError()

    @classmethod
    def goMapPath(cls) -> int:
        """按地图路线行走"""
        raise RBKVersionError()

    @classmethod
    def goPath(cls):
        """控制AGV移动"""
        raise RBKVersionError()

    @classmethod
    def goPGVRun(cls, params: dict) -> int:
        """code二次调整

        Args:
            params (dict):

        Returns:
            (int)
        """
        raise RBKVersionError()

    @classmethod
    def hasGoods(cls) -> bool:
        """获取身上是否有货物的状态

        Returns:
            (bool): 是否有货物
        """
        raise RBKVersionError()

    @classmethod
    def inSpin(cls) -> bool:
        """是否在随动"""
        raise RBKVersionError()

    @classmethod
    def isPathReached(cls) -> bool:
        """agv是否完成线路

        Returns:
            (bool): 如果完成则返回True
        """
        raise RBKVersionError()

    @classmethod
    def laserCollision(cls, ids: list) -> bool:
        """检测激光点是否和自身碰撞

        Returns:
            (bool): 激光点是否和自身碰撞
        """
        raise RBKVersionError()

    @classmethod
    def moveTask(cls) -> dict:
        """获得任务信息以字典类型返回

        Returns:
            (dict): 具体的任务信息
        """
        raise RBKVersionError()

    @classmethod
    def realTimeMoveTask(cls) -> dict:
        """获得任务信息以字典类型返回

        Returns:
            (dict): 具体的任务信息
        """
        raise RBKVersionError()

    @classmethod
    def getBinTask(cls, bin_name: str, task_key: str) -> dict:
        """获取库位任务
        Args:
        bin_name (str): 库位名称
        task_key (str): 库位任务的键
        Returns:
        (str): 库位任务的值
        """
        raise RBKVersionError()


    @classmethod
    def openSpeed(cls, vx: float, vy: float, vw: float):
        """让agv按vx,vy,vw行走，此函数考虑了碰撞检测"""
        raise RBKVersionError()

    @classmethod
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
        raise RBKVersionError()

    @classmethod
    def resetGoMapPath(cls):
        """行走的动作"""
        raise RBKVersionError()

    @classmethod
    def resetGoPGV(cls):
        """ """
        raise RBKVersionError()

    @classmethod
    def resetLocalShelfArea(cls):
        """取消顶升上的货架"""
        raise RBKVersionError()

    @classmethod
    def resetOdoMove(cls):
        """ """
        raise RBKVersionError()

    @classmethod
    def setBlockReason(cls, collision_type: int, x: float, y: float, key: str):
        """设置阻挡原因

        Args:
            collision_type (int): 阻挡原因见syspy/lib/module.py脚本中的CollisionType类
            x (float): 障碍物位置
            y (float): 障碍物位置
            key (str): 障碍物key
        """
        raise RBKVersionError()

    @classmethod
    def setGlobalSpinAngle(cls, angle: float, direction: int):
        """

        Args:
            angle (float):
            direction (int):
        """
        raise RBKVersionError()

    @classmethod
    def setGoForkForkPos(cls, x: float, y: float, theta: float, hold_dir: float):
        """重置叉车去往识别点的路径规划

        Args:
            x (float): 货叉相对于里程中心的 x 轴坐标 m
            y (float): 货叉相对于里程中心的 y 轴坐标 m
            theta (float): 是货叉相对于里程中心的偏移角度 rad
            hold_dir (float): 是车体的横移角度 单位: °
        """
        raise RBKVersionError()

    @classmethod
    def setGoodsShape(cls, head: float, tail: float, width: float):
        """设置货物形状，并且告诉rbk车上装载有货物了。
           如果head,tail, width都小于等于0，则没有货物形状。
           货物的0，0点与小车的0，0点一样

        Args:
            head (float): 货物头部长度
            tail (float): 货物的尾部长度
            width (float): 货物的宽度
        """
        raise RBKVersionError()

    @classmethod
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
        raise RBKVersionError()

    @classmethod
    def setGoodsPolyShape(
            cls, shape, recfile: str
    ):
        """设置货物形状时传入识别文件路径
            shape = [
            {"x": 1.0, "y": 1.0},
            {"x": -1.0, "y": 1.0},
            {"x": -1.0, "y": -1.0},
            {"x": 1.0, "y": 1.0}]

        Args:
            shape (List[Dict[str, float]]):
            recfile (str):
        """
        raise RBKVersionError()

    @classmethod
    def setIncreaseSpinAngle(cls, angle: float):
        """增量旋转托盘到一个弧度

        Args:
            angle (float): 弧度
        """
        raise RBKVersionError()

    @classmethod
    def setLocalShelfArea(cls, object_model_path: str) -> bool:
        """加载顶升上的货物模型

        Args:
            object_model_path (str): 货架模型文件名称

        Returns:
            (bool): 如果不存在这个货架模型则报错
        """
        raise RBKVersionError()

    @classmethod
    def setObsStopDist(cls, dist: float):
        """设置避障距离

        Args:
            dist (float): 避障距离，单位 m
        """
        raise RBKVersionError()

    @classmethod
    def setPathBackMode(cls, a: bool) -> None:
        """路径导航是否倒走

        Args:
            a (bool): 如果倒走则为True

        """
        raise RBKVersionError()

    @classmethod
    def setPathHoldDir(cls, a: float):
        """路径导航的 hold_dir

        Args:
            a (float): 单位度

        """
        raise RBKVersionError()

    @classmethod
    def setPathMaxRot(cls, a: float):
        """路径导航的最大角速度

        Args:
            a (float): 单位rad/s

        """
        raise RBKVersionError()

    @classmethod
    def setPathMaxSpeed(cls, a: float):
        """路径导航的最大速度

        Args:
            a (float): 单位m/s

        """
        raise RBKVersionError()

    @classmethod
    def setPathOnRobot(cls, x: list, y: list, angle: float):
        """让agv在agv坐标系下以特定线路行走

        Args:
            x (list): 线路的x坐标
            y (list): 线路的y坐标
            angle (float): 终点的朝向
        """
        raise RBKVersionError()

    @classmethod
    def setPathOnWorld(cls, x: list, y: list, angle: float):
        """让agv在世界坐标系下以特定线路行走

        Args:
            x (list): 线路的x坐标
            y (list): 线路的y坐标
            angle (float): 终点的朝向
        """
        raise RBKVersionError()

    @classmethod
    def setPathReachAngle(cls, a: float):
        """路径导航的到点角度精度

        Args:
            a (float): 单位rad

        """
        raise RBKVersionError()

    @classmethod
    def setPathReachDist(cls, a: float) -> None:
        """路径导航的到点精度

        Args:
            a (float): 单位m
        """
        raise RBKVersionError()

    @classmethod
    def setPathUseOdo(cls, a: bool):
        """路径导航是否用里程定位

        Args:
            a (bool): 如果用里程定位则为True
        """
        raise RBKVersionError()

    @classmethod
    def setRobotSpinAngle(cls, angle: float, direction: int):
        """

        Args:
            angle (float):
            direction (int):
        """
        raise RBKVersionError()

    @classmethod
    def setSafeOssdSwitch(cls, laser_key: str, ossdRegion: int):
        """设置OSSD区域组切换

        Args:
            laser_key (str): 激光设备的key。""表示选择全部激光。
            ossdRegion (int): 表示需要切换到的OSSD区域组，0代表未载货或者载小货，1代表已载货或者载大货
        """
        raise RBKVersionError()

    @classmethod
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
        raise RBKVersionError()

    @classmethod
    def setSteerAngle(cls, name: str, angle: float, action_name: str = "") -> bool:
        """转动舵角

        Args:
            name (str): 舵机名称
            angle (float): 角度位置, 单位rad
            action_name (str): 动作名。缺省为""

        Returns:
            (bool): 如果为True电机到位
        """
        raise RBKVersionError()

    @classmethod
    def spinRun(cls) -> bool:
        """

        Returns:
            (bool):
        """
        raise RBKVersionError()

    @classmethod
    def stopRobot(cls, flag: bool):
        """让agv停下来

        Args:
            flag (bool): 如果是True就是急停，如果是False则以StopAcc停下来
        """
        raise RBKVersionError()

    @classmethod
    def stopRobotNow(cls):
        """让agv立即停下来"""
        raise RBKVersionError()

    @classmethod
    def calibRecord(cls) -> bool:
        """XXX

        Returns:
            (bool): 数据记录成功
        """
        raise RBKVersionError()

    @classmethod
    def wheelBaseShift(cls, flag: bool) -> bool:
        """变轴距标定时,触发MF中的模型变化响应

        Args:
            flag (bool): False:放下货叉， True:抬起货叉

        Returns:
            (bool): 是否完成
        """
        raise RBKVersionError()

    @classmethod
    def recordCapture(cls, fileName: str, filePath: str, cameraKey: str) -> bool:
        """相机标定时,触发图像采集

        Args:
            fileName (str): 文件名称
            filePath (str): 文件保存路径
            cameraKey (str): 相机设备的key

        Returns:
            (bool): 是否完成
        """
        raise RBKVersionError()

    @classmethod
    def appendPolicy(cls, name: str):
        """增加策略

        Args:
            name (str): 策略名

        Examples:
            >>> Navigation.appendPolicy("policy1")  # 切换到"policy1"策略
        """
        raise RBKVersionError()

    @classmethod
    def appendCustomPolicy(cls, name: str, params: dict):
        """增加策略参数

        Args:
            name (str): 策略名
            params (dict): 待增加的策略参数，没有指定的参数保留旧值

        Examples:
            >>> new_params = {
            ...     "navigation.basic.load.loadMaxSpeed":1,
            ...     "direction": "left"
            ... }
            >>> # 自定义策略"policy2"，修改参数Navigation.basic.load.loadMaxSpeed和direction的值
            >>> Navigation.appendCustomPolicy("policy2", new_params)
        """
        raise RBKVersionError()

    @classmethod
    def clearPolicy(cls):
        """清除策略

        Examples:
            >>> Navigation.clearPolicy()  # 清除当前策略
        """
        raise RBKVersionError()

    @classmethod
    def setClearRegion(cls, name: str, x: typing.List[float], y: typing.List[float], lasers_key: typing.List[str], coordinate: Coordinate):
        """
        设置避障扣除区域。

        Args:
            name (str): 区域名称。
            x (List[float]): 区域顶点的x坐标列表。
            y (List[float]): 区域顶点的y坐标列表。
            lasers_key (List[str]): 激光传感器键值列表。
            coordinate (Coordinate): 区域坐标系。Coordinate.ROBOT 或 Coordinate.WORLD。
        """
        raise RBKVersionError()

    @classmethod
    def deleteClearRegion(cls, name: str, coordinate: Coordinate):
        """
        删除避障扣除区域。

        Args:
            name (str): 要删除的区域名称。
            coordinate (Coordinate): 区域坐标系。Coordinate.ROBOT 或 Coordinate.WORLD。
        """
        raise RBKVersionError()

    @classmethod
    def getClearRegion(cls, coordinate: Coordinate) -> typing.List[str]:
        """
        获取避障扣除区域。

        Args:
            coordinate (Coordinate): 区域坐标系。Coordinate.ROBOT 或 Coordinate.WORLD。

        Returns:
            (List[str]): 避障扣除区域名称列表。
        """
        raise RBKVersionError()

    @classmethod
    def collisionDetection(cls, device_keys: List[str], x: List[float], y: List[float]) -> bool:
        """检测指定传感器设备与指定机器人坐标系下的区域是否发生碰撞

        Args:
            device_keys (List[str]): 参与碰撞检测的传感器（支持相机、激光、距离传感器）列表。（如["Laser-000", "Camera-001"]表示使用key为"Laser-000", "Camera-001"的传感器）
            x (List[float]): 区域顶点的x坐标列表。
            y (List[float]): 区域顶点的y坐标列表。

        Returns:
            (bool): 碰撞检测结果。发生碰撞返回True，未碰撞返回False

        Raises:
            ValueError: device_keys只支持"Laser"、"Camera"和"DistanceSensor"
        """
        raise RBKVersionError()

    @classmethod
    def calTCPTrans(cls, x: float, y: float, theta: float, tcp_name: str) -> typing.Dict:
        """将目标点增加TCP坐标系补偿

        Args:
            x (float): 目标点的 x 坐标（单位: 米）
            y (float): 目标点的 y 坐标（单位: 米）
            theta (float): 目标点的角度（单位: 弧度）
            tcp_name (str): TCP 名称，若不存在TCP 名称，则返回原始的目标点不进行TCP变换

        Returns:
            (typing.Dict): 包含转换后的目标点位置信息，格式为 {"x": double, "y": double, "theta": double}
        """
        raise RBKVersionError()

    @classmethod
    def liveRecGoReset(cls, recfile: str, x: float, y: float, theta: float, tracker_id: str, paths: typing.Dict) -> bool:
        """重置实时识别行走路径，用于重新初始化路径跟踪器

        Args:
            recfile (str): 记录文件路径
            x (float): 起始位置的 x 坐标（单位：米）
            y (float): 起始位置的 y 坐标（单位：米）
            theta (float): 起始位置的角度（单位：弧度）
            tracker_id (str): 跟踪器ID
            paths (typing.Dict): 路径数据数组，包含PathData对象的JSON数组

        Returns:
            (bool): 重置是否成功，成功返回true，失败返回false
        """
        raise RBKVersionError()

    @classmethod
    def liveRecGo(cls) -> int:
        """启动实时识别行走任务

        Returns:
            (int): 返回路径状态码，可能的值包括：
            0(NONE-无状态)、1(RUNNING-运行中)、2(NEARTOGOAL-接近目标)、3(FINISHED-已完成)、4(FAILED-失败)、5(SUSPENDED-暂停)。
            若m_live_go_path为空则返回FAILED(4)
        """
        raise RBKVersionError()

    @classmethod
    def getRecPath(cls, robot_pos_x: float, robot_pos_y: float, robot_pos_theta: float, rec_x: float, rec_y: float,
                   rec_theta: float, back_dist: float, min_ahead_dist: float, ahead_dist: float, back_mode: bool,
                   use_bezier: bool, hold_dir: float, max_speed: float, slow_down_dist: float, slow_down_speed: float,
                   liveRec: bool) -> typing.Dict:
        """根据机器人当前位置和识别位置生成路径，支持贝塞尔曲线和直线路径两种模式

        Args:
            robot_pos_x (float): 机器人当前位置的 x 坐标（单位：米）
            robot_pos_y (float): 机器人当前位置的 y 坐标（单位：米）
            robot_pos_theta (float): 机器人当前位置的角度（单位：弧度）
            rec_x (float): 识别位置的 x 坐标（单位：米）
            rec_y (float): 识别位置的 y 坐标（单位：米）
            rec_theta (float): 识别位置的角度（单位：弧度）
            back_dist (float): 后退距离（单位：米）
            min_ahead_dist (float): 最小前进距离（单位：米）
            ahead_dist (float): 前进距离（单位：米）
            back_mode (bool): 是否使用后退模式
            use_bezier (bool): 是否使用贝塞尔曲线路径
            hold_dir (float): 保持方向角度（单位：弧度），若为999则不保持方向
            max_speed (float): 最大速度（单位：米/秒）
            slow_down_dist (float): 减速距离（单位：米）
            slow_down_speed (float): 减速速度（单位：米/秒）
            liveRec (bool): 是否为实时识别模式

        Returns:
            (typing.Dict): 包含路径数据的JSON数组
        """
        raise RBKVersionError()

    @classmethod
    def cancelLiveRecGo(cls):
        """取消当前正在执行的实时识别行走任务
        """
        raise RBKVersionError()

    @classmethod
    def getLiveResult(cls) -> typing.Dict:
        """获取实时识别行走任务的结果
        Returns:
            (typing.Dict): 包含任务执行结果的JSON对象，若任务不存在则返回空JSON
        """
        raise RBKVersionError()


class NavStatusInterface(ABC, Message):
    """导航状态类"""

    @classmethod
    def getChassisStop(cls) -> bool:
        """底盘是否停止（仅通过walk电机判断）

        Returns:
            (bool): 停止为True, 否则为False
        """
        raise RBKVersionError()

    @classmethod
    def getBlock(cls):
        raise RBKVersionError()

    @classmethod
    def getTurn(cls, v_x, v_w):
        raise RBKVersionError()

    @classmethod
    def getTaskStatus(cls) -> "msgMoveStatus.taskStatus":
        """获取任务状态

        Returns:
            (msgMoveStatus.TaskStatus): 返回任务状态
        """
        raise RBKVersionError()

    @classmethod
    def getRunningStatus(self) -> "msgMoveStatus.runningStatus":
        """获取运行状态

        Returns:
            (msgMoveStatus.runningStatus): 返回运行状态
        """
        raise RBKVersionError()

    @classmethod
    def getCurrentStation(self) -> str:
        """获取机器人当前所在站点

        Returns:
            (str): 机器人站点名
        """
        raise RBKVersionError()


class NavSpeedInterface(ABC, Message):
    """导航速度类"""

    @classmethod
    def getSpeeds(cls) -> Tuple[float, float, float]:
        """获取当前速度信息

        Returns:
            (Tuple[float, float, float]): 包含三个速度分量的元组
                - v_x (float): X轴方向速度，单位 m/s
                - v_y (float): Y轴方向速度，单位 m/s
                - v_w (float): 角速度，单位 rad/s
        """
        raise RBKVersionError()

    @classmethod
    def getMotorCmd(cls) -> typing.List["msgMotorCmd"]:
        """获取电机指令列表

        Returns:
            (typing.List[msgMotorCmd]): 返回电机指令列表
        """
        raise RBKVersionError()

    @classmethod
    def getIs2Move(cls) -> bool:
        """获取是否准备移动的标志位

        Returns:
            (bool): True表示准备移动，False表示未准备移动
        """
        raise RBKVersionError()