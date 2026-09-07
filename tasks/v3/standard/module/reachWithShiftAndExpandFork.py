# -*- coding: utf-8 -*-

from syspy import Di, Distance, Motor, Navigation, Trace, _TR
from syspy.utils.param_server import ParamType

from standard.fork import ConfigParams, ReachFork
from standard.fork_utils import (
    ActionStatus,
    GoPathWithContactDi,
    RunReachMotorsByPosition,
    RunMotorByPosition,
    clamp,
    get_r_loc,
    pos2Base,
    pos2World,
)


DISTANCE_SENSOR_BLOCK_ERROR = "PalletBackDistanceInsufficient"


def _reach_expand_config_builder(config_cls, builder):
    with builder.GROUP(
            key="reachExpandScene",
            name=_TR("Reach Expand"),
            desc=_TR("Reach expand scene settings"),
    ):
        builder.TYPE(ParamType.ARRAY)
        with builder.CHILDREN():
            with builder.CHILD(
                    key="reachObsStopCompensationEnabled",
                    name=_TR("Reach Obs Compensation"),
                    desc=_TR("Add reach extension distance to obstacle stop distance after reach motors extend"),
            ):
                builder.TYPE(ParamType.BOOL)
                builder.DEFAULTVALUE(False)


def _reach_expand_config_reload(config_cls, cfg):
    config_cls.reachObsStopCompensationEnabled = config_cls._safe_bool(
        config_cls._find_config_value(["reachObsStopCompensationEnabled"], cfg),
        False,
    )


def _expand_operation_input(_input_cls, builder, _min_height, _max_height):
    # 基类在“单 expand 电机”时会自动注册 operation=expand；
    # 这里兜住“模型里仍存在多项 expand 配置，但本车型按单逻辑 expand 使用”的场景，
    # 避免 operation 输入参数消失。
    if not ConfigParams.expand_motor_name or len(ConfigParams.expand_motor_items) <= 1:
        return
    with builder.CHILD(key="expand", name=_TR("Expand Motor"), desc=_TR("Expand motor jog or move")):
        builder.TYPE(ParamType.ARRAY)
        with builder.CHILDREN():
            with builder.CHILD(key="jogStep", name=_TR("Jog Step"), desc=_TR("Jog step for expand motor")):
                builder.TYPE(ParamType.FLOAT)
                builder.UNIT("m")
                builder.SINGLESTEP(0.01)
                builder.DEFAULTVALUE(0.1)
            with builder.CHILD(key="position", name=_TR("Position"), desc=_TR("Target position for expand motor")):
                builder.TYPE(ParamType.FLOAT)
                builder.UNIT("m")
                builder.SINGLESTEP(0.01)
                builder.DEFAULTVALUE(-1)


