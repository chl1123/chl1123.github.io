# -*- coding: utf-8 -*-
import copy
import json
import math
import struct
import time
from typing import Any, Dict, List, Optional

from syspy import Container, Di, Do, Laser, Motor, Navigation, Loc, NavSpeed, Recognize, RobotError, RobotParam, ScriptStatus, Trace, _TR
from syspy.utils import Coordinate
from syspy.utils.time import Timer
from syspy.script_data import ScriptData
from syspy.utils.param_server import BindType, ParamBuilder, ParamType
from syspy.lib.action_task import ActionBase, ActionStatus as TaskActionStatus, ActionTask
from syspy.lib.module import pos2Base, pos2World
import standard.goBezier as GoBezier
from standard.goPath import GoPath


MOD = "fork"
_CONFIG = None
EPS = 1e-6
ActionStatus = TaskActionStatus
MOTOR_ACTION_ERROR_KEY = "ms@MotorAction"
MOTOR_LIMIT_OPERATIONS = {"forkHeight", "lift", "shift", "pitch", "reach", "expand"}


def bind_runtime(config_cls):
    global _CONFIG
    _CONFIG = config_cls


def _config():
    if _CONFIG is None:
        raise RuntimeError("fork utils runtime is not initialized")
    return _CONFIG


def _trace_log(text: str, *, name: str = f"{MOD}.action") -> None:
    Trace.log(str(text), name=name)


def get_weight_can_config(can_device):
    """Resolve a configured CAN device to the channel/bitrate expected by the scale driver."""
    can_port = str(RobotParam.getDevice(can_device, "canPort") or "").lower()
    channel = {"port1": "can0", "port2": "can1"}.get(can_port, "")
    baudrate = str(RobotParam.getDevice(can_device, "baudrate") or "").upper()
    return (
        channel,
        int(baudrate[:-1]) * 1000
        if baudrate.endswith("K") and baudrate[:-1].isdigit()
        else 0
    )


def add_weight_config(builder):
    with builder.GROUP(
        key="weight",
        name=_TR("Weight Settings"),
        desc=_TR("Goods weight configuration"),
    ):
        builder.TYPE(ParamType.ARRAY)
        with builder.CHILDREN():
            with builder.CHILD(
                key="weightCan",
                name=_TR("Weight CAN"),
                desc=_TR("CAN device connected to the weight scale"),
            ):
                builder.TYPE(ParamType.BIND_TYPE)
                builder.BINDTYPE(BindType.Device.CAN)
            for key, name, default, param_type in (
                ("weightNodeId", "CAN Node ID", 0x0A, ParamType.INT),
                ("weightSampleCount", "Sample Count", 3, ParamType.INT),
                ("weightSampleInterval", "Sample Interval", 0.1, ParamType.FLOAT),
                ("maxWeight", "Max Weight", 1000.0, ParamType.FLOAT),
            ):
                with builder.CHILD(key=key, name=_TR(name), desc=_TR(name)):
                    builder.TYPE(param_type)
                    builder.DEFAULTVALUE(default)


def add_weight_input(builder):
    with builder.CHILD(
        key="weightGood",
        name=_TR("Goods Weight"),
        desc=_TR("Measure goods weight"),
    ):
        builder.TYPE(ParamType.ARRAY)


def build_weight_action(config):
    channel, bitrate = get_weight_can_config(getattr(config, "weightCan", ""))
    return WeightCheckAction(
        protocol="ruibot",
        scale_options={
            "channel": channel,
            "bitrate": bitrate,
            "node_id": getattr(config, "weightNodeId", 0x0A),
        },
        max_weight=getattr(config, "maxWeight", 1000.0),
        sample_count=getattr(config, "weightSampleCount", 3),
        sample_interval=getattr(config, "weightSampleInterval", 0.1),
        action_name="weightGood",
    )


def check_motor_action_error(action, operation, module_motors) -> bool:
    """仅允许单电机反向动作清除 MF 的限位错误。"""
    try:
        exists = RobotError.existSystemError(MOTOR_ACTION_ERROR_KEY)
    except Exception as exc:
        Trace.log(f"read system error {MOTOR_ACTION_ERROR_KEY} failed: {exc}", name=f"{MOD}.err")
        return False
    if not exists:
        return False

    triggered = []
    for motor in module_motors:
        motor_key = motor.get("motorKey", "")
        for direction in ("up", "down"):
            di = motor.get(f"{direction}LimitDi", "")
            if not di:
                continue
            try:
                if Di.getDi(di):
                    triggered.append((motor_key, direction, di))
            except Exception as exc:
                Trace.log(
                    f"read limit DI failed motor={motor_key}, di={di}: {exc}",
                    name=f"{MOD}.err",
                )

    motor_key = getattr(action, "motor_name", "")
    delta = getattr(action, "delta", None)
    action_direction = "up" if delta is not None and delta > EPS else (
        "down" if delta is not None and delta < -EPS else ""
    )
    matched = [item for item in triggered if not motor_key or item[0] == motor_key]
    details = ", ".join(
        f"motor={key}, {direction}LimitDi={di}" for key, direction, di in matched
    )
    if operation in MOTOR_LIMIT_OPERATIONS and matched and action_direction and all(
            direction != action_direction for _, direction, _ in matched):
        try:
            RobotError.clearSystemError(MOTOR_ACTION_ERROR_KEY)
            Trace.log(
                f"clear MF {MOTOR_ACTION_ERROR_KEY} before reverse action: {details}",
                name=f"{MOD}.motor",
            )
            return False
        except Exception as exc:
            Trace.log(f"clear MF {MOTOR_ACTION_ERROR_KEY} failed: {exc}", name=f"{MOD}.err")

    if not details:
        details = ", ".join(
            f"unmatched motor={key}, {direction}LimitDi={di}"
            for key, direction, di in triggered
        ) or "no active limit DI identified"
    error_desc = (
        f"MF {MOTOR_ACTION_ERROR_KEY} in operation={operation or 'unknown'} "
        f"for motor={motor_key or 'unknown'}; {details}"
    )
    Trace.log(error_desc, name=f"{MOD}.err")
    action.fail_reason = error_desc
    action.action_status = ActionStatus.FAILED
    return True


# ============================================================================
# 基础通用工具
# ============================================================================
def get_r_loc():
    r_loc = Loc.getPose()
    return [r_loc["x"], r_loc["y"], math.radians(r_loc["yaw"])]


def cal_dist(first_loc, second_loc):
    cur_dist = math.sqrt(
        (first_loc[0] - second_loc[0]) ** 2 + (first_loc[1] - second_loc[1]) ** 2)
    return cur_dist


def clamp(val, lo, hi):
    return max(lo, min(val, hi))


def has_valid_target_pos(target_pos) -> bool:
    return bool(target_pos) and len(target_pos) > 3 and target_pos[3] != -1


def is_enabled(value) -> bool:
    if isinstance(value, str):
        return value.lower() in ("on", "true", "1")
    return bool(value)


def is_do_motor_key(motor_name) -> bool:
    """兼容设备模型中 DOMotor/DoMotor 两种历史大小写。"""
    return str(motor_name or "").lower().startswith("domotor")


def get_motor_limit_di(motor_name, direction, fallback_motor_func=""):
    if not motor_name or is_do_motor_key(motor_name):
        return ""
    motor_func = RobotParam.getDevice(motor_name, "func") or fallback_motor_func
    if not motor_func:
        return ""
    names = ("upLimitDI", "upLimitDi", "UpLimitDI") if direction == "up" else (
        "DownLimitDI", "downLimitDI", "downLimitDi", "DownLimitDi"
    )
    for name in names:
        value = RobotParam.getDevice(motor_name, f"func.{motor_func}.{name}")
        if value:
            return str(value)
    return ""


def normalize_motor_operation(motor_type):
    if motor_type in ("expand_left", "expand_right"):
        return "expand", motor_type.split("_", 1)[1]
    return motor_type, ""


def apply_tcp_target(target_pos, tcp_name, *, enabled=True, log_name="fork.task"):
    if not enabled or not tcp_name:
        return target_pos

    tcp_target = Navigation.calTCPTrans(target_pos[0], target_pos[1], target_pos[2], tcp_name)
    tcp_target_pos = [tcp_target["x"], tcp_target["y"], tcp_target["theta"]]
    Trace.log(f"ap world tcp :{tcp_target_pos}", name=log_name)
    return tcp_target_pos


def build_path_adjust_plan(*, back_dist, min_ahead_dist, adjust_dist, enabled=True):
    if not enabled:
        return "goPath", {}
    cfg = _config()
    args = {
        "back_dist": back_dist,
        "min_ahead_dist": min_ahead_dist,
        "adjust_dist": adjust_dist,
    }
    method = cfg.pathAdjustMode
    if method == "straightLine":
        args["max_angle"] = cfg.maxAngle
    elif method == "bezier":
        args["max_curve"] = cfg.maxCurve
    return method, args


def build_return_path_action(fallback_args, *, allow_same_path_return=False):
    cfg = _config()
    if allow_same_path_return and cfg.returnOnSamePath:
        if cfg.pathAdjustMode == "bezier":
            return GoBezier.GoBezierWorldReturn(False)
        if cfg.pathAdjustMode == "straightLine":
            return GoTwoStraightLine(0, 0, 0, 0, 0, 0, 0, True)
    return GoPath(fallback_args)


def resolve_rec_center_to_robot(target_pos, r_loc):
    if not has_valid_target_pos(target_pos):
        rec_center2robot = [_config().recCenterX, _config().recCenterY]
    else:
        target2robot = pos2Base(target_pos, r_loc)
        rec_center2robot = pos2World([_config().module_x, 0, 0], target2robot)
    Trace.log(f"rec center to robot :{rec_center2robot}", output_console=True, output_time=True, name="fork.task")
    return rec_center2robot


def resolve_back_dist(rec_info):
    if not is_enabled(rec_info.get("enableBackDistance", "off")):
        return _config().module_x
    return rec_info.get("backDistance")


def apply_default_navigation_policy():
    Navigation.appendCustomPolicy("policy", {"navigation.freeBypass": "off"})


def enable_falling_down_detect(ctx) -> bool:
    cfg = _config()
    if (
            ctx.opt not in ("load", "unload")
            or not cfg.enableFallingDownDetect
            or cfg.module_type in ("pickFork", "liftFork", "singleFork")
            or getattr(ctx, "_falling_down_detect_enabled", False)
    ):
        return True

    try:
        enabled = bool(Navigation.enableFallingDownDetect())
    except Exception as exc:
        Trace.log(f"enable FallingDown detect failed: {exc}", name=f"{MOD}.err")
        enabled = False

    if not enabled:
        Navigation.setTaskError("FallingDownNotReady", "FallingDown detector is not ready")
        ctx.set_status(ScriptStatus.FAILED)
        return False

    ctx._falling_down_detect_enabled = True
    Trace.log("FallingDown detect enabled", name=f"{MOD}.task")
    return True


def disable_falling_down_detect(ctx) -> None:
    if not getattr(ctx, "_falling_down_detect_enabled", False):
        return

    try:
        if not Navigation.disableFallingDownDetect():
            Trace.log("disable FallingDown detect returned false", name=f"{MOD}.err")
    except Exception as exc:
        Trace.log(f"disable FallingDown detect failed: {exc}", name=f"{MOD}.err")
    finally:
        ctx._falling_down_detect_enabled = False


def clear_goods_shape_when_lift_fork_low(ctx, fork_height, cfg):
    if (fork_height - cfg.min_height) <= EPS and Navigation.hasGoods():
        Navigation.clearGoodsShape()


def update_back_laser_clear_region_by_height(ctx, fork_height, cfg):
    if not cfg.fork_root_2D_lasers:
        return

    if fork_height <= cfg.backLaserEnableHeight and not ctx.set_fork_region_by_height:
        ctx.set_fork_region_by_height = True
        ctx.clear_fork_region_by_height = False
        Navigation.setClearRegion(
            ctx.chassis_clear_region,
            [p["x"] for p in cfg.chassis_area],
            [p["y"] for p in cfg.chassis_area],
            [cfg.fork_root_2D_lasers],
            Coordinate.ROBOT,
        )
        Trace.log(f"set clear region:{ctx.chassis_clear_region},{cfg.chassis_area}", name="fork.task")

    elif fork_height > cfg.backLaserEnableHeight and not ctx.clear_fork_region_by_height:
        ctx.clear_fork_region_by_height = True
        ctx.set_fork_region_by_height = False
        Navigation.deleteClearRegion(ctx.chassis_clear_region, Coordinate.ROBOT)
        Trace.log(f"delete clear region:{ctx.chassis_clear_region},{cfg.chassis_area}", name="fork.task")


# ============================================================================
# 识别 / 货物辅助工具
# ============================================================================
def ensure_recfile(ctx) -> bool:
    if ctx.recfile:
        return True
    Navigation.setTaskError("RecfileMissing", "recognize enabled but recfile is empty")
    ctx.set_status(ScriptStatus.FAILED)
    return False


def load_recognition_assets(ctx, *, log_name="fork.task") -> bool:
    if not ctx.recfile:
        return True

    recognition_pallet_path = "recognitionObject.pallet"
    ctx.pallet_deduct_infos = get_deduct_area(ctx.recfile)
    ctx.carrier_width = RobotParam.getConfig(
        "recognition", f"{recognition_pallet_path}.carrierParameter.carrierWidth", ctx.recfile
    )
    ctx.carrier_length = RobotParam.getConfig(
        "recognition", f"{recognition_pallet_path}.carrierParameter.carrierLength", ctx.recfile
    )
    ctx.carrier_height = RobotParam.getConfig(
        "recognition", f"{recognition_pallet_path}.carrierParameter.carrierHeight", ctx.recfile
    )
    ctx.carrier_shape = [
        {"x": ctx.carrier_length / 2, "y": ctx.carrier_width / 2},
        {"x": -ctx.carrier_length / 2, "y": ctx.carrier_width / 2},
        {"x": -ctx.carrier_length / 2, "y": -ctx.carrier_width / 2},
        {"x": ctx.carrier_length / 2, "y": -ctx.carrier_width / 2},
    ]
    goods_shape = RobotParam.getConfig(
        "recognition", f"{recognition_pallet_path}.goodsParameter.goodsShape", ctx.recfile
    )
    ctx.goods_shape = parse_shapes(goods_shape)

    if not ctx.recognize:
        Trace.log(
            f"load pallet assets for blind load: carrier_shape:{ctx.carrier_shape}, "
            f"goods_shape:{ctx.goods_shape}, pallet_deduct_infos:{ctx.pallet_deduct_infos}",
            name=log_name,
        )
        return True

    ctx.rec_info = get_rec_side_info(ctx.recfile, ctx.recSide)
    Trace.log(f"pallet info:{ctx.rec_info}", name=log_name)
    if ctx.rec_info is None:
        ctx.set_status(ScriptStatus.FAILED)
        return False

    if ctx.recSide and ctx.rec_info.get("side_value") == ctx.recSide:
        ctx.pallet_deduct_infos = transform_deduct_area_infos_by_rec_side(ctx.pallet_deduct_infos, ctx.recSide)
        ctx.carrier_shape = transform_pallet_shape_by_rec_side(ctx.carrier_shape, ctx.recSide)
        ctx.goods_shape = transform_pallet_shape_by_rec_side(ctx.goods_shape, ctx.recSide)
        Trace.log(
            f"transform pallet shapes by recSide:{ctx.recSide}, carrier_shape:{ctx.carrier_shape}, "
            f"goods_shape:{ctx.goods_shape}, pallet_deduct_infos:{ctx.pallet_deduct_infos}",
            name="fork.cfg",
        )

    if any(v is None or v == "none" for v in ctx.rec_info.values()):
        Navigation.setTaskError("InvalidRecInfo", f"Invalid side info, found None: {ctx.rec_info},script failed")
        ctx.set_status(ScriptStatus.FAILED)
        return False

    return True


def resolve_load_recognition_pose(rec_action):
    results = rec_action.results_list
    rec_result_dict = results[0]
    world_result = rec_result_dict.get("worldResult", {})
    robot_result = rec_result_dict.get("robotResult", {})
    rec_world_pos = [world_result["x"], world_result["y"], world_result["yaw"]]
    rec_robot_pos = [robot_result["x"], robot_result["y"], robot_result["yaw"]]
    return results, rec_result_dict, rec_world_pos, rec_robot_pos


def apply_recognized_pallet_width(carrier_shape, deduct_infos, pallet_width):
    """按识别宽度平移模型和抠除区域的进叉面，保持背面位置不变。"""
    adjusted_shape = copy.deepcopy(carrier_shape)
    adjusted_deduct_infos = copy.deepcopy(deduct_infos)
    try:
        detected_width = float(pallet_width)
    except (TypeError, ValueError):
        return adjusted_shape, adjusted_deduct_infos
    if detected_width <= 0 or not adjusted_shape:
        return adjusted_shape, adjusted_deduct_infos

    x_values = [float(point["x"]) for point in adjusted_shape]
    configured_width = max(x_values) - min(x_values)
    if configured_width <= 0:
        return adjusted_shape, adjusted_deduct_infos
    delta = detected_width - configured_width

    def move_entry_face(points):
        if not points:
            return
        max_x = max(float(point["x"]) for point in points)
        for point in points:
            if math.isclose(float(point["x"]), max_x, abs_tol=1e-6):
                point["x"] = float(point["x"]) + delta

    move_entry_face(adjusted_shape)
    for info in adjusted_deduct_infos or []:
        for area in info.get("areas", []):
            points = [
                {"x": x, "y": y}
                for x, y in zip(area.get("x", []), area.get("y", []))
            ]
            move_entry_face(points)
            area["x"] = [point["x"] for point in points]
            area["y"] = [point["y"] for point in points]
    return adjusted_shape, adjusted_deduct_infos


