"""Shared helpers for the standard door and elevator scripts."""

import importlib
import json
import math
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, Optional

from syspy import Map


class DoorPhase(str, Enum):
    VALIDATING = "VALIDATING"
    ACQUIRING_CONTROL = "ACQUIRING_CONTROL"
    REQUESTING_OPEN = "REQUESTING_OPEN"
    PASSING = "PASSING"
    RELEASING = "RELEASING"
    SAFETY_HOLDING = "SAFETY_HOLDING"
    FINISHED = "FINISHED"
    FAILED = "FAILED"


class ElevatorPhase(str, Enum):
    VALIDATING = "VALIDATING"
    CALLING_SOURCE = "CALLING_SOURCE"
    WAITING_SOURCE = "WAITING_SOURCE"
    ENTERING = "ENTERING"
    RIDING = "RIDING"
    SWITCHING_MAP = "SWITCHING_MAP"
    WAITING_TARGET = "WAITING_TARGET"
    EXITING = "EXITING"
    RELEASING = "RELEASING"
    SAFETY_HOLDING = "SAFETY_HOLDING"
    FINISHED = "FINISHED"
    FAILED = "FAILED"


class DoorCarPosition(str, Enum):
    OUTSIDE = "OUTSIDE"
    PASSING = "PASSING"


class ElevatorCarPosition(str, Enum):
    UNKNOWN = "UNKNOWN"
    OUTSIDE = "OUTSIDE"
    ENTERING = "ENTERING"
    INSIDE = "INSIDE"
    EXITING = "EXITING"


class EntryMotionPhase(str, Enum):
    GUIDE = "GUIDE"
    ENTERING = "ENTERING"
    BACKING_OFF_GUIDE_RETRY = "BACKING_OFF_GUIDE_RETRY"
    BACKING_OFF_GUIDE_FINAL = "BACKING_OFF_GUIDE_FINAL"
    BACKING_OFF_CALL_POINT_FIRST = "BACKING_OFF_CALL_POINT_FIRST"
    BACKING_OFF_CALL_POINT_FINAL = "BACKING_OFF_CALL_POINT_FINAL"
    WAITING_RETRY_MOTION = "WAITING_RETRY_MOTION"
    WAITING_SOURCE = "WAITING_SOURCE"


@dataclass(frozen=True)
class DoorPassContext:
    """Resolved gate-pass state, kept out of the raw task input args.

    ``device_id`` / ``source_station`` / ``target_station`` come from the task
    input; the rest is derived from the gate map metadata and
    ``workspace_topology.json``.
    """

    device_id: str
    source_station: str
    target_station: str
    source_side: str = ""
    active_time: int = 30
    instance_args: Optional[Dict[str, Any]] = None
    protocol_site: Optional[Dict[str, Any]] = None
    point_names: Optional[Any] = None
    workspace: str = ""
    legacy_open_mode: Optional[int] = None

    @classmethod
    def from_args(cls, args):
        return cls(
            device_id=str(args.get("operation.pass.deviceId", "") or "").strip(),
            source_station=str(
                args.get("operation.pass.sourceStation", "") or ""
            ).strip(),
            target_station=str(
                args.get("operation.pass.targetStation", "") or ""
            ).strip(),
        )

    def as_payload(self):
        """Fields published to ScriptData for MF and the dashboard."""
        return {
            "deviceId": self.device_id,
            "sourceStation": self.source_station,
            "targetStation": self.target_station,
            "sourceSide": self.source_side,
        }


@dataclass(frozen=True)
class ElevatorRideContext:
    """Resolved ride state, kept out of the raw task input args.

    ``device_id`` / ``target_workspace`` / ``target_station`` come from the task
    input; everything else is derived from ``workspace_topology.json`` and the
    target map.  Mixing the two into one dict made the input params and the
    resolved context indistinguishable at the call sites.
    """

    device_id: str
    target_workspace: str
    source_workspace: str
    source_station: str
    source_switch_point: str
    source_floor: int
    target_station: str
    target_floor: int
    target_map: str
    target_switch_point: str
    target_switch_pose: Optional[Dict[str, float]] = None
    target_switch_dir: Optional[float] = None
    source_guide_point: Optional[Any] = None
    protocol_site: Optional[Dict[str, Any]] = None

    def as_payload(self):
        """Fields published to ScriptData for MF and the dashboard."""
        return {
            "deviceId": self.device_id,
            "sourceWorkspace": self.source_workspace,
            "sourceStation": self.source_station,
            "targetWorkspace": self.target_workspace,
            "targetStation": self.target_station,
        }


