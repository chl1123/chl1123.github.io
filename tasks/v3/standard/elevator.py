import json
import math
import os
import time
from functools import partial

from syspy import Loc, Map, Module, ModuleBase, Navigation, NavStatus, RobotParam, ScriptStatus, ScriptParam, Trace
from syspy.lib.action_task import ActionBase, ActionStatus, ActionTask
from syspy.script_data import ScriptData
from syspy.utils.param_server import BindType, ParamType

from standard.goBezier import GoBezierWorld as _BaseGoBezierWorld
from standard.goArc import GoArcWorld
from third import (
    ElevatorCarPosition,
    ElevatorPhase,
    ElevatorRideContext,
    EntryMotionPhase,
    create_protocol,
    enum_value,
    load_workspace_topology,
    map_device_data,
    resolve_map_point,
)
from third.elevator_protocol.base import ProtocolRejected, ProtocolUnavailable


script_param = ScriptParam(__file__)

_MAPS_DIR = "/opt/.data/rbk/resources/maps"
_TOPOLOGY_PATH = os.path.join(_MAPS_DIR, "workspace_topology.json")


def _protocol_script_choices(kind):
    directory = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", "third", f"{kind}_protocol"
    ))
    return sorted(
        name[:-3] for name in os.listdir(directory)
        if name.endswith(".py") and name not in ("__init__.py", "base.py")
    ) if os.path.isdir(directory) else ["yuefan"]


def _workspace_map_name(topology, workspace):
    matches = [
        str(item.get("map", ""))
        for item in topology.get("workspaceList", [])
        if isinstance(item, dict) and str(item.get("workspace", "")) == workspace
        and item.get("map")
    ]
    if len(matches) != 1:
        raise ValueError(
            "workspace {} must bind exactly one map in workspace_topology.json".format(
                workspace
            )
        )
    return matches[0]


def _enabled_entries(elevator, workspace):
    entries = []
    for floor in elevator.get("floorList", []):
        if not isinstance(floor, dict) or floor.get("isEnabled", True) is False:
            continue
        for entry in floor.get("entryList", []):
            if (not isinstance(entry, dict)
                    or entry.get("isEnabled", True) is False
                    or str(entry.get("workspace", "")) != workspace):
                continue
            entries.append((floor, entry))
    return entries


def _select_entry(elevator, workspace, station, station_field, role,
                  allow_single_fallback=False):
    candidates = _enabled_entries(elevator, workspace)
    if station:
        matches = [
            item for item in candidates
            if str(item[1].get(station_field, "")) == station
        ]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ValueError(
                "{} Entry is ambiguous for workspace {} and station {}".format(
                    role, workspace, station
                )
            )
        if not allow_single_fallback:
            raise ValueError(
                "{} Entry is missing for workspace {} and station {}".format(
                    role, workspace, station
                )
            )
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise ValueError(
            "{} Entry is missing for workspace {}".format(role, workspace)
        )
    raise ValueError(
        "{} Entry is ambiguous for workspace {}; station is required".format(
            role, workspace
        )
    )


def _load_map_point(map_name, point_name):
    map_path = os.path.join(_MAPS_DIR, map_name, "0.smap")
    try:
        with open(map_path, encoding="utf-8") as stream:
            map_data = json.load(stream)
    except (OSError, TypeError, ValueError) as error:
        raise ValueError("failed to load map {}: {}".format(map_name, error))
    if not isinstance(map_data, dict):
        raise ValueError("map {} root must be an object".format(map_name))
    points = map_data.get("advancedPointList", [])
    if not isinstance(points, list):
        raise ValueError("map {} advancedPointList must be an array".format(map_name))
    coordinates = []
    for point in points:
        pos = point.get("pos", {}) if isinstance(point, dict) else {}
        try:
            coordinates.extend((abs(float(pos["x"])), abs(float(pos["y"]))))
        except (KeyError, TypeError, ValueError):
            continue
    scale = 0.001 if coordinates and max(coordinates) >= 1000.0 else 1.0
    matches = [
        point for point in points
        if isinstance(point, dict)
        and point_name in (point.get("instanceName"), point.get("pointName"))
    ]
    if len(matches) != 1:
        raise ValueError(
            "point {} must exist exactly once in map {}".format(point_name, map_name)
        )
    point = matches[0]
    pos = point.get("pos", {})
    try:
        return {
            "x": float(pos["x"]) * scale,
            "y": float(pos["y"]) * scale,
            "dir": float(point["dir"]),
        }
    except (KeyError, TypeError, ValueError):
        raise ValueError(
            "point {} in map {} must contain numeric x, y and dir".format(
                point_name, map_name
            )
        )


def _resolve_ride_context(args):
    topology = load_workspace_topology(_TOPOLOGY_PATH)
    device_id = str(args["deviceId"])
    elevators = [
        elevator for elevator in topology.get("elevatorList", [])
        if isinstance(elevator, dict)
        and elevator.get("isEnabled", True) is not False
        and str(elevator.get("instanceName", "")) == device_id
    ]
    if len(elevators) != 1:
        raise ValueError(
            "enabled elevator {} must exist exactly once in workspace_topology.json".format(
                device_id
            )
        )
    elevator = elevators[0]
    source_workspace = str(Map.getCurrentWorkspace() or "")
    if not source_workspace:
        raise ValueError("current map must bind exactly one workspace")
    current_station = str(NavStatus.getCurrentStation() or "")
    source_floor, source_entry = _select_entry(
        elevator, source_workspace, current_station, "callPoint", "source",
        allow_single_fallback=True,
    )
    target_workspace = str(args["targetWorkspace"])
    requested_target = str(args.get("targetStation", "") or "")
    target_floor, target_entry = _select_entry(
        elevator, target_workspace, requested_target, "exitPoint", "target"
    )

    source_call = str(source_entry.get("callPoint", "") or "")
    source_guide = source_entry.get("entryPoint")
    source_switch = str(source_entry.get("switchPoint", "") or "")
    target_switch = str(target_entry.get("switchPoint", "") or "")
    target_exit = str(target_entry.get("exitPoint", "") or "")
    if not source_call:
        raise ValueError("source Entry must configure callPoint")
    if not source_switch:
        raise ValueError("source Entry must configure switchPoint")
    if not target_switch:
        raise ValueError("target Entry must configure switchPoint")
    if not target_exit:
        raise ValueError("target Entry must configure exitPoint for elevator exit")

    target_map = _workspace_map_name(topology, target_workspace)
    target_switch_pose = _load_map_point(target_map, target_switch)
    protocol_site = map_device_data(device_id, source_workspace)
    if not protocol_site.get("jsonObject") and elevator.get("jsonObject"):
        # Keep topology JSON usable during the map-message transition.
        protocol_site = {"jsonObject": dict(elevator.get("jsonObject") or {})}
    context = ElevatorRideContext(
        source_workspace=source_workspace,
        source_station=source_call,
        source_switch_point=source_switch,
        source_floor=int(source_floor["floorNumber"]),
        target_workspace=target_workspace,
        target_station=target_exit,
        target_floor=int(target_floor["floorNumber"]),
        target_map=target_map,
        target_switch_point=target_switch,
        target_switch_pose={
            "x": target_switch_pose["x"],
            "y": target_switch_pose["y"],
        },
        target_switch_dir=float(target_switch_pose["dir"]),
        source_guide_point=source_guide,
        protocol_site=(protocol_site if protocol_site.get("jsonObject") else None),
    ).as_args()
    Trace.log({
        "event": "elevatorContextResolved",
        "deviceId": device_id,
        "currentStation": current_station,
        **context,
    }, name="elevator")
    return context


class GoBezierWorld(_BaseGoBezierWorld):
    """Elevator-local Bezier path with optional geometry-based tangent.

    The shared implementation uses the target angle for both the final pose
    and the curve control point. Elevator entry/exit points may have an angle
    that is only meaningful after reaching the point, so keep that angle for
    MF's final pose while deriving the curve tangent from actual path geometry.
    """

    def __init__(self, *args, use_geometry_path=False,
                 avoid_initial_backoff=False, curve_start_heading=None,
                 curve_end_heading=None, **kwargs):
        self._use_geometry_path = bool(use_geometry_path)
        self._avoid_initial_backoff = bool(avoid_initial_backoff)
        self._curve_start_heading = curve_start_heading
        self._curve_end_heading = curve_end_heading
        super().__init__(*args, **kwargs)

    def get_path(self):
        if not self._use_geometry_path:
            return super().get_path()
        # GoBezierWorld places min_ahead_dist along target theta. In geometry
        # mode use the approach direction instead, so the guide point remains
        # before the target rather than beyond it.
        original_target = list(self.target_world)
        pose = Loc.getPose()
        approach_heading = math.atan2(
            float(original_target[1]) - float(pose["y"]),
            float(original_target[0]) - float(pose["x"]),
        )
        self.target_world[2] = approach_heading + math.pi
        original_adjust = self.adjust_dist_for_curvature_limit
        original_limit = self.curvature_limit
        if self._avoid_initial_backoff:
            # The guide/backoff motion must not move the robot away from its
            # safe observed pose just to satisfy the curvature threshold.
            self.adjust_dist_for_curvature_limit = 0.0
            self.curvature_limit = max(original_limit, 30.0)
        try:
            return super().get_path()
        finally:
            self.adjust_dist_for_curvature_limit = original_adjust
            self.curvature_limit = original_limit
            self.target_world = original_target
            if self.end_position_world is not None:
                self.end_position_world[2] = original_target[2]

    def compute_bezier_controls_dir(self, p0, p3, alpha=0.3):
        if not self._use_geometry_path:
            return super().compute_bezier_controls_dir(p0, p3, alpha)
        path_heading = math.atan2(p3[1] - p0[1], p3[0] - p0[0])
        # These headings describe the spatial curve, not chassis orientation.
        # P1 points away from P0 while P2 points back from P3, regardless of
        # whether the robot traverses the curve forwards or backwards.
        start_heading = (
            path_heading if self._curve_start_heading is None
            else float(self._curve_start_heading)
        )
        end_heading = (
            path_heading + math.pi if self._curve_end_heading is None
            else float(self._curve_end_heading)
        )
        geometry_start = [p0[0], p0[1], start_heading]
        geometry_target = [p3[0], p3[1], end_heading]
        return super().compute_bezier_controls_dir(geometry_start, geometry_target, alpha)


class GoRecordedPathWorld(ActionBase):
    """Return from the current pose over an already travelled local path."""

    def __init__(self, navigation, max_speed=0.2, path_dist_accuracy=0.05):
        super().__init__(self.__class__.__name__)
        self.source = navigation
        self.max_speed = float(max_speed)
        self.path_dist_accuracy = float(path_dist_accuracy)
        self.is_backwards = not bool(getattr(navigation, "is_backwards", False))
        self.target_world = None
        self.path_started = False

    def reset(self):
        super().reset()
        Navigation.resetPath()
        xs = list(getattr(self.source, "xs", ()) or ())
        ys = list(getattr(self.source, "ys", ()) or ())
        pose = Loc.getPose() or {}
        if len(xs) < 2 or len(xs) != len(ys):
            self.fail_reason = "local path is unavailable for return"
            self.action_status = ActionStatus.FAILED
            return
        try:
            current_x, current_y = float(pose["x"]), float(pose["y"])
            current_yaw = math.radians(float(pose["yaw"]))
        except (KeyError, TypeError, ValueError) as error:
            self.fail_reason = "invalid return pose: {}".format(error)
            self.action_status = ActionStatus.FAILED
            return
        nearest = min(
            range(len(xs)),
            key=lambda index: math.hypot(xs[index] - current_x, ys[index] - current_y),
        )
        return_xs = [current_x] + list(reversed(xs[:nearest + 1]))
        return_ys = [current_y] + list(reversed(ys[:nearest + 1]))
        self.target_world = [return_xs[-1], return_ys[-1], current_yaw]
        Navigation.setPathReachAngle(math.pi)
        Navigation.setPathReachDist(self.path_dist_accuracy)
        Navigation.setPathBackMode(self.is_backwards)
        Navigation.setPathMaxSpeed(self.max_speed)
        Navigation.setPathOnWorld(return_xs, return_ys, current_yaw)
        Navigation.goPathParam({})
        self.path_started = True
        Trace.log({
            "event": "recordedPathReturnStarted",
            "backwards": self.is_backwards,
            "sourcePoints": len(xs),
            "nearestIndex": nearest,
            "returnPoints": len(return_xs),
            "target": self.target_world[:2],
        }, name="elevator.entry")

    def run(self, _ctx=None):
        if self.action_status != ActionStatus.RUNNING:
            return self.action_status
        if Navigation.isPathReached():
            self.action_status = ActionStatus.FINISHED
        return self.action_status

    def cancel(self):
        Navigation.resetPath()
        self.path_started = False
        super().cancel()

    def suspend(self):
        if self.action_status == ActionStatus.RUNNING and self.path_started:
            Navigation.stopRobotNow()
        super().suspend()

    def resume(self):
        if self.action_status == ActionStatus.SUSPENDED and self.path_started:
            Navigation.goPathParam({})
        super().resume()


class GoStraightPathWorld(ActionBase):
    """Drive directly from the current pose to a world position."""

    def __init__(self, target_world, is_backwards=False, max_speed=0.2,
                 path_dist_accuracy=0.05):
        super().__init__(self.__class__.__name__)
        self.target_world = list(target_world[:3])
        self.is_backwards = bool(is_backwards)
        self.max_speed = float(max_speed)
        self.path_dist_accuracy = float(path_dist_accuracy)
        self.path_started = False

    def reset(self):
        super().reset()
        Navigation.resetPath()
        self.path_started = False
        pose = Loc.getPose() or {}
        try:
            x0, y0 = float(pose["x"]), float(pose["y"])
            yaw = math.radians(float(pose["yaw"]))
            xt, yt = float(self.target_world[0]), float(self.target_world[1])
        except (KeyError, TypeError, ValueError) as error:
            self.fail_reason = "invalid straight path pose: {}".format(error)
            self.action_status = ActionStatus.FAILED
            return
        if math.hypot(xt - x0, yt - y0) <= self.path_dist_accuracy:
            self.target_world = [xt, yt, yaw]
            self.action_status = ActionStatus.FINISHED
            return
        self.target_world = [xt, yt, yaw]
        Navigation.setPathReachAngle(math.pi)
        Navigation.setPathReachDist(self.path_dist_accuracy)
        Navigation.setPathBackMode(self.is_backwards)
        Navigation.setPathMaxSpeed(self.max_speed)
        Navigation.setPathOnWorld([x0, xt], [y0, yt], yaw)
        Navigation.goPathParam({})
        self.path_started = True
        Trace.log({
            "event": "straightPathStarted",
            "target": [xt, yt],
            "backwards": self.is_backwards,
        }, name="elevator.entry")

    def run(self, _ctx=None):
        if self.action_status != ActionStatus.RUNNING:
            return self.action_status
        if Navigation.isPathReached():
            self.action_status = ActionStatus.FINISHED
            Navigation.resetPath()
        return self.action_status

    def cancel(self):
        Navigation.resetPath()
        self.path_started = False
        super().cancel()

    def suspend(self):
        if self.action_status == ActionStatus.RUNNING and self.path_started:
            Navigation.stopRobotNow()
        super().suspend()

    def resume(self):
        if self.action_status == ActionStatus.SUSPENDED and self.path_started:
            Navigation.goPathParam({})
        super().resume()


