from typing import Union, List

from .py_rpc import Service, default_plugin, call_service


@default_plugin("Abnormal")
class Abnormal(Service):

    @classmethod
    def exists(cls, codes: Union[int, List[int]]) -> Union[bool, List[bool]]:
        """异常码是否存在

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
    @call_service(func_name="clearAbnormal")
    def clear(cls, code: int) -> bool:
        """清除异常码

        Args:
            code (int): 异常码

        Returns:
            bool: 是否清除成功。清楚成功返回True; 不存在异常码或清除失败返回False。
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
    def setTask(cls, code: int, desc: str, reason: str, method: str, task: Union[str, list, dict]) -> bool:
        """设置任务异常

        Args:
            code (int): 异常码
            desc (str): 异常现象描述
            reason (str): 异常原因
            method (str): 异常处理方法
            task (str): 异常任务内容

        Returns:
            bool: 是否设置成功。成功返回True; 失败返回False。
        """
        return cls.client().call_service("Abnormal", "setTaskAbnormal", code, desc, reason, method, str(task))

    @classmethod
    @call_service(func_name="setMapAbnormal")
    def setMap(cls, code: int, desc: str, reason: str, method: str, fileName: str, mapType: str = "",
               elementType: str = "", elementName: str = "", param: str = "") -> bool:
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
            param (str): 异常参数(可缺省)

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
    @call_service(func_name="setAppAbnormal")
    def setApp(cls, code: int, desc: str, reason: str, method: str, appType: str, fileName: str,
               param: str = "") -> bool:
        """设置App异常

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
    @call_service(func_name="setSRCAbnormal")
    def setSRC(cls, code: int, desc: str, reason: str, method: str) -> bool:
        """设置SRC异常

        Args:
            code (int): 异常码（原报警码）
            desc (str): 异常现象描述
            reason (str): 异常原因
            method (str): 异常处理方法

        Returns:
            bool: 是否设置成功。成功返回True; 失败返回False。
        """
        pass

    @classmethod
    @call_service(func_name="setEnvironmentAbnormal")
    def setEnvironment(cls, code: int, desc: str, reason: str, method: str) -> bool:
        """设置环境异常

        Args:
            code (int): 异常码（原报警码）
            desc (str): 异常现象描述
            reason (str): 异常原因
            method (str): 异常处理方法

        Returns:
            bool: 是否设置成功。成功返回True; 失败返回False。
        """
        pass

    @classmethod
    @call_service(func_name="setDeviceAbnormal")
    def setDevice(cls, code: int, desc: str, reason: str, method: str, fileName: str, deviceType: str = "",
                  deviceName: str = "", param: str = "", errorCode: int = 0) -> bool:
        """设置设备异常

        Args:
            code (int): 异常码（原报警码）
            desc (str): 异常现象描述
            reason (str): 异常原因
            method (str): 异常处理方法
            fileName (str): 异常（设备模型）文件名
            deviceType (str): 异常设备类型
            deviceName (str): 异常设备名
            param (str): 异常参数
            errorCode (int): device上报

        Returns:
            bool: 是否设置成功。成功返回True; 失败返回False。
        """
        pass

    @classmethod
    @call_service(func_name="setConnectionAbnormal")
    def setConnect(cls, code: int, desc: str, reason: str, method: str, fileName: str, deviceType: str = "",
                   deviceName: str = "", param: str = "") -> bool:
        """设置连接异常

        Args:
            code (int): 异常码
            desc (str): 异常现象描述
            reason (str): 异常原因
            method (str): 异常处理方法
            fileName (str): 异常（设备模型）文件名
            deviceType (str): 异常设备类型
            deviceName (str): 异常设备名
            param (str): 异常参数

        Returns:
            bool: 是否设置成功。成功返回True; 失败返回False。
        """
        pass

    @classmethod
    @call_service(func_name="setCalibrationAbnormal")
    def setCalibrate(cls, code: int, desc: str, reason: str, method: str, fileName: str, param: str = "") -> bool:
        """设置标定异常

        Args:
            code (int): 异常码
            desc (str): 异常现象描述
            reason (str): 异常原因
            method (str): 异常处理方法
            fileName (str): 异常设备文件名
            param (str): 异常设备key

        Returns:
            bool: 是否设置成功。成功返回True; 失败返回False。
        """
        pass

    @classmethod
    @call_service(func_name="setAPIAbnormal")
    def setAPI(cls, code: int, desc: str, reason: str, method: str, APIcode: int = 0, context: str = "",
               param: str = "") -> bool:
        """设置API异常

        Args:
            code (int): 异常码
            desc (str): 异常现象描述
            reason (str): 异常原因
            method (str): 异常处理方法
            APIcode (int): API编号
            context (str): 请求内容
            param (str): 异常内容

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