def enum_value(value):
    return value.value if isinstance(value, Enum) else value


def create_protocol(args, kind):
    """Load a protocol factory from the map/task protocol metadata."""
    protocol_site = args.get("protocolSite") or {}
    data = protocol_site.get("jsonObject", protocol_site)
    data = data if isinstance(data, dict) else {}

    def value(key, default=None):
        if key in args and args[key] not in (None, ""):
            return args[key]
        if key in data and data[key] not in (None, ""):
            return data[key]
        nested = data
        for part in key.split("."):
            if not isinstance(nested, dict) or part not in nested:
                return default
            nested = nested[part]
        return default if nested in (None, "") else nested

    protocol_name = str(value("communicationProtocol", "") or "").strip().lower()
    if not protocol_name:
        candidates = set()
        for key in list(args) + list(data):
            prefix = "communicationProtocol."
            if str(key).startswith(prefix):
                suffix = str(key)[len(prefix):].split(".", 1)[0].strip().lower()
                if suffix:
                    candidates.add(suffix)
        if len(candidates) == 1:
            protocol_name = candidates.pop()
    if not protocol_name:
        raise ValueError("communicationProtocol is required")

    script_name = value(
        "communicationProtocol.{}.name".format(protocol_name),
        value(
            "communicationProtocol.{}.script.name".format(protocol_name),
            "tasks/third/{}_protocol/{}.py".format(kind, protocol_name),
        ),
    )
    script_name = str(script_name or "").replace("\\", "/")
    marker = "third/{}_protocol/".format(kind)
    if marker not in script_name or not script_name.endswith(".py"):
        raise ValueError("invalid {} protocol script: {}".format(kind, script_name))
    suffix = script_name.split(marker, 1)[1][:-3].replace("/", ".")
    module = importlib.import_module("third.{}_protocol.{}".format(kind, suffix))
    factory = getattr(module, "create_protocol", None)
    if factory is None:
        raise ValueError("protocol script {} does not export create_protocol".format(script_name))
    return factory(args)


def load_workspace_topology(path):
    try:
        with open(path, encoding="utf-8") as stream:
            topology = json.load(stream)
    except (OSError, TypeError, ValueError) as error:
        raise ValueError("failed to load workspace topology: {}".format(error))
    if not isinstance(topology, dict):
        raise ValueError("workspace topology root must be an object")
    return topology


def map_device_data(device_id, workspace=""):
    if not device_id:
        return {}
    try:
        try:
            site = Map.getSiteDataByName(device_id, workspace=workspace)
        except TypeError:
            site = Map.getSiteDataByName(device_id)
        return dict(site or {})
    except Exception:
        return {}


def topology_device_data(path, key, device_id):
    try:
        topology = load_workspace_topology(path)
    except ValueError:
        return {}
    for item in topology.get(key, []):
        if isinstance(item, dict) and item.get("instanceName") == device_id:
            result = dict(item.get("jsonObject") or {})
            if item.get("pointNames") is not None:
                result["pointNames"] = item["pointNames"]
            return result
    return {}


def resolve_map_point(reference, field, workspace=""):
    if isinstance(reference, dict):
        point = dict(reference)
    elif isinstance(reference, str) and reference:
        try:
            point = Map.getSiteDataByName(reference, workspace=workspace) if workspace else None
        except TypeError:
            point = Map.getSiteDataByName(reference)
        if not point:
            point = Map.getSiteDataByName(reference)
        if not point:
            header = getattr(getattr(Map, "data", None), "header", None)
            map_name = getattr(header, "mapName", "")
            raise ValueError("{} {} is missing from map {}".format(
                field, reference, map_name or "message"
            ))
        point = dict(point)
    else:
        raise ValueError("{} point name or coordinates are required".format(field))
    if not all(key in point for key in ("x", "y")):
        raise ValueError("{} must contain x and y".format(field))
    if "theta" not in point:
        point["theta"] = math.radians(float(point.get("dir", 0.0) or 0.0))
    return point