class ReachExpandGoPathWithContactDi(GoPathWithContactDi):
    """前移开合车型的近场路径包装。

    该车型没有可用于近场阻挡的叉尖 2D 激光，叉根 3D 激光又跟随前移机构运动，
    因此前移取货时额外用 forkTipDistanceSensors 做一次进叉前距离校验。
    """

    def __init__(
            self,
            contact_dis,
            world_pos,
            obs_dist,
            method,
            args,
            check_di=True,
            operation_type="",
            reach_phase_config=None,
            obs_dist_compensation: float = 0.0,
            distance_check_length: float = 0.0,
    ):
        super().__init__(
            contact_dis,
            world_pos,
            obs_dist,
            method,
            args,
            check_di=check_di,
            operation_type=operation_type,
            reach_phase_config=reach_phase_config,
            obs_dist_compensation=obs_dist_compensation,
        )
        self.distance_check_length = max(0.0, float(distance_check_length or 0.0))
        self.distance_check_enabled = (
            self.operation_type == "load"
            and self.method == "bezier"
            and self.distance_check_length > 1e-6
        )
        self.distance_check_started = not self.distance_check_enabled
        self.distance_check_done = not self.distance_check_enabled
        self.distance_check_aligned = not self.distance_check_enabled
        self.distance_check_align_long_thresh = ConfigParams.tail
        self.distance_sensor_device_keys = []
        self.latest_distance_sensor_dist = None
        self.distance_sensor_no_data_logged = False
        self.distance_check_skip_continuous_once = False
        self.distance_sensor_blocked = False
        if self.distance_check_enabled:
            Trace.log(
                f"enable reach distance check, motion target:{self.motion_target}, "
                f"check_length:{self.distance_check_length}",
                name="fork.task",
            )

    def _load_distance_sensor_config(self) -> bool:
        if Distance is None:
            Navigation.setTaskError("DistanceSensorUnavailable", "distance sensor api is unavailable")
            self.action_status = ActionStatus.FAILED
            return False
        sensor_keys = [
            str(sensor_key).strip()
            for sensor_key in (ConfigParams.fork_tip_distance_sensors or [])
            if str(sensor_key).strip()
        ]
        if not sensor_keys:
            Navigation.setTaskError("DistanceSensorNotConfigured", "fork_tip_distance_sensors is not configured")
            self.action_status = ActionStatus.FAILED
            return False
        self.distance_sensor_device_keys = sensor_keys
        return True

    def _read_distance_sensor_dist(self):
        if Distance is None:
            return None
        try:
            data = Distance.getData(["node"])
        except Exception as exc:
            Trace.log(f"read distance sensor failed: {exc}", name="fork.task")
            return None

        nodes = data.get("node", []) if isinstance(data, dict) else []
        if not isinstance(nodes, list):
            return None

        matched_distances = []
        for node in nodes:
            if not isinstance(node, dict):
                continue
            node_key = str(node.get("key") or node.get("name") or "").strip()
            if node_key not in self.distance_sensor_device_keys:
                continue
            if not bool(node.get("valid", False)):
                continue
            try:
                dist = float(node.get("dist"))
            except (TypeError, ValueError):
                continue
            Trace.log(f"distance sensor raw: key={node_key}, dist={dist}", name="fork.task")
            if dist <= 0.0:
                continue
            matched_distances.append(dist)
        if not matched_distances:
            return None
        return min(matched_distances)

    def _is_distance_check_aligned(self) -> bool:
        offset = pos2Base(get_r_loc(), self.target_pos)
        return offset[0] <= self.distance_check_align_long_thresh

    def _report_distance_sensor_blocked(self, dist: float, source: str) -> bool:
        if not self.distance_sensor_blocked:
            self.stop_robot()
            Trace.log(
                f"{source}: distance sensor blocked, dist={dist}, "
                f"check_length={self.distance_check_length}",
                name="fork.err",
            )
        if not Navigation.errorExists(DISTANCE_SENSOR_BLOCK_ERROR):
            Navigation.setTaskError(
                DISTANCE_SENSOR_BLOCK_ERROR,
                f"{source}: distance sensor {self.distance_sensor_device_keys} dist={dist:.3f}m < "
                f"check_length={self.distance_check_length:.3f}m",
            )
        self.distance_sensor_blocked = True
        return False

    def _clear_distance_sensor_blocked(self, source: str) -> None:
        if not self.distance_sensor_blocked:
            return
        if Navigation.errorExists(DISTANCE_SENSOR_BLOCK_ERROR):
            Navigation.clearTaskError(DISTANCE_SENSOR_BLOCK_ERROR)
        Navigation.goPathParam(dict())
        self.distance_sensor_blocked = False
        Trace.log(f"{source}: distance sensor recovered, resume path", name="fork.task")

    def _check_distance_sensor_once(self, source: str, *, allow_no_data_pass: bool) -> bool:
        if not self.distance_sensor_device_keys and not self._load_distance_sensor_config():
            return False

        dist = self._read_distance_sensor_dist()
        if dist is None:
            if not self.distance_sensor_no_data_logged:
                Trace.log(
                    f"{source}: distance sensor no valid data, sensors={self.distance_sensor_device_keys}",
                    name="fork.task",
                )
                self.distance_sensor_no_data_logged = True
            return allow_no_data_pass

        self.distance_sensor_no_data_logged = False
        self.latest_distance_sensor_dist = dist
        Trace.log(
            f"{source}: distance sensor read, sensors={self.distance_sensor_device_keys}, "
            f"dist={dist}, check_length={self.distance_check_length}",
            name="fork.task",
        )
        if dist < self.distance_check_length:
            return self._report_distance_sensor_blocked(dist, source)
        self._clear_distance_sensor_blocked(source)
        return True

    def _begin_distance_sensor_check(self, source: str) -> bool:
        if self.distance_check_started:
            return True
        self.distance_check_started = True
        self.distance_check_aligned = True
        Trace.log(
            f"{source}: start distance sensor monitoring before inserting",
            name="fork.task",
        )
        if not self._check_distance_sensor_once(source, allow_no_data_pass=True):
            return False
        self.distance_check_skip_continuous_once = True
        return True

    def _poll_distance_sensor_during_motion(self, source: str) -> bool:
        if not self.distance_check_enabled or self.distance_check_done:
            return False
        if not self.distance_check_started and not self._begin_distance_sensor_check(source):
            return True

        back_action = getattr(self, "back_action", None)
        if back_action is None:
            return False

        if self.distance_check_skip_continuous_once:
            self.distance_check_skip_continuous_once = False
        elif back_action.action_status not in [ActionStatus.FAILED, ActionStatus.FINISHED]:
            if not self._check_distance_sensor_once(source, allow_no_data_pass=True):
                return True

        if back_action.action_status == ActionStatus.FINISHED:
            self.distance_check_done = True
        return False

    def _initialize_motion(self) -> None:
        super()._initialize_motion()
        if not self.distance_check_enabled or self.reach_phase_enabled:
            return
        if self._begin_distance_sensor_check("distance sensor startup check"):
            return

    def _handle_contact_di_fallback(self) -> bool:
        if not self.check_di:
            return False
        self.di_status = [Di.getDi(d) for d in self.contact_di]
        if not any(self.di_status):
            return False
        Trace.log(
            f"contact di fallback triggered during distance check, di_status:{self.di_status}",
            name="fork.task",
        )
        if self.stop_robot():
            self.action_status = ActionStatus.FINISHED
            return True
        return False

    def _handle_motion_extensions(self) -> bool:
        if self.reach_phase_enabled:
            if self.reach_phase == "align_path":
                if self._is_reach_aligned_by_geometry():
                    self._transition_align_to_reach("geometry threshold")
                    return True
                if self.back_action.action_status == ActionStatus.FINISHED:
                    self._transition_align_to_reach("align path finished")
                    return True
            if (
                    self.reach_phase == "reach"
                    and self.reach_action is not None
                    and self.reach_action.action_status == ActionStatus.FINISHED
            ):
                if self.distance_check_enabled and not self.distance_check_done:
                    if not self._begin_distance_sensor_check("distance sensor before final insert"):
                        return True
                self._start_final_path()
                return True
            if self.reach_phase == "final_path":
                return self._poll_distance_sensor_during_motion("distance sensor continuous")

        if not self.distance_check_enabled or self.distance_check_done or self.reach_phase_enabled:
            return False

        if self._poll_distance_sensor_during_motion("distance sensor continuous"):
            return True

        if self._handle_contact_di_fallback():
            return True

        return False

    def _handle_contact_di_completion(self) -> None:
        if self.distance_check_enabled and not self.distance_check_done:
            return
        super()._handle_contact_di_completion()

    def _trace_extra_state(self):
        state = dict(super()._trace_extra_state())
        state.update({
            "distance_check_enabled": self.distance_check_enabled,
            "distance_check_started": self.distance_check_started,
            "distance_check_done": self.distance_check_done,
            "distance_check_aligned": self.distance_check_aligned,
            "distance_sensor_blocked": self.distance_sensor_blocked,
            "latest_distance_sensor_dist": self.latest_distance_sensor_dist or 0.0,
        })
        return state

    def _build_reach_phase_action(self):
        if not self.reach_motor_names:
            Navigation.setTaskError("ReachMotorMissing", "reach motor is not configured for staged pathFirst")
            self.action_status = ActionStatus.FAILED
            return None
        return ReachExpandRunReachMotorsByPosition(
            self.reach_motor_names,
            self.reach_target,
            self.reach_max_speed,
            self.reach_sync_tolerance,
            contact_di=[],
            check_all_di=False,
            action_name="extendReachMotors",
            distance_check_length=self.distance_check_length,
        )


