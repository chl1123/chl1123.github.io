import math
from typing import Tuple, List, Optional

from syspy.core.rbk_rpc import call_service, default_plugin, RBKVersionError
from ..utils import Coordinate
from syspy.navigation import NavigationInterface, NavStatusInterface, NavSpeedInterface


@default_plugin("Navigation")  # todo RBK4
class NavigationV4(NavigationInterface):
    """导航类"""

    @classmethod
    @call_service()
    def resetPath(cls):
        pass

    @classmethod
    @call_service()
    def goPathParam(cls, params: dict):
        pass

    @classmethod
    @call_service()
    def getLM(cls, name: str, flag: bool) -> list:
        pass

    @classmethod
    @call_service()
    def runOdoMove(cls, params: dict):
        pass

    @classmethod
    @call_service()
    def clearGoodsShape(cls):
        pass

    @classmethod
    @call_service()
    def getCurrentAdvancedArea(cls) -> dict:
        pass

    @classmethod
    @call_service()
    def getCurrentPathProperty(cls) -> dict:
        pass

    @classmethod
    @call_service()
    def getGoodsName(cls) -> str:
        pass

    @classmethod
    @call_service()
    def getMinDynamicObs(cls) -> list:
        pass

    @classmethod
    @call_service()
    def getTargetPGVParam(cls) -> dict:
        pass

    @classmethod
    @call_service()
    def goForkPath(cls):
        pass

    @classmethod
    @call_service()
    def goForkUseStraightLine(cls):
        pass

    @classmethod
    @call_service()
    def goMapPath(cls) -> int:
        pass

    @classmethod
    @call_service()
    def goPath(cls):
        pass

    @classmethod
    @call_service()
    def goPGVRun(cls, params: dict) -> int:
        pass

    @classmethod
    @call_service()
    def hasGoods(cls) -> bool:
        pass

    @classmethod
    @call_service()
    def inSpin(cls) -> bool:
        pass

    @classmethod
    @call_service()
    def isPathReached(cls) -> bool:
        pass

    @classmethod
    @call_service()
    def laserCollision(cls, ids: list) -> bool:
        pass

    @classmethod
    @call_service()
    def moveTask(cls) -> dict:
        pass

    @classmethod
    @call_service()
    def openSpeed(cls, vx: float, vy: float, vw: float):
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
        pass

    @classmethod
    @call_service()
    def resetGoMapPath(cls):
        pass

    @classmethod
    @call_service()
    def resetGoPGV(cls):
        pass

    @classmethod
    @call_service()
    def resetLocalShelfArea(cls):
        pass

    @classmethod
    @call_service()
    def resetOdoMove(cls):
        pass

    @classmethod
    @call_service()
    def setBlockReason(cls, collision_type: int, x: float, y: float, key: str):
        pass

    @classmethod
    @call_service()
    def setGlobalSpinAngle(cls, angle: float, direction: int):
        pass

    @classmethod
    @call_service()
    def setGoForkForkPos(cls, x: float, y: float, theta: float, hold_dir: float):
        pass

    @classmethod
    @call_service()
    def setGoodsShape(cls, head: float, tail: float, width: float):
        pass

    @classmethod
    @call_service()
    def setGoodsShapeWithName(
            cls, head: float, tail: float, width: float, recfile: str
    ):
        pass
    @classmethod
    @call_service()
    def setGoodsPolyShape(
            cls, shape, recfile: str
    ):
        pass
    @classmethod
    @call_service()
    def setIncreaseSpinAngle(cls, angle: float):
        pass

    @classmethod
    @call_service()
    def setLocalShelfArea(cls, object_model_path: str) -> bool:
        pass

    @classmethod
    @call_service()
    def setObsStopDist(cls, dist: float):
        pass

    @classmethod
    @call_service()
    def setPathBackMode(cls, a: bool) -> None:
        pass

    @classmethod
    @call_service()
    def setPathHoldDir(cls, a: float):
        pass

    @classmethod
    @call_service()
    def setPathMaxRot(cls, a: float):
        pass

    @classmethod
    @call_service()
    def setPathMaxSpeed(cls, a: float):
        pass

    @classmethod
    @call_service()
    def setPathOnRobot(cls, x: list, y: list, angle: float):
        pass

    @classmethod
    @call_service()
    def setPathOnWorld(cls, x: list, y: list, angle: float):
        pass

    @classmethod
    @call_service()
    def setPathReachAngle(cls, a: float):
        pass

    @classmethod
    @call_service()
    def setPathReachDist(cls, a: float) -> None:
        pass

    @classmethod
    @call_service()
    def setPathUseOdo(cls, a: bool):
        pass

    @classmethod
    @call_service()
    def setRobotSpinAngle(cls, angle: float, direction: int):
        pass

    @classmethod
    @call_service(plugin_name="DSPChassis")  # todo RBK4 App名
    def setSafeOssdSwitch(cls, laser_key: str, ossdRegion: int):
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
        pass

    @classmethod
    @call_service()
    def setSteerAngle(cls, name: str, angle: float, action_name: str = "") -> bool:
        pass

    @classmethod
    @call_service()
    def spinRun(cls) -> bool:
        pass

    @classmethod
    @call_service()
    def stopRobot(cls, flag: bool):
        pass

    @classmethod
    @call_service()
    def stopRobotNow(cls):
        pass

    @classmethod
    @call_service(func_name="calibRecordService")
    def calibRecord(cls) -> bool:
        pass

    @classmethod
    @call_service(func_name="wheelBaseShift")
    def wheelBaseShift(cls, flag: bool) -> bool:
        pass

    @classmethod
    @call_service(func_name="recordCapture")
    def recordCapture(cls, fileName: str, filePath: str, camName: str) -> bool:
        pass

    @classmethod
    def appendPolicy(cls, name: str):
        # todo RBK4
        return cls.client().call_service("Navigation", "updatePolicy", [name])

    @classmethod
    def appendCustomPolicy(cls, name: str, params: dict):
        # todo RBK4
        return cls.client().call_service("Navigation", "updatePolicy", [], [(name, params)])

    @classmethod
    def clearPolicy(cls):
        return cls.client().call_service("MoveFactory", "updatePolicy", [], [])

    @classmethod
    def setClearRegion(cls, name: str, x: List[float], y: List[float], lasers_key: List[str], coordinate: Coordinate):
        if coordinate == Coordinate.ROBOT:
            return cls.client().call_service("MoveFactory", "setClearRegionInRobotFrame", name=name, x=x, y=y, lasers_key=lasers_key)
        elif coordinate == Coordinate.WORLD:
            return cls.client().call_service("MoveFactory", "setClearRegionInMapFrame", name=name, x=x, y=y, lasers_key=lasers_key)

    @classmethod
    def deleteClearRegion(cls, name: str, coordinate: Coordinate):
        if coordinate == Coordinate.ROBOT:
            cls.client().call_service("MoveFactory", "deleteClearRegionInRobotFrame", name=name)
        elif coordinate == Coordinate.WORLD:
            cls.client().call_service("MoveFactory", "deleteClearRegionInMapFrame", name=name)

    @classmethod
    def getClearRegion(cls, coordinate: Coordinate) -> List[str]:
        if coordinate == Coordinate.ROBOT:
            return cls.client().call_service("MoveFactory", "getClearRegionInRobotFrame")
        elif coordinate == Coordinate.WORLD:
            return cls.client().call_service("MoveFactory", "getClearRegionInMapFrame")

    @classmethod
    def collisionDetection(cls, device_keys: List[str], x: List[float], y: List[float]) -> bool:
        if not device_keys:
            raise ValueError("collisionDetection method param cannot be empty")

        supported_prefixes = ("Laser", "Camera", "DistanceSensor")
        if any(not key.startswith(supported_prefixes) for key in device_keys):
            raise ValueError("collisionDetection method param only support 'Laser', 'Camera', 'DistanceSensor'")

        return cls.client().call_service("MoveFactory", "collisionDetection", device_keys=device_keys, x=x, y=y)


