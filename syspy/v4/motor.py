from typing import Union, List, TYPE_CHECKING

from syspy.core.rbk_rpc import default_plugin, call_service
from syspy.motor import MotorInterface
from syspy import NavSpeed

if TYPE_CHECKING:
    from syspy.v4.protobuf.message.messageV4_movetask_pb2 import MessageV4_MInfo as Message_MotorInfo


@default_plugin("Navigation")  # todo RBK4
class MotorV4(MotorInterface):
    """电机类"""

    _TOPIC = "Odom"  # todo RBK4
    _MODEL_CLASS = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from syspy.v4.protobuf.message.messageV4_movetask_pb2 import MessageV4_Odo
            cls._MODEL_CLASS = MessageV4_Odo

    def getMotorInfos(self) -> List["Message_MotorInfo"]:
        self.update()
        return self.data.motor_info

    def getMotorPos(self, motor_name: str) -> Union[float, int]:
        motor_pos = -1
        if self.update():
            for motor in self.data.motor_info:
                if motor.motor_name == motor_name:
                    motor_pos = motor.position
        return motor_pos

    def getMotorSpeed(self, motor_name: str) -> Union[float, int]:
        motor_speed = -1
        if NavSpeed.update():
            for motor in NavSpeed.data.motor_cmd:
                if motor.motor_name == motor_name:
                    motor_speed = motor.value
        return motor_speed

    @classmethod
    @call_service()
    def setMotorSpeed(cls, name: str, vel: float, stopDI: str = "") -> bool:
        pass

    @classmethod
    @call_service()
    def setMotorPosition(cls, motor_name: str, pos: float, maxVel: float, stopDI: str = "") -> bool:
        pass

    @classmethod
    def setMotorPositionAdv(cls, name: str, pos: float, maxSpeed: float = None, maxAcc: float = None,
                            maxDec: float = None, jerk: float = None, stopDI: str = "") -> bool:
        params = {"name": name, "position": pos}
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
        # todo RBK4
        return cls.client().call_service("MoveFactory", "setMotorPositionAdv", params)

    @classmethod
    @call_service()
    def stopMotor(cls):
        pass

    @classmethod
    @call_service()
    def resetMotor(cls, motor_name: str) -> bool:
        pass

    @classmethod
    @call_service()
    def isMotorReached(cls, motor_name: str) -> bool:
        pass

    @classmethod
    @call_service()
    def isMotorPositionReached(cls, motor_name: str, pos: float, stopDI: str = "") -> bool:
        pass

    @classmethod
    @call_service()
    def isMotorStop(cls, motor_name: str) -> bool:
        pass

    @classmethod
    @call_service(plugin_name="DSPChassis")  # todo RBK4
    def disableMotor(cls, name: str):
        pass

    @classmethod
    @call_service(plugin_name="DSPChassis")  # todo RBK4
    def enableMotor(cls, name: str):
        pass

    @classmethod
    @call_service(plugin_name="DSPChassis")  # todo RBK4
    def motorCalib(cls, m: str):
        pass

    @classmethod
    @call_service(plugin_name="DSPChassis")  # todo RBK4
    def motorForceCalib(cls, m: str):
        pass