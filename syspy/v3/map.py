import json
import os

from syspy.core.rbk_rpc import call_service, default_plugin
from syspy.map import MapInterface


@default_plugin("MoveFactory")
class MapV3(MapInterface):
    """地图类"""

    _TOPIC = "rbk.protocol.msgMap"
    _PLUGIN = "BlockMapLoader"
    _MODEL_CLASS = None
    _MM_COORDINATE_THRESHOLD = 1000.0
    _TOPOLOGY_PATH = "/opt/.data/rbk/resources/maps/workspace_topology.json"

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf.message.message_map_pb2 import msgMap
            cls._MODEL_CLASS = msgMap

    def getCurrentMapName(self) -> str:
        if not self.update():
            return ""
        return str(getattr(getattr(self.data, "header", None), "mapName", ""))

    def getCurrentWorkspace(self) -> str:
        map_name = self.getCurrentMapName()
        workspaces = [
            workspace for workspace, mapped_name in self._workspace_map().items()
            if mapped_name == map_name
        ]
        return workspaces[0] if len(workspaces) == 1 else ""

    def getMapNameByWorkspace(self, workspace: str) -> str:
        return self._workspace_map().get(str(workspace), "")

    def _workspace_map(self) -> dict:
        try:
            with open(self._TOPOLOGY_PATH, encoding="utf-8") as stream:
                topology = json.load(stream)
        except (OSError, TypeError, ValueError):
            return {}
        return {
            str(item["workspace"]): str(item["map"])
            for item in topology.get("workspaceList", [])
            if item.get("workspace") and item.get("map")
        }

    def _mark_policy_user_extra(self, map_name: str) -> dict:
        map_path = os.path.join(
            os.path.dirname(self._TOPOLOGY_PATH), map_name, "0.smap"
        )
        try:
            with open(map_path, encoding="utf-8") as stream:
                map_data = json.load(stream)
        except (OSError, TypeError, ValueError):
            return {}

        result = {}
        for policy in map_data.get("policies", []):
            if policy.get("type") != "map:mark" or not policy.get("key"):
                continue
            user_extra = (policy.get("value") or {}).get("userExtra")
            if isinstance(user_extra, str):
                try:
                    user_extra = json.loads(user_extra)
                except (TypeError, ValueError):
                    continue
            if isinstance(user_extra, dict):
                result[str(policy["key"])] = user_extra
        return result

    def _coordinate_scale(self) -> float:
        """Return the scale needed to expose map coordinates in metres.

        RBK 3 map messages from the simulator/older MF builds may contain
        integer-like millimetres (e.g. 5917), while injected test messages and
        map files commonly already use metres.  A map-sized coordinate is a
        reliable discriminator without changing the latter representation.
        """
        if not self.data:
            return 1.0
        values = []
        for point in getattr(self.data, "advancedPointList", ()):
            values.extend((abs(float(point.pos.x)), abs(float(point.pos.y))))
        for charger in getattr(self.data, "chargerList", ()):
            values.extend((abs(float(charger.x)), abs(float(charger.y))))
        return 0.001 if values and max(values) >= self._MM_COORDINATE_THRESHOLD else 1.0

    @staticmethod
    def _property_value(property_value):
        """Convert a map property oneof to its Python value."""
        try:
            field = property_value.WhichOneof("oneofValue")
        except (AttributeError, ValueError):
            field = None
        if not field:
            return None
        value = getattr(property_value, field)
        if getattr(property_value, "type", "") == "json" and field == "stringValue":
            try:
                return json.loads(value)
            except (TypeError, ValueError):
                return value
        return value

    @classmethod
    def _properties_to_json_object(cls, properties) -> dict:
        result = {}
        for property_value in properties or ():
            key = str(getattr(property_value, "key", "") or "")
            if not key:
                continue
            value = cls._property_value(property_value)
            if key == "jsonObject" and isinstance(value, dict):
                result.update(value)
            else:
                result[key] = value
        return result

    def _get_site_data_list(self) -> list:
        if not self.update():
            return []
        scale = self._coordinate_scale()
        map_name = self.getCurrentMapName()
        workspace = self.getCurrentWorkspace()
        policy_user_extra = self._mark_policy_user_extra(map_name)
        sites = [{
            "className": point.className,
            "instanceName": point.instanceName,
            "pointName": point.instanceName,
            "workspace": workspace,
            "mapName": map_name,
            "x": float(point.pos.x) * scale,
            "y": float(point.pos.y) * scale,
            "dir": float(point.dir),
        } for point in self.data.advancedPointList]
        for site, point in zip(sites, self.data.advancedPointList):
            json_object = self._properties_to_json_object(point.property)
            policy_key = str(json_object.get("policy") or "")
            if policy_key in policy_user_extra:
                json_object["userExtra"] = policy_user_extra[policy_key]
            if json_object:
                site["jsonObject"] = json_object
        for charger in self.data.chargerList:
            site = self._normalize_site_data(charger)
            site["workspace"] = workspace
            site["mapName"] = map_name
            site["x"] *= scale
            site["y"] *= scale
            sites.append(site)
        for device in self.data.externalDeviceList:
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
            json_object = self._properties_to_json_object(device.property)
            if json_object:
                site["jsonObject"] = json_object
            sites.append(site)
        return sites

    @classmethod
    @call_service()
    def switchMap(
            cls,
            map: str,
            switchPoint: str,
            center_x: float = 0.0,
            center_y: float = 0.0,
            initial_angle: float = 65535.0,
    ) -> int:
        pass
