from abc import ABC
from typing import Union, List, Optional
from syspy.core.rbk_rpc import Service, RBKVersionError

VALID_ABNORMAL_CODE = [(53300, 53599), (53600, 53999)]


class AbnormalCodeError(Exception):
    """异常码范围错误异常

    当提供的异常码不在有效范围内时抛出此异常。
    有效的异常码范围为：
    - 标准脚本范围：53300-53599
    - 用户自定义脚本范围：53600-53999
    """

    def __init__(self, code: int, message: str = None):
        """初始化异常实例

        Args:
            code (int): 无效的异常码
            message (str, optional): 自定义错误消息
        """
        self.code = code
        if message is None:
            message = (f"Abnormal code '{code}' is out of valid range. "
                       f"standard scripts '{VALID_ABNORMAL_CODE[0][0]}-{VALID_ABNORMAL_CODE[0][1]}'. "
                       f"custom scripts '{VALID_ABNORMAL_CODE[1][0]}-{VALID_ABNORMAL_CODE[1][1]}'")

        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return self.message


def check_abnormal_code(code: int):
    """验证异常码是否在有效范围内

    Args:
        code (int): 要验证的异常码

    Raises:
        AbnormalCodeError: 如果异常码不在有效范围内
    """

    if not (VALID_ABNORMAL_CODE[0][0] <= code <= VALID_ABNORMAL_CODE[1][1]):
        raise AbnormalCodeError(code)


