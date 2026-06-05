import json

from syspy.core.rbk_rpc import default_plugin, call_service
from syspy.recognize import RecognizeInterface


@default_plugin("RecoFactory")  # todo RBK4
class RecognizeV4(RecognizeInterface):
    @classmethod
    @call_service()
    def doRec(
        cls,
        objectModelPath: str,
        recognitionRegion: str = "",
        recognitionSide: str = "A",
    ):
        pass

    @classmethod
    @call_service()
    def getRecResults(cls) -> dict:
        pass

    @classmethod
    def recTargetObs(
        cls,
        deviceName: str,
        x: float,
        y: float,
        theta: float,
        obs_area_min_height: float,
        obs_area_max_height: float,
        obs_area_length: float,
        obs_area_width: float,
    ):
        dict_str = {
            "deviceName": deviceName,
            "x": x,
            "y": y,
            "theta": theta,
            "obs_area_min_height": obs_area_min_height,
            "obs_area_max_height": obs_area_max_height,
            "obs_area_length": obs_area_length,
            "obs_area_width": obs_area_width,
        }
        # todo RBK4
        cls.client().call_service("RecoFactory", "recTargetObs", json.dumps(dict_str))

    @classmethod
    @call_service()
    def getForkTipObsDist(cls, json: str) -> str:
        pass

    @classmethod
    @call_service()
    def setRealtimeDetect(cls, jsonStr: str):
        pass

    @classmethod
    @call_service()
    def resetRec(cls):
        pass

    @classmethod
    @call_service()
    def getRecStatus(cls) -> int:
        pass

    @classmethod
    @call_service()
    def multiShelfDetect(cls, seq: int):
        pass

    @classmethod
    @call_service()
    def loadStatus(cls, dist: float):
        pass

    @classmethod
    @call_service(plugin_name="NetProtocol")  # todo RBK4
    def getRecFile(cls, name: str) -> str:
        pass
