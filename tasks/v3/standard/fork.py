# -*- coding: utf-8 -*-
# Author: mazj
# Time: 2026/06/26

import json
import math
import time
import inspect
from datetime import datetime
from typing import Optional, List, Dict, Any
from syspy import (Module, Di, Motor, Navigation, ScriptStatus, NetProtocol,
                   Trace, Controller, NavStatus, Container, _TR,
                   AutoPreSequenceAction)
from syspy.utils import Coordinate, SCRIPTS_DIR, TaskStage, DEFAULT_TASK_STAGE
from syspy.utils.time import Timer
from syspy.utils.param_server import BindItem, ParamBuilder, ParamType, ParamValidator, BindType, ScriptParam
from syspy.lib.module import pos2Base, pos2World, ModuleBase, SafeMoveStatus
from syspy.lib.net_protocol import parseModbus
from syspy.lib.robot import RobotParam
import standard.goBezier as GoBezier
from syspy import LevelDB


db = None
FORK_TOTAL_COUNT_KEY = "forkTotalCount"
FORK_TODAY_COUNT_KEY = "forkTodayCount"
FORK_LAST_DATE_KEY = "forkLastDate"


def _get_run_db():
    global db
    if db is None:
        db = LevelDB("run")
    return db


def _init_fork_count():
    run_db = _get_run_db()
    defaults = {
        FORK_TOTAL_COUNT_KEY: 0,
        FORK_TODAY_COUNT_KEY: 0,
        FORK_LAST_DATE_KEY: "",
    }
    for key, default in defaults.items():
        value_type = "str" if isinstance(default, str) else "int"
        if run_db.get(key, value_type) is None:
            run_db.add(key, default, False)


def increment_fork_count():
    run_db = _get_run_db()
    today = datetime.now().strftime("%Y-%m-%d")
    last_date = run_db.get(FORK_LAST_DATE_KEY, "str") or ""
    today_count = run_db.get(FORK_TODAY_COUNT_KEY, "int") or 0
    if last_date != today:
        today_count = 0

    total_count = run_db.get(FORK_TOTAL_COUNT_KEY, "int") or 0
    run_db.put(FORK_TOTAL_COUNT_KEY, total_count + 1)
    run_db.put(FORK_TODAY_COUNT_KEY, today_count + 1)
    run_db.put(FORK_LAST_DATE_KEY, today)
    Trace.log(
        f"fork count total={total_count + 1} today={today_count + 1}",
        name=f"{MOD}.motor",
    )

param_loader: Optional[ScriptParam] = None
ACTIVE_SCRIPT_FILE = ""
SCRIPT_OPTIONS = {
    "config_builder_hook": None,
    "config_reload_hook": None,
    "rec_input_params_hook": None,
    "operation_input_hook": None,
    "root_input_hook": None,
    "custom_operation_inputs_hook": None,
    "custom_action_templates_hook": None,
    "period_run_hook": None,
}
MOD = "fork"


def _require_param_loader() -> ScriptParam:
    if param_loader is None:
        raise RuntimeError("Fork script runtime is not initialized")
    return param_loader


def _run_script_hook(name, *args):
    hook = SCRIPT_OPTIONS.get(name)
    if callable(hook):
        return hook(*args)
    return None


def _call_fork_class_hook(name, *args):
    """调用当前车型子类（ConfigParams.active_fork_class）上注册的钩子，未注册则安全跳过。"""
    fork_cls = ConfigParams.active_fork_class
    if fork_cls is None:
        return None
    hook = getattr(fork_cls, name, None)
    if callable(hook):
        return hook(*args)
    return None


EPS = 1e-6  # 浮点比较公差
_CONFIG_ROOT = object()


SELF_POSITION_MARKER = "SELF_POSITION"


from standard.fork_utils import (
    ActionStatus,
    ForkActionQueue,
    GoLiveRec,
    GoPathWithContactDi,
    LocDetectGoods,
    Rec,
    RunReachMotorsByPosition,
    RunMotorByPosition,
    WeightCheckAction,
    _action_chart_dict,
    bind_runtime as bind_fork_utils_runtime,
    build_recognition_readjust_target,
    build_path_adjust_plan,
    build_return_path_action,
    apply_tcp_target,
    clamp,
    create_end_height_param,
    create_fork_height_param,
    create_loc_detect_height_param,
    create_loc_detect_layer_param,
    create_rec_param,
    create_start_height_param,
    delete_deduct_area,
    disable_falling_down_detect,
    enable_falling_down_detect,
    float_to_modbus_poll_regs,
    format_action,
    get_r_loc,
    has_valid_target_pos,
    is_do_motor_key,
    is_enabled,
    load_goods_shape,
    load_recognition_assets,
    MoveChassisByY,
    normalize_motor_operation,
    OperationFlow,
    resolve_load_recognition_pose,
    resolve_back_dist,
    resolve_rec_center_to_robot,
    apply_default_navigation_policy,
    ensure_recfile,
    evaluate_recognition_readjust,
    extract_recognition_height_z,
    calculate_recognition_pick_height,
    check_motor_action_error,
    add_weight_config,
    add_weight_input,
    build_weight_action,
    load_pallet_z_offset,
    update_back_laser_clear_region_by_height,
    validate_goods_state_for_operation,
    validate_recognition_tilt,
    validate_recognition_result_against_target,
)


def _robot_device_change_callback(device_change_set: List[str]):
    """机器人设备参数改变回调"""
    """设备参数变化回调"""
    if "Model" in device_change_set:
        ConfigParams.get_device_model_param()
        ConfigParams._build_fork_area()
        ConfigParams._build_module_motor()
    if "Motor" in device_change_set or "DOMotor" in device_change_set:
        ConfigParams.get_device_motor_param()
        ConfigParams._build_module_motor()
    # InputParams.init()


def _robot_config_change_callback(diff_map: Dict[str, Any]):
    """机器人配置参数变化回调"""
    pass


def _script_config_callback():
    if param_loader is not None:
        ConfigParams.reload_config()


