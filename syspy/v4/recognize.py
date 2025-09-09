import json

from syspy.core.rbk_rpc import default_plugin, call_service
from syspy.recognize import RecognizeInterface


@default_plugin("RecoFactory")  # todo RBK4
class RecognizeV4(RecognizeInterface):

    @classmethod
    @call_service()
    def doRec(
            cls,
            file: str,
            withRegion: bool,
            x: float = 0.0,
            y: float = 0.0,
            theta: float = 0.0,
            radius: float = 0.0,
            recognition_side: str = "A"
    ):
        """进行识别

        Args:
            file (str): 识别文件
            withRegion (bool): 是否有限制识别区域(扇形)
            x (float): 识别区域的圆心坐标x（车体坐标系）
            y (float): 识别区域的圆心坐标y（车体坐标系）
            theta (float): 识别区域扇形角度
            radius (float):识别半径
            recognition_side (str): 识别面，可选none、A、B、C、D
        """
        pass

    @classmethod
    @call_service()
    def getRecResults(cls) -> dict:
        """获取识别结果

        Returns:
            dict: 识别结果的结构体
        """
        pass

    @classmethod
    def recTargetObs(cls, deviceName: str, x: float, y: float, theta: float, obs_area_min_height: float,
                     obs_area_max_height: float,
                     obs_area_length: float, obs_area_width: float):
        """识别指定区域内是否存在障碍物

        Args:
            deviceName (str): 检测设备名称
            x (float): 区域中心点x坐标（车体坐标系）
            y (float): 区域中心点y坐标（车体坐标系）
            theta (float): 区域角度
            obs_area_min_height (float):检测区域为长方体，检测区域最低高度
            obs_area_max_height (float):检测区域最高高度
            obs_area_length (float): 检测区域长度
            obs_area_width (float): 检测区域宽度
        """
        dict_str = {
            "deviceName": deviceName,
            "x": x,
            "y": y,
            "theta": theta,
            "obs_area_min_height": obs_area_min_height,
            "obs_area_max_height": obs_area_max_height,
            "obs_area_length": obs_area_length,
            "obs_area_width": obs_area_width
        }
        # todo RBK4
        cls.client().call_service("RecoFactory", "recTargetObs", json.dumps(dict_str))

    @classmethod
    @call_service()
    def getForkTipObsDist(cls, json: str) -> str:
        """

        Args:
            json (str): 包含任务参数的JSON字符串

        Returns:
            str: 包含检测状态和超时距离的JSON字符串
        """
        pass

    @classmethod
    @call_service()
    def setRealtimeDetect(cls, jsonStr: str):
        """

        Args:
            jsonStr (str): 包含实时检测参数的JSON字符串
        """
        pass

    @classmethod
    @call_service()
    def resetRec(cls):
        """重置识别模块"""
        pass

    @classmethod
    @call_service()
    def getRecStatus(cls) -> int:
        """获取识别状态

        Returns:
            int: 0 刚刚初始化，1识别中，2.获得结果, 3识别出错, -1 未知错误
        """
        pass

    @classmethod
    @call_service()
    def multiShelfDetect(cls, seq: int):
        """

        Args:
            seq (int):
        """
        pass

    @classmethod
    @call_service()
    def loadStatus(cls, dist: float):
        """

        Args:
            dist (float):
        """
        pass

    @classmethod
    @call_service(plugin_name="NetProtocol")  # todo RBK4
    def getRecFile(cls, name: str) -> str:
        """获得识别文件的原始数据
        Args:
            name (str): 识别文件名称，比如 shelf.srec, pallet.srec

        Returns:
            dict: 具体数据以字典类型返回
        """
        pass
