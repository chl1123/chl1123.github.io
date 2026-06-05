from typing import Union, List, Optional

from syspy.core.rbk_rpc import default_plugin, call_service
from syspy.lib.abnormal import AbnormalInterface, check_abnormal_code


@default_plugin("Abnormal")
class AbnormalV3(AbnormalInterface):

    @classmethod
    def exists(cls, codes: Union[int, List[int]]) -> Union[bool, List[bool]]:
        if isinstance(codes, int):
            return cls.client().call_service("Abnormal", "existsAbnormal", [codes])[0]
        else:
            return cls.client().call_service("Abnormal", "existsAbnormal", codes)

    @classmethod
    @call_service(func_name="existsDeviceAbnormal")
    def existsDevice(cls, deviceKey: str, code: Optional[int] =  None) -> bool:
        pass

    @classmethod
    @call_service(func_name="clearAbnormal")
    def clear(cls, code: int) -> bool:
        pass

    @classmethod
    @call_service(func_name="clearDeviceAbnormal")
    def clearDevice(cls, deviceKey: str, code: Optional[int] =  None) -> bool:
        pass

    @classmethod
    @call_service(func_name="maskAbnormal")
    def mask(cls, code: int, deviceKey: Optional[str] = None) -> bool:
        pass

    @classmethod
    @call_service(func_name="unmaskAbnormal")
    def unmask(cls, code: int, deviceKey: Optional[str] = None):
        pass

    @classmethod
    @call_service(func_name="isMaskedAbnormal")
    def isMasked(cls, code: int, deviceKey: Optional[str] = None) -> bool:
        pass

    @classmethod
    @call_service(func_name="getNumAbnormal")
    def getNum(cls) -> int:
        pass

    @classmethod
    def setTask(cls, code: int, desc: str, reason: str, method: str, task: Union[str, list, dict],
                fileName: str = "", mapType: str = "", elementType: str = "", elementName: str = "",
                policyName: str = "", param: str = "") -> bool:
        check_abnormal_code(code)
        return cls.client().call_service("Abnormal", "setTaskAbnormal", code, desc, reason, method, str(task),
                                         fileName, mapType, elementType, elementName, policyName, param)

    @classmethod
    def setMap(cls, code: int, desc: str, reason: str, method: str, fileName: str, mapType: str = "",
               elementType: str = "", elementName: str = "") -> bool:
        check_abnormal_code(code)
        return cls.client().call_service("Abnormal", "setMapAbnormal", code, desc, reason, method, fileName,
                                         mapType, elementType, elementName)

    @classmethod
    def setModel(cls, code: int, desc: str, reason: str, method: str, fileName: str, deviceType: str = "",
                 deviceKey: str = "", param: str = "") -> bool:
        check_abnormal_code(code)
        return cls.client().call_service("Abnormal", "setModelAbnormal", code, desc, reason, method, fileName,
                                         deviceType, deviceKey, param)

    @classmethod
    def setConfig(cls, code: int, desc: str, reason: str, method: str, appType: str, fileName: str,
               param: str = "") -> bool:
        check_abnormal_code(code)
        return cls.client().call_service("Abnormal", "setConfigAbnormal", code, desc, reason, method, appType,
                                         fileName, param)

    @classmethod
    def setSystem(cls, code: int, desc: str, reason: str, method: str, fileName: str, param: str = "") -> bool:
        check_abnormal_code(code)
        return cls.client().call_service("Abnormal", "setSystemAbnormal", code, desc, reason, method, fileName, param)

    @classmethod
    def setEnvironment(cls, code: int, desc: str, reason: str, method: str, position: str = "") -> bool:
        check_abnormal_code(code)
        return cls.client().call_service("Abnormal", "setEnvironmentAbnormal", code, desc, reason, method, position)

    @classmethod
    def setDevice(cls, code: int, desc: str, reason: str, method: str, fileName: str, deviceType: str = "",
                  deviceKey: str = "", param: str = "", errorCode: int = 0) -> bool:
        check_abnormal_code(code)
        return cls.client().call_service("Abnormal", "setDeviceAbnormal", code, desc, reason, method, fileName,
                                         deviceType, deviceKey, param, errorCode)

    @classmethod
    def setConnect(cls, code: int, desc: str, reason: str, method: str, fileName: str, deviceType: str = "",
                   deviceKey: str = "", param: str = "") -> bool:
        check_abnormal_code(code)
        return cls.client().call_service("Abnormal", "setConnectionAbnormal", code, desc, reason, method, fileName,
                                         deviceType, deviceKey, param)

    @classmethod
    def setCalibrate(cls, code: int, desc: str, reason: str, method: str, deviceType: str, deviceKey: str = "") -> bool:
        check_abnormal_code(code)
        return cls.client().call_service("Abnormal", "setCalibrationAbnormal", code, desc, reason, method, deviceType,
                                         deviceKey)

    @classmethod
    def setLicense(
            cls, code: int, desc: str, reason: str, method: str, licenseType: str = ""
    ) -> bool:
        check_abnormal_code(code)
        return cls.client().call_service("Abnormal", "setLicenseAbnormal", code, desc, reason, method, licenseType)

    @classmethod
    def setChassis(cls, code: int, desc: str, reason: str, method: str) -> bool:
        check_abnormal_code(code)
        return cls.client().call_service("Abnormal", "setChassisAbnormal", code, desc, reason, method)
