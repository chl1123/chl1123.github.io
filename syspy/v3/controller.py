from typing import Optional, TYPE_CHECKING

from syspy.controller import ControllerInterface


class ControllerV3(ControllerInterface):
    """控制器类"""

    _TOPIC = "rbk.protocol.msgController"
    _PLUGIN = "DSPChassis"
    _MODEL_CLASS = None

    if TYPE_CHECKING:
        from .protobuf import msgController
        data: msgController = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import msgController
            cls._MODEL_CLASS = msgController

    def getTemperature(self) -> Optional[float]:
        if self.update():
            return self.data.temp

    def getHumidity(self) -> Optional[float]:
        if self.update():
            return self.data.humi

    def getVoltage(self) -> Optional[float]:
        if self.update():
            return self.data.voltage

    def getEmc(self) -> Optional[bool]:
        if self.update():
            return self.data.emc

    def getBrake(self) -> Optional[bool]:
        if self.update():
            return self.data.brake

    def getDriverEmc(self) -> Optional[bool]:
        if self.update():
            return self.data.driverEmc

    def getManualCharge(self) -> Optional[bool]:
        if self.update():
            return self.data.manualCharge

    def getAutoCharge(self) -> Optional[bool]:
        if self.update():
            return self.data.autoCharge

    def getElectric(self) -> Optional[bool]:
        if self.update():
            return self.data.electric

    def getSoftEmc(self) -> Optional[bool]:
        if self.update():
            return self.data.softEMC

    def getIsExternalControl(self) -> Optional[bool]:
        if self.update():
            return self.data.isExternalControl

    def getIsImuCalibrating(self) -> Optional[bool]:
        if self.update():
            return self.data.isIMUCalibrating

    def getAdcVoltage(self) -> Optional[float]:
        if self.update():
            return self.data.voltagebyAdc