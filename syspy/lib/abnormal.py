from typing import Union, List, Optional

from .py_rpc import Service, default_plugin, call_service


@default_plugin("Abnormal")
class Abnormal(Service):

    @classmethod
    def exists(cls, codes: Union[int, List[int]]) -> Union[bool, List[bool]]:
        """异常是否存在

        Args:
            codes (Union[int, List[int]]): 单个或多个异常码

        Returns:
            Union[bool, List[bool]]: 是否异常。异常为True, 否则为False。输入int, 输出bool; 输入List[int], 输出List[bool]
        """
        if isinstance(codes, int):
            return cls.client().call_service("Abnormal", "existsAbnormal", [codes])[0]
        else:
            return cls.client().call_service("Abnormal", "existsAbnormal", codes)

    @classmethod
    @call_service(func_name="existsDeviceAbnormal")
    def existsDevice(cls, deviceName: str, code: Optional[int] =  None) -> bool:
        """是否存在指定设备名及异常码的异常

        Args:
            deviceName (str): 是否存在指定设备的异常
            code (Optional[int]): 指定异常码; 缺省表示是否存在设备名为deviceName所有异常

        Returns:
            bool: 是否异常。异常为True, 否则为False
        """
        pass

    @classmethod
    @call_service(func_name="clearAbnormal")
    def clear(cls, code: int) -> bool:
        """清除异常

        Args:
            code (int): 异常码

        Returns:
            bool: 是否清除成功。清除成功返回True; 不存在异常码或清除失败返回False。
        """
        pass

    @classmethod
    @call_service(func_name="clearDeviceAbnormal")
    def clearDevice(cls, deviceName: str, code: Optional[int] =  None) -> bool:
        """清除指定设备名及异常码的异常

        Args:
            deviceName (str): 需要清除的设备名
            code (Optional[int]): 需要清除的异常码；缺省表示清除指定deviceName的所有异常

        Returns:
            bool: 是否清除成功。清除成功返回True; 不存在异常码或清除失败返回False。
        """
        pass

    @classmethod
    @call_service(func_name="maskAbnormal")
    def mask(cls, code: int, deviceName: Optional[str] = None) -> bool:
        """屏蔽指定异常码及设备名的异常

        Args:
            code (int): 需要屏蔽的异常码
            deviceName (Optional[str]): 需要屏蔽的异常码；缺省时表示屏蔽指定code的所有异常

        Returns:
            bool: 是否屏蔽成功。成功返回True; 不存在异常码或清除失败返回False。
        """
        pass

    @classmethod
    @call_service(func_name="unmaskAbnormal")
    def unmask(cls, code: int, deviceName: Optional[str] = None):
        """取消屏蔽指定异常码及设备名的异常

        Args:
            code (int): 需要取消屏蔽的异常码
            deviceName (Optional[str]): 需要取消屏蔽的异常码；缺省时表示取消屏蔽指定code的所有异常
        """
        pass

    @classmethod
    @call_service(func_name="isMaskedAbnormal")
    def isMasked(cls, code: int, deviceName: Optional[str] = None) -> bool:
        """断指定异常码及设备名的异常是否被屏蔽

        Args:
            code (int): 需要查询屏蔽的异常码
            deviceName (Optional[str]): 需要查询屏蔽的设备；缺省时表示查询是否屏蔽指定code的异常

        Returns:
            bool: 是否屏蔽异常。屏蔽返回True; 没有屏蔽返回False。
        """
        pass

    @classmethod
    @call_service(func_name="getNumAbnormal")
    def getNum(cls) -> int:
        """获取异常码数量

        Returns:
            int: 异常的数量
        """
        pass

    @classmethod
    def setTask(cls, code: int, desc: str, reason: str, method: str, task: Union[str, list, dict],
                fileName: str = "", mapType: str = "", elementType: str = "", elementName: str = "",
                policyName: str = "", param: str = "") -> bool:
        """设置任务异常

        Args:
            code (int): 异常码
            desc (str): 异常现象描述
            reason (str): 异常原因
            method (str): 异常处理方法
            task (str): 异常任务内容
            fileName (str): 地图文件名
            mapType (str): 地图类型
            elementType (str): 图元类型
            elementName (str): 图元名称
            policyName (str): 策略名称
            param (str): 异常参数

        Returns:
            bool: 是否设置成功。成功返回True; 失败返回False。
        """
        return cls.client().call_service("Abnormal", "setTaskAbnormal", code, desc, reason, method, str(task),
                                         fileName, mapType, elementType, elementName, policyName, param)

    @classmethod
    @call_service(func_name="setMapAbnormal")
    def setMap(cls, code: int, desc: str, reason: str, method: str, fileName: str, mapType: str = "",
               elementType: str = "", elementName: str = "") -> bool:
        """设置地图异常

        Args:
            code (int): 异常码
            desc (str): 异常现象描述
            reason (str): 异常原因
            method (str): 异常处理方法
            fileName (str): 异常（地图）文件名
            mapType (str): 地图类型：2D、3D、vslam、纹理等(可缺省)
            elementType (str): 异常图元类型(可缺省)
            elementName (str): 异常图元名字(可缺省)

        Returns:
            bool: 是否设置成功。成功返回True; 失败返回False。
        """
        pass

    @classmethod
    @call_service(func_name="setModelAbnormal")
    def setModel(cls, code: int, desc: str, reason: str, method: str, fileName: str, deviceType: str = "",
                 deviceKey: str = "", param: str = "") -> bool:
        """设置模型异常

        Args:
            code (int): 异常码
            desc (str): 异常现象描述
            reason (str): 异常原因
            method (str): 异常处理方法
            fileName (str): 异常（设备模型）文件名
            deviceType (str): 异常设备类型(可缺省)
            deviceKey (str): 异常设备(可缺省)
            param (str): 异常参数(可缺省)

        Returns:
            bool: 是否设置成功。成功返回True; 失败返回False。
        """
        pass

    @classmethod
    @call_service(func_name="setConfigAbnormal")
    def setConfig(cls, code: int, desc: str, reason: str, method: str, appType: str, fileName: str,
               param: str = "") -> bool:
        """设置参数配置异常

        Args:
            code (int): 异常码
            desc (str): 异常现象描述
            reason (str): 异常原因
            method (str): 异常处理方法
            appType (str): App类型
            fileName (str): 异常（应用）文件名(可缺省)
            param (str): 异常参数（包含路径）(可缺省)

        Returns:
            bool: 是否设置成功。成功返回True; 失败返回False。
        """
        pass

    @classmethod
    @call_service(func_name="setSystemAbnormal")
    def setSystem(cls, code: int, desc: str, reason: str, method: str, fileName: str, param: str = "") -> bool:
        """设置系统异常

        Args:
            code (int): 异常码
            desc (str): 异常现象描述
            reason (str): 异常原因
            method (str): 异常处理方法
            fileName (str): 异常（应用）文件名
            param (str): 异常参数（包含路径）

        Returns:
            bool: 是否设置成功。成功返回True; 失败返回False。
        """
        pass

    @classmethod
    @call_service(func_name="setEnvironmentAbnormal")
    def setEnvironment(cls, code: int, desc: str, reason: str, method: str, position: str = "") -> bool:
        """设置环境异常

        Args:
            code (int): 异常码（原报警码）
            desc (str): 异常现象描述
            reason (str): 异常原因
            method (str): 异常处理方法
            position (str): 异常坐标位置

        Returns:
            bool: 是否设置成功。成功返回True; 失败返回False。
        """
        pass

    @classmethod
    @call_service(func_name="setDeviceAbnormal")
    def setDevice(cls, code: int, desc: str, reason: str, method: str, fileName: str, deviceType: str = "",
                  deviceKey: str = "", param: str = "", errorCode: int = 0) -> bool:
        """设置设备异常

        Args:
            code (int): 异常码（原报警码）
            desc (str): 异常现象描述
            reason (str): 异常原因
            method (str): 异常处理方法
            fileName (str): 异常（设备模型）文件名
            deviceType (str): 异常设备类型
            deviceKey (str): 异常设备名
            param (str): 异常参数
            errorCode (int): device上报

        Returns:
            bool: 是否设置成功。成功返回True; 失败返回False。
        """
        pass

    @classmethod
    @call_service(func_name="setConnectionAbnormal")
    def setConnect(cls, code: int, desc: str, reason: str, method: str, fileName: str, deviceType: str = "",
                   deviceKey: str = "", param: str = "") -> bool:
        """设置连接异常

        Args:
            code (int): 异常码
            desc (str): 异常现象描述
            reason (str): 异常原因
            method (str): 异常处理方法
            fileName (str): 异常（设备模型）文件名
            deviceType (str): 异常设备类型
            deviceKey (str): 异常设备key
            param (str): 异常参数

        Returns:
            bool: 是否设置成功。成功返回True; 失败返回False。
        """
        pass

    @classmethod
    @call_service(func_name="setCalibrationAbnormal")
    def setCalibrate(cls, code: int, desc: str, reason: str, method: str, deviceType: str, deviceKey: str = "") -> bool:
        """设置标定异常

        Args:
            code (int): 异常码
            desc (str): 异常现象描述
            reason (str): 异常原因
            method (str): 异常处理方法
            deviceType (str): 异常设备文件名
            deviceKey (str): 异常设备key

        Returns:
            bool: 是否设置成功。成功返回True; 失败返回False。
        """
        pass

    @classmethod
    @call_service(func_name="setLicenseAbnormal")
    def setLicense(
            cls, code: int, desc: str, reason: str, method: str, licenseType: str = ""
    ) -> bool:
        """设置证书异常

        Args:
            code (int): 异常码
            desc (str): 异常现象描述
            reason (str): 异常原因
            method (str): 异常处理方法
            licenseType (str): 证书类型

        Returns:
            bool: 是否设置成功。成功返回True; 失败返回False。
        """
        pass

    @classmethod
    @call_service(func_name="setChassisAbnormal")
    def setChassis(cls, code: int, desc: str, reason: str, method: str) -> bool:
        """设置车体异常

        Args:
            code (int): 异常码
            desc (str): 异常现象描述
            reason (str): 异常原因
            method (str): 异常处理方法

        Returns:
            bool: 是否设置成功。成功返回True; 失败返回False。
        """
        pass