class ConfigParams:
    """生成和定义配置参数的示例"""
    # 这里只保留脚本启动前必须存在的字段；业务配置默认值统一由 _build_and_load_config/reload_config 管理。

    # --- 设备模型参数
    chassis_type: str = ""
    module_type: str = ""
    scriptName: str = ""

    shape: str = ""
    head: float = 0.0
    tail: float = 0.0
    width: float = 0.0
    module_x: float = 0.0
    base_shift: bool = False
    base_shift_length: float = 0.0

    # 叉车电机动作类：默认 None（基类通用行程感知实现）；车型脚本可在子类上重写 Fork.fork_motor_action_class 注册专属实现
    fork_motor_action_class = None
    # 当前车型子类（Fork.__init__ 在配置加载前注入）；供 get_device_model_param / _build_module_motor
    # 等配置阶段钩子读取，避免按 module_type 硬编码分支。未初始化时为 None。
    active_fork_class = None

    # --- 机构与电机参数
    fork_motor_name: str = ""
    shiftMotor: str = ""  # legacy key，保持与任务参数兼容
    pitch_motor_name: str = ""
    reach_motor_name: str = ""
    expand_motor_name: str = ""
    expand_motor_left: str = ""
    expand_motor_right: str = ""
    pitch_motor_names: List[str] = []
    reach_motor_names: List[str] = []
    expand_motor_names: List[str] = []
    expand_motor_items: List[Dict[str, Any]] = []

    # --- 识别微调（reload_config 会用脚本配置覆盖）
    readjust: bool = False
    readjustMaxTimes: int = 3
    readjustDistPrecision: float = 0.02
    readjustAnglePrecision: float = 0.5
    adjustHeight: bool = False
    camLiftWithFork: bool = False
    camCalibMotorHeight: float = 0.0
    adaptivePalletStackUnstack: bool = False
    loadPalletLayer: int = 1
    cageRecfileDefault: str = "cage.srec"
    cageRecfile: str = cageRecfileDefault
    adjustMethod: str = "pathFirst"
    autoPreAdvanceTime: float = 1.0
    enableNavForkHeight: bool = False
    navForkHeight: float = 0.3
    allowForkMoveWhileNav: bool = False
    enableLoadNavForkHeight: bool = False
    loadNavForkHeight: float = 0.3
    allowLoadForkMoveWhileNav: bool = False
    forkLeaveSafeHeight: float = 0.3
    reachMotorSyncTolerance: float = 0.02
    reachMotorMaxSpeed: float = 0.1
    useForPalletFallProtection: bool = False
    enableFallingDownDetect: bool = False

    motor_func: str = ""
    min_height: float = 0.0
    max_height: float = 0.0
    pitch_motor_min: float = 0.0
    pitch_motor_max: float = 0.0
    expand_motor_left_min: float = 0.0
    expand_motor_left_max: float = 0.0
    expand_motor_right_min: float = 0.0
    expand_motor_right_max: float = 0.0
    up_di: str = ""
    down_di: str = ""
    fork_max_speed: float = 0.0
    reach_up_dist: float = 0.001
    reach_down_dist: float = 0.001
    DOMotor: bool = False
    weightCan: str = ""
    weightNodeId: int = 0x0A
    weightSampleCount: int = 3
    weightSampleInterval: float = 0.1
    maxWeight: float = 1000.0

    # --- 车体几何与传感器
    fork_tip_width: float = 0.0
    center_distance_between_forks: float = 0.0
    fork_root_3D_camera: str = ""
    fork_root_2D_lasers: str = ""
    fork_tip_3D_cameras: List[str] = []
    fork_tip_2D_lasers: List[str] = []
    fork_tip_di_sensors: List[str] = []
    fork_tip_distance_sensors: List[str] = []
    contact_ids: List[str] = []

    # --- 库位 3D 检测
    locDetect3d: bool = False
    locDetect3dDevice: str = ""
    obsAreaMinHeight: float = 0.05
    obsAreaMaxHeight: float = 0.7
    obsAreaLength: float = 1.5
    obsAreaWidth: float = 1.0

    # --- 运行期缓存
    config: Dict[str, Any] = {}
    moduleMotor: List[Dict[str, Any]] = []

    # --- 叉车车头后面那块区域
    fork_area: List[Dict[str, float]] = []
    chassis_area: List[Dict[str, float]] = []

    @staticmethod
    def increment_fork_count():
        active_fork_class = ConfigParams.active_fork_class
        if active_fork_class and active_fork_class.fork_count_enabled:
            increment_fork_count()

    @classmethod
    def init(cls):
        """初始化所有设备参数"""
        cls.get_device_model_param()
        cls.get_device_motor_param()
        cls._build_fork_area()
        cls._build_and_load_config()
        cls._build_module_motor()

    @classmethod
    def reload_config(cls):
        """重新加载配置参数"""
        Trace.log("Reloading config parameters", name="fork.cfg")
        cfg = _require_param_loader().loadConfig()
        cls.config = cfg

        # --- script
        cls.timeout = cfg.get("timeout", 120.0)
        cls.scriptDebug = cls._safe_bool(cfg.get("scriptDebug"), False)
        cls.autoPreAdvanceTime = max(0.0, cls._safe_float(cfg.get("autoPreAdvanceTime"), 1.0))
        if cls.scriptDebug:
            Trace.log(f"Loaded config: {cls.config}", name="fork.cfg")

        # --- fork
        cls.upMaxSpeedWithGoods = cfg.get("upMaxSpeedWithGoods")
        cls.downMaxSpeedWithGoods = cfg.get("downMaxSpeedWithGoods")
        cls.backLaserEnableHeight = cfg.get("backLaserEnableHeight")
        cls.checkGoodsWhileLoad = cls._safe_bool(cfg.get("checkGoodsWhileLoad"), False)
        cls.checkAllContactDis = cls._safe_bool(cfg.get("checkAllContactDi"), False)
        cls.upDo = cfg.get("upDo", "")
        cls.upDoStatus = cls._safe_bool(cfg.get("upDoStatus"), False)
        cls.downDo = cfg.get("downDo", "")
        cls.downDoStatus = cls._safe_bool(cfg.get("downDoStatus"), False)
        cls.enableNavForkHeight = cls._safe_bool(cfg.get("enableNavForkHeight"), False)
        cls.navForkHeight = cls._safe_float(cfg.get("navForkHeight"), 0.3)
        cls.allowForkMoveWhileNav = cls._safe_bool(cfg.get("allowForkMoveWhileNav"), False)
        cls.enableLoadNavForkHeight = cls._safe_bool(cfg.get("enableLoadNavForkHeight"), False)
        cls.loadNavForkHeight = cls._safe_float(cfg.get("loadNavForkHeight"), 0.3)
        cls.allowLoadForkMoveWhileNav = cls._safe_bool(cfg.get("allowLoadForkMoveWhileNav"), False)
        load_time = cls._safe_float(cfg.get("loadTime", 30.0), 30.0)
        unload_time = cls._safe_float(cfg.get("UnloadTime", cfg.get("unloadTime", 30.0)), 30.0)
        cls.loadTime = load_time if cls._safe_bool(cfg.get("enableLoadTime"), True) else -1.0
        cls.unloadTime = unload_time if cls._safe_bool(cfg.get("enableUnLoadTime"), True) else -1.0

        # --- forkByDO
        cls.downDelayTime = cfg.get("downDelayTime")
        cls.upDelayTime = cfg.get("upDelayTime")
        cls.downDiDoFork = cfg.get("downDiDoFork")
        cls.upDiDoFork = cfg.get("upDiDoFork")
        cls.leakDo = cfg.get("leakDo")
        cls.pumpDo = cfg.get("pumpDo")

        # --- loadUnload
        cls.laserDetectionWidth = cfg.get("laserDetectionWidth")
        cls.aheadDist = cfg.get("aheadDist")
        cls.minAheadDist = cfg.get("minAheadDist")
        cls.loadAdjustMaxSpeed = cfg.get("loadAdjustMaxSpeed")
        cls.returnOnSamePath = cls._safe_bool(cfg.get("returnOnSamePath"), True)
        cls.forkDiDist = cfg.get("forkDiDist")
        cls.forkDiEnableAtLoad = cls._safe_bool(cfg.get("forkDiEnableAtLoad"), False)
        cls.forkDiEnableAtUnload = cls._safe_bool(cfg.get("forkDiEnableAtUnload"), True)
        cls.diTriggerMeasureUnload = cfg.get("diTriggerMeasureUnload", "collision")
        cls.enableContactDiNoRec = cls._safe_bool(cfg.get("enableContactDiNoRec"), True)
        cls.enableTcp = cls._safe_bool(cfg.get("enableTcp"), False)
        cls.loadObsStopDist = cfg.get("loadObsStopDist")
        cls.weightCan = cfg.get("weightCan", "")
        cls.weightNodeId = cfg.get("weightNodeId", 0x0A)
        cls.weightSampleCount = cfg.get("weightSampleCount", 3)
        cls.weightSampleInterval = cfg.get("weightSampleInterval", 0.1)
        cls.maxWeight = cfg.get("maxWeight", 1000.0)
        cls.useForPalletFallProtection = cls._safe_bool(cfg.get("useForPalletFallProtection"), False)
        cls.enableFallingDownDetect = cls._safe_bool(
            cfg.get("enableFallingDownDetect"),
            bool(getattr(cls.active_fork_class, "falling_down_detect_default", False)),
        )
        cls.setRoiX = cfg.get("setRoiX", 2.0)
        cls.setRoiMaxY = cfg.get("setRoiMaxY", 2.0)
        cls.setRoiMinY = cfg.get("setRoiMinY", 2.0)
        cls.setRoiZ = cfg.get("setRoiZ", 2.0)
        cls.errorRecY = cfg.get("errorRecY")
        cls.errorRecAngle = cfg.get("errorRecAngle")
        cls.errorRecTiltAngle = cls._safe_float(cfg.get("errorRecTiltAngle"), -1.0)
        cls.readjust = cls._safe_bool(cfg.get("readjust"), False)
        cls.readjustMaxTimes = max(1, int(cls._safe_float(cfg.get("readjustMaxTimes"), 3)))
        cls.readjustDistPrecision = max(0.0, cls._safe_float(cfg.get("readjustDistPrecision"), 0.02))
        cls.readjustAnglePrecision = max(0.0, cls._safe_float(cfg.get("readjustAnglePrecision"), 0.5))
        recognition_height_default = bool(
            getattr(cls.active_fork_class, "recognition_height_default", False)
        )
        cls.adjustHeight = cls._safe_bool(cfg.get("adjustHeight"), recognition_height_default)
        cam_lift_default = bool(getattr(cls.active_fork_class, "cam_lift_with_fork_default", False))
        cls.camLiftWithFork = cls._safe_bool(cfg.get("camLiftWithFork"), cam_lift_default)
        cls.camCalibMotorHeight = cls._safe_float(cfg.get("camCalibMotorHeight"), 0.0)
        adaptive_default = bool(getattr(
            cls.active_fork_class,
            "adaptive_pallet_stack_unstack_default",
            False,
        ))
        cls.adaptivePalletStackUnstack = cls.camLiftWithFork and cls._safe_bool(
            cfg.get("adaptivePalletStackUnstack"),
            adaptive_default,
        )
        cls.loadPalletLayer = max(1, int(cls._safe_float(cfg.get("loadPalletLayer"), 1)))
        cls.adjustMethod = str(cfg.get("adjustMethod") or "pathFirst")
        if cls.adjustMethod not in ("strechFirst", "pathFirst"):
            cls.adjustMethod = "pathFirst"
        cls.forkLeaveSafeHeight = max(0.0, cls._safe_float(cfg.get("forkLeaveSafeHeight"), 0.3))
        cls.reachMotorSyncTolerance = max(0.0, cls._safe_float(cfg.get("reachMotorSyncTolerance"), 0.02))
        cls.reachMotorMaxSpeed = max(0.001, cls._safe_float(cfg.get("reachMotorMaxSpeed"), 0.1))
        cls.zMax = cls._safe_bool(cfg.get("zMax"), True)
        cls.recCenterX = cfg.get("recCenterX", 0.0)
        cls.recCenterY = cfg.get("recCenterY", 0.0)
        cls.recRadius = cfg.get("recRadius", 0.7)
        cls.pathAdjustMode = cfg.get("pathAdjustMode", "bezier")
        cls.maxCurve = cfg.get("maxCurve", 3.0)
        cls.maxAngle = cfg.get("maxAngle", 10.0)

        # --- linearUnload
        cls.laserWidth = cfg.get("laserWidth")
        cls.obsDist = cfg.get("obsDist")
        cls.loadObsDist = cfg.get("loadObsDist")

        # --- location 3D detection
        cls.locDetect3d = cls._safe_bool(cfg.get("locDetect3d"), False)
        cls.locDetect3dDevice = str(cfg.get("device") or cfg.get("deviceName") or "")
        cls.obsAreaMinHeight = cls._safe_float(cfg.get("obsAreaMinHeight"), 0.05)
        cls.obsAreaMaxHeight = cls._safe_float(cfg.get("obsAreaMaxHeight"), 0.7)
        cls.obsAreaLength = cls._safe_float(cfg.get("obsAreaLength"), 1.5)
        cls.obsAreaWidth = cls._safe_float(cfg.get("obsAreaWidth"), 1.0)

        cls.reload_extra_config(cfg)

        cls._build_module_motor()

        Trace.log(f"Updated config: {cls.config}", False, name="fork.cfg")

    @staticmethod
    def _split_motor_names(value):
        if not value:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return [item.strip() for item in str(value).split(",") if item.strip()]

    @staticmethod
    def _safe_float(value, default=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_bool(value, default=False):
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            return value.lower() in ("on", "true", "1", "yes")
        return default

    @classmethod
    def _get_motor_limits(cls, motor_name):
        if not motor_name:
            return 0.0, 0.0
        basic_min = RobotParam.getDevice(motor_name, "basic.minLength")
        basic_max = RobotParam.getDevice(motor_name, "basic.maxLength")
        if basic_min is not None or basic_max is not None:
            return cls._safe_float(basic_min, 0.0), cls._safe_float(basic_max, 0.0)
        if is_do_motor_key(motor_name):
            min_length = cls._safe_float(RobotParam.getDevice(motor_name, "basic.minLength") or 0)
            max_length = cls._safe_float(RobotParam.getDevice(motor_name, "basic.maxLength") or 0)
        else:
            motor_func = RobotParam.getDevice(motor_name, "func") or RobotParam.getDevice(f"{cls.fork_motor_name}", "func") or ""

            min_length = cls._safe_float(RobotParam.getDevice(motor_name, f"func.{motor_func}.minLength") or 0)
            max_length = cls._safe_float(RobotParam.getDevice(motor_name, f"func.{motor_func}.maxLength") or 0)
        return min_length, max_length

    @classmethod
    def _get_motor_limit_di(cls, motor_name, direction):
        if not motor_name or is_do_motor_key(motor_name):
            return ""
        motor_func = RobotParam.getDevice(motor_name, "func") or cls.motor_func
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

    @classmethod
    def _find_config_value(cls, keys, node=_CONFIG_ROOT, visited=None):
        if node is _CONFIG_ROOT:
            node = cls.config
        if not isinstance(node, dict):
            return None
        if visited is None:
            visited = set()
        node_id = id(node)
        if node_id in visited:
            return None
        visited.add(node_id)
        for key in keys:
            if key in node:
                return node[key]
        for value in node.values():
            found = cls._find_config_value(keys, value, visited)
            if found is not None:
                return found
        return None

    @staticmethod
    def _is_position_control_on(value, default=True):
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() == "on"
        if isinstance(value, dict):
            if "positionControl" in value:
                return ConfigParams._is_position_control_on(value.get("positionControl"), default)
            if "Position Control" in value:
                return ConfigParams._is_position_control_on(value.get("Position Control"), default)
        return default

    @classmethod
    def _module_motor_position_enabled(cls, motor_type, motor_name, default=True):
        if not motor_name:
            return default
        keys = [
            f"left-{motor_name}",
            f"right-{motor_name}",
            f"{motor_type}-{motor_name}",
        ]
        value = cls._find_config_value(keys)
        return cls._is_position_control_on(value, default)

    @classmethod
    def _build_expand_motor_items(cls, motor_names):
        if len(motor_names) != 2:
            return [{"side": "", "motorKey": motor_name} for motor_name in motor_names]
        items = []
        for motor_name in motor_names:
            y = cls._safe_float(RobotParam.getDevice(motor_name, "installPosition.y") or 0)
            items.append({"side": "", "motorKey": motor_name, "y": y})
        items.sort(key=lambda item: item["y"])
        items[0]["side"] = "left"
        items[1]["side"] = "right"
        return items

    # 从设备模型文件中获取的参数
    @classmethod
    def get_device_model_param(cls):
        cls.chassis_type = RobotParam.getDevice("Model-000", "chassisType")
        cls.module_type = RobotParam.getDevice("Model-000", "moduleType") or ""
        cls.scriptName = RobotParam.getDevice("Model-000", f"moduleType.{cls.module_type}.moduleScript") or ""
        cls.fork_motor_name = RobotParam.getDevice("Model-000", f"moduleType.{cls.module_type}.liftMotor") or ""
        cls.shiftMotor = RobotParam.getDevice("Model-000", f"moduleType.{cls.module_type}.shiftMotor")
        cls.pitch_motor_name = RobotParam.getDevice("Model-000", f"moduleType.{cls.module_type}.pitchMotor") or ""
        cls.reach_motor_name = RobotParam.getDevice("Model-000", f"moduleType.{cls.module_type}.reachMotor") or ""
        cls.expand_motor_name = RobotParam.getDevice("Model-000", f"moduleType.{cls.module_type}.expandMotor") or ""
        cls.pitch_motor_names = cls._split_motor_names(cls.pitch_motor_name)
        cls.reach_motor_names = cls._split_motor_names(cls.reach_motor_name)
        cls.expand_motor_names = cls._split_motor_names(cls.expand_motor_name)
        cls.expand_motor_items = cls._build_expand_motor_items(cls.expand_motor_names)
        cls.expand_motor_left = ""
        cls.expand_motor_right = ""
        for item in cls.expand_motor_items:
            if item.get("side") == "left":
                cls.expand_motor_left = item["motorKey"]
            elif item.get("side") == "right":
                cls.expand_motor_right = item["motorKey"]
        cls.shape = RobotParam.getDevice("Model-000", "shape") or ""
        cls.head = float(RobotParam.getDevice("Model-000", f"shape.{cls.shape}.head") or 0)
        cls.tail = float(RobotParam.getDevice("Model-000", f"shape.{cls.shape}.tail") or 0)
        cls.width = float(RobotParam.getDevice("Model-000", f"shape.{cls.shape}.width") or 0)
        cls.module_x = float(RobotParam.getDevice("Model-000", f"moduleType.{cls.module_type}.installPosition.x") or 0)
        cls.fork_tip_width = float(RobotParam.getDevice("Model-000", f"moduleType.{cls.module_type}.forkWidth") or 0)
        cls.center_distance_between_forks = float(
            RobotParam.getDevice("Model-000", f"moduleType.{cls.module_type}.centerDistanceBetweenForks") or 0
        )

        cls.fork_root_3D_camera = RobotParam.getDevice("Model-000", f"moduleType.{cls.module_type}.forkRoot3DCamera")
        cls.fork_root_2D_lasers = RobotParam.getDevice("Model-000", f"moduleType.{cls.module_type}.forkRoot2DLasers")
        _tmp_val = RobotParam.getDevice("Model-000", f"moduleType.{cls.module_type}.forkTip3DCameras")
        cls.fork_tip_3D_cameras = _tmp_val.split(',') if _tmp_val else []
        _tmp_val = RobotParam.getDevice("Model-000", f"moduleType.{cls.module_type}.forkTip2DLasers")
        cls.fork_tip_2D_lasers = _tmp_val.split(',') if _tmp_val else []
        _tmp_val = RobotParam.getDevice("Model-000", f"moduleType.{cls.module_type}.diSensor")
        cls.fork_tip_di_sensors = _tmp_val.split(',') if _tmp_val else []
        _tmp_val = RobotParam.getDevice("Model-000", f"moduleType.{cls.module_type}.forkTipDistanceSensors")
        cls.fork_tip_distance_sensors = _tmp_val.split(',') if _tmp_val else []
        _tmp_val = RobotParam.getDevice("Model-000", f"moduleType.{cls.module_type}.id")
        cls.contact_ids = _tmp_val.split(',') if _tmp_val else []

        # 车型级扩展钩子：设备模型参数加载完成后，由各车型子类做差异化处理（如搬运车变轴距）。
        # 不再按 module_type 硬编码；具体逻辑下沉到 module/liftFork.py 等车型脚本。
        _call_fork_class_hook("on_device_model_param_loaded", cls)

    # 从设备模型文件中获取的参数
    @classmethod
    def get_device_motor_param(cls):
        """读取电机相关参数（线性电机）"""
        if is_do_motor_key(cls.fork_motor_name):
            ConfigParams.DOMotor = True
            cls.min_height = float(RobotParam.getDevice(f"{cls.fork_motor_name}", f"basic.minLength") or 0)
            cls.max_height = float(RobotParam.getDevice(f"{cls.fork_motor_name}", f"basic.maxLength") or 0)
        else:
            cls.motor_func = RobotParam.getDevice(f"{cls.fork_motor_name}", "func") or ""
            cls.min_height = float(
                RobotParam.getDevice(f"{cls.fork_motor_name}", f"func.{cls.motor_func}.minLength") or 0)
            cls.max_height = float(
                RobotParam.getDevice(f"{cls.fork_motor_name}", f"func.{cls.motor_func}.maxLength") or 0)
            cls.up_di = RobotParam.getDevice(f"{cls.fork_motor_name}", f"func.{cls.motor_func}.upLimitDI")
            cls.down_di = RobotParam.getDevice(f"{cls.fork_motor_name}", f"func.{cls.motor_func}.DownLimitDI")
            cls.fork_max_speed = float(
                RobotParam.getDevice(f"{cls.fork_motor_name}", f"func.{cls.motor_func}.maxSpeed") or 0)
            cls.reach_up_dist = float(
                RobotParam.getDevice(f"{cls.fork_motor_name}", f"func.{cls.motor_func}.reachUpDist") or 0)
            cls.reach_down_dist = float(
                RobotParam.getDevice(f"{cls.fork_motor_name}", f"func.{cls.motor_func}.reachDownDist") or 0)

        if cls.pitch_motor_name:
            cls.pitch_motor_min, cls.pitch_motor_max = cls._get_motor_limits(cls.pitch_motor_name)
        else:
            cls.pitch_motor_min = 0.0
            cls.pitch_motor_max = 0.0

        if cls.expand_motor_left:
            cls.expand_motor_left_min, cls.expand_motor_left_max = cls._get_motor_limits(cls.expand_motor_left)
        else:
            cls.expand_motor_left_min = 0.0
            cls.expand_motor_left_max = 0.0

        if cls.expand_motor_right:
            cls.expand_motor_right_min, cls.expand_motor_right_max = cls._get_motor_limits(cls.expand_motor_right)
        else:
            cls.expand_motor_right_min = 0.0
            cls.expand_motor_right_max = 0.0

    @classmethod
    def _build_fork_area(cls):
        # 货叉 / 车体近场碰撞区域统一使用相同的 rear / width 外扩，避免 clear region 与碰撞检测边界打架。
        tail_margin = 0.07
        width_margin = 0.03
        cls.fork_area = [{"x": cls.module_x - tail_margin, "y": cls.width / 2 + width_margin},
                         {"x": -cls.tail - tail_margin, "y": cls.width / 2 + width_margin},
                         {"x": -cls.tail - tail_margin, "y": -cls.width / 2 - width_margin},
                         {"x": cls.module_x - tail_margin, "y": -cls.width / 2 - width_margin}]

        cls.chassis_area = [{"x": cls.head, "y": cls.width / 2 + width_margin},
                            {"x": -cls.tail - tail_margin, "y": cls.width / 2 + width_margin},
                            {"x": -cls.tail - tail_margin, "y": -cls.width / 2 - width_margin},
                            {"x": cls.head, "y": -cls.width / 2 - width_margin}]

    @classmethod
    def _build_module_motor(cls):
        """构建 moduleMotor 列表"""
        cls.moduleMotor = []

        # lift 电机
        if cls.fork_motor_name:
            # lift 点动支持由各车型子类声明（默认支持；liftFork / pickFork 等声明 False）
            fork_cls = cls.active_fork_class
            lift_jog_support = getattr(fork_cls, "lift_jog_support", True) if fork_cls is not None else True
            lift_motor = {
                "type": "lift",
                "motorKey": cls.fork_motor_name,
                "jogSupport": lift_jog_support,
                "currentPosition": 0.0,
                "maxLength": cls.max_height,
                "minLength": cls.min_height
            }
            lift_motor["upLimitDi"] = (
                cls._get_motor_limit_di(cls.fork_motor_name, "up") or cls.up_di or ""
            )
            lift_motor["downLimitDi"] = (
                cls._get_motor_limit_di(cls.fork_motor_name, "down") or cls.down_di or ""
            )
            cls.moduleMotor.append(lift_motor)

        # shift 电机
        if cls.shiftMotor:
            cls._append_module_motor("shift", cls.shiftMotor, "shiftMotor", "")

        # pitch 电机
        for motor_name in cls.pitch_motor_names:
            cls._append_module_motor("pitch", motor_name, "pitchMotor", "")

        # reach 电机
        for motor_name in cls.reach_motor_names:
            cls._append_module_motor("reach", motor_name, "reachMotor", "")

        # expand 电机
        for item in cls.expand_motor_items:
            cls._append_module_motor("expand", item["motorKey"], "expandMotor", item.get("side", ""))

        Trace.log(f"moduleMotor built count={len(cls.moduleMotor)}", name=f"{MOD}.cfg")

    @classmethod
    def _append_module_motor(cls, motor_type, motor_name, config_type, side):
        if not motor_name:
            return
        min_length, max_length = cls._get_motor_limits(motor_name)
        motor = {
            "type": motor_type,
            "motorKey": motor_name,
            "jogSupport": cls._module_motor_position_enabled(config_type, motor_name, True),
            "currentPosition": 0.0,
            "maxLength": max_length,
            "minLength": min_length
        }
        motor["upLimitDi"] = cls._get_motor_limit_di(motor_name, "up")
        motor["downLimitDi"] = cls._get_motor_limit_di(motor_name, "down")
        if side:
            motor["side"] = side
        cls.moduleMotor.append(motor)

    @staticmethod
    def _build_position_control_config(builder, key, name):
        with builder.CHILD(key=key, name=name, desc=_TR("Position Control")):
            builder.TYPE(ParamType.ARRAY)
            with builder.CHILDREN():
                with builder.CHILD(key="positionControl", name=_TR("Position Control"), desc=_TR("Position Control")):
                    builder.TYPE(ParamType.COMBO_BOX_BOOL)
                    builder.DEFAULTVALUE("on")
                    with builder.CHILDREN():
                        with builder.CHILD(key="on", name=_TR("On"), desc=_TR("Enable position control")):
                            builder.TYPE(ParamType.ARRAY)
                        with builder.CHILD(key="off", name=_TR("Off"), desc=_TR("Disable position control")):
                            builder.TYPE(ParamType.ARRAY)

    def get_app_rec_param(cls):
        pass

    @classmethod
    def reload_extra_config(cls, cfg):
        _run_script_hook("config_reload_hook", cls, cfg)

    @classmethod
    def extend_config_builder(cls, builder):
        _run_script_hook("config_builder_hook", cls, builder)

    # 设置脚本配置参数
    @classmethod
    def _build_and_load_config(cls):
        builder = _require_param_loader().builderConfig()

        with builder.GROUPS():
            # ===== 脚本相关 =====
            with builder.GROUP(key="script", name=_TR("Script Settings"), desc=_TR("Script configuration")):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILD(key="timeout", name=_TR("Timeout"), desc=_TR("Script timeout")):
                    builder.TYPE(ParamType.FLOAT)
                    builder.DEFAULTVALUE(200)
                    builder.UNIT("s")

                with builder.CHILD(key="scriptDebug", name=_TR("Script Debug"), desc=_TR("Enable script debug logs")):
                    builder.TYPE(ParamType.BOOL)
                    builder.DEFAULTVALUE(False)

                with builder.CHILD(key="autoPreAdvanceTime", name=_TR("AutoPre Advance Time"),
                                   desc=_TR("Advance time used to start the AutoPre action")):
                    builder.TYPE(ParamType.FLOAT)
                    builder.DEFAULTVALUE(1.0, min_value=0)
                    builder.UNIT("s")

            # ===== fork 相关 =====
            with builder.GROUP(key="fork", name=_TR("Fork Settings"), desc=_TR("Fork configuration")):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    with builder.CHILD(key="upMaxSpeedWithGoods", name=_TR("Up Max Speed With Goods"),
                                       desc=_TR("Maximum fork lift speed with goods")):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.06, min_value=-1, max_value=0.5)
                        builder.UNIT("m/s")
                    with builder.CHILD(key="downMaxSpeedWithGoods", name=_TR("Down Max Speed With Goods"),
                                       desc=_TR("Maximum fork lower speed with goods")):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.06, min_value=-1, max_value=0.5)
                        builder.UNIT("m/s")
                    with builder.CHILD(key="backLaserEnableHeight", name=_TR("Back Laser Enable Height"),
                                       desc=_TR("Fork height at which the rear laser becomes active")):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.3, min_value=0, max_value=2)
                        builder.UNIT("m")
                    with builder.CHILD(key="checkGoodsWhileLoad", name=_TR("Check Goods While Load"),
                                       desc=_TR("Check the goods DI during loading")):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(False)
                    with builder.CHILD(key="enableLoadTime", name=_TR("Enable Load Time"),
                                       desc=_TR("Enable the fork lift timeout")):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(True)
                        with builder.CHILDREN():
                            with builder.CHILD(key="loadTime", name=_TR("Load Time"),
                                               desc=_TR("Fork lift timeout")):
                                builder.TYPE(ParamType.FLOAT)
                                builder.DEFAULTVALUE(30, min_value=-1, max_value=300)
                                builder.UNIT("s")
                    with builder.CHILD(key="enableUnLoadTime", name=_TR("Enable Unload Time"),
                                       desc=_TR("Enable the fork lower timeout")):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(True)
                        with builder.CHILDREN():
                            with builder.CHILD(key="UnloadTime", name=_TR("Unload Time"),
                                               desc=_TR("Fork lower timeout")):
                                builder.TYPE(ParamType.FLOAT)
                                builder.DEFAULTVALUE(30, min_value=-1, max_value=300)
                                builder.UNIT("s")
                    with builder.CHILD(key="upDo", name=_TR("UP DO"), desc=_TR("DO used to lift the fork")):
                        builder.TYPE(ParamType.BIND_TYPE)
                        builder.BINDTYPE(BindType.Device.DO)
                    with builder.CHILD(key="upDoStatus", name=_TR("Up Do Status"), desc=_TR("DO state used to lift the fork")):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(False)
                    with builder.CHILD(key="downDo", name=_TR("Down DO"), desc=_TR("DO used to lower the fork")):
                        builder.TYPE(ParamType.BIND_TYPE)
                        builder.BINDTYPE(BindType.Device.DO)
                    with builder.CHILD(key="downDoStatus", name=_TR("Down Do Status"), desc=_TR("DO state used to lower the fork")):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(False)
                    with builder.CHILD(key="enableNavForkHeight", name=_TR("Enable Nav Fork Height"),
                                       desc=_TR("Enable the fork travel height without goods")):
                        builder.TYPE(ParamType.COMBO_BOX_BOOL)
                        builder.DEFAULTVALUE("off")
                        with builder.CHILDREN():
                            with builder.CHILD(key="off", name=_TR("Off"),
                                               desc=_TR("Disable the fork travel height without goods")):
                                builder.TYPE(ParamType.ARRAY)
                            with builder.CHILD(key="on", name=_TR("On"),
                                               desc=_TR("Enable the fork travel height without goods")):
                                builder.TYPE(ParamType.ARRAY)
                                with builder.CHILDREN():
                                    with builder.CHILD(key="navForkHeight", name=_TR("Nav Fork Height"),
                                                       desc=_TR("Fork travel height without goods")):
                                        builder.TYPE(ParamType.FLOAT)
                                        builder.DEFAULTVALUE(0.3, min_value=ConfigParams.min_height,
                                                             max_value=ConfigParams.max_height)
                                        builder.UNIT("m")
                                    with builder.CHILD(key="allowForkMoveWhileNav",
                                                       name=_TR("Allow Fork Move While Nav"),
                                                       desc=_TR("Allow the fork to move during navigation")):
                                        builder.TYPE(ParamType.BOOL)
                                        builder.DEFAULTVALUE(False)
                    with builder.CHILD(key="enableLoadNavForkHeight", name=_TR("Enable Load Nav Fork Height"),
                                       desc=_TR("Enable the fork travel height with goods")):
                        builder.TYPE(ParamType.COMBO_BOX_BOOL)
                        builder.DEFAULTVALUE("off")
                        with builder.CHILDREN():
                            with builder.CHILD(key="off", name=_TR("Off"),
                                               desc=_TR("Disable the fork travel height with goods")):
                                builder.TYPE(ParamType.ARRAY)
                            with builder.CHILD(key="on", name=_TR("On"),
                                               desc=_TR("Enable the fork travel height with goods")):
                                builder.TYPE(ParamType.ARRAY)
                                with builder.CHILDREN():
                                    with builder.CHILD(key="loadNavForkHeight", name=_TR("Load Nav Fork Height"),
                                                       desc=_TR("Fork travel height with goods")):
                                        builder.TYPE(ParamType.FLOAT)
                                        builder.DEFAULTVALUE(0.3, min_value=ConfigParams.min_height,
                                                             max_value=ConfigParams.max_height)
                                        builder.UNIT("m")
                                    with builder.CHILD(key="allowLoadForkMoveWhileNav",
                                                       name=_TR("Allow Load Fork Move While Nav"),
                                                       desc=_TR("Allow the loaded fork to move during navigation")):
                                        builder.TYPE(ParamType.BOOL)
                                        builder.DEFAULTVALUE(False)

                    add_weight_config(builder)

            # ===== 取放货 =====
            with builder.GROUP(key="loadUnload", name=_TR("Load & Unload"), desc=_TR("Load and unload configuration")):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    with builder.CHILD(key="pathAdjustMode", name=_TR("Path Adjust Mode"), desc=_TR("Path adjustment mode")):
                        builder.TYPE(ParamType.COMBO_BOX)
                        builder.DEFAULTVALUE("bezier")

                        with builder.CHILDREN():
                            with builder.CHILD(key="bezier", name=_TR("Bezier"), desc=_TR("Bezier path adjustment")):
                                builder.TYPE(ParamType.ARRAY)
                                with builder.CHILDREN():
                                    with builder.CHILD(key="maxCurve", name=_TR("Max Curve"),
                                                       desc=_TR("Maximum curvature for Bezier path adjustment")):
                                        builder.TYPE(ParamType.FLOAT)
                                        builder.DEFAULTVALUE(3)
                                        builder.UNIT("m")

                            with builder.CHILD(key="straightLine", name=_TR("Straight Line"), desc=_TR("Straight-line path adjustment")):
                                builder.TYPE(ParamType.ARRAY)
                                with builder.CHILDREN():
                                    with builder.CHILD(key="maxAngle", name=_TR("Max Angle"),
                                                       desc=_TR("Maximum angle for straight-line path adjustment")):
                                        builder.TYPE(ParamType.FLOAT)
                                        builder.DEFAULTVALUE(10)
                                        builder.UNIT("deg")

                    with builder.CHILD(key="returnOnSamePath", name=_TR("Return On Same Path"),
                                       desc=_TR("Return on the same path after recognition adjustment")):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(True)

                    with builder.CHILD(key="locDetect3d", name=_TR("Location 3D Detection"),
                                       desc=_TR("Check whether the target location contains goods")):
                        builder.TYPE(ParamType.COMBO_BOX_BOOL)
                        builder.DEFAULTVALUE("off")
                        with builder.CHILDREN():
                            with builder.CHILD(key="off", name=_TR("Disable Location 3D Detection"),
                                               desc=_TR("Do not check the target location")):
                                builder.TYPE(ParamType.ARRAY)
                            with builder.CHILD(key="on", name=_TR("Enable Location 3D Detection"),
                                               desc=_TR("Check the target location before load or unload")):
                                builder.TYPE(ParamType.ARRAY)
                                with builder.CHILDREN():
                                    with builder.CHILD(key="device", name=_TR("Detection Device"),
                                                       desc=_TR("Laser or camera used for location detection")):
                                        builder.TYPE(ParamType.BIND_TYPE)
                                        builder.BINDTYPE(
                                            BindItem(BindType.Device.LASER)
                                            + BindItem(BindType.Device.CAMERA)
                                        )
                                    with builder.CHILD(key="obsAreaMinHeight", name=_TR("Obstacle Area Min Height"),
                                                       desc=_TR("Minimum height of the location detection area")):
                                        builder.TYPE(ParamType.FLOAT)
                                        builder.DEFAULTVALUE(0.05, min_value=0, max_value=10)
                                        builder.UNIT("m")
                                    with builder.CHILD(key="obsAreaMaxHeight", name=_TR("Obstacle Area Max Height"),
                                                       desc=_TR("Maximum height of the location detection area")):
                                        builder.TYPE(ParamType.FLOAT)
                                        builder.DEFAULTVALUE(0.7, min_value=0, max_value=10)
                                        builder.UNIT("m")
                                    with builder.CHILD(key="obsAreaLength", name=_TR("Obstacle Area Length"),
                                                       desc=_TR("Length of the location detection area")):
                                        builder.TYPE(ParamType.FLOAT)
                                        builder.DEFAULTVALUE(1.5, min_value=0, max_value=10)
                                        builder.UNIT("m")
                                    with builder.CHILD(key="obsAreaWidth", name=_TR("Obstacle Area Width"),
                                                       desc=_TR("Width of the location detection area")):
                                        builder.TYPE(ParamType.FLOAT)
                                        builder.DEFAULTVALUE(1.0, min_value=0, max_value=10)
                                        builder.UNIT("m")

                    if bool(getattr(ConfigParams.active_fork_class, "supports_reach_motor", False)):
                        with builder.CHILD(key="adjustMethod", name=_TR("Reach Adjust Method"),
                                           desc=_TR("Reach mechanism adjustment sequence for loading")):
                            builder.TYPE(ParamType.STRING_COMBO_LIST)
                            builder.DEFAULTVALUE("pathFirst")
                            with builder.CHILDREN():
                                with builder.CHILD(key="strechFirst", name=_TR("Stretch First"),
                                                   desc=_TR("Extend the reach mechanism before path adjustment")):
                                    builder.TYPE(ParamType.STRING)
                                with builder.CHILD(key="pathFirst", name=_TR("Path First"),
                                                   desc=_TR("Move to the approach point, extend the reach mechanism, then insert straight")):
                                    builder.TYPE(ParamType.STRING)
                        with builder.CHILD(key="forkLeaveSafeHeight", name=_TR("Fork Leave Safe Height"),
                                           desc=_TR("Minimum fork height for retracting the reach mechanism after leaving the location")):
                            builder.TYPE(ParamType.FLOAT)
                            builder.DEFAULTVALUE(0.3, min_value=0, max_value=2)
                            builder.UNIT("m")
                        with builder.CHILD(key="reachMotorSyncTolerance", name=_TR("Reach Motor Sync Tolerance"),
                                           desc=_TR("Maximum allowed relative extension difference between reach motors")):
                            builder.TYPE(ParamType.FLOAT)
                            builder.DEFAULTVALUE(0.02, min_value=0, max_value=0.2)
                            builder.UNIT("m")
                        with builder.CHILD(key="reachMotorMaxSpeed", name=_TR("Reach Motor Max Speed"),
                                           desc=_TR("Maximum reach motor speed")):
                            builder.TYPE(ParamType.FLOAT)
                            builder.DEFAULTVALUE(0.1, min_value=0.001, max_value=1)
                            builder.UNIT("m/s")

                    with builder.CHILD(key="forkDiDist", name=_TR("Fork DI Dist"), desc=_TR("Back-off distance after blind insertion reaches the target")):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.1, min_value=-2, max_value=2)
                        builder.UNIT("m")
                    if ConfigParams.fork_tip_2D_lasers:
                        with builder.CHILD(key="laserDetectionWidth", name=_TR("Load Laser Detection Width"),
                                           desc=_TR("Laser width during fork insertion")):
                            builder.TYPE(ParamType.FLOAT)
                            builder.DEFAULTVALUE(0.05, min_value=0, max_value=2)
                            builder.UNIT("m")
                    with builder.CHILD(key="loadObsStopDist", name=_TR("Load Obstacle Stop Distance"),
                                       desc=_TR("Obstacle stop distance while backing during loading")):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.05, min_value=0, max_value=2)
                        builder.UNIT("m")
                    with builder.CHILD(key="checkAllContactDi", name=_TR("Check All Contact DI"),
                                       desc=_TR("Check all contact DIs; contact DI detection must be enabled first")):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(False)

                    if ConfigParams.fork_tip_di_sensors:
                        with builder.CHILD(key="forkDiEnableAtLoad", name=_TR("Fork Di Enable At Load"),
                                           desc=_TR("Enable fork-tip DI sensors during loading; disable them to prevent false blocking")):
                            builder.TYPE(ParamType.BOOL)
                            builder.DEFAULTVALUE(False)

                        with builder.CHILD(key="forkDiEnableAtUnload", name=_TR("Fork Di Enable At Unload"),
                                           desc=_TR("Enable fork-tip DI sensors during unloading")):
                            builder.TYPE(ParamType.COMBO_BOX_BOOL)
                            builder.DEFAULTVALUE("on")
                            with builder.CHILDREN():
                                # on选项
                                with builder.CHILD(key="on", name=_TR("Fork Di Enable At Unload"),
                                                   desc=_TR("Enable fork-tip DI during unloading")):
                                    builder.TYPE(ParamType.ARRAY)
                                    with builder.CHILD(key="diTriggerMeasureUnload", name=_TR("Di Trigger Measure Unload"),
                                                       desc=_TR("Robot behavior when a DI is triggered during unloading")):
                                        builder.TYPE(ParamType.STRING_COMBO_LIST)
                                        builder.DEFAULTVALUE("collision")
                                        with builder.CHILDREN():
                                            with builder.CHILD("collision", _TR("Collision"), _TR("Report a collision")):
                                                builder.TYPE(ParamType.STRING)
                                            with builder.CHILD("autoClearError", _TR("Auto Clear Error"),
                                                               _TR("Report goods present when triggered; continue when not triggered")):
                                                builder.TYPE(ParamType.STRING)
                                            with builder.CHILD("failTask", _TR("Fail Task"), _TR("Fail the task when triggered")):
                                                builder.TYPE(ParamType.STRING)

                                # off选项
                                with builder.CHILD(key="off", name=_TR("Fork Di Disable At Unload"),
                                                   desc=_TR("Disable fork-tip DI during unloading")):
                                    builder.TYPE(ParamType.ARRAY)

                    if bool(getattr(ConfigParams.active_fork_class, "supports_cam_lift_with_fork", False)):
                        with builder.CHILD(key="camLiftWithFork", name=_TR("Camera Lift With Fork"),
                                           desc=_TR("Camera height conversion and adaptive pallet unstacking configuration")):
                            builder.TYPE(ParamType.COMBO_BOX_BOOL)
                            builder.DEFAULTVALUE(
                                "on" if bool(getattr(
                                    ConfigParams.active_fork_class,
                                    "cam_lift_with_fork_default",
                                    False,
                                )) else "off"
                            )
                            with builder.CHILDREN():
                                with builder.CHILD(key="off", name=_TR("Disable Camera Lift With Fork"),
                                                   desc=_TR("Disable camera height conversion configuration")):
                                    builder.TYPE(ParamType.ARRAY)
                                with builder.CHILD(key="on", name=_TR("Enable Camera Lift With Fork"),
                                                   desc=_TR("Enable camera height conversion configuration")):
                                    builder.TYPE(ParamType.ARRAY)
                                    with builder.CHILDREN():
                                        with builder.CHILD(
                                                key="camCalibMotorHeight",
                                                name=_TR("Camera Calib Motor Height"),
                                                desc=_TR("Lift motor height during camera calibration, used only to calculate recognition pick height")):
                                            builder.TYPE(ParamType.FLOAT)
                                            builder.DEFAULTVALUE(0.0)
                                            builder.UNIT("m")
                                        with builder.CHILD(
                                                key="adaptivePalletStackUnstack",
                                                name=_TR("Adaptive Pallet Stack Unstack"),
                                                desc=_TR("Enable pallet layer selection from recognition results")):
                                            builder.TYPE(ParamType.COMBO_BOX_BOOL)
                                            builder.DEFAULTVALUE(
                                                "on" if bool(getattr(
                                                    ConfigParams.active_fork_class,
                                                    "adaptive_pallet_stack_unstack_default",
                                                    False,
                                                )) else "off"
                                            )
                                            with builder.CHILDREN():
                                                with builder.CHILD(
                                                        key="off",
                                                        name=_TR("Disable Adaptive Pallet Stack Unstack"),
                                                        desc=_TR("Disable adaptive pallet unstacking")):
                                                    builder.TYPE(ParamType.ARRAY)
                                                with builder.CHILD(
                                                        key="on",
                                                        name=_TR("Enable Adaptive Pallet Stack Unstack"),
                                                        desc=_TR("Enable adaptive pallet unstacking")):
                                                    builder.TYPE(ParamType.ARRAY)
                                                    with builder.CHILDREN():
                                                        with builder.CHILD(
                                                                key="loadPalletLayer",
                                                                name=_TR("Load Pallet Layer"),
                                                                desc=_TR("Default pallet layer to load; 1 is the highest layer")):
                                                            builder.TYPE(ParamType.INT)
                                                            builder.DEFAULTVALUE(1, min_value=1)

                    with builder.CHILD(key="recLoad", name=_TR("Recognition Load"),
                                       desc=_TR("Recognition load configuration")):
                        builder.TYPE(ParamType.ARRAY)
                        with builder.CHILDREN():
                            # 需要移到 bintask
                            with builder.CHILD(key="zMax", name=_TR("Sort Recognition Results By Height"),
                                               desc=_TR("Sort recognition results by height in descending order")):
                                builder.TYPE(ParamType.BOOL)
                                builder.DEFAULTVALUE(False)
                            with builder.CHILD(key="errorRecY", name=_TR("Error Rec Y"),
                                               desc=_TR("Recognition Y error threshold relative to the AP; -1 disables the check")):
                                builder.TYPE(ParamType.FLOAT)
                                builder.DEFAULTVALUE(0.1)
                                builder.UNIT("m")
                            with builder.CHILD(key="errorRecAngle", name=_TR("Error Rec Angle"),
                                               desc=_TR("Recognition yaw error threshold relative to the AP; -1 disables the check")):
                                builder.TYPE(ParamType.FLOAT)
                                builder.DEFAULTVALUE(15)
                                builder.UNIT("°")
                            with builder.CHILD(key="errorRecTiltAngle", name=_TR("Error Rec Tilt Angle"),
                                               desc=_TR("Recognition pallet tilt error threshold; -1 disables the check")):
                                builder.TYPE(ParamType.FLOAT)
                                builder.DEFAULTVALUE(-1)
                                builder.UNIT("°")
                            with builder.CHILD(key="readjust", name=_TR("Recognition Readjust"),
                                               desc=_TR("Move to the target approach point and recognize again for fine adjustment")):
                                builder.TYPE(ParamType.BOOL)
                                builder.DEFAULTVALUE(False)
                            with builder.CHILD(key="readjustMaxTimes", name=_TR("Recognition Readjust Max Times"),
                                               desc=_TR("Maximum number of secondary recognition adjustments")):
                                builder.TYPE(ParamType.INT)
                                builder.DEFAULTVALUE(3, min_value=1, max_value=5)
                            with builder.CHILD(key="readjustDistPrecision", name=_TR("Recognition Readjust Dist Precision"),
                                               desc=_TR("Lateral convergence tolerance for secondary recognition in robot coordinates")):
                                builder.TYPE(ParamType.FLOAT)
                                builder.DEFAULTVALUE(0.02, min_value=0, max_value=0.5)
                                builder.UNIT("m")
                            with builder.CHILD(key="readjustAnglePrecision", name=_TR("Recognition Readjust Angle Precision"),
                                               desc=_TR("Angular convergence tolerance for secondary recognition in robot coordinates")):
                                builder.TYPE(ParamType.FLOAT)
                                builder.DEFAULTVALUE(0.5, min_value=0, max_value=10)
                                builder.UNIT("°")
                            with builder.CHILD(key="adjustHeight", name=_TR("Adjust Height By Recognition"),
                                               desc=_TR("Use recognition results to calculate fork height during loading")):
                                builder.TYPE(ParamType.BOOL)
                                builder.DEFAULTVALUE(bool(getattr(
                                    ConfigParams.active_fork_class,
                                    "recognition_height_default",
                                    False,
                                )))
                            with builder.CHILD(key="enableTcp", name=_TR("Enable TCP"), desc=_TR("Enable TCP for recognition loading")):
                                builder.TYPE(ParamType.BOOL)
                                builder.DEFAULTVALUE(False)
                            with builder.CHILD(key="aheadDist", name=_TR("Ahead Dist"), desc=_TR("Approach distance for recognition loading")):
                                builder.TYPE(ParamType.FLOAT)
                                builder.DEFAULTVALUE(0.8, min_value=0, max_value=2)
                                builder.UNIT("m")
                            with builder.CHILD(key="minAheadDist", name=_TR("Min Ahead Dist"),
                                               desc=_TR("Minimum straight-line distance for recognition loading")):
                                builder.TYPE(ParamType.FLOAT)
                                builder.DEFAULTVALUE(ConfigParams.tail + 0.1, min_value=-2, max_value=2)
                                builder.UNIT("m")
                            with builder.CHILD(key="recCenterX", name=_TR("Rec Center X"),
                                               desc=_TR("Recognition region center X in robot coordinates when no AP is specified")):
                                builder.TYPE(ParamType.FLOAT)
                                builder.DEFAULTVALUE(-(ConfigParams.tail + 0.3), min_value=-5, max_value=5)
                                builder.UNIT("m")
                            with builder.CHILD(key="recCenterY", name=_TR("Rec Center Y"),
                                               desc=_TR("Recognition region center Y in robot coordinates when no AP is specified")):
                                builder.TYPE(ParamType.FLOAT)
                                builder.DEFAULTVALUE(0.0, min_value=-5, max_value=5)
                                builder.UNIT("m")
                            with builder.CHILD(key="recRadius", name=_TR("Rec Radius"),
                                               desc=_TR("Recognition radius")):
                                builder.TYPE(ParamType.FLOAT)
                                builder.DEFAULTVALUE(0.7, min_value=0.1, max_value=5)
                                builder.UNIT("m")
                    with builder.CHILD(key="noRecLoad", name=_TR("Load By Landmark"),
                                       desc=_TR("Load by station position")):
                        builder.TYPE(ParamType.ARRAY)
                        with builder.CHILDREN():
                            with builder.CHILD(key="enableContactDiNoRec", name=_TR("Enable Contact DI (No Rec)"),
                                               desc=_TR("Enable contact DIs for loading without recognition")):
                                builder.TYPE(ParamType.BOOL)
                                builder.DEFAULTVALUE(True)
                    with builder.CHILD(key="useForPalletFallProtection", name=_TR("Use For Pallet Fall Protection"),
                                       desc=_TR("Enable pallet fall protection during loading and unloading")):
                        builder.TYPE(ParamType.COMBO_BOX_BOOL)
                        builder.DEFAULTVALUE("off")
                        with builder.CHILDREN():
                            # off选项
                            with builder.CHILD(key="off", name=_TR("Disable Pallet Fall Protection"),
                                               desc=_TR("Disable Pallet Fall Protection")):
                                builder.TYPE(ParamType.ARRAY)

                            # on选项
                            with builder.CHILD(key="on", name=_TR("Enable Pallet Fall Protection"),
                                               desc=_TR("Use an external IMU")):
                                builder.TYPE(ParamType.ARRAY)

                                with builder.CHILDREN():
                                    with builder.CHILD(key="setRoiX", name=_TR("Set Roi X"),
                                                       desc=""):
                                        builder.TYPE(ParamType.FLOAT)
                                        builder.REQUIRED(True)
                                        builder.DEFAULTVALUE(2.0)
                                    with builder.CHILD(key="setRoiMaxY", name=_TR("Set Roi Max Y"),
                                                       desc=""):
                                        builder.TYPE(ParamType.FLOAT)
                                        builder.REQUIRED(True)
                                        builder.DEFAULTVALUE(2.0)
                                    with builder.CHILD(key="setRoiMinY", name=_TR("Set Roi Min Y"),
                                                       desc=""):
                                        builder.TYPE(ParamType.FLOAT)
                                        builder.REQUIRED(True)
                                        builder.DEFAULTVALUE(2.0)
                                    with builder.CHILD(key="setRoiZ", name=_TR("Set Roi Z"),
                                                       desc=""):
                                        builder.TYPE(ParamType.FLOAT)
                                        builder.REQUIRED(True)
                                        builder.DEFAULTVALUE(2.0)

                    with builder.CHILD(key="enableFallingDownDetect", name=_TR("Enable Falling Down Detect"),
                                       desc=_TR("Enable pallet fall detection during loading and unloading")):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(bool(getattr(
                            ConfigParams.active_fork_class,
                            "falling_down_detect_default",
                            False,
                        )))

            # ===== moduleMotor =====
            with builder.GROUP(key="moduleMotor", name=_TR("Module Motor Settings"), desc=_TR("Module motor settings")):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    if ConfigParams.shiftMotor:
                        ConfigParams._build_position_control_config(
                            builder, f"shiftMotor-{ConfigParams.shiftMotor}", f"shiftMotor-{ConfigParams.shiftMotor}"
                        )
                    for motor_name in ConfigParams.pitch_motor_names:
                        ConfigParams._build_position_control_config(
                            builder, f"pitchMotor-{motor_name}", f"pitchMotor-{motor_name}"
                        )
                    for motor_name in ConfigParams.reach_motor_names:
                        ConfigParams._build_position_control_config(
                            builder, f"reachMotor-{motor_name}", f"reachMotor-{motor_name}"
                        )
                    for item in ConfigParams.expand_motor_items:
                        motor_name = item["motorKey"]
                        side = item.get("side", "")
                        if side:
                            with builder.CHILD(key=f"expandMotor-{motor_name}", name=f"expandMotor-{motor_name}",
                                               desc=_TR("Expand Motor")):
                                builder.TYPE(ParamType.ARRAY)
                                with builder.CHILDREN():
                                    ConfigParams._build_position_control_config(
                                        builder, f"{side}-{motor_name}", f"{side}-{motor_name}"
                                    )
                        else:
                            ConfigParams._build_position_control_config(
                                builder, f"expandMotor-{motor_name}", f"expandMotor-{motor_name}"
                            )
            # ===== 线性堆栈 =====
            with builder.GROUP(key="linearUnload", name=_TR("Linear Unload"), desc=_TR("Linear unload configuration")):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    with builder.CHILD(key="laserWidth", name=_TR("Laser Width"), desc=_TR("Laser width for linear unloading")):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.1, min_value=0, max_value=1)
                        builder.UNIT("m")
                    with builder.CHILD(key="obsDist", name=_TR("Obs Dist"), desc=_TR("Obstacle distance for linear unloading")):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.5, min_value=0, max_value=1)
                        builder.UNIT("m")
                    with builder.CHILD(key="loadObsDist", name=_TR("Load Obs Dist"), desc=_TR("Obstacle distance during fork insertion for loading")):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.1, min_value=0, max_value=11)
                        builder.UNIT("m")

            cls.extend_config_builder(builder)

        builder.save(merge=True)
        cls.reload_config()

