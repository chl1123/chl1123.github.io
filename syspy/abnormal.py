from .py_ipc import Service
from .service_utils import default_plugin, call_service

@default_plugin("Abnormal")
class Abnormal(Service):
    @classmethod
    @call_service(func_name="existsAbnormal")
    def exists(cls, code: int) -> bool:
        """
        Args:
            code (int):

        Returns:
            bool:
        """
        pass

    @classmethod
    @call_service(func_name="clearAbnormal")
    def clear(cls, code: int) -> bool:
        """
        Args:
            code (int):

        Returns:
            bool:
        """
        pass

    @classmethod
    @call_service(func_name="setTaskAbnormal")
    def setTask(cls, code: int, desc: str, reason: str, method: str, task: str) -> bool:
        """
        Args:
            code (int):
            desc (str):
            reason (str):
            method (str):
            task (str):

        Returns:
            bool:
        """
        pass

    @classmethod
    @call_service(func_name="setMapAbnormal")
    def setMap(cls, code: int, desc: str, reason: str, method: str, fileName: str, mapType: str = "", elementType: str = "", elementName: str = "", param: str = "") -> bool:
        """
        Args:
            code (int):
            desc (str):
            reason (str):
            method (str):
            fileName (str):
            mapType (str):
            elementType (str):
            elementName (str):
            param (str):

        Returns:
            bool:
        """
        pass

    @classmethod
    @call_service(func_name="setModelAbnormal")
    def setModel(cls, code: int, desc: str, reason: str, method: str, fileName: str, deviceType: str = "", deviceKey: str = "", param: str = "") -> bool:
        """
        Args:
            code (int):
            desc (str):
            reason (str):
            method (str):
            fileName (str):
            deviceType (str):
            deviceKey (str):
            param (str):

        Returns:
            bool:
        """
        pass

    @classmethod
    @call_service(func_name="setAppAbnormal")
    def setApp(cls, code: int, desc: str, reason: str, method: str, appType: str, fileName: str, param: str = "") -> bool:
        """
        Args:
            code (int):
            desc (str):
            reason (str):
            method (str):
            appType (str):
            fileName (str):
            param (str):

        Returns:
            bool:
        """
        pass

    @classmethod
    @call_service(func_name="setAppAbnormal")
    def setSystem(cls, code: int, desc: str, reason: str, method: str, fileName: str, param: str = "") -> bool:
        """
        Args:
            code (int):
            desc (str):
            reason (str):
            method (str):
            fileName (str):
            param (str):

        Returns:
            bool:
        """
        pass

    @classmethod
    @call_service(func_name="setAppAbnormal")
    def setSRC(cls, code: int, desc: str, reason: str, method: str) -> bool:
        """
        Args:
            code (int):
            desc (str):
            reason (str):
            method (str):

        Returns:
            bool:
        """
        pass

    @classmethod
    @call_service(func_name="setEnvironmentAbnormal")
    def setEnvironment(cls, code: int, desc: str, reason: str, method: str) -> bool:
        """
        Args:
            code (int):
            desc (str):
            reason (str):
            method (str):

        Returns:
            bool:
        """
        pass

    @classmethod
    @call_service(func_name="setDeviceAbnormal")
    def setDevice(cls, code: int, desc: str, reason: str, method: str, fileName: str, deviceType: str = "", deviceName: str = "", param: str = "", errorCode: int = 0) -> bool:
        """
        Args:
            code (int):
            desc (str):
            reason (str):
            method (str):
            fileName (str):
            deviceType (str):
            deviceName (str):
            param (str):
            errorCode (int):

        Returns:
            bool:
        """
        pass

    @classmethod
    @call_service(func_name="setConnectionAbnormal")
    def setConnect(cls, code: int, desc: str, reason: str, method: str, fileName: str, deviceType: str = "", deviceName: str = "", param: str = "") -> bool:
        """
        Args:
            code (int):
            desc (str):
            reason (str):
            method (str):
            fileName (str):
            deviceType (str):
            deviceName (str):
            param (str):

        Returns:
            bool:
        """
        pass

    @classmethod
    @call_service(func_name="setCalibrationAbnormal")
    def setCalibrate(cls, code: int, desc: str, reason: str, method: str, fileName: str, param: str = "") -> bool:
        """
        Args:
            code (int):
            desc (str):
            reason (str):
            method (str):
            fileName (str):
            param (str):

        Returns:
            bool:
        """
        pass

    @classmethod
    @call_service(func_name="setAPIAbnormal")
    def setAPI(cls, code: int, desc: str, reason: str, method: str, APIcode: int = 0, param: str = "") -> bool:
        """
        Args:
            code (int):
            desc (str):
            reason (str):
            method (str):
            APIcode (int):
            param (str):

        Returns:
            bool:
        """
        pass

    @classmethod
    @call_service(func_name="setLicenseAbnormal")
    def setLicense(cls, code: int, desc: str, reason: str, method: str, licenseType: str = "") -> bool:
        """
        Args:
            code (int):
            desc (str):
            reason (str):
            method (str):
            licenseType (str):

        Returns:
            bool:
        """
        pass

    @classmethod
    @call_service(func_name="setChassisAbnormal")
    def setChassis(cls, code: int, desc: str, reason: str, method: str) -> bool:
        """
        Args:
            code (int):
            desc (str):
            reason (str):
            method (str):

        Returns:
            bool:
        """
        pass