def load_pallet_z_offset(rec_file: str, rec_side=None) -> float:
    """读取当前识别面的栈板高度补偿，并兼容历史字段位置。"""
    if not rec_file:
        return 0.0

    recognition_side_key = "recognitionObject.pallet.recognitionSide"
    try:
        side_count = RobotParam.getConfigCloneSize("recognition", recognition_side_key, rec_file)
        for index in range(side_count):
            side_value = RobotParam.getConfig(
                "recognition",
                f"{recognition_side_key}._{index}",
                rec_file,
            )
            if rec_side and side_value != rec_side:
                continue
            path = f"{recognition_side_key}._{index}.{side_value}.zOffset"
            value = RobotParam.getConfig("recognition", path, rec_file, None)
            if value is not None:
                return float(value)
            if rec_side:
                break
    except Exception as exc:
        Trace.log(
            f"load recognition side zOffset failed, rec_file={rec_file}, "
            f"rec_side={rec_side}, err={exc}",
            name="fork.cfg",
        )

    for path in (
            "recognitionObject.pallet.zOffset",
            "recognitionObject.pallet.carrierParameter.zOffset",
    ):
        try:
            value = RobotParam.getConfig("recognition", path, rec_file, None)
            if value is not None:
                return float(value)
        except Exception as exc:
            Trace.log(
                f"load pallet zOffset failed, rec_file={rec_file}, path={path}, err={exc}",
                name="fork.cfg",
            )
    return 0.0


def extract_recognition_height_z(rec_action):
    """从车型识别 action 或标准 robotResult 中提取用于取货的 z。"""
    selected_z = getattr(rec_action, "selected_recognition_z", None)
    if selected_z is not None:
        return float(selected_z)

    result = getattr(rec_action, "result", None)
    if not isinstance(result, dict):
        results_list = getattr(rec_action, "results_list", None) or []
        result = results_list[0] if results_list and isinstance(results_list[0], dict) else {}
    robot_result = result.get("robotResult", {}) if isinstance(result, dict) else {}
    raw_z = robot_result.get("z") if isinstance(robot_result, dict) else None
    if raw_z is None and isinstance(result, dict):
        raw_z = result.get("z")
    if raw_z is None:
        return None
    try:
        return float(raw_z)
    except (TypeError, ValueError):
        return None


def calculate_recognition_pick_height(
        recognition_z,
        z_offset,
        *,
        camera_moves_with_fork,
        fork_height_at_recognition=0.0,
        camera_calibration_fork_height=0.0,
):
    """按相机安装方式把识别 z 换算为货叉取货高度。"""
    pick_height = float(recognition_z) + float(z_offset)
    if not camera_moves_with_fork:
        pick_height += float(fork_height_at_recognition) - float(camera_calibration_fork_height)
    return pick_height


def build_recognition_readjust_target(rec_world_pos, min_ahead_dist):
    """计算识别目标前方的微调停车位，坐标约定与现有进叉路径一致。"""
    return pos2World([float(min_ahead_dist), 0.0, 0.0], rec_world_pos)


def evaluate_recognition_readjust(rec_robot_pos, dist_precision, angle_precision_deg):
    """返回二次识别是否收敛，以及用于日志/报错的横向和角度偏差。"""
    lateral_error = float(rec_robot_pos[1])
    angle_error_deg = math.degrees(float(rec_robot_pos[2]))
    converged = (
        abs(lateral_error) <= max(0.0, float(dist_precision))
        and abs(angle_error_deg) <= max(0.0, float(angle_precision_deg))
    )
    return converged, lateral_error, angle_error_deg


def _parse_recognition_info_payload(info_data):
    if isinstance(info_data, str):
        try:
            info_data = json.loads(info_data)
        except (TypeError, ValueError, json.JSONDecodeError):
            Trace.log(f"Failed to parse recognition info: {info_data}", name="fork.err")
            return {}, [], 0.0

    result_angle = 0.0
    hole_info_list = []
    if isinstance(info_data, dict):
        result_angle = info_data.get("angle", 0.0)
        hole_info_data = info_data.get("hole_info", info_data.get("holeInfo", []))
        if isinstance(hole_info_data, str):
            try:
                hole_info_data = json.loads(hole_info_data)
            except (TypeError, ValueError, json.JSONDecodeError):
                Trace.log(f"Failed to parse hole_info: {hole_info_data}", name="fork.err")
                hole_info_data = []
        if isinstance(hole_info_data, list):
            hole_info_list = hole_info_data
    elif isinstance(info_data, list):
        hole_info_list = [item for item in info_data if isinstance(item, dict)]
        if hole_info_list:
            result_angle = hole_info_list[0].get("angle", 0.0)
    return info_data, hole_info_list, result_angle


def _normalize_recognition_hole_info(result, hole_info_list):
    robot_result = result.get("robotResult", {})
    if not isinstance(robot_result, dict):
        robot_result = {}
    pallet_pos = [
        float(robot_result.get("x", 0.0) or 0.0),
        float(robot_result.get("y", 0.0) or 0.0),
        float(robot_result.get("yaw", 0.0) or 0.0),
    ]

    normalized_holes = []
    for hole_info in hole_info_list:
        if not isinstance(hole_info, dict):
            continue
        try:
            robot_result_x = float(hole_info.get("robotResultX", 0.0) or 0.0)
            robot_result_y = float(hole_info.get("robotResultY", 0.0) or 0.0)
            hole_z = float(hole_info.get("z", hole_info.get("robotResultZ", 0.0)) or 0.0)
            hole_width = float(hole_info.get("width", hole_info.get("holeWidth", 0.0)) or 0.0)
        except (TypeError, ValueError):
            Trace.log(f"Invalid hole info: {hole_info}", name="fork.err")
            continue

        hole_in_pallet = pos2Base([robot_result_x, robot_result_y, 0.0], pallet_pos)
        normalized_hole = {
            "x": hole_in_pallet[0],
            "y": hole_in_pallet[1],
            "z": hole_z,
            "width": hole_width,
        }
        normalized_holes.append(normalized_hole)
        Trace.log(
            f"hole robotResult=[{robot_result_x:.4f}, {robot_result_y:.4f}], "
            f"palletCoord=[{hole_in_pallet[0]:.4f}, {hole_in_pallet[1]:.4f}]",
            name="fork.task",
        )
    result["holeInfo"] = normalized_holes
    return normalized_holes


def _build_action_hole_positions(result):
    hole_info_list = result.get("holeInfo", [])
    if not isinstance(hole_info_list, list):
        return []
    return [
        {
            "holeX": float(hole.get("x", 0.0) or 0.0),
            "holeY": float(hole.get("y", 0.0) or 0.0),
            "holeZ": float(hole.get("z", 0.0) or 0.0),
            "holeWidth": float(hole.get("width", 0.0) or 0.0),
        }
        for hole in hole_info_list
        if isinstance(hole, dict)
    ]


def normalize_recognition_result_metadata(result):
    """把识别结果 ``info`` 中的通用元数据归一到结果顶层。

    同时处理栈板倾斜角 ``angle`` 和叉孔 ``holeInfo``。兼容 ``info`` 为 JSON 字符串、
    dict 或 list；缺失/非法值按 0 处理，保持参考脚本行为。
    """
    if not isinstance(result, dict):
        return result

    raw_angle = result.get("angle")
    info_data, hole_info_list, parsed_angle = _parse_recognition_info_payload(result.get("info", {}))
    _normalize_recognition_hole_info(result, hole_info_list)
    if raw_angle is None:
        if isinstance(info_data, dict):
            raw_angle = info_data.get("angle", parsed_angle)
        else:
            raw_angle = parsed_angle

    try:
        result["angle"] = float(raw_angle)
    except (TypeError, ValueError):
        Trace.log(f"Invalid recognition tilt angle: {raw_angle}", name="fork.err")
        result["angle"] = 0.0
    return result


def validate_recognition_tilt(ctx, rec_result_dict):
    """校验识别栈板倾斜角；负阈值表示关闭。"""
    threshold = getattr(_config(), "errorRecTiltAngle", -1.0)
    try:
        threshold = float(threshold)
    except (TypeError, ValueError):
        threshold = -1.0
    if threshold < 0:
        return True

    normalize_recognition_result_metadata(rec_result_dict)
    tilt_angle = float(rec_result_dict.get("angle", 0.0))
    if abs(tilt_angle) <= threshold:
        return True

    Navigation.setTaskError(
        "RecTiltAngleError",
        f"rec result tilt angle too large:{tilt_angle}deg",
    )
    ctx.set_status(ScriptStatus.FAILED)
    return False


def validate_goods_state_for_operation(ctx, operation):
    """取放货前强制校验当前载货状态。"""
    has_goods = Container.hasGoods("0")
    if operation == "load" and has_goods:
        Navigation.setTaskError("ForkHasGoods", "fork has goods, cannot load, script failed")
        ctx.set_status(ScriptStatus.FAILED)
        return False
    if operation == "unload" and not has_goods:
        Navigation.setTaskError("ForkNoGoods", "fork has no goods, cannot unload, script failed")
        ctx.set_status(ScriptStatus.FAILED)
        return False
    return True


def validate_recognition_result_against_target(ctx, rec_world_pos):
    if not has_valid_target_pos(ctx.target_pos):
        return True

    rec2ap_pos = pos2Base(rec_world_pos, ctx.target_pos)
    angle = math.degrees(rec2ap_pos[2])
    Trace.log(
        f"rec2ap_pos: {rec2ap_pos},rec_world_pos: {rec_world_pos},target_pos:{ctx.target_pos},angle2ap:{angle}",
        output_console=True,
        output_time=True,
        name="fork.task",
    )
    y = rec2ap_pos[1]
    if abs(angle) > _config().errorRecAngle != -1:
        Navigation.setTaskError("RecYError", f"rec result yaw angle too large:{angle}° from action point")
        ctx.set_status(ScriptStatus.FAILED)
        return False
    if abs(y) > _config().errorRecY != -1:
        Navigation.setTaskError("RecYError", f"rec result y too large :{y}m from action point")
        ctx.set_status(ScriptStatus.FAILED)
        return False
    return True


def load_goods_shape(ctx):
    base_pos = [_config().module_x - ctx.carrier_length / 2, 0, 0]
    if ctx.recognize and ctx.recognized_pallet_world_pos is not None:
        pallet_entry_in_robot = pos2Base(ctx.recognized_pallet_world_pos, get_r_loc())
        entry_face_x = max(float(point["x"]) for point in ctx.carrier_shape)
        base_pos = pos2World([-entry_face_x, 0, 0], pallet_entry_in_robot)
        Trace.log(
            f"recognized pallet model base:{base_pos}, entry:{pallet_entry_in_robot}, "
            f"palletWidth:{ctx.pallet_width}",
            name="fork.task",
        )

    goods_point2robot = []
    for point in ctx.carrier_shape:
        point2ap = pos2World([point["x"], point["y"], 0], base_pos)
        goods_point2robot.append({"x": point2ap[0], "y": point2ap[1]})

    if ctx.pallet_deduct_infos:
        set_deduct_area(
            ctx.pallet_deduct_infos,
            base_pos,
            "PalletRobotDeductArea",
            Coordinate.ROBOT,
        )

    Navigation.setGoodsPolyShape(goods_point2robot, ctx.recfile)


# ============================================================================
# 设备 / 形状 / 参数解析工具
# ============================================================================
def split_device_keys(raw) -> List[str]:
    return [part.strip() for part in str(raw or "").split(",") if part.strip()]


def get_fork_root_laser_keys(cfg=None) -> List[str]:
    if cfg is None:
        cfg = _config()
    return split_device_keys(getattr(cfg, "fork_root_2D_lasers", ""))


def parse_bind_shape_points(raw_shape) -> List[Dict[str, float]]:
    if not raw_shape:
        return []

    try:
        data = json.loads(raw_shape) if isinstance(raw_shape, str) else raw_shape
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid bind shape json: {exc}")

    def _normalize_points(points) -> List[Dict[str, float]]:
        normalized_points = []
        if not isinstance(points, list):
            return normalized_points
        for point in points:
            if not isinstance(point, dict):
                continue
            try:
                normalized_points.append({
                    "x": float(point["x"]),
                    "y": float(point["y"]),
                })
            except (KeyError, TypeError, ValueError):
                continue
        return normalized_points

    if isinstance(data, dict):
        normalized_points = _normalize_points(data.get("points", []))
        if len(normalized_points) >= 3:
            return normalized_points
    elif isinstance(data, list):
        normalized_points = _normalize_points(data)
        if len(normalized_points) >= 3:
            return normalized_points
        for item in data:
            if not isinstance(item, dict):
                continue
            normalized_points = _normalize_points(item.get("points", []))
            if len(normalized_points) >= 3:
                return normalized_points
    else:
        raise ValueError(f"unsupported bind shape type: {type(data).__name__}")

    raise ValueError("bind shape has no valid polygon points")


def check_sensor_collision(device_keys: List[str], shape_points: List[Dict[str, float]], *, world_frame: bool = False) -> bool:
    if not device_keys or len(shape_points or []) < 3:
        return False

    x_list = []
    y_list = []
    robot_pose = get_r_loc() if world_frame else None
    for point in shape_points:
        x = float(point["x"])
        y = float(point["y"])
        if world_frame and robot_pose is not None:
            x, y, _ = pos2Base([x, y, 0.0], robot_pose)
        x_list.append(float(x))
        y_list.append(float(y))
    return bool(Navigation.collisionDetection(device_keys, x_list, y_list))


def float32_to_regs(value: float):
    """float32 转成两个寄存器（小端：低位在前）"""
    raw = struct.pack("!f", value)
    word1 = int.from_bytes(raw[2:], "big")
    word2 = int.from_bytes(raw[:2], "big")
    return [word1, word2]


def float_to_modbus_poll_regs(value: float):
    """
    将 float 数值转换为两个 uint16 的 Modbus Poll 寄存器值，符合小端序（B0 B1 B2 B3 → reg1 = B3B2, reg2 = B1B0）
    """
    value = struct.unpack('<f', struct.pack('<f', value))[0]
    packed = struct.pack('<f', value)
    b0, b1, b2, b3 = packed
    reg1 = (b1 << 8) + b0
    reg2 = (b3 << 8) + b2
    return [reg1, reg2]


def create_fork_height_param(builder: ParamBuilder, min_height: float, max_height: float):
    with builder.CHILD(key="height", name=_TR("Fork Height"), desc=_TR("The height for lift operations")):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(True)
        builder.UNIT("m")
        builder.SINGLESTEP(0.01)
        builder.DEFAULTVALUE(0.1)


def create_end_height_param(builder: ParamBuilder, min_height: float, max_height: float):
    with builder.CHILD(key="endHeight", name=_TR("End Height"), desc=_TR("The fork height after load")):
        builder.TYPE(ParamType.FLOAT)
        builder.UNIT("m")
        builder.SINGLESTEP(0.01)
        builder.DEFAULTVALUE(0.1)


def create_start_height_param(builder: ParamBuilder, min_height: float, max_height: float):
    with builder.CHILD(key="startHeight", name=_TR("Start Height"), desc=_TR("The fork height before load")):
        builder.TYPE(ParamType.FLOAT)
        builder.UNIT("m")
        builder.SINGLESTEP(0.01)
        builder.DEFAULTVALUE(0.1)


def create_loc_detect_height_param(builder: ParamBuilder, min_height: float, max_height: float):
    with builder.CHILD(key="locDetectHeight", name=_TR("Location Detection Height"),
                       desc=_TR("Fork height used to detect whether the location contains goods")):
        builder.TYPE(ParamType.FLOAT)
        builder.UNIT("m")
        builder.SINGLESTEP(0.01)
        builder.DEFAULTVALUE(-1, min_value=-1, max_value=max_height)


def create_loc_detect_layer_param(builder: ParamBuilder):
    with builder.CHILD(key="locDetectLayer", name=_TR("Location Detection Layer"),
                       desc=_TR("Location layer used to calculate the fork detection height")):
        builder.TYPE(ParamType.INT)
        builder.DEFAULTVALUE(-1, min_value=-1)

def create_rec_param(builder: ParamBuilder, extra_on_params_hook=None, include_rec_height=True):
    with builder.CHILD(key="recognize", name=_TR("Recognition"), desc=_TR("Enable pallet recognition")):
        builder.TYPE(ParamType.COMBO_BOX_BOOL)
        builder.DEFAULTVALUE("off")

        with builder.CHILDREN():
            with builder.CHILD(key="off", name=_TR("Recognize"), desc=_TR("Load Without Recognition")):
                builder.TYPE(ParamType.ARRAY)

            with builder.CHILD(key="on", name=_TR("Recognize"), desc=_TR("Load With Recognition")):
                builder.TYPE(ParamType.ARRAY)

                with builder.CHILD(key="recSide", name=_TR("Recognition Side"), desc=_TR("Recognition Side")):
                    builder.TYPE(ParamType.STRING_COMBO_LIST)
                    builder.DEFAULTVALUE("none")
                    builder.REQUIRED(False)
                    with builder.CHILDREN():
                        with builder.CHILD(key="none", name=_TR("None"), desc=_TR("No recognition side")):
                            builder.TYPE(ParamType.STRING)
                        for rec_side in ("A", "B", "C", "D"):
                            with builder.CHILD(key=rec_side, name=rec_side, desc=_TR("Recognition Side")):
                                builder.TYPE(ParamType.STRING)

                if include_rec_height:
                    with builder.CHILD(key="recHeight", name=_TR("Rec Height"), desc=_TR("The fork height before load after rec")):
                        builder.TYPE(ParamType.FLOAT)
                        builder.UNIT("m")
                        builder.SINGLESTEP(0.01)
                        builder.DEFAULTVALUE(0.1)
                if extra_on_params_hook is not None:
                    extra_on_params_hook(builder)

    with builder.CHILD(key="recfile", name=_TR("Recognition File"), desc=_TR("Pallet asset file name")):
        builder.TYPE(ParamType.BIND_TYPE)
        builder.BINDTYPE(BindType.App.RECOGNITION)
        builder.REQUIRED(False)



