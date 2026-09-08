import json
import os
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Tuple

from syspy.core.rbk_rpc import call_service, default_plugin
from syspy.map import MapInterface


@dataclass(frozen=True)
class MapListSpec:
    required: Tuple[str, ...]
    defaults: dict = field(default_factory=dict)
    list_fields: Tuple[str, ...] = ()
    dict_fields: Tuple[str, ...] = ()
    numeric_fields: Tuple[str, ...] = ()


_SITE_DEFAULTS = {
    "dir": 0.0,
    "width": 0.0,
    "length": 0.0,
    "height": 0.0,
    "desc": "",
    "jsonObject": {},
}
_MAP_LIST_SPECS = {
    "advancedAreaList": MapListSpec(
        ("className", "instanceName", "posGroup"),
        {"dir": 0.0, "property": [], "attribute": {}, "desc": ""},
        ("posGroup", "property"), ("attribute",), ("dir",),
    ),
    "advancedCurveList": MapListSpec(
        ("className", "instanceName", "startPos", "endPos"),
        {"property": [], "desc": ""}, ("property",),
    ),
    "advancedLineList": MapListSpec(
        ("className", "instanceName", "line"),
        {"property": [], "desc": ""}, ("property",), ("line",),
    ),
    "advancedPointList": MapListSpec(
        ("className", "instanceName", "pos"),
        {"dir": 0.0, "ignoreDir": False, "property": [], "desc": ""},
        ("property",), ("pos",), ("dir",),
    ),
    "topoAreaList": MapListSpec(
        ("className", "instanceName"),
        {"advancedPointNames": [], "posGroup": [], "property": [],
         "attribute": {}, "dir": 0.0, "desc": ""},
        ("advancedPointNames", "posGroup", "property"), ("attribute",),
        ("dir",),
    ),
    "tagGroupList": MapListSpec(
        ("instanceName",),
        {"tagType": "", "tagPosList": [], "angle": 0.0},
        ("tagPosList",), (), ("angle",),
    ),
    "reflectorPosList": MapListSpec(
        ("type", "width", "x", "y"), numeric_fields=("width", "x", "y"),
    ),
    "chargerList": MapListSpec(
        ("className", "instanceName", "pointName", "x", "y"),
        _SITE_DEFAULTS, dict_fields=("jsonObject",),
        numeric_fields=("x", "y", "dir", "width", "length", "height"),
    ),
    "autoGateList": MapListSpec(
        ("className", "instanceName", "pointNames", "x", "y"),
        {**_SITE_DEFAULTS, "pointNames": [], "isEnabled": True},
        ("pointNames",), ("jsonObject",),
        ("x", "y", "dir", "width", "length", "height"),
    ),
    "callButtonList": MapListSpec(
        ("className", "instanceName", "pointName", "x", "y"),
        _SITE_DEFAULTS, dict_fields=("jsonObject",),
        numeric_fields=("x", "y", "dir", "width", "length", "height"),
    ),
    "bins": MapListSpec(("bin",), list_fields=("bin",)),
    "binTasks": MapListSpec(
        ("key", "name"),
        {"value": {}, "isRecovered": False, "isExclusive": False},
        dict_fields=("value",),
    ),
    "policies": MapListSpec(
        ("key", "name", "type"),
        {"value": {}, "instanceName": "", "isRecovered": False,
         "isExclusive": False},
        dict_fields=("value",),
    ),
}