def _deg_to_rad_or_none(value):
    if value is None:
        return None
    return math.radians(float(value))


def _normalize_motion_status(status):
    if status == ActionStatus.INIT:
        return ActionStatus.RUNNING
    return status


def _get_nav_defaults(keys):
    """Read the navigation defaults needed by the local rotation action."""
    has_goods = bool(Navigation.hasGoods())
    state_key = "load" if has_goods else "unload"
    path_map = {key: [f"basic.{state_key}.{key}"] for key in keys}
    if has_goods and "maxSpeed" in path_map:
        path_map["maxSpeed"].append("basic.load.loadMaxSpeed")
    if "maxRot" in path_map:
        path_map["maxRot"].append("basic.load.loadMaxRot")
    params = {}
    for key, paths in path_map.items():
        for path in paths:
            value = RobotParam.getConfig("navigation", path, default=None)
            if value is None:
                continue
            params[key] = (
                _deg_to_rad_or_none(value)
                if key == "maxRot" else float(value)
            )
            break
    return params


class ElevatorStatePublisher:
    """Best-effort ScriptData publisher; diagnostics must not stop the safety loop."""

    def __init__(self, args):
        self.args = args
        self.entry_attempt = 1
        self.phase = ElevatorPhase.VALIDATING
        self.lease = None
        self.last_error = None

    def publish(self, phase=None):
        if phase is not None:
            self.phase = ElevatorPhase(phase)
        lease = self.lease
        latest = getattr(lease, "latest", None)
        payload = {
            "phase": self.phase.value,
            "deviceId": str(self.args.get("deviceId", "")),
            "sourceWorkspace": str(self.args.get("sourceWorkspace", "")),
            "sourceStation": str(self.args.get("sourceStation", "")),
            "targetWorkspace": str(self.args.get("targetWorkspace", "")),
            "entryAttempt": int(self.entry_attempt),
            "controlState": getattr(latest, "control_state", "UNKNOWN"),
            "carPosition": getattr(
                getattr(lease, "car_position", None), "value", "UNKNOWN"
            ),
        }
        if self.args.get("targetStation"):
            payload["targetStation"] = str(self.args["targetStation"])
        try:
            ScriptData.set("elevatorState", payload)
            self.last_error = None
            return True
        except Exception as error:
            self.last_error = error
            try:
                Trace.log({
                    "event": "elevatorStatePublishFailed",
                    "error": str(error),
                }, name="elevator.err")
            except Exception:
                pass
            return False

    def set_attempt(self, attempt):
        self.entry_attempt = int(attempt)
        self.publish()


