from typing import Union, List, TYPE_CHECKING

from syspy.core.rbk_rpc import default_plugin, call_service
from syspy.motor import MotorInterface
if TYPE_CHECKING:
    from .protobuf import msgMotorInfo  # IDE类型提示

@default_plugin("MoveFactory")
class MotorV3(MotorInterface):
    """电机类"""

    @staticmethod
    def getMotorInfos() -> List["msgMotorInfo"]:
        from syspy import Odometer
        return Odometer.data.motorInfo

    @staticmethod
    def getMotorPos(key: str) -> Union[float, int]:
        from syspy import Odometer
        motor_pos = -1
        if Odometer.update():
            for motor in Odometer.data.motorInfo:
                if motor.key == key:
                    motor_pos = motor.position
        return motor_pos

    @staticmethod
    def getMotorSpeed(key: str) -> Union[float, int]:
        from syspy import NavSpeed
        motor_speed = -1
        if NavSpeed.update():
            for motor in NavSpeed.data.motorCmd:
                if motor.key == key:
                    motor_speed = motor.value
        return motor_speed

    @classmethod
    @call_service()
    def setMotorSpeed(cls, key: str, vel: float, stopDI: str = "") -> bool:
        pass

    @classmethod
    @call_service()
    def setMotorPosition(cls, key: str, pos: float, maxVel: float, stopDI: str = "") -> bool:
        pass

    @classmethod
    def setMotorPositionAdv(cls, key: str, pos: float, maxSpeed: float = None, maxAcc: float = None,
                            maxDec: float = None, jerk: float = None, stopDI: str = "") -> bool:
        params = {"key": key, "position": pos}
        if maxSpeed is not None:
            params["maxSpeed"] = maxSpeed
        if maxAcc is not None:
            params["maxAcc"] = maxAcc
        if maxDec is not None:
            params["maxDec"] = maxDec
        if jerk is not None:
            params["jerk"] = jerk
        if stopDI is not None:
            params["stopDI"] = stopDI
        return cls.client().call_service("MoveFactory", "setMotorPositionAdv", params)

    @classmethod
    @call_service()
    def stopMotor(cls):
        pass

    @classmethod
    @call_service()
    def resetMotor(cls, key: str) -> bool:
        pass

    @classmethod
    @call_service()
    def isMotorReached(cls, key: str) -> bool:
        pass

    @classmethod
    @call_service()
    def isMotorPositionReached(cls, key: str, pos: float, stopDI: str = "") -> bool:
        pass

    @classmethod
    @call_service()
    def isMotorStop(cls, key: str) -> bool:
        pass

    @classmethod
    @call_service(plugin_name="DSPChassis")
    def disableMotor(cls, key: str):
        pass

    @classmethod
    @call_service(plugin_name="DSPChassis")
    def enableMotor(cls, key: str):
        pass

    @classmethod
    @call_service(plugin_name="DSPChassis")
    def motorCalib(cls, key: str):
        pass

    @classmethod
    @call_service(plugin_name="DSPChassis")
    def motorForceCalib(cls, key: str):
        pass