class InputParams:
    builder = None

    @classmethod
    def extend_recognize_on_params(cls, builder):
        _run_script_hook("rec_input_params_hook", cls, builder)

    @classmethod
    def extend_operation_inputs(cls, builder, min_height: float, max_height: float):
        _run_script_hook("operation_input_hook", cls, builder, min_height, max_height)

    @classmethod
    def extend_root_inputs(cls, builder):
        _run_script_hook("root_input_hook", cls, builder)

    @classmethod
    def extend_custom_operation_inputs(cls, builder, min_height: float, max_height: float):
        _run_script_hook("custom_operation_inputs_hook", cls, builder, min_height, max_height)

    @classmethod
    def init(cls, script_file: str):
        cls.builder = ParamBuilder(script_file, desc=_TR("Input parameter configuration"))
        min_height = ConfigParams.min_height
        max_height = ConfigParams.max_height

        with cls.builder.GROUPS():
            # 公共参数:
            # 使用PGV参数
            # with builder.CHILD(key="use_pgv", name="Use PGV", desc="Use PGV for position adjustment"):
            #     builder.TYPE(ParamType.BOOL)
            #     builder.DEFAULTVALUE(False)

            # 操作组合框
            with cls.builder.GROUP(key="operation", name=_TR("Operations"), desc=_TR("Task script input parameters")):
                cls.builder.TYPE(ParamType.COMBO_BOX)

                with cls.builder.CHILDREN():
                    # 取货操作
                    with cls.builder.CHILD(key="load", name=_TR("Fork Load"), desc=_TR("Load the pallet")):
                        cls.builder.TYPE(ParamType.ARRAY)

                        with cls.builder.CHILDREN():
                            lift_fork_limits = bool(getattr(
                                ConfigParams.active_fork_class, "lift_fork_model_limits", False
                            ))
                            if not lift_fork_limits:
                                create_start_height_param(cls.builder, min_height, max_height)
                                create_end_height_param(cls.builder, min_height, max_height)
                            if bool(getattr(ConfigParams.active_fork_class, "supports_loc_detection", False)):
                                create_loc_detect_height_param(cls.builder, min_height, max_height)
                                create_loc_detect_layer_param(cls.builder)
                            create_rec_param(
                                cls.builder,
                                cls.extend_recognize_on_params,
                                include_rec_height=not lift_fork_limits,
                            )

                            if not lift_fork_limits:
                                with cls.builder.CHILD(key="leaveLocHeight", name=_TR("Leave Loc Height"),
                                                       desc=_TR("The fork height after leave loc")):
                                    cls.builder.TYPE(ParamType.FLOAT)
                                    cls.builder.UNIT("m")
                                    cls.builder.SINGLESTEP(0.01)
                                    cls.builder.DEFAULTVALUE(-1)
                            with cls.builder.CHILD(key="leaveLoc", name=_TR("Leave Loc"),
                                                   desc=_TR("Return to the source location after load")):
                                cls.builder.TYPE(ParamType.BOOL)
                                cls.builder.DEFAULTVALUE(False)

                    # 放货操作
                    with cls.builder.CHILD(key="unload", name=_TR("Fork Unload"),
                                           desc=_TR("Unload the pallet")):
                        cls.builder.TYPE(ParamType.ARRAY)

                        with cls.builder.CHILDREN():
                            lift_fork_limits = bool(getattr(
                                ConfigParams.active_fork_class, "lift_fork_model_limits", False
                            ))
                            if not lift_fork_limits:
                                create_start_height_param(cls.builder, min_height, max_height)
                                create_end_height_param(cls.builder, min_height, max_height)
                            if bool(getattr(ConfigParams.active_fork_class, "supports_loc_detection", False)):
                                create_loc_detect_height_param(cls.builder, min_height, max_height)
                                create_loc_detect_layer_param(cls.builder)
                            create_rec_param(
                                cls.builder,
                                cls.extend_recognize_on_params,
                                include_rec_height=not lift_fork_limits,
                            )

                            if not lift_fork_limits:
                                with cls.builder.CHILD(key="leaveLocHeight", name=_TR("Leave Loc Height"),
                                                       desc=_TR("The fork height after leave loc")):
                                    cls.builder.TYPE(ParamType.FLOAT)
                                    cls.builder.UNIT("m")
                                    cls.builder.SINGLESTEP(0.01)
                                    cls.builder.DEFAULTVALUE(-1)
                            with cls.builder.CHILD(key="leaveLoc", name=_TR("Leave Loc"),
                                                   desc=_TR("Return to the source location after unload")):
                                cls.builder.TYPE(ParamType.BOOL)
                                cls.builder.DEFAULTVALUE(False)

                    # ForkHeight 操作
                    with cls.builder.CHILD(key="forkHeight", name=_TR("Fork Height"),
                                           desc=_TR("Lift the fork")):
                        cls.builder.TYPE(ParamType.ARRAY)
                        create_fork_height_param(cls.builder, min_height, max_height)

                        with cls.builder.CHILD(key="forkSpeed", name=_TR("Fork Speed"), desc=_TR("Fork lift speed")):
                            cls.builder.TYPE(ParamType.FLOAT)
                            cls.builder.SINGLESTEP(0.01)
                            # builder.REQUIRED(True)
                            cls.builder.DEFAULTVALUE(ConfigParams.fork_max_speed)

                    add_weight_input(cls.builder)

                    # 电机点动/长按操作
                    with cls.builder.CHILD(key="lift", name=_TR("Lift Motor"), desc=_TR("Lift motor jog or move")):
                        cls.builder.TYPE(ParamType.ARRAY)
                        with cls.builder.CHILDREN():
                            with cls.builder.CHILD(key="jogStep", name=_TR("Jog Step"), desc=_TR("Jog step for lift motor")):
                                cls.builder.TYPE(ParamType.FLOAT)
                                cls.builder.UNIT("m")
                                cls.builder.SINGLESTEP(0.01)
                                cls.builder.DEFAULTVALUE(0.1)
                            with cls.builder.CHILD(key="position", name=_TR("Position"),
                                                   desc=_TR("Target position for lift motor")):
                                cls.builder.TYPE(ParamType.FLOAT)
                                cls.builder.UNIT("m")
                                cls.builder.SINGLESTEP(0.01)
                                cls.builder.DEFAULTVALUE(-1)

                    if ConfigParams.shiftMotor:
                        with cls.builder.CHILD(key="shift", name=_TR("Shift Motor"), desc=_TR("Shift motor jog or move")):
                            cls.builder.TYPE(ParamType.ARRAY)
                            with cls.builder.CHILDREN():
                                with cls.builder.CHILD(key="jogStep", name=_TR("Jog Step"), desc=_TR("Jog step for shift motor")):
                                    cls.builder.TYPE(ParamType.FLOAT)
                                    cls.builder.UNIT("m")
                                    cls.builder.SINGLESTEP(0.01)
                                    cls.builder.DEFAULTVALUE(0.1)
                                with cls.builder.CHILD(key="position", name=_TR("Position"),
                                                       desc=_TR("Target position for shift motor")):
                                    cls.builder.TYPE(ParamType.FLOAT)
                                    cls.builder.UNIT("m")
                                    cls.builder.SINGLESTEP(0.01)
                                    cls.builder.DEFAULTVALUE(-1)

                    if ConfigParams.pitch_motor_name:
                        with cls.builder.CHILD(key="pitch", name=_TR("Pitch Motor"), desc=_TR("Pitch motor jog or move")):
                            cls.builder.TYPE(ParamType.ARRAY)
                            with cls.builder.CHILDREN():
                                with cls.builder.CHILD(key="jogStep", name=_TR("Jog Step"), desc=_TR("Jog step for pitch motor")):
                                    cls.builder.TYPE(ParamType.FLOAT)
                                    cls.builder.UNIT("m")
                                    cls.builder.SINGLESTEP(0.01)
                                    cls.builder.DEFAULTVALUE(0.1)
                                with cls.builder.CHILD(key="position", name=_TR("Position"),
                                                       desc=_TR("Target position for pitch motor")):
                                    cls.builder.TYPE(ParamType.FLOAT)
                                    cls.builder.UNIT("m")
                                    cls.builder.SINGLESTEP(0.01)
                                    cls.builder.DEFAULTVALUE(-1)

                    if ConfigParams.reach_motor_name:
                        with cls.builder.CHILD(key="reach", name=_TR("Reach Motor"), desc=_TR("Reach motor jog or move")):
                            cls.builder.TYPE(ParamType.ARRAY)
                            with cls.builder.CHILDREN():
                                with cls.builder.CHILD(key="jogStep", name=_TR("Jog Step"), desc=_TR("Jog step for reach motor")):
                                    cls.builder.TYPE(ParamType.FLOAT)
                                    cls.builder.UNIT("m")
                                    cls.builder.SINGLESTEP(0.01)
                                    cls.builder.DEFAULTVALUE(0.1)
                                with cls.builder.CHILD(key="position", name=_TR("Position"),
                                                       desc=_TR("Target position for reach motor")):
                                    cls.builder.TYPE(ParamType.FLOAT)
                                    cls.builder.UNIT("m")
                                    cls.builder.SINGLESTEP(0.01)
                                    cls.builder.DEFAULTVALUE(-1)

                    if ConfigParams.expand_motor_name:
                        if len(ConfigParams.expand_motor_items) <= 1:
                            with cls.builder.CHILD(key="expand", name=_TR("Expand Motor"), desc=_TR("Expand motor jog or move")):
                                cls.builder.TYPE(ParamType.ARRAY)
                                with cls.builder.CHILDREN():
                                    with cls.builder.CHILD(key="jogStep", name=_TR("Jog Step"),
                                                           desc=_TR("Jog step for expand motor")):
                                        cls.builder.TYPE(ParamType.FLOAT)
                                        cls.builder.UNIT("m")
                                        cls.builder.SINGLESTEP(0.01)
                                        cls.builder.DEFAULTVALUE(0.1)
                                    with cls.builder.CHILD(key="position", name=_TR("Position"),
                                                           desc=_TR("Target position for expand motor")):
                                        cls.builder.TYPE(ParamType.FLOAT)
                                        cls.builder.UNIT("m")
                                        cls.builder.SINGLESTEP(0.01)
                                        cls.builder.DEFAULTVALUE(-1)

                    # 脱离库位操作
                    with cls.builder.CHILD(key="leaveLoc", name=_TR("Leave Loc"),
                                           desc=_TR("Leave loc after load")):
                        cls.builder.TYPE(ParamType.ARRAY)

                        with cls.builder.CHILDREN():
                            create_end_height_param(cls.builder, min_height, max_height)

                    cls.extend_operation_inputs(cls.builder, min_height, max_height)
                    cls.extend_custom_operation_inputs(cls.builder, min_height, max_height)

                    if ConfigParams.scriptDebug:
                        with cls.builder.CHILD(key="rec", name=_TR("Rec"), desc=_TR("Recognize the pallet")):
                            cls.builder.TYPE(ParamType.ARRAY)

                            with cls.builder.CHILD(key="recfile", name=_TR("Recognition File Name"),
                                                   desc=_TR("Recognition file name")):
                                cls.builder.TYPE(ParamType.STRING)
                                cls.builder.DEFAULTVALUE("default.srec")

                        with cls.builder.CHILD(key="deleteClearRegion", name=_TR("Delete Clear Region"),
                                               desc=_TR("Delete Clear Region")):
                            cls.builder.TYPE(ParamType.ARRAY)

                        with cls.builder.CHILD(key="test", name=_TR("Test"),
                                               desc=_TR("Test operation")):
                            cls.builder.TYPE(ParamType.ARRAY)

                            with cls.builder.CHILDREN():
                                create_start_height_param(cls.builder, min_height, max_height)
                                create_end_height_param(cls.builder, min_height, max_height)
                                create_rec_param(cls.builder, cls.extend_recognize_on_params)

            if ConfigParams.scriptDebug:
                with cls.builder.CHILD(key="targetName", name=_TR("Target Name"), desc=_TR("Target ID Name")):
                    cls.builder.TYPE(ParamType.STRING)
                    cls.builder.DEFAULTVALUE("AP1")

            cls.extend_root_inputs(cls.builder)

        cls.builder.save_to_file()


