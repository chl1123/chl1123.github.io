from typing import Union, List, Optional

from .rbk import abnormal
from syspy.lib.abnormal import AbnormalInterface, check_abnormal_code


class AbnormalV4(AbnormalInterface):

    @classmethod
    def exists(cls, codes: Union[int, List[int]]) -> Union[bool, List[bool]]:
        if isinstance(codes, int):
            return abnormal.exists(codes)
        else:
            return [abnormal.exists(code) for code in codes]

    @classmethod
    def existsDevice(cls, deviceName: str, code: Optional[int] = None) -> bool:
        if code is None:
            return abnormal.existsDevice(deviceName)
        else:
            return abnormal.exists(code, deviceName)

    @classmethod
    def clear(cls, code: int) -> bool:
        return abnormal.clear(code)

    @classmethod
    def clearDevice(cls, deviceName: str, code: Optional[int] = None) -> bool:
        if code is None:
            return abnormal.clearDevice(deviceName)
        else:
            return abnormal.clear(code, deviceName)

    @classmethod
    def mask(cls, code: int, deviceName: Optional[str] = None) -> bool:
        return True

    @classmethod
    def unmask(cls, code: int, deviceName: Optional[str] = None):
        pass

    @classmethod
    def isMasked(cls, code: int, deviceName: Optional[str] = None) -> bool:
        return False

    @classmethod
    def getNum(cls) -> int:
        return abnormal.getNum()

    @classmethod
    def setTask(
        cls,
        code: int,
        desc: str,
        reason: str,
        method: str,
        task: Union[str, list, dict],
        fileName: str = "",
        mapType: str = "",
        elementType: str = "",
        elementName: str = "",
        policyName: str = "",
        param: str = "",
    ) -> bool:
        check_abnormal_code(code)
        return abnormal.setTask(
            code,
            desc,
            reason,
            method,
            str(task),
            fileName,
            mapType,
            elementType,
            elementName,
            policyName,
            param,
        )

    @classmethod
    def setMap(
        cls,
        code: int,
        desc: str,
        reason: str,
        method: str,
        fileName: str,
        mapType: str = "",
        elementType: str = "",
        elementName: str = "",
    ) -> bool:
        check_abnormal_code(code)
        return abnormal.setMap(
            code,
            desc,
            reason,
            method,
            fileName,
            mapType,
            elementType,
            elementName,
        )

    @classmethod
    def setModel(
        cls,
        code: int,
        desc: str,
        reason: str,
        method: str,
        fileName: str,
        deviceType: str = "",
        deviceKey: str = "",
        param: str = "",
    ) -> bool:
        check_abnormal_code(code)
        return abnormal.setModel(
            code,
            desc,
            reason,
            method,
            fileName,
            deviceType,
            deviceKey,
            param,
        )

    @classmethod
    def setConfig(
        cls,
        code: int,
        desc: str,
        reason: str,
        method: str,
        appType: str,
        fileName: str,
        param: str = "",
    ) -> bool:
        check_abnormal_code(code)
        return abnormal.setConfig(
            code,
            desc,
            reason,
            method,
            appType,
            fileName,
            param,
        )

    @classmethod
    def setSystem(
        cls,
        code: int,
        desc: str,
        reason: str,
        method: str,
        fileName: str,
        param: str = "",
    ) -> bool:
        check_abnormal_code(code)
        return abnormal.setSystem(
            code,
            desc,
            reason,
            method,
            fileName,
            param,
        )

    @classmethod
    def setEnvironment(
        cls, code: int, desc: str, reason: str, method: str, position: str = ""
    ) -> bool:
        check_abnormal_code(code)
        return abnormal.setEnvironment(
            code,
            desc,
            reason,
            method,
            position,
        )

    @classmethod
    def setDevice(
        cls,
        code: int,
        desc: str,
        reason: str,
        method: str,
        fileName: str,
        deviceType: str = "",
        deviceKey: str = "",
        param: str = "",
        errorCode: int = 0,
    ) -> bool:
        check_abnormal_code(code)
        return abnormal.setDevice(
            code,
            desc,
            reason,
            method,
            fileName,
            deviceType,
            deviceKey,
            param,
            errorCode,
        )

    @classmethod
    def setConnect(
        cls,
        code: int,
        desc: str,
        reason: str,
        method: str,
        fileName: str,
        deviceType: str = "",
        deviceKey: str = "",
        param: str = "",
    ) -> bool:
        check_abnormal_code(code)
        return abnormal.setConnect(
            code,
            desc,
            reason,
            method,
            fileName,
            deviceType,
            deviceKey,
            param,
        )

    @classmethod
    def setCalibrate(
        cls,
        code: int,
        desc: str,
        reason: str,
        method: str,
        deviceType: str,
        deviceKey: str = "",
    ) -> bool:
        check_abnormal_code(code)
        return abnormal.setCalibrate(
            code,
            desc,
            reason,
            method,
            deviceType,
            deviceKey,
        )

    @classmethod
    def setLicense(
        cls, code: int, desc: str, reason: str, method: str, licenseType: str = ""
    ) -> bool:
        check_abnormal_code(code)
        return abnormal.setLicense(
            code,
            desc,
            reason,
            method,
            licenseType,
        )

    @classmethod
    def setChassis(cls, code: int, desc: str, reason: str, method: str) -> bool:
        check_abnormal_code(code)
        return abnormal.setChassis(code, desc, reason, method)