class ConfigParams:
    aheadDist = 0.5
    minAheadDist = 0.2
    maxSpeed = 0.2
    maxCurve = 2.0
    reachDist = 0.05
    reachAngle = 5.0
    minObsStopDist = 0.05
    minObsDecDist = 0.1
    entry_obstacle_start_ratio = 0.3
    map_switch_stable_time = 2.0
    map_switch_min_confidence = 0.65
    switch_map_before_arrival = True
    protocol_active_time = 30
    elevator_arrival_timeout = 120.0
    elevator_status_poll_interval = 2.0
    entry_blocked_timeout = 3.0
    entry_retry_motion_timeout = 30.0
    max_entry_attempts = 3
    exit_blocked_timeout = 30.0
    exit_retry_interval = 3.0
    entry_guide_distance = 0.5
    release_control_on_pause = False
    entryForward = True
    exitForward = None
    guidePathMode = "arc"

    @classmethod
    def init(cls):
        builder = script_param.builderConfig()
        with builder.GROUPS():
            with builder.GROUP(key="bezier", name="Bezier", desc="Bezier path parameters"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    cls._float_param(builder, "aheadDist", "Ahead Dist", 0.5, 0.0, 1.5, "m")
                    cls._float_param(builder, "minAheadDist", "Min Ahead Dist", 0.2, 0.0, 2.0, "m")
                    cls._float_param(builder, "maxSpeed", "Maximum speed", 0.2, 0.01, 1.0, "m/s")
                    cls._float_param(builder, "maxCurve", "Max Curve", 2.0, 0.1, 30.0)
                    cls._float_param(builder, "reachDist", "Reach distance", 0.05, 0.001, 0.5, "m")
                    cls._float_param(builder, "reachAngle", "Reach angle", 5.0, 0.1, 30.0, "deg")
            with builder.GROUP(key="motion", name="Elevator motion", desc="Entry and exit motion direction"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    with builder.CHILD(key="entryForward", name="Entry direction", desc="Drive forward or backward into the elevator"):
                        builder.TYPE(ParamType.COMBO_BOX)
                        builder.DEFAULTVALUE("forward")
                        with builder.CHILDREN():
                            with builder.CHILD(key="forward", name="Forward entry", desc="Drive forward into the elevator"):
                                builder.TYPE(ParamType.ARRAY)
                            with builder.CHILD(key="backward", name="Backward entry", desc="Drive backward into the elevator"):
                                builder.TYPE(ParamType.ARRAY)
                    with builder.CHILD(key="exitForward", name="Exit direction", desc="Exit forward, backward, or automatically resolve direction"):
                        builder.TYPE(ParamType.COMBO_BOX)
                        builder.DEFAULTVALUE("auto")
                        with builder.CHILDREN():
                            with builder.CHILD(key="auto", name="Auto", desc="Resolve direction from the switch point"):
                                builder.TYPE(ParamType.ARRAY)
                            with builder.CHILD(key="forward", name="Forward exit", desc="Drive forward out of the elevator"):
                                builder.TYPE(ParamType.ARRAY)
                            with builder.CHILD(key="backward", name="Backward exit", desc="Drive backward out of the elevator"):
                                builder.TYPE(ParamType.ARRAY)
                    with builder.CHILD(key="guidePathMode", name="Guide path mode", desc="Path from callPoint to the entry guide point"):
                        builder.TYPE(ParamType.COMBO_BOX)
                        builder.DEFAULTVALUE("arc")
                        with builder.CHILDREN():
                            with builder.CHILD(key="bezier", name="Bezier", desc="Follow a Bezier path"):
                                builder.TYPE(ParamType.ARRAY)
                            with builder.CHILD(key="arc", name="Arc", desc="Follow one circular arc"):
                                builder.TYPE(ParamType.ARRAY)
            with builder.GROUP(key="mapSwitch", name="Map switch", desc="Map switch parameters"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    cls._float_param(builder, "mapSwitchStableTime", "Localization stable time", 2.0, 0.0, 10.0, "s")
                    cls._float_param(builder, "mapSwitchMinConfidence", "Minimum localization confidence", 0.65, 0.0, 1.0)
                    with builder.CHILD(
                            key="switchMapBeforeArrival",
                            name="Switch map before arrival",
                            desc="Switch map while the elevator is travelling"):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(True)
            with builder.GROUP(key="obstacleStop", name="Obstacle stop", desc="Elevator obstacle distances"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    cls._float_param(builder, "minObsStopDist", "Minimum obstacle stop distance", 0.05, 0.0, 2.0, "m")
                    cls._float_param(builder, "minObsDecDist", "Minimum obstacle deceleration distance", 0.1, 0.0, 2.0, "m")
                    cls._float_param(builder, "entryObstacleStartRatio", "Entry obstacle start ratio", 0.3, 0.0, 1.0)
            with builder.GROUP(key="elevatorState", name="Elevator state", desc="Elevator state parameters"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    cls._float_param(builder, "elevatorArrivalTimeout", "Arrival timeout", 120.0, 1.0, 600.0, "s") # todo: 改为呼梯时间
                    cls._float_param(builder, "entryBlockedTimeout", "Entry blocked timeout", 3.0, 0.1, 3600.0, "s")
                    cls._float_param(builder, "entryRetryMotionTimeout", "Entry retry motion timeout", 30.0, 0.1, 3600.0, "s")
                    cls._int_param(builder, "maxEntryAttempts", "Maximum entry attempts", 3, 1, 100)
                    cls._float_param(builder, "exitBlockedTimeout", "Exit blocked timeout", 30.0, 0.1, 3600.0, "s")
                    cls._float_param(builder, "exitRetryInterval", "Exit retry interval", 3.0, 0.0, 3600.0, "s")
                    cls._float_param(builder, "entryGuideDistance", "Entry guide distance", 0.5, 0.05, 10.0, "m")
                    with builder.CHILD(
                            key="releaseControlOnPause",
                            name="Release control on pause",
                            desc="Release elevator control when the task is paused"):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(False)
            builder.save(merge=True)
        cls.load_config()

    @staticmethod
    def _float_param(builder, key, name, default, minimum, maximum, unit=None):
        with builder.CHILD(key=key, name=name, desc=name):
            builder.TYPE(ParamType.FLOAT)
            builder.DEFAULTVALUE(default, min_value=minimum, max_value=maximum)
            builder.SINGLESTEP(0.01)
            if unit:
                builder.UNIT(unit)

    @staticmethod
    def _int_param(builder, key, name, default, minimum, maximum):
        with builder.CHILD(key=key, name=name, desc=name):
            builder.TYPE(ParamType.INT)
            builder.DEFAULTVALUE(default, min_value=minimum, max_value=maximum)
            builder.SINGLESTEP(1)

    @staticmethod
    def _entry_forward(value, default):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            value = value.lower()
            if value in ("forward", "on", "true"):
                return True
            if value in ("backward", "off", "false"):
                return False
        return default

    @staticmethod
    def _exit_forward(value, default):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            value = value.lower()
            if value in ("forward", "on", "true"):
                return True
            if value in ("backward", "off", "false"):
                return False
            if value == "auto":
                return None
        return default

    @classmethod
    def load_config(cls):
        config = script_param.loadConfig()
        cls.aheadDist = float(config.get("aheadDist", cls.aheadDist))
        cls.minAheadDist = float(config.get("minAheadDist", cls.minAheadDist))
        cls.maxSpeed = float(config.get("maxSpeed", cls.maxSpeed))
        cls.maxCurve = float(config.get("maxCurve", cls.maxCurve))
        cls.reachDist = float(config.get("reachDist", cls.reachDist))
        cls.reachAngle = float(config.get("reachAngle", cls.reachAngle))
        cls.minObsStopDist = float(config.get("minObsStopDist", cls.minObsStopDist))
        cls.minObsDecDist = float(config.get("minObsDecDist", cls.minObsDecDist))
        cls.entry_obstacle_start_ratio = float(
            config.get("entryObstacleStartRatio", cls.entry_obstacle_start_ratio)
        )
        cls.map_switch_stable_time = float(config.get("mapSwitchStableTime", cls.map_switch_stable_time))
        cls.map_switch_min_confidence = float(
            config.get("mapSwitchMinConfidence", cls.map_switch_min_confidence)
        )
        cls.switch_map_before_arrival = cls._bool_value(
            config.get("switchMapBeforeArrival"), cls.switch_map_before_arrival
        )
        cls.entryForward = cls._entry_forward(config.get("entryForward"), cls.entryForward)
        cls.exitForward = cls._exit_forward(config.get("exitForward"), cls.exitForward)
        cls.guidePathMode = str(config.get("guidePathMode", cls.guidePathMode)).lower()
        cls.elevator_arrival_timeout = float(config.get("elevatorArrivalTimeout", cls.elevator_arrival_timeout))
        cls.entry_blocked_timeout = float(config.get("entryBlockedTimeout", cls.entry_blocked_timeout))
        cls.entry_retry_motion_timeout = float(config.get("entryRetryMotionTimeout", cls.entry_retry_motion_timeout))
        raw_attempts = config.get("maxEntryAttempts", cls.max_entry_attempts)
        attempts = float(raw_attempts)
        if not attempts.is_integer():
            raise ValueError("maxEntryAttempts must be an integer")
        cls.max_entry_attempts = int(attempts)
        cls.exit_blocked_timeout = float(config.get("exitBlockedTimeout", cls.exit_blocked_timeout))
        cls.exit_retry_interval = float(config.get("exitRetryInterval", cls.exit_retry_interval))
        cls.entry_guide_distance = float(config.get("entryGuideDistance", cls.entry_guide_distance))
        cls.release_control_on_pause = cls._bool_value(
            config.get("releaseControlOnPause"), cls.release_control_on_pause,
            "releaseControlOnPause",
        )
        cls._validate_ranges()

    @classmethod
    def _validate_ranges(cls):
        ranges = (
            ("minObsStopDist", cls.minObsStopDist, 0.0, 2.0),
            ("minObsDecDist", cls.minObsDecDist, 0.0, 2.0),
            ("entryObstacleStartRatio", cls.entry_obstacle_start_ratio, 0.0, 1.0),
            ("mapSwitchStableTime", cls.map_switch_stable_time, 0.0, 10.0),
            ("mapSwitchMinConfidence", cls.map_switch_min_confidence, 0.0, 1.0),
            ("entryBlockedTimeout", cls.entry_blocked_timeout, 0.1, 3600.0),
            ("entryRetryMotionTimeout", cls.entry_retry_motion_timeout, 0.1, 3600.0),
            ("exitBlockedTimeout", cls.exit_blocked_timeout, 0.1, 3600.0),
            ("exitRetryInterval", cls.exit_retry_interval, 0.0, 3600.0),
            ("entryGuideDistance", cls.entry_guide_distance, 0.05, 10.0),
        )
        for name, value, minimum, maximum in ranges:
            if not minimum <= value <= maximum:
                raise ValueError(
                    "{} must be in range {}..{}".format(name, minimum, maximum)
                )
        if not 1 <= cls.max_entry_attempts <= 100:
            raise ValueError("maxEntryAttempts must be in range 1..100")
        if cls.guidePathMode not in ("bezier", "arc"):
            raise ValueError("guidePathMode must be bezier or arc")

    @staticmethod
    def _bool_value(value, default, name="switchMapBeforeArrival"):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            value = value.strip().lower()
            if value in ("true", "on", "1"):
                return True
            if value in ("false", "off", "0"):
                return False
        if value is None:
            return default
        raise ValueError("{} must be a boolean".format(name))


ConfigParams.init()


class InputParams:
    """Formal MF RunScript inputs."""

    builder = script_param.builderInput()
    with builder.GROUPS():
        with builder.GROUP(key="operation", name="Operation", desc="Elevator operation"):
            builder.TYPE(ParamType.COMBO_BOX)
            builder.REQUIRED(True)
            with builder.CHILDREN():
                with builder.CHILD(key="ride", name="Ride", desc="Ride one elevator"):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        with builder.CHILD(key="deviceId", name="Elevator device", desc="MF selected elevator"):
                            builder.TYPE(ParamType.STRING)
                            builder.REQUIRED(True)
                        with builder.CHILD(key="targetWorkspace", name="Target workspace", desc="Target workspace"):
                            builder.TYPE(ParamType.STRING)
                            builder.REQUIRED(True)
                        with builder.CHILD(key="targetStation", name="Target station", desc="Optional target Entry station"):
                            builder.TYPE(ParamType.STRING)
        with builder.GROUP(key="communicationProtocol", name="Communication protocol", desc="Elevator protocol binding"):
            builder.TYPE(ParamType.COMBO_BOX)
            with builder.CHILDREN():
                for protocol_name in _protocol_script_choices("elevator"):
                    with builder.CHILD(key=protocol_name, name=protocol_name, desc="Elevator {} protocol".format(protocol_name)):
                        builder.TYPE(ParamType.ARRAY)
                        with builder.CHILDREN():
                            with builder.CHILD(key="name", name="Protocol script", desc="Protocol implementation script"):
                                builder.TYPE(ParamType.BIND_TYPE)
                                builder.BINDTYPE(
                                    BindType.script("tasks:third:elevator_protocol")
                                )
                                builder.DEFAULTVALUE(
                                    "tasks/third/elevator_protocol/{}.py".format(protocol_name)
                                )
                            with builder.CHILD(key="config", name="Config", desc="Elevator protocol instance configuration"):
                                builder.TYPE(ParamType.ARRAY)
                                builder.REQUIRED(False)
                                builder.DEFAULTVALUE({})
    builder.save()


script_param.addAction(
    action_name="Ride Elevator",
    policy={},
    args={
        "operation": "ride",
        "operation.ride.deviceId": "EL1",
        "operation.ride.targetWorkspace": "",
        "operation.ride.targetStation": "",
    },
    config={},
    stage=3,
)
script_param.saveAction()


class ProtocolAction(ActionBase):
    def __init__(self, operation, callback, on_error=None, on_cancel=None,
                 error_code=None, on_started=None, on_finished=None, callback_args=()):
        super().__init__(operation)
        self._callback = callback
        self._on_error = on_error
        self._on_cancel = on_cancel
        self._explicit_error_code = error_code
        self._on_started = on_started
        self._on_finished = on_finished
        self._callback_args = tuple(callback_args)
        self.cleanup_on_failure = on_cancel is not None
        self.result = None

    def reset(self):
        super().reset()
        if self._on_started is not None:
            self._on_started()

    def run(self, _ctx=None):
        try:
            self.result = self._callback(*self._callback_args)
            if self._on_finished is not None:
                self._on_finished(self.result)
            self.action_status = ActionStatus.FINISHED
        except Exception as error:
            self.fail_reason = str(error)
            if self._explicit_error_code:
                self.error_code = self._explicit_error_code
            elif isinstance(error, ProtocolUnavailable):
                self.error_code = "ElevatorProtocolUnavailable"
            elif isinstance(error, ProtocolRejected):
                self.error_code = "ElevatorProtocolRejected"
            else:
                self.error_code = "ElevatorInternalError"
            if self._on_error is not None:
                try:
                    self._on_error()
                except Exception as cleanup_error:
                    Trace.log({
                        "event": "protocolCleanupFailed",
                        "operation": self.action_type,
                        "error": str(cleanup_error),
                    }, name="elevator.err")
            self.action_status = ActionStatus.FAILED
        return self.action_status

    def cancel(self):
        if self._on_cancel is not None:
            try:
                self._on_cancel()
            except Exception as cleanup_error:
                Trace.log({
                    "event": "protocolCleanupFailed",
                    "operation": self.action_type,
                    "error": str(cleanup_error),
                }, name="elevator.err")
        super().cancel()

    def result_description(self):
        if self.result is None:
            return {}
        return {key: value for key, value in vars(self.result).items()
                if isinstance(value, (bool, int, float, str))}


class ElevatorLease:
    """持有电梯控制权期间共享协议状态，并保证安全释放与幂等。"""

    def __init__(self, protocol, floor, active_time):
        self.protocol = protocol
        self.floor = int(floor)
        self.active_time = int(active_time)
        self.latest = None
        self.status_generation = 0
        self.acquired = False
        self.car_position = ElevatorCarPosition.UNKNOWN
        self._released = False
        self._release_result = None

    def mark_entering(self):
        self.car_position = ElevatorCarPosition.ENTERING

    def mark_inside(self):
        self.car_position = ElevatorCarPosition.INSIDE

    def mark_exiting(self):
        self.car_position = ElevatorCarPosition.EXITING

    def mark_outside(self):
        self.car_position = ElevatorCarPosition.OUTSIDE

    def call(self, floor):
        was_acquired = self.acquired
        result = self.protocol.call(int(floor), self.active_time)
        self.floor = int(floor)
        self.latest = result
        self.status_generation += 1
        self.acquired = True
        self._released = False
        self._release_result = None
        if not was_acquired:
            # 首次呼梯对应来源 callPoint；之后 select 目标层不得覆盖车内状态。
            self.car_position = ElevatorCarPosition.OUTSIDE
        return result

    def keep_alive(self):
        if not self.acquired:
            return self.latest
        result = self.protocol.keep_alive(self.floor, self.active_time)
        self.latest = result
        self.status_generation += 1
        return result

    def release(self):
        if self._released:
            return self._release_result
        if not self.acquired:
            return None
        if self.car_position != ElevatorCarPosition.OUTSIDE:
            Trace.log({
                "event": "elevatorSafetyHolding",
                "carPosition": self.car_position.value,
                "reason": "release forbidden while robot is in elevator",
            }, name="elevator.err")
            raise RuntimeError(
                "cannot release elevator while car position is {}".format(
                    self.car_position.value
                )
            )
        result = self.protocol.release(self.active_time)
        self.latest = result
        self._release_result = result
        self._released = True
        self.acquired = False
        return result

    def release_if_safe(self):
        """动作清理时延迟释放；模块终态收口负责强制释放。"""
        if not self.acquired or self.car_position == ElevatorCarPosition.OUTSIDE:
            return self.release()
        Trace.log({
            "event": "elevatorSafetyHolding",
            "carPosition": self.car_position.value,
            "reason": "defer release until robot exits elevator",
        }, name="elevator.err")
        return None

    def release_unconditionally(self, reason):
        """终态失败或取消时立即释放控制权，不进入安全保持。"""
        if not self.acquired or self._released:
            return self._release_result
        if self.car_position != ElevatorCarPosition.OUTSIDE:
            Trace.log({
                "event": "elevatorForcedRelease",
                "carPosition": self.car_position.value,
                "reason": str(reason),
            }, name="elevator.err")
            self.car_position = ElevatorCarPosition.OUTSIDE
        return self.release()


class ElevatorKeepAliveAction(ActionBase):
    """后台维持梯控控制权，覆盖入梯、切图、等梯和出梯阶段。"""

    def __init__(self, lease, poll_interval=None, on_state=None):
        super().__init__(self.__class__.__name__)
        self.background = True
        self.lease = lease
        # Polling is an internal lease-maintenance setting, not a task input.
        self._poll_interval = float(
            ConfigParams.elevator_status_poll_interval
            if poll_interval is None else poll_interval
        )
        self._on_state = on_state
        self._next_poll_at = None
        self._stop_requested = False

    def reset(self):
        super().reset()
        self._next_poll_at = time.monotonic()
        self._stop_requested = False

    def request_stop(self):
        self._stop_requested = True

    def _release_safely(self):
        try:
            self.lease.release_if_safe()
        except Exception as error:
            Trace.log({
                "event": "protocolCleanupFailed",
                "operation": "KeepAlive",
                "error": str(error),
            }, name="elevator.err")

    def run(self, _ctx=None):
        if self._stop_requested:
            self.action_status = ActionStatus.FINISHED
            return self.action_status
        now = time.monotonic()
        if now < self._next_poll_at:
            return self.action_status
        try:
            self.lease.keep_alive()
        except Exception as error:
            self._release_safely()
            self.fail_reason = str(error)
            self.error_code = (
                "ElevatorProtocolRejected"
                if isinstance(error, ProtocolRejected)
                else "ElevatorProtocolUnavailable"
            )
            self.action_status = ActionStatus.FAILED
            return self.action_status
        if self._on_state is not None:
            self._on_state()
        self._next_poll_at = now + self._poll_interval
        return self.action_status

    def cancel(self):
        self._release_safely()
        super().cancel()


class ElevatorSafetyHolding:
    """Deprecated: 保留供后续独立安全会话复用，当前业务入口已停用。"""

    def __init__(self, lease, poll_interval=1.0, publisher=None):
        self.lease = lease
        self.poll_interval = float(poll_interval)
        self._next_poll_at = time.monotonic()
        self.resolved = False
        self.publisher = publisher
        if self.publisher is not None:
            self.publisher.publish(ElevatorPhase.SAFETY_HOLDING)

    def step(self):
        if self.resolved:
            return True
        if self.lease.car_position == ElevatorCarPosition.OUTSIDE:
            try:
                self.lease.release()
                self.resolved = True
                Trace.log({"event": "safetyHoldingResolved",
                           "carPosition": self.lease.car_position.value},
                          name="elevator.safety")
                return True
            except Exception as error:
                Trace.log({"event": "safetyHoldingReleaseFailed",
                           "error": str(error)}, name="elevator.err")
                return False

        now = time.monotonic()
        if now < self._next_poll_at:
            return False
        try:
            self.lease.keep_alive()
            if self.publisher is not None:
                self.publisher.publish(ElevatorPhase.SAFETY_HOLDING)
            Trace.log({"event": "safetyHoldingKeepAlive",
                       "carPosition": self.lease.car_position.value},
                      name="elevator.safety")
        except Exception as error:
            # 安全保持期间通信失败也不能退化为 release；下一周期继续尝试。
            Trace.log({"event": "safetyHoldingKeepAliveFailed",
                       "error": str(error),
                       "carPosition": self.lease.car_position.value},
                      name="elevator.err")
        self._next_poll_at = now + self.poll_interval
        return False


class SwitchMapAction(ActionBase):
    def __init__(self, map_name, switch_point, switch_pose=None,
                 stable_time=2.0, min_confidence=0.65, on_started=None,
                 source_switch_dir=None, target_switch_dir=None):
        super().__init__(self.__class__.__name__)
        self.map_name = str(map_name)
        self.switch_point = str(switch_point)
        self.switch_pose = switch_pose
        self.stable_time = float(stable_time)
        self.min_confidence = float(min_confidence)
        self.source_switch_dir = source_switch_dir
        self.target_switch_dir = target_switch_dir
        self._switch_complete = False
        self._stable_since = None
        self._switch_heading = None
        self._confidence_wait_logged = False
        self._switch_call_count = 0
        self._switch_request_logged = False
        self._last_switch_result = None
        self._on_started = on_started

    def reset(self):
        super().reset()
        self._switch_complete = False
        self._stable_since = None
        self._switch_heading = None
        self._confidence_wait_logged = False
        self._switch_call_count = 0
        self._switch_request_logged = False
        self._last_switch_result = None
        if self.switch_pose:
            pose = Loc.getPose() or {}
            heading = pose.get("yaw")
            source_switch_dir = self.source_switch_dir
            target_switch_dir = self.target_switch_dir
            if target_switch_dir is None:
                target_switch_dir = self.switch_pose.get("dir")
            try:
                if (heading is not None and source_switch_dir is not None
                        and target_switch_dir is not None):
                    # Preserve the physical heading relative to the source
                    # SM while expressing it in the target map.
                    heading = float(target_switch_dir) + _normalize_heading(
                        float(heading) - float(source_switch_dir)
                    )
            except (TypeError, ValueError):
                # Older callers may not provide both SM directions.
                heading = pose.get("yaw")
            if heading is None:
                heading = self.switch_pose.get("angle")
            if heading is not None:
                self._switch_heading = _normalize_heading(heading)
            Trace.log({
                "event": "switchMapHeadingCaptured",
                "switchPoint": self.switch_point,
                "sourceSwitchDir": source_switch_dir,
                "targetSwitchDir": target_switch_dir,
                "currentYaw": pose.get("yaw"),
                "switchHeading": self._switch_heading,
            }, name="elevator.map")
        if self._on_started is not None:
            self._on_started()

    def run(self, _ctx=None):
        if not self._switch_complete:
            if self.switch_pose and self._switch_heading is not None:
                mode = "targetPose"
                switch_args = [
                    self.map_name,
                    "",
                    float(self.switch_pose["x"]),
                    float(self.switch_pose["y"]),
                    self._switch_heading,
                ]
            else:
                mode = "switchPoint"
                switch_args = [self.map_name, self.switch_point]
            if not self._switch_request_logged:
                Trace.log({
                    "event": "switchMapRequested",
                    "mode": mode,
                    "args": switch_args,
                }, name="elevator.map")
                self._switch_request_logged = True
            self._switch_call_count += 1
            try:
                result = Map.switchMap(*switch_args)
            except Exception as error:
                Trace.log({
                    "event": "switchMapCallFailed",
                    "mode": mode,
                    "args": switch_args,
                    "callCount": self._switch_call_count,
                    "error": str(error),
                }, name="elevator.map")
                raise
            if result != self._last_switch_result:
                Trace.log({
                    "event": "switchMapReturned",
                    "mode": mode,
                    "args": switch_args,
                    "callCount": self._switch_call_count,
                    "result": result,
                }, name="elevator.map")
                self._last_switch_result = result
            if result == 0:
                self._switch_complete = True
            elif result == 1:
                return self.action_status
            else:
                self.fail_reason = "Map.switchMap returned {}".format(result)
                self.error_code = "ElevatorMapSwitchFailed"
                self.action_status = ActionStatus.FAILED
                return self.action_status

        loc_state = int(Loc.getLocState())
        if loc_state == 4:
            try:
                confidence = Loc.getConfidence()
            except Exception as error:
                confidence = None
                if not self._confidence_wait_logged:
                    Trace.log({
                        "event": "switchMapConfidenceReadFailed",
                        "error": str(error),
                    }, name="elevator.map")
                    self._confidence_wait_logged = True
            if confidence is None or float(confidence) < self.min_confidence:
                self._stable_since = None
                if not self._confidence_wait_logged:
                    Trace.log({
                        "event": "switchMapLocalizationLowConfidence",
                        "map": self.map_name,
                        "switchPoint": self.switch_point,
                        "confidence": confidence,
                        "minConfidence": self.min_confidence,
                    }, name="elevator.map")
                    self._confidence_wait_logged = True
                return self.action_status
            self._confidence_wait_logged = False
            now = time.monotonic()
            if self._stable_since is None:
                self._stable_since = now
            if now - self._stable_since >= self.stable_time:
                Trace.log({
                    "event": "switchMapLocalized",
                    "map": self.map_name,
                    "switchPoint": self.switch_point,
                    "locState": loc_state,
                    "confidence": float(confidence),
                    "minConfidence": self.min_confidence,
                }, name="elevator.map")
                self.action_status = ActionStatus.FINISHED
        elif loc_state == 2:
            self.fail_reason = "failed to load map {}".format(self.map_name)
            self.error_code = "ElevatorMapSwitchFailed"
            self.action_status = ActionStatus.FAILED
            Trace.log({
                "event": "switchMapLocalizationFailed",
                "map": self.map_name,
                "switchPoint": self.switch_point,
                "locState": loc_state,
                "reason": self.fail_reason,
            }, name="elevator.map")
        elif loc_state == 5:
            self.fail_reason = "localization is invalid after switching to {}".format(
                self.map_name
            )
            self.error_code = "ElevatorMapSwitchFailed"
            self.action_status = ActionStatus.FAILED
            Trace.log({
                "event": "switchMapLocalizationFailed",
                "map": self.map_name,
                "switchPoint": self.switch_point,
                "locState": loc_state,
                "reason": self.fail_reason,
            }, name="elevator.map")
        else:
            self._stable_since = None
        return self.action_status


class WaitTargetElevatorAction(ActionBase):
    def __init__(self, protocol, target_floor, active_time=None,
                 timeout=120.0, poll_interval=None, lease=None, on_started=None):
        super().__init__(self.__class__.__name__)
        self.protocol = protocol
        self.target_floor = int(target_floor)
        self.timeout = float(timeout)
        self._poll_interval = float(
            ConfigParams.elevator_status_poll_interval
            if poll_interval is None else poll_interval
        )
        self.result = None
        self._started_at = None
        self._next_poll_at = None
        self._last_state = None
        self.lease = lease
        self._minimum_lease_generation = None
        self._minimum_lease_result = None
        self._on_started = on_started

    def reset(self):
        super().reset()
        now = time.monotonic()
        self._started_at = now
        self._next_poll_at = now
        self._last_state = None
        generation = (
            getattr(self.lease, "status_generation", None)
            if self.lease is not None else None
        )
        self._minimum_lease_generation = (
            generation if isinstance(generation, (int, float)) else None
        )
        self._minimum_lease_result = (
            getattr(self.lease, "latest", None) if self.lease is not None else None
        )
        if self._on_started is not None:
            self._on_started()

    def run(self, _ctx=None):
        now = time.monotonic()
        if now - self._started_at > self.timeout:
            self.fail_reason = "elevator did not arrive at floor {} with door open".format(
                self.target_floor
            )
            self.error_code = "ElevatorStateTimeout"
            self.action_status = ActionStatus.FAILED
            return self.action_status
        if self.lease is not None:
            # keep-alive 后台 Action 已经完成协议轮询，这里只消费最新状态。
            current_generation = getattr(self.lease, "status_generation", None)
            if (self._minimum_lease_generation is not None
                    and isinstance(current_generation, (int, float))
                    and current_generation <= self._minimum_lease_generation
                    and getattr(self.lease, "latest", None)
                    is self._minimum_lease_result):
                return self.action_status
            self.result = self.lease.latest
            if self.result is None:
                return self.action_status
        else:
            if now < self._next_poll_at:
                return self.action_status
            try:
                self.result = self.protocol.keep_alive(
                    self.target_floor, ConfigParams.protocol_active_time
                )
            except Exception as error:
                self.fail_reason = str(error)
                if isinstance(error, ProtocolUnavailable):
                    self.error_code = "ElevatorProtocolUnavailable"
                elif isinstance(error, ProtocolRejected):
                    self.error_code = "ElevatorProtocolRejected"
                else:
                    self.error_code = "ElevatorStateTimeout"
                self.action_status = ActionStatus.FAILED
                return self.action_status
            self._next_poll_at = now + self._poll_interval

        state = (self.result.floor, self.result.move_state, self.result.door_state)
        if state != self._last_state:
            Trace.log({
                "event": "elevatorStateChanged",
                "targetFloor": self.target_floor,
                "floor": self.result.floor,
                "moveState": self.result.move_state,
                "doorState": self.result.door_state,
            }, name="elevator.state")
            self._last_state = state
        if self.protocol.is_target_ready(self.result, self.target_floor):
            self.action_status = ActionStatus.FINISHED
        return self.action_status

    def result_description(self):
        if self.result is None:
            return {}
        return {
            "floor": self.result.floor,
            "move_state": self.result.move_state,
            "door_state": self.result.door_state,
        }


class WaitSourceElevatorAction(WaitTargetElevatorAction):
    """Wait until the source-floor car is stopped, open, and owned by this task."""

    def __init__(self, protocol, source_floor, active_time=None,
                 timeout=120.0, poll_interval=None, lease=None, on_started=None):
        super().__init__(protocol, source_floor, active_time, timeout,
                         poll_interval, lease, on_started)
        self.action_type = self.__class__.__name__

    def run(self, _ctx=None):
        status = super().run(_ctx)
        if status == ActionStatus.FINISHED and getattr(self.result, "control_state", None) != "OWNED_BY_SELF":
            self.action_status = ActionStatus.RUNNING
        return self.action_status


def _normalize_heading(angle):
    """Normalize a world heading in degrees to [-180, 180)."""
    return (float(angle) + 180.0) % 360.0 - 180.0


class ElevatorEntryHeadingAction(ActionBase):
    """Align the chassis with the elevator door before entering."""

    def __init__(self, call_point_dir, forward=True, tolerance=None):
        super().__init__(self.__class__.__name__)
        self.call_point_dir = (
            None if call_point_dir is None else float(call_point_dir)
        )
        self.forward = bool(forward)
        self.tolerance = ConfigParams.reachAngle if tolerance is None else float(tolerance)
        self.target_heading = None

    def args_summary(self):
        return {
            "call_point_dir": self.call_point_dir,
            "forward": self.forward,
            "tolerance": self.tolerance,
        }

    def reset(self):
        super().reset()
        if self.call_point_dir is None:
            self.action_status = ActionStatus.FINISHED
            Trace.log({
                "event": "entryHeadingDelegatedToNavigation",
            }, name="elevator.entry")
            return
        Navigation.resetOdoMove()
        self.target_heading = _normalize_heading(
            self.call_point_dir + (0.0 if self.forward else 180.0)
        )
        try:
            pose = Loc.getPose() or {}
            current_heading = _normalize_heading(pose["yaw"])
            error = _normalize_heading(self.target_heading - current_heading)
            if abs(error) <= self.tolerance:
                self.action_status = ActionStatus.FINISHED
                Trace.log({
                    "event": "entryHeadingAlreadyAligned",
                    "current": current_heading,
                    "target": self.target_heading,
                    "error": error,
                }, name="elevator.entry")
                return

            params = _get_nav_defaults(["maxRot"])
            params["moveAngle"] = abs(math.radians(error))
            # runOdoMove uses the sign of speedW for rotation direction.
            params["speedW"] = (
                1.0 if error > 0.0 else -1.0
            ) * float(params.get("maxRot", 0.5))
            params["locMode"] = 0
            params["actionName"] = "ElevatorEntryHeading"
            self._params = params
            Trace.log({
                "event": "entryHeadingStarted",
                "current": current_heading,
                "target": self.target_heading,
                "error": error,
                "params": params,
            }, name="elevator.entry")
        except Exception as error:
            self.fail_reason = str(error)
            self.error_code = "ElevatorLocalMoveFailed"
            self.action_status = ActionStatus.FAILED

    def run(self, _ctx=None):
        if self.action_status != ActionStatus.RUNNING:
            return self.action_status
        try:
            self.action_status = _normalize_motion_status(
                Navigation.runOdoMove(self._params)
            )
        except Exception as error:
            self.fail_reason = str(error)
            self.error_code = "ElevatorLocalMoveFailed"
            self.action_status = ActionStatus.FAILED
        if self.action_status == ActionStatus.FAILED and not self.error_code:
            self.error_code = "ElevatorLocalMoveFailed"
        if self.action_status in (ActionStatus.FINISHED, ActionStatus.FAILED):
            Navigation.resetOdoMove()
        return self.action_status

    def cancel(self):
        Navigation.resetOdoMove()
        super().cancel()


class ElevatorBezierAction(ActionBase):
    _POLICY_PROGRESS_STEP = 0.05
    _POLICY_LOG_PROGRESS_STEP = 0.25
    _POLICY_FIELDS = (
        ("navigation.obstacleStop.obsStopLoad.loadObsStopDist",
         "obstacleStop.obsStopLoad.loadObsStopDist", "stop"),
        ("navigation.obstacleStop.obsStopLoad.loadObsDecDist",
         "obstacleStop.obsStopLoad.loadObsDecDist", "deceleration"),
        ("navigation.obstacleStop.obsStopUnload.obsStopDist",
         "obstacleStop.obsStopUnload.obsStopDist", "stop"),
        ("navigation.obstacleStop.obsStopUnload.obsDecDist",
         "obstacleStop.obsStopUnload.obsDecDist", "deceleration"),
    )

    def __init__(self, target, is_exit=False, on_started_callback=None,
                 on_finished_callback=None, switch_dir=None, backwards=None,
                 geometry_path=None, avoid_initial_backoff=False,
                 curve_start_heading=None, curve_end_heading=None,
                 policy_start_ratio=1.0, position_only=False, workspace="",
                 path_mode="bezier", recorded_navigation=None):
        super().__init__(self.__class__.__name__)
        self.target = target
        self.is_exit = is_exit
        self.navigation = None
        self.on_started_callback = on_started_callback
        self.on_finished_callback = on_finished_callback
        self.switch_dir = switch_dir
        self.workspace = workspace
        self.backwards = backwards
        self.geometry_path = self.is_exit if geometry_path is None else bool(geometry_path)
        self.avoid_initial_backoff = bool(avoid_initial_backoff)
        self.curve_start_heading = curve_start_heading
        self.curve_end_heading = curve_end_heading
        self.policy_start_ratio = max(0.0, min(1.0, float(policy_start_ratio)))
        self.position_only = bool(position_only)
        self.path_mode = str(path_mode)
        self.recorded_navigation = recorded_navigation
        self._path_angle_accuracy = ConfigParams.reachAngle
        self._finish_notified = False
        self._policy_initialized = False
        self._policy_active = False
        self._policy_defaults = {}
        self._policy_values = {}
        self._policy_start_distance = 0.0
        self._last_policy_progress = -1.0
        self._last_policy_log_progress = -1.0

    def args_summary(self):
        summary = {
            "target": self.target,
            "is_exit": self.is_exit,
        }
        if self.switch_dir is not None:
            summary["switch_dir"] = self.switch_dir
        if self.backwards is not None:
            summary["backwards"] = self.backwards
        if self.position_only:
            summary["position_only"] = True
        if self.path_mode != "bezier":
            summary["path_mode"] = self.path_mode
        return summary

    def reset(self):
        super().reset()
        self._finish_notified = False
        self._policy_initialized = False
        self._policy_active = False
        self._policy_defaults = {}
        self._policy_values = {}
        self._policy_start_distance = 0.0
        self._last_policy_progress = -1.0
        self._last_policy_log_progress = -1.0
        try:
            self.target = resolve_map_point(
                self.target, "exitPoint", self.workspace
            )
            switch_dir = self.switch_dir
            if isinstance(switch_dir, str):
                switch_dir = resolve_map_point(
                    switch_dir, "target switchPoint", self.workspace
                ).get("dir", 0.0)
        except (TypeError, ValueError) as error:
            self.fail_reason = str(error)
            self.error_code = "ElevatorConfigError"
            self.action_status = ActionStatus.FAILED
            return
        if self.backwards is not None:
            is_backwards = bool(self.backwards)
        elif not self.is_exit:
            is_backwards = not ConfigParams.entryForward
        elif ConfigParams.exitForward is not None:
            is_backwards = not ConfigParams.exitForward
        elif switch_dir is not None:
            pose = Loc.getPose() or {}
            current_heading = pose.get("yaw")
            if current_heading is None:
                is_backwards = bool(self.target.get("backwards", False))
                current_heading = None
            else:
                current_heading = float(current_heading)
                forward_error = abs(_normalize_heading(
                    current_heading - float(switch_dir)
                ))
                backward_error = abs(_normalize_heading(
                    current_heading + 180.0 - float(switch_dir)
                ))
                is_backwards = backward_error < forward_error
                Trace.log({
                    "event": "exitDirectionResolved",
                    "mode": "auto",
                    "currentHeading": current_heading,
                    "switchDir": float(switch_dir),
                    "forwardError": forward_error,
                    "backwardError": backward_error,
                    "backwards": is_backwards,
                }, name="elevator.exit")
        else:
            is_backwards = bool(self.target.get("backwards", False))
        # Entry guide/SM and elevator exit are position targets. Their map
        # angles must not trigger a final in-place rotation in the car or hall.
        self._path_angle_accuracy = (
            180.0 if self.position_only or self.is_exit else ConfigParams.reachAngle
        )
        target_world = [
            float(self.target["x"]), float(self.target["y"]),
            float(self.target["theta"]),
        ]
        if self.path_mode == "recorded":
            self.navigation = GoRecordedPathWorld(
                self.recorded_navigation,
                max_speed=ConfigParams.maxSpeed,
                path_dist_accuracy=ConfigParams.reachDist,
            )
        elif self.path_mode == "line":
            self.navigation = GoStraightPathWorld(
                target_world,
                is_backwards=is_backwards,
                max_speed=ConfigParams.maxSpeed,
                path_dist_accuracy=ConfigParams.reachDist,
            )
        elif self.path_mode == "arc":
            self.navigation = GoArcWorld(
                target_world,
                is_backwards=is_backwards,
                max_speed=ConfigParams.maxSpeed,
                path_dist_accuracy=ConfigParams.reachDist,
                path_angle_accuracy=self._path_angle_accuracy,
            )
        else:
            self.navigation = GoBezierWorld(
                target_world,
                adjust_dist_for_curvature_limit=ConfigParams.aheadDist,
                min_ahead_dist=ConfigParams.minAheadDist,
                is_backwards=is_backwards,
                use_geometry_path=self.geometry_path,
                avoid_initial_backoff=self.avoid_initial_backoff,
                curve_start_heading=self.curve_start_heading,
                curve_end_heading=self.curve_end_heading,
                max_speed=ConfigParams.maxSpeed,
                curvature_limit=ConfigParams.maxCurve,
                path_dist_accuracy=ConfigParams.reachDist,
                path_angle_accuracy=self._path_angle_accuracy,
            )
        self.navigation.reset()
        if self.on_started_callback is not None:
            self.on_started_callback()
        Trace.log({"event": "started", "target": self.navigation.target_world,
                   "isExit": self.is_exit, "backwards": is_backwards,
                   "positionOnly": self.position_only or self.is_exit,
                   "pathMode": self.path_mode},
                  name="elevator.bezier")

    def _distance_to_target(self):
        pose = Loc.getPose()
        return math.hypot(
            float(self.target["x"]) - float(pose["x"]),
            float(self.target["y"]) - float(pose["y"]),
        )

    def _initialize_policy(self):
        for policy_key, config_key, _kind in self._POLICY_FIELDS:
            self._policy_defaults[policy_key] = float(
                RobotParam.getConfig("navigation", config_key)
            )
        self._policy_start_distance = self._distance_to_target()
        self._update_policy(force=True, remaining=self._policy_start_distance)
        self._policy_initialized = True

    def _update_policy(self, force=False, remaining=None):
        if self._policy_start_distance <= 1e-6:
            progress = 1.0
        else:
            if remaining is None:
                remaining = self._distance_to_target()
            progress = max(0.0, min(1.0, 1.0 - remaining / self._policy_start_distance))
        progress = max(progress, self._last_policy_progress)
        if (not force and progress < 1.0
                and progress - self._last_policy_progress < self._POLICY_PROGRESS_STEP):
            return

        policy = {}
        for policy_key, _config_key, kind in self._POLICY_FIELDS:
            default = self._policy_defaults[policy_key]
            configured = (
                ConfigParams.minObsStopDist
                if kind == "stop" else ConfigParams.minObsDecDist
            )
            target = min(default, configured)
            start = max(target, default * self.policy_start_ratio)
            policy[policy_key] = round(
                target + (start - target) * (1.0 - progress), 4
            )
        policy_name = (
            "elevator_exit_obstacle_distance"
            if self.is_exit else "elevator_entry_obstacle_distance"
        )
        policy.update({"navigation.freeBypass": "off"})
        policy_changed = policy != self._policy_values
        if policy_changed:
            Navigation.appendCustomPolicy(policy_name, policy)
            self._policy_active = True
            self._policy_values = dict(policy)
        self._last_policy_progress = progress
        if (policy_changed and (
                force or self._last_policy_log_progress < 0.0
                or progress >= 1.0
                or progress - self._last_policy_log_progress
                >= self._POLICY_LOG_PROGRESS_STEP)):
            Trace.log({
                "event": "obstaclePolicyApplied",
                "policyName": policy_name,
                "isExit": self.is_exit,
                "progress": round(progress, 4),
                "remaining": None if remaining is None else round(float(remaining), 4),
                "startDistance": round(self._policy_start_distance, 4),
                "defaults": dict(self._policy_defaults),
                "values": dict(policy),
            }, name="elevator.policy")
            self._last_policy_log_progress = progress

    def _clear_policy(self):
        if self._policy_active:
            Navigation.clearPolicy()
            self._policy_active = False

    def run(self, _ctx=None):
        try:
            if not self._policy_initialized:
                self._initialize_policy()
            else:
                self._update_policy()
            self.action_status = self.navigation.run()
        except Exception as error:
            self.fail_reason = str(error)
            self.error_code = "ElevatorInternalError"
            self.action_status = ActionStatus.FAILED
        if self.action_status == ActionStatus.FAILED and not self.error_code:
            self.error_code = "ElevatorLocalMoveFailed"
        if self.action_status in (ActionStatus.FINISHED, ActionStatus.FAILED):
            try:
                self._clear_policy()
            except Exception as error:
                self.fail_reason = str(error)
                self.error_code = "ElevatorInternalError"
                self.action_status = ActionStatus.FAILED
        if self.action_status == ActionStatus.FINISHED:
            Navigation.resetPath()
            pose = Loc.getPose() or {}
            distance = None
            heading_error = None
            if "x" in pose and "y" in pose:
                distance = math.hypot(
                    float(self.target["x"]) - float(pose["x"]),
                    float(self.target["y"]) - float(pose["y"]),
                )
            if "yaw" in pose and "theta" in self.target:
                heading_error = _normalize_heading(
                    float(pose["yaw"]) - math.degrees(float(self.target["theta"]))
                )
            Trace.log({
                "event": "finished",
                "isExit": self.is_exit,
                "target": [self.target["x"], self.target["y"], self.target.get("theta")],
                "actualPose": pose,
                "distance": distance,
                "headingError": heading_error,
                "reachDist": ConfigParams.reachDist,
                "reachAngle": self._path_angle_accuracy,
                "positionOnly": self.position_only,
                "policy": dict(self._policy_values),
            }, name="elevator.bezier")
            if self.on_finished_callback is not None and not self._finish_notified:
                self._finish_notified = True
                self.on_finished_callback()
        return self.action_status

    def cancel(self):
        try:
            self._clear_policy()
        except Exception as error:
            Trace.log({"event": "navigationPolicyClearFailed", "error": str(error)},
                      name="elevator.err")
        if self.navigation is not None:
            self.navigation.cancel()
        else:
            Navigation.resetPath()
        super().cancel()

    def suspend(self):
        if self.action_status == ActionStatus.RUNNING and self.navigation is not None:
            self.navigation.suspend()
        super().suspend()

    def resume(self):
        if self.action_status == ActionStatus.SUSPENDED and self.navigation is not None:
            self.navigation.resume()
        super().resume()


class ElevatorEntryAction(ActionBase):
    """Navigate through an entry guide point with obstacle retry handling."""

    _MOTION_PHASES = frozenset((
        EntryMotionPhase.GUIDE,
        EntryMotionPhase.ENTERING,
        EntryMotionPhase.BACKING_OFF_GUIDE_RETRY,
        EntryMotionPhase.BACKING_OFF_GUIDE_FINAL,
        EntryMotionPhase.BACKING_OFF_CALL_POINT_FIRST,
        EntryMotionPhase.BACKING_OFF_CALL_POINT_FINAL,
    ))
    _GUIDE_BACKOFF_PHASES = frozenset((
        EntryMotionPhase.BACKING_OFF_GUIDE_RETRY,
        EntryMotionPhase.BACKING_OFF_GUIDE_FINAL,
    ))
    _CALL_POINT_BACKOFF_PHASES = frozenset((
        EntryMotionPhase.BACKING_OFF_CALL_POINT_FIRST,
        EntryMotionPhase.BACKING_OFF_CALL_POINT_FINAL,
    ))

    def __init__(self, entry, call_point, lease, protocol, source_floor, active_time=None,
                 on_entering=None, on_inside=None, guide_point=None):
        super().__init__(self.__class__.__name__)
        self.entry = dict(entry)
        self.call_point = dict(call_point)
        self.lease = lease
        self.protocol = protocol
        self.source_floor = int(source_floor)
        self.on_entering = on_entering
        self.on_inside = on_inside
        self.guide_point = dict(guide_point) if isinstance(guide_point, dict) else None
        self._motion = None
        self._phase = None
        self._blocked_since = None
        self._backoff_block_logged = False
        self._backoff_waiting_for_clear = False
        self._retry_started = None
        self._attempt = 1
        self._wait_source = None
        self._arrival_deadline = None

    def args_summary(self):
        summary = {
            "entry": self.entry,
            "call_point": self.call_point,
        }
        if self.guide_point is not None:
            summary["entryPoint"] = self.guide_point
        else:
            summary["entryGuideDistance"] = ConfigParams.entry_guide_distance
        return summary

    def _guide_point(self):
        if self.guide_point is not None:
            return dict(self.guide_point)
        ex, ey = float(self.entry["x"]), float(self.entry["y"])
        heading = self.entry.get("theta")
        if heading is None:
            heading = math.radians(float(self.entry.get("dir", 0.0)))
        if "theta" not in self.entry and "dir" not in self.entry:
            heading = math.atan2(
                float(self.call_point["y"]) - ey,
                float(self.call_point["x"]) - ex,
            )
        guide = dict(self.entry)
        guide["x"] = ex + ConfigParams.entry_guide_distance * math.cos(heading)
        guide["y"] = ey + ConfigParams.entry_guide_distance * math.sin(heading)
        return guide

    def _call_point_target(self):
        target = dict(self.call_point)
        if "theta" not in target:
            target["theta"] = math.radians(float(target.get("dir", 0.0)))
        return target

    @staticmethod
    def _path_target(target, backwards):
        result = dict(target)
        pose = Loc.getPose() or {}
        if "x" in pose and "y" in pose:
            dx = float(result["x"]) - float(pose["x"])
            dy = float(result["y"]) - float(pose["y"])
            if math.hypot(dx, dy) > 1e-6:
                heading = math.atan2(dy, dx) + (math.pi if backwards else 0.0)
                result["theta"] = (heading + math.pi) % (2.0 * math.pi) - math.pi
        return result

    @staticmethod
    def _has_recorded_path(motion):
        navigation = getattr(motion, "navigation", None)
        xs = getattr(navigation, "xs", None)
        ys = getattr(navigation, "ys", None)
        return bool(xs and ys and len(xs) == len(ys) and len(xs) >= 2)

    @staticmethod
    def _target_errors(pose, target):
        distance = None
        heading_error = None
        try:
            distance = math.hypot(
                float(target["x"]) - float(pose["x"]),
                float(target["y"]) - float(pose["y"]),
            )
            if "yaw" in pose and "theta" in target:
                heading_error = abs(_normalize_heading(
                    float(pose["yaw"]) - math.degrees(float(target["theta"]))
                ))
        except (KeyError, TypeError, ValueError):
            return None, None
        return distance, heading_error

    def _start_motion(self, target, phase, backwards=None):
        phase = EntryMotionPhase(phase)
        self._phase = phase
        self._backoff_waiting_for_clear = False
        if backwards is None:
            backwards = not ConfigParams.entryForward
        motion_target = self._path_target(target, backwards)
        curve_start_heading = None
        curve_end_heading = None
        if phase == EntryMotionPhase.GUIDE and self.call_point.get("dir") is not None:
            curve_start_heading = math.radians(float(self.call_point["dir"]))
            next_heading = math.atan2(
                float(self.entry["y"]) - float(motion_target["y"]),
                float(self.entry["x"]) - float(motion_target["x"]),
            )
            motion_target["theta"] = next_heading + (math.pi if backwards else 0.0)
            motion_target["theta"] = (
                motion_target["theta"] + math.pi
            ) % (2.0 * math.pi) - math.pi
            # P2 is placed from P3 towards the previous portion of the curve.
            curve_end_heading = next_heading + math.pi
        if phase == EntryMotionPhase.GUIDE:
            policy_start_ratio = 0.5
            path_mode = ConfigParams.guidePathMode
        elif phase == EntryMotionPhase.ENTERING:
            # Keep the compact elevator approach conservative: start at the
            # configured fraction of normal obstacle distances and taper to
            # the configured minimum as the robot approaches SM.
            policy_start_ratio = ConfigParams.entry_obstacle_start_ratio
            path_mode = "line"
        elif phase in self._GUIDE_BACKOFF_PHASES:
            policy_start_ratio = 0.0
            path_mode = "line"
        elif phase == EntryMotionPhase.BACKING_OFF_CALL_POINT_FIRST:
            policy_start_ratio = 0.5
            path_mode = "line"
        elif phase == EntryMotionPhase.BACKING_OFF_CALL_POINT_FINAL:
            policy_start_ratio = 0.0
            path_mode = "line"
        else:
            policy_start_ratio = 1.0
            path_mode = "bezier"
        recorded_navigation = None
        self._motion = ElevatorBezierAction(
            motion_target, is_exit=False, backwards=backwards, geometry_path=True,
            avoid_initial_backoff=True,
            curve_start_heading=curve_start_heading,
            curve_end_heading=curve_end_heading,
            policy_start_ratio=policy_start_ratio,
            # The guide-to-switchPoint segment is a physical door path.  Its
            # retry/backoff motions must preserve the current chassis heading
            # instead of appending an in-place rotation at the target.
            position_only=(phase in (
                EntryMotionPhase.GUIDE,
                EntryMotionPhase.ENTERING,
            ) or phase in self._GUIDE_BACKOFF_PHASES
                or phase in self._CALL_POINT_BACKOFF_PHASES),
            path_mode=path_mode,
            recorded_navigation=recorded_navigation,
        )
        self._motion.reset()
        Trace.log({
            "event": "entryMotionStarted",
            "phase": enum_value(phase),
            "attempt": self._attempt,
            "target": [motion_target["x"], motion_target["y"]],
            "targetHeading": math.degrees(float(motion_target["theta"])),
            "backwards": backwards,
            "positionOnly": (phase in (
                EntryMotionPhase.GUIDE,
                EntryMotionPhase.ENTERING,
            ) or phase in self._GUIDE_BACKOFF_PHASES
                or phase in self._CALL_POINT_BACKOFF_PHASES),
            "pathMode": path_mode,
        }, name="elevator.entry")

    def reset(self):
        super().reset()
        now = time.monotonic()
        self._blocked_since = None
        self._backoff_block_logged = False
        self._backoff_waiting_for_clear = False
        self._retry_started = None
        self._attempt = 1
        self._wait_source = None
        self._arrival_deadline = now + ConfigParams.elevator_arrival_timeout
        guide = self._guide_point()
        guide_distance = math.hypot(
            float(guide["x"]) - float(self.entry["x"]),
            float(guide["y"]) - float(self.entry["y"]),
        )
        Trace.log({
            "event": "entryGuidePoint",
            "point": [guide["x"], guide["y"]],
            "distance": guide_distance,
            "source": "entity" if self.guide_point is not None else "virtual",
            "pointName": guide.get("pointName") or guide.get("instanceName"),
        }, name="elevator.entry")
        self._start_motion(guide, EntryMotionPhase.GUIDE)

    def _on_guide_to_entry_path(self, pose):
        try:
            guide = self._guide_point()
            sx, sy = float(guide["x"]), float(guide["y"])
            ex, ey = float(self.entry["x"]), float(self.entry["y"])
            px, py = float(pose["x"]), float(pose["y"])
        except (KeyError, TypeError, ValueError):
            return False
        dx, dy = ex - sx, ey - sy
        length_sq = dx * dx + dy * dy
        if length_sq <= 1e-9:
            return math.hypot(px - sx, py - sy) <= ConfigParams.reachDist
        ratio = ((px - sx) * dx + (py - sy) * dy) / length_sq
        if ratio < 0.0 or ratio > 1.0:
            return False
        nearest_x = sx + ratio * dx
        nearest_y = sy + ratio * dy
        return math.hypot(px - nearest_x, py - nearest_y) <= max(
            ConfigParams.reachDist, 0.25
        )

    def _arrival_timed_out(self, now):
        return (
            self._arrival_deadline is not None
            and now >= self._arrival_deadline
        )

    def _start_source_retry(self, now):
        try:
            self.lease.call(self.source_floor)
        except Exception as error:
            self.fail_reason = str(error)
            if isinstance(error, ProtocolUnavailable):
                self.error_code = "ElevatorProtocolUnavailable"
            elif isinstance(error, ProtocolRejected):
                self.error_code = "ElevatorProtocolRejected"
            else:
                self.error_code = "ElevatorInternalError"
            self.action_status = ActionStatus.FAILED
            return self.action_status
        timeout = ConfigParams.elevator_arrival_timeout
        if self._arrival_deadline is not None:
            timeout = max(0.1, self._arrival_deadline - now)
        self._wait_source = WaitSourceElevatorAction(
            self.protocol,
            self.source_floor,
            timeout=timeout,
            lease=self.lease,
        )
        self._wait_source.reset()
        self._phase = EntryMotionPhase.WAITING_SOURCE
        Trace.log({
            "event": "entryRetrySourceCalled",
            "attempt": self._attempt + 1,
            "remainingArrivalTimeout": round(timeout, 3),
        }, name="elevator.entry")
        return self.action_status

    def _start_final_call_point_backoff(self):
        self.lease.mark_outside()
        try:
            self.lease.release()
        except Exception as error:
            self.fail_reason = str(error)
            self.error_code = "ElevatorReleaseFailed"
            self.action_status = ActionStatus.FAILED
            Trace.log({
                "event": "entryRetryReleaseFailed",
                "attempt": self._attempt,
                "error": str(error),
            }, name="elevator.err")
            return False
        Trace.log({
            "event": "entryRetryReleasedBeforeCallPointBackoff",
            "attempt": self._attempt,
        }, name="elevator.entry")
        self._start_motion(
            self._call_point_target(),
            phase=EntryMotionPhase.BACKING_OFF_CALL_POINT_FINAL,
            backwards=ConfigParams.entryForward,
        )
        return True

    def _blocked(self):
        try:
            return bool(NavStatus.getBlock())
        except Exception as error:
            Trace.log({"event": "entryBlockReadFailed", "error": str(error)},
                      name="elevator.entry")
            return False

    def _handle_block(self, now):
        if not self._blocked():
            self._blocked_since = None
            self._backoff_block_logged = False
            return False
        pose = Loc.getPose() or {}
        target = getattr(self._motion, "target", {}) or {}
        distance, heading_error = self._target_errors(pose, target)
        try:
            block_device = NavStatus.getBlockDevice()
        except Exception:
            block_device = None

        # MF may keep isPathReached false while collision detection is stopping
        # at the final SM pose.  Require both configured tolerances before
        # accepting the car as inside; position-only navigation prevents an
        # additional in-place rotation while recovering from a block.
        if (self._phase == EntryMotionPhase.ENTERING and distance is not None
                and heading_error is not None
                and distance <= ConfigParams.reachDist
                and heading_error <= ConfigParams.reachAngle):
            if self._motion is not None:
                self._motion.cancel()
            self._blocked_since = None
            if self.on_inside is not None:
                self.on_inside()
            self.action_status = ActionStatus.FINISHED
            Trace.log({
                "event": "entryReachedWhileBlocked",
                "attempt": self._attempt,
                "blockDevice": block_device,
                "pose": pose,
                "target": target,
                "distance": distance,
                "headingError": heading_error,
                "reachDist": ConfigParams.reachDist,
                "reachAngle": ConfigParams.reachAngle,
                "policy": dict(getattr(self._motion, "_policy_values", {}) or {}),
            }, name="elevator.entry")
            return True

        if self._blocked_since is None:
            self._blocked_since = now
            self._backoff_block_logged = False
            Trace.log({
                "event": "entryBlocked",
                "phase": enum_value(self._phase),
                "attempt": self._attempt,
                "blockDevice": block_device,
                "pose": pose,
                "target": target,
                "distance": distance,
                "headingError": heading_error,
                "policy": dict(getattr(self._motion, "_policy_values", {}) or {}),
                "reachDist": ConfigParams.reachDist,
                "reachAngle": ConfigParams.reachAngle,
            }, name="elevator.entry")
        blocked_for = now - self._blocked_since
        if blocked_for < ConfigParams.entry_blocked_timeout:
            return True

        # A backoff is the recovery motion itself.  Do not cancel/recreate it
        # or fail the entry action merely because the short forward-block
        # confirmation window elapsed.  Keep the current path and control
        # lease while NavStatus reports a block; the arrival deadline remains
        # the only terminal bound.  Once the aggregate block clears, the
        # navigation action can continue from its current pose.
        if self._phase in self._GUIDE_BACKOFF_PHASES | self._CALL_POINT_BACKOFF_PHASES:
            if not self._backoff_block_logged:
                Trace.log({
                    "event": "entryBackoffBlockedWaiting",
                    "phase": enum_value(self._phase),
                    "attempt": self._attempt,
                    "continuousSeconds": round(blocked_for, 3),
                    "requiredSeconds": ConfigParams.entry_blocked_timeout,
                    "blockDevice": block_device,
                }, name="elevator.entry")
                self._backoff_block_logged = True
            return True

        Trace.log({
            "event": "entryBlockConfirmed",
            "phase": enum_value(self._phase),
            "attempt": self._attempt,
            "continuousSeconds": round(now - self._blocked_since, 3),
            "requiredSeconds": ConfigParams.entry_blocked_timeout,
            "blockDevice": block_device,
        }, name="elevator.entry")

        if self._on_guide_to_entry_path(pose):
            retained_phase = None
            retained_target = None
            retained_backwards = None
            if (self._phase == EntryMotionPhase.ENTERING
                    and self._attempt < ConfigParams.max_entry_attempts):
                retained_phase = EntryMotionPhase.BACKING_OFF_GUIDE_RETRY
                retained_target = self._guide_point()
                retained_backwards = ConfigParams.entryForward
            elif self._phase == EntryMotionPhase.BACKING_OFF_GUIDE_RETRY:
                if self._attempt >= ConfigParams.max_entry_attempts:
                    retained_phase = EntryMotionPhase.BACKING_OFF_GUIDE_FINAL
                    retained_target = self._guide_point()
                    retained_backwards = ConfigParams.entryForward
                else:
                    retained_phase = EntryMotionPhase.ENTERING
                    retained_target = self.entry
            elif self._phase == EntryMotionPhase.BACKING_OFF_GUIDE_FINAL:
                retained_phase = EntryMotionPhase.BACKING_OFF_GUIDE_FINAL
                retained_target = self._guide_point()
                retained_backwards = ConfigParams.entryForward
            elif self._phase in (
                    EntryMotionPhase.BACKING_OFF_CALL_POINT_FIRST,
                    EntryMotionPhase.BACKING_OFF_CALL_POINT_FINAL,
            ):
                retained_phase = self._phase
                retained_target = self._call_point_target()
                retained_backwards = ConfigParams.entryForward

            if retained_phase is not None:
                if self._motion is not None:
                    self._motion.cancel()
                self._blocked_since = None
                if retained_backwards is None:
                    self._start_motion(retained_target, retained_phase)
                else:
                    self._start_motion(
                        retained_target,
                        phase=retained_phase,
                        backwards=retained_backwards,
                    )
                Trace.log({
                    "event": "entryBlockedOnDoorPathRetained",
                    "attempt": self._attempt,
                    "blockDevice": block_device,
                    "pose": pose,
                    "nextPhase": enum_value(self._phase),
                }, name="elevator.entry")
                return True

        if self._motion is not None:
            self._motion.cancel()

        if self._phase == EntryMotionPhase.GUIDE:
            self._start_motion(
                self._call_point_target(),
                phase=EntryMotionPhase.BACKING_OFF_CALL_POINT_FIRST,
                backwards=ConfigParams.entryForward,
            )
            self._blocked_since = None
            Trace.log({
                "event": "entryBackingOffCallPoint",
                "attempt": self._attempt,
                "blockDevice": block_device,
                "pose": pose,
                "distance": distance,
                "headingError": heading_error,
            }, name="elevator.entry")
            return True

        if self._phase in self._GUIDE_BACKOFF_PHASES:
            from_phase = self._phase
            if (from_phase == EntryMotionPhase.BACKING_OFF_GUIDE_FINAL
                    or self._attempt >= ConfigParams.max_entry_attempts):
                if not self._start_final_call_point_backoff():
                    self._blocked_since = None
                    return True
            else:
                self._start_motion(
                    self._call_point_target(),
                    phase=EntryMotionPhase.BACKING_OFF_CALL_POINT_FINAL,
                    backwards=ConfigParams.entryForward,
                )
            self._blocked_since = None
            Trace.log({
                "event": "entryBackingOffCallPoint",
                "attempt": self._attempt,
                "blockDevice": block_device,
                "pose": pose,
                "distance": distance,
                "headingError": heading_error,
                "fromPhase": enum_value(from_phase),
            }, name="elevator.entry")
            return True

        if self._attempt >= ConfigParams.max_entry_attempts:
            self._start_motion(
                self._guide_point(),
                phase=EntryMotionPhase.BACKING_OFF_GUIDE_FINAL,
                backwards=ConfigParams.entryForward,
            )
            self._blocked_since = None
            Trace.log({
                "event": "entryRetryExhaustedBackingOff",
                "attempt": self._attempt,
                "blockDevice": block_device,
            }, name="elevator.entry")
            return True

        self._start_motion(
            self._guide_point(),
            phase=EntryMotionPhase.BACKING_OFF_GUIDE_RETRY,
            backwards=ConfigParams.entryForward,
        )
        Trace.log({"event": "entryBackingOffGuide", "attempt": self._attempt},
                  name="elevator.entry")
        self._blocked_since = None
        return True

    @staticmethod
    def _clear_block_status():
        try:
            NavStatus.clearBlock()
        except Exception:
            pass

    def _motion_failure_fallback(self):
        if self._phase == EntryMotionPhase.GUIDE:
            return EntryMotionPhase.BACKING_OFF_CALL_POINT_FIRST
        if self._phase == EntryMotionPhase.ENTERING:
            return (
                EntryMotionPhase.BACKING_OFF_GUIDE_FINAL
                if self._attempt >= ConfigParams.max_entry_attempts
                else EntryMotionPhase.BACKING_OFF_GUIDE_RETRY
            )
        if self._phase in self._GUIDE_BACKOFF_PHASES:
            return EntryMotionPhase.BACKING_OFF_CALL_POINT_FINAL
        return None

    def _handle_motion_failure(self):
        failed_phase = self._phase
        failed_reason = self._motion.fail_reason
        failed_error_code = self._motion.error_code
        pose = Loc.getPose() or {}
        if (failed_phase in self._GUIDE_BACKOFF_PHASES | self._CALL_POINT_BACKOFF_PHASES
                and self._blocked()):
            # A failed recovery path must not fail the elevator task while the
            # chassis is still across the doorway.  Hold the lease and wait
            # for the aggregate block flag to clear before recreating the same
            # straight backoff from the current pose.
            self._backoff_waiting_for_clear = True
            Trace.log({
                "event": "entryBackoffMotionFailedWaiting",
                "phase": enum_value(failed_phase),
                "attempt": self._attempt,
                "reason": failed_reason,
                "errorCode": failed_error_code,
            }, name="elevator.entry")
            return self.action_status
        if (failed_phase in self._MOTION_PHASES
                and self._on_guide_to_entry_path(pose)):
            if failed_phase == EntryMotionPhase.ENTERING:
                fallback_phase = (
                    EntryMotionPhase.BACKING_OFF_GUIDE_FINAL
                    if self._attempt >= ConfigParams.max_entry_attempts
                    else EntryMotionPhase.BACKING_OFF_GUIDE_RETRY
                )
                fallback_target = self._guide_point()
                fallback_backwards = ConfigParams.entryForward
            elif failed_phase == EntryMotionPhase.BACKING_OFF_GUIDE_FINAL:
                fallback_phase = EntryMotionPhase.BACKING_OFF_GUIDE_FINAL
                fallback_target = self._guide_point()
                fallback_backwards = ConfigParams.entryForward
            elif failed_phase == EntryMotionPhase.BACKING_OFF_GUIDE_RETRY:
                if self._attempt >= ConfigParams.max_entry_attempts:
                    fallback_phase = EntryMotionPhase.BACKING_OFF_GUIDE_FINAL
                    fallback_target = self._guide_point()
                    fallback_backwards = ConfigParams.entryForward
                else:
                    fallback_phase = EntryMotionPhase.ENTERING
                    fallback_target = self.entry
                    fallback_backwards = None
            elif failed_phase in self._CALL_POINT_BACKOFF_PHASES:
                fallback_phase = failed_phase
                fallback_target = self._call_point_target()
                fallback_backwards = ConfigParams.entryForward
            else:
                fallback_phase = EntryMotionPhase.ENTERING
                fallback_target = self.entry
                fallback_backwards = None
            self._start_motion(
                fallback_target,
                phase=fallback_phase,
                backwards=fallback_backwards,
            )
            Trace.log({
                "event": "entryRecoveryMotionFailedOnDoorPath",
                "attempt": self._attempt,
                "phase": enum_value(failed_phase),
                "fallbackPhase": enum_value(fallback_phase),
                "reason": failed_reason,
                "errorCode": failed_error_code,
            }, name="elevator.entry")
            return self.action_status
        fallback_phase = self._motion_failure_fallback()
        if fallback_phase is None:
            self.fail_reason = failed_reason
            self.error_code = failed_error_code or "ElevatorLocalMoveFailed"
            self.action_status = ActionStatus.FAILED
            return self.action_status
        fallback_target = (
            self._call_point_target()
            if fallback_phase in self._CALL_POINT_BACKOFF_PHASES
            else self._guide_point()
        )
        if (fallback_phase == EntryMotionPhase.BACKING_OFF_CALL_POINT_FINAL
                and (failed_phase == EntryMotionPhase.BACKING_OFF_GUIDE_FINAL
                     or self._attempt >= ConfigParams.max_entry_attempts)):
            if not self._start_final_call_point_backoff():
                return self.action_status
        else:
            self._start_motion(
                fallback_target,
                phase=fallback_phase,
                backwards=ConfigParams.entryForward,
            )
        Trace.log({
            "event": "entryRecoveryMotionFailed",
            "attempt": self._attempt,
            "phase": enum_value(failed_phase),
            "fallbackPhase": enum_value(fallback_phase),
            "reason": failed_reason,
            "errorCode": failed_error_code,
        }, name="elevator.entry")
        return self.action_status

    def _handle_motion_finished(self, now):
        if self._phase == EntryMotionPhase.GUIDE:
            if self.on_entering is not None:
                self.on_entering()
            self._start_motion(self.entry, EntryMotionPhase.ENTERING)
        elif self._phase == EntryMotionPhase.ENTERING:
            if self.on_inside is not None:
                self.on_inside()
            self.action_status = ActionStatus.FINISHED
        elif self._phase == EntryMotionPhase.BACKING_OFF_GUIDE_RETRY:
            self._blocked_since = None
            self._clear_block_status()
            if self._attempt >= ConfigParams.max_entry_attempts:
                self._start_final_call_point_backoff()
            else:
                self._attempt += 1
                self._start_motion(self.entry, EntryMotionPhase.ENTERING)
        elif self._phase == EntryMotionPhase.BACKING_OFF_GUIDE_FINAL:
            self._blocked_since = None
            self._clear_block_status()
            self._start_final_call_point_backoff()
        elif self._phase == EntryMotionPhase.BACKING_OFF_CALL_POINT_FINAL:
            self.lease.mark_outside()
            self._clear_block_status()
            return self._start_source_retry(now)
        else:
            self.lease.mark_outside()
            self._clear_block_status()
            self._phase = EntryMotionPhase.WAITING_RETRY_MOTION
            self._retry_started = now
        return self.action_status

    def run(self, ctx=None):
        if self.action_status != ActionStatus.RUNNING:
            return self.action_status
        now = time.monotonic()
        if self._arrival_timed_out(now):
            if self._motion is not None:
                self._motion.cancel()
            self.fail_reason = "elevator entry did not complete before arrival timeout"
            self.error_code = "ElevatorStateTimeout"
            self.action_status = ActionStatus.FAILED
            return self.action_status
        if self._backoff_waiting_for_clear:
            if self._blocked():
                return self.action_status
            self._backoff_waiting_for_clear = False
            self._blocked_since = None
            self._backoff_block_logged = False
            target = (
                self._call_point_target()
                if self._phase in self._CALL_POINT_BACKOFF_PHASES
                else self._guide_point()
            )
            self._start_motion(
                target,
                phase=self._phase,
                backwards=ConfigParams.entryForward,
            )
            return self.action_status
        if self._phase in self._MOTION_PHASES:
            # Advance motion before reading the block flag, which may still
            # describe the previous navigation tick.
            try:
                self._motion.run(ctx)
            except Exception as error:
                # A local navigation exception must not unwind the script
                # while the robot is on the guide-to-switchPoint door path.
                # Convert it to the same recoverable motion-failure flow used
                # for an explicit FAILED status; the arrival deadline remains
                # the only terminal bound for this recovery loop.
                self._motion.fail_reason = str(error)
                self._motion.error_code = "ElevatorLocalMoveFailed"
                self._motion.action_status = ActionStatus.FAILED
                Trace.log({
                    "event": "entryMotionException",
                    "phase": enum_value(self._phase),
                    "attempt": self._attempt,
                    "error": str(error),
                }, name="elevator.err")
            if self._motion.action_status == ActionStatus.FAILED:
                return self._handle_motion_failure()
            if self._motion.action_status == ActionStatus.FINISHED:
                return self._handle_motion_finished(now)
            self._handle_block(now)
            return self.action_status

        if self._phase == EntryMotionPhase.WAITING_RETRY_MOTION:
            if now - self._retry_started > ConfigParams.entry_retry_motion_timeout:
                return self._start_source_retry(now)
            latest = self.lease.latest
            if latest is None or int(getattr(latest, "move_state", 0)) == 0:
                return self.action_status
            return self._start_source_retry(now)

        if self._phase == EntryMotionPhase.WAITING_SOURCE:
            self._wait_source.run(ctx)
            if self._wait_source.action_status == ActionStatus.FAILED:
                self.fail_reason = self._wait_source.fail_reason
                self.error_code = self._wait_source.error_code or "ElevatorStateTimeout"
                self.action_status = ActionStatus.FAILED
            elif self._wait_source.action_status == ActionStatus.FINISHED:
                self._attempt = 1
                self._blocked_since = None
                self._clear_block_status()
                self._start_motion(self._guide_point(), EntryMotionPhase.GUIDE)
            return self.action_status
        return self.action_status

    def cancel(self):
        if self._motion is not None:
            self._motion.cancel()
        super().cancel()


class ElevatorExitRecoveryAction(ActionBase):
    """Exit the elevator and recover from a blocked doorway without failing."""

    EXITING = "EXITING"
    WAITING_RETRY_INTERVAL = "WAITING_RETRY_INTERVAL"
    WAITING_TARGET = "WAITING_TARGET"
    SWITCHING_MAP = "SWITCHING_MAP"

    def __init__(self, target, protocol, lease, target_floor, active_time,
                 target_map, switch_point, switch_pose=None,
                 stable_time=2.0, min_confidence=0.65,
                 source_switch_dir=None, target_switch_dir=None,
                 workspace="",
                 on_started=None, on_finished=None):
        super().__init__(self.__class__.__name__)
        self.target = target
        self.protocol = protocol
        self.lease = lease
        self.target_floor = int(target_floor)
        self.active_time = int(active_time)
        self.target_map = str(target_map)
        self.switch_point = str(switch_point)
        self.switch_pose = switch_pose
        self.stable_time = float(stable_time)
        self.min_confidence = float(min_confidence)
        self.source_switch_dir = source_switch_dir
        self.target_switch_dir = target_switch_dir
        self.workspace = workspace
        self.on_started = on_started
        self._on_finished = on_finished
        self.motion = None
        self.wait_target = None
        self.switch_map = None
        self.phase = None
        self._blocked_since = None
        self._retry_count = 0
        self._retry_at = None

    def args_summary(self):
        return {
            "target": self.target,
            "target_floor": self.target_floor,
            "target_map": self.target_map,
            "switch_point": self.switch_point,
        }

    def _fail_from(self, action, default_code="ElevatorExitRecoveryFailed"):
        self.fail_reason = getattr(action, "fail_reason", "")
        self.error_code = getattr(action, "error_code", "") or default_code
        self.action_status = ActionStatus.FAILED

    def _start_motion(self):
        self.motion = ElevatorBezierAction(
            self.target,
            is_exit=True,
            switch_dir=self.target_switch_dir,
            workspace=self.workspace,
        )
        self.motion.reset()
        if self.motion.action_status == ActionStatus.FAILED:
            self._fail_from(self.motion, "ElevatorLocalMoveFailed")
            return
        self.phase = self.EXITING
        self._blocked_since = None
        if self.on_started is not None:
            self.on_started()
        Trace.log({
            "event": "elevatorExitAttemptStarted",
            "retry": self._retry_count,
            "target": [self.motion.target.get("x"), self.motion.target.get("y")],
        }, name="elevator.exit")

    def reset(self):
        super().reset()
        self.motion = None
        self.wait_target = None
        self.switch_map = None
        self.phase = None
        self._blocked_since = None
        self._retry_count = 0
        self._retry_at = None
        self._start_motion()

    def _start_recovery(self, now):
        if self.motion is not None:
            self.motion.cancel()
        try:
            self.lease.release_unconditionally("exit blocked timeout retry")
        except Exception as error:
            self.fail_reason = str(error)
            if isinstance(error, ProtocolRejected):
                self.error_code = "ElevatorProtocolRejected"
            elif isinstance(error, ProtocolUnavailable):
                self.error_code = "ElevatorProtocolUnavailable"
            else:
                self.error_code = "ElevatorReleaseFailed"
            self.action_status = ActionStatus.FAILED
            return
        self._retry_count += 1
        self._retry_at = now + ConfigParams.exit_retry_interval
        self.phase = self.WAITING_RETRY_INTERVAL
        self._blocked_since = None
        Trace.log({
            "event": "elevatorExitRetryIntervalStarted",
            "retry": self._retry_count,
            "interval": ConfigParams.exit_retry_interval,
        }, name="elevator.exit")

    def _start_target_retry(self):
        try:
            self.lease.call(self.target_floor)
        except Exception as error:
            self.fail_reason = str(error)
            if isinstance(error, ProtocolRejected):
                self.error_code = "ElevatorProtocolRejected"
            elif isinstance(error, ProtocolUnavailable):
                self.error_code = "ElevatorProtocolUnavailable"
            else:
                self.error_code = "ElevatorInternalError"
            self.action_status = ActionStatus.FAILED
            return
        self.wait_target = WaitTargetElevatorAction(
            self.protocol,
            self.target_floor,
            timeout=ConfigParams.elevator_arrival_timeout,
            lease=self.lease,
        )
        self.wait_target.reset()
        self.phase = self.WAITING_TARGET
        self._blocked_since = None
        Trace.log({
            "event": "elevatorExitBlockedRetry",
            "retry": self._retry_count,
            "targetFloor": self.target_floor,
            "remainingArrivalTimeout": ConfigParams.elevator_arrival_timeout,
        }, name="elevator.exit")

    def _start_remap(self):
        self.switch_map = SwitchMapAction(
            self.target_map,
            self.switch_point,
            self.switch_pose,
            self.stable_time,
            self.min_confidence,
            # Recovery starts on the target-floor map already.  Reusing the
            # original source-floor direction would apply a second, incorrect
            # heading offset during same-map relocalization.
            source_switch_dir=self.target_switch_dir,
            target_switch_dir=self.target_switch_dir,
        )
        self.switch_map.reset()
        self.phase = self.SWITCHING_MAP

    def run(self, ctx=None):
        if self.action_status != ActionStatus.RUNNING:
            return self.action_status
        now = time.monotonic()
        if self.phase == self.WAITING_RETRY_INTERVAL:
            if now < self._retry_at:
                return self.action_status
            self._start_target_retry()
            return self.action_status
        if self.phase == self.EXITING:
            self.motion.run(ctx)
            if self.motion.action_status == ActionStatus.FAILED:
                self._fail_from(self.motion, "ElevatorLocalMoveFailed")
                return self.action_status
            if self.motion.action_status == ActionStatus.FINISHED:
                if self._on_finished is not None:
                    self._on_finished()
                self.action_status = ActionStatus.FINISHED
                return self.action_status
            try:
                blocked = bool(NavStatus.getBlock())
            except Exception:
                blocked = False
            if not blocked:
                self._blocked_since = None
            elif self._blocked_since is None:
                self._blocked_since = now
            elif now - self._blocked_since >= ConfigParams.exit_blocked_timeout:
                self._start_recovery(now)
            return self.action_status
        if self.phase == self.WAITING_TARGET:
            self.wait_target.run(ctx)
            if self.wait_target.action_status == ActionStatus.FAILED:
                self._fail_from(self.wait_target, "ElevatorStateTimeout")
            elif self.wait_target.action_status == ActionStatus.FINISHED:
                self._start_remap()
            return self.action_status
        if self.phase == self.SWITCHING_MAP:
            self.switch_map.run(ctx)
            if self.switch_map.action_status == ActionStatus.FAILED:
                self._fail_from(self.switch_map, "ElevatorMapSwitchFailed")
            elif self.switch_map.action_status == ActionStatus.FINISHED:
                self._start_motion()
            return self.action_status
        self.fail_reason = "invalid elevator exit recovery phase"
        self.error_code = "ElevatorInternalError"
        self.action_status = ActionStatus.FAILED
        return self.action_status

    def cancel(self):
        if self.motion is not None:
            self.motion.cancel()
        if self.wait_target is not None:
            self.wait_target.cancel()
        if self.switch_map is not None:
            self.switch_map.cancel()
        super().cancel()


def _resolve_exit_point(args):
    exit_point = args.get("targetStation")
    if exit_point in (None, "", {}):
        raise ValueError("target Entry must configure exitPoint for elevator exit")
    if isinstance(exit_point, str):
        return exit_point
    return resolve_map_point(exit_point, "exitPoint")


def build_actions(args, protocol, publisher=None):
    active_time = int(ConfigParams.protocol_active_time)
    if not 2 <= active_time <= 0xFF:
        raise ValueError("protocol active time must be in range 2..255")
    if ConfigParams.elevator_status_poll_interval >= active_time:
        raise ValueError("elevator status poll interval must be less than protocol active time")
    if (not -128 <= int(args["sourceFloor"]) <= 127
            or not -128 <= int(args["targetFloor"]) <= 127):
        raise ValueError("sourceFloor and targetFloor must be in range -128..127")
    lease = ElevatorLease(protocol, args["sourceFloor"], active_time)
    if publisher is not None:
        publisher.lease = lease
    keep_alive = ElevatorKeepAliveAction(
        lease,
        on_state=publisher.publish if publisher is not None else None,
    )

    def mark_entering():
        lease.mark_entering()
        if publisher is not None:
            publisher.publish(ElevatorPhase.ENTERING)

    def mark_inside():
        lease.mark_inside()
        if publisher is not None:
            publisher.publish(ElevatorPhase.RIDING)

    def mark_exiting():
        lease.mark_exiting()
        if publisher is not None:
            publisher.publish(ElevatorPhase.EXITING)

    def mark_outside():
        lease.mark_outside()
        keep_alive.request_stop()
        if publisher is not None:
            publisher.publish(ElevatorPhase.RELEASING)

    source_workspace = args.get("sourceWorkspace", "")
    call_point = resolve_map_point(
        args["sourceStation"],
        "callPoint", source_workspace,
    )
    entry = resolve_map_point(
        args["sourceSwitchPoint"],
        "source switchPoint", source_workspace,
    )
    if entry.get("dir") is None:
        raise ValueError("source switchPoint must configure dir")
    guide_reference = args.get("sourceEntryPoint")
    guide_point = None
    if guide_reference not in (None, "", {}):
        guide_point = resolve_map_point(
            guide_reference, "source entryPoint", source_workspace,
        )
        if isinstance(guide_reference, str):
            guide_point.setdefault("pointName", guide_reference)
    call_point_dir = call_point.get("dir")
    target_switch_pose = args.get("targetSwitchPose")
    target_switch_dir = args.get("targetSwitchDir")
    if target_switch_dir is None:
        raise ValueError("target switchPoint must configure dir")
    exit_point = _resolve_exit_point(args)
    target_workspace = args.get("targetWorkspace", "")
    target_map = args.get("targetMap")
    if not target_map and target_workspace:
        target_map = Map.getMapNameByWorkspace(target_workspace)
    if not target_map:
        raise ValueError(
            "targetWorkspace must bind a map in workspace_topology.json"
        )
    if not args.get("targetSwitchPoint"):
        raise ValueError("targetSwitchPoint is required")

    switch_map = SwitchMapAction(
        target_map,
        args["targetSwitchPoint"],
        args.get("targetSwitchPose"),
        ConfigParams.map_switch_stable_time,
        ConfigParams.map_switch_min_confidence,
        partial(publisher.publish, ElevatorPhase.SWITCHING_MAP) if publisher else None,
        source_switch_dir=entry.get("dir"),
        target_switch_dir=target_switch_dir,
    )
    wait_target = WaitTargetElevatorAction(
        protocol,
        args["targetFloor"],
        timeout=ConfigParams.elevator_arrival_timeout,
        lease=lease,
    )
    target_actions = (
        [switch_map, wait_target]
        if ConfigParams.switch_map_before_arrival
        else [wait_target, switch_map]
    )

    return [
        ProtocolAction(
            "CallSourceElevator",
            lease.call,
            on_started=(
                partial(publisher.publish, ElevatorPhase.CALLING_SOURCE)
                if publisher else None
            ),
            callback_args=(int(args["sourceFloor"]),),
        ),
        (keep_alive, "NONE"),
        WaitSourceElevatorAction(
            protocol,
            args["sourceFloor"],
            timeout=ConfigParams.elevator_arrival_timeout,
            lease=lease,
            on_started=(
                partial(publisher.publish, ElevatorPhase.WAITING_SOURCE)
                if publisher else None
            ),
        ),
        ElevatorEntryHeadingAction(
            call_point_dir,
            forward=ConfigParams.entryForward,
        ),
        ElevatorEntryAction(
            entry,
            call_point,
            lease,
            protocol,
            args["sourceFloor"],
            on_entering=mark_entering,
            on_inside=mark_inside,
            guide_point=guide_point,
        ),
        ProtocolAction(
            "SelectTargetFloor",
            lease.call,
            on_error=lease.release_if_safe,
            on_cancel=lease.release_if_safe,
            callback_args=(int(args["targetFloor"]),),
        ),
        *target_actions,
        ElevatorExitRecoveryAction(
            exit_point,
            protocol,
            lease,
            args["targetFloor"],
            active_time,
            target_map,
            args["targetSwitchPoint"],
            args.get("targetSwitchPose"),
            ConfigParams.map_switch_stable_time,
            ConfigParams.map_switch_min_confidence,
            source_switch_dir=entry.get("dir"),
            target_switch_dir=target_switch_dir,
            workspace=target_workspace,
            on_started=mark_exiting,
            on_finished=mark_outside,
        ),
        ProtocolAction(
            "ReleaseElevator",
            lease.release,
            on_error=lease.release_if_safe,
            on_cancel=lease.release_if_safe,
            error_code="ElevatorReleaseFailed",
        ),
    ]


def _find_lease(queue):
    for action in queue.action_list:
        lease = getattr(action, "lease", None)
        if lease is not None:
            return lease
    return None


class ElevatorModule(ModuleBase):
    """梯控业务编排器；main 只负责 SDK 初始化和 tick 驱动。"""

    def __init__(self):
        super().__init__()
        self.status = ScriptStatus.NONE
        self.args = {}
        self.queue = None
        self.publisher = None
        self.protocol = None
        self.safety_holding = None

    def set_status(self, status):
        status = ScriptStatus(status)
        if self.status != status:
            Trace.log({"event": "moduleStateChanged", "status": status.name}, name="elevator")
        self.status = status

    def _fail_queue(self):
        failed = next(
            (action for action in self.queue.action_list
             if action.action_status == ActionStatus.FAILED), None
        )
        if failed is None:
            return
        Navigation.setTaskError(
            failed.error_code or "ElevatorActionFailed",
            failed.fail_reason or "elevator action failed",
        )
        lease = _find_lease(self.queue)
        self.safety_holding = None
        if lease is not None:
            try:
                lease.release_unconditionally(
                    failed.error_code or "elevator action failed"
                )
            except Exception as error:
                Trace.log({
                    "event": "elevatorFailureReleaseFailed",
                    "errorCode": failed.error_code,
                    "error": str(error),
                }, name="elevator.err")
        if self.publisher is not None:
            self.publisher.publish(ElevatorPhase.FAILED)
        self.set_status(ScriptStatus.FAILED)

    def init_args(self, args):
        raw_args = dict(args or {})
        if raw_args.get("operation") != "ride":
            Navigation.setTaskError("ElevatorInputParamError", "operation must be ride")
            self.set_status(ScriptStatus.FAILED)
            return
        try:
            device_id = str(raw_args["operation.ride.deviceId"]).strip()
            target_workspace = str(
                raw_args["operation.ride.targetWorkspace"]
            ).strip()
            if not device_id:
                raise ValueError("operation.ride.deviceId is required")
            if not target_workspace:
                raise ValueError("operation.ride.targetWorkspace is required")
            self.args = {
                key: value for key, value in raw_args.items()
                if key == "operation" or key.startswith("operation.ride.")
                or key == "communicationProtocol"
                or key.startswith("communicationProtocol.")
            }
            self.args["deviceId"] = device_id
            self.args["targetWorkspace"] = target_workspace
            target_station = str(
                raw_args.get("operation.ride.targetStation", "") or ""
            ).strip()
            if target_station:
                self.args["targetStation"] = target_station
        except (KeyError, TypeError, ValueError) as error:
            Navigation.setTaskError("ElevatorInputParamError", str(error))
            Trace.log(str(error), name="elevator.err")
            self.set_status(ScriptStatus.FAILED)
            return
        try:
            self.args.update(_resolve_ride_context(dict(self.args)))
        except (KeyError, TypeError, ValueError) as error:
            Navigation.setTaskError("ElevatorConfigError", str(error))
            Trace.log(str(error), name="elevator.err")
            self.set_status(ScriptStatus.FAILED)
            return
        except Exception as error:
            Navigation.setTaskError("ElevatorInternalError", str(error))
            Trace.log(str(error), name="elevator.err")
            self.set_status(ScriptStatus.FAILED)
            return
        try:
            self.protocol = create_protocol(self.args, "elevator")
        except (KeyError, TypeError, ValueError) as error:
            Navigation.setTaskError("ElevatorInputParamError", str(error))
            Trace.log(str(error), name="elevator.err")
            self.set_status(ScriptStatus.FAILED)
            return
        except Exception as error:
            Navigation.setTaskError("ElevatorInternalError", str(error))
            Trace.log(str(error), name="elevator.err")
            self.set_status(ScriptStatus.FAILED)
            return
        try:
            self.publisher = ElevatorStatePublisher(self.args)
            self.publisher.publish(ElevatorPhase.VALIDATING)
            self.queue = ActionTask(mod="elevator")
            self.queue.build(build_actions(self.args, self.protocol, self.publisher))
            self.set_status(ScriptStatus.RUNNING)
        except (KeyError, TypeError, ValueError) as error:
            Navigation.setTaskError("ElevatorConfigError", str(error))
            Trace.log(str(error), name="elevator.err")
            self.set_status(ScriptStatus.FAILED)
        except Exception as error:
            Navigation.setTaskError("ElevatorInternalError", str(error))
            Trace.log(str(error), name="elevator.err")
            self.set_status(ScriptStatus.FAILED)

    def run(self):
        if self.queue is None:
            return
        if self.queue.is_suspended:
            self.queue.resume()
        self.queue.step(self)
        if self.queue.status == ActionStatus.FAILED:
            self._fail_queue()
        elif self.queue.status == ActionStatus.FINISHED:
            if (self.publisher is not None
                    and not self.publisher.publish(ElevatorPhase.FINISHED)):
                Navigation.setTaskError(
                    "ElevatorResultUnavailable",
                    str(self.publisher.last_error or "failed to publish final elevator state"),
                )
                self.set_status(ScriptStatus.FAILED)
            else:
                self.set_status(ScriptStatus.FINISHED)

    def run_suspended(self):
        if self.queue is None:
            return
        self.queue.step(self)
        if self.queue.status == ActionStatus.FAILED:
            self._fail_queue()

    def suspend(self):
        if self.queue is not None and self.status == ScriptStatus.RUNNING:
            self.queue.suspend()
            if ConfigParams.release_control_on_pause:
                lease = _find_lease(self.queue)
                if lease is not None:
                    try:
                        lease.release_unconditionally("task paused")
                        Trace.log({
                            "event": "elevatorControlReleasedOnPause",
                            "carPosition": lease.car_position.value,
                        }, name="elevator")
                    except Exception as error:
                        Trace.log({
                            "event": "elevatorPauseReleaseFailed",
                            "error": str(error),
                        }, name="elevator.err")
            self.set_status(ScriptStatus.SUSPENDED)

    def resume(self):
        if self.queue is not None and self.status == ScriptStatus.SUSPENDED:
            if ConfigParams.release_control_on_pause:
                lease = _find_lease(self.queue)
                if lease is not None and not lease.acquired:
                    try:
                        lease.call(lease.floor)
                        Trace.log({
                            "event": "elevatorControlReacquiredAfterPause",
                            "floor": lease.floor,
                        }, name="elevator")
                    except Exception as error:
                        Navigation.setTaskError(
                            "ElevatorProtocolUnavailable", str(error)
                        )
                        self.queue.cancel("failed to reacquire elevator after pause")
                        self.set_status(ScriptStatus.FAILED)
                        return
            self.queue.resume()
            self.set_status(ScriptStatus.RUNNING)

    def cancel(self):
        lease = _find_lease(self.queue) if self.queue is not None else None
        if self.queue is not None and not self.queue.is_done:
            self.queue.cancel("module stopped")
        # Explicit cancellation differs from an unexpected action failure:
        # the caller asked to end the control session, so do not keep-alive.
        self.safety_holding = None
        if lease is not None:
            try:
                lease.release_unconditionally("explicit module cancellation")
            except Exception as error:
                Trace.log({
                    "event": "elevatorCancellationReleaseFailed",
                    "error": str(error),
                }, name="elevator.err")
        self.set_status(ScriptStatus.FAILED)

    def reset(self):
        if self.queue is not None:
            self.queue.reset()
        self.queue = None
        self.publisher = None
        self.protocol = None
        self.args = {}
        self.set_status(ScriptStatus.NONE)
        return True


def main():
    ScriptParam.setConfigChangeCallBack(ConfigParams.load_config)
    Module.init()
    module = ElevatorModule()
    while True:
        Module.setStatus(module.status)
        status = module.status
        if status == ScriptStatus.NONE:
            args = Module.getTaskArgs()
            if args:
                try:
                    module.init_args(script_param.loadInput(args))
                except ValueError as error:
                    Navigation.setTaskError("ElevatorInputParamError", str(error))
                    module.set_status(ScriptStatus.FAILED)
        elif status == ScriptStatus.RUNNING:
            module.run()
        elif status == ScriptStatus.SUSPENDED:
            module.run_suspended()
        elif status in (ScriptStatus.FAILED, ScriptStatus.FINISHED):
            module.reset()
        time.sleep(0.05)


if __name__ == "__main__":
    main()