@default_plugin("MoveFactory")
class MapV3(MapInterface):
    _TOPIC = "rbk.protocol.msgMap"
    _PLUGIN = "BlockMapLoader"
    _MODEL_CLASS = None
    _TOPOLOGY_PATH = "/opt/.data/rbk/resources/maps/workspace_topology.json"

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf.message.message_map_pb2 import msgMap

            cls._MODEL_CLASS = msgMap

    def getCurrentMapName(self):
        if not self.update():
            return ""
        return str(getattr(getattr(self.data, "header", None), "mapName", ""))

    def getCurrentWorkspace(self):
        name = self.getCurrentMapName()
        values = [w for w, m in self._workspace_map().items() if m == name]
        return values[0] if len(values) == 1 else ""

    def getMapNameByWorkspace(self, workspace):
        return self._workspace_map().get(str(workspace), "")

    def _workspace_map(self):
        try:
            with open(self._TOPOLOGY_PATH, encoding="utf-8") as stream:
                data = json.load(stream)
        except (OSError, TypeError, ValueError):
            return {}
        return {
            str(x["workspace"]): str(x["map"])
            for x in data.get("workspaceList", [])
            if x.get("workspace") and x.get("map")
        }

    def _map_file_data(self, map_name=""):
        map_name = str(map_name or self.getCurrentMapName())
        path = os.path.join(os.path.dirname(self._TOPOLOGY_PATH), map_name, "0.smap")
        try:
            with open(path, encoding="utf-8") as stream:
                data = json.load(stream)
        except (OSError, TypeError, ValueError) as error:
            raise ValueError(f"failed to load map {map_name}: {error}")
        if not isinstance(data, dict):
            raise ValueError(f"map {map_name} root must be an object")
        return data

    @staticmethod
    def _normalize_item(name, index, raw):
        path = f"0.smap.{name}[{index}]"
        if not isinstance(raw, dict):
            raise ValueError(f"{path} must be an object")
        spec = _MAP_LIST_SPECS[name]
        result = deepcopy(raw)
        for key in spec.required:
            if key not in result or result[key] is None:
                raise ValueError(f"{path}.{key} is required")
        for key, value in spec.defaults.items():
            result.setdefault(key, deepcopy(value))
        for key in spec.list_fields:
            if not isinstance(result[key], list):
                raise ValueError(f"{path}.{key} must be an array")
        for key in spec.dict_fields:
            if not isinstance(result[key], dict):
                raise ValueError(f"{path}.{key} must be an object")
        for key in spec.numeric_fields:
            try:
                result[key] = float(result[key])
            except (KeyError, TypeError, ValueError):
                raise ValueError(f"{path}.{key} must be numeric")
        if name == "advancedPointList":
            for key in ("x", "y"):
                try:
                    result["pos"][key] = float(result["pos"][key])
                except (KeyError, TypeError, ValueError):
                    raise ValueError(f"{path}.pos.{key} must be numeric")
        return result

    def getMapDataList(self, data_name, map_name=""):
        if data_name not in _MAP_LIST_SPECS:
            raise ValueError(f"unsupported map list: {data_name}")
        data = self._map_file_data(map_name)
        if data_name not in data:
            return None
        if not isinstance(data[data_name], list):
            raise ValueError(f"0.smap.{data_name} must be an array")
        return [
            self._normalize_item(data_name, i, value)
            for i, value in enumerate(data[data_name])
        ]

    def getMapData(self, data_name, instance_name, map_name=""):
        matches = [
            x for x in (self.getMapDataList(data_name, map_name) or [])
            if str(x.get("instanceName", "")) == str(instance_name)
        ]
        return matches[0] if len(matches) == 1 else None

    def getAdvancedAreaList(self, map_name=""):
        return self.getMapDataList("advancedAreaList", map_name)

    def getAdvancedCurveList(self, map_name=""):
        return self.getMapDataList("advancedCurveList", map_name)

    def getAdvancedLineList(self, map_name=""):
        return self.getMapDataList("advancedLineList", map_name)

    def getAdvancedPointList(self, map_name=""):
        return self.getMapDataList("advancedPointList", map_name)

    def getTopoAreaList(self, map_name=""):
        return self.getMapDataList("topoAreaList", map_name)

    def getTagGroupList(self, map_name=""):
        return self.getMapDataList("tagGroupList", map_name)

    def getReflectorPosList(self, map_name=""):
        return self.getMapDataList("reflectorPosList", map_name)

    def getChargerList(self, map_name=""):
        return self.getMapDataList("chargerList", map_name)

    def getAutoGateList(self, map_name=""):
        return self.getMapDataList("autoGateList", map_name)

    def getCallButtonList(self, map_name=""):
        return self.getMapDataList("callButtonList", map_name)

    def getBinList(self, map_name=""):
        return self.getMapDataList("bins", map_name)

    def getBinTaskList(self, map_name=""):
        return self.getMapDataList("binTasks", map_name)

    def getPolicyList(self, map_name=""):
        return self.getMapDataList("policies", map_name)

    @staticmethod
    def _properties_to_json_object(properties):
        result = {}
        for item in properties:
            key = str(item.get("key", ""))
            value = item.get("value")
            if "value" not in item:
                value = next(
                    (item[name] for name in (
                        "stringValue", "boolValue", "int32Value", "uint32Value",
                        "int64Value", "uint64Value", "floatValue", "doubleValue",
                        "bytesValue") if name in item),
                    None,
                )
            if item.get("type") == "json" and isinstance(value, str):
                try:
                    value = json.loads(value)
                except (TypeError, ValueError):
                    pass
            if key: result[key] = value
        return result

    def _get_site_data_list(self):
        if not self.update():
            return []
        map_name = self.getCurrentMapName()
        workspace = self.getCurrentWorkspace()
        policies = {x["key"]: x for x in (self.getPolicyList(map_name) or [])}
        sites = []
        for point in (self.getAdvancedPointList(map_name) or []):
            obj = self._properties_to_json_object(point["property"])
            policy = policies.get(str(obj.get("policy") or ""), {})
            extra = policy.get("value", {}).get("userExtra")
            if isinstance(extra, str):
                try:
                    extra = json.loads(extra)
                except (TypeError, ValueError):
                    extra = None
            if isinstance(extra, dict):
                obj["userExtra"] = extra
            site = {
                "className": point["className"],
                "instanceName": point["instanceName"],
                "pointName": point["instanceName"],
                "workspace": workspace,
                "mapName": map_name,
                "x": point["pos"]["x"],
                "y": point["pos"]["y"],
                "dir": point["dir"],
                "desc": point["desc"],
            }
            if obj:
                site["jsonObject"] = obj
            sites.append(site)
        for site in ((self.getChargerList(map_name) or [])
                     + (self.getCallButtonList(map_name) or [])):
            site.update(workspace=workspace, mapName=map_name)
            sites.append(site)
        for device in getattr(self.data, "externalDeviceList", ()):
            obj = {}
            for item in device.property:
                try:
                    field = item.WhichOneof("oneofValue")
                except (AttributeError, ValueError):
                    field = None
                if field:
                    obj[str(item.key)] = getattr(item, field)
            site = {
                "className": device.className,
                "instanceName": device.instanceName,
                "pointName": device.instanceName,
                "workspace": workspace,
                "mapName": map_name,
                "x": 0.0,
                "y": 0.0,
                "dir": 0.0,
            }
            if obj:
                site["jsonObject"] = obj
            sites.append(site)
        return sites

    def getSiteData(self, point_name, workspace=""):
        values = self.getSiteDataList(point_name=point_name, workspace=workspace)
        return values[0] if values else None

    def getSiteDataByName(self, instance_name, class_name="", workspace=""):
        values = self.getSiteDataList(class_name=class_name, workspace=workspace)
        values = [x for x in values if x.get("instanceName") == instance_name]
        return values[0] if values else None

    def getSiteDataList(self, class_name="", point_name="", workspace=""):
        cls = class_name.strip().lower()
        return [
            x for x in self._get_site_data_list()
            if (not cls or str(x.get("className", "")).lower() == cls)
            and (not point_name or x.get("pointName") == point_name)
            and (not workspace or x.get("workspace") == workspace)
        ]

    @classmethod
    @call_service()
    def switchMap(
            cls, map, switchPoint, center_x=0.0, center_y=0.0,
            initial_angle=65535.0):
        pass
