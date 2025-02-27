from .py_rpc import Service, default_plugin, call_service


@default_plugin("Abnormal")
class Abnormal(Service):

    @classmethod
    @call_service(func_name="existsAbnormal")
    def exists(cls, code: int) -> bool:
        """异常是否存在

        Args:
            code (int):

        Returns:
            bool:
        """
        pass

    @classmethod
    @call_service(func_name="clearAbnormal")
    def clear(cls, code: int) -> bool:
        """清除异常

        Args:
            code (int):

        Returns:
            bool:
        """
        pass

    @classmethod
    @call_service(func_name="getNumAbnormal")
    def getNum(cls) -> int:
        """获取异常数量

        Returns:
            int: abnormal的数量
        """
        pass

    @classmethod
    @call_service(func_name="setTaskAbnormal")
    def setTask(cls, code: int, desc: str, reason: str, method: str, task: str) -> bool:
        """设置任务异常

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
    def setMap(cls, code: int, desc: str, reason: str, method: str, fileName: str, mapType: str = "",
               elementType: str = "", elementName: str = "", param: str = "") -> bool:
        """设置地图异常

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
    def setModel(cls, code: int, desc: str, reason: str, method: str, fileName: str, deviceType: str = "",
                 deviceKey: str = "", param: str = "") -> bool:
        """设置模型异常

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
    def setApp(cls, code: int, desc: str, reason: str, method: str, appType: str, fileName: str,
               param: str = "") -> bool:
        """设置App异常

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
        """设置系统异常

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
        """设置SRC异常

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
        """设置环境异常

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
    def setDevice(cls, code: int, desc: str, reason: str, method: str, fileName: str, deviceType: str = "",
                  deviceName: str = "", param: str = "", errorCode: int = 0) -> bool:
        """设置设备异常

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
    def setConnect(cls, code: int, desc: str, reason: str, method: str, fileName: str, deviceType: str = "",
                   deviceName: str = "", param: str = "") -> bool:
        """设置连接异常

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
        """设置标定异常

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
        """设置API异常

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
    def setLicense(
            cls, code: int, desc: str, reason: str, method: str, licenseType: str = ""
    ) -> bool:
        """设置证书异常

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
        """设置底盘异常

        Args:
            code (int):
            desc (str):
            reason (str):
            method (str):

        Returns:
            bool:
        """
        pass
