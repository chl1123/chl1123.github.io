from typing import Union, List, Optional

from .rbk import abnormal
from syspy.lib.abnormal import AbnormalInterface, check_abnormal_code


class AbnormalV4(AbnormalInterface):

    @classmethod
    def exists(cls, codes: Union[int, List[int]]) -> Union[bool, List[bool]]:
        """异常是否存在

        Args:
            codes (Union[int, List[int]]): 单个或多个异常码

        Returns:
            Union[bool, List[bool]]: 是否异常。异常为True, 否则为False。输入int, 输出bool; 输入List[int], 输出List[bool]
        """
        if isinstance(codes, int):
            return abnormal.exists(codes)
        else:
            return [abnormal.exists(code) for code in codes]

    @classmethod
    def existsDevice(cls, deviceName: str, code: Optional[int] = None) -> bool:
        """是否存在指定设备名及异常码的异常

        Args:
            deviceName (str): 是否存在指定设备的异常
            code (Optional[int]): 指定异常码; 缺省表示是否存在设备名为deviceName所有异常

        Returns:
            bool: 是否异常。异常为True, 否则为False
        """
        if code is None:
            return abnormal.existsDevice(deviceName)
        else:
            return abnormal.exists(code, deviceName)

    @classmethod
    def clear(cls, code: int) -> bool:
        """清除异常

        Args:
            code (int): 异常码

        Returns:
            bool: 是否清除成功。清除成功返回True; 不存在异常码或清除失败返回False。
        """
        return abnormal.clear(code)

    @classmethod
    def clearDevice(cls, deviceName: str, code: Optional[int] = None) -> bool:
        """清除指定设备名及异常码的异常

        Args:
            deviceName (str): 需要清除的设备名
            code (Optional[int]): 需要清除的异常码；缺省表示清除指定deviceName的所有异常

        Returns:
            bool: 是否清除成功。清除成功返回True; 不存在异常码或清除失败返回False。
        """
        if code is None:
            return abnormal.clearDevice(deviceName)
        else:
            return abnormal.clear(code, deviceName)

    @classmethod
    def mask(cls, code: int, deviceName: Optional[str] = None) -> bool:
        """屏蔽指定异常码及设备名的异常

        Args:
            code (int): 需要屏蔽的异常码
            deviceName (Optional[str]): 需要屏蔽的异常码；缺省时表示屏蔽指定code的所有异常

        Returns:
            bool: 是否屏蔽成功。成功返回True; 不存在异常码或清除失败返回False。
        """
        return True

    @classmethod
    def unmask(cls, code: int, deviceName: Optional[str] = None):
        """取消屏蔽指定异常码及设备名的异常

        Args:
            code (int): 需要取消屏蔽的异常码
            deviceName (Optional[str]): 需要取消屏蔽的异常码；缺省时表示取消屏蔽指定code的所有异常
        """
        pass

    @classmethod
    def isMasked(cls, code: int, deviceName: Optional[str] = None) -> bool:
        """断指定异常码及设备名的异常是否被屏蔽

        Args:
            code (int): 需要查询屏蔽的异常码
            deviceName (Optional[str]): 需要查询屏蔽的设备；缺省时表示查询是否屏蔽指定code的异常

        Returns:
            bool: 是否屏蔽异常。屏蔽返回True; 没有屏蔽返回False。
        """
        return False

    @classmethod
    def getNum(cls) -> int:
        """获取异常码数量

        Returns:
            int: 异常的数量
        """
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