def delete_deduct_area(names, coordinate):
    if not names:  # names 为空 → 删除全部
        deduct_area_list = Navigation.getClearRegion(coordinate)
    else:
        if isinstance(names, str):
            names = [names]
        deduct_area_list = [
            s for s in Navigation.getClearRegion(coordinate)
            if s.startswith(tuple(names))
        ]

    for region in deduct_area_list:
        Navigation.deleteClearRegion(region, coordinate)


def set_deduct_area(area_infos, base_pos, prefix: str, coordinate):
    """
    扣除栈板相关的内容，区域名称以PalletRobotDeductArea[idx]命名
    """
    for info_idx, info in enumerate(area_infos):
        devices = info["deduct_device"]
        for area_idx, area in enumerate(info["areas"], start=1):
            x_coords, y_coords = [], []

            for x, y in zip(area["x"], area["y"]):
                wx, wy, wz = pos2World([x, y, 0], base_pos)
                x_coords.append(wx)
                y_coords.append(wy)

            # 区域合法性检查
            if len(x_coords) < 3 or len(x_coords) != len(y_coords):
                Trace.log(f"skip invalid area idx={area_idx}, device={devices}", name="fork.cfg")
                continue

            region_name = f"{prefix}{info_idx + 1}_{area_idx}"
            Navigation.setClearRegion(
                region_name,
                x_coords,
                y_coords,
                devices,  # 支持一个或多个 device
                coordinate,
            )

            Trace.log(f"set clear region: {region_name}, devices={devices}", name="fork.task")


def get_deduct_area(recfile):
    """
    解析 pallet 障碍物扣除区域配置。
    返回格式:
    [
        {
            "deduct_device": ["Laser-003"],
            "areas": [
                {"x": [...], "y": [...]},
                {"x": [...], "y": [...]}
            ]
        },
        ...
    ]
    """
    recognition_obstacle_deduction_path = "recognitionObject.pallet.deductModel"
    size = RobotParam.getConfigCloneSize("recognition", recognition_obstacle_deduction_path, recfile)

    result = []

    if size is None:
        Navigation.setTaskError("NoDeductShape", f"no deductShape in recfile")
        return []

    for i in range(size):
        # 获取设备ID
        device_str = RobotParam.getConfig(
            "recognition",
            f"{recognition_obstacle_deduction_path}._{i}.deductDevice",
            recfile,
        )
        if not device_str:
            continue
        devices = [d for d in device_str.split(",") if d.strip()]

        # 获取形状信息
        shape_str = RobotParam.getConfig(
            "recognition",
            f"{recognition_obstacle_deduction_path}._{i}.deductShape",
            recfile,
        )
        # print(shape_str)
        if not shape_str:
            continue
        shapes = json.loads(shape_str)

        areas = []
        for shape in shapes:
            pts = shape.get("points", [])
            if len(pts) < 3:  # 至少3个点才构成区域
                continue
            x_list = [p["x"] for p in pts]
            y_list = [p["y"] for p in pts]
            areas.append({"x": x_list, "y": y_list})

        if devices and areas:
            result.append({"deduct_device": devices, "areas": areas})

    Trace.log(f"pallet_deduct_infos: {result}", name="fork.cfg")
    return result


def get_rec_side_info(recfile, rec_side):
    recognitionSide_key = "recognitionObject.pallet.recognitionSide"
    recognitionSide_size = RobotParam.getConfigCloneSize("recognition", recognitionSide_key, recfile)
    rec_sides = []

    for i in range(recognitionSide_size):
        side_value = RobotParam.getConfig("recognition", f"{recognitionSide_key}._{i}", recfile)
        # coordinateSystem = RobotParam.getConfig(
        #     "recognition",
        #     f"{recognitionSide_key}._{i}.{side_value}.coordinateSystem",
        #     recfile
        # )
        enableCargoContactDI = RobotParam.getConfig(
            "recognition",
            f"{recognitionSide_key}._{i}.{side_value}.enableCargoContactDI",
            recfile
        )
        enableBackDistance = RobotParam.getConfig(
            "recognition",
            f"{recognitionSide_key}._{i}.{side_value}.enableBackDistance",
            recfile
        )

        side_info = {
            "side_value": side_value,
            # "coordinateSystem": coordinateSystem,  # 3.5.4 proto变更取消字段
            "enableCargoContactDI": enableCargoContactDI,
            "enableBackDistance": enableBackDistance
        }

        if enableBackDistance == "on":
            backDistance = RobotParam.getConfig(
                "recognition",
                f"{recognitionSide_key}._{i}.{side_value}.enableBackDistance.{enableBackDistance}.backDistance",
                recfile
            )
            side_info["backDistance"] = backDistance

        rec_sides.append(side_info)

    if rec_side:
        rec_info = next((s for s in rec_sides if s["side_value"] == rec_side), None)
        if rec_info is None:
            Navigation.setTaskError("RecSideError",
                                    f"Recognition side {rec_side} is not match in {recfile}, script failed")
            Trace.log(f"input rec_side:{rec_side}, rec_info: None, rec_sides:{rec_sides}", name="fork.err")
            return None
    else:
        if len(rec_sides) == 0:
            Navigation.setTaskError("RecSideError", f"RecSide is not config in {recfile}, script failed")
            Trace.log(f"no rec side in {recfile}", output_console=True, output_time=True, name="fork.err")
            return None
        rec_info = rec_sides[0]

    Trace.log(f"input rec_side:{rec_side}, rec_info:{rec_info}, rec_sides:{rec_sides}", name="fork.cfg")
    return rec_info


def parse_shapes(json_str):
    """
       输入: JSon 字符串（来自 RobotParam.getConfig）
       输出: [
                [{"x":..,"y":..}, {"x":..,"y":..}, ...],
                [{"x":..,"y":..}, {"x":..,"y":..}, ...]
             ]
       """
    if not json_str:
        return []
    try:
        data = json.loads(json_str) if isinstance(json_str, str) else json_str
    except json.JSonDecodeError:
        return []

    points = []
    for obj in data:
        for p in obj.get("points", []):
            points.append({"x": p["x"], "y": p["y"]})
    return points


def transform_pallet_point_by_rec_side(point, rec_side):
    """Transform pallet-center coordinates when the recognition-side axes rotate."""
    x = point["x"]
    y = point["y"]
    side = str(rec_side).lower()

    # 栈板坐标顺时针转90°
    if side == "a":
        return {"x": y, "y": -x}
    # 栈板坐标顺时针转180°
    if side == "b":
        return {"x": -x, "y": -y}
    # 栈板坐标逆时针转90°
    if side == "c":
        return {"x": -y, "y": x}
    return {"x": x, "y": y}


def transform_pallet_shape_by_rec_side(points, rec_side):
    return [transform_pallet_point_by_rec_side(point, rec_side) for point in points]


def transform_deduct_area_infos_by_rec_side(area_infos, rec_side):
    transformed_infos = []
    for info in area_infos:
        transformed_areas = []
        for area in info["areas"]:
            points = [{"x": x, "y": y} for x, y in zip(area["x"], area["y"])]
            transformed_points = transform_pallet_shape_by_rec_side(points, rec_side)
            transformed_areas.append({
                "x": [point["x"] for point in transformed_points],
                "y": [point["y"] for point in transformed_points],
            })
        transformed_infos.append({
            "deduct_device": info["deduct_device"],
            "areas": transformed_areas,
        })
    return transformed_infos


def convex_hull(points1, points2=None, points3=None):
    """输入三组 [{'x':..,'y':..},...] 点，输出凸包 [{'x':..,'y':..},...]"""

    # 合并三组点
    all_points = []
    for group in (points1, points2, points3):
        if group:  # 可能为空
            for p in group:
                all_points.append((float(p["x"]), float(p["y"])))

    # 去重 & 排序
    pts = sorted(set(all_points))
    if len(pts) <= 1:
        return [{"x": x, "y": y} for x, y in pts]

    # 叉积
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    # 下凸壳
    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)

    # 上凸壳
    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)

    hull = lower[:-1] + upper[:-1]
    return [{"x": x, "y": y} for x, y in hull]


def _action_chart_dict(action, idx: int) -> dict:
    """把 action._trace_state() 加上前缀 action.{idx}.{cls}. 用于 Trace.chart"""
    cls = action.__class__.__name__
    state = action._trace_state() if hasattr(action, "_trace_state") else {}
    return {f"action.{idx}.{cls}.{k}": v for k, v in state.items()}


def _init_action_runtime(action):
    action.start_time = time.time()
    action.action_state = {}


def format_action(action) -> str:
    return json.dumps(
        {
            "class_name": getattr(action, "action_name", action.__class__.__name__),
            "action_id": getattr(action, "action_id", ""),
            "action_status": int(getattr(action, "action_status", ActionStatus.INIT)),
        },
        ensure_ascii=False,
    )


class OperationFlow:
    """生成器式 operation 驱动器：把一个 operation 表达成"批的序列"。

    handler 写成生成器函数：每 `yield` 一批动作（list），队列跑完这批（全部 FINISHED）后
    才 `advance()` 拉下一批；生成器耗尽（StopIteration）即 operation 完成（`done` 置位）。
    `yield` 之后的代码只在该批结束后执行，故可就地读刚结束动作的结果，无需 on_finished 回调。

    职责单一：只管"拉批 + 注入"，通过 `set_actions` 回调把批交给动作队列；
    "当前批是否跑完 / 任务成败"由持有方（队列归属方）判定，不进本类。

    与车型/fork 无关，仅依赖 Python 生成器协议 + 一个注入回调，便于日后整体上移到
    任务生命周期层（ModuleBase / mixin）——见 fork-refactor-spec §3.2。
    """

    def __init__(self, set_actions):
        self._set_actions = set_actions
        self._gen = None
        self._done = False

    @property
    def active(self) -> bool:
        """生成器仍在推进中（已 start 且未耗尽）。"""
        return self._gen is not None

    @property
    def done(self) -> bool:
        """生成器已耗尽（含首次即结束 / 无 yield）。"""
        return self._done

    def start(self, gen):
        """接入一个 operation 生成器并注入第一批。"""
        self._gen = gen
        self._done = False
        self.advance()

    def advance(self) -> bool:
        """拉下一批动作并入队。

        耗尽返回 False 并置 `done`；否则入队非空批返回 True。
        空批（`[]` / `None`）自动跳过继续拉，允许生成器 yield 空表示"这步无动作"。
        `next()` 期间生成器可能改变持有方状态（如置 FAILED）后 return——持有方须其后复查。
        """
        if self._gen is None:
            return False
        while True:
            try:
                batch = next(self._gen)
            except StopIteration:
                self._gen = None
                self._done = True
                return False
            if batch:
                self._set_actions(list(batch))
                return True

    def close(self):
        """关闭未跑完的生成器，触发其内部 finally 清理（任务收尾 / 取消时调用）。"""
        gen = self._gen
        self._gen = None
        self._done = False
        if gen is not None:
            gen.close()


class ForkActionQueue(ActionTask):
    """兼容旧 fork 串行执行语义的 ActionTask 包装器。"""

    def __init__(self, mod: str = MOD, on_change=None):
        super().__init__(mod, on_change=on_change)
        self.cursor = 0
        self._finish_pending = False

    def _finalize_failed_action(self, action):
        self._failed_at = action.action_id or self._failed_at
        self._finalize_failed(reason=action.fail_reason or "")

    def __repr__(self):
        return "[" + ", ".join(format_action(action) for action in self.action_list) + "]"

    __str__ = __repr__

    @property
    def current_action(self):
        if not self.action_list:
            return None
        if self.status == ActionStatus.FINISHED:
            return None
        return self.action_list[self.current_index]

    def replace(self, actions, *, blocking_type: str = "HARD"):
        actions = list(actions or [])
        if not actions:
            self.reset()
            return
        self.cursor = 0
        self._finish_pending = False
        super().build(actions, blocking_type=blocking_type)

    def append(self, action, *, blocking_type: str = "HARD"):
        self.extend([action], blocking_type=blocking_type)

    def extend(self, actions, *, blocking_type: str = "HARD"):
        actions = list(actions or [])
        if not actions:
            return
        self._finish_pending = False
        if self.status in (ActionStatus.RUNNING, ActionStatus.SUSPENDED) and self.total > 0:
            super().extend(actions, blocking_type=blocking_type)
        else:
            combined = list(self.action_list) + actions
            self.cursor = 0
            super().build(combined, blocking_type=blocking_type)


    def step(self, ctx=None):
        if self.status != ActionStatus.RUNNING:
            self._notify()
            return
        if not self.action_list:
            self._notify()
            return

        if self.cursor >= len(self.action_list):
            if self._finish_pending:
                self._finish_pending = False
                self._finalize_finished()
                self.cursor = len(self.action_list)
            self._notify()
            return

        current = self.action_list[self.cursor]
        if current.action_status == ActionStatus.FAILED:
            self._finalize_failed_action(current)
            self._notify()
            return

        if current.action_status == ActionStatus.FINISHED:
            self._fire_step_end(current, ctx)
            if self.cursor >= len(self.action_list) - 1:
                if self._finish_pending:
                    self._finish_pending = False
                    self._finalize_finished()
                    self.cursor = len(self.action_list)
                else:
                    self._finish_pending = True
            else:
                self.cursor += 1
                self._finish_pending = False
            self._notify()
            return

        self._finish_pending = False

        if current.action_status == ActionStatus.INIT:
            self._action_start_ts[current.action_id] = time.time()
            self._fire_step_start(current, ctx)
            current.reset()
            if current.action_status == ActionStatus.INIT:
                current.action_status = ActionStatus.RUNNING
            self._emit_state_changed(current, current.action_status)
            if current.action_status == ActionStatus.FAILED:
                self._fire_step_end(current, ctx)
                self._finalize_failed_action(current)
            self._notify()
            return

        if current.action_status == ActionStatus.RUNNING:
            last_status = self._last_status.get(current.action_id, ActionStatus.RUNNING)
            current.run(ctx)
            if current.action_status != last_status:
                self._emit_state_changed(current, current.action_status)
            if current.action_status in (ActionStatus.FINISHED, ActionStatus.FAILED):
                self._fire_step_end(current, ctx)
            if current.action_status == ActionStatus.FAILED:
                self._finalize_failed_action(current)
            self._notify()
            return

        self._notify()

    def suspend(self):
        super().suspend()  # 基类已 _notify

    def resume(self):
        super().resume()  # 基类已 _notify

    def cancel(self, reason: str = "cancelled"):
        super().cancel(reason=reason)  # 基类已 _notify

    def reset(self):
        self.cursor = 0
        self._finish_pending = False
        super().reset()  # 基类已 _notify（在清空后触发）


# 仿真识别结果 / 到位 di 注入原语已迁至 tests/fork_sim_inject（由 tests/fork_flow.py 在仿真下驱动）。
# fork_utils 仅在仿真守卫下惰性委托，实机永不触发。