class ReachExpandRunReachMotorsByPosition(RunReachMotorsByPosition):
    """取货伸叉动作内联距离传感器检测。"""

    def __init__(
            self,
            motor_names,
            target="max",
            max_speed=0.1,
            sync_tolerance=0.02,
            contact_di=None,
            check_all_di=False,
            action_name="RunReachMotors",
            distance_check_length: float = 0.0,
    ):
        super().__init__(
            motor_names,
            target=target,
            max_speed=max_speed,
            sync_tolerance=sync_tolerance,
            contact_di=contact_di,
            check_all_di=check_all_di,
            action_name=action_name,
        )
        self.distance_check_length = max(0.0, float(distance_check_length or 0.0))
        self.distance_check_enabled = self.distance_check_length > 1e-6
        self.distance_sensor_device_keys = []
        self.latest_distance_sensor_dist = None
        self.distance_sensor_no_data_logged = False
        self.distance_sensor_blocked = False
        if self.distance_check_enabled:
            Trace.log(
                f"enable reach motor distance check, motors:{self.motor_names}, "
                f"check_length:{self.distance_check_length}",
                name="fork.task",
            )

    def _load_distance_sensor_config(self) -> bool:
        if Distance is None:
            Navigation.setTaskError("DistanceSensorUnavailable", "distance sensor api is unavailable")
            self.action_status = ActionStatus.FAILED
            return False
        sensor_keys = [
            str(sensor_key).strip()
            for sensor_key in (ConfigParams.fork_tip_distance_sensors or [])
            if str(sensor_key).strip()
        ]
        if not sensor_keys:
            Navigation.setTaskError("DistanceSensorNotConfigured", "fork_tip_distance_sensors is not configured")
            self.action_status = ActionStatus.FAILED
            return False
        self.distance_sensor_device_keys = sensor_keys
        return True

    def _read_distance_sensor_dist(self):
        if Distance is None:
            return None
        try:
            data = Distance.getData(["node"])
        except Exception as exc:
            Trace.log(f"read reach motor distance sensor failed: {exc}", name="fork.task")
            return None

        nodes = data.get("node", []) if isinstance(data, dict) else []
        if not isinstance(nodes, list):
            return None

        matched_distances = []
        for node in nodes:
            if not isinstance(node, dict):
                continue
            node_key = str(node.get("key") or node.get("name") or "").strip()
            if node_key not in self.distance_sensor_device_keys:
                continue
            if not bool(node.get("valid", False)):
                continue
            try:
                dist = float(node.get("dist"))
            except (TypeError, ValueError):
                continue
            Trace.log(f"distance sensor raw: key={node_key}, dist={dist}", name="fork.task")
            if dist <= 0.0:
                continue
            matched_distances.append(dist)
        if not matched_distances:
            return None
        return min(matched_distances)

    def _report_distance_sensor_blocked(self, dist: float, source: str) -> bool:
        if not self.distance_sensor_blocked:
            self._stop_all()
            Trace.log(
                f"{source}: reach motor distance sensor blocked, dist={dist}, "
                f"check_length={self.distance_check_length}",
                name="fork.err",
            )
        if not Navigation.errorExists(DISTANCE_SENSOR_BLOCK_ERROR):
            Navigation.setTaskError(
                DISTANCE_SENSOR_BLOCK_ERROR,
                f"{source}: distance sensor {self.distance_sensor_device_keys} dist={dist:.3f}m < "
                f"check_length={self.distance_check_length:.3f}m",
            )
        self.distance_sensor_blocked = True
        return False

    def _clear_distance_sensor_blocked(self, source: str) -> None:
        if not self.distance_sensor_blocked:
            return
        if Navigation.errorExists(DISTANCE_SENSOR_BLOCK_ERROR):
            Navigation.clearTaskError(DISTANCE_SENSOR_BLOCK_ERROR)
        self.distance_sensor_blocked = False
        if self.init:
            self._start_all()
        Trace.log(f"{source}: distance sensor recovered, resume reach motors", name="fork.task")

    def _check_distance_sensor_once(self, source: str, *, allow_no_data_pass: bool) -> bool:
        if not self.distance_sensor_device_keys and not self._load_distance_sensor_config():
            return False

        dist = self._read_distance_sensor_dist()
        if dist is None:
            if not self.distance_sensor_no_data_logged:
                Trace.log(
                    f"{source}: distance sensor no valid data, sensors={self.distance_sensor_device_keys}",
                    name="fork.task",
                )
                self.distance_sensor_no_data_logged = True
            return allow_no_data_pass

        self.distance_sensor_no_data_logged = False
        self.latest_distance_sensor_dist = dist
        Trace.log(
            f"{source}: distance sensor read, sensors={self.distance_sensor_device_keys}, "
            f"dist={dist}, check_length={self.distance_check_length}",
            name="fork.task",
        )
        if dist < self.distance_check_length:
            return self._report_distance_sensor_blocked(dist, source)
        self._clear_distance_sensor_blocked(source)
        return True

    def run(self, ctx=None):
        if self.action_status in (ActionStatus.FINISHED, ActionStatus.FAILED):
            return
        if self.distance_check_enabled:
            source = "reach motor startup check" if not self.init else "reach motor continuous"
            if not self._check_distance_sensor_once(source, allow_no_data_pass=True):
                return

        super().run(ctx)

    def _trace_state(self):
        state = dict(super()._trace_state())
        state.update({
            "distance_check_enabled": self.distance_check_enabled,
            "distance_check_length": self.distance_check_length,
            "distance_sensor_blocked": self.distance_sensor_blocked,
            "latest_distance_sensor_dist": self.latest_distance_sensor_dist or 0.0,
        })
        return state


