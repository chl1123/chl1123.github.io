from abc import ABC
from typing import Any, Dict, List, Optional, TypedDict

from google.protobuf.json_format import MessageToDict

from syspy.core.rbk_rpc import Message, RBKVersionError
from syspy.utils import Coordinate


class MapSiteData(TypedDict, total=False):
    className: str
    instanceName: str
    pointName: str
    workspace: str
    mapName: str
    x: float
    y: float
    dir: float
    width: float
    length: float
    height: float
    desc: str
    jsonObject: dict


class MapPointData(TypedDict):
    x: float
    y: float
    dir: Optional[float]


MapData = Dict[str, Any]


class MapInterface(ABC, Message):
    """地图类"""

    @classmethod
    def switchMap(
            cls,
            map: str,
            switchPoint: str,
            center_x: float = 0.0,
            center_y: float = 0.0,
            initial_angle: float = 65535.0,
    ) -> int:
        """切换地图

        Args:
            map (str): 地图名称
            switchPoint (str): 重定位点位
            center_x (float): 重定位中心点 x 坐标 单位 m
            center_y (float): 重定位中心点 y 坐标 单位 m
            initial_angle (float): 重定位中心朝向 单位 degree

        Returns:
            (int): 2没有进行切换，1切换中，0切换成功，-1不存在地图，-2切换失败
        """
        raise RBKVersionError()

    def _normalize_site_data(self, raw_site: Any) -> MapSiteData:
        json_object = {}
        if hasattr(raw_site, "jsonObject"):
            try:
                json_object = MessageToDict(raw_site.jsonObject, preserving_proto_field_name=True)
            except Exception:
                json_object = {}

        return {
            "className": getattr(raw_site, "className", ""),
            "instanceName": getattr(raw_site, "instanceName", ""),
            "pointName": getattr(raw_site, "pointName", ""),
            "x": float(getattr(raw_site, "x", 0.0) or 0.0),
            "y": float(getattr(raw_site, "y", 0.0) or 0.0),
            "dir": float(getattr(raw_site, "dir", 0.0) or 0.0),
            "width": float(getattr(raw_site, "width", 0.0) or 0.0),
            "length": float(getattr(raw_site, "length", 0.0) or 0.0),
            "height": float(getattr(raw_site, "height", 0.0) or 0.0),
            "jsonObject": json_object,
        }

    def _get_site_data_list(self) -> List[MapSiteData]:
        raise RBKVersionError()

    def getMapDataList(self, data_name: str, map_name: str = "") -> Optional[List[MapData]]:
        """读取当前地图 ``0.smap`` 中指定根字段的对象列表。

        Args:
            data_name (str): 地图 JSON 根字段名，例如
                ``callButtonList``、``autoGateList``、``topoAreaList``。

        Returns:
            (Optional[List[dict]]): 对应字段经过校验并补齐可选默认值后的
                对象列表；根字段未配置时返回 None，配置为空数组时返回 []。

        Raises:
            ValueError: 地图不可读或字段格式不符合地图规范。
        """
        raise RBKVersionError()

    def getMapData(
            self, data_name: str, instance_name: str,
            map_name: str = "") -> Optional[MapData]:
        """按实例名读取当前地图 ``0.smap`` 中的一个对象。"""
        raise RBKVersionError()

    def getAdvancedAreaList(self, map_name: str = "") -> Optional[List[MapData]]:
        """读取高级区域列表。"""
        raise RBKVersionError()

    def getAdvancedCurveList(self, map_name: str = "") -> Optional[List[MapData]]:
        """读取连接线列表。"""
        raise RBKVersionError()

    def getAdvancedLineList(self, map_name: str = "") -> Optional[List[MapData]]:
        """读取禁行线列表。"""
        raise RBKVersionError()

    def getAdvancedPointList(self, map_name: str = "") -> Optional[List[MapData]]:
        """读取站点列表。"""
        raise RBKVersionError()

    def getPoint(
            self, point_name: str, coordinate: Coordinate = Coordinate.WORLD,
            map_name: str = "",
    ) -> Optional[MapPointData]:
        """读取一个站点的地图坐标和可选朝向。

        Args:
            point_name (str): ``advancedPointList`` 中的站点实例名，或
                ``LM``/``SM`` 点的编号后缀。例如 ``"LM123"``、``"SM123"``
                和 ``"123"`` 均可查询编号为 123 的点。
            coordinate (Coordinate): 返回坐标系，``"world"``（默认）或
                ``"robot"``。机器人坐标系以调用时的机器人位姿为基准。
            map_name (str): 地图名称；缺省时读取当前地图。

        Returns:
            (Optional[MapPointData]): 找到时返回 ``x``、``y``（单位 m）和
            ``dir``（单位 degree）。站点未勾选朝向时 ``dir`` 为 ``None``；
            站点不存在时返回 ``None``。
        """
        raise RBKVersionError()

    def getTopoAreaList(self, map_name: str = "") -> Optional[List[MapData]]:
        """读取拓扑区域列表。"""
        raise RBKVersionError()

    def getTagGroupList(self, map_name: str = "") -> Optional[List[MapData]]:
        """读取二维码组列表。"""
        raise RBKVersionError()

    def getReflectorPosList(self, map_name: str = "") -> Optional[List[MapData]]:
        """读取反光柱列表。"""
        raise RBKVersionError()

    def getChargerList(self, map_name: str = "") -> Optional[List[MapData]]:
        """读取充电桩列表。"""
        raise RBKVersionError()

    def getAutoGateList(self, map_name: str = "") -> Optional[List[MapData]]:
        """读取自动门列表。"""
        raise RBKVersionError()

    def getCallButtonList(self, map_name: str = "") -> Optional[List[MapSiteData]]:
        """读取当前地图的按键呼叫器配置。

        呼叫器对象沿用充电桩的地图对象字段，并通过 ``pointName`` 绑定
        被呼叫后前往的目标站点。
        """
        raise RBKVersionError()

    def getBinList(self, map_name: str = "") -> Optional[List[MapData]]:
        """读取库位列表。"""
        raise RBKVersionError()

    def getBinTaskList(self, map_name: str = "") -> Optional[List[MapData]]:
        """读取库位动作列表。"""
        raise RBKVersionError()

    def getPolicyList(self, map_name: str = "") -> Optional[List[MapData]]:
        """读取地图策略列表。"""
        raise RBKVersionError()

    def getSiteData(self, point_name: str, workspace: str = "") -> Optional[MapSiteData]:
        """通过站点名/绑定点名获取地图站点扩展数据。"""
        raise RBKVersionError()

    def getSiteDataByName(
            self, instance_name: str, class_name: str = "",
            workspace: str = "") -> Optional[MapSiteData]:
        """通过地图对象实例名获取站点扩展数据。"""
        raise RBKVersionError()

    def getSiteDataList(
            self, class_name: str = "", point_name: str = "",
            workspace: str = "") -> Optional[List[MapSiteData]]:
        """批量获取地图站点扩展数据。"""
        raise RBKVersionError()

    def getCurrentMapName(self) -> str:
        """返回地图消息当前加载的地图名。"""
        raise RBKVersionError()

    def getCurrentWorkspace(self) -> str:
        """返回拓扑中与当前地图绑定的 workspace。"""
        raise RBKVersionError()

    def getWorkspaceList(self) -> List[MapData]:
        """读取工作空间拓扑列表。

        Returns:
            (List[MapData]): ``workspace_topology.json`` 中的
            ``workspaceList``，每项包含 ``workspace`` 和 ``map`` 等原始字段。

        Raises:
            ValueError: 拓扑文件不可读，或 ``workspaceList`` 不是数组。
        """
        raise RBKVersionError()

    def getMapNameByWorkspace(self, workspace: str) -> str:
        """返回拓扑中 workspace 绑定的地图名。"""
        raise RBKVersionError()


from syspy import RBK_VERSION
if RBK_VERSION == 3:
    from syspy.v3.map import MapV3
    Map: MapInterface = MapV3()
elif RBK_VERSION == 4:
    from syspy.v4.map import MapV4
    Map: MapInterface = MapV4()
else:
    raise ValueError(f"Unsupported RBK version: {RBK_VERSION}")