# 用于识别栈板并获取识别的栈板坐标
class Rec(ActionBase):
    def __init__(
            self,
            pallet_file,
            rec_center_x=-1.0,
            rec_center_y=0.0,
            rec_radius=0.7,
            action_name="RecPallet",
            checkQR=False,
            z_max: Optional[bool] = None,
            max_attempts: int = 20,
    ):
        super().__init__(action_name)
        _init_action_runtime(self)
        self.rec_status = None
        self.result = dict()
        self.action_status = ActionStatus.INIT
        self.recfile = pallet_file
        self.attempts = 0
        self.max_attempts = max(1, int(max_attempts))
        self.success = False
        self.results_dict = {}
        self.results_list = []
        self.hole_positions = []
        self.obstacle_polygon = []
        self.check_qr = checkQR
        self.z_max = z_max
        self.is_error = False
        self.max_rec_times = 3
        self.rec_times = 0
        self.object_message = ""
        self.fork_height_at_recognition = None
        # 识别区域参数
        self.rec_center_x = rec_center_x
        self.rec_center_y = rec_center_y
        self.rec_radius = rec_radius
        self.region = {
            "point": {"x": self.rec_center_x, "y": self.rec_center_y},
            "radius": self.rec_radius,
            "shape": "circle"
        }
        Trace.log(f"region: {self.region}", name="fork.task")
        self._last_wait_trace_status = None
        self._last_wait_trace_second = -1

    def run(self, ctx=None):
        if not self.init:
            self.init = True
            self.success = False
            time.sleep(1)

        self.action_status = ActionStatus.RUNNING
        if not self.success:
            self.success, self.rec_status, self.results_dict = self.rec(self.recfile)
        else:
            results_list = self.results_dict.get("recoList", [])
            self.obstacle_polygon = self.results_dict.get("obstaclePolygon", [])
            for result in results_list:
                normalize_recognition_result_metadata(result)
            sort_by_z_desc = _config().zMax if self.z_max is None else bool(self.z_max)
            # 处理识别结果，并按降序排序，z值最大的结果在前
            if sort_by_z_desc:
                results_list.sort(key=lambda x: x["robotResult"]["z"], reverse=True)
                results_list.sort(key=lambda x: x["worldResult"]["z"], reverse=True)
            # z值最小的结果在前
            else:
                results_list.sort(key=lambda x: x["robotResult"]["z"])
                results_list.sort(key=lambda x: x["worldResult"]["z"])

            self.results_list = results_list
            self.result = self.results_list[0]
            self.hole_positions = _build_action_hole_positions(self.result)
            self.fork_height_at_recognition = Motor.getMotorPos(_config().fork_motor_name)

            Trace.log(f"rec_result_list: {self.results_list}", name="fork.cfg")

            self.action_status = ActionStatus.FINISHED

    def reset(self):
        Recognize.resetRec()
        _init_action_runtime(self)
        self.action_status = ActionStatus.RUNNING
        self.init = False
        self.hole_positions = []
        self._last_wait_trace_status = None
        self._last_wait_trace_second = -1

    def _trace_waiting_state(self, recfile, rec_status):
        elapsed = time.time() - self.start_time
        elapsed_second = int(elapsed)
        if self._last_wait_trace_status == rec_status and self._last_wait_trace_second == elapsed_second:
            return
        self._last_wait_trace_status = rec_status
        self._last_wait_trace_second = elapsed_second
        """
        @NameZh @fork.rec 叉车识别等待状态
        @NameEn @fork.rec fork recognition waiting state
        @KeyZh @recStatus 识别状态
        @KeyEn @recStatus recognition status
        @NumberType @recStatus
        @KeyZh @recAttempts 重试次数
        @KeyEn @recAttempts retry attempts
        @NumberType @recAttempts
        @KeyZh @recElapsed 识别耗时
        @KeyEn @recElapsed recognition elapsed time
        @NumberType @recElapsed
        @Unit @recElapsed s
        @KeyZh @recIssued 是否已下发识别
        @KeyEn @recIssued whether recognition request has been issued
        @BooleanType @recIssued
        """
        Trace.log(
            {
                "recStatus": int(rec_status),
                "recAttempts": int(self.attempts),
                "recElapsed": round(elapsed, 3),
                "recIssued": bool(rec_status != 0),
            },
            False,
            name="fork.rec",
        )
        Trace.log(
            f"rec waiting, file:{recfile}, status:{rec_status}, attempts:{self.attempts}, elapsed:{elapsed:.3f}s",
            name="fork.task",
        )

    def rec(self, recfile):
        try:
            from tests.fork_sim_inject import load_sim_rec_result
            sim_result = load_sim_rec_result()
        except Exception:  # noqa: BLE001
            sim_result = None
        if sim_result is not None:
            Trace.log(f"[sim] inject rec result for {recfile}: {sim_result}", name="fork.cfg")
            return True, 2, sim_result
        rec_status = Recognize.getRecStatus()
        if rec_status == 2:
            rec_result = Recognize.getRecResults()
            Trace.log(f"raw results:{rec_result}", name="fork.cfg")
            if self.check_qr:
                reco_list = rec_result.get("recoList", [])
                is_valid_qr = False
                for item in reco_list:
                    if item.get("class") == "qrCode" and item.get("objectMessage"):
                        is_valid_qr = True
                        self.object_message = item.get("objectMessage", "")
                        break
                if is_valid_qr:
                    if "resultImg" in rec_result:
                        rec_result.pop("resultImg")
                    Recognize.resetRec()
                    self.action_status = ActionStatus.FINISHED
                    Trace.log(f"rec success (qrCode): {rec_result}", name="fork.cfg")
                    return True, rec_status, rec_result

                Trace.log(f"rec got non-qrCode or empty objectMessage, retry. result={rec_result}", name="fork.err")
                Recognize.resetRec()
                self.rec_times += 1
                if self.rec_times > self.max_rec_times:
                    if not self.is_error:
                        Navigation.setTaskError("RecFailed", f"连续{self.max_rec_times}次未识别到有效二维码")
                        self.is_error = True
                    self.action_status = ActionStatus.FAILED
                    return False, rec_status, rec_result
                return False, rec_status, rec_result
            return True, rec_status, rec_result
        elif rec_status in (-1, 3):
            if Timer.delay(0.05):
                self.attempts += 1
                if self.attempts > self.max_attempts:
                    results = Recognize.getRecResults()
                    # Trace.log(f"raw results:{results}")
                    error_type = results["error"]
                    error_msg = results["logMsg"]
                    Trace.log(f"error_type: {error_type}", name="fork.err")
                    self.action_status = ActionStatus.FAILED
                    Navigation.setTaskError("RecFailed",
                                            f"Recognition failed, the maximum number of retries exceeded,error_type: {error_type}, error_msg: {error_msg}")
                else:
                    Recognize.resetRec()
        elif rec_status == 0:
            self._trace_waiting_state(recfile, rec_status)
            Recognize.doRec(recfile, json.dumps(self.region))
            Timer.delay(0.05)
        else:
            self._trace_waiting_state(recfile, rec_status)
            Timer.delay(0.05)
        return False, rec_status, list

    def _trace_state(self) -> dict:
        return {
            "action_status": int(self.action_status),
            "attempts": self.attempts,
            "success": self.success,
            "rec_status": self.rec_status or 0,
        }


class GoTwoStraightLine(ActionBase):
    def __init__(self, world_target, min_ahead_dist, ahead_dist, back_dist, speed, max_angle=20.0, dec_dist=1.0,
                 return_back=False):
        super().__init__("GoTwoStraightLine")
        _init_action_runtime(self)
        self.path_actions = []
        self.current_step = 0
        self.temp_start = []
        self.first_point = None
        self.start_pos = []
        self.world_target = world_target
        self.min_ahead_dist = min_ahead_dist
        self.ahead_dist = ahead_dist
        self.back_dist = back_dist
        self.speed = speed
        self.max_angle = max_angle
        self.dec_dist = dec_dist
        self.step = 20

        self.go_step = []
        self.action_status = ActionStatus.INIT
        self.init = False
        self.return_back = return_back
        # 如果执行去目标点
        if not self.return_back:

            # 栈板前的点
            self.second_point = pos2World([self.min_ahead_dist, 0, 0], self.world_target)
            # 终点
            self.third_point = pos2World([-self.back_dist, 0, 0], self.world_target)

            # 记录起始点
            self.start_pos = get_r_loc()
            # 如果从当前点出发区栈板前的点角度不满足要求就开始迭代
            if abs(self.cal_angle(self.start_pos, self.second_point)) > self.max_angle:
                self.start_pos[2] = self.world_target[2]
                self.temp_start = self.search_min_angle_str(self.max_angle, self.step)
            else:
                self.temp_start = self.start_pos
            Trace.log(f"points before set': {self.start_pos, self.temp_start, self.second_point, self.world_target}",
                      name="fork.task")

            ScriptData.set('goTwoStraightLine',
                           {'points': [self.start_pos, self.temp_start, self.second_point, self.world_target]})
        # 如果执行原路返回
        else:
            points = ScriptData.get('goTwoStraightLine').get('points', [])
            Trace.log(f"points after get:{points}", name="fork.task")
            if not points:
                self.action_status = ActionStatus.FAILED
                Navigation.setTaskError("NoRoute", "no route before leave loc, script failed")
                return

            self.temp_start = points[2]  # 退出库位的第一个点，栈板 min_ahead_dist 前置点
            self.second_point = points[1]  # 退出库位第二个点，ahead_dist 点
            self.third_point = points[0]  # 退出库位第三个点，前置点/起始点
            self.check_point = points[3]

    def run(self, ctx=None):
        if self.action_status == ActionStatus.FAILED:
            return

        if not self.init:
            self.init = True

            if self.return_back:
                pos = get_r_loc()
                dist = cal_dist(self.check_point, pos)
                if dist >= 0.5:
                    Navigation.setTaskError("NotAtLastLoadPoint",
                                            "cannot leave loc when robot is not at last load point")
                    self.action_status = ActionStatus.FAILED
                    return
                ScriptData.set('goTwoStraightLine', {})

            self.path_actions = [GoPath(args) for args in self._build_path_args()]
            self.go_step = [False] * len(self.path_actions)

        if self.current_step >= len(self.path_actions):
            self.action_status = ActionStatus.FINISHED
            return

        current = self.path_actions[self.current_step]
        if current.action_status not in [ActionStatus.FINISHED, ActionStatus.FAILED]:
            current.run()
        if current.action_status == ActionStatus.FINISHED:
            self.go_step[self.current_step] = True
            self.current_step += 1
        elif current.action_status == ActionStatus.FAILED:
            self.action_status = ActionStatus.FAILED
            return

        if all(self.go_step):
            self.action_status = ActionStatus.FINISHED

    def _build_path_args(self):
        if self.return_back:
            segments = [
                (self.temp_start, 0, math.radians(1), 0.01),
                (self.second_point, 0, math.radians(1), 0.01),
                (self.third_point, 1, math.radians(1), 0.01),
            ]
        else:
            segments = [
                (self.temp_start, 0, math.radians(1), 0.01),
                (self.second_point, 1, math.radians(0.2), 0.005),
                (self.third_point, 1, math.radians(0.2), 0.005),
            ]
        return [self._build_go_path_args(point, back_mode, reach_angle, reach_dist)
                for point, back_mode, reach_angle, reach_dist in segments]

    @staticmethod
    def _build_go_path_args(point, back_mode, reach_angle, reach_dist):
        return {
            "x": point[0],
            "y": point[1],
            "theta": point[2],
            "backMode": back_mode,
            "maxSpeed": 0.1,
            "maxRot": math.radians(5),
            "coordinate": Coordinate.WORLD.value,
            "reachAngle": reach_angle,
            "reachDist": reach_dist,
        }

    def cal_angle(self, start_pos, end_pos):
        start2end = pos2Base(start_pos, end_pos)
        angle = math.degrees(math.atan2(start2end[1], start2end[0]))
        return angle

    def search_min_angle_str(self, max_angle, step):
        for n in range(1, step + 1):
            adjust_dist = self.ahead_dist / self.step * n
            # 临时构造一个新的起点：在原 start_pos 基础上往前平移
            temp_start = pos2World([adjust_dist, 0, 0], self.start_pos)
            angle = abs(self.cal_angle(temp_start, self.second_point))

            if angle <= max_angle:
                Trace.log(f"满足角度要求，当前角度：{angle:.2f}°，使用第 {n} 次调整", name=f"{MOD}.nav")
                return temp_start

        angle = abs(self.cal_angle(temp_start, self.second_point))
        Trace.log(f"未满足角度要求，当前角度：{angle:.2f}°", name=f"{MOD}.nav")
        return self.start_pos

    def reset(self):
        self.action_status = ActionStatus.RUNNING
        Navigation.resetPath()

    def cancel(self):
        Navigation.resetPath()
        self.action_status = ActionStatus.FAILED

    def _current_action(self):
        if 0 <= self.current_step < len(self.path_actions):
            return self.path_actions[self.current_step]
        return None

    def suspend(self):
        if self.action_status == ActionStatus.RUNNING:
            current_action = self._current_action()
            if current_action is not None:
                current_action.suspend()
            super().suspend()

    def resume(self):
        if self.action_status == ActionStatus.SUSPENDED:
            current_action = self._current_action()
            if current_action is not None:
                current_action.resume()
            super().resume()

    def _trace_state(self) -> dict:
        return {
            "action_status": int(self.action_status),
            "go_step": self.go_step if isinstance(self.go_step, list) else [],
            "current_step": self.current_step,
        }


class GoLiveRec(ActionBase):
    def __init__(self, recfile="default.srec", action_name="GoLiveRec", back_dist=-1.7,
                 ahead_dist=None, min_ahead_dist=None, rec_x=None, rec_y=None, rec_radius=None):
        super().__init__(action_name)
        _init_action_runtime(self)

        self.target_world = [0, 0, 0, -1]
        self.back_dist = back_dist
        self.ahead_dist = _config().aheadDist if ahead_dist is None else ahead_dist
        self.min_ahead_dist = _config().minAheadDist if min_ahead_dist is None else min_ahead_dist
        self.attempts = 0
        self.results_dict = None
        self.rec_status = None
        self.success = False
        self.max_attempts = None
        self.goal = [0, 0, 0]
        self.init = False
        self.action_status = ActionStatus.INIT
        self.task_state = True
        self.doing_rec = True
        self.doing_path = True
        self.live_motion_started = False
        # Variable to store recognition results
        self.rec_result = None
        # Path to the recognition data file
        self.recfile = recfile
        rec_x = _config().recCenterX if rec_x is None else rec_x
        rec_y = _config().recCenterY if rec_y is None else rec_y
        rec_radius = _config().recRadius if rec_radius is None else rec_radius
        self.rec = Rec(self.recfile, rec_center_x=rec_x,
                       rec_center_y=rec_y, rec_radius=rec_radius)

    def run(self, ctx=None):
        self.action_status = ActionStatus.RUNNING
        # Initialize on first run
        if not self.init:
            self.init = True
            self.doing_rec = True
            self.doing_path = True
            self.rec.reset()
            return self.action_status

        # Log current recognition and path planning status
        Trace.log(f"[liveRecScript][{self.doing_rec}|{self.doing_path}]", True, True)

        # Perform recognition if needed
        if self.doing_rec:
            if self.rec.action_status not in [ActionStatus.FAILED, ActionStatus.FINISHED]:
                self.rec.run()
            if self.rec.action_status == ActionStatus.FAILED:
                self.action_status = ActionStatus.FAILED
            if self.rec.action_status == ActionStatus.FINISHED:
                self.doing_rec = False
                self.rec_result = self.rec.result
                Trace.log(f"rec result:{self.rec_result}")
                self.target_world = [self.rec_result["worldResult"]["x"], self.rec_result["worldResult"]["y"],
                                     self.rec_result["worldResult"]["yaw"], ]
            return self.action_status

        # Perform path planning if needed
        if self.doing_path:
            self.doing_path = False
            # Get current robot position
            pos = Loc.getPose()
            Trace.log("pos: " + json.dumps(pos), False, True)

            # Calculate path based on current position and recognition results
            path = Navigation.getRecPath(
                robot_pos_x=0,
                robot_pos_y=0,
                robot_pos_theta=0,
                rec_x=self.rec_result["robotResult"]["x"],
                rec_y=self.rec_result["robotResult"]["y"],
                rec_theta=self.rec_result["robotResult"]["yaw"],
                back_dist=self.back_dist,
                min_ahead_dist=self.min_ahead_dist,
                ahead_dist=self.ahead_dist,
                back_mode=True,
                use_bezier=True,
                hold_dir=999,
                max_speed=0.1,
                slow_down_dist=0.5,
                slow_down_speed=0.05,
                liveRec=True)
            Trace.log("path: " + json.dumps(path))

            # Reset and prepare for movement
            if not Navigation.liveRecGoReset(
                    recfile=self.recfile,
                    x=self.rec_result["robotResult"]["x"],
                    y=self.rec_result["robotResult"]["y"],
                    theta=self.rec_result["robotResult"]["yaw"],
                    tracker_id=self.rec_result["trackerId"],
                    paths=path):
                Trace.log("liveRecGoReset fail!")
                self.action_status = ActionStatus.FAILED
                return self.action_status
            self.live_motion_started = True

        Trace.log(Navigation.getLiveResult())

        # Execute the planned movement
        self.action_status = Navigation.liveRecGo()
        Trace.log(f"liveRecGoStatus: {self.action_status}")
        return self.action_status

    def cancel(self):
        self.live_motion_started = False
        self.action_status = ActionStatus.FAILED
        Navigation.cancelLiveRecGo()

    def reset(self):
        self.live_motion_started = False
        self.action_status = ActionStatus.RUNNING

    def suspend(self):
        if self.action_status == ActionStatus.RUNNING:
            if self.live_motion_started:
                Navigation.stopRobotNow()
            super().suspend()

    def resume(self):
        super().resume()