class AbnormalInterface(ABC, Service):

    @classmethod
    def exists(cls, codes: Union[int, List[int]]) -> Union[bool, List[bool]]:
        """异常是否存在

        Args:
            codes (Union[int, List[int]]): 单个或多个异常码

        Returns:
            Union[bool, List[bool]]: 是否异常。异常为True, 否则为False。输入int, 输出bool; 输入List[int], 输出List[bool]
        """
        raise RBKVersionError()

    @classmethod
    def existsDevice(cls, deviceName: str, code: Optional[int] =  None) -> bool:
        """是否存在指定设备名及异常码的异常

        Args:
            deviceName (str): 是否存在指定设备的异常
            code (Optional[int]): 指定异常码; 缺省表示是否存在设备名为deviceName所有异常

        Returns:
            bool: 是否异常。异常为True, 否则为False
        """
        raise RBKVersionError()

    @classmethod
    def clear(cls, code: int) -> bool:
        """清除异常

        Args:
            code (int): 异常码

        Returns:
            bool: 是否清除成功。清除成功返回True; 不存在异常码或清除失败返回False。
        """
        raise RBKVersionError()

    @classmethod
    def clearDevice(cls, deviceName: str, code: Optional[int] =  None) -> bool:
        """清除指定设备名及异常码的异常

        Args:
            deviceName (str): 需要清除的设备名
            code (Optional[int]): 需要清除的异常码；缺省表示清除指定deviceName的所有异常

        Returns:
            bool: 是否清除成功。清除成功返回True; 不存在异常码或清除失败返回False。
        """
        raise RBKVersionError()

    @classmethod
    def mask(cls, code: int, deviceName: Optional[str] = None) -> bool:
        """屏蔽指定异常码及设备名的异常

        Args:
            code (int): 需要屏蔽的异常码
            deviceName (Optional[str]): 需要屏蔽的异常码；缺省时表示屏蔽指定code的所有异常

        Returns:
            bool: 是否屏蔽成功。成功返回True; 不存在异常码或清除失败返回False。
        """
        raise RBKVersionError()

    @classmethod
    def unmask(cls, code: int, deviceName: Optional[str] = None):
        """取消屏蔽指定异常码及设备名的异常

        Args:
            code (int): 需要取消屏蔽的异常码
            deviceName (Optional[str]): 需要取消屏蔽的异常码；缺省时表示取消屏蔽指定code的所有异常
        """
        raise RBKVersionError()

    @classmethod
    def isMasked(cls, code: int, deviceName: Optional[str] = None) -> bool:
        """断指定异常码及设备名的异常是否被屏蔽

        Args:
            code (int): 需要查询屏蔽的异常码
            deviceName (Optional[str]): 需要查询屏蔽的设备；缺省时表示查询是否屏蔽指定code的异常

        Returns:
            bool: 是否屏蔽异常。屏蔽返回True; 没有屏蔽返回False。
        """
        raise RBKVersionError()

    @classmethod
    def getNum(cls) -> int:
        """获取异常码数量

        Returns:
            int: 异常的数量
        """
        raise RBKVersionError()

    @classmethod
    def setTask(cls, code: int, desc: str, reason: str, method: str, task: Union[str, list, dict],
                fileName: str = "", mapType: str = "", elementType: str = "", elementName: str = "",
                policyName: str = "", param: str = "") -> bool:
        """设置任务异常

        Args:
            code (int): 异常码。标准脚本：53300-53599；用户自定义脚本：53600-53999。超出该范围抛出异常。
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

        Raises:
            AbnormalCodeError: code不在允许的范围内
        """
        raise RBKVersionError()

    @classmethod
    def setMap(cls, code: int, desc: str, reason: str, method: str, fileName: str, mapType: str = "",
               elementType: str = "", elementName: str = "") -> bool:
        """设置地图异常

        Args:
            code (int): 异常码。标准脚本：53300-53599；用户自定义脚本：53600-53999。超出该范围抛出异常。
            desc (str): 异常现象描述
            reason (str): 异常原因
            method (str): 异常处理方法
            fileName (str): 异常（地图）文件名
            mapType (str): 地图类型：2D、3D、vslam、纹理等(可缺省)
            elementType (str): 异常图元类型(可缺省)
            elementName (str): 异常图元名字(可缺省)

        Returns:
            bool: 是否设置成功。成功返回True; 失败返回False。

        Raises:
            AbnormalCodeError: code不在允许的范围内
        """
        raise RBKVersionError()

    @classmethod
    def setModel(cls, code: int, desc: str, reason: str, method: str, fileName: str, deviceType: str = "",
                 deviceKey: str = "", param: str = "") -> bool:
        """设置模型异常

        Args:
            code (int): 异常码。标准脚本：53300-53599；用户自定义脚本：53600-53999。超出该范围抛出异常。
            desc (str): 异常现象描述
            reason (str): 异常原因
            method (str): 异常处理方法
            fileName (str): 异常（设备模型）文件名
            deviceType (str): 异常设备类型(可缺省)
            deviceKey (str): 异常设备(可缺省)
            param (str): 异常参数(可缺省)

        Returns:
            bool: 是否设置成功。成功返回True; 失败返回False。

        Raises:
            AbnormalCodeError: code不在允许的范围内
        """
        raise RBKVersionError()

    @classmethod
    def setConfig(cls, code: int, desc: str, reason: str, method: str, appType: str, fileName: str,
               param: str = "") -> bool:
        """设置参数配置异常

        Args:
            code (int): 异常码。标准脚本：53300-53599；用户自定义脚本：53600-53999。超出该范围抛出异常。
            desc (str): 异常现象描述
            reason (str): 异常原因
            method (str): 异常处理方法
            appType (str): App类型
            fileName (str): 异常（应用）文件名(可缺省)
            param (str): 异常参数（包含路径）(可缺省)

        Returns:
            bool: 是否设置成功。成功返回True; 失败返回False。

        Raises:
            AbnormalCodeError: code不在允许的范围内
        """
        raise RBKVersionError()

    @classmethod
    def setSystem(cls, code: int, desc: str, reason: str, method: str, fileName: str, param: str = "") -> bool:
        """设置系统异常

        Args:
            code (int): 异常码。标准脚本：53300-53599；用户自定义脚本：53600-53999。超出该范围抛出异常。
            desc (str): 异常现象描述
            reason (str): 异常原因
            method (str): 异常处理方法
            fileName (str): 异常（应用）文件名
            param (str): 异常参数（包含路径）

        Returns:
            bool: 是否设置成功。成功返回True; 失败返回False。

        Raises:
            AbnormalCodeError: code不在允许的范围内
        """
        raise RBKVersionError()

    @classmethod
    def setEnvironment(cls, code: int, desc: str, reason: str, method: str, position: str = "") -> bool:
        """设置环境异常

        Args:
            code (int): 异常码。标准脚本：53300-53599；用户自定义脚本：53600-53999。超出该范围抛出异常。
            desc (str): 异常现象描述
            reason (str): 异常原因
            method (str): 异常处理方法
            position (str): 异常坐标位置

        Returns:
            bool: 是否设置成功。成功返回True; 失败返回False。

        Raises:
            AbnormalCodeError: code不在允许的范围内
        """
        raise RBKVersionError()

    @classmethod
    def setDevice(cls, code: int, desc: str, reason: str, method: str, fileName: str, deviceType: str = "",
                  deviceKey: str = "", param: str = "", errorCode: int = 0) -> bool:
        """设置设备异常

        Args:
            code (int): 异常码。标准脚本：53300-53599；用户自定义脚本：53600-53999。超出该范围抛出异常。
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


        Raises:
            AbnormalCodeError: code不在允许的范围内
        """
        raise RBKVersionError()

    @classmethod
    def setConnect(cls, code: int, desc: str, reason: str, method: str, fileName: str, deviceType: str = "",
                   deviceKey: str = "", param: str = "") -> bool:
        """设置连接异常

        Args:
            code (int): 异常码。标准脚本：53300-53599；用户自定义脚本：53600-53999。超出该范围抛出异常。
            desc (str): 异常现象描述
            reason (str): 异常原因
            method (str): 异常处理方法
            fileName (str): 异常（设备模型）文件名
            deviceType (str): 异常设备类型
            deviceKey (str): 异常设备key
            param (str): 异常参数

        Returns:
            bool: 是否设置成功。成功返回True; 失败返回False。

        Raises:
            AbnormalCodeError: code不在允许的范围内
        """
        raise RBKVersionError()

    @classmethod
    def setCalibrate(cls, code: int, desc: str, reason: str, method: str, deviceType: str, deviceKey: str = "") -> bool:
        """设置标定异常

        Args:
            code (int): 异常码。标准脚本：53300-53599；用户自定义脚本：53600-53999。超出该范围抛出异常。
            desc (str): 异常现象描述
            reason (str): 异常原因
            method (str): 异常处理方法
            deviceType (str): 异常设备文件名
            deviceKey (str): 异常设备key

        Returns:
            bool: 是否设置成功。成功返回True; 失败返回False。

        Raises:
            AbnormalCodeError: code不在允许的范围内
        """
        raise RBKVersionError()

    @classmethod
    def setLicense(
            cls, code: int, desc: str, reason: str, method: str, licenseType: str = ""
    ) -> bool:
        """设置证书异常

        Args:
            code (int): 异常码。标准脚本：53300-53599；用户自定义脚本：53600-53999。超出该范围抛出异常。
            desc (str): 异常现象描述
            reason (str): 异常原因
            method (str): 异常处理方法
            licenseType (str): 证书类型

        Returns:
            bool: 是否设置成功。成功返回True; 失败返回False。

        Raises:
            AbnormalCodeError: code不在允许的范围内
        """
        raise RBKVersionError()

    @classmethod
    def setChassis(cls, code: int, desc: str, reason: str, method: str) -> bool:
        """设置车体异常

        Args:
            code (int): 异常码。标准脚本：53300-53599；用户自定义脚本：53600-53999。超出该范围抛出异常。
            desc (str): 异常现象描述
            reason (str): 异常原因
            method (str): 异常处理方法

        Returns:
            bool: 是否设置成功。成功返回True; 失败返回False。

        Raises:
            AbnormalCodeError: code不在允许的范围内
        """
        raise RBKVersionError()


from syspy.config import RBK_VERSION
if RBK_VERSION == 3:
    from syspy.v3.lib.abnormal import AbnormalV3
    Abnormal: AbnormalInterface = AbnormalV3()
elif RBK_VERSION == 4:
    from syspy.v4.lib.abnormal import AbnormalV4
    Abnormal: AbnormalInterface = AbnormalV4()
else:
    raise ValueError(f"Unsupported RBK version: {RBK_VERSION}")