def _init_action_templates():
    loader = _require_param_loader()

    def add_template(action_name, operation, *, stage=None):
        kwargs = {
            "action_name": action_name,
            "policy": {},
            "args": {"operation": operation},
            "config": {},
        }
        if stage is not None:
            kwargs["stage"] = stage
        loader.addAction(**kwargs)

    add_template(_TR("Fork Load"), "load", stage=3)
    add_template(_TR("Fork UnLoad"), "unload", stage=3)
    add_template(_TR("Fork Height"), "forkHeight")
    add_template(_TR("Goods Weight"), "weightGood")
    add_template(_TR("Leave Loc"), "leaveLoc", stage=3)
    for template in _collect_custom_action_templates():
        add_template(**template)

    loader.saveAction()


def _collect_custom_action_templates():
    templates = _run_script_hook("custom_action_templates_hook")
    if templates is None:
        return []
    return list(templates)


def _initialize_fork_script(
        script_file: str,
        *,
        config_builder_hook=None,
        config_reload_hook=None,
        rec_input_params_hook=None,
        operation_input_hook=None,
        root_input_hook=None,
        custom_operation_inputs_hook=None,
        custom_action_templates_hook=None,
        period_run_hook=None,
):
    global param_loader, ACTIVE_SCRIPT_FILE
    ACTIVE_SCRIPT_FILE = script_file
    SCRIPT_OPTIONS["config_builder_hook"] = config_builder_hook
    SCRIPT_OPTIONS["config_reload_hook"] = config_reload_hook
    SCRIPT_OPTIONS["rec_input_params_hook"] = rec_input_params_hook
    SCRIPT_OPTIONS["operation_input_hook"] = operation_input_hook
    SCRIPT_OPTIONS["root_input_hook"] = root_input_hook
    SCRIPT_OPTIONS["custom_operation_inputs_hook"] = custom_operation_inputs_hook
    SCRIPT_OPTIONS["custom_action_templates_hook"] = custom_action_templates_hook
    SCRIPT_OPTIONS["period_run_hook"] = period_run_hook
    param_loader = ScriptParam(script_file, callback=_script_config_callback)
    ConfigParams.init()
    bind_fork_utils_runtime(ConfigParams)
    InputParams.init(script_file)
    _init_action_templates()


