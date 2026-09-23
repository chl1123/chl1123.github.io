import json
from abc import ABC
from syspy.core.rbk_rpc import Service, RBKVersionError


class RecognizeInterface(ABC, Service):
    """识别类接口定义"""

    @classmethod
    def doRec(
        cls,
        objectModelPath: str,
        recognitionRegion: str = "",
        recognitionSide: str = "A",
    ):
        """进行识别

        Args:
            objectModelPath (str): 识别文件名称。
            recognitionRegion (str): 识别区域 (json 对象序列化后的字符串)，作用：确定识别方向、剔除干扰识别结果。
            recognitionSide (str): 识别面，可选 none、A、B、C、D。
        """
        raise RBKVersionError()

    @classmethod
    def getRecResults(cls) -> dict:
        """获取识别结果

        Returns:
            (dict): 识别结果的结构体。
        """
        raise RBKVersionError()

    @classmethod
    def recTargetObs(
        cls,
        deviceKey: str,
        x: float,
        y: float,
        theta: float,
        obs_area_min_height: float,
        obs_area_max_height: float,
        obs_area_length: float,
        obs_area_width: float,
    ):
        """识别指定区域内是否存在障碍物

        Args:
            deviceKey (str): 检测设备的key。
            x (float): 区域中心点 x 坐标（车体坐标系），单位 m。
            y (float): 区域中心点 y 坐标（车体坐标系），单位 m。
            theta (float): 区域角度，单位 rad。
            obs_area_min_height (float): 检测区域为长方体，检测区域最低高度，单位 m。
            obs_area_max_height (float): 检测区域最高高度，单位 m。
            obs_area_length (float): 检测区域长度，单位 m。
            obs_area_width (float): 检测区域宽度，单位 m。
        """
        dict_str = {
            "deviceName": deviceKey,
            "x": x,
            "y": y,
            "theta": theta,
            "obs_area_min_height": obs_area_min_height,
            "obs_area_max_height": obs_area_max_height,
            "obs_area_length": obs_area_length,
            "obs_area_width": obs_area_width,
        }

        cls.client().call_service("RecoFactory", "recTargetObs", json.dumps(dict_str))

    @classmethod
    def getForkTipObsDist(cls, json: str) -> str:
        """获取叉尖障碍物检测状态和超时距离

        Args:
            json (str): 包含任务参数的 JSON 字符串。

        Returns:
            (str): 包含检测状态和超时距离的 JSON 字符串。
        """
        raise RBKVersionError()

    @classmethod
    def setRealtimeDetect(cls, jsonStr: str):
        """设置实时检测参数

        Args:
            jsonStr (str): 包含实时检测参数的 JSON 字符串。
        """
        raise RBKVersionError()

    @classmethod
    def resetRec(cls):
        """重置识别模块"""
        raise RBKVersionError()

    @classmethod
    def getRecStatus(cls) -> int:
        """获取识别状态

        Returns:
            (int): 0 刚刚初始化，1 识别中，2 获得结果，3 识别出错，-1 未知错误。
        """
        raise RBKVersionError()

    @classmethod
    def multiShelfDetect(cls, seq: int):
        """触发多货架检测

        Args:
            seq (int): 检测序号。
        """
        raise RBKVersionError()

    @classmethod
    def loadStatus(cls, dist: float):
        """设置载货状态距离

        Args:
            dist (float): 距离，单位 m。
        """
        raise RBKVersionError()

    @classmethod
    def getRecFile(cls, name: str) -> str:
        """获得识别文件的原始数据

        Args:
            name (str): 识别文件名称，比如 shelf.srec, pallet.srec。

        Returns:
            (str): 识别文件内容（JSON 字符串）。
        """
        raise RBKVersionError()


from syspy import RBK_VERSION

if RBK_VERSION == 3:
    from syspy.v3.recognize import RecognizeV3

    Recognize: RecognizeInterface = RecognizeV3()
elif RBK_VERSION == 4:
    from syspy.v4.recognize import RecognizeV4

    Recognize: RecognizeInterface = RecognizeV4()
else:
    raise ValueError(f"Unsupported RBK version: {RBK_VERSION}")
