import math
import json
import os
import time
from functools import partial

from syspy import Loc, Map, Module, ModuleBase, Navigation, RobotParam, ScriptStatus, ScriptParam, Trace
from syspy.lib.action_task import ActionBase, ActionStatus, ActionTask
from syspy.script_data import ScriptData
from syspy.utils.param_server import BindType, ParamType

from standard.goBezier import GoBezierWorld as _BaseGoBezierWorld
from third import (
    DoorCarPosition,
    DoorPassContext,
    DoorPhase,
    create_protocol,
    map_device_data,
    resolve_map_point,
    topology_device_data,
)
from third.door_protocol.base import ProtocolRejected, ProtocolUnavailable


script_param = ScriptParam(__file__)

_TOPOLOGY_PATH = "/opt/.data/rbk/resources/maps/workspace_topology.json"


def _protocol_script_choices():
    directory = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", "third", "door_protocol"
    ))
    return sorted(
        name[:-3] for name in os.listdir(directory)
        if name.endswith(".py") and name not in ("__init__.py", "base.py")
    ) if os.path.isdir(directory) else ["yuefan"]


def _map_gate_point_names(protocol_data):
    point_names = protocol_data.get("pointNames")
    if isinstance(point_names, str):
        try:
            point_names = json.loads(point_names)
        except ValueError:
            point_names = [item.strip() for item in point_names.split(",") if item.strip()]
    if point_names is None:
        indexed = [protocol_data.get("pointNames.0"), protocol_data.get("pointNames.1")]
        if all(indexed):
            point_names = indexed
    if isinstance(point_names, (list, tuple)):
        return list(point_names)
    return None


class GoBezierWorld(_BaseGoBezierWorld):
    """Door-local Bezier path whose curve follows target geometry."""

    def __init__(self, *args, use_geometry_path=False, path_heading=None, **kwargs):
        self._use_geometry_path = bool(use_geometry_path)
        self._path_heading = (
            None if path_heading is None else float(path_heading)
        )
        super().__init__(*args, **kwargs)

    def get_path(self):
        if not self._use_geometry_path:
            return super().get_path()
        original_target = list(self.target_world)
        pose = Loc.getPose()
        approach_heading = self._path_heading
        if approach_heading is None:
            approach_heading = math.atan2(
                float(original_target[1]) - float(pose["y"]),
                float(original_target[0]) - float(pose["x"]),
            )
        self.target_world[2] = approach_heading + math.pi
        try:
            return super().get_path()
        finally:
            self.target_world = original_target
            if self.end_position_world is not None:
                self.end_position_world[2] = original_target[2]

    def compute_bezier_controls_dir(self, p0, p3, alpha=0.3):
        if not self._use_geometry_path:
            return super().compute_bezier_controls_dir(p0, p3, alpha)
        path_heading = self._path_heading
        if path_heading is None:
            path_heading = math.atan2(p3[1] - p0[1], p3[0] - p0[0])
        geometry_target = [p3[0], p3[1], path_heading + math.pi]
        return super().compute_bezier_controls_dir(p0, geometry_target, alpha)

    def start_bezier_path(self):
        if self._use_geometry_path and not self.is_backwards:
            self.end_position_world[2] -= math.pi
        return super().start_bezier_path()


