from typing import Optional

from syspy.controller import ControllerInterface


class ControllerV4(ControllerInterface):
    """控制器类"""
    _TOPIC = ""  # todo RBK4
    _MODEL_CLASS = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from syspy.v4.protobuf.message.messageV4_controller_pb2 import MessageV4_Controller
            cls._MODEL_CLASS = MessageV4_Controller

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