class Fork(ModuleBase): #todo: 各种_build_*_actions 缺乏层级关系，不方便维护和查找
    fork_count_enabled = False
    config_builder_hook = None
    config_reload_hook = None
    rec_input_params_hook = None
    operation_input_hook = None
    root_input_hook = None
    custom_operation_inputs_hook = None
    custom_action_templates_hook = None
    period_run_hook = None
    # 车型专属叉车电机动作类；None 表示使用基类通用实现（ReachAwareForkMotorByPosition）。
    # 车型脚本在子类上重写此属性即可注册，无需改动 fork.py / fork_utils.py。
    fork_motor_action_class = None
    # lift 电机点动支持；默认支持，车型子类声明 False 即可关闭（如 liftFork / pickFork）
    lift_jog_support = True
    # 识别高度 seam：普通车型相机随货叉移动，默认不开启；车型可只重写这两个声明。
    recognition_height_default = False
    camera_moves_with_fork = True
    supports_cam_lift_with_fork = False
    cam_lift_with_fork_default = False
    adaptive_pallet_stack_unstack_default = False
    falling_down_detect_default = False
    supports_reach_motor = False
    # Ordinary fork types approach at the current fork height when startHeight
    # is omitted. Reach/softbag types require an explicit startHeight instead.
    use_current_height_when_start_omitted = True
    requires_explicit_start_height = False
    lift_fork_model_limits = False
    # PickFork overrides this to apply its recognition-file collision model
    # during the initial load approach only.
    use_recfile_collision_policy = False
    task_trace_channel = f"{MOD}.task"
    motor_trace_channel = f"{MOD}.motor"
    script_trace_channel = f"{MOD}.script"

    @classmethod
    def _resolve_runtime_init_options(
            cls,
            *,
            config_builder_hook=None,
            config_reload_hook=None,
            rec_input_params_hook=None,
            operation_input_hook=None,
            root_input_hook=None,
            custom_operation_inputs_hook=None,
            custom_action_templates_hook=None,
            period_run_hook=None,
    ):
        return {
            "config_builder_hook": (
                getattr(cls, "config_builder_hook", None)
                if config_builder_hook is None
                else config_builder_hook
            ),
            "config_reload_hook": (
                getattr(cls, "config_reload_hook", None)
                if config_reload_hook is None
                else config_reload_hook
            ),
            "rec_input_params_hook": (
                getattr(cls, "rec_input_params_hook", None)
                if rec_input_params_hook is None
                else rec_input_params_hook
            ),
            "operation_input_hook": (
                getattr(cls, "operation_input_hook", None)
                if operation_input_hook is None
                else operation_input_hook
            ),
            "root_input_hook": (
                getattr(cls, "root_input_hook", None)
                if root_input_hook is None
                else root_input_hook
            ),
            "custom_operation_inputs_hook": (
                (
                    getattr(cls, "custom_operation_inputs_hook", None)
                    or getattr(cls, "extend_custom_operation_inputs", None)
                )
                if custom_operation_inputs_hook is None
                else custom_operation_inputs_hook
            ),
            "custom_action_templates_hook": (
                (
                    getattr(cls, "custom_action_templates_hook", None)
                    or getattr(cls, "custom_action_templates", None)
                )
                if custom_action_templates_hook is None
                else custom_action_templates_hook
            ),
            "period_run_hook": (
                getattr(cls, "period_run_hook", None)
                if period_run_hook is None
                else period_run_hook
            ),
        }

    def __init__(
            self,
            script_file: str,
            *,
            rec_check_qr: bool = False,
            config_builder_hook=None,
            config_reload_hook=None,
            rec_input_params_hook=None,
            operation_input_hook=None,
            root_input_hook=None,
            custom_operation_inputs_hook=None,
            custom_action_templates_hook=None,
            period_run_hook=None,
    ):
        # 在配置加载（ConfigParams.init）之前注入当前车型子类，供 get_device_model_param /
        # _build_module_motor 等配置阶段钩子读取，避免按 module_type 硬编码分支。
        ConfigParams.active_fork_class = type(self)
        ConfigParams.fork_motor_action_class = type(self).fork_motor_action_class
        if type(self).fork_count_enabled:
            _init_fork_count()
        runtime_options = self._resolve_runtime_init_options(
            config_builder_hook=config_builder_hook,
            config_reload_hook=config_reload_hook,
            rec_input_params_hook=rec_input_params_hook,
            operation_input_hook=operation_input_hook,
            root_input_hook=root_input_hook,
            custom_operation_inputs_hook=custom_operation_inputs_hook,
            custom_action_templates_hook=custom_action_templates_hook,
            period_run_hook=period_run_hook,
        )
        _initialize_fork_script(
            script_file,
            **runtime_options,
        )
        super().__init__()
        self.script_file = script_file
        self.rec_check_qr = rec_check_qr
        self.script_status = ScriptStatus.NONE
        self.action_task = ForkActionQueue(mod=MOD, on_change=self._sync_action_runtime) # todo: 优化Action_Task 串行并行实现
        self.suspended_at = None
        self._op_flow = OperationFlow(self._set_actions)  # 生成器式 operation 驱动器
        self._init_geometry_cache()
        self._init_runtime_cache()
        self._init_mileage_state()
        Container.initContainer(0)
        self.reset_task_state()

        # 周期循环日志守卫状态
        self._last_fork_moving_state = None  # 记录上次 fork_is_moving 状态，变化时才打 log
        self.set_fork_region_by_height = False
        self.clear_fork_region_by_height = False

    def _init_geometry_cache(self):
        self.name_left = "back_laser_clear_left"  # 未被读；delete_clear_region 只删 region+right、漏删 left，疑似 bug，暂只保留标注
        self.name_right = "back_laser_clear_right"  # delete_clear_region 读
        self.back_laser_clear_region_name = "back_laser_clear_region"  # delete_clear_region 读
        self.chassis_clear_region = "chassis_clear_region"  # 全仓无读取点，待确认用途，暂保留

    def _init_runtime_cache(self):
        self.fork_height = 0.0
        self.carrier_length = 0
        self.carrier_width = 0
        self.carrier_height = 0
        self.pallet_deduct_infos = None
        self.carrier_shape = []
        self.pallet_width = None
        self.recognized_pallet_world_pos = None
        self.target_pos = [0, 0, 0, -1]
        self.hasReachDi = None
        self.fork_cur_height = None
        self._nav_fork_height_action = None
        self._nav_fork_height_task_id = ""
        self._skip_next_nav_fork_height = False
        self._nav_fork_height_read_error = False
        self._falling_down_detect_enabled = False

    def _init_mileage_state(self):
        run_db = _get_run_db() if not type(self).fork_count_enabled else None
        self.mileage_total_key = "forkMileage"
        self.mileage_up_key = "forkMileageUp"
        self.mileage_down_key = "forkMileageDown"
        self.key_today_total_mileage = "forkMileageToday"
        self.key_today_up_mileage = "forkMileageUpToday"
        self.key_today_down_mileage = "forkMileageDownToday"
        self.key_today_date = "fork_mileage_today_date"

        self.mileage_enabled = not type(self).fork_count_enabled
        defaults = {
            self.mileage_total_key: 0.0,
            self.mileage_up_key: 0.0,
            self.mileage_down_key: 0.0,
            self.key_today_total_mileage: 0.0,
            self.key_today_up_mileage: 0.0,
            self.key_today_down_mileage: 0.0,
            self.key_today_date: "",
        }
        if self.mileage_enabled:
            for key, default in defaults.items():
                value_type = "str" if isinstance(default, str) else "float"
                if run_db.get(key, value_type) is None:
                    run_db.add(key, default, False)
            self.total_dist = run_db.get(self.mileage_total_key, "float") or 0.0
            self.up_dist = run_db.get(self.mileage_up_key, "float") or 0.0
            self.down_dist = run_db.get(self.mileage_down_key, "float") or 0.0
            self.today_total = run_db.get(self.key_today_total_mileage, "float") or 0.0
            self.today_up = run_db.get(self.key_today_up_mileage, "float") or 0.0
            self.today_down = run_db.get(self.key_today_down_mileage, "float") or 0.0
            self.today_date = run_db.get(self.key_today_date, "str") or ""
        else:
            self.total_dist = 0.0
            self.up_dist = 0.0
            self.down_dist = 0.0
            self.today_total = 0.0
            self.today_up = 0.0
            self.today_down = 0.0
            self.today_date = ""

        self.last_pos = None
        self.last_save_ts = time.time()
        self.save_interval = 5
        self.mileage_dirty = False
        self._reset_daily_mileage_if_needed()

    def _reset_daily_mileage_if_needed(self):
        if not self.mileage_enabled:
            return
        today = datetime.now().strftime("%Y-%m-%d")
        if self.today_date == today:
            return
        self.today_total = 0.0
        self.today_up = 0.0
        self.today_down = 0.0
        self.today_date = today
        run_db = _get_run_db()
        run_db.put(self.key_today_total_mileage, self.today_total)
        run_db.put(self.key_today_up_mileage, self.today_up)
        run_db.put(self.key_today_down_mileage, self.today_down)
        run_db.put(self.key_today_date, self.today_date)
        Trace.log(f"fork daily mileage reset: date={today}", name="fork.task")

    def _reset_extra_task_state(self):
        pass

    def _init_extra_args(self):
        pass

    def _reset_operation_runtime_state(self):
        self.opt = ""
        self.min_safe_height = 0.0 # 只有一两个operation在用
        self.leave_loc_height = -1
        self.rec_height = -1 # 只有有识别的operation用
        self.check_di = False

    def _init_task_runtime_state(self): # 放到各自的operation和action里
        self.move_task = {}
        self.recfile = ""
        self.rec_params = {}
        self.recognize = False
        self.rec_result = {}
        self.rec_sides = []
        self.rec_info = {}
        self.pallet_deduct_info = {}
        self.obstacle_polygon_by_rec = []
        self.back_dist = 0
        self.goPathArgs = None
        self.first_point = None
        self.second_path = None
        self.first_point_return = None
        self.second_path_return = None

    def custom_operations(self):
        return {}

    def custom_cleanup_operations(self):
        return set()

    def _sync_action_runtime(self):
        self.action_status = self.action_task.status
        self.current_action = self.action_task.current_action
        self.action_id = self.action_task.current_index

    def _set_actions(self, actions):
        self.action_task.replace(actions)

    def _actions_done(self) -> bool:
        return self.action_task.is_finished

    # ------------------------------------------------------------------
    # 生成器式 operation 流程（通用机制，与车型无关）
    #
    # 驱动器本体见 fork_utils.OperationFlow（拉批 + 注入，职责单一）。这里只做与
    # Fork 任务态的对接：首 tick 创建生成器（_dispatch_operation）、每批跑完推进
    # （_finalize_operation_if_ready）、任务收尾/取消时关闭（reset_task_state）。
    #
    # 一个 operation handler 可写成生成器函数：每 `yield` 一批动作，队列跑完这批
    # （全部 FINISHED）后驱动器才 resume；`yield` 之后的代码只在该批结束后执行，
    # 故可就地读取刚结束动作的结果（生成器持有它构建的 action 引用），无需
    # on_finished / operation_init 标志。生成器耗尽即 operation 完成 -> 收尾 FINISHED。
    #
    # OperationFlow 未耦合任何 fork/车型逻辑，便于日后整体上移到任务生命周期层
    # （mixin / ModuleBase）——见 fork-refactor-spec §3.2 线 B。
    # ------------------------------------------------------------------
    def _close_op_flow(self):
        flow = getattr(self, "_op_flow", None)
        if flow is not None:
            flow.close()

    def _task_is_terminal(self) -> bool:
        return self.script_status in (ScriptStatus.FINISHED, ScriptStatus.FAILED)

    def set_status(self, new_status: ScriptStatus) -> None:
        if self.script_status == new_status:
            return
        prev_name = ScriptStatus(self.script_status).name
        next_name = ScriptStatus(new_status).name
        Trace.log(f"status {prev_name} -> {next_name}", name="fork.task")
        self.script_status = new_status

    def reset_task_state(self):
        self._close_op_flow()  # 关闭上一个任务未跑完的生成器（触发其 finally 清理）
        self.suspended_at = None
        self.init_args = False # todo: 在基类生命周期里处理
        self.operation_init = False # todo: 在基类生命周期里处理
        self.action_task.reset()
        self._sync_action_runtime()
        self.task_args = {}
        self.start_time = time.time()
        self.rec_pallet_handled = False #todo: 优化项
        self.rec_cage_handled = False
        self.cage_count = 0 # 单独的operation在用，可以作为operation内部参数
        self.start_loc = [] # 放到load unload是不是更好
        self.report_info = {}
        self._reset_operation_runtime_state()
        self.task_trace_payload = {
            "scriptStatus": int(self.script_status),
            "actionStatus": int(self.action_status),
            "actionIndex": int(self.action_id),
            "actionCount": int(self.action_task.total),
            "forkAutoFlag": False,
        }
        self.script_trace_payload = {
            "script.task_len": int(self.action_task.total),
            "script.action_id": int(self.action_id),
            "script.all_action_status": int(self.action_status),
            "script.cur_action": "",
            "script.cur_action_status": 0,
            "script.script_status": int(self.script_status),
        }
        self.motor_trace_payload = {
            "forkHeight": 0.0,
            "forkHeightInPlace": True,
            "forkMileage": float(self.total_dist),
            "forkMileageUp": float(self.up_dist),
            "forkMileageDown": float(self.down_dist),
            "minSafeHeight": 0.0,
        }
        self.fork_height_in_place = True
        self.deferred_leave_loc_actions = []
        self.recognition_readjust_count = 0
        self.load_recognition_pick_height = None
        self.pallet_width = None
        self.recognized_pallet_world_pos = None
        self._auto_pre_active = False
        self._reset_extra_task_state()
        self.set_status(ScriptStatus.NONE)

    def _poll_runtime_events(self, pending_input):
        if self.event_safe_move_check:
            self.safe_move_check()
        if self.event_modbus:
            pending_input = self.modbus()
        return pending_input

    def _get_input_params(self, pending_input):
        return pending_input or Module.getTaskArgs()

    def _validate_task_args(self, input_params, validator):
        if not input_params:
            return None
        Trace.log(f"check before, args:{input_params}", name="fork.task")
        try:
            validated_args = validator.validate(input_params)
        except ValueError as exc:
            Trace.log(f"check error:{exc}", name="fork.err")
            Navigation.setTaskError(
                "InvalidInputParams",
                f"invalid input params: {exc}",
            )
            self.set_status(ScriptStatus.FAILED)
            return None

        Trace.log(f"check ok, args:{json.dumps(validated_args, indent=2)}", name="fork.task")
        return validated_args

    def _start_task_cycle(self, args):
        self.set_status(ScriptStatus.RUNNING)
        self.action_task.reset()
        self._sync_action_runtime()
        self.init_args = True
        self.operation_init = False
        self.task_args = dict(args or {})
        NavStatus.clearBlock()
        self.min_safe_height = 0.0
        Trace.log(f"script args:{self.task_args}", name="fork.task")
        self._init_args()
        if self.script_status != ScriptStatus.RUNNING:
            return
        if not self._enable_falling_down_detect():
            return
        self._start_auto_pre_if_requested()

    def _start_auto_pre_if_requested(self):
        if not Module.getAutoPre():
            return
        if self.opt not in ("load", "unload"):
            Navigation.setTaskError(
                "autoPreNotSupported",
                f"auto-pre does not support operation:{self.opt}",
            )
            self.set_status(ScriptStatus.FAILED)
            return
        if self._task_stage() != TaskStage.SCRIPT_DRIVEN:
            Navigation.setTaskError(
                "autoPreNotSupported",
                f"fork auto-pre requires stage {int(TaskStage.SCRIPT_DRIVEN)}",
            )
            self.set_status(ScriptStatus.FAILED)
            return
        required_time = Motor.estimatePositionMoveDuration(
            key=ConfigParams.fork_motor_name,
            targetPos=self.start_height,
            startPos=None,
            startSpeed=None,
            maxSpeed=ConfigParams.fork_max_speed,
        )
        if required_time is None:
            Navigation.setTaskError(
                "autoPreDurationUnavailable",
                f"cannot estimate auto-pre duration for motor:{ConfigParams.fork_motor_name}",
            )
            self.set_status(ScriptStatus.FAILED)
            return
        pre_action = RunMotorByPosition(
            ConfigParams.fork_motor_name,
            self.start_height,
            ConfigParams.fork_max_speed,
        )
        self._set_actions([AutoPreSequenceAction(
            [pre_action],
            required_time=required_time,
            advance_time=ConfigParams.autoPreAdvanceTime,
            station="preStation",
            include_rotation=False,
            must_stop_at_pre_station=False,
        )])
        self._auto_pre_active = True

    def _finish_task_cycle(self):
        final_status = self.script_status
        self.save_mileage(force=True)
        delete_deduct_area("PalletRobotDeductArea", Coordinate.WORLD)
        delete_deduct_area("noRecDeduct2World", Coordinate.WORLD)
        Trace.log(f"script end, script_status: {final_status}", name="fork.task")
        self._disable_falling_down_detect()
        Module.setStatus(final_status)
        self.reset_task_state()

    def _dispatch_operation(self):
        if self._is_motor_operation(self.opt):
            self.motor_jog_or_move(self.opt)
            return
        if self.script_status != ScriptStatus.RUNNING:
            return

        handler_map = {
            "load": self.load,
            "unload": self.unload,
            "forkHeight": self.fork_move,
            "weightGood": self.weight_good,
            "rec": self.rec,
            "leaveLoc": self.leave_loc,
            "test": self.test,
            "deleteClearRegion": self.delete_clear_region,
        }
        custom_handler_map = self.custom_operations() or {}
        handler = custom_handler_map.get(self.opt, handler_map.get(self.opt))

        if handler is None:
            Navigation.setTaskError("WrongOperation", f"wrong operation:{self.opt}, script failed")
            self.set_status(ScriptStatus.FAILED)
            return
        if inspect.isgeneratorfunction(handler):
            # 生成器式 operation：首 tick 创建并注入第一批，之后由 _op_flow.advance 驱动。
            # operation_init 复用为"已创建"守卫，避免每 tick 重建生成器。
            if not self.operation_init:
                self.operation_init = True
                self._op_flow.start(handler())
            return
        handler()

    def _finalize_operation_if_ready(self):
        if self.script_status != ScriptStatus.RUNNING:
            return
        if self.opt == "deleteClearRegion":
            self.set_status(ScriptStatus.FINISHED)
            return
        if self._op_flow.active:
            # 生成器活跃：当前批跑完才推进下一批；未耗尽则继续，不收尾。
            if not self._actions_done():
                return
            advanced = self._op_flow.advance()
            if self.script_status != ScriptStatus.RUNNING:  # 推进途中生成器可能置 FAILED
                return
            if advanced:
                return
            # 生成器耗尽 -> 落到收尾
        elif not self._op_flow.done:
            # 经典 operation（on_finished / operation_init）：动作全部结束才收尾
            if not self._actions_done():
                return
        # else: 生成器已耗尽（含首批即结束 / 无 yield）-> 直接收尾，不看队列
        if self.opt == "forkHeight":
            self.fork_height_in_place = True
        # The final sample completes the action during _execute_actions().
        # Capture its result before the terminal task cycle clears report_info.
        if self.opt == "weightGood":
            self.weight_good()
        cleanup_operations = {"unload"} | set(self.custom_cleanup_operations() or set())
        if self.opt in cleanup_operations:
            delete_deduct_area(["no_rec_deduct_pallet_area", "PalletRobotRegionByHeight"], Coordinate.ROBOT)
        if self.opt != "deleteClearRegion":
            self._skip_next_nav_fork_height = True
        self.set_status(ScriptStatus.FINISHED)

    @staticmethod
    def _is_plain_navigation_task(move_task):
        return (
            isinstance(move_task, dict)
            and bool(move_task.get("taskId"))
            and move_task.get("skillName") != "Action"
        )

    @staticmethod
    def _nav_fork_height_target():
        if Container.hasGoods("0"):
            if not (ConfigParams.enableLoadNavForkHeight and ConfigParams.allowLoadForkMoveWhileNav):
                return None
            return ConfigParams.loadNavForkHeight
        if not (ConfigParams.enableNavForkHeight and ConfigParams.allowForkMoveWhileNav):
            return None
        return ConfigParams.navForkHeight

    def _cancel_nav_fork_height_action(self):
        if self._nav_fork_height_action is not None:
            self._nav_fork_height_action.cancel()
            self._nav_fork_height_action = None
        self.fork_height_in_place = True

    @staticmethod
    def _nav_fork_height_enabled():
        return (
            (ConfigParams.enableNavForkHeight and ConfigParams.allowForkMoveWhileNav)
            or (ConfigParams.enableLoadNavForkHeight and ConfigParams.allowLoadForkMoveWhileNav)
        )

    def _run_nav_fork_height(self, module_status):
        """Move the fork to its configured travel height during a plain 3066 navigation."""
        if module_status in (ScriptStatus.RUNNING, ScriptStatus.NEARTOGOAL, ScriptStatus.SUSPENDED):
            self._cancel_nav_fork_height_action()
            return

        if not self._nav_fork_height_enabled():
            self._cancel_nav_fork_height_action()
            return

        try:
            move_task = Navigation.realTimeMoveTask() or {}
            self._nav_fork_height_read_error = False
        except Exception as exc:
            self._cancel_nav_fork_height_action()
            if not self._nav_fork_height_read_error:
                Trace.log(f"read navigation task for fork travel height failed: {exc}", name="fork.err")
                self._nav_fork_height_read_error = True
            return

        if not self._is_plain_navigation_task(move_task):
            self._cancel_nav_fork_height_action()
            self._nav_fork_height_task_id = ""
            return

        task_id = str(move_task["taskId"])
        if task_id != self._nav_fork_height_task_id:
            self._cancel_nav_fork_height_action()
            self._nav_fork_height_task_id = task_id
            if self._skip_next_nav_fork_height:
                self._skip_next_nav_fork_height = False
                Trace.log(
                    f"skip fork travel height on first navigation after script action, task_id={task_id}",
                    name="fork.task",
                )
                return

            target = self._nav_fork_height_target()
            if target is None:
                return
            current = Motor.getMotorPos(ConfigParams.fork_motor_name)
            if abs(current - target) <= 0.02:
                Trace.log(
                    f"fork travel height already in place, current={current}, target={target}, task_id={task_id}",
                    name="fork.task",
                )
                return
            self.fork_height_in_place = False
            self._nav_fork_height_action = RunMotorByPosition(
                ConfigParams.fork_motor_name,
                target,
                ConfigParams.fork_max_speed,
                action_name="NavForkHeight",
            )
            Trace.log(
                f"start fork travel height while navigating, current={current}, target={target}, task_id={task_id}",
                name="fork.task",
            )

        action = self._nav_fork_height_action
        if action is None:
            return
        action.run(self)
        if action.action_status == ActionStatus.FINISHED:
            Trace.log(f"fork travel height finished, task_id={task_id}", name="fork.task")
            self._nav_fork_height_action = None
            self.fork_height_in_place = True
        elif action.action_status == ActionStatus.FAILED:
            Trace.log(f"fork travel height failed, task_id={task_id}", name="fork.err")
            self._nav_fork_height_action = None
            self.fork_height_in_place = True

    def _run_task_cycle(self):
        if self.script_status != ScriptStatus.RUNNING:
            return
        self._check_timeout()
        if self.script_status != ScriptStatus.RUNNING:
            return
        if self._auto_pre_active:
            self._execute_actions()
            if self.action_status == ActionStatus.FAILED:
                self.set_status(ScriptStatus.FAILED)
            elif self._actions_done():
                self.action_task.reset()
                self._sync_action_runtime()
                self._auto_pre_active = False
                # AutoPre starts while an earlier navigation leg is active, so the
                # move-task snapshot captured in _init_args() may not yet contain
                # the formal leg's source/target stations.
                self.move_task = Navigation.moveTask()
            return
        self._dispatch_operation()
        if self.script_status != ScriptStatus.RUNNING:
            return
        if self.opt == "deleteClearRegion":
            self._finalize_operation_if_ready()
            return
        self._execute_actions()
        if self.action_status == ActionStatus.FAILED:
            self.set_status(ScriptStatus.FAILED)
            return
        self._finalize_operation_if_ready()

    def _tick_task_cycle(self, pending_input, validator):
        if self._task_is_terminal():
            self._finish_task_cycle()
            return None

        if self.script_status == ScriptStatus.NONE:
            args = self._validate_task_args(self._get_input_params(pending_input), validator)
            if args is None:
                if self._task_is_terminal():
                    self._finish_task_cycle()
                    return None
                return pending_input
            self._start_task_cycle(args)
            pending_input = None

        if self.script_status == ScriptStatus.RUNNING:
            self._run_task_cycle()

        if self._task_is_terminal():
            self._finish_task_cycle()
            return None

        return pending_input

    def main(self):
        RobotParam.setConfigChangeCallBack(_robot_config_change_callback)
        RobotParam.setDeviceChangeCallBack(_robot_device_change_callback)
        ScriptParam.setConfigChangeCallBack(_script_config_callback)
        if param_loader is not None:
            ScriptParam.file_callback[param_loader.script_file] = _script_config_callback
        Module.init(script_file=self.script_file)

        pending_input = None
        validator = ParamValidator(InputParams.builder.toDict())

        time.sleep(5)

        while True:
            pending_input = self._poll_runtime_events(pending_input)

            self.period_run()

            status = Module.getStatus()

            self._run_nav_fork_height(status)

            if ConfigParams.scriptDebug:
                pass

            if status == ScriptStatus.RUNNING:
                pending_input = self._tick_task_cycle(pending_input, validator)

            time.sleep(0.1)

    def run(self, args):
        if not self.init_args:
            self._start_task_cycle(args)
        self._run_task_cycle()

    def suspend(self):
        if self.script_status != ScriptStatus.RUNNING:
            return
        self.action_task.suspend()
        self._sync_action_runtime()
        self.suspended_at = time.time()
        self.set_status(ScriptStatus.SUSPENDED)
        Module.setStatus(ScriptStatus.SUSPENDED)
        Trace.log("suspend", name="fork.task")

    def resume(self):
        if self.script_status != ScriptStatus.SUSPENDED:
            return
        if self.suspended_at is not None and self.start_time is not None:
            self.start_time += time.time() - self.suspended_at
        self.suspended_at = None
        self.action_task.resume()
        self._sync_action_runtime()
        self.set_status(ScriptStatus.RUNNING)
        Module.setStatus(ScriptStatus.RUNNING)
        Trace.log("resume", name="fork.task")

    def cancel(self):
        was_suspended = Module.getStatus() == ScriptStatus.SUSPENDED
        self.set_status(ScriptStatus.FAILED)
        self.action_task.cancel()
        self._sync_action_runtime()
        self._disable_falling_down_detect()
        if was_suspended:
            Module.setStatus(ScriptStatus.RUNNING)
        Trace.log("cancel", name="fork.task")
        return

    def reset(self):
        self.start_time = time.time()
        self.suspended_at = None
        self.action_task.reset()
        self._sync_action_runtime()
        # Motor.resetMotor(ConfigParams.fork_motor_name)
        # Navigation.clearGoodsShape()

    def _enable_falling_down_detect(self):
        return enable_falling_down_detect(self)

    def _disable_falling_down_detect(self):
        disable_falling_down_detect(self)

    def bindContainer(self, container_id: str, goods_name: str, desc: str) -> bool:
        # 1. 绑定容器
        Container.bindContainer(container_id, goods_name, desc)
        # 2. 设置货物形状
        goods_shape = [{"x": 1.2 / 2, "y": 1.0 / 2},
                       {"x": 1.2 / 2, "y": -1.0 / 2},
                       {"x": -1.2 / 2, "y": -1.0 / 2},
                       {"x": -1.2 / 2, "y": 1.0 / 2}]
        if not goods_shape:
            return False
        goods_point2robot = []

        for point in goods_shape:
            point2ap = pos2World([point["x"], point["y"], 0],
                                 [ConfigParams.module_x - 1.2 / 2, 0, 0])
            goods_point2robot.append({"x": point2ap[0], "y": point2ap[1]})
        Navigation.setGoodsPolyShape(goods_point2robot, goods_name)
        return True

    def delete_clear_region(self):
        delete_deduct_area("PalletRobotDeductArea", Coordinate.WORLD)
        delete_deduct_area("noRecDeduct2World", Coordinate.WORLD)
        Navigation.deleteClearRegion(self.back_laser_clear_region_name, Coordinate.ROBOT)
        Navigation.deleteClearRegion(self.name_right, Coordinate.ROBOT)

    def modbus(self):
        # modbus解析器
        trigger_data = NetProtocol.getModbusData("4x", 200, 1)
        Trace.log(f"modbus trigger 4x[200]:{trigger_data}", name="fork.task")
        try:
            motor_registers = {
                203: "lift",
                204: "shift",
                205: "pitch",
                206: "reach",
            }
            for address, operation in motor_registers.items():
                signal_data = NetProtocol.getModbusData("4x", address, 1)
                signal = parseModbus(signal_data, "int16")
                Trace.log(
                    f"modbus motor 4x[{address}]:{signal_data}, signal:{signal}",
                    name="fork.task",
                )
                if signal not in (-2, -1, 1, 2):
                    continue

                if abs(signal) == 1:
                    return {
                        "operation": operation,
                        "jogStep": 0.1 if signal > 0 else -0.1,
                    }

                motors = [
                    motor for motor in ConfigParams.moduleMotor
                    if motor.get("type") == operation
                ]
                if not motors:
                    Trace.log(
                        f"modbus operation {operation} has no configured motor",
                        name="fork.err",
                    )
                    return {"operation": operation, "position": 0.0}

                if signal > 0:
                    position = min(float(motor["maxLength"]) for motor in motors)
                else:
                    position = max(float(motor["minLength"]) for motor in motors)
                return {"operation": operation, "position": position}

            modbus_data = NetProtocol.getModbusData("4x", 201, 2)
            data = parseModbus(modbus_data, "float")
            Trace.log(
                f"modbus target 4x[201:203]:{modbus_data}, parsed height:{data}",
                name="fork.task",
            )
            return {"operation": "forkHeight", "height": data}
        finally:
            self.event_modbus = False

    def safe_move_check(self):
        status = SafeMoveStatus.FINISHED
        self.setSafeMoveStatus(status)
        if ConfigParams.scriptDebug:
            Trace.log(f"safe_move_check {Module.getSafeMoveCheck()}", name="fork.task")
        if status == SafeMoveStatus.FAILED or status == SafeMoveStatus.FINISHED:
            self.event_safe_move_check = False

    def get_station_pos(self, station_type):
        pos = [0, 0, 0, -1]
        tcp_key = ""
        station_id = self.move_task.get(station_type, "")  # int, 可能是 LM，可能是 AP
        Trace.log(f"target id:{station_id}", name="fork.task")
        if station_id == "" and station_type == "targetName":
            # task_args 里已经是带前缀的字符串
            target_id_str = self.task_args.get("targetName", "")
            pos = Navigation.getLM(target_id_str, True)
            tcp_info = Navigation.getLmTcpInfo(target_id_str) or []
            tcp_key = next((tcp.get("key", "") for tcp in tcp_info if tcp.get("usage") == "move"), "")
            Trace.log(f"pos:{pos}, tcp key:{tcp_key}", name="fork.task")
        elif station_id != "":
            # 尝试 AP 和 LM 两个前缀

            pos = Navigation.getLM(station_id, True)
            tcp_info = Navigation.getLmTcpInfo(station_id) or []
            tcp_key = next((tcp.get("key", "") for tcp in tcp_info if tcp.get("usage") == "move"), "")
            if pos[3] != -1:  # 找到有效结果
                Trace.log(f"id_str:{station_id}, id:{station_id}, pos:{pos} tcp key:{tcp_key}", name="fork.task")
                return pos, tcp_key  # 优先返回成功的结果

            # 如果走到这里，说明 AP 和 LM 都失败了
            Trace.log(f"{station_id} not found, return {pos}", name="fork.err")
        return pos, tcp_key

    def _has_usable_target_pos(self, target_pos):
        """移动动作能否直接用这个目标点。

        原地任务（SELF_POSITION，stage=2）没有真实目标点：即便参数里带了
        AP/LM 名称解析出了坐标，也不允许据此下发路径，否则会在原地动作任务里
        把车开走。
        """
        return has_valid_target_pos(target_pos) and not self._is_in_place_task()

    def _task_stage(self):
        """当前 TASK 的调度阶段；缺省用平台默认值。"""
        try:
            return TaskStage(Module.getTaskParams("stage", DEFAULT_TASK_STAGE))
        except ValueError:
            return DEFAULT_TASK_STAGE

    def _is_in_place_task(self):
        """原地动作任务：MF 用 SELF_POSITION 的 move task 下发的脚本任务。

        只看 move task 标记（taskId/sourceId/id）。注意 ``stage`` 不能用来判定
        这件事：stage 的语义是“前置点停不停 / 谁控制导航”（见 TaskStage），
        与原地任务无关，默认值 2 也不是原地任务的标志。

        原地任务并不等于“不需要 startHeight”：原地识别取货仍要先走到
        startHeight，部分前移车型也需要原地先到位再伸叉，因此这里只用来阻断
        路径动作，不参与参数校验。
        """
        move_task = self.move_task or {}
        markers = (move_task.get("taskId"), move_task.get("sourceId"), move_task.get("id"))
        return any(str(marker or "") == SELF_POSITION_MARKER for marker in markers)

    def _target_name(self):
        target_name = self.move_task.get("targetName", "")
        if target_name != "":
            return target_name
        return self.task_args.get("targetName", "")

    def _build_loc_detect_action(self, expect_goods):
        if not ConfigParams.locDetect3d:
            return None
        return LocDetectGoods(self._target_name(), expect_goods)

    def _resolve_motor_info(self, motor_type):
        base_type, side = normalize_motor_operation(motor_type)
        candidates = [
            motor for motor in ConfigParams.moduleMotor
            if motor.get("type") == base_type and (not side or motor.get("side") == side)
        ]
        if not candidates:
            return None
        if len(candidates) > 1 and not side:
            Navigation.setTaskError("motorTypeError",
                                    f"motor type {motor_type} is ambiguous, check moduleMotor config")
            self.set_status(ScriptStatus.FAILED)
            return None
        return candidates[0]

    def _is_motor_operation(self, motor_type):
        if motor_type == "reach" and len(ConfigParams.reach_motor_names) > 1:
            return True
        return self._resolve_motor_info(motor_type) is not None

    def _init_start_loc_from_source(self, r_loc, *, log_name="fork.task"):
        source_pos = self.get_station_pos("sourceName")[0]
        Trace.log(f"source_pos:{source_pos},recfile:{self.recfile}", name=log_name)
        self.start_loc = r_loc if source_pos[3] == -1 else source_pos
        return source_pos

    def _build_leave_loc_followup_actions(self, allow_same_path_return=False):
        leave_loc = getattr(self, "leave_loc", self.leave_loc_height >= 0)
        if not leave_loc or self.leave_loc_height < 0:
            return []

        args = {
            "x": self.start_loc[0],
            "y": self.start_loc[1],
            "theta": self.start_loc[2],
            "coordinate": "world",
            "backMode": 0,
            "maxRot": 10,
            "maxSpeed": 0.2,
            "useOdo": 0,
            "reachAngle": math.radians(0.5),
            "reachDist": 0.005,
        }
        return [
            build_return_path_action(args, allow_same_path_return=allow_same_path_return),
            RunMotorByPosition(ConfigParams.fork_motor_name, self.leave_loc_height),
        ]

    def _build_load_transport_lift_action(self):
        # 顶升到目标高度。生成器在进叉批跑完后才构建本动作，故 end_height / _get_load_end_height
        # 读到的是"进叉后"的真实货叉高度（softbag 靠此读 Motor.getMotorPos）。
        return RunMotorByPosition(
            ConfigParams.fork_motor_name,
            self.end_height,
            ConfigParams.fork_max_speed,
            "upFork",
        )

    def _build_height_probe_action(self, probe_height: float, expect_present: bool,
                                   error_code: str, error_msg: str, action_name: str):
        return []

    def _build_load_guard_actions(self):
        return []

    def _build_unload_guard_actions(self):
        return []

    def _build_start_height_actions(self, action=None, action_name=None):
        if self._skip_next_start_height_action:
            self._skip_next_start_height_action = False
            return []
        # An omitted startHeight means "keep the current fork height".  This
        # preserves endHeight-only and in-place action behavior.
        if not self.start_height_provided and type(self).use_current_height_when_start_omitted:
            return []
        if action is None:
            action = RunMotorByPosition(ConfigParams.fork_motor_name, self.start_height, action_name=action_name)
        return [action]

    def _build_load_no_rec_approach_batch(self, target_pos, tcp_name):
        # 盲叉进叉批（不含顶升）：到起始高度 -> 进叉到目标点。self.check_di 由 load() 预先设好。
        actions = self._build_start_height_actions()
        resolved_target_pos = target_pos
        if tcp_name:
            resolved_target_pos = apply_tcp_target(target_pos, tcp_name)
            method, args = build_path_adjust_plan(
                back_dist=0,
                min_ahead_dist=ConfigParams.tail + ConfigParams.module_x,
                adjust_dist=ConfigParams.aheadDist,
            )
        else:
            method = "goPath"
            args = {}
        actions.append(
            GoPathWithContactDi(
                ConfigParams.contact_ids,
                resolved_target_pos,
                ConfigParams.loadObsStopDist,
                method,
                args,
                self.check_di,
                "load",
                recfile=self.recfile,
            )
        )
        return actions

    def _create_load_recognition_action(self, rec_center2robot):
        return Rec(self.recfile, rec_center2robot[0], rec_center2robot[1], ConfigParams.recRadius)

    def _build_load_entry_batch(self, rec_action):
        # 识别进入批：到起始高度 -> 识别 -> 到识别高度。
        actions = self._build_start_height_actions()
        actions.append(rec_action)
        if self.rec_height >= 0:
            actions.append(RunMotorByPosition(ConfigParams.fork_motor_name, self.rec_height))
        return actions

    def _resolve_load_recognition_pose(self, rec_action):
        return resolve_load_recognition_pose(rec_action)

    def _prepare_load_recognition_height(self, rec_action):
        self.load_recognition_pick_height = None
        if not ConfigParams.adjustHeight:
            return True

        recognition_z = extract_recognition_height_z(rec_action)
        if recognition_z is None:
            Navigation.setTaskError("RecHeightMissing", "recognition height z is missing")
            self.set_status(ScriptStatus.FAILED)
            return False

        fork_height_at_recognition = getattr(rec_action, "fork_height_at_recognition", None)
        if not self.camera_moves_with_fork and (
                fork_height_at_recognition is None or float(fork_height_at_recognition) < 0
        ):
            Navigation.setTaskError(
                "RecForkHeightMissing",
                "fork height at recognition is unavailable for fixed camera",
            )
            self.set_status(ScriptStatus.FAILED)
            return False
        rec_info = getattr(self, "rec_info", None)
        rec_side = rec_info.get("side_value") if isinstance(rec_info, dict) else getattr(self, "recSide", None)
        z_offset = load_pallet_z_offset(self.recfile, rec_side)
        raw_pick_height = calculate_recognition_pick_height(
            recognition_z,
            z_offset,
            camera_moves_with_fork=self.camera_moves_with_fork,
            fork_height_at_recognition=fork_height_at_recognition,
            camera_calibration_fork_height=ConfigParams._safe_float(
                getattr(ConfigParams, "camCalibMotorHeight", 0.0),
                0.0,
            ),
        )
        self.load_recognition_pick_height = clamp(
            raw_pick_height,
            ConfigParams.min_height,
            ConfigParams.max_height,
        )
        Trace.log(
            f"recognition pick height:{self.load_recognition_pick_height}, raw:{raw_pick_height}, "
            f"rec_z:{recognition_z}, zOffset:{z_offset}, "
            f"forkHeightAtRec:{fork_height_at_recognition}, cameraMovesWithFork:{self.camera_moves_with_fork}",
            name="fork.task",
        )
        return True

    def _resolve_validated_recognition(self, rec_action, *, check_tilt):
        resolved = self._resolve_load_recognition_pose(rec_action)
        _, rec_result_dict, rec_world_pos, rec_robot_pos = resolved
        self.recognized_pallet_world_pos = list(rec_world_pos)
        self.obstacle_polygon_by_rec = rec_action.obstacle_polygon
        Trace.log(
            f"rec_world_pos:{rec_world_pos}, robotResult:{rec_robot_pos}",
            output_console=True,
            output_time=True,
            name="fork.task",
        )
        if check_tilt and not validate_recognition_tilt(self, rec_result_dict):
            return None
        rec_world_pos = apply_tcp_target(
            rec_world_pos,
            "move/defaultTcp",
            enabled=ConfigParams.enableTcp,
            log_name="fork.task",
        )
        if not validate_recognition_result_against_target(self, rec_world_pos):
            return None
        return rec_action, rec_result_dict, rec_world_pos, rec_robot_pos

    def _build_recognition_readjust_move_action(self, rec_world_pos):
        target_pos = build_recognition_readjust_target(rec_world_pos, ConfigParams.minAheadDist)
        return GoPathWithContactDi(
            ConfigParams.contact_ids,
            target_pos,
            ConfigParams.loadObsStopDist,
            "goPath",
            {},
            False,
            "load",
            recfile=self.recfile,
        )

    def _resolve_recognition_approach_plan(self, rec_world_pos, back_dist, method, args):
        if self.recognition_readjust_count == 0:
            return rec_world_pos, method, args

        # 二次识别已将车体对齐并停在目标前置位；最终进叉只需沿目标轴线直达。
        # GoPathWithContactDi 在启用到位 DI 时还会继续叠加 forkDiDist。
        straight_target = pos2World([-back_dist, 0.0, 0.0], rec_world_pos)
        return straight_target, "goPath", {}

    def _run_recognition_readjust(self, rec_action, create_recognition_action, *, check_tilt):
        """识别结果未收敛时移动到目标前置位复识别；返回最终识别结果元组。"""
        resolved = self._resolve_validated_recognition(rec_action, check_tilt=check_tilt)
        if resolved is None or not ConfigParams.readjust:
            return resolved

        last_error = (0.0, 0.0)
        while self.recognition_readjust_count < ConfigParams.readjustMaxTimes:
            _, _, rec_world_pos, rec_robot_pos = resolved
            self.recognition_readjust_count += 1
            yield [self._build_recognition_readjust_move_action(rec_world_pos)]

            current_loc = get_r_loc()
            if self._has_usable_target_pos(self.target_pos):
                rec_center2robot = resolve_rec_center_to_robot(self.target_pos, current_loc)
            else:
                rec_center2robot = [ConfigParams.recCenterX, ConfigParams.recCenterY]
            rec_action = create_recognition_action(rec_center2robot)
            yield [rec_action]
            resolved = self._resolve_validated_recognition(rec_action, check_tilt=check_tilt)
            if resolved is None:
                return None

            _, _, _, rec_robot_pos = resolved
            converged, lateral_error, angle_error_deg = evaluate_recognition_readjust(
                rec_robot_pos,
                ConfigParams.readjustDistPrecision,
                ConfigParams.readjustAnglePrecision,
            )
            last_error = lateral_error, angle_error_deg
            Trace.log(
                f"recognition readjust count:{self.recognition_readjust_count}, "
                f"lateral:{lateral_error}m, yaw:{angle_error_deg}deg, converged:{converged}",
                name="fork.task",
            )
            if converged:
                return resolved

        lateral_error, angle_error_deg = last_error
        Navigation.setTaskError(
            "RecAdjustExceeded",
            f"recognition readjust exceeded {ConfigParams.readjustMaxTimes} times, "
            f"lateral error:{lateral_error}m, yaw error:{angle_error_deg}deg",
        )
        self.set_status(ScriptStatus.FAILED)
        return None

    def _build_expand_motor_action(self, rec_action):
        return None

    def _build_load_approach_batch(self, rec_action, rec_world_pos, method, args):
        # 识别后进叉批（不含顶升）：伸缩电机（车型可选）-> 进叉到识别位姿。
        actions = []
        if self.load_recognition_pick_height is not None:
            actions.append(RunMotorByPosition(
                ConfigParams.fork_motor_name,
                self.load_recognition_pick_height,
                ConfigParams.fork_max_speed,
                "pickHeight",
            ))
        expand_action = self._build_expand_motor_action(rec_action)
        if expand_action is not None:
            actions.append(expand_action)
        actions.append(
            GoPathWithContactDi(
                ConfigParams.contact_ids,
                rec_world_pos,
                ConfigParams.loadObsStopDist,
                method,
                args,
                self.check_di,
                "load",
                recfile=self.recfile,
            )
        )
        return actions

    def _build_post_load_actions(self):
        return []

    def _build_leave_loc_operation_actions(self, target_pos):
        args = {
            "x": target_pos[0],
            "y": target_pos[1],
            "theta": target_pos[2],
            "coordinate": "world",
            "backMode": 0,
            "maxRot": 10,
            "maxSpeed": 0.2,
            "useOdo": 0,
        }
        return [
            build_return_path_action(args, allow_same_path_return=True),
            RunMotorByPosition(ConfigParams.fork_motor_name, self.end_height),
        ]

    def _build_unload_prepare_lift_action(self, target_height):
        return RunMotorByPosition(ConfigParams.fork_motor_name, target_height)

    def _build_unload_release_action(self):
        # 落叉释放。生成器在进叉批跑完后才 yield 本动作，释放完成的续接写在 unload() 尾部。
        return RunMotorByPosition(
            ConfigParams.fork_motor_name,
            self.end_height,
            action_name="downFork",
        )

    def _build_unload_no_target_prepare_batch(self):
        # 无目标点放货：落叉释放前的准备批（基类无，softbag 先抬到起始高度）。
        return []

    def _build_unload_target_approach(self, target_pos, tcp_name):
        # 有目标点放货进叉批（不含释放）：抬到起始高度 -> 进/退到放货点。
        resolved_target_pos = target_pos
        if tcp_name:
            resolved_target_pos = apply_tcp_target(target_pos, tcp_name)
        method, args = build_path_adjust_plan(
            back_dist=0,
            min_ahead_dist=ConfigParams.tail + ConfigParams.module_x - ConfigParams.base_shift_length,
            adjust_dist=ConfigParams.aheadDist,
            enabled=bool(tcp_name),
        )
        if ConfigParams.base_shift and (ConfigParams.max_height - self.fork_height) < EPS:
            resolved_target_pos = pos2World([-ConfigParams.base_shift_length, 0, 0], resolved_target_pos)

        actions = self._build_start_height_actions(self._build_unload_prepare_lift_action(self.start_height))
        actions.append(
            GoPathWithContactDi(
                ConfigParams.contact_ids,
                resolved_target_pos,
                None,
                method,
                args,
                False,
                "unload",
                recfile=self.recfile,
            )
        )
        return actions, bool(tcp_name)

    def _create_unload_recognition_action(self, rec_center2robot):
        # 卸货识别动作（基类 Rec；与取货识别动作 _create_load_recognition_action 独立，
        # 避免 softbag 只改取货识别却波及放货识别）。
        return Rec(self.recfile, rec_center2robot[0], rec_center2robot[1], ConfigParams.recRadius)

    def _build_unload_entry_batch(self, rec_action):
        # 卸货识别进入批：起始高度 -> 识别 -> 识别高度。
        actions = self._build_start_height_actions()
        actions.append(rec_action)
        if self.rec_height >= 0:
            actions.append(RunMotorByPosition(ConfigParams.fork_motor_name, self.rec_height))
        return actions

    def _build_unload_approach_batch(self, rec_action, rec_world_pos, method, args):
        # 卸货识别后进叉批（不含释放）：进/退到放货位姿。
        return [
            GoPathWithContactDi(
                ConfigParams.contact_ids,
                rec_world_pos,
                None,
                method,
                args,
                False,
                "unload",
                recfile=self.recfile,
            ),
        ]

    def _on_unload_actions_build(self):
        # 放货动作构建前的钩子（基类无；softbag 在此读后激光屏蔽状态）。
        pass

    def _build_post_unload_actions(self):
        return []

    def test(self):
        if not self.operation_init:
            # 实时识别的
            self.operation_init = True
            r_loc = get_r_loc()

            if not load_recognition_assets(self):
                return

            # 从任务参数 或者从 脚本任务参数里获取到AP点及其坐标
            self.target_pos, tcp_name = self.get_station_pos("targetName")

            if self._has_usable_target_pos(self.target_pos):
                rec_center2robot = resolve_rec_center_to_robot(self.target_pos, r_loc)
            else:
                rec_center2robot = [ConfigParams.recCenterX, ConfigParams.recCenterY]
            self.back_dist = resolve_back_dist(self.rec_info)

            self._set_actions([
                RunMotorByPosition(ConfigParams.fork_motor_name, self.start_height),
                GoLiveRec(self.recfile, back_dist=self.back_dist, rec_x=rec_center2robot[0], rec_y=rec_center2robot[1],
                          rec_radius=ConfigParams.recRadius),
                RunMotorByPosition(ConfigParams.fork_motor_name, self.end_height)])

    # 识别取货和非识别取货
    def load(self):
        # 生成器式取货：识别/盲叉 -> 进叉 -> 顶升 -> 收尾，全流程顶到底可读。
        # 每 yield 一批动作，队列跑完后 resume；yield 之后就地读刚结束动作的结果。
        if not validate_goods_state_for_operation(self, "load"):
            return
        apply_default_navigation_policy()
        r_loc = get_r_loc()
        self._init_start_loc_from_source(r_loc)
        if (self.recognize and self.check_di) or (not self.recognize and ConfigParams.enableContactDiNoRec):
            ConfigParams.checkGoodsWhileLoad = False
        if not load_recognition_assets(self, log_name=f"{MOD}.rec"):
            return

        # 从任务参数 或者从脚本任务参数里获取到 AP 点及其坐标；库位检测 ROI 依赖该点。
        self.target_pos, tcp_name = self.get_station_pos("targetName")
        load_guard = self._build_load_guard_actions()
        if self.script_status == ScriptStatus.FAILED:
            return
        if load_guard:
            yield load_guard
            self._skip_next_start_height_action = True

        loc_detect_action = self._build_loc_detect_action(expect_goods=True)
        if loc_detect_action is not None and (
                self.recognize or self._has_usable_target_pos(self.target_pos)
        ):
            yield [loc_detect_action]

        if not self.recognize:
            # 不需要根据识别结果通过盲走插货
            self.check_di = ConfigParams.enableContactDiNoRec
            if self._has_usable_target_pos(self.target_pos):
                if self.leave_loc_height >= 0:
                    self.deferred_leave_loc_actions = self._build_leave_loc_followup_actions()
                yield self._build_load_no_rec_approach_batch(self.target_pos, tcp_name)
        else:
            # 如果需要识别后再取货
            if not ensure_recfile(self):
                return
            if self._has_usable_target_pos(self.target_pos):
                rec_center2robot = resolve_rec_center_to_robot(self.target_pos, r_loc)
            else:
                rec_center2robot = [ConfigParams.recCenterX, ConfigParams.recCenterY]
            self.back_dist = resolve_back_dist(self.rec_info)
            rec_action = self._create_load_recognition_action(rec_center2robot)
            yield self._build_load_entry_batch(rec_action)

            # 识别完成，就地读结果并校验
            self.check_di = is_enabled(self.rec_info.get("enableCargoContactDI"))
            Trace.log(f"add task list {format_action(rec_action)},id {self.action_id}", output_console=True,
                      output_time=True, name="fork.task")
            resolved = yield from self._run_recognition_readjust(
                rec_action,
                self._create_load_recognition_action,
                check_tilt=True,
            )
            if resolved is None:
                return
            rec_action, rec_result_dict, rec_world_pos, rec_robot_pos = resolved
            if not self._prepare_load_recognition_height(rec_action):
                return
            Trace.log(f"carrier {self.carrier_shape, self.goods_shape, self.obstacle_polygon_by_rec}",
                      output_console=True, output_time=True, name="fork.task")
            method, args = build_path_adjust_plan(
                back_dist=self.back_dist,
                min_ahead_dist=ConfigParams.minAheadDist,
                adjust_dist=ConfigParams.aheadDist,
            )
            rec_world_pos, method, args = self._resolve_recognition_approach_plan(
                rec_world_pos,
                self.back_dist,
                method,
                args,
            )
            Trace.log(f"method:{method}", name="fork.task")
            self.deferred_leave_loc_actions = self._build_leave_loc_followup_actions(
                allow_same_path_return=self.recognition_readjust_count == 0,
            )
            yield self._build_load_approach_batch(rec_action, rec_world_pos, method, args)

        # 进叉完成（或无目标点盲叉）：此刻构建顶升动作，读到进叉后真实货叉高度
        lift = self._build_load_transport_lift_action()
        yield [lift]
        # 顶升完成：设置货物模型（副作用），再把 post_load + 延迟的 leaveLoc 作为最后一批 yield
        # （必须 yield 而非 _extend：生成器耗尽即收尾，extend 进队的动作会来不及执行）
        load_goods_shape(self)
        goods_name = self.task_args.get("goodsName") or Container.getTaskGoods() or self.recfile or "shelf"
        Container.bindContainer("0", goods_name, self.recfile or "")
        tail = list(self._build_post_load_actions())
        tail.extend(self.deferred_leave_loc_actions)
        self.deferred_leave_loc_actions = []
        if tail:
            yield tail

    def leave_loc(self):
        if not self.operation_init:
            self.operation_init = True

            target_pos = self.get_station_pos("targetName")[0]
            if not has_valid_target_pos(target_pos):
                Navigation.setTaskError("NoTargetId", f"cannot find point, script failed")
                self.set_status(ScriptStatus.FAILED)
                return
            self._set_actions(self._build_leave_loc_operation_actions(target_pos))
            Trace.log(f"task:{self.action_task}", name="fork.task")

    def unload(self):
        # 生成器式放货：识别/盲放 -> 进叉 -> 落叉释放 -> 收尾，全流程顶到底可读。
        if not validate_goods_state_for_operation(self, "unload"):
            return
        apply_default_navigation_policy()
        r_loc = get_r_loc()
        self._init_start_loc_from_source(r_loc)
        target_pos, tcp_name = self.get_station_pos("targetName")
        self.target_pos = target_pos
        Trace.log(f"target_pos: {target_pos}", name="fork.task")
        self._on_unload_actions_build()

        unload_guard = self._build_unload_guard_actions()
        if self.script_status == ScriptStatus.FAILED:
            return
        if unload_guard:
            yield unload_guard
            self._skip_next_start_height_action = True

        loc_detect_action = self._build_loc_detect_action(expect_goods=False)
        if loc_detect_action is not None and self._has_usable_target_pos(target_pos):
            yield [loc_detect_action]

        if self.recognize:
            if not ensure_recfile(self):
                return
            if self._has_usable_target_pos(target_pos):
                rec_center2robot = resolve_rec_center_to_robot(target_pos, get_r_loc())
            else:
                rec_center2robot = [ConfigParams.recCenterX, ConfigParams.recCenterY]
            self.back_dist = resolve_back_dist(self.rec_info)
            rec_action = self._create_unload_recognition_action(rec_center2robot)
            yield self._build_unload_entry_batch(rec_action)

            # 卸货识别完成，就地读结果并校验
            Trace.log(f"add unload task list {format_action(rec_action)},id {self.action_id}", output_console=True,
                      output_time=True, name="fork.task")
            _, _, rec_world_pos, rec_robot_pos = self._resolve_load_recognition_pose(rec_action)
            Trace.log(f"rec_world_pos: {rec_world_pos},robotResult:{rec_robot_pos}", output_console=True,
                      output_time=True, name="fork.task")
            tcp_enabled = bool(ConfigParams.enableTcp)
            rec_world_pos = apply_tcp_target(
                rec_world_pos, "move/defaultTcp", enabled=tcp_enabled, log_name="fork.task")
            if not validate_recognition_result_against_target(self, rec_world_pos):
                return
            method, args = build_path_adjust_plan(
                back_dist=self.back_dist,
                min_ahead_dist=ConfigParams.minAheadDist,
                adjust_dist=ConfigParams.aheadDist,
                enabled=tcp_enabled,
            )
            Trace.log(f"method:{method}", name="fork.task")
            self.deferred_leave_loc_actions = self._build_leave_loc_followup_actions(
                allow_same_path_return=tcp_enabled,
            )
            yield self._build_unload_approach_batch(rec_action, rec_world_pos, method, args)
        elif not self._has_usable_target_pos(target_pos):
            # 无目标点：直接落叉释放（softbag 先抬到起始高度）
            prepare = self._build_unload_no_target_prepare_batch()
            if prepare:
                yield prepare
        else:
            actions, allow_same_path_return = self._build_unload_target_approach(target_pos, tcp_name)
            self.deferred_leave_loc_actions = self._build_leave_loc_followup_actions(
                allow_same_path_return=allow_same_path_return,
            )
            yield actions

        # 进叉完成（或无目标点）：落叉释放
        release = self._build_unload_release_action()
        yield [release]
        # 释放完成：清货物模型（副作用），再把 post_unload + 延迟的 leaveLoc 作为最后一批 yield
        # （必须 yield 而非 _extend：生成器耗尽即收尾，extend 进队的动作会来不及执行）
        self.unbindContainer("0")
        tail = list(self._build_post_unload_actions())
        tail.extend(self.deferred_leave_loc_actions)
        self.deferred_leave_loc_actions = []
        if tail:
            yield tail

    def _execute_actions(self):
        if self.action_task.is_empty:
            Trace.log(f"no action found", name="fork.err")
            return

        prev_index = self.action_id
        prev_current = self.current_action
        prev_status = prev_current.action_status if prev_current else None

        if prev_current is not None:
            check_motor_action_error(prev_current, self.opt, ConfigParams.moduleMotor)
        self.action_task.step(self)
        self._sync_action_runtime()

        if prev_current is not None and prev_status == ActionStatus.INIT:
            if self.current_action is prev_current and self.current_action.action_status == ActionStatus.RUNNING:
                Trace.log(f"execute {self.current_action.action_name} start", output_console=True, output_time=True,
                          name="fork.action")
        elif prev_current is not None and prev_status == ActionStatus.FINISHED:
            Trace.log(f"execute {prev_current.action_name} finished", output_console=True, output_time=True,
                      name="fork.action")
        elif prev_current is not None and prev_status == ActionStatus.FAILED:
            Trace.log(f"execute {prev_current.action_name} failed", output_console=True, output_time=True,
                      name="fork.err")

        chart_action = self.current_action or prev_current
        chart_index = self.action_id if self.current_action is not None else max(prev_index - 1, 0)
        if chart_action is not None and not self.action_task.is_empty:
            self.report_info.update(
                _action_chart_dict(chart_action, min(chart_index, self.action_task.total - 1))
            )

        if self.action_status == ActionStatus.FAILED:
            failed_action = self.current_action or prev_current
            if failed_action is not None:
                Trace.log(f"execute {failed_action.action_name} failed", output_console=True, output_time=True,
                          name="fork.err")
                if not getattr(failed_action, "preserve_task_error", False):
                    Navigation.setTaskError(
                        "ExecuteActionError",
                        f"execute action {format_action(failed_action)} failed!",
                    )

        # script 状态独立 chart 通道
        script_trace_payload = self.script_trace_payload
        script_trace_payload["script.task_len"] = self.action_task.total
        script_trace_payload["script.action_id"] = self.action_id
        script_trace_payload["script.all_action_status"] = int(self.action_status)
        script_trace_payload["script.cur_action"] = self.current_action.action_name if self.current_action else ""
        script_trace_payload["script.cur_action_status"] = (
            int(self.current_action.action_status) if self.current_action else 0
        )
        script_trace_payload["script.script_status"] = int(self.script_status)
        """
        @NameZh @fork.script 叉车脚本动作时序
        @NameEn @fork.script fork script action timeline
        @KeyZh @script.task_len 动作队列长度
        @KeyEn @script.task_len action queue length
        @NumberType @script.task_len
        @KeyZh @script.action_id 当前动作索引
        @KeyEn @script.action_id current action index
        @NumberType @script.action_id
        @KeyZh @script.all_action_status 整体动作状态
        @KeyEn @script.all_action_status overall action status
        @NumberType @script.all_action_status
        @KeyZh @script.cur_action 当前动作名称
        @KeyEn @script.cur_action current action name
        @StringType @script.cur_action
        @KeyZh @script.cur_action_status 当前动作状态
        @KeyEn @script.cur_action_status current action status
        @NumberType @script.cur_action_status
        @KeyZh @script.script_status 脚本状态
        @KeyEn @script.script_status script status
        @NumberType @script.script_status
        """
        Trace.log(script_trace_payload, False, True, name=self.script_trace_channel)

    def motor_jog_or_move(self, motor_type):
        """电机点动或长按操作"""
        if not self.operation_init:
            self.operation_init = True

            if motor_type == "reach" and len(ConfigParams.reach_motor_names) > 1:
                self._set_actions([self._build_multi_reach_manual_action()])
                return

            motor_info = self._resolve_motor_info(motor_type)

            if not motor_info:
                if self.script_status == ScriptStatus.FAILED:
                    return
                Navigation.setTaskError("motorTypeError",
                                        f"motor type {motor_type} not found,check moduleMotor config", )
                self.set_status(ScriptStatus.FAILED)
                return

            motor_key = motor_info["motorKey"]
            min_length = motor_info["minLength"]
            max_length = motor_info["maxLength"]

            # 点动操作
            if self.jog_step is not None:
                current_pos = Motor.getMotorPos(motor_key)
                target_pos = current_pos + self.jog_step
                # 边界检查
                target_pos = clamp(target_pos, min_length, max_length)
                if motor_type == "lift":
                    self._set_actions([RunMotorByPosition(motor_key, target_pos)])
                else:
                    self._set_actions([RunMotorByPosition(
                        motor_key, target_pos, self.motor_max_speed, stop_di=self.motor_stop_di
                    )])
            # 长按操作
            elif self.target_position is not None:
                if motor_type == "lift":
                    self._set_actions([RunMotorByPosition(motor_key, self.target_position)])
                else:
                    self._set_actions([RunMotorByPosition(
                        motor_key, self.target_position, self.motor_max_speed, stop_di=self.motor_stop_di
                    )])
            else:
                Navigation.setTaskError("inputParamError",
                                        f"jogStep or position not provided check the input param provide jogStep or position")
                self.set_status(ScriptStatus.FAILED)
                return

    def _build_multi_reach_manual_action(self):
        contact_di = [self.motor_stop_di] if self.motor_stop_di else []
        if self.jog_step is not None:
            targets = []
            for motor_name in ConfigParams.reach_motor_names:
                current_pos = Motor.getMotorPos(motor_name)
                min_length, max_length = ConfigParams._get_motor_limits(motor_name)
                targets.append(clamp(current_pos + self.jog_step, min_length, max_length))
            target = targets
        elif self.target_position is not None:
            target = self.target_position
        else:
            Navigation.setTaskError(
                "inputParamError",
                "jogStep or position not provided check the input param provide jogStep or position",
            )
            self.set_status(ScriptStatus.FAILED)
            return None

        return RunReachMotorsByPosition(
            ConfigParams.reach_motor_names,
            target,
            self.motor_max_speed,
            ConfigParams.reachMotorSyncTolerance,
            contact_di=contact_di,
            check_all_di=False,
            action_name="manualReachMotors",
        )

    def fork_move(self):
        if not self.operation_init:
            self.fork_height_in_place = False
            self.operation_init = True
            # forkHeight 和 forkSpeed 为任务输入参数
            # if ConfigParams.fork_motor_name:
            self._set_actions([RunMotorByPosition(ConfigParams.fork_motor_name, self.forkHeight, self.forkSpeed)])
        # print("action_status:" + json.dumps(cur_status))

    def weight_good(self):
        if not self.operation_init:
            self.operation_init = True
            self._set_actions([build_weight_action(ConfigParams)])
        action = self.action_task.first_action
        if isinstance(action, WeightCheckAction) and action.weight_result is not None:
            self.report_info["weightResult"] = round(action.weight_result, 3)

    def _init_args(self):

        # 解析任务参数，script_args 里的参数
        self._init_task_runtime_state()
        self.rec_pallet_handled = False
        self.rec_cage_handled = False
        self.obstacle_polygon_by_rec = []
        self.recfile = self.task_args.get("recfile", "") or ""
        if self.recfile.startswith("recognition/"):
            self.recfile = self.recfile[len("recognition/"):]
        self.opt = self.task_args.get("operation", "")
        self.start_height_provided = "startHeight" in self.task_args
        self.start_height = self.task_args.get("startHeight", 0.09)
        self.rec_height = self.task_args.get("recHeight", -1)
        self.end_height = self.task_args.get("endHeight", 0.2)
        self.loc_detect_height = self.task_args.get("locDetectHeight", -1)
        self.loc_detect_layer = self.task_args.get("locDetectLayer", -1)
        self._skip_next_start_height_action = False
        self.leave_loc_height = self.task_args.get("leaveLocHeight", -1)
        # New payloads use leaveLoc as the explicit switch. Keep legacy payloads
        # with a non-negative leaveLocHeight working until callers migrate.
        self.leave_loc = is_enabled(
            self.task_args.get("leaveLoc", self.leave_loc_height >= 0)
        )
        if type(self).lift_fork_model_limits and self.opt in ("load", "unload"):
            # LiftFork is a two-position mechanism; ignore generic height
            # fields from legacy callers and use device-model limits.
            self.start_height_provided = False
            self.start_height = ConfigParams.min_height
            self.rec_height = -1
            self.end_height = (
                ConfigParams.max_height if self.opt == "load" else ConfigParams.min_height
            )
            self.leave_loc_height = ConfigParams.min_height if self.leave_loc else -1
        self.forkHeight = self.task_args.get("height")
        self.forkSpeed = self.task_args.get("forkSpeed", ConfigParams.fork_max_speed)
        self.recSide = self.task_args.get("recSide", None)
        if self.recSide == "none":
            self.recSide = None
        self.jog_step = self.task_args.get("jogStep", None)
        self.target_position = self.task_args.get("position", None)
        default_motor_speed = 0.05 if self.opt == "reach" else 0.01
        self.motor_max_speed = self.task_args.get(
            "max_speed",
            self.task_args.get("maxSpeed", default_motor_speed),
        )
        self.motor_stop_di = self.task_args.get("stop_di", self.task_args.get("stopDi", ""))
        input_recognize = is_enabled(self.task_args.get("recognize", False))

        # 解析任务下发的参数，不含在 script_args 里的参数
        self.move_task = Navigation.moveTask()

        movetask_recognize = next(
            (p.get('boolValue') for p in self.move_task.get('params', [])
             if p.get('key') == 'recognize'),
            False
        )
        self.min_safe_height = next(
            (float(p.get('floatValue', p.get('value', 0.0))) for p in self.move_task.get('params', [])
             if p.get('key') == 'minSafeHeight'),
            0.0
        )
        Trace.log(f"min_safe_height:{self.min_safe_height}", name="fork.task")
        Trace.log(f"move task:{self.move_task}", name="fork.task")

        self.recognize = any([input_recognize, is_enabled(movetask_recognize)])

        self.start_time = time.time()

        self._init_extra_args()
        in_place_end_height_only = (
            self.opt in ("load", "unload")
            and self.move_task.get("skillName", "") == "Action"
            and not self.recognize
        )
        if (
                type(self).requires_explicit_start_height
                and self.opt in ("load", "unload", "cageStack", "unstack")
                and not self.start_height_provided
                and not in_place_end_height_only
        ):
            Navigation.setTaskError(
                "StartHeightRequired",
                f"startHeight is required for {type(self).__name__} operation {self.opt}",
            )
            self.set_status(ScriptStatus.FAILED)
            return
        Trace.log("init args", name="fork.task")

    def _check_timeout(self):
        self.script_runtime = time.time() - self.start_time
        if self.script_runtime > ConfigParams.timeout:
            Trace.log(f"script timeout:{ConfigParams.timeout}", name="fork.err")
            Navigation.setTaskError("ScriptTimeout", f"script timeout:{ConfigParams.timeout}, script failed")
            self.set_status(ScriptStatus.FAILED)
            self.action_task.cancel(reason=f"script timeout:{ConfigParams.timeout}")
            self._sync_action_runtime()

    def rec(self):
        if not self.operation_init:
            self.operation_init = True
            self._set_actions([Rec(self.recfile, rec_center_x=ConfigParams.recCenterX,
                                   rec_center_y=ConfigParams.recCenterY, rec_radius=ConfigParams.recRadius,
                                   checkQR=self.rec_check_qr)])
        first_action = self.action_task.first_action
        if self.rec_check_qr and isinstance(first_action, Rec):
            self.report_info.update({"objectMessage ": first_action.object_message})

    def save_mileage(self, force=False):
        if not self.mileage_enabled:
            return
        if not force and not self.mileage_dirty:
            return
        run_db = _get_run_db()
        run_db.put(self.mileage_total_key, self.total_dist)
        run_db.put(self.mileage_up_key, self.up_dist)
        run_db.put(self.mileage_down_key, self.down_dist)
        run_db.put(self.key_today_total_mileage, self.today_total)
        run_db.put(self.key_today_up_mileage, self.today_up)
        run_db.put(self.key_today_down_mileage, self.today_down)
        run_db.put(self.key_today_date, self.today_date)
        self.mileage_dirty = False

    def period_run(self):
        self._reset_daily_mileage_if_needed()
        fork_height = round(Motor.getMotorPos(ConfigParams.fork_motor_name), 3)
        self.fork_height = fork_height
        fork_auto_flag = not Controller.getIsExternalControl()

        # 更新 moduleMotor 的 currentPosition
        for motor in ConfigParams.moduleMotor:
            try:
                motor["currentPosition"] = round(Motor.getMotorPos(motor["motorKey"]), 3)
            except Exception as e:
                Trace.log(f"Failed to get motor position for {motor['motorKey']}: {e}", name=f"{MOD}.err")

        # 根据变动量记录货叉的里程数据
        if self.last_pos is not None:
            delta = fork_height - self.last_pos
            if delta > ConfigParams.reach_up_dist:
                self.up_dist += delta
                self.total_dist += delta
                self.today_up += delta
                self.today_total += delta
                self.mileage_dirty = True
            elif delta < -ConfigParams.reach_down_dist:
                d = -delta
                self.down_dist += d
                self.total_dist += d
                self.today_down += d
                self.today_total += d
                self.mileage_dirty = True

        self.last_pos = fork_height

        if self.mileage_dirty and time.time() - self.last_save_ts > self.save_interval:
            self.save_mileage()
            self.last_save_ts = time.time()

        report_info = self.report_info
        report_info["forkHeight"] = fork_height  # 货叉高度, 单位 m
        report_info["forkHeightInPlace"] = self.fork_height_in_place
        report_info["forkAutoFlag"] = fork_auto_flag
        report_info["containers"] = Container.getContainers()
        report_info["moduleMotor"] = ConfigParams.moduleMotor
        report_info["moduleScript"] = ConfigParams.scriptName
        Module.reportInfo(report_info)

        # 高频时序通道复用固定 payload，避免每 tick 临时构造 dict / 动态通道名。
        task_trace_payload = self.task_trace_payload
        task_trace_payload["scriptStatus"] = int(self.script_status)
        task_trace_payload["actionStatus"] = int(self.action_status)
        task_trace_payload["actionIndex"] = int(self.action_id)
        task_trace_payload["actionCount"] = int(self.action_task.total)
        task_trace_payload["forkAutoFlag"] = bool(fork_auto_flag)
        """
        @NameZh @fork.task 叉车任务执行状态
        @NameEn @fork.task fork task execution status
        @KeyZh @scriptStatus 脚本状态
        @KeyEn @scriptStatus script status
        @NumberType @scriptStatus
        @KeyZh @actionStatus 动作状态
        @KeyEn @actionStatus action status
        @NumberType @actionStatus
        @KeyZh @actionIndex 当前动作索引
        @KeyEn @actionIndex current action index
        @NumberType @actionIndex
        @KeyZh @actionCount 动作总数
        @KeyEn @actionCount total action count
        @NumberType @actionCount
        @KeyZh @forkAutoFlag 是否自动控制
        @KeyEn @forkAutoFlag fork auto flag
        @BooleanType @forkAutoFlag
        """
        Trace.log(task_trace_payload, output_console=False, name=self.task_trace_channel)

        motor_trace_payload = self.motor_trace_payload
        motor_trace_payload["forkHeight"] = float(fork_height)
        motor_trace_payload["forkHeightInPlace"] = bool(self.fork_height_in_place)
        motor_trace_payload["forkMileage"] = float(self.total_dist)
        motor_trace_payload["forkMileageUp"] = float(self.up_dist)
        motor_trace_payload["forkMileageDown"] = float(self.down_dist)
        motor_trace_payload["minSafeHeight"] = float(self.min_safe_height)
        """
        @NameZh @fork.motor 叉车货叉电机状态
        @NameEn @fork.motor fork motor status
        @KeyZh @forkHeight 当前货叉高度
        @KeyEn @forkHeight current fork height
        @NumberType @forkHeight
        @Unit @forkHeight m
        @KeyZh @forkHeightInPlace 货叉是否到位
        @KeyEn @forkHeightInPlace fork in place
        @BooleanType @forkHeightInPlace
        @KeyZh @forkMileage 货叉总里程
        @KeyEn @forkMileage total fork mileage
        @NumberType @forkMileage
        @Unit @forkMileage m
        @KeyZh @forkMileageUp 货叉上升里程
        @KeyEn @forkMileageUp fork upward mileage
        @NumberType @forkMileageUp
        @Unit @forkMileageUp m
        @KeyZh @forkMileageDown 货叉下降里程
        @KeyEn @forkMileageDown fork downward mileage
        @NumberType @forkMileageDown
        @Unit @forkMileageDown m
        @KeyZh @minSafeHeight 最小安全高度
        @KeyEn @minSafeHeight minimum safe height
        @NumberType @minSafeHeight
        @Unit @minSafeHeight m
        """
        Trace.log(motor_trace_payload, output_console=False, name=self.motor_trace_channel)

        # 写modbus寄存器
        modbus_list_fork_height = float_to_modbus_poll_regs(fork_height)
        NetProtocol.setModbusData("3x", 57, modbus_list_fork_height)

        _run_script_hook("period_run_hook", self, fork_height)

        # 处理载货时di状态监控
        if ConfigParams.checkGoodsWhileLoad:

            # 获取到位 di 的状态
            di_status = []
            contact_ids = ConfigParams.contact_ids
            for di in contact_ids:
                di_status.append(Di.getDi(di))

            # 根据是否检测所有到位di 决定错误状态
            if Container.hasGoods("0"):
                if ConfigParams.checkAllContactDis:
                    missing_goods = not all(di_status)
                else:
                    missing_goods = not any(di_status)

                # 做 0.3s 的延时处理
                if missing_goods and Timer.delay(0.3):
                    Navigation.setTaskError("forkMissingGood", "fork missing goods,No Contact Di Trigger")
                else:
                    if Timer.delay(0.3):
                        if Navigation.errorExists("forkMissingGood"):
                            Navigation.clearTaskError("forkMissingGood")


