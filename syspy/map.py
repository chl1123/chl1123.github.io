from abc import ABC
from typing import Any, List, TypedDict

from google.protobuf.json_format import MessageToDict

from syspy.core.rbk_rpc import Message, RBKVersionError


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
    jsonObject: dict


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

    def getSiteData(self, point_name: str, workspace: str = "") -> MapSiteData:
        """通过站点名/绑定点名获取地图站点扩展数据。"""
        for site_data in self.getSiteDataList(
                point_name=point_name, workspace=workspace):
            if site_data.get("pointName") == point_name:
                return site_data
        return {}

    def getSiteDataByName(
            self, instance_name: str, class_name: str = "",
            workspace: str = "") -> MapSiteData:
        """通过地图对象实例名获取站点扩展数据。"""
        for site_data in self.getSiteDataList(
                class_name=class_name, workspace=workspace):
            if site_data.get("instanceName") == instance_name:
                return site_data
        return {}

    def getSiteDataList(
            self, class_name: str = "", point_name: str = "",
            workspace: str = "") -> List[MapSiteData]:
        """批量获取地图站点扩展数据。"""
        class_name_lower = class_name.lower().strip()
        point_name = point_name.strip()
        workspace = workspace.strip()
        results = []
        for site_data in self._get_site_data_list():
            if class_name_lower and str(site_data.get("className", "")).lower() != class_name_lower:
                continue
            if point_name and site_data.get("pointName") != point_name:
                continue
            if workspace and site_data.get("workspace") != workspace:
                continue
            results.append(site_data)
        return results

    def getCurrentMapName(self) -> str:
        """返回地图消息当前加载的地图名。"""
        return ""

    def getCurrentWorkspace(self) -> str:
        """返回拓扑中与当前地图绑定的 workspace。"""
        return ""

    def getMapNameByWorkspace(self, workspace: str) -> str:
        """返回拓扑中 workspace 绑定的地图名。"""
        return ""


from syspy import RBK_VERSION
if RBK_VERSION == 3:
    from syspy.v3.map import MapV3
    Map: MapInterface = MapV3()
elif RBK_VERSION == 4:
    from syspy.v4.map import MapV4
    Map: MapInterface = MapV4()
else:
    raise ValueError(f"Unsupported RBK version: {RBK_VERSION}")
