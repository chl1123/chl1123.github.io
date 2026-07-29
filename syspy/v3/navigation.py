from __future__ import annotations

import math
from typing import Dict, Tuple, List, Optional, TYPE_CHECKING

from google.protobuf.internal.containers import RepeatedCompositeFieldContainer

from syspy.core.rbk_rpc import call_service, default_plugin
from syspy.navigation import NavigationInterface, NavStatusInterface, NavSpeedInterface
from ..utils import Coordinate

if TYPE_CHECKING:
    from .protobuf.message.message_navigation_pb2 import msgMotorCmd, msgNavSpeed
    from .protobuf.message.message_movetask_pb2 import msgMoveStatus


@default_plugin("MoveFactory")
class NavigationV3(NavigationInterface):
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
    def realTimeMoveTask(cls) -> dict:
        pass

    @classmethod
    @call_service()
    def getBinTask(cls, bin_name: str, task_key: str) -> dict:
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
    def setGoodsShape(cls, head: float, tail: float, width: float, goodsAngleInSpin: Optional[float] = 0.0):
        pass

    @classmethod
    @call_service()
    def setGoodsShapeWithName(
            cls, head: float, tail: float, width: float, recfile: str, goodsAngleInSpin: Optional[float] = 0.0
    ):
        pass
    @classmethod
    @call_service()
    def setGoodsPolyShape(
            cls, shape: List[Dict[str, float]], recfile: str, goodsAngleInSpin: Optional[float] = 0.0
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
    @call_service(plugin_name="DSPChassis")
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
    def recordCapture(cls, fileName: str, filePath: str, cameraKey: str) -> bool:
        pass

    @classmethod
    @call_service()
    def getLmTcpInfo(cls, lm_name: str) -> List[Dict]:
        pass

    @classmethod
    @call_service()
    def calTCPTrans(cls, x: float, y: float, theta: float, tcp_key: str) -> Dict:
        pass

    @classmethod
    @call_service()
    def liveRecGoReset(cls, recfile: str, x: float, y: float, theta: float, tracker_id: str, paths: Dict) -> bool:
        pass

    @classmethod
    @call_service()
    def liveRecGo(cls) -> int:
        pass

    @classmethod
    @call_service()
    def getRecPath(cls, robot_pos_x: float, robot_pos_y: float, robot_pos_theta: float, rec_x: float, rec_y: float,
                   rec_theta: float, back_dist: float, min_ahead_dist: float, ahead_dist: float, back_mode: bool,
                   use_bezier: bool, hold_dir: float, max_speed: float, slow_down_dist: float, slow_down_speed: float,
                   liveRec: bool) -> Dict:
        pass

    @classmethod
    @call_service()
    def cancelLiveRecGo(cls):
        pass

    @classmethod
    @call_service()
    def getLiveResult(cls) -> Dict:
        pass

    @classmethod
    def appendPolicy(cls, name: str):
        return cls.client().call_service("MoveFactory", "updatePolicy", [name])

    @classmethod
    def appendCustomPolicy(cls, name: str, params: dict):
        return cls.client().call_service("MoveFactory", "updatePolicy", [], [(name, params)])


    @classmethod
    def clearPolicy(cls):
        return cls.client().call_service("MoveFactory", "updatePolicy", [], [])

    @classmethod
    def setClearRegion(cls, name: str, x: List[float], y: List[float],
                       lasers_key: List[str], coordinate: Coordinate):
        if coordinate == Coordinate.ROBOT:
            return cls.client().call_service("MoveFactory", "setClearRegionInRobotFrame", name, x, y, lasers_key)
        elif coordinate == Coordinate.WORLD:
            return cls.client().call_service("MoveFactory", "setClearRegionInMapFrame", name, x, y, lasers_key)

    @classmethod
    def deleteClearRegion(cls, name: str, coordinate: Coordinate):
        if coordinate == Coordinate.ROBOT:
            cls.client().call_service("MoveFactory", "deleteClearRegionInRobotFrame", name)
        elif coordinate == Coordinate.WORLD:
            cls.client().call_service("MoveFactory", "deleteClearRegionInMapFrame", name)


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

        return cls.client().call_service("MoveFactory", "collisionDetection", device_keys, x, y)

    @classmethod
    @call_service()
    def goBoustrophedonPath(cls, entranceName: str, exitName: str, startPos: List[float], params: Dict) -> int:
        pass

    @classmethod
    @call_service()
    def resetBoustrophedonPath(cls) -> None:
        pass

    @classmethod
    @call_service()
    def cancelBoustrophedonPath(cls) -> Dict:
        pass

    @classmethod
    @call_service()
    def goRemainingPath(cls, entranceName: str, exitName: str, params: Dict) -> int:
        pass

    @classmethod
    @call_service()
    def goCrossArea(cls, entranceName: str, exitName: str, params: Dict) -> int:
        pass

    @classmethod
    @call_service()
    def goExitPoint(cls, entranceName: str, exitName: str, params: Dict) -> int:
        pass

    @classmethod
    @call_service()
    def getLmTcpName(cls, lm_name: str) -> str:
        pass


    @classmethod
    @call_service()
    def runRotateMove(cls, robot_params: dict, shelf_params: dict) -> int:
        pass

    @classmethod
    @call_service()
    def resetRotateMove(cls):
        pass

    @classmethod
    def setTaskError(cls, key: str, desc: str) -> None:
        cls.client().call_service("MoveFactory", "setTaskError", "py@" + key, desc)

    @classmethod
    def clearTaskError(cls, key: str) -> None:
        cls.client().call_service("MoveFactory", "clearTaskError", "py@" + key)

    @classmethod
    def setDeviceError(cls, key: str, desc: str, param: str = "") -> None:
        cls.client().call_service("MoveFactory", "setDeviceError", "py@" + key, desc, "", "Model", "Model-000", param)

    @classmethod
    def clearDeviceError(cls, key: str) -> None:
        cls.client().call_service("MoveFactory", "clearDeviceError", "py@" + key)

    @classmethod
    def errorExists(cls, key: str) -> bool:
        return cls.client().call_service("MoveFactory", "errorExists", "py@" + key)


@default_plugin("MoveFactory")
class NavStatusV3(NavStatusInterface):
    """导航状态类"""

    data: msgMoveStatus = None

    _TOPIC = "rbk.protocol.msgMoveStatus"
    _PLUGIN = "MoveFactory"
    _MODEL_CLASS = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf.message.message_movetask_pb2 import msgMoveStatus
            cls._MODEL_CLASS = msgMoveStatus

    @classmethod
    def getChassisStop(cls) -> bool:
        return cls.client().call_service("DSPChassis", "isChassisStop", True)

    def getBlock(self) -> Optional[bool]:
        if self.update():
            return self.data.blocked

    def getBlockDevice(self) -> Optional[str]:
        if self.update():
            return self.data.blockDevice

    @classmethod
    def clearBlock(cls) -> None:
        """清除机器人的阻挡状态"""
        cls.client().call_service("MoveFactory", "clearBlockError")

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

    def getTaskStatus(self) -> Optional[int]:
        if self.update():
            return self.data.taskStatus

    def getRunningStatus(self) -> Optional[int]:
        if self.update():
            return self.data.runningStatus

    def getCurrentStation(self) -> Optional[str]:
        if self.update():
            return self.data.closestTarget


class NavSpeedV3(NavSpeedInterface):
    """导航速度类"""

    data: msgNavSpeed = None

    _TOPIC = "rbk.protocol.msgNavSpeed"
    _PLUGIN = "MoveFactory"
    _MODEL_CLASS = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf.message.message_navigation_pb2 import msgNavSpeed
            cls._MODEL_CLASS = msgNavSpeed

    def getSpeeds(self) -> Optional[Tuple[float, float, float]]:
        if self.update():
            return self.data.x, self.data.y, self.data.rotate

    def getMotorCmd(self) -> Optional[RepeatedCompositeFieldContainer["msgMotorCmd"]]:
        if self.update():
            return self.data.motorCmd
