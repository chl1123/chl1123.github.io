from .lib.py_rpc import Service, default_plugin, call_service


@default_plugin("RecoFactory")
class Recognize(Service):
    @classmethod
    @call_service()
    def doRec(cls, file: str, withRegion: bool, x: float = 0.0, y: float = 0.0, theta: float = 0.0,
              radius: float = 0.0):
        """
        Args:

        Returns:

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
    @call_service()
    def recTargetObs(cls, paramJson: str):
        """
        Args:
            paramJson (str): JSON string containing the target observation parameters.

        Returns:
            None
        """
        pass

    @classmethod
    @call_service()
    def getForkTipObsDist(cls, json: str) -> str:
        """
        Args:
            json (str): JSON string containing task parameters.

        Returns:
            str: JSON string with the detection status and exceed distance.
        """
        pass

    @classmethod
    @call_service()
    def setRealtimeDetect(cls, jsonStr: str):
        """
        Args:
            jsonStr (str): JSON string containing real-time detection parameters.

        Returns:
            None
        """
        pass

    @classmethod
    @call_service()
    def resetRec(cls):
        """重置识别模块
        """
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
    @call_service(plugin_name="NetProtocol")
    def getRecFile(cls, name: str) -> str:
        """获得识别文件的原始数据
        Args:
            name (str): 识别文件名称，比如 shelf/s0001.shelf, pallet/p0001.pallet
        Returns:
            dict: 具体数据以字典类型返回
        """
        pass