def _heavy_period_run(robot, fork_height):
    update_back_laser_clear_region_by_height(robot, fork_height, ConfigParams)


def cage_stack_config_builder(_config_cls, builder):
    with builder.GROUP(key="cageStackScene", name=_TR("Cage Stack"),
                       desc=_TR("Cage stack settings")):
        builder.TYPE(ParamType.ARRAY)
        with builder.CHILDREN():
            with builder.CHILD(key="cageRecfile", name=_TR("Cage Recognition File"),
                               desc=_TR("Recognition file used for cage alignment")):
                builder.TYPE(ParamType.BIND_TYPE)
                builder.BINDTYPE(BindType.App.RECOGNITION)
                builder.DEFAULTVALUE(_config_cls.cageRecfileDefault)


def cage_stack_config_reload(config_cls, cfg):
    recfile = (
        config_cls._find_config_value(["cageRecfile"], cfg)
        or config_cls.cageRecfileDefault
    )
    recfile = str(recfile)
    if recfile.startswith("recognition/"):
        recfile = recfile[len("recognition/"):]
    config_cls.cageRecfile = recfile


class HeavyFork(Fork):
    """重型车型共享基类。

    集中承载「重型车型通用、但非全车型通用」的能力，避免各车型脚本重复实现：
    - 后激光按高度屏蔽（period_run_hook）：原在 counterBalance 系列逐字复制、straddle 同名实现，共 4 份等价代码。
    - 料笼堆叠 cage_stack 及其辅助方法：标杆实现源自 straddleLiftFork，作为重型车型共享归宿。

    注意：cage_stack 的「注册」（extend_custom_operation_inputs / custom_action_templates /
    custom_operations / custom_cleanup_operations）仍只由需要该操作的车型声明，避免给其他
    HeavyFork 子类意外开启 cageStack 操作。

    非重型车型（singleFork / liftFork / pickFork / softbagFork）不要继承本类。
    """
    supports_cam_lift_with_fork = True
    # 后激光按高度屏蔽：所有重型车型通用，原在 counterBalance 系列逐字复制、straddle 同名实现
    period_run_hook = staticmethod(_heavy_period_run)

    # ------------------------------------------------------------------
    # cage_stack（料笼堆叠，标杆实现，源自 straddleLiftFork）
    # ------------------------------------------------------------------
    def _create_cage_stack_pallet_recognition_action(self, rec_center2robot):
        return Rec(
            self.recfile,
            rec_center2robot[0],
            rec_center2robot[1],
            ConfigParams.recRadius,
            action_name="RecPallet",
        )

    def _create_cage_stack_cage_recognition_action(self):
        return Rec(
            ConfigParams.cageRecfile,
            -ConfigParams.tail,
            0,
            ConfigParams.recRadius,
            action_name="RecCage",
        )

    def _build_cage_stack_entry_batch(self, pallet_rec):
        actions = self._build_start_height_actions()
        actions.append(pallet_rec)
        return actions

    def _build_cage_stack_guard_actions(self):
        return []

    def _build_cage_stack_pre_insert_guard_actions(self):
        return []

    def _build_cage_stack_post_pallet_recognition_actions(self, rec_world_pos, method, args, cage_rec):
        actions = [
            RunMotorByPosition(ConfigParams.fork_motor_name, self.rec_height),
        ]
        actions.extend(self._build_cage_stack_pre_insert_guard_actions())
        actions.extend([
            GoPathWithContactDi(
                ConfigParams.contact_ids,
                rec_world_pos,
                ConfigParams.loadObsStopDist,
                method,
                args,
                False,
                "load",
                recfile=self.recfile,
            ),
            cage_rec,
        ])
        return actions

    def _build_cage_stack_finish_actions(self):
        return [RunMotorByPosition(ConfigParams.fork_motor_name, self.end_height)]

    def _build_cage_stack_retry_actions(self, robot2pos, cage_rec):
        return [MoveChassisByY(robot2pos), cage_rec]

    def _build_cage_stack_adjust_plan(self):
        return build_path_adjust_plan(
            back_dist=-0.15,
            min_ahead_dist=ConfigParams.minAheadDist,
            adjust_dist=ConfigParams.aheadDist,
        )

    @staticmethod
    def _is_invalid_cage_target_pose(robot2pos):
        return any(abs(value) >= 999 for value in robot2pos[:3])

    @staticmethod
    def _is_cage_alignment_in_range(robot2pos):
        return abs(math.degrees(robot2pos[2])) <= 10 and abs(robot2pos[0]) <= 0.3

    @staticmethod
    def _is_cage_alignment_complete(robot2pos):
        return (
            abs(math.degrees(robot2pos[2])) <= 0.5
            and abs(robot2pos[0]) <= 0.01
            and abs(robot2pos[1]) <= 0.01
        )

    def _setup_cage_stack(self):
        """cageStack 一次性初始化：返回 (rec_center2robot, tcp_name)；失败返回 None。"""
        apply_default_navigation_policy()

        r_loc = get_r_loc()
        self._init_start_loc_from_source(r_loc)
        self.target_pos, tcp_name = self.get_station_pos("targetName")
        Trace.log(f"target_pos: {self.target_pos}", output_console=True, output_time=True, name="fork.task")

        self.recfile = self.recfile or "default.srec"
        if not load_recognition_assets(self):
            return None

        self.back_dist = resolve_back_dist(self.rec_info)
        return resolve_rec_center_to_robot(self.target_pos, r_loc), tcp_name

    def cage_stack(self):
        # 生成器式 operation：可选识别托盘 -> 进叉 + 识别料笼 -> 对齐循环 -> 落叉。
        # 每 yield 一批动作，队列跑完后 resume；yield 之后就地读刚结束动作的结果，
        # 续接由 yield 边界驱动，不再需要 on_finished 谓词 / _handled 标志 / cage_count 轮询。
        self.cage_count = 0
        setup_result = self._setup_cage_stack()
        if setup_result is None:
            return
        rec_center2robot, tcp_name = setup_result

        cage_stack_guard = self._build_cage_stack_guard_actions()
        if self.script_status == ScriptStatus.FAILED:
            return
        if cage_stack_guard:
            yield cage_stack_guard
            self._skip_next_start_height_action = True

        cage_rec = self._create_cage_stack_cage_recognition_action()

        if not self.recognize:
            # 与 load 的盲叉分支保持一致：按 AP/TCP 生成路径，到位后直接识别料笼。
            if not self._has_usable_target_pos(self.target_pos):
                Navigation.setTaskError("NoTargetId", "cannot find point, script failed")
                self.set_status(ScriptStatus.FAILED)
                return
            self.check_di = ConfigParams.enableContactDiNoRec
            actions = self._build_load_no_rec_approach_batch(self.target_pos, tcp_name)
            actions.append(cage_rec)
            yield actions
        else:
            # 1) 到起始高度 + 识别托盘（车型可插入堆垛层激光校验）
            pallet_rec = self._create_cage_stack_pallet_recognition_action(rec_center2robot)
            yield self._build_cage_stack_entry_batch(pallet_rec)

            # 托盘识别完成，就地读结果
            resolved = yield from self._run_recognition_readjust(
                pallet_rec,
                self._create_cage_stack_pallet_recognition_action,
                check_tilt=False,
            )
            if resolved is None:
                return
            pallet_rec, rec_result_dict, rec_world_pos, rec_robot_pos = resolved
            Trace.log(f"carrier {self.carrier_shape, self.goods_shape, self.obstacle_polygon_by_rec}",
                      output_console=True, output_time=True, name="fork.task")
            method, args = self._build_cage_stack_adjust_plan()
            rec_world_pos, method, args = self._resolve_recognition_approach_plan(
                rec_world_pos,
                args["back_dist"],
                method,
                args,
            )
            Trace.log(f"method:{method}", name="fork.task")

            # 2) 进叉到识别高度 + 识别料笼；对齐不足则 MoveChassisByY 微调后复识别
            yield self._build_cage_stack_post_pallet_recognition_actions(rec_world_pos, method, args, cage_rec)

        while True:
            robot2pos = self.get_robot2target_pos(cage_rec.results_list)
            Trace.log(f"robot2pos: {robot2pos},yaw: {math.degrees(robot2pos[2])}",
                      output_console=True, output_time=True, name="fork.task")
            if self._is_invalid_cage_target_pose(robot2pos):
                self.set_status(ScriptStatus.FAILED)
                return
            if not self._is_cage_alignment_in_range(robot2pos):
                Navigation.setTaskError("CageTooFar", "cage too far")
                self.set_status(ScriptStatus.FAILED)
                return
            Trace.log(f"cage_count:{self.cage_count}", output_console=True, output_time=True, name="fork.task")
            if self._is_cage_alignment_complete(robot2pos) or self.cage_count >= 1:
                break
            self.cage_count += 1
            cage_rec = self._create_cage_stack_cage_recognition_action()
            yield self._build_cage_stack_retry_actions(robot2pos, cage_rec)

        # 3) 落叉到目标高度
        yield self._build_cage_stack_finish_actions()

    def get_robot2target_pos(self, results_list):
        def get_robot_pose(obj):
            robot_result = obj.get("robotResult", "")

            if isinstance(robot_result, str):
                robot_result = json.loads(robot_result)

            return {
                "class": obj.get("class"),
                "x": robot_result.get("x", 0),
                "y": robot_result.get("y", 0),
                "z": robot_result.get("z", 0),
                "yaw": robot_result.get("yaw", 0)
            }

        def normalize_angle_rad(a):
            return (a + math.pi) % (2 * math.pi) - math.pi

        def calc_yaw_from_two_points(p0, p1):
            p0, p1 = sorted([p0, p1], key=lambda p: p["y"])

            dx = p1["x"] - p0["x"]
            dy = p1["y"] - p0["y"]

            if abs(dx) < EPS:
                return 0.0

            yaw = math.atan2(-dx, dy)
            return normalize_angle_rad(yaw)

        bottom_cages = [
            get_robot_pose(obj)
            for obj in results_list
            if obj.get("class") == "Head"
        ]

        top_cages = [
            get_robot_pose(obj)
            for obj in results_list
            if obj.get("class") == "Bottom"
        ]

        Trace.log(f"bottom_cages: {bottom_cages},top_cages: {top_cages}", True, True)

        if len(bottom_cages) < 2:
            Navigation.setTaskError("Wrong bottom num", "")
            return [999, 999, 999]

        if len(top_cages) < 2:
            Navigation.setTaskError("Wrong top num", "")
            return [999, 999, 999]

        tops_sorted = sorted(top_cages, key=lambda o: o["x"], reverse=True)
        bottoms_sorted = sorted(bottom_cages, key=lambda o: o["x"], reverse=True)

        top_two = tops_sorted[:2]
        bottom_two = bottoms_sorted[:2]

        top_mid = {
            "x": (top_two[0]["x"] + top_two[1]["x"]) / 2.0,
            "y": (top_two[0]["y"] + top_two[1]["y"]) / 2.0,
            "z": (top_two[0]["z"] + top_two[1]["z"]) / 2.0,
            "yaw": calc_yaw_from_two_points(top_two[0], top_two[1])
        }

        bottom_mid = {
            "x": (bottom_two[0]["x"] + bottom_two[1]["x"]) / 2.0,
            "y": (bottom_two[0]["y"] + bottom_two[1]["y"]) / 2.0,
            "z": (bottom_two[0]["z"] + bottom_two[1]["z"]) / 2.0,
            "yaw": calc_yaw_from_two_points(bottom_two[0], bottom_two[1])
        }

        # 上料笼比下料笼宽，分别按自身 yaw 做中心偏移
        top_mid_offset = pos2World(
            [-0.15 / 2, 0, 0],
            [top_mid["x"], top_mid["y"], top_mid["yaw"]]
        )

        # if ConfigParams.shiftMotor:
        #     shift_position = Motor.getMotorPos(ConfigParams.shiftMotor)
        #     Trace.log(f"shift_position:{shift_position}")
        #     top_mid_offset = pos2World([0, shift_position, 0], top_mid_offset)

        bottom_mid_offset = pos2World(
            [-0.05 / 2, 0, 0],
            [bottom_mid["x"], bottom_mid["y"], bottom_mid["yaw"]]
        )

        # 上料笼相对下料笼的位姿
        robot2target = pos2Base(top_mid_offset, bottom_mid_offset)

        Trace.log(
            f"top_two:{top_two}, "
            f"bottom_two:{bottom_two}, "
            f"top_mid:{top_mid}, "
            f"bottom_mid:{bottom_mid}, "
            f"top_mid_offset:{top_mid_offset}, "
            f"bottom_mid_offset:{bottom_mid_offset}, "
            f"top2bottom_pos:{robot2target}",
            name="fork.task"
        )

        return robot2target