class GoPathWithContactDi(ActionBase):
    """执行取放货近距离路径，并在运动期间管理叉尖传感器和导航策略。

    初始化时只构建底层路径 action；run 按 tick 推进路径、切换避障策略、处理放货
    防撞 DI 和取货到位 DI，进入成功或失败终态后统一恢复激光宽度、策略和路径缓存。
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
            reach_phase_config: Optional[Dict] = None,
            obs_dist_compensation: float = 0.0,
            recfile: str = "",
            initial_policy_name: str = "loadPolicy",
    ):
        super().__init__()
        _init_action_runtime(self)
        if args is None:
            args = {}
        self.di_filter_time = 1
        self.check_di = check_di
        self.check_all_contact_di = _config().checkAllContactDis
        self.operation_type = operation_type
        self.recfile = recfile or ""
        self.initial_policy_name = initial_policy_name or "loadPolicy"
        self.use_recfile_collision_policy = bool(getattr(
            getattr(_config(), "active_fork_class", None),
            "use_recfile_collision_policy",
            False,
        ))
        self.fork_root_collision_models: Optional[List[Dict[str, Any]]] = None
        self.fork_root_collision_model_error = ""
        self.initial_motion_policy = None
        self.near_motion_policy = None
        self.laser_id = []
        self.laser_width = None
        self.walk_dist = None
        self.action_status = ActionStatus.INIT
        self.di_status = []
        self.contact_di = [d for d in contact_dis if d]
        self.fork_tip_di_ids = self._load_fork_tip_di_ids()
        self.di_triggered_stopped = False
        self.di_trigger_start_time = None
        self.di_clear_start_time = None
        self.contact_di_finish_wait_start_time = None
        self.contact_di_partial_wait_start_time = None
        self._last_contact_di_trace_state = None
        self._last_contact_di_trace_time = None

        self.target_pos = world_pos
        if self.check_di and not self.contact_di:
            Navigation.setTaskError("ContactDiNone", f"check di is True in recfile, but contact di is none")
            self.action_status = ActionStatus.FAILED
        self.goal = [0, 0, 0]
        self.init = False
        self.obs_dist = obs_dist
        self.obs_dist_compensation = max(0.0, float(obs_dist_compensation or 0.0))
        self.start_loc = None
        self.method = method
        self.di_trigger_time = 1
        self.set_policy = False
        self.clear_policy = False
        self.policy = {}
        self.motion_target = [world_pos[0], world_pos[1], world_pos[2]]
        self.policy_unloaded_obs_dist = RobotParam.getConfig(
            "navigation", "obstacleStop.obsStopUnload.obsStopDist"
        )
        self.policy_loaded_obs_dist = RobotParam.getConfig(
            "navigation", "obstacleStop.obsStopLoad.loadObsStopDist"
        )
        self.policy["navigation.freeBypass"] = "off"
        self.reach_phase_config = dict(reach_phase_config or {})
        self.reach_phase_enabled = bool(self.reach_phase_config)
        self.reach_phase = "direct_path"
        self.reach_action = None
        self.reach_motor_names = []
        self.reach_target = "max"
        self.reach_max_speed = 0.0
        self.reach_sync_tolerance = 0.0
        self.reach_align_use_geometry = False
        self.reach_align_long_thresh = 0.0
        self.reach_final_back_mode = None
        self.reach_final_obs_dist_compensation = self.obs_dist_compensation
        self.align_world_pos = world_pos
        self.align_method = method
        self.align_args = dict(args)
        self.final_world_pos = world_pos

        Trace.log(f"go path with di target pos:{world_pos},args:{args}", name="fork.task")
        if self.reach_phase_enabled:
            self._initialize_reach_phase_plan(world_pos, method, args)
        # 三种路径模式在初始化阶段固定为一个 back_action，run 中只推进其状态机。
        self._build_back_action(self.align_method, self.align_world_pos, self._resolve_back_dist(self.align_args), self.align_args)

    def _initialize_reach_phase_plan(self, world_pos, method, args) -> None:
        self.reach_phase = "align_path"
        # pathFirst 的“对齐完成”与 softbag 对齐：
        # 对 bezier / straightLine 这类“目标仍是托盘位姿”的路径，
        # 运行中按 offset[0] <= ConfigParams.tail 的几何门槛判定已到前置对齐位，
        # 一旦到位就停车并切到前移机构阶段，避免第一段曲线继续把车体带进托盘。
        # goPath 模式本身就直接给了明确的前置位目标，因此仍按第一段 action 完成切段。
        self.align_world_pos = self.reach_phase_config.get("align_world_pos") or world_pos
        self.align_method = str(self.reach_phase_config.get("align_method") or method)
        self.align_args = dict(self.reach_phase_config.get("align_args") or args or {})
        self.final_world_pos = self.reach_phase_config.get("final_world_pos") or world_pos
        self.reach_motor_names = [
            str(name).strip()
            for name in (self.reach_phase_config.get("motor_names") or [])
            if str(name).strip()
        ]
        self.reach_target = self.reach_phase_config.get("target", "max")
        self.reach_max_speed = float(
            self.reach_phase_config.get("max_speed", getattr(_config(), "reachMotorMaxSpeed", 0.1))
        )
        self.reach_sync_tolerance = float(
            self.reach_phase_config.get("sync_tolerance", getattr(_config(), "reachMotorSyncTolerance", 0.02))
        )
        self.reach_align_long_thresh = float(
            self.reach_phase_config.get("align_long_thresh", getattr(_config(), "tail", 0.0))
        )
        self.reach_align_use_geometry = bool(
            self.reach_phase_config.get("align_use_geometry", self.align_method != "goPath")
        )
        final_back_mode = self.reach_phase_config.get("final_back_mode")
        self.reach_final_back_mode = None if final_back_mode is None else int(final_back_mode)
        self.reach_final_obs_dist_compensation = max(
            0.0,
            float(self.reach_phase_config.get("final_obs_dist_compensation", self.obs_dist_compensation) or 0.0),
        )
        Trace.log(
            f"enable staged reach path: align_method={self.align_method}, "
            f"align_target={self.align_world_pos}, final_target={self.final_world_pos}, "
            f"reach_motors={self.reach_motor_names}, align_use_geometry={self.reach_align_use_geometry}, "
            f"align_long_thresh={self.reach_align_long_thresh}, final_back_mode={self.reach_final_back_mode}, "
            f"final_obs_comp={self.reach_final_obs_dist_compensation}",
            name="fork.task",
        )

    def _check_di_active(self) -> bool:
        if not self.check_di:
            return False
        if not self.reach_phase_enabled:
            return True
        return self.reach_phase == "final_path"

    def _load_fork_tip_di_ids(self) -> List[str]:
        di_ids = []
        for sensor_name in (_config().fork_tip_di_sensors or []):
            # Most models bind a sensor object whose basic.id is the actual
            # DI key.  Some models bind the DI device directly and therefore
            # have no basic.id; in that case the configured key is already
            # what Di.getDi expects.
            di_id = RobotParam.getDevice(sensor_name, "basic.id") or sensor_name
            if di_id and di_id not in di_ids:
                di_ids.append(di_id)
        return di_ids

    def _resolve_back_dist(self, args) -> float:
        back_dist = args.get("back_dist", 0.0)
        # 识别取货依赖接触 DI 时多走 forkDiDist，保证叉尖能够真正触发到位信号。
        if self._check_di_active() and self.operation_type == "load":
            back_dist += _config().forkDiDist
        return back_dist

    def _build_back_action(self, method, world_pos, back_dist, args):
        if method == "goPath":
            self._build_go_path_back_action(world_pos)
            return
        if method == "bezier":
            self._build_bezier_back_action(world_pos, back_dist, args)
            return
        if method == "straightLine":
            self._build_straight_line_back_action(world_pos, back_dist, args)
            return
        Navigation.setTaskError("WrongGoPathMethod", f"wrong gopath method :{method}, script failed")
        self.action_status = ActionStatus.FAILED

    def _build_go_path_back_action(self, world_pos, back_mode_override=None):
        if self._check_di_active() and self.operation_type == "load":
            target_pos = pos2World([-_config().forkDiDist, 0, 0], world_pos)
        else:
            target_pos = world_pos
        self.final_target = target_pos
        self.motion_target = target_pos

        Trace.log(f"go path with di target pos:{target_pos}", name="fork.task")
        self.back_args = {
            "x": target_pos[0],
            "y": target_pos[1],
            "theta": target_pos[2],
            "coordinate": "world",
            "backMode": 1,
            "maxRot": 10,
            "maxSpeed": 0.15,
            "useOdo": 0,
            "reachAngle": math.radians(0.5),
            "reachDist": 0.005,
        }
        # goPath 没有固定的进叉方向，根据建路时机器人与目标的相对位置选择前进或后退。
        if back_mode_override is None:
            target2robot = pos2Base(world_pos, get_r_loc())
            if target2robot[0] > 0:
                self.back_args["backMode"] = 0
        else:
            self.back_args["backMode"] = int(back_mode_override)
        self.back_action = GoPath(self.back_args)

    def _get_effective_obs_stop_dist(self) -> Optional[float]:
        if self.obs_dist is None and self.obs_dist_compensation <= 0:
            return None
        if self.obs_dist is None:
            base_dist = self._default_obs_stop_dist()
        else:
            base_dist = self.obs_dist
        try:
            return max(0.0, float(base_dist or 0.0) + self.obs_dist_compensation)
        except (TypeError, ValueError):
            return None

    def _should_use_obs_compensation_now(self) -> bool:
        if self.obs_dist_compensation <= 0:
            return False
        if not self.reach_phase_enabled:
            return True
        return self.reach_phase == "final_path"

    def _set_obs_stop_dist_for_phase(self, use_compensation: bool) -> None:
        if use_compensation:
            effective_obs_dist = self._get_effective_obs_stop_dist()
            if effective_obs_dist is not None:
                self._set_obs_stop_dist(effective_obs_dist)
                return
        if self.obs_dist is not None:
            self._set_obs_stop_dist(self.obs_dist)

    def _start_final_path(self) -> None:
        self.reach_phase = "final_path"
        self.target_pos = self.final_world_pos
        if abs(self.reach_final_obs_dist_compensation - self.obs_dist_compensation) > EPS:
            self.obs_dist_compensation = self.reach_final_obs_dist_compensation
        if self.init:
            self._set_obs_stop_dist_for_phase(self._should_use_obs_compensation_now())
            self._apply_policy("reachFinalPolicy")
            self.clear_policy = False
            self.set_policy = True
        self._build_go_path_back_action(self.final_world_pos, back_mode_override=self.reach_final_back_mode)
        Trace.log(
            f"staged reach path enter final goPath, target:{self.final_world_pos}, "
            f"motion_target:{self.motion_target}, back_mode:{self.reach_final_back_mode}, "
            f"obs_stop_dist:{self._get_effective_obs_stop_dist()}",
            name="fork.task",
        )

    def _build_reach_phase_action(self):
        if not self.reach_motor_names:
            Navigation.setTaskError("ReachMotorMissing", "reach motor is not configured for staged pathFirst")
            self.action_status = ActionStatus.FAILED
            return None
        return RunReachMotorsByPosition(
            self.reach_motor_names,
            self.reach_target,
            self.reach_max_speed,
            self.reach_sync_tolerance,
            contact_di=[],
            check_all_di=False,
            action_name="extendReachMotors",
        )

    def _is_reach_aligned_by_geometry(self) -> bool:
        if not self.reach_phase_enabled or self.reach_phase != "align_path":
            return False
        if not self.reach_align_use_geometry:
            return False
        # 与 softbag 一致：target_pos 仍是托盘/识别目标位姿，offset[0] 代表
        # 机器人沿目标轴线距离目标前缘还剩的纵向距离；小于 tail 认为已到前置对齐位。
        offset = pos2Base(get_r_loc(), self.target_pos)
        return offset[0] <= self.reach_align_long_thresh

    def _transition_align_to_reach(self, reason: str) -> None:
        Navigation.stopRobotNow()
        Navigation.resetPath()
        if self.back_action is not None:
            self.back_action.action_status = ActionStatus.FINISHED
        self.reach_phase = "reach"
        self.target_pos = self.final_world_pos
        Trace.log(
            f"staged reach path aligned by {reason}, start extend reach motors",
            name="fork.task",
        )

    def _build_bezier_back_action(self, world_pos, back_dist, args):
        self.motion_target = pos2World([-back_dist, 0, 0], world_pos)
        self.back_action = GoBezier.GoBezierWorld(
            world_pos,
            back_dist,
            args["adjust_dist"],
            args["min_ahead_dist"],
            True,
            None,
            0.1,
            0.3,
            0.2,
            0.5,
            args["max_curve"],
        )
        self.final_target = pos2World([-args["back_dist"], 0, 0], world_pos)
        Trace.log(f"goBezier target pos:{self.final_target}", name="fork.task")

    def _build_straight_line_back_action(self, world_pos, back_dist, args):
        self.back_action = GoTwoStraightLine(
            world_pos,
            args["min_ahead_dist"],
            args["adjust_dist"],
            back_dist,
            0.2,
            args["max_angle"],
            1,
        )
        self.final_target = pos2World([-args["back_dist"], 0, 0], world_pos)
        self.motion_target = pos2World([-back_dist, 0, 0], world_pos)
        Trace.log(f"twoStraightLine target pos:{self.final_target}", name="fork.task")

    def _get_fork_root_laser_keys(self) -> List[str]:
        return get_fork_root_laser_keys()

    def _fail_action(
            self,
            task_error_key: str,
            task_error_msg: str,
            *,
            robot_error_key: Optional[str] = None,
            robot_error_msg: Optional[str] = None,
    ) -> None:
        Navigation.setTaskError(task_error_key, task_error_msg)
        if robot_error_key:
            RobotError.setSystemError(
                robot_error_key,
                robot_error_msg or task_error_msg,
                True,
            )
        self.action_status = ActionStatus.FAILED

    def _finish_by_stop_robot(self) -> bool:
        if self.stop_robot():
            self.action_status = ActionStatus.FINISHED
            return True
        return False

    def _should_shield_fork_tip_di(self) -> bool:
        if not _config().fork_tip_di_sensors:
            return False
        if self.operation_type == "load":
            return not _config().forkDiEnableAtLoad
        if self.operation_type == "unload":
            # autoClearError/failTask are script-owned modes.  Leaving the DI
            # in navigation collision detection lets the collision layer win
            # the race, so neither scripted behavior can take effect.
            return (
                not _config().forkDiEnableAtUnload
                or _config().diTriggerMeasureUnload != "collision"
            )
        return True

    def _ensure_unload_collision_devices(self) -> None:
        """Make collision mode self-contained instead of relying on global config."""
        if not (
                self.operation_type == "unload"
                and _config().forkDiEnableAtUnload
                and _config().diTriggerMeasureUnload == "collision"
        ):
            return
        policy_devices = self.policy.get("navigation.collisionDetection.detectionDevice")
        current_collision_devices = (
            split_device_keys(policy_devices)
            if policy_devices is not None
            else self._load_collision_devices()
        )
        changed = False
        for sensor_name in (_config().fork_tip_di_sensors or []):
            if sensor_name and sensor_name not in current_collision_devices:
                current_collision_devices.append(sensor_name)
                changed = True
        if changed:
            collision_device_str = ",".join(current_collision_devices)
            self.policy["navigation.collisionDetection.detectionDevice"] = collision_device_str
            Trace.log(
                f"enabled unload fork-tip collision devices:{collision_device_str}",
                name="fork.task",
            )

    def _load_collision_devices(self) -> List[str]:
        current_collision_device_str = RobotParam.getConfig(
            "navigation", "collisionDetection.detectionDevice"
        )
        return [
            device.strip()
            for device in str(current_collision_device_str or "").split(",")
            if device.strip()
        ]

    def _load_navigation_collision_devices(self) -> List[str]:
        current_collision_device_str = RobotParam.getConfig(
            "navigation", "collisionDetection.collisionDevice"
        )
        return split_device_keys(current_collision_device_str)

    def _apply_collision_device_shielding(
            self,
            should_shield_di: bool,
            *,
            shield_fork_root: bool = True,
    ) -> None:
        fork_root_laser_keys = self._get_fork_root_laser_keys()
        if (not fork_root_laser_keys or not shield_fork_root) and not should_shield_di:
            return

        current_collision_device = self._load_collision_devices()
        original_collision_device = list(current_collision_device)
        Trace.log(f"current_collision_device:{current_collision_device}", name="fork.task")

        # 进入货物近场后，叉根激光和按配置关闭的叉尖 DI 不再参与全局碰撞检测；
        # 叉尖到位判断仍由本 action 独立处理，避免导航层与业务层重复抢停。
        if shield_fork_root:
            for laser_key in fork_root_laser_keys:
                while laser_key in current_collision_device:
                    current_collision_device.remove(laser_key)
        if should_shield_di:
            for di_sensor in _config().fork_tip_di_sensors:
                while di_sensor in current_collision_device:
                    current_collision_device.remove(di_sensor)

        if current_collision_device == original_collision_device:
            return

        current_collision_device_str = ",".join(current_collision_device)
        self.policy["navigation.collisionDetection.detectionDevice"] = current_collision_device_str
        Trace.log(
            f"shielded collision devices, new collision device:{current_collision_device_str}",
            name="fork.task",
        )

    def _apply_navigation_collision_device_shielding(self, collision_devices: List[str]) -> None:
        if not collision_devices:
            return

        current_collision_devices = self._load_navigation_collision_devices()
        remaining_collision_devices = [
            device for device in current_collision_devices if device not in collision_devices
        ]
        if remaining_collision_devices == current_collision_devices:
            return

        collision_device_str = ",".join(remaining_collision_devices)
        self.policy["navigation.collisionDetection.collisionDevice"] = collision_device_str
        Trace.log(
            f"shielded navigation collision devices:{collision_devices}, remaining:{collision_device_str}",
            name="fork.task",
        )

    def _load_fork_root_collision_models(self) -> Optional[List[Dict[str, Any]]]:
        """Load the collision regions/devices explicitly configured by the recognition file."""
        self.fork_root_collision_model_error = ""
        if not self.recfile:
            return []

        recognition_collision_model_path = "recognitionObject.pallet.collisionModel"
        try:
            size = RobotParam.getConfigCloneSize(
                "recognition", recognition_collision_model_path, self.recfile
            )
            matched_models = []
            for idx in range(size):
                collision_device = str(RobotParam.getConfig(
                    "recognition",
                    f"{recognition_collision_model_path}._{idx}.collisionDevice",
                    self.recfile,
                ) or "").strip()
                if not collision_device:
                    continue
                collision_shape = RobotParam.getConfig(
                    "recognition",
                    f"{recognition_collision_model_path}._{idx}.collisionShape",
                    self.recfile,
                )
                if not collision_shape:
                    continue
                matched_models.append({
                    "collisionDevice": collision_device,
                    "collisionShape": collision_shape,
                })
        except Exception as exc:
            self.fork_root_collision_model_error = f"read collisionModel from recfile failed: {exc}"
            return None

        return matched_models

    def _get_fork_root_collision_models(self) -> Optional[List[Dict[str, Any]]]:
        if self.fork_root_collision_models is None:
            self.fork_root_collision_models = self._load_fork_root_collision_models()
        return self.fork_root_collision_models

    def _set_obs_stop_dist(self, stop_dist: float) -> None:
        self.policy[self._active_obs_stop_dist_key()] = stop_dist

    def _set_default_obs_stop_dist(self) -> None:
        self.policy[self._active_obs_stop_dist_key()] = self._default_obs_stop_dist()

    def _active_obs_stop_dist_key(self) -> str:
        # 取货进叉期间尚未置为载货，生效的是空载停车距离；放货期间仍是
        # 载货状态，生效的是载货停车距离。不要同时写两个字段，否则取货
        # 调整阶段会把无关的载货配置（历史上甚至是 None）带入自定义策略。
        if self.operation_type == "unload":
            return "navigation.obstacleStop.obsStopLoad.loadObsStopDist"
        return "navigation.obstacleStop.obsStopUnload.obsStopDist"

    def _default_obs_stop_dist(self):
        if self.operation_type == "unload":
            return self.policy_loaded_obs_dist
        return self.policy_unloaded_obs_dist

    def _apply_policy(self, policy_name: str, *, sleep_sec: float = 0.0, reset_path: bool = False) -> None:
        Navigation.appendCustomPolicy(policy_name, self.policy)
        if sleep_sec > 0:
            time.sleep(sleep_sec)
        if reset_path:
            Navigation.goPathParam(dict())

    def _configure_initial_policy(self) -> bool:
        # 近货阶段关闭自由绕行并使用取放货停车距离，防止局部规划绕开目标货物。
        should_shield_di = self._should_shield_fork_tip_di()
        collision_models_enabled = (
            self.use_recfile_collision_policy
            and self.operation_type == "load"
        )
        initial_navigation_collision_devices = []
        fork_root_collision_models = []
        collision_model_devices = []
        if collision_models_enabled:
            initial_navigation_collision_devices = self._load_navigation_collision_devices()
            fork_root_collision_models = self._get_fork_root_collision_models()
            if fork_root_collision_models is None:
                err_msg = self.fork_root_collision_model_error or "fork root collision model is invalid"
                Navigation.setTaskError("ForkRootCollisionModelInvalid", err_msg)
                self.action_status = ActionStatus.FAILED
                Trace.log(err_msg, name="fork.err")
                return False
            if fork_root_collision_models:
                self.policy["navigation.collisionDetection.collisionModel"] = fork_root_collision_models
                collision_model_devices = list(dict.fromkeys(
                    device
                    for model in fork_root_collision_models
                    for device in split_device_keys(model["collisionDevice"])
                ))
                Trace.log(
                    f"apply fork root collision model policy: models={fork_root_collision_models}",
                    name="fork.task",
                )
            else:
                Trace.log(
                    "recognition file has no collision model; remove fork root lasers from collision devices",
                    name="fork.task",
                )

        # PickFork 的识别文件将碰撞设备单独列在 collisionDevice；初始化阶段从
        # 导航 collisionDevice 中移除这些设备，近货阶段再恢复原始列表。
        self._apply_collision_device_shielding(
            should_shield_di,
            shield_fork_root=not bool(collision_model_devices),
        )
        self._ensure_unload_collision_devices()
        self._apply_navigation_collision_device_shielding(collision_model_devices)
        self._set_obs_stop_dist_for_phase(self._should_use_obs_compensation_now())
        self.policy["navigation.obstacleStop.obsStopUnload.obsExpansion"] = 0.02
        self.policy["navigation.obstacleStop.obsStopLoad.loadObsExpansion"] = 0.01
        if collision_models_enabled:
            self.initial_motion_policy = copy.deepcopy(self.policy)
            self.near_motion_policy = copy.deepcopy(self.policy)
            self.near_motion_policy[
                "navigation.collisionDetection.collisionDevice"
            ] = ",".join(initial_navigation_collision_devices)
        self._apply_policy(self.initial_policy_name, sleep_sec=0.5)
        self.set_policy = True

        current_collision_device_change = RobotParam.getConfig(
            "navigation", "collisionDetection.detectionDevice"
        )
        unload_stop_dist = RobotParam.getConfig("navigation", "obstacleStop.obsStopUnload.obsStopDist")
        Trace.log(
            f"policy :{self.policy},current_collision_device_change:{current_collision_device_change}, cur_unload_stop_dist:{unload_stop_dist}",
            name="fork.task",
        )
        return True

    def _initialize_motion(self) -> None:
        self.init = True
        # start_loc 仅用于运行状态记录；路径目标已经在 __init__ 中按当时位姿构建完成。
        self.start_loc = get_r_loc()
        Trace.log(f"fork tip 2d laser:{_config().fork_tip_2D_lasers}", name="fork.task")
        if self.obs_dist is not None and _config().fork_tip_2D_lasers:
            for laser in _config().fork_tip_2D_lasers:
                Trace.log(f"set2DLaserWidth:{laser}", name="fork.task")
                Laser.set2DLaserWidth(laser, _config().laserDetectionWidth)
        Trace.log(
            f"fork tip di sensors:{_config().fork_tip_di_sensors}, "
            f"fork_tip_di_ids:{self.fork_tip_di_ids}, operation_type:{self.operation_type}",
            name="fork.task",
        )
        if not self._configure_initial_policy():
            back_action = getattr(self, "back_action", None)
            if back_action is not None:
                back_action.action_status = ActionStatus.FAILED

    def _advance_back_action(self) -> bool:
        if self.reach_phase_enabled and self.reach_phase == "reach":
            if self.reach_action is None:
                self.reach_action = self._build_reach_phase_action()
                if self.reach_action is None:
                    return False
            if self.reach_action.action_status not in [ActionStatus.FAILED, ActionStatus.FINISHED]:
                self.reach_action.run()
            if self.reach_action.action_status == ActionStatus.FAILED:
                self.action_status = ActionStatus.FAILED
                return False
            return True
        back_action = getattr(self, "back_action", None)
        if back_action is None:
            self.action_status = ActionStatus.FAILED
            return False
        if back_action.action_status not in [ActionStatus.FAILED, ActionStatus.FINISHED]:
            back_action.run()
        if back_action.action_status == ActionStatus.FAILED:
            self.action_status = ActionStatus.FAILED
            return False
        return True

    def _sync_motion_policy(self) -> None:
        vx = NavSpeed.getSpeeds()[0]
        # 调整段出现前进速度时恢复默认停车距离；重新进入进叉方向后切回近货策略。
        if vx > 0.005 and not self.clear_policy:
            self._set_default_obs_stop_dist()
            self._apply_policy("forwardPolicy")
            self.clear_policy = True
            self.set_policy = False
            Trace.log(f"vx:{vx},set forward policy:{self.policy}", name=f"{MOD}.nav")
            return
        if vx <= 0 and not self.set_policy:
            near_motion_policy = getattr(self, "near_motion_policy", None)
            if near_motion_policy is not None:
                self.policy = copy.deepcopy(near_motion_policy)
            else:
                self._set_obs_stop_dist_for_phase(self._should_use_obs_compensation_now())
            self._apply_policy("policy", sleep_sec=0.2, reset_path=True)
            self.clear_policy = False
            self.set_policy = True
            Trace.log(f"vx:{vx},set load policy:{self.policy}", name=f"{MOD}.nav")

    def _should_handle_unload_tip_di(self) -> bool:
        return bool(
            self.operation_type == "unload"
            and _config().forkDiEnableAtUnload
            and self.fork_tip_di_ids
            and _config().diTriggerMeasureUnload != "collision"
        )

    def _handle_unload_tip_di_auto_clear(self, di_triggered: bool) -> None:
        # 放货遇到叉尖 DI 连续触发 0.3 s 先停车报错；连续释放 0.3 s 后清错续走。
        if di_triggered:
            if self.di_trigger_start_time is None:
                self.di_trigger_start_time = time.time()
            elif time.time() - self.di_trigger_start_time > 0.3:
                if not self.di_triggered_stopped:
                    Navigation.stopRobotNow()
                    Navigation.setTaskError("ForkTipDiTrigger", "unload fork tip di triggered, goods detected")
                    self.di_triggered_stopped = True
                    Trace.log("autoClearError: fork tip di triggered, stopped robot", name="fork.err")
                self.di_clear_start_time = None
            return

        self.di_trigger_start_time = None
        if not self.di_triggered_stopped:
            self.di_clear_start_time = None
            return
        if self.di_clear_start_time is None:
            self.di_clear_start_time = time.time()
            return
        if time.time() - self.di_clear_start_time <= 0.3:
            return
        if Navigation.errorExists("ForkTipDiTrigger"):
            Navigation.clearTaskError("ForkTipDiTrigger")
        Navigation.goPathParam(dict())
        self.di_triggered_stopped = False
        self.di_clear_start_time = None
        Trace.log("autoClearError: fork tip di cleared, resumed robot", name="fork.task")

    def _handle_unload_tip_di_fail_task(self, di_triggered: bool) -> bool:
        # failTask 模式同样做 0.3 s 去抖，但触发后终止整个 action，不自动恢复。
        if not di_triggered:
            self.di_trigger_start_time = None
            return False
        if self.di_trigger_start_time is None:
            self.di_trigger_start_time = time.time()
            return False
        if time.time() - self.di_trigger_start_time <= 0.3:
            return False
        Navigation.stopRobotNow()
        Navigation.setTaskError("UnloadTipDiFail", "unload fork tip di triggered, fail task")
        self.action_status = ActionStatus.FAILED
        Trace.log("failTask: fork tip di triggered, failed task", name="fork.err")
        return True

    def _handle_unload_tip_di(self) -> bool:
        if not self._should_handle_unload_tip_di():
            return False
        di_triggered = any(Di.getDi(di_id) for di_id in self.fork_tip_di_ids)
        if _config().diTriggerMeasureUnload == "autoClearError":
            self._handle_unload_tip_di_auto_clear(di_triggered)
            return False
        if _config().diTriggerMeasureUnload == "failTask":
            return self._handle_unload_tip_di_fail_task(di_triggered)
        return False

    def _distance_to_final_target(self):
        return pos2Base(get_r_loc(), self.final_target)

    def _delay_with_local_timer(self, attr_name: str, second: float, enabled: bool) -> bool:
        if not enabled:
            setattr(self, attr_name, None)
            return False
        now = time.time()
        start_time = getattr(self, attr_name, None)
        if start_time is None:
            setattr(self, attr_name, now)
            return False
        if now - start_time > second:
            setattr(self, attr_name, None)
            return True
        return False

    def _handle_any_contact_di(self, dist2target) -> bool:
        if dist2target[0] > 0.2 and any(self.di_status):
            self._fail_action(
                "NotReachGoal",
                f"reach di not reach goal, still {dist2target[0]}m left, ",
                robot_error_key="NoContactDiTriger",
                robot_error_msg="not trigger di but robot reach goal",
            )
            return True
        if any(self.di_status):
            self.contact_di_finish_wait_start_time = None
            self.contact_di_partial_wait_start_time = None
            return self._finish_by_stop_robot()
        if self._delay_with_local_timer(
                "contact_di_finish_wait_start_time",
                1,
                self.back_action.action_status == ActionStatus.FINISHED and not all(self.di_status),
        ):
            self._fail_action(
                "NoContactDiTriger",
                "not trigger di but robot reach goal",
                robot_error_key="NoContactDiTriger",
            )
            return True
        return False

    def _handle_all_contact_di(self, dist2target) -> bool:
        if dist2target[0] > 0.2 and all(self.di_status):
            self._fail_action(
                "NotReachGoal",
                f"reach di not reach goal, still {dist2target[0]:.2f}m left, ",
                robot_error_key="NotReachGoal",
            )
            return True
        if all(self.di_status):
            self.contact_di_finish_wait_start_time = None
            self.contact_di_partial_wait_start_time = None
            return self._finish_by_stop_robot()
        if self._delay_with_local_timer(
                "contact_di_finish_wait_start_time",
                1,
                self.back_action.action_status == ActionStatus.FINISHED and not any(self.di_status),
        ):
            self._fail_action(
                "NoContactDiTriger",
                "not trigger di but robot reach goal",
                robot_error_key="NoContactDiTriger",
            )
            return True
        if not any(self.di_status):
            return False
        if self._delay_with_local_timer(
                "contact_di_partial_wait_start_time",
                self.di_trigger_time,
                any(self.di_status) and not all(self.di_status),
        ):
            self._fail_action(
                "NoAllContactDiTriger",
                "not all di triggered but robot reach goal",
                robot_error_key="NoAllContactDiTriger",
            )
            return True
        return False

    def _read_contact_di(self) -> List[bool]:
        """读取到位 di 状态。仿真无到位传感器，Di.getDi 恒 False，会误报
        NoContactDiTriger；仿真下按几何到位模拟——机器人接近 final_target 到阈值内即
        视为 di 触发，从而走完整的"接近→到位→di 触发→成功"路径。实机走真实读数。"""
        if self.contact_di:
            try:
                from tests.fork_sim_inject import is_simulation, sim_contact_di_triggered
                if is_simulation():
                    dist2target = self._distance_to_final_target()
                    if sim_contact_di_triggered(dist2target):
                        return [True for _ in self.contact_di]
            except Exception:  # noqa: BLE001
                pass
        return [Di.getDi(d) for d in self.contact_di]

    def _trace_contact_di_process(self, dist2target) -> None:
        """Log DI processing on state changes, with a bounded idle heartbeat."""
        back_action_status = self.back_action.action_status
        trace_state = (
            tuple(bool(status) for status in self.di_status),
            getattr(back_action_status, "value", back_action_status),
        )
        now = time.monotonic()
        unchanged = trace_state == self._last_contact_di_trace_state
        if unchanged and self._last_contact_di_trace_time is not None and now - self._last_contact_di_trace_time < 1.0:
            return

        _trace_log(
            f"contact_di_process: status={self.di_status}, back_action_status={back_action_status}, "
            f"dist2target={dist2target}"
        )
        self._last_contact_di_trace_state = trace_state
        self._last_contact_di_trace_time = now

    def _handle_contact_di_completion(self) -> None:
        if self.reach_phase_enabled and self.reach_phase != "final_path":
            return
        if not self._check_di_active():
            # 不检查到位 DI 时，包装 action 直接跟随底层路径的终态。
            self.action_status = ActionStatus(self.back_action.action_status.value)
            return

        # 检查模式下，路径走完不等于成功，还需结合距目标距离和任意/全部 DI 规则判定。
        self.di_status = self._read_contact_di()
        dist2target = self._distance_to_final_target()
        self._trace_contact_di_process(dist2target)
        if not self.check_all_contact_di:
            self._handle_any_contact_di(dist2target)
            return
        self._handle_all_contact_di(dist2target)

    def _cleanup_terminal_state(self) -> None:
        if self.action_status not in [ActionStatus.FINISHED, ActionStatus.FAILED]:
            return
        # 只在终态恢复现场配置，RUNNING 时策略必须跨 tick 保持，不能每轮反复清空。
        Laser.clear2DLaserWidth(_config().fork_tip_2D_lasers)
        Navigation.clearPolicy()
        Navigation.resetPath()

    def _handle_motion_extensions(self) -> bool:
        if self.reach_phase_enabled:
            if self.reach_phase == "align_path":
                if self._is_reach_aligned_by_geometry():
                    self._transition_align_to_reach("geometry threshold")
                    return True
                if self.back_action.action_status == ActionStatus.FINISHED:
                    self._transition_align_to_reach("align path finished")
                    return True
            if self.reach_phase == "reach" and self.reach_action is not None and self.reach_action.action_status == ActionStatus.FINISHED:
                self._start_final_path()
                return True
        return False

    def _trace_extra_state(self) -> Dict[str, object]:
        return {}

    def run(self, ctx=None):
        self.action_status = ActionStatus.RUNNING
        try:
            # 1. 首个 tick 配置叉尖激光宽度、碰撞设备屏蔽和近货停车策略。
            if not self.init:
                self._initialize_motion()

            # 2. 推进实际路径；底层失败时不再执行后续 DI 和策略判断。
            if not self._advance_back_action():
                return

            # 3. 预留给车型扩展运动（例如额外机构联动），基类默认不拦截。
            if self._handle_motion_extensions():
                return

            # 4. 随路径方向切换避障策略，再分别处理放货防撞 DI 和取货到位 DI。
            self._sync_motion_policy()
            if self._handle_unload_tip_di():
                return

            self._handle_contact_di_completion()
        finally:
            self._cleanup_terminal_state()

    def reset(self):
        self.action_status = ActionStatus.RUNNING

    def _current_motion_action(self):
        if self.reach_phase_enabled and self.reach_phase == "reach":
            return self.reach_action
        return getattr(self, "back_action", None)

    def suspend(self):
        if self.action_status == ActionStatus.RUNNING:
            current_action = self._current_motion_action()
            if current_action is not None:
                current_action.suspend()
            super().suspend()

    def resume(self):
        if self.action_status == ActionStatus.SUSPENDED:
            current_action = self._current_motion_action()
            if current_action is not None:
                current_action.resume()
            super().resume()

    def stop_robot(self):
        Navigation.stopRobotNow()
        Navigation.resetPath()
        return True

    def cancel(self):
        # 取消先传递给具体路径 action；本包装标记完成，交由任务框架退出当前动作。
        back_action = getattr(self, "back_action", None)
        if back_action is not None:
            back_action.cancel()
        if self.reach_action is not None:
            self.reach_action.cancel()
        self.action_status = ActionStatus.FINISHED

    def _trace_state(self) -> dict:
        state = {
            "action_status": int(self.action_status),
            "di_status": self.di_status,
            "di_triggered_stopped": self.di_triggered_stopped,
            "set_policy": self.set_policy,
            "clear_policy": self.clear_policy,
            "goal": self.goal if isinstance(self.goal, list) else [],
            "reach_phase": self.reach_phase,
        }
        state.update(self._trace_extra_state())
        return state


class WeightCheckAction(ActionBase):
    """协议无关的货物重量检测动作。

    业务脚本通过 ``protocol + scale_options`` 选择 Modbus RTU 或 CAN，也可注入已创建的
    ``scale`` 实例。动作按 tick 采样，达到 ``sample_count`` 后计算 kg 平均值；配置
    ``max_weight`` 时超重失败，未配置时只测量并把结果留在 ``weight_result``。
    """

    def __init__(
            self,
            protocol: str = "",
            scale_options: Optional[Dict] = None,
            max_weight: Optional[float] = None,
            sample_count: int = 3,
            sample_interval: float = 0.1,
            scale=None,
            close_scale: bool = True,
            action_name: str = "WeightCheck",
    ):
        super().__init__(action_name)
        _init_action_runtime(self)
        self.protocol = str(protocol or "")
        self.scale_options = dict(scale_options or {})
        self.max_weight = None if max_weight is None else float(max_weight)
        self.sample_count = max(1, int(sample_count))
        self.sample_interval = max(0.0, float(sample_interval))
        self.scale = scale
        self.close_scale = bool(close_scale)
        self.samples: List[float] = []
        self.weight_result: Optional[float] = None
        self.last_measurement: Dict = {}
        self.last_sample_time = 0.0
        self.started = False
        self.action_status = ActionStatus.INIT

    def _open_scale(self):
        if self.scale is None:
            if not self.protocol:
                raise ValueError("weight protocol is empty")
            from standard.weighing_scale import create_scale
            self.scale = create_scale(self.protocol, **self.scale_options)
        self.scale.open()

    def _close_scale(self):
        if self.scale is not None and self.close_scale:
            try:
                self.scale.close()
            except Exception:
                pass

    def _fail(self, error_code: str, message: str):
        self.error_code = error_code
        self.fail_reason = message
        Navigation.setTaskError(error_code, message)
        self._close_scale()
        self.action_status = ActionStatus.FAILED

    def _read_weight_kg(self) -> float:
        from standard.weighing_scale import weight_to_kg
        measurement = self.scale.read_weight()
        if not isinstance(measurement, dict):
            raise ValueError(f"invalid weight result: {measurement!r}")
        self.last_measurement = dict(measurement)
        return weight_to_kg(measurement.get("value"), measurement.get("unit"))

    def run(self, ctx=None):
        if self.action_status in (ActionStatus.FINISHED, ActionStatus.FAILED):
            return
        self.action_status = ActionStatus.RUNNING

        if not self.started:
            try:
                self._open_scale()
            except Exception as exc:
                self._fail("WeightDeviceOpenFailed", f"open weight device failed: {exc}")
                return
            self.started = True

        now = time.time()
        if self.samples and now - self.last_sample_time < self.sample_interval:
            return
        self.last_sample_time = now
        try:
            self.samples.append(self._read_weight_kg())
        except Exception as exc:
            self._fail("WeightReadFailed", f"read weight failed: {exc}")
            return

        if len(self.samples) < self.sample_count:
            return

        self.weight_result = sum(self.samples) / len(self.samples)
        if self.max_weight is not None and self.weight_result >= self.max_weight:
            self._fail(
                "GoodsOverweight",
                f"weight of goods is {self.weight_result:.3f} kg, not less than {self.max_weight:.3f} kg",
            )
            return

        _trace_log(
            f"weight check finished: average={self.weight_result:.3f}kg, "
            f"samples={self.samples}, max={self.max_weight}"
        )
        self._close_scale()
        self.action_status = ActionStatus.FINISHED

    def reset(self):
        self._close_scale()
        self.samples = []
        self.weight_result = None
        self.last_measurement = {}
        self.last_sample_time = 0.0
        self.started = False
        self.fail_reason = ""
        self.error_code = ""
        self.action_status = ActionStatus.RUNNING

    def cancel(self):
        self._close_scale()
        self.action_status = ActionStatus.FAILED
        if not self.fail_reason:
            self.fail_reason = "cancelled"

    def result_description(self) -> dict:
        if self.weight_result is None:
            return {}
        return {
            "weightKg": round(self.weight_result, 3),
            "sampleCount": len(self.samples),
            "maxWeightKg": self.max_weight,
        }

    def _trace_state(self) -> dict:
        return {
            "action_status": int(self.action_status),
            "sample_count": len(self.samples),
            "weight_result": self.weight_result,
            "max_weight": self.max_weight,
            "protocol": self.protocol,
        }


class LocDetectGoods(ActionBase):
    MAX_ATTEMPTS = 10

    def __init__(self, loc_name: str, expect_goods: bool, action_name = "LocDetectGoods"):
        super().__init__(action_name)
        _init_action_runtime(self)
        self.loc_name = loc_name
        self.expect_goods = bool(expect_goods)
        self.target = [0, 0, 0, -1]
        self.target_in_robot = [0, 0, 0]
        self.detect_result = None
        self.detected_goods = None
        self.attempts = 0
        self.rec_status = 0

    @staticmethod
    def _result_has_goods(result) -> bool:
        if isinstance(result, dict):
            if "valid" in result:
                return bool(result.get("valid"))
            reco_list = result.get("recoList")
            if isinstance(reco_list, list):
                return any(
                    bool(item.get("valid", True))
                    for item in reco_list
                    if isinstance(item, dict)
                )
            return False
        if isinstance(result, list):
            return any(
                bool(item.get("valid", True)) if isinstance(item, dict) else bool(item)
                for item in result
            )
        return bool(result)

    def _fail(self, error_code: str, message: str):
        self.error_code = error_code
        self.fail_reason = message
        Navigation.setTaskError(error_code, message)
        self.action_status = ActionStatus.FAILED

    def _finish_detection(self, has_goods: bool):
        self.detected_goods = has_goods
        if has_goods == self.expect_goods:
            self.action_status = ActionStatus.FINISHED
            return
        if has_goods:
            self._fail("TargetFilled", f"{self.loc_name} is filled")
        else:
            self._fail("TargetNotFilled", f"{self.loc_name} is not filled")

    def _start_detection(self):
        cfg = _config()
        if not cfg.locDetect3dDevice:
            self._fail("LocDetectDeviceMissing", "location detection device is empty")
            return
        Recognize.recTargetObs(
            cfg.locDetect3dDevice,
            self.target_in_robot[0],
            self.target_in_robot[1],
            self.target_in_robot[2],
            cfg.obsAreaMinHeight,
            cfg.obsAreaMaxHeight,
            cfg.obsAreaLength,
            cfg.obsAreaWidth,
        )

    def run(self, ctx=None):
        if self.action_status in (ActionStatus.FINISHED, ActionStatus.FAILED):
            return
        self.action_status = ActionStatus.RUNNING
        self.rec_status = Recognize.getRecStatus()
        if self.rec_status == 0:
            self._start_detection()
        elif self.rec_status == 2:
            self.detect_result = Recognize.getRecResults()
            self._finish_detection(self._result_has_goods(self.detect_result))
        elif self.rec_status in (-1, 3):
            self.attempts += 1
            if self.attempts >= self.MAX_ATTEMPTS:
                self._finish_detection(False)
            else:
                Recognize.resetRec()
        Trace.log("loc detect goods run")
        self.action_state.update({
            "locName": self.loc_name,
            "target": self.target,
            "targetInRobot": self.target_in_robot,
            "expectGoods": self.expect_goods,
            "detectedGoods": self.detected_goods,
            "detectResult": self.detect_result,
            "recStatus": self.rec_status,
            "recAttempts": self.attempts,
        })

    def reset(self):
        _init_action_runtime(self)
        self.target = Navigation.getLM(self.loc_name, True)
        if not has_valid_target_pos(self.target):
            self._fail("TargetPointNotFound", f"{self.loc_name} does not exist")
            return
        self.target_in_robot = pos2Base(self.target[:3], get_r_loc())
        self.detect_result = None
        self.detected_goods = None
        self.attempts = 0
        self.rec_status = 0
        Recognize.resetRec()
        self.action_status = ActionStatus.RUNNING

    def cancel(self):
        Recognize.resetRec()
        super().cancel()

    def result_description(self) -> dict:
        return {
            "locName": self.loc_name,
            "expectGoods": self.expect_goods,
            "detectedGoods": self.detected_goods,
            "attempts": self.attempts,
        }

    def _trace_state(self) -> dict:
        return {
            "action_status": int(self.action_status),
            "rec_status": self.rec_status,
            "attempts": self.attempts,
            "expect_goods": self.expect_goods,
            "detected_goods": self.detected_goods,
        }


class RunMotorByPosition(ActionBase):
    """模块电机位置控制公共骨架。"""

    position_tolerance = 0.01

    def __new__(cls, motor_name, position, max_speed=0.01, action_name="RunMotor", stop_di="", min_safe_height=0.0):
        if cls is not RunMotorByPosition:
            return super().__new__(cls)
        if motor_name == _config().fork_motor_name:
            action_cls = _resolve_fork_motor_action_class()
            instance = super().__new__(action_cls)
            action_cls.__init__(
                instance,
                motor_name,
                position,
                max_speed=max_speed,
                action_name=action_name,
                stop_di=stop_di,
                min_safe_height=min_safe_height,
            )
            return instance
        return super().__new__(cls)

    def __init__(self, motor_name, position, max_speed=0.01, action_name="RunMotor", stop_di="", min_safe_height=0.0):
        super().__init__(action_name)
        _init_action_runtime(self)
        if not motor_name:
            self.action_status = ActionStatus.FAILED
            Navigation.setTaskError("NoMotorInModel", "not motor find in Device.Model.moduleType.XXXMotor, script failed")
            return
        self.motor_name = motor_name
        self.position = position
        self.max_speed = abs(max_speed or 0.01)
        self.stop_di = stop_di
        self.min_safe_height = min_safe_height
        self.init = False
        self.is_reach = False
        self.positions = []
        self.motor_timestamps = []
        self.check_duration = 20
        self.last_sample_time = None
        self.start_time = time.time()
        self.action_status = ActionStatus.INIT
        self.cur_position = Motor.getMotorPos(self.motor_name)
        self.cur_position_at_init = self.cur_position
        self.delta = self.position - self.cur_position
        self._motor_reset_done = False

    def _reset_motor_once(self):
        if self.motor_name and not self._motor_reset_done:
            Motor.resetMotor(self.motor_name)
            self._motor_reset_done = True

    def _no_move_error(self):
        return (
            getattr(self, "_no_move_error_key", "ForkNoMove"),
            getattr(self, "_no_move_error_desc", "motor position not change"),
        )

    def _start_motion(self):
        min_length, max_length = _config()._get_motor_limits(self.motor_name)
        self.position = clamp(self.position, min_length, max_length)
        self.cur_position = Motor.getMotorPos(self.motor_name)
        delta = self.position - self.cur_position
        self.delta = delta
        if abs(delta) <= self.position_tolerance:
            self.action_status = ActionStatus.FINISHED
            Trace.log(
                f"module motor does not need move: motor={self.motor_name}, current={self.cur_position}, "
                f"target={self.position}, delta={delta}, tolerance={self.position_tolerance}",
                name="fork.task",
            )
            return
        if is_do_motor_key(self.motor_name):
            speed = self.max_speed if delta > 0 else -self.max_speed
            Motor.setMotorSpeed(self.motor_name, speed, self.stop_di)
        else:
            Motor.setMotorPosition(self.motor_name, self.position, self.max_speed, self.stop_di)
        self._motor_reset_done = False
        Trace.log(f"module motor:{self.motor_name}, position:{self.position}", name="fork.task")

    def _after_start_motion(self):
        hook = getattr(self, "_after_start_motion_hook", None)
        if callable(hook):
            hook(self)
        return

    def _before_reach_check(self):
        hook = getattr(self, "_before_reach_check_hook", None)
        if callable(hook):
            hook(self)
        return

    def _after_reached(self):
        hook = getattr(self, "_after_reached_hook", None)
        if callable(hook):
            hook(self)
        return

    def on_step_start(self, ctx=None):
        self._reset_motor_once()

    def on_step_end(self, ctx=None):
        self._reset_motor_once()
        hook = getattr(self, "_step_end_hook", None)
        if callable(hook):
            hook(self)

    def suspend(self):
        if self.action_status == ActionStatus.RUNNING:
            self._reset_motor_once()
            hook = getattr(self, "_suspend_hook", None)
            if callable(hook):
                hook(self)
        super().suspend()

    def resume(self):
        if self.action_status == ActionStatus.SUSPENDED:
            self.init = False
        super().resume()

    def run(self, ctx=None):
        self.cur_position = Motor.getMotorPos(self.motor_name)
        if self.action_status in [ActionStatus.FAILED, ActionStatus.FINISHED]:
            self._reset_motor_once()
            return

        if not self.init:
            self.action_status = ActionStatus.RUNNING
            self.last_sample_time = time.time()
            self.start_time = time.time()
            self.cur_position_at_init = self.cur_position
            self.init = True
            self._start_motion()
            self._after_start_motion()
            if self.action_status in [ActionStatus.FAILED, ActionStatus.FINISHED]:
                self._reset_motor_once()
                return

        self._before_reach_check()
        if is_do_motor_key(self.motor_name):
            # DO 电机（如开合电机）走 setMotorSpeed，未下发 setMotorPosition；
            # 调用 isMotorReached 会让电机报错，故跳过到位查询。到位由 stop_di 触发
            # （DI 到位即停）后判定完成。
            self.is_reach = False
            if self.stop_di and Di.getDi(self.stop_di):
                self._after_reached()
                self.action_status = ActionStatus.FINISHED
        else:
            self.is_reach = Motor.isMotorReached(self.motor_name)
            if self.is_reach:
                self._after_reached()
                self.action_status = ActionStatus.FINISHED

        now = time.time()
        if self.last_sample_time is not None and now - self.last_sample_time > 0.5:
            self.last_sample_time = now
            self.positions.append(self.cur_position)
            self.motor_timestamps.append(now)

            if self.motor_timestamps and now - self.motor_timestamps[0] >= self.check_duration:
                min_pos = min(self.positions)
                max_pos = max(self.positions)
                if abs(max_pos - min_pos) <= self.position_tolerance:
                    error_key, error_desc = self._no_move_error()
                    _trace_log(f"{error_desc} between:{min_pos}m-{max_pos}m in {self.check_duration}s")
                    self.action_status = ActionStatus.FINISHED

            while self.motor_timestamps and now - self.motor_timestamps[0] > self.check_duration:
                self.positions.pop(0)
                self.motor_timestamps.pop(0)

        if self.action_status in [ActionStatus.FAILED, ActionStatus.FINISHED]:
            self._reset_motor_once()

    def reset(self):
        self._reset_motor_once()
        self.action_status = ActionStatus.RUNNING
        self.motor_timestamps.clear()
        self.positions.clear()
        self.init = False
        self._motor_reset_done = False
        hook = getattr(self, "_reset_hook", None)
        if callable(hook):
            hook(self)

    def cancel(self):
        self._reset_motor_once()
        self.motor_timestamps.clear()
        self.positions.clear()
        self.init = False
        self.action_status = ActionStatus.FAILED
        hook = getattr(self, "_cancel_hook", None)
        if callable(hook):
            hook(self)

    def _trace_state(self) -> dict:
        builder = getattr(self, "_trace_state_builder", None)
        if callable(builder):
            return builder(self)
        return {
            "action_status": int(self.action_status),
            "is_reach": self.is_reach,
            "cur_position_at_init": self.cur_position_at_init or 0.0,
            "target_position": self.position,
        }


class RunReachMotorsByPosition(ActionBase):
    """同步控制一个或多个前移电机，并持续检查相对伸出量。

    target 可用 min/max、统一绝对位置或与电机数量一致的位置列表。位置型电机走
    setMotorPosition，DoMotor 走带方向的 setMotorSpeed；无论何种协议，结束、失败、
    reset 和 cancel 都通过 resetMotor 停止整组电机。
    """

    def __init__(
            self,
            motor_names,
            target="max",
            max_speed=0.1,
            sync_tolerance=0.02,
            contact_di=None,
            check_all_di=False,
            action_name="RunReachMotors",
    ):
        super().__init__(action_name)
        _init_action_runtime(self)
        self.motor_names = [str(name).strip() for name in list(motor_names or []) if str(name).strip()]
        self.position_motor_names = []
        self.position_targets_reached = False
        self.target = target
        self.max_speed = abs(float(max_speed or 0.1))
        self.sync_tolerance = max(0.0, float(sync_tolerance or 0.0))
        self.contact_di = list(contact_di or [])
        self.check_all_di = bool(check_all_di)
        self.limits = [_config()._get_motor_limits(name) for name in self.motor_names]
        self.target_positions = self._resolve_targets(target)
        self.positions = []
        self.relative_positions = []
        self.max_relative_diff = 0.0
        self.init = False
        self.action_status = ActionStatus.INIT

    def _resolve_targets(self, target):
        # 每个目标都按各自电机行程限幅，避免双电机行程不一致时使用同一裸目标越界。
        if isinstance(target, (list, tuple)):
            values = list(target)
            if len(values) != len(self.motor_names):
                raise ValueError("reach motor target count does not match motor count")
            return [clamp(float(value), limits[0], limits[1]) for value, limits in zip(values, self.limits)]
        if target == "min":
            return [limits[0] for limits in self.limits]
        if target == "max":
            return [limits[1] for limits in self.limits]
        return [clamp(float(target), limits[0], limits[1]) for limits in self.limits]

    def _stop_all(self):
        # 任一结束条件都停止整组电机，不能只停已到位或已触发 DI 的单侧。
        for motor_name in self.motor_names:
            Motor.resetMotor(motor_name)

    def suspend(self):
        if self.action_status == ActionStatus.RUNNING:
            self._stop_all()
        super().suspend()

    def resume(self):
        if self.action_status == ActionStatus.SUSPENDED:
            self.init = False
        super().resume()

    def _contact_di_triggered(self):
        if not self.contact_di:
            return False
        # check_all_di 对应现场“全部叉尖到位”模式；关闭时任一到位即可结束伸出。
        statuses = [bool(Di.getDi(di_id)) for di_id in self.contact_di]
        return all(statuses) if self.check_all_di else any(statuses)

    def _start_all(self):
        # 每个新的位置命令先清除上一轮到位状态；只有本轮成功下发过的
        # 位置电机才允许查询 isMotorReached。
        self.position_motor_names = []
        self.position_targets_reached = True
        for motor_name, target in zip(self.motor_names, self.target_positions):
            current = Motor.getMotorPos(motor_name)
            if abs(target - current) <= 0.005:
                continue
            self.position_targets_reached = False
            Motor.resetMotor(motor_name)
            if is_do_motor_key(motor_name):
                speed = self.max_speed if target > current else -self.max_speed
                Motor.setMotorSpeed(motor_name, speed, "")
            else:
                if not Motor.setMotorPosition(motor_name, target, self.max_speed, ""):
                    self._stop_all()
                    Navigation.setTaskError(
                        "ReachMotorCommandRejected",
                        f"reach motor command rejected: motor:{motor_name}, target:{target}",
                    )
                    self.action_status = ActionStatus.FAILED
                    return False
                self.position_motor_names.append(motor_name)
        Trace.log(
            f"reach motors:{self.motor_names}, targets:{self.target_positions}, speed:{self.max_speed}",
            name="fork.task",
        )
        return True

    def _update_sync_state(self):
        self.positions = [float(Motor.getMotorPos(name)) for name in self.motor_names]
        # 同步比较采用“当前位置 - 各自最小位”的相对伸出量，不能直接比较绝对编码器值。
        self.relative_positions = [
            position - limits[0]
            for position, limits in zip(self.positions, self.limits)
        ]
        if len(self.relative_positions) <= 1:
            self.max_relative_diff = 0.0
        else:
            self.max_relative_diff = max(self.relative_positions) - min(self.relative_positions)

    def run(self, ctx=None):
        if self.action_status in (ActionStatus.FINISHED, ActionStatus.FAILED):
            return
        if not self.motor_names:
            Navigation.setTaskError("ReachMotorMissing", "reach motor is not configured")
            self.action_status = ActionStatus.FAILED
            return
        if not self.init:
            self.init = True
            self.action_status = ActionStatus.RUNNING
            if not self._start_all():
                return

        self._update_sync_state()
        # 多电机不同步优先级高于 DI/到位完成；超差时立即停整组并保留各电机位置到错误信息。
        if len(self.motor_names) > 1 and self.max_relative_diff > self.sync_tolerance:
            self._stop_all()
            Navigation.setTaskError(
                "ReachMotorOutOfSync",
                f"reach motor relative difference {self.max_relative_diff:.4f}m exceeds "
                f"{self.sync_tolerance:.4f}m, positions:{self.positions}",
            )
            self.action_status = ActionStatus.FAILED
            return
        if self._contact_di_triggered():
            # 接触 DI 是允许的提前完成条件，触发后必须先停电机再把 action 标为完成。
            self._stop_all()
            self.action_status = ActionStatus.FINISHED
            return
        if self.position_motor_names and all(
            Motor.isMotorReached(name) for name in self.position_motor_names
        ):
            self._stop_all()
            self.action_status = ActionStatus.FINISHED
        elif self.position_targets_reached:
            self._stop_all()
            self.action_status = ActionStatus.FINISHED

    def reset(self):
        # reset 既负责清除上次下发，也允许同一个 action 在队列重新驱动时再次启动。
        self._stop_all()
        self.action_status = ActionStatus.RUNNING
        self.init = False

    def cancel(self):
        # 取消不等待位置到达，立即停止整组并让上层按失败路径收尾。
        self._stop_all()
        self.action_status = ActionStatus.FAILED

    def _trace_state(self):
        return {
            "action_status": int(self.action_status),
            "motor_names": self.motor_names,
            "positions": self.positions,
            "targets": self.target_positions,
            "max_relative_diff": self.max_relative_diff,
            "sync_tolerance": self.sync_tolerance,
        }


def _init_fork_motor_action(action, min_safe_height=0.0):
    action.min_safe_height = min_safe_height
    action.timeout = None
    action.delta = action.position - action.cur_position
    action.cur_fork_height = 0.0
    action.cur_fork_height_at_init = 0.0
    action._count_recorded = False
    action._no_move_error_key = "ForkNoMove"
    action._no_move_error_desc = "fork height not change"
    action._before_reach_check_hook = _fork_before_reach_check
    action._after_reached_hook = _fork_after_reached
    action._cancel_hook = _fork_close_dos
    action._suspend_hook = _fork_close_dos
    action._step_end_hook = _fork_close_dos
    action._reset_hook = _fork_reset_runtime
    action._trace_state_builder = _fork_trace_state
    action._collision_device = []
    action._collision_x = []
    action._collision_y = []
    if _config().fork_root_2D_lasers:
        action._collision_x = [p["x"] for p in _config().fork_area]
        action._collision_y = [p["y"] for p in _config().fork_area]
        action._collision_device = [_config().fork_root_2D_lasers]
        Trace.log(
            f"x_list:{action._collision_x},y_list:{action._collision_y},collision device:{action._collision_device}",
            name="fork.task",
        )


def _fork_current_position(action):
    action.cur_fork_height = Motor.getMotorPos(action.motor_name)
    return action.cur_fork_height


def _fork_close_dos(action):
    if action.motor_name == _config().fork_motor_name:
        if _config().upDo:
            Do.setDo(_config().upDo, not _config().upDoStatus)
        if _config().downDo:
            Do.setDo(_config().downDo, not _config().downDoStatus)


def _fork_check_back_laser_collision(action):
    if not (_config().fork_root_2D_lasers and action.delta < -EPS):
        return
    if 0 < action.min_safe_height <= action.cur_fork_height:
        Trace.log(
            f"fork moving, height:{action.cur_fork_height} >= min_safe_height:{action.min_safe_height}, skip back laser collision detection",
            name="fork.task",
        )
        return
    Navigation.collisionDetection(action._collision_device, action._collision_x, action._collision_y)


def _fork_apply_loaded_speed_limit(action):
    max_speed = min(_config().fork_max_speed, action.max_speed)
    if Container.hasGoods("0"):
        loaded_speed_limit = (
            _config().upMaxSpeedWithGoods
            if action.delta > 0
            else _config().downMaxSpeedWithGoods
        )
        if loaded_speed_limit is not None and loaded_speed_limit >= 0:
            max_speed = min(max_speed, loaded_speed_limit)
    action.max_speed = max_speed


def _fork_prepare_target_position(action):
    min_h, max_h = _config().min_height, _config().max_height
    action.position = clamp(action.position, min_h, max_h)
    action.delta = action.position - action.cur_fork_height
    action.cur_fork_height_at_init = action.cur_fork_height
    if not action.stop_di:
        if action.delta > EPS:
            action.stop_di = _config().up_di or ""
        elif action.delta < -EPS:
            action.stop_di = _config().down_di or ""


def _fork_configure_motion(action):
    if action.motor_name != _config().fork_motor_name:
        return
    if action.delta > EPS:
        action.timeout = _config().loadTime
    elif action.delta < -EPS:
        action.timeout = _config().unloadTime
    else:
        action.timeout = None

    if action.delta > EPS and _config().upDo:
        Do.setDo(_config().upDo, _config().upDoStatus)
        Trace.log(f"fork moving up, set upDo:{_config().upDo} to {_config().upDoStatus}", name="fork.task")
    elif action.delta < -EPS and _config().downDo:
        Do.setDo(_config().downDo, _config().downDoStatus)
        Trace.log(f"fork moving down, set downDo:{_config().downDo} to {_config().downDoStatus}", name="fork.task")


def _fork_before_reach_check(action):
    if action.motor_name == _config().fork_motor_name and action.timeout is not None and action.timeout >= 0:
        if (time.time() - action.start_time) > action.timeout:
            error_desc = f"Fork motor timeout: {action.motor_name} exceeded {action.timeout}s"
            Navigation.setTaskError("ForkMoveTimeout", error_desc)
            RobotError.setSystemError("ForkMoveTimeout", error_desc, True)
            action.action_status = ActionStatus.FAILED
            return
    _fork_check_back_laser_collision(action)


def _fork_after_reached(action):
    _fork_close_dos(action)
    increment_fork_count = getattr(_config(), "increment_fork_count", None)
    if action.delta > EPS and not action._count_recorded and callable(increment_fork_count):
        action._count_recorded = True
        increment_fork_count()
    Trace.log(f"agv base shift config:{_config().base_shift}", name="fork.task")
    if _config().base_shift and abs(action.position - _config().max_height) < EPS:
        Navigation.wheelBaseShift(True)
        Trace.log("base shift true", name="fork.task")
    elif _config().base_shift and abs(action.position - _config().min_height) < EPS:
        Navigation.wheelBaseShift(False)
        Trace.log("base shift false", name="fork.task")


def _fork_reset_runtime(action):
    action.timeout = None
    action.cur_fork_height = Motor.getMotorPos(action.motor_name)
    action.delta = action.position - action.cur_fork_height


def _fork_trace_state(action) -> dict:
    return {
        "action_status": int(action.action_status),
        "is_reach": action.is_reach,
        "cur_fork_height_at_init": action.cur_fork_height_at_init or 0.0,
        "timeout": action.timeout or 0,
    }


class LiftForkMotorByPosition(RunMotorByPosition):
    def __init__(self, motor_name, position, max_speed=None, action_name="RunMotor", stop_di="", min_safe_height=0.0):
        super().__init__(
            motor_name,
            position,
            _config().fork_max_speed if max_speed is None else max_speed,
            action_name=action_name,
            stop_di=stop_di,
        )
        _init_fork_motor_action(self, min_safe_height=min_safe_height)

    def _start_motion(self):
        self.cur_fork_height = _fork_current_position(self)
        _fork_prepare_target_position(self)
        mid_height = (_config().max_height + _config().min_height) / 2
        if _config().DOMotor:
            if self.position < mid_height:
                vel = -0.01
                self.position = _config().min_height
            elif self.position > mid_height:
                vel = 0.01
                self.position = _config().max_height
            else:
                self.action_status = ActionStatus.FINISHED
                return
            self.delta = self.position - self.cur_fork_height
            if abs(self.delta) <= self.position_tolerance:
                self.action_status = ActionStatus.FINISHED
                return
            _fork_configure_motion(self)
            Motor.setMotorSpeed(self.motor_name, vel, self.stop_di)
        else:
            if self.position < mid_height:
                self.position = _config().min_height
            elif self.position > mid_height:
                self.position = _config().max_height
            self.delta = self.position - self.cur_fork_height
            if abs(self.delta) <= self.position_tolerance:
                self.action_status = ActionStatus.FINISHED
                return
            _fork_configure_motion(self)
            Motor.setMotorPosition(self.motor_name, self.position, self.max_speed, self.stop_di)
        self._motor_reset_done = False
        Trace.log(f"position:{self.position}", name="fork.task")


class GoodsAwareForkMotorByPosition(RunMotorByPosition):
    def __init__(self, motor_name, position, max_speed=None, action_name="RunMotor", stop_di="", min_safe_height=0.0):
        super().__init__(
            motor_name,
            position,
            _config().fork_max_speed if max_speed is None else max_speed,
            action_name=action_name,
            stop_di=stop_di,
        )
        _init_fork_motor_action(self, min_safe_height=min_safe_height)

    def _start_motion(self):
        self.cur_fork_height = _fork_current_position(self)
        _fork_prepare_target_position(self)
        _fork_apply_loaded_speed_limit(self)
        _fork_configure_motion(self)
        Motor.setMotorPosition(self.motor_name, self.position, self.max_speed, self.stop_di)
        self._motor_reset_done = False
        Trace.log(f"position:{self.position}", name="fork.task")


class ReachAwareForkMotorByPosition(RunMotorByPosition):
    def __init__(self, motor_name, position, max_speed=None, action_name="RunMotor", stop_di="", min_safe_height=0.0):
        super().__init__(
            motor_name,
            position,
            _config().fork_max_speed if max_speed is None else max_speed,
            action_name=action_name,
            stop_di=stop_di,
        )
        _init_fork_motor_action(self, min_safe_height=min_safe_height)

    def _start_motion(self):
        self.cur_fork_height = _fork_current_position(self)
        _fork_prepare_target_position(self)
        tolerance = max(_config().reach_up_dist, _config().reach_down_dist, self.position_tolerance)
        if abs(self.delta) <= tolerance:
            self.action_status = ActionStatus.FINISHED
            Trace.log(
                f"fork motor does not need move: current={self.cur_fork_height}, target={self.position}, "
                f"delta={self.delta}, tolerance={tolerance}",
                name="fork.task",
            )
            return
        _fork_check_back_laser_collision(self)
        _fork_apply_loaded_speed_limit(self)
        _fork_configure_motion(self)
        Motor.setMotorPosition(self.motor_name, self.position, self.max_speed, self.stop_di)
        self._motor_reset_done = False
        Trace.log(f"position:{self.position}", name="fork.task")


def _resolve_fork_motor_action_class():
    # 车型脚本通过 Fork.fork_motor_action_class 注册专属实现（推入 ConfigParams）；
    # 未注册的车型使用基类通用实现（行程感知）。此处不再按 module_type 硬编码分支。
    return _config().fork_motor_action_class or ReachAwareForkMotorByPosition


class RunMotorBySpeed(ActionBase):
    def __init__(self, motor_name, max_speed, stop_di=""):
        super().__init__()
        _init_action_runtime(self)
        self.motor_name = motor_name
        self.max_speed = max_speed
        self.stop_di = stop_di
        self.init = False
        Motor.resetMotor(self.motor_name)

    def run(self, ctx=None):
        if not self.init:
            self.action_status = ActionStatus.RUNNING
            self.init = True
            Motor.setMotorSpeed(self.motor_name, self.max_speed, self.stop_di)
        if Motor.isMotorReached(self.motor_name):
            self.action_status = ActionStatus.FINISHED

    def reset(self):
        self.action_status = ActionStatus.INIT
        Motor.resetMotor(self.motor_name)

    def _trace_state(self) -> dict:
        return {
            "action_status": int(self.action_status),
            "max_speed": self.max_speed,
        }



class MoveChassisByY(ActionBase):
    def __init__(self, robot2pos):
        super().__init__("MoveChassisByY")
        _init_action_runtime(self)
        self.x = -robot2pos[0]
        self.y = -robot2pos[1]
        self.yaw = -robot2pos[2]
        self.shiftMotor = _config().shiftMotor
        self.action_status = ActionStatus.INIT

        pos2robot = pos2Base([0, 0, 0], robot2pos)
        target_world = pos2World(pos2robot, get_r_loc())
        self.chassis_move = None
        self.step = [False] * 3

        if self.shiftMotor != "":
            chassis_yaw_args = {
                "x": 0,
                "y": 0,
                "theta": self.yaw,
                "backMode": 0,
                "maxSpeed": 0.1,
                "maxRot": math.radians(2),
                "coordinate": Coordinate.ROBOT.value,
                "reachAngle": math.radians(0.5),
                "reachDist": 0.005,
            }
            self.yaw_move = GoPath(chassis_yaw_args)
            cur_position = Motor.getMotorPos(self.shiftMotor)
            self.shift = RunMotorByPosition(self.shiftMotor, (cur_position + self.y), 0.1)
            Trace.log(
                f"cur pos shift:{cur_position},target:{cur_position + self.y}",
                output_console=True,
                output_time=True,
                name="fork.task",
                debug=True,
            )
            chassis_x_args = {
                "x": self.x,
                "y": 0,
                "theta": 0,
                "backMode": 0,
                "maxSpeed": 0.03,
                "maxRot": math.radians(2),
                "coordinate": Coordinate.ROBOT.value,
                "reachAngle": math.radians(0.5),
                "reachDist": 0.005,
            }
            if self.x < 0:
                chassis_x_args["backMode"] = 1
            self.x_move = GoPath(chassis_x_args)
        else:
            chassis_args = {
                "x": self.x,
                "y": self.y,
                "theta": self.yaw,
                "holdDir": math.degrees(target_world[2]),
                "backMode": 0,
                "maxSpeed": 0.05,
                "maxRot": math.radians(3),
                "coordinate": Coordinate.ROBOT.value,
                "reachAngle": math.radians(0.5),
                "reachDist": 0.005,
            }
            Trace.log(f"chassis args:{chassis_args}", name="fork.task")
            if self.x < 0:
                chassis_args["backMode"] = 1
            self.chassis_move = GoPath(chassis_args)

    def run(self, ctx=None):
        if not self.init:
            self.init = True
        if self.shiftMotor == "":
            if self.chassis_move.action_status not in [ActionStatus.FINISHED, ActionStatus.FAILED]:
                self.chassis_move.run()
            elif self.chassis_move.action_status == ActionStatus.FINISHED:
                self.action_status = ActionStatus.FINISHED
        else:
            if not self.step[0]:
                if self.yaw_move.action_status not in [ActionStatus.FINISHED, ActionStatus.FAILED]:
                    self.yaw_move.run()
                if self.yaw_move.action_status == ActionStatus.FINISHED:
                    self.step[0] = True
            elif self.step[0] and not self.step[1]:
                if self.shift.action_status not in [ActionStatus.FINISHED, ActionStatus.FAILED]:
                    self.shift.run()
                if self.shift.action_status == ActionStatus.FINISHED:
                    self.step[1] = True
            elif self.step[1] and not self.step[2]:
                if self.x_move.action_status not in [ActionStatus.FINISHED, ActionStatus.FAILED]:
                    self.x_move.run()
                if self.x_move.action_status == ActionStatus.FINISHED:
                    self.step[2] = True
            if all(self.step):
                self.action_status = ActionStatus.FINISHED

    def reset(self):
        self.action_status = ActionStatus.RUNNING
        self.init = False

    def cancel(self):
        self.init = False
        self.action_status = ActionStatus.FAILED
        Navigation.resetPath()
        if self.shiftMotor:
            Motor.resetMotor(_config().shiftMotor)

    def _current_action(self):
        if self.shiftMotor == "":
            return self.chassis_move
        if not self.step[0]:
            return self.yaw_move
        if not self.step[1]:
            return self.shift
        if not self.step[2]:
            return self.x_move
        return None

    def suspend(self):
        if self.action_status == ActionStatus.RUNNING:
            current_action = self._current_action()
            if current_action is not None:
                current_action.suspend()
            super().suspend()

    def resume(self):
        if self.action_status == ActionStatus.SUSPENDED:
            current_action = self._current_action()
            if current_action is not None:
                current_action.resume()
            super().resume()

    def _trace_state(self) -> dict:
        return {
            "action_status": int(self.action_status),
        }