class ConfigParams:
    aheadDist = 2.0
    minAheadDist = 0.5
    maxSpeed = 0.2
    maxCurve = 1.3
    reachDist = 0.05
    reachAngle = 5.0
    minObsStopDist = 0.05
    minObsDecDist = 0.1
    door_open_timeout = 30.0
    status_poll_interval = 1.0

    @classmethod
    def init(cls):
        builder = script_param.builderConfig()
        with builder.GROUPS():
            with builder.GROUP(key="bezier", name="Bezier", desc="Bezier path parameters"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    cls._float_param(builder, "aheadDist", "Ahead Dist", 2.0, 0.0, 5.0, "m")
                    cls._float_param(builder, "minAheadDist", "Min Ahead Dist", 0.5, 0.0, 2.0, "m")
                    cls._float_param(builder, "maxSpeed", "Maximum speed", 0.2, 0.01, 1.0, "m/s")
                    cls._float_param(builder, "maxCurve", "Max Curve", 1.3, 0.1, 30.0)
                    cls._float_param(builder, "reachDist", "Reach distance", 0.05, 0.001, 0.5, "m")
                    cls._float_param(builder, "reachAngle", "Reach angle", 5.0, 0.1, 30.0, "deg")
            with builder.GROUP(key="doorState", name="Door state", desc="Door state parameters"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    cls._float_param(builder, "doorOpenTimeout", "Door open timeout", 30.0, 1.0, 120.0, "s")
                    cls._float_param(builder, "statusPollInterval", "Status poll interval", 1.0, 0.1, 5.0, "s")
            with builder.GROUP(key="obstacleStop", name="Obstacle stop", desc="Passage obstacle distances"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    cls._float_param(builder, "minObsStopDist", "Minimum obstacle stop distance", 0.05, 0.0, 2.0, "m")
                    cls._float_param(builder, "minObsDecDist", "Minimum obstacle deceleration distance", 0.1, 0.0, 2.0, "m")
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
        cls.door_open_timeout = float(config.get("doorOpenTimeout", cls.door_open_timeout))
        cls.status_poll_interval = float(config.get("statusPollInterval", cls.status_poll_interval))
        for name, value, minimum, maximum in (
                ("minObsStopDist", cls.minObsStopDist, 0.0, 2.0),
                ("minObsDecDist", cls.minObsDecDist, 0.0, 2.0),
                ("doorOpenTimeout", cls.door_open_timeout, 1.0, 120.0),
                ("statusPollInterval", cls.status_poll_interval, 0.1, 5.0)):
            if not minimum <= value <= maximum:
                raise ValueError(
                    "{} must be in range {}..{}".format(name, minimum, maximum)
                )


ConfigParams.init()


class InputParams:
    """Formal MF RunScript inputs."""

    builder = script_param.builderInput()
    with builder.GROUPS():
        with builder.GROUP(key="operation", name="Operation", desc="Door operation"):
            builder.TYPE(ParamType.COMBO_BOX)
            builder.REQUIRED(True)
            with builder.CHILDREN():
                with builder.CHILD(key="pass", name="Pass", desc="Pass one automatic gate"):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        with builder.CHILD(key="deviceId", name="Gate device", desc="MF selected gate"):
                            builder.TYPE(ParamType.STRING)
                            builder.REQUIRED(True)
                        with builder.CHILD(key="sourceStation", name="Source station", desc="Directed gate edge start"):
                            builder.TYPE(ParamType.STRING)
                            builder.REQUIRED(True)
                        with builder.CHILD(key="targetStation", name="Target station", desc="Directed gate edge end"):
                            builder.TYPE(ParamType.STRING)
                            builder.REQUIRED(True)
        with builder.GROUP(key="communicationProtocol", name="Communication protocol", desc="Door protocol binding"):
            builder.TYPE(ParamType.COMBO_BOX)
            with builder.CHILDREN():
                for protocol_name in _protocol_script_choices():
                    with builder.CHILD(key=protocol_name, name=protocol_name, desc="Door {} protocol".format(protocol_name)):
                        builder.TYPE(ParamType.ARRAY)
                        with builder.CHILDREN():
                            with builder.CHILD(key="name", name="Protocol script", desc="Protocol implementation script"):
                                builder.TYPE(ParamType.BIND_TYPE)
                                builder.BINDTYPE(
                                    BindType.script("tasks:third:door_protocol")
                                )
                                builder.DEFAULTVALUE(
                                    "tasks/third/door_protocol/{}.py".format(protocol_name)
                                )
                            with builder.CHILD(key="config", name="Config", desc="Door protocol instance configuration"):
                                builder.TYPE(ParamType.ARRAY)
                                builder.REQUIRED(False)
                                builder.DEFAULTVALUE({})
    builder.save()


script_param.addAction(
    action_name="Pass Automatic Gate",
    policy={},
    args={
        "operation": "pass",
        "operation.pass.deviceId": "GATE1",
        "operation.pass.sourceStation": "",
        "operation.pass.targetStation": "",
    },
    config={},
    stage=3,
)
script_param.saveAction()


class ProtocolAction(ActionBase):
    def __init__(self, operation, callback, on_error=None, on_cancel=None,
                 on_started=None, on_finished=None, callback_args=()):
        super().__init__(operation)
        self._callback = callback
        self._on_error = on_error
        self._on_cancel = on_cancel
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
            if isinstance(error, ProtocolUnavailable):
                self.error_code = "DoorProtocolUnavailable"
            elif isinstance(error, ProtocolRejected):
                self.error_code = "DoorProtocolRejected"
            else:
                self.error_code = "DoorActionFailed"
            if self._on_error is not None:
                try:
                    self._on_error()
                except Exception as cleanup_error:
                    Trace.log({
                        "event": "protocolCleanupFailed",
                        "operation": self.action_type,
                        "error": str(cleanup_error),
                    }, name="door.err")
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
                }, name="door.err")
        super().cancel()

    def result_description(self):
        if self.result is None:
            return {}
        return {key: value for key, value in vars(self.result).items()
                if isinstance(value, (bool, int, float, str))}


class DoorBezierAction(ActionBase):
    _POLICY_PROGRESS_STEP = 0.05
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

    def __init__(self, target, on_started_callback=None,
                 on_finished_callback=None, source=None):
        super().__init__(self.__class__.__name__)
        self.target = target
        self.source = source
        self.navigation = None
        self.on_started_callback = on_started_callback
        self.on_finished_callback = on_finished_callback
        self._policy_initialized = False
        self._policy_active = False
        self._policy_defaults = {}
        self._policy_start_distance = 0.0
        self._last_policy_progress = -1.0

    def args_summary(self):
        summary = {"target": self.target}
        if self.source is not None:
            summary["source"] = self.source
        return summary

    def _path_heading(self):
        if self.source is None:
            return None
        return math.atan2(
            float(self.target["y"]) - float(self.source["y"]),
            float(self.target["x"]) - float(self.source["x"]),
        )

    def reset(self):
        super().reset()
        self._policy_initialized = False
        self._policy_active = False
        self._policy_defaults = {}
        self._policy_start_distance = 0.0
        self._last_policy_progress = -1.0
        path_heading = self._path_heading()
        self.navigation = GoBezierWorld(
            [float(self.target["x"]), float(self.target["y"]), float(self.target["theta"])],
            adjust_dist_for_curvature_limit=ConfigParams.aheadDist,
            min_ahead_dist=ConfigParams.minAheadDist,
            is_backwards=bool(self.target.get("backwards", False)),
            use_geometry_path=True,
            max_speed=ConfigParams.maxSpeed,
            curvature_limit=ConfigParams.maxCurve,
            path_dist_accuracy=ConfigParams.reachDist,
            # Passing a gate is position-first.  The target station heading
            # must not trigger an in-place rotation after the crossing.
            path_angle_accuracy=180.0,
            path_heading=path_heading,
        )
        if self.on_started_callback is not None:
            self.on_started_callback()
        Trace.log({"event": "started", "target": self.navigation.target_world}, name="door.bezier")

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
            policy[policy_key] = round(
                target + (default - target) * (1.0 - progress), 4
            )
        Navigation.appendCustomPolicy("door_obstacle_distance", policy)
        self._policy_active = True
        self._last_policy_progress = progress

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
            self.error_code = "DoorActionFailed"
            self.action_status = ActionStatus.FAILED
        if self.action_status == ActionStatus.FAILED and not self.error_code:
            self.error_code = "DoorNavigationFailed"
        if self.action_status == ActionStatus.FINISHED:
            Navigation.resetPath()
            Trace.log({"event": "finished"}, name="door.bezier")
            if self.on_finished_callback is not None:
                self.on_finished_callback()
        if self.action_status in (ActionStatus.FINISHED, ActionStatus.FAILED):
            try:
                self._clear_policy()
            except Exception as error:
                self.fail_reason = str(error)
                self.error_code = "DoorActionFailed"
                self.action_status = ActionStatus.FAILED
        return self.action_status

    def cancel(self):
        try:
            self._clear_policy()
        except Exception as error:
            Trace.log({"event": "navigationPolicyClearFailed", "error": str(error)},
                      name="door.err")
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


class DoorLease:
    """门控控制权的幂等持有与释放。"""

    def __init__(self, protocol, active_time, source_side=None, instance_args=None,
                 legacy_open_mode=None):
        self.protocol = protocol
        self.active_time = int(active_time)
        self.source_side = source_side
        self.instance_args = dict(instance_args or {})
        self.acquired = False
        self._released = False
        self._release_result = None
        self.latest = None
        self.legacy_open_mode = legacy_open_mode
        self.car_position = DoorCarPosition.OUTSIDE
        self.open_requested = False

    def _request(self, method):
        if getattr(self.protocol, "supports_source_side", False):
            return method(self.source_side, self.instance_args, self.active_time)
        # Existing protocol fakes and old integrations remain usable while the
        # formal interface migrates to sourceSide + instanceArgs.
        return method(self.legacy_open_mode, self.active_time)

    def open(self):
        result = self._request(self.protocol.request_open)
        self.acquired = True
        self.open_requested = True
        self.latest = result
        return result

    def acquire_control(self):
        method = getattr(self.protocol, "acquire_control", None)
        if method is None:
            raise ValueError("door protocol does not support openDelayTime")
        result = method(self.instance_args, self.active_time)
        self.acquired = True
        self.latest = result
        return result

    def keep_alive(self):
        acquire = getattr(self.protocol, "acquire_control", None)
        if self.acquired and not self.open_requested and acquire is not None:
            self.latest = acquire(self.instance_args, self.active_time)
        else:
            # A status query is observation only. Once the gate has been
            # opened, use the protocol keep-alive command so devices that
            # close or expire their lease without a control request remain
            # held open during passage.
            self.latest = self._request(self.protocol.keep_alive)
        return self.latest

    def mark_passing(self):
        self.car_position = DoorCarPosition.PASSING

    def mark_outside(self):
        self.car_position = DoorCarPosition.OUTSIDE

    def release(self):
        if not self.acquired:
            return None
        if self._released:
            return self._release_result
        if getattr(self.protocol, "supports_source_side", False):
            result = self.protocol.release(self.instance_args)
        else:
            result = self.protocol.release()
        self._release_result = result
        self._released = True
        return result

    def release_if_safe(self):
        if not self.acquired or self.car_position == DoorCarPosition.OUTSIDE:
            return self.release()
        Trace.log({
            "event": "doorSafetyHolding",
            "carPosition": self.car_position.value,
            "reason": "defer release until robot exits passage",
        }, name="door.err")
        return None


class DoorOpenDelayAction(ActionBase):
    def __init__(self, delay_time):
        super().__init__(self.__class__.__name__)
        self.delay_time = float(delay_time)
        self._started_at = None

    def reset(self):
        super().reset()
        self._started_at = time.monotonic()

    def run(self, _ctx=None):
        if time.monotonic() - self._started_at >= self.delay_time:
            self.action_status = ActionStatus.FINISHED
        return self.action_status


class DoorKeepAliveAction(ActionBase):
    def __init__(self, lease, poll_interval=1.0, on_state=None):
        super().__init__(self.__class__.__name__)
        self.background = True
        self.cleanup_on_failure = True
        self.lease = lease
        self.poll_interval = float(poll_interval)
        self.on_state = on_state
        self._next_poll_at = None
        self._stop_requested = False

    def reset(self):
        super().reset()
        self._next_poll_at = time.monotonic()
        self._stop_requested = False

    def request_stop(self):
        self._stop_requested = True

    def run(self, _ctx=None):
        if self._stop_requested:
            self.action_status = ActionStatus.FINISHED
            return self.action_status
        now = time.monotonic()
        if now < self._next_poll_at:
            return self.action_status
        try:
            self.lease.keep_alive()
            if self.on_state is not None:
                self.on_state()
        except Exception as error:
            self.fail_reason = str(error)
            self.error_code = (
                "DoorProtocolRejected"
                if isinstance(error, ProtocolRejected)
                else "DoorProtocolUnavailable"
            )
            self.action_status = ActionStatus.FAILED
            return self.action_status
        self._next_poll_at = now + self.poll_interval
        return self.action_status

    def cancel(self):
        try:
            self.lease.release_if_safe()
        except Exception as error:
            Trace.log({"event": "doorCleanupFailed", "error": str(error)}, name="door.err")
        super().cancel()


class DoorStatePublisher:
    def __init__(self, args):
        self.args = args
        self.phase = DoorPhase.VALIDATING
        self.lease = None
        self.last_error = None

    def publish(self, phase=None):
        if phase is not None:
            self.phase = DoorPhase(phase)
        latest = getattr(self.lease, "latest", None)
        payload = {
            "phase": self.phase.value,
            "deviceId": str(self.args.get("deviceId", "")),
            "sourceStation": str(self.args.get("sourceStation", "")),
            "targetStation": str(self.args.get("targetStation", "")),
            "sourceSide": str(self.args.get("sourceSide", "")),
            "controlState": getattr(latest, "control_state", "UNKNOWN"),
            "passageState": getattr(latest, "passage_state", "UNKNOWN"),
            "carPosition": getattr(
                getattr(self.lease, "car_position", None), "value", "UNKNOWN"
            ),
        }
        try:
            ScriptData.set("doorState", payload)
            self.last_error = None
            return True
        except Exception as error:
            self.last_error = error
            try:
                Trace.log({
                    "event": "doorStatePublishFailed",
                    "error": str(error),
                }, name="door.err")
            except Exception:
                pass
            return False


def _resolve_source_side(args):
    explicit = args.get("sourceSide")
    if explicit in ("sideA", "sideB"):
        return explicit
    point_names = args.get("pointNames")
    if point_names is not None:
        if not isinstance(point_names, (list, tuple)) or len(point_names) != 2:
            raise ValueError("pointNames must contain exactly two stations")
        source_station = args.get("sourceStation")
        if source_station == point_names[0]:
            return "sideA"
        if source_station == point_names[1]:
            return "sideB"
        raise ValueError("sourceStation is not one of pointNames")
    # Compatibility for the current simulator and old callers. Production MF
    # calls should always provide pointNames or sourceSide.
    if "openMode" in args and int(args["openMode"]) in (1, 2):
        return "sideA" if int(args["openMode"]) == 1 else "sideB"
    raise ValueError("pointNames/sourceSide is required")


def _protocol_instance_args(args):
    protocol_site = args.get("protocolSite") or {}
    data = protocol_site.get("jsonObject", protocol_site)
    data = data if isinstance(data, dict) else {}
    protocol_name = str(data.get("communicationProtocol", "") or "").strip()
    prefix = "communicationProtocol.{}.args.".format(protocol_name)
    instance_args = {
        str(key)[len(prefix):]: value
        for key, value in data.items()
        if protocol_name and str(key).startswith(prefix)
    }
    instance_args.update(dict(args.get("protocol.instanceArgs") or {}))
    for key, value in args.items():
        if key.startswith("protocol.") and key not in (
                "protocol.port", "protocol.timeout", "protocol.retries"):
            instance_args[key[len("protocol."):]] = value
    return instance_args


def build_actions(args, protocol, publisher=None):
    legacy_open_mode = args.get("openMode")
    if legacy_open_mode is not None and int(legacy_open_mode) not in (0, 1, 2):
        raise ValueError("openMode must be 0, 1, or 2")
    active_time = int(args.get("activeTime", 30))
    if not 2 <= active_time <= 0xFF:
        raise ValueError("activeTime must be in range 2..255")
    if ConfigParams.status_poll_interval >= active_time:
        raise ValueError("statusPollInterval must be less than activeTime")
    source_side = _resolve_source_side(args)
    instance_args = _protocol_instance_args(args)
    open_delay_time = float(instance_args.get("openDelayTime", 0.0) or 0.0)
    if not 0.0 <= open_delay_time <= 120.0:
        raise ValueError("openDelayTime must be in range 0..120")
    args["sourceSide"] = source_side
    lease = DoorLease(
        protocol,
        active_time,
        source_side=source_side,
        instance_args=instance_args,
        legacy_open_mode=(int(legacy_open_mode) if legacy_open_mode is not None else None),
    )
    if publisher is not None:
        publisher.lease = lease
    keep_alive = DoorKeepAliveAction(
        lease, ConfigParams.status_poll_interval,
        publisher.publish if publisher is not None else None,
    )

    def mark_passing():
        lease.mark_passing()
        if publisher is not None:
            publisher.publish(DoorPhase.PASSING)

    def finish_passage():
        lease.mark_outside()
        if publisher is not None:
            publisher.publish(DoorPhase.RELEASING)

    target = resolve_map_point(
        args.get("target") or args.get("targetStation"),
        "targetStation", args.get("workspace", ""),
    )
    source_reference = args.get("source") or args.get("sourceStation")
    source = None
    if source_reference not in (None, "", {}):
        source = resolve_map_point(
            source_reference, "sourceStation", args.get("workspace", ""),
        )

    actions = []
    if open_delay_time > 0.0:
        actions.extend([
            ProtocolAction(
                "AcquireDoorControl",
                lease.acquire_control,
                on_error=lease.release_if_safe,
                on_cancel=lease.release_if_safe,
                on_started=(
                    partial(publisher.publish, DoorPhase.ACQUIRING_CONTROL)
                    if publisher else None
                ),
            ),
            (keep_alive, "NONE"),
            DoorOpenDelayAction(open_delay_time),
        ])
    actions.append(ProtocolAction(
            "OpenDoor",
            lease.open,
            on_error=lease.release_if_safe,
            on_cancel=lease.release_if_safe,
            on_started=(
                partial(publisher.publish, DoorPhase.REQUESTING_OPEN)
                if publisher else None
            ),
        ))
    if open_delay_time <= 0.0:
        actions.append((keep_alive, "NONE"))
    actions.extend([
        DoorBezierAction(
            target,
            source=source,
            on_started_callback=mark_passing,
            on_finished_callback=finish_passage,
        ),
        ProtocolAction(
            "ReleaseDoor",
            lease.release,
            on_error=lease.release_if_safe,
            on_cancel=lease.release_if_safe,
            on_started=keep_alive.request_stop,
        ),
    ])
    return actions


class DoorSafetyHolding:
    """Keep the gate lease until a failed passage is known to be clear."""

    def __init__(self, lease, poll_interval=1.0, publisher=None):
        self.lease = lease
        self.poll_interval = float(poll_interval)
        self._next_poll_at = time.monotonic()
        self.resolved = False
        self.publisher = publisher
        if self.publisher is not None:
            self.publisher.publish(DoorPhase.SAFETY_HOLDING)

    def step(self):
        if self.resolved:
            return True
        if self.lease.car_position == DoorCarPosition.OUTSIDE:
            try:
                self.lease.release()
                self.resolved = True
                Trace.log({"event": "doorSafetyHoldingResolved"}, name="door.safety")
                return True
            except Exception as error:
                Trace.log({"event": "doorSafetyHoldingReleaseFailed", "error": str(error)},
                          name="door.err")
                return False
        now = time.monotonic()
        if now < self._next_poll_at:
            return False
        try:
            self.lease.keep_alive()
            if self.publisher is not None:
                self.publisher.publish(DoorPhase.SAFETY_HOLDING)
            Trace.log({"event": "doorSafetyHoldingKeepAlive",
                       "carPosition": self.lease.car_position.value}, name="door.safety")
        except Exception as error:
            Trace.log({"event": "doorSafetyHoldingKeepAliveFailed", "error": str(error),
                       "carPosition": self.lease.car_position.value}, name="door.err")
        self._next_poll_at = now + self.poll_interval
        return False


class DoorModule(ModuleBase):
    """门控业务编排器；协议、等待、过门和释放均由 ActionTask 驱动。"""

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
            Trace.log({"event": "moduleStateChanged", "status": status.name}, name="door")
        self.status = status

    def init_args(self, args):
        self.args = dict(args or {})
        if self.args.get("operation") != "pass":
            Navigation.setTaskError("DoorInputParamError", "operation must be pass")
            self.set_status(ScriptStatus.FAILED)
            return
        try:
            pass_context = DoorPassContext.from_args(self.args)
            for key, value in pass_context.as_args().items():
                self.args.setdefault(key, value)
            protocol_site = map_device_data(
                self.args.get("deviceId"), self.args.get("workspace", "")
            )
            protocol_data = protocol_site.get("jsonObject") or {}
            if not protocol_data:
                protocol_data = topology_device_data(
                    _TOPOLOGY_PATH, "doorList", self.args.get("deviceId")
                )
                if protocol_data:
                    protocol_site = {"jsonObject": protocol_data}
            if protocol_data:
                self.args["protocolSite"] = protocol_site
            point_names = _map_gate_point_names(protocol_data)
            if "pointNames" not in self.args and point_names is not None:
                self.args["pointNames"] = point_names
            self.protocol = create_protocol(self.args, "door")
        except (KeyError, TypeError, ValueError) as error:
            Navigation.setTaskError("DoorInputParamError", str(error))
            Trace.log(str(error), name="door.err")
            self.set_status(ScriptStatus.FAILED)
            return
        except Exception as error:
            Navigation.setTaskError("DoorActionFailed", str(error))
            Trace.log(str(error), name="door.err")
            self.set_status(ScriptStatus.FAILED)
            return
        try:
            self.publisher = DoorStatePublisher(self.args)
            self.publisher.publish(DoorPhase.VALIDATING)
            self.queue = ActionTask(mod="door")
            self.queue.build(build_actions(self.args, self.protocol, self.publisher))
            self.set_status(ScriptStatus.RUNNING)
        except (KeyError, TypeError, ValueError) as error:
            Navigation.setTaskError("DoorConfigError", str(error))
            Trace.log(str(error), name="door.err")
            self.set_status(ScriptStatus.FAILED)
        except Exception as error:
            Navigation.setTaskError("DoorActionFailed", str(error))
            Trace.log(str(error), name="door.err")
            self.set_status(ScriptStatus.FAILED)

    def _fail_queue(self):
        failed = next(
            action for action in self.queue.action_list
            if action.action_status == ActionStatus.FAILED
        )
        Navigation.setTaskError(
            failed.error_code or "DoorActionFailed",
            failed.fail_reason or "door action failed",
        )
        self._start_safety_holding()
        if self.safety_holding is None and self.publisher is not None:
            self.publisher.publish(DoorPhase.FAILED)
        self.set_status(ScriptStatus.FAILED)

    def _start_safety_holding(self):
        if self.queue is None or self.safety_holding is not None:
            return
        lease = next(
            (getattr(action, "lease", None) for action in self.queue.action_list
             if getattr(action, "lease", None) is not None),
            None,
        )
        if (lease is not None and lease.acquired
                and lease.car_position != DoorCarPosition.OUTSIDE):
            self.safety_holding = DoorSafetyHolding(
                lease, ConfigParams.status_poll_interval, self.publisher
            )
            Trace.log({"event": "doorSafetyHoldingStarted",
                       "carPosition": lease.car_position.value}, name="door.safety")

    def tick_safety(self):
        if self.safety_holding is not None and self.safety_holding.step():
            self.safety_holding = None

    def run(self):
        if self.queue is None:
            return
        if self.queue.is_suspended:
            self.queue.resume()
        self.queue.step(self)
        if self.queue.status == ActionStatus.FAILED:
            self._fail_queue()
        elif self.queue.status == ActionStatus.FINISHED:
            if self.publisher is not None and not self.publisher.publish(DoorPhase.FINISHED):
                Navigation.setTaskError(
                    "DoorResultUnavailable",
                    str(self.publisher.last_error or "failed to publish final door state"),
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
            self.set_status(ScriptStatus.SUSPENDED)

    def resume(self):
        if self.queue is not None and self.status == ScriptStatus.SUSPENDED:
            self.queue.resume()
            self.set_status(ScriptStatus.RUNNING)

    def cancel(self):
        if self.queue is not None and not self.queue.is_done:
            self.queue.cancel("module stopped")
        self._start_safety_holding()
        if self.safety_holding is None and self.publisher is not None:
            self.publisher.publish(DoorPhase.FAILED)
        self.set_status(ScriptStatus.FAILED)

    def reset(self):
        if self.safety_holding is not None:
            return False
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
    module = DoorModule()
    while True:
        if module.safety_holding is not None:
            Module.setStatus(ScriptStatus.FAILED)
            module.tick_safety()
            time.sleep(0.05)
            continue
        Module.setStatus(module.status)
        status = module.status
        if status == ScriptStatus.NONE:
            args = Module.getTaskArgs()
            if args:
                try:
                    module.init_args(script_param.loadInput(args))
                except ValueError as error:
                    Navigation.setTaskError("DoorInputParamError", str(error))
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