class ReachWithShiftAndExpandFork(ReachFork):
    """前移+开合车型。

    该车型的设备模型只配置一个 expand 逻辑电机，由底层同时联动两侧开合机构，
    因此这里不再区分 left / right，也不再额外注册左右独立的 operation 输入。
    """
    config_builder_hook = staticmethod(_reach_expand_config_builder)
    config_reload_hook = staticmethod(_reach_expand_config_reload)
    operation_input_hook = staticmethod(_expand_operation_input)

    @staticmethod
    def _get_expand_motor_key():
        for motor_name in ConfigParams.expand_motor_names:
            if str(motor_name).strip():
                return str(motor_name).strip()
        return str(ConfigParams.expand_motor_name or "").strip()

    def _resolve_motor_info(self, motor_type):
        if motor_type == "expand":
            motor_key = self._get_expand_motor_key()
            if not motor_key:
                return None
            min_length, max_length = ConfigParams._get_motor_limits(motor_key)
            return {
                "type": "expand",
                "motorKey": motor_key,
                "minLength": min_length,
                "maxLength": max_length,
            }
        return super()._resolve_motor_info(motor_type)

    @staticmethod
    def _resolve_expand_target_position(rec_action, motor_key):
        hole_positions = getattr(rec_action, "hole_positions", None) or []
        hole_offsets = []
        for hole in hole_positions:
            try:
                hole_y = abs(float(hole.get("holeY", 0.0) or 0.0))
            except (TypeError, ValueError):
                continue
            if hole_y > 0:
                hole_offsets.append(hole_y)

        if not hole_offsets:
            return float(Motor.getMotorPos(motor_key))

        return sum(hole_offsets)

    def _build_expand_motor_action(self, rec_action):
        if not getattr(rec_action, "hole_positions", None):
            return None

        motor_key = self._get_expand_motor_key()
        if not motor_key:
            return None

        target_pos = self._resolve_expand_target_position(rec_action, motor_key)
        Trace.log(
            f"Expand motor target: motor={motor_key}, target={target_pos:.4f}, "
            f"hole_positions={getattr(rec_action, 'hole_positions', [])}",
            name="fork.task",
        )
        return RunMotorByPosition(
            motor_key,
            target_pos,
            0.1,
            action_name="RunExpandMotor",
        )

    def _reach_obs_stop_compensation(self):
        if not getattr(ConfigParams, "reachObsStopCompensationEnabled", False):
            return 0.0
        return self._reach_extension_distance()

    def _build_unload_reach_path_target(self, target_pos):
        # 放货要在 AP 点前一个前移长度停车，保证释放后货物回到取货前的同一位置。
        return pos2World([self._reach_extension_distance(), 0.0, 0.0], target_pos)

    def _build_unload_reach_plan(self, method, args):
        adjusted = dict(args or {})
        adjusted["back_dist"] = -self._reach_extension_distance()
        return method, adjusted

    def _build_reach_action(self, target, *, stop_on_contact=False, action_name="RunReachMotors"):
        if target == "max" and action_name == "extendReachMotors":
            return ReachExpandRunReachMotorsByPosition(
                ConfigParams.reach_motor_names,
                target,
                ConfigParams.reachMotorMaxSpeed,
                ConfigParams.reachMotorSyncTolerance,
                contact_di=ConfigParams.contact_ids if stop_on_contact else [],
                check_all_di=ConfigParams.checkAllContactDis,
                action_name=action_name,
                distance_check_length=ConfigParams.loadObsStopDist,
            )
        return super()._build_reach_action(target, stop_on_contact=stop_on_contact, action_name=action_name)

    def _build_reach_unload_prefix(self):
        actions = [super()._build_reach_action("max", action_name="extendReachMotors")]
        actions.append(self._build_unload_prepare_lift_action(self.start_height))
        return actions

    def _build_reach_path_action(
            self,
            target_pos,
            method,
            args,
            *,
            operation_type,
            check_di,
    ):
        path_target = target_pos
        if operation_type == "unload":
            path_method, path_args = self._build_unload_reach_plan(method, args)
        else:
            path_method, path_args = self._reach_adjusted_plan(method, args)
        if path_method == "goPath":
            if operation_type == "unload":
                path_target = self._build_unload_reach_path_target(target_pos)
            else:
                path_target = self._shift_path_target_for_reach(target_pos)
        return ReachExpandGoPathWithContactDi(
            ConfigParams.contact_ids,
            path_target,
            ConfigParams.loadObsStopDist if operation_type == "load" else None,
            path_method,
            path_args,
            check_di,
            operation_type,
            obs_dist_compensation=self._reach_obs_stop_compensation(),
            distance_check_length=ConfigParams.loadObsStopDist if operation_type == "load" else 0.0,
        )

    def _build_path_first_load_actions(self, rec_world_pos, method, args):
        reach_distance = self._reach_extension_distance()
        front_dist = ConfigParams.minAheadDist + reach_distance
        if method == "goPath":
            align_world_pos = self._shift_path_target_for_reach(rec_world_pos, front_dist)
            align_method = "goPath"
            align_args = {}
        else:
            align_world_pos = rec_world_pos
            align_method = method
            align_args = dict(args or {})
            align_args["back_dist"] = front_dist
            align_args["min_ahead_dist"] = front_dist
        final_target = pos2World(
            [reach_distance - float(self.back_dist), 0.0, 0.0],
            rec_world_pos,
        )
        return [
            ReachExpandGoPathWithContactDi(
                ConfigParams.contact_ids,
                align_world_pos,
                ConfigParams.loadObsStopDist - reach_distance,
                align_method,
                align_args,
                self.check_di,
                "load",
                reach_phase_config={
                    "align_world_pos": align_world_pos,
                    "align_method": align_method,
                    "align_args": align_args,
                    "final_world_pos": final_target,
                    "final_back_mode": 1,
                    "final_obs_dist_compensation": 0.0,
                    "motor_names": ConfigParams.reach_motor_names,
                    "target": "max",
                    "max_speed": ConfigParams.reachMotorMaxSpeed,
                    "sync_tolerance": ConfigParams.reachMotorSyncTolerance,
                },
                distance_check_length=ConfigParams.loadObsStopDist,
            ),
        ]

    def _build_load_entry_batch(self, rec_action):
        # 取货识别进入批：先保证前移电机在 0 位（缩回），若不在识别前先补一个缩回到 0 位的动作，
        # 避免前移伸出状态下识别导致识别点相对车体偏移。
        actions = list(super()._build_load_entry_batch(rec_action))
        if not self._reach_motors_at_zero():
            actions.insert(0, self._build_reach_action("min", action_name="retractReachMotors"))
        return actions

    def _reach_motors_at_zero(self):
        for name in ConfigParams.reach_motor_names:
            try:
                current = Motor.getMotorPos(name)
                limits = ConfigParams._get_motor_limits(name)
            except Exception:
                return False
            if abs(current - float(limits[0])) > 0.005:
                return False
        return True


robot = ReachWithShiftAndExpandFork(__file__)


if __name__ == "__main__":
    robot.main()