class ReachFork(HeavyFork):
    """带前移机构车型的共享流程层。

    前移机构只改变取放货的进叉、退叉和离库编排；识别、顶升、货物模型等仍复用
    Fork/HeavyFork 主流程。现场调试时优先关注 adjustMethod、前移电机动作和
    leaveLoc 三段日志，不需要从车型薄入口查找流程差异。
    """

    supports_reach_motor = True
    use_current_height_when_start_omitted = False
    requires_explicit_start_height = True

    def _reach_extension_distance(self):
        # 路径需要按机构的最大可伸出距离预留空间；多电机时取最大行程作为整组伸出量。
        distances = []
        for motor_name in ConfigParams.reach_motor_names:
            min_length, max_length = ConfigParams._get_motor_limits(motor_name)
            distances.append(max(0.0, max_length - min_length))
        return max(distances, default=0.0)

    def _build_reach_action(self, target, *, stop_on_contact=False, action_name="RunReachMotors"):
        # 只有明确要求 stop_on_contact 的动作才绑定叉尖 DI，普通伸出/收回以目标位置结束。
        return RunReachMotorsByPosition(
            ConfigParams.reach_motor_names,
            target,
            ConfigParams.reachMotorMaxSpeed,
            ConfigParams.reachMotorSyncTolerance,
            contact_di=ConfigParams.contact_ids if stop_on_contact else [],
            check_all_di=ConfigParams.checkAllContactDis,
            action_name=action_name,
        )

    def _shift_path_target_for_reach(self, target_pos, distance=None):
        # 前移机构负责补足这一段距离，因此底盘目标沿托盘朝向后移，避免车体多走一个伸出量。
        reach_distance = self._reach_extension_distance() if distance is None else float(distance)
        return pos2World([-reach_distance, 0.0, 0.0], target_pos)

    def _reach_adjusted_plan(self, method, args):
        # bezier/直线模式不能直接改世界坐标目标，需要把伸出量计入路径的距离参数。
        adjusted = dict(args or {})
        reach_distance = self._reach_extension_distance()
        if adjusted:
            adjusted["back_dist"] = float(adjusted.get("back_dist", 0.0)) - reach_distance
            adjusted["min_ahead_dist"] = float(
                adjusted.get("min_ahead_dist", ConfigParams.minAheadDist)
            )
        return method, adjusted

    def _build_reach_path_action(
            self,
            target_pos,
            method,
            args,
            *,
            operation_type,
            check_di,
            obs_dist_compensation=0.0,
    ):
        path_target = target_pos
        path_method, path_args = self._reach_adjusted_plan(method, args)
        if path_method == "goPath":
            path_target = self._shift_path_target_for_reach(target_pos)
        return GoPathWithContactDi(
            ConfigParams.contact_ids,
            path_target,
            ConfigParams.loadObsStopDist if operation_type == "load" else None,
            path_method,
            path_args,
            check_di,
            operation_type,
            obs_dist_compensation=obs_dist_compensation,
            recfile=self.recfile,
        )

    def _build_path_first_load_actions(self, rec_world_pos, method, args):
        # pathFirst：外层仍是一个 GoPathWithContactDi，但内部拆为
        # “前置位对齐 -> 前移机构伸出 -> goPath 完成 backDist 进叉” 三阶段。
        reach_distance = self._reach_extension_distance()
        front_dist = ConfigParams.minAheadDist + reach_distance
        if method == "goPath":
            align_world_pos = pos2World([-front_dist, 0.0, 0.0], rec_world_pos)
            align_method = "goPath"
            align_args = {}
        else:
            align_world_pos = rec_world_pos
            align_method = method
            align_args = dict(args or {})
            align_args["back_dist"] = front_dist
            align_args["min_ahead_dist"] = front_dist
        # 最后一段 goPath 的底盘终点要与 stretchFirst 保持同一几何语义：
        # 目标底盘位置 = “不带前移机构时的 back_dist 终点” 再减去前移机构已补足的 reach_distance。
        # 也就是 back_dist - reach_distance；之前误写成 back_dist + reach_distance，
        # 会把最终目标放到托盘后方更远处，导致 DI 先触发时被判定为“离目标还很远”。
        final_target = pos2World(
            [reach_distance - float(self.back_dist), 0.0, 0.0],
            rec_world_pos,
        )
        return [
            GoPathWithContactDi(
                ConfigParams.contact_ids,
                align_world_pos,
                ConfigParams.loadObsStopDist,
                align_method,
                align_args,
                self.check_di,
                "load",
                recfile=self.recfile,
                reach_phase_config={
                    "align_world_pos": align_world_pos,
                    "align_method": align_method,
                    "align_args": align_args,
                    "final_world_pos": final_target,
                    "final_back_mode": 1,
                    "motor_names": ConfigParams.reach_motor_names,
                    "target": "max",
                    "max_speed": ConfigParams.reachMotorMaxSpeed,
                    "sync_tolerance": ConfigParams.reachMotorSyncTolerance,
                },
            ),
        ]

    def _build_load_approach_batch(self, rec_action, rec_world_pos, method, args):
        actions = list(super()._build_load_approach_batch(rec_action, rec_world_pos, method, args))
        if not ConfigParams.reach_motor_names:
            return actions
        # 基类末项是普通进叉动作；前移车型必须替换它，不能在其后简单追加伸叉动作。
        actions.pop()
        if ConfigParams.adjustMethod == "pathFirst":
            actions.extend(self._build_path_first_load_actions(rec_world_pos, method, args))
            return actions
        # strechFirst：机构先完全伸出，再让底盘按修正后的路径完成进叉。
        actions.extend([
            self._build_reach_action("max", action_name="extendReachMotors"),
            self._build_reach_path_action(
                rec_world_pos,
                method,
                args,
                operation_type="load",
                check_di=self.check_di,
            ),
        ])
        return actions

    def _build_load_no_rec_approach_batch(self, target_pos, tcp_name):
        actions = list(super()._build_load_no_rec_approach_batch(target_pos, tcp_name))
        if not ConfigParams.reach_motor_names:
            return actions
        # 盲叉与识别取货保持相同的前移语义，只是路径目标来自库位而不是识别结果。
        path_action = actions.pop()
        resolved_target = getattr(path_action, "target_pos", None) or target_pos
        if ConfigParams.adjustMethod == "pathFirst":
            reach_distance = self._reach_extension_distance()
            front_target = pos2World(
                [-(ConfigParams.minAheadDist + reach_distance), 0.0, 0.0],
                resolved_target,
            )
            actions.append(GoPathWithContactDi(
                ConfigParams.contact_ids,
                front_target,
                ConfigParams.loadObsStopDist,
                "goPath",
                {},
                False,
                "load",
                recfile=self.recfile,
            ))
        actions.extend([
            self._build_reach_action("max", action_name="extendReachMotors"),
            GoPathWithContactDi(
                ConfigParams.contact_ids,
                self._shift_path_target_for_reach(resolved_target),
                ConfigParams.loadObsStopDist,
                "goPath",
                {},
                self.check_di,
                "load",
                recfile=self.recfile,
            ),
        ])
        return actions

    def _build_reach_unload_prefix(self):
        actions = []
        # 低位直接伸叉可能碰到支撑轮/货架；先抬过安全高度，再伸出，最后回到放货起始高度。
        if self.start_height <= ConfigParams.forkLeaveSafeHeight:
            safe_height = clamp(
                ConfigParams.forkLeaveSafeHeight + 0.02,
                ConfigParams.min_height,
                ConfigParams.max_height,
            )
            actions.append(RunMotorByPosition(
                ConfigParams.fork_motor_name,
                safe_height,
                action_name="unloadReachSafeHeight",
            ))
        actions.append(self._build_reach_action("max", action_name="extendReachMotors"))
        actions.append(self._build_unload_prepare_lift_action(self.start_height))
        return actions

    def _build_unload_approach_batch(self, rec_action, rec_world_pos, method, args):
        if not ConfigParams.reach_motor_names:
            return super()._build_unload_approach_batch(rec_action, rec_world_pos, method, args)
        # 放货统一采用“安全高度检查 -> 伸叉 -> startHeight -> 进入放货位”的顺序。
        actions = self._build_reach_unload_prefix()
        actions.append(self._build_reach_path_action(
            rec_world_pos,
            method,
            args,
            operation_type="unload",
            check_di=False,
        ))
        return actions

    def _build_unload_target_approach(self, target_pos, tcp_name):
        if not ConfigParams.reach_motor_names:
            return super()._build_unload_target_approach(target_pos, tcp_name)
        resolved_target = apply_tcp_target(target_pos, tcp_name) if tcp_name else target_pos
        method, args = build_path_adjust_plan(
            back_dist=0,
            min_ahead_dist=ConfigParams.tail + ConfigParams.module_x,
            adjust_dist=ConfigParams.aheadDist,
            enabled=bool(tcp_name),
        )
        actions = self._build_reach_unload_prefix()
        actions.append(self._build_reach_path_action(
            resolved_target,
            method,
            args,
            operation_type="unload",
            check_di=False,
        ))
        return actions, bool(tcp_name)

    def _build_leave_loc_followup_actions(self, allow_same_path_return=False):
        # pathFirst 包含多段独立路径，缓存的原路只代表其中一段，不能用于完整离库返回。
        actions = super()._build_leave_loc_followup_actions(
            allow_same_path_return=allow_same_path_return and ConfigParams.adjustMethod != "pathFirst",
        )
        if not actions or not ConfigParams.reach_motor_names:
            return actions
        # 基类最后一项是 leaveLocHeight；先取出，插入安全抬升和收叉后再放回队尾。
        actions.pop()
        safe_height = clamp(
            ConfigParams.forkLeaveSafeHeight + 0.05,
            ConfigParams.min_height,
            ConfigParams.max_height,
        )
        if self.end_height < ConfigParams.forkLeaveSafeHeight:
            actions.append(RunMotorByPosition(
                ConfigParams.fork_motor_name,
                safe_height,
                action_name="leaveReachSafeHeight",
            ))
        actions.append(self._build_reach_action("min", action_name="retractReachMotors"))
        leave_height_target = clamp(
            max(float(self.leave_loc_height), safe_height),
            ConfigParams.min_height,
            ConfigParams.max_height,
        )
        actions.append(RunMotorByPosition(
            ConfigParams.fork_motor_name,
            leave_height_target,
            action_name="leaveLocHeight",
        ))
        return actions


def main(script_file: str = __file__, **kwargs):
    robot = Fork(script_file, **kwargs)
    robot.main()


if __name__ == '__main__':
    main()