@default_plugin("MoveFactory")  # todo RBK4
class NavStatusV4(NavStatusInterface):
    """导航状态类"""

    _TOPIC = ""  # todo RBK4
    _MODEL_CLASS = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf.message.messageV4_movetask_pb2 import MessageV4_MoveStatus
            cls._MODEL_CLASS = MessageV4_MoveStatus

    @classmethod
    def getChassisStop(cls) -> bool:
        # todo RBK4
        return cls.client().call_service("DSPChassis", "isChassisStop", True)

    def getBlock(self):
        if self.update():
            return self.data.blocked

    @classmethod
    def getTurn(cls, v_x, v_w):
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

    def getTaskStatus(self) -> Optional["MessageV4_MoveStatus.TaskStatus"]:
        if self.update():
            return self.data.task_status


class NavSpeedV4(NavSpeedInterface):
    """导航速度类"""

    _TOPIC = "Tracking.MessageV4_NavSpeed"
    _MODEL_CLASS = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf.message.messageV4_navigation_pb2 import MessageV4_NavSpeed
            cls._MODEL_CLASS = MessageV4_NavSpeed

    def getSpeeds(self) -> Optional[Tuple[float, float, float]]:
        if self.update():
            return self.data.x, self.data.y, self.data.rotate

    def getMotorCmd(self) -> Optional[List["MessageV4_MotorCmd"]]:
        if self.update():
            return self.data.motor_cmd

    def getIs2Move(self) -> bool:
        raise RBKVersionError()
