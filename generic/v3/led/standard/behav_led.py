#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DMX512 灯光逻辑（BehavFactory 新接口版）。

接口约束（与 BehavFactory.cpp 对齐）：
- light_type: ConstantLight/MutableBreath/MutableHorseRace/Flow/Rainbow/Blink/Off
- rgbw: Red/RedDark/PinkPurple/Green/Blue/BlueCobalt/Yellow/ChargeYellow/White/Black

状态优先级（从高到低）：
1) 报警：`MutableBreath + Red`
2) 任务失败：`Blink + Yellow`，500ms 周期
3) 急停：`Flow + RedDark` (内置灯效，无法通过脚本调整, 固定625ms周期)
4) 阻挡：`MutableHorseRace + PinkPurple`(内置灯效，无法通过脚本调整，固定 1000ms 翻转间隔)
5) 运动：
   - 无转向：`MutableBreath + BlueCobalt`（后退且 `is_back_breath=True` 时用 `White`）
   - 转向：`Blink + Yellow`，并按 `turn_pos/turn_num` 生成 `led_idx`
6) 静止且有电池：
   - 充电：`MutableBreath + ChargeYellow`
   - 低于关机阈值：`MutableBreath + Red`
   - 低于低电阈值：`MutableHorseRace + RedDark`
   - 正常电量显示：`ConstantLight + (Green/Yellow/ChargeYellow/RedDark)`
7) 无电池/电池错误：`Rainbow + Black`（`Black` 仅作接口占位，彩虹灯不依赖颜色）

日志策略：
- 仅在灯效命令变化时打印结构化下发日志（含 `light_type/rgbw/period/led_idx` 与 `reason`）。

周期语义：
- `MutableBreath` / `Blink`：`period` 表示完整周期时长（ms）
- `MutableHorseRace`：`period` 表示翻转间隔（ms）
- `Flow`：`period` 表示完整流水周期（ms）；急停由 C++ 内置为 25 个虚拟槽位、625ms 一轮
- `Rainbow`：当前速度由 C++ 内部实现决定，脚本侧不依赖 `period`
"""

import time
from enum import Enum
from typing import Any, Dict, List, Optional

from syspy import (
    Battery,
    Module,
    NavSpeed,
    NavStatus,
    RobotParam,
    Controller,
    ScriptParam,
    Trace,
    RobotError,
    sim_only,
    _TR
)
from syspy.led import LegacyDmxOutput
from syspy.utils.param_server import ParamType

script_param = ScriptParam(__file__) # 以脚本文件名为命名空间加载配置参数，文件路径见 /opt/.data/rbk/resources/scripts/params/tasks/v3/standard/
LOG_MODULE = "LED"


class LedLightType(str, Enum):
    ConstantLight = "ConstantLight"
    MutableBreath = "MutableBreath"
    MutableHorseRace = "MutableHorseRace"
    Flow = "Flow"
    Rainbow = "Rainbow"
    Blink = "Blink"
    Off = "Off" # 清空DMX数据并不再更新


class LedColor(str, Enum):
    Red = "Red"
    RedDark = "RedDark"
    PinkPurple = "PinkPurple"
    Green = "Green"
    Blue = "Blue"
    BlueCobalt = "BlueCobalt"
    Yellow = "Yellow"
    ChargeYellow = "ChargeYellow"
    White = "White"
    Black = "Black"


def _trace_log(text: str, name: str) -> None:
    """Emit trace logs with channel name."""
    Trace.log(text, name=name)


def _is_src2000_platform() -> bool:
    """读取 /etc/srcname，包含 src2000 时启用旧 DMX 消息机制。"""
    try:
        with open("/etc/srcname", "r", encoding="utf-8") as f:
            return "src2000" in f.read().lower()
    except Exception:
        return False


IS_SRC2000_PLATFORM = _is_src2000_platform()

if IS_SRC2000_PLATFORM:
    ecal_rpc = None
    Led = None
else:
    from syspy.behavs import ecal_rpc
    from syspy.led import Led


def _get_ecal_rpc():
    if ecal_rpc is None:
        raise RuntimeError("BehavFactory eCAL RPC is unavailable in SRC2000")
    return ecal_rpc.get_ecal_rpc()


class ConfigParams:
    """脚本配置参数。"""

    resend_interval_sec = 2.0

    show_charging = True
    show_battery = True
    is_back_breath = False

    turn_pos = [4, 3, 1, 2]  # 左前/左后/右前/右后
    turn_num = [1, 1, 1, 1]  # 左前/左后/右前/右后
    light_total_num = 4

    @classmethod
    def init(cls) -> None:
        builder = script_param.builderConfig()
        with builder.GROUPS():
            with builder.GROUP(key="logic", name=_TR("Logic"), desc=_TR("LED logic config")):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    with builder.CHILD(key="resendIntervalSec", name=_TR("Resend Interval"), desc=_TR("Periodically resend the same LED command after this interval (seconds)")):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(2.0, min_value=0.0, max_value=30.0)
                        builder.SINGLESTEP(0.1)
                        builder.UNIT("s")
                    with builder.CHILD(key="showCharging", name=_TR("Show Charging"), desc=_TR("Whether to display the charging status")):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(True)
                    with builder.CHILD(key="showBattery", name=_TR("Show Battery"), desc=_TR("Whether to display the battery status when idle")):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(True)
                    with builder.CHILD(key="isBackBreath", name=_TR("Back Breath"), desc=_TR("Whether to show a white breathing effect when moving backward")):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(False)
                    if not IS_SRC2000_PLATFORM:
                        with builder.CHILD(key="lightTotalNum", name=_TR("Light Total Num"), desc=_TR("Total number of lights for the turn signal effect")):
                            builder.TYPE(ParamType.INT)
                            builder.DEFAULTVALUE(4)
            if not IS_SRC2000_PLATFORM:
                with builder.GROUP(key="turnPos", name=_TR("Turn Pos"), desc=_TR("Starting positions of turn signal lights (left-front, left-rear, right-front, right-rear)")):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        with builder.CHILD(key="turnPosLeftFront", name=_TR("Left Front"), desc=_TR("Starting position of the left-front turn signal")):
                            builder.TYPE(ParamType.INT)
                            builder.DEFAULTVALUE(4, min_value=1, max_value=256)
                        with builder.CHILD(key="turnPosLeftRear", name=_TR("Left Rear"), desc=_TR("Starting position of the left-rear turn signal")):
                            builder.TYPE(ParamType.INT)
                            builder.DEFAULTVALUE(3, min_value=1, max_value=256)
                        with builder.CHILD(key="turnPosRightFront", name=_TR("Right Front"), desc=_TR("Starting position of the right-front turn signal")):
                            builder.TYPE(ParamType.INT)
                            builder.DEFAULTVALUE(1, min_value=1, max_value=256)
                        with builder.CHILD(key="turnPosRightRear", name=_TR("Right Rear"), desc=_TR("Starting position of the right-rear turn signal")):
                            builder.TYPE(ParamType.INT)
                            builder.DEFAULTVALUE(2, min_value=1, max_value=256)
                with builder.GROUP(key="turnNum", name=_TR("Turn Num"), desc=_TR("Number of lights for each turn signal (left-front, left-rear, right-front, right-rear)")):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        with builder.CHILD(key="turnNumLeftFront", name=_TR("Left Front"), desc=_TR("Number of left-front turn signal lights")):
                            builder.TYPE(ParamType.INT)
                            builder.DEFAULTVALUE(1, min_value=0, max_value=256)
                        with builder.CHILD(key="turnNumLeftRear", name=_TR("Left Rear"), desc=_TR("Number of left-rear turn signal lights")):
                            builder.TYPE(ParamType.INT)
                            builder.DEFAULTVALUE(1, min_value=0, max_value=256)
                        with builder.CHILD(key="turnNumRightFront", name=_TR("Right Front"), desc=_TR("Number of right-front turn signal lights")):
                            builder.TYPE(ParamType.INT)
                            builder.DEFAULTVALUE(1, min_value=0, max_value=256)
                        with builder.CHILD(key="turnNumRightRear", name=_TR("Right Rear"), desc=_TR("Number of right-rear turn signal lights")):
                            builder.TYPE(ParamType.INT)
                            builder.DEFAULTVALUE(1, min_value=0, max_value=256)

        builder.save(merge=True)
        cls.reload()

    @classmethod
    def _load_src2000_turn_params(cls) -> bool:
        """SRC2000 从 LED 设备模型读取转向灯位置和数量：
            LED.<device_key>.deviceBrand.WST_SM16512PS_DMX512.turnLeftFrontPos 等
        （device_key 通过 RobotParam.getDeviceList("LED") 获取，一般为 LED-000）。
        """
        try:
            device_keys = RobotParam.getDeviceList("LED")
        except Exception as exc:
            _trace_log(
                f"src2000 turn params: getDeviceList('LED') failed err={exc}",
                name=f"{LOG_MODULE}.err",
            )
            return False
        if not device_keys:
            _trace_log("src2000 turn params: no LED device found", name=f"{LOG_MODULE}.err")
            return False

        device_key = device_keys[0]
        base = "deviceBrand.WST_SM16512PS_DMX512"

        def _read_int(name: str, default: int) -> int:
            try:
                return int(RobotParam.getDevice(device_key, f"{base}.{name}", default))
            except Exception:
                return default

        # 参数顺序与 turn_pos/turn_num 一致：左前/左后/右前/右后
        cls.turn_pos = [
            _read_int("turnLeftFrontPos", cls.turn_pos[0]),
            _read_int("turnLeftRearPos", cls.turn_pos[1]),
            _read_int("turnRightFrontPos", cls.turn_pos[2]),
            _read_int("turnRightRearPos", cls.turn_pos[3]),
        ]
        cls.turn_num = [
            _read_int("turnLeftFrontNum", cls.turn_num[0]),
            _read_int("turnLeftRearNum", cls.turn_num[1]),
            _read_int("turnRightFrontNum", cls.turn_num[2]),
            _read_int("turnRightRearNum", cls.turn_num[3]),
        ]
        cls.light_total_num = max(1, _read_int("lightTotalNum", cls.light_total_num))
        _trace_log(
            f"src2000 turn params loaded device={device_key} "
            f"turn_pos={cls.turn_pos} turn_num={cls.turn_num} "
            f"light_total_num={cls.light_total_num}",
            name=f"{LOG_MODULE}.cfg",
        )
        return True

    @classmethod
    def reload(cls) -> None:
        cfg = script_param.loadConfig()
        cls.resend_interval_sec = max(0.0, float(cfg.get("resendIntervalSec", 2.0)))
        cls.show_charging = bool(cfg.get("showCharging", True))
        cls.show_battery = bool(cfg.get("showBattery", True))
        cls.is_back_breath = bool(cfg.get("isBackBreath", False))
        cls.turn_pos = [4, 3, 1, 2]
        cls.turn_num = [1, 1, 1, 1]
        cls.light_total_num = 4
        if not IS_SRC2000_PLATFORM:
            cls.turn_pos = [
                int(cfg.get("turnPosLeftFront", 4)),
                int(cfg.get("turnPosLeftRear", 3)),
                int(cfg.get("turnPosRightFront", 1)),
                int(cfg.get("turnPosRightRear", 2)),
            ]
            cls.turn_num = [
                int(cfg.get("turnNumLeftFront", 1)),
                int(cfg.get("turnNumLeftRear", 1)),
                int(cfg.get("turnNumRightFront", 1)),
                int(cfg.get("turnNumRightRear", 1)),
            ]
            cls.light_total_num = max(1, int(cfg.get("lightTotalNum", 4)))
        else:
            cls._load_src2000_turn_params()

        _trace_log(
            "config reload "
            f"resend={cls.resend_interval_sec:.2f}s "
            f"legacy={IS_SRC2000_PLATFORM} charging={cls.show_charging} battery={cls.show_battery} "
            f"turn_pos={cls.turn_pos} turn_num={cls.turn_num} "
            f"light_total_num={cls.light_total_num} ok=True",
            name=f"{LOG_MODULE}",
        )

class RobotConfig:
    """电池低电阈值参数（来自 RobotParam）。"""

    low_battery_warning = "off"
    warning_percentage = -1.0
    automatic_shutdown = "off"
    shutdown_percentage = -1.0

    @classmethod
    def load_robot_config_params(cls):
        try:
            cls.low_battery_warning = str(
                RobotParam.getConfig("power", "lowBatteryManage.lowBatteryWarning", default="off")
            ).strip().lower()
            if cls.low_battery_warning == "on":
                cls.warning_percentage = float(
                    RobotParam.getConfig(
                        "power",
                        "lowBatteryManage.lowBatteryWarning.on.warningPercentage",
                        default=-1.0,
                    )
                )
            else:
                cls.warning_percentage = -1.0

            cls.automatic_shutdown = str(
                RobotParam.getConfig("power", "lowBatteryManage.automaticShutdown", default="off")
            ).strip().lower()
            if cls.automatic_shutdown == "on":
                cls.shutdown_percentage = float(
                    RobotParam.getConfig(
                        "power",
                        "lowBatteryManage.automaticShutdown.on.shutdownPercentage",
                        default=-1.0,
                    )
                )
            else:
                cls.shutdown_percentage = -1.0
        except Exception as exc:
            _trace_log(f"load_robot_config_params failed, err={exc}", name=f"{LOG_MODULE}.err")

        _trace_log(
            "robot config "
            f"{cls.low_battery_warning=} "
            f"{cls.warning_percentage=} "
            f"{cls.automatic_shutdown=} "
            f"{cls.shutdown_percentage=}",
            name=f"{LOG_MODULE}.cfg",
        )

def robot_config_change_callback(diff_map: Dict[str, Any]) -> None:
    """RobotParam 配置变更回调，动态更新 RobotConfig 参数。"""
    if not isinstance(diff_map, dict):
        return
    watched_keys = {
        "lowBatteryManage.lowBatteryWarning",
        "lowBatteryManage.lowBatteryWarning.on.warningPercentage",
        "lowBatteryManage.automaticShutdown",
        "lowBatteryManage.automaticShutdown.on.shutdownPercentage",
    }
    if watched_keys.isdisjoint(diff_map.keys()):
        return
    RobotConfig.load_robot_config_params()
    _trace_log(f"robot config changed diff={diff_map}", name=f"{LOG_MODULE}.cfg")

def script_config_callback() -> None:
    ConfigParams.reload()
    apply_ecal_rpc_config()

def apply_ecal_rpc_config(rpc=None) -> bool:
    if IS_SRC2000_PLATFORM:
        _trace_log("ecal rpc config skipped mode=legacy_message", name=f"{LOG_MODULE}.cfg")
        return True
    if rpc is None:
        rpc = _get_ecal_rpc()

    light_total_ok = rpc.call("setLightTotalNum", int(ConfigParams.light_total_num))
    dmx_enabled_ok = rpc.call("setLedDmxEnabled", True)
    ok = light_total_ok and dmx_enabled_ok
    _trace_log(
        "ecal rpc config applied "
        f"light_total_num={ConfigParams.light_total_num} "
        f"total_ok={light_total_ok} enable_ok={dmx_enabled_ok}",
        name=f"{LOG_MODULE}.cfg",
    )
    return ok

class Dmx512NativeBehav:
    STARTUP_CONFIG_RETRY_MAX = 10
    STARTUP_CONFIG_RETRY_INTERVAL_SEC = 0.2

    def __init__(self) -> None:
        self._use_legacy_dmx = IS_SRC2000_PLATFORM
        self._rpc = None if self._use_legacy_dmx else _get_ecal_rpc()
        self._legacy_dmx = LegacyDmxOutput() if self._use_legacy_dmx else None
        self._last_payload = ""
        self._last_send_time = 0.0
        self._last_log_signature = ""
        self._chassis_stop_rpc_warned = False
        _trace_log(
            f"dmx output mode={('legacy_message' if self._use_legacy_dmx else 'behav_factory')}",
            name=f"{LOG_MODULE}.cfg",
        )

    def _send_led(
        self,
        light_type: LedLightType,
        rgbw: LedColor,
        period: int = 1000,
        led_idx: Optional[List[int]] = None,
        reason: str = "",
    ) -> None:
        payload = {"light_type": light_type.value, "rgbw": rgbw.value, "period": int(period)}
        idx: List[int] = []
        if led_idx:
            idx = [int(v) for v in led_idx if int(v) > 0]
            if idx:
                payload["led_idx"] = idx

        payload_text = str(sorted(payload.items()))
        now = time.time()
        if payload_text == self._last_payload and ConfigParams.resend_interval_sec > 0:
            if now - self._last_send_time < ConfigParams.resend_interval_sec:
                return

        self._last_payload = payload_text
        self._last_send_time = now

        if self._use_legacy_dmx and self._legacy_dmx is not None:
            self._legacy_dmx.send(light_type, rgbw, period=int(period), led_idx=idx)
        else:
            Led.trySet(light_type.value, rgbw.value, int(period), idx)

        log_signature = f"{reason}|{payload_text}"
        if log_signature != self._last_log_signature:
            self._last_log_signature = log_signature
            led_idx_text = payload.get("led_idx", "ALL")
            _trace_log(
                "led command "
                f"reason={reason} "
                f"light_type={light_type.value} rgbw={rgbw.value} period={int(period)} "
                f"led_idx={led_idx_text}",
                name=f"{LOG_MODULE}.action",
            )

    def is_alarm(self) -> bool:
        return RobotError.existSystemError()

    def is_task_failed(self) -> bool:
        try:
            task_status = NavStatus.getTaskStatus()
        except Exception:
            return False
        if task_status is None:
            return False
        status_name = getattr(task_status, "name", "")
        if status_name:
            return str(status_name).lower() == "failed"
        if str(task_status).lower() == "failed":
            return True
        try:
            return int(task_status) == 5
        except Exception:
            return False

    @staticmethod
    def _mock_battery_percentage() -> float:
        """
        仿真环境下模拟电量周期变化：
        每120秒为一个周期，前60秒从100%线性降到5%，后60秒从5%线性升到100%。
        """
        cycle_sec = 120.0
        half_cycle = cycle_sec / 2.0
        phase = time.time() % cycle_sec
        if phase <= half_cycle:
            ratio = phase / half_cycle
            percentage = 1.0 - 0.95 * ratio
        else:
            ratio = (phase - half_cycle) / half_cycle
            percentage = 0.05 + 0.95 * ratio
        return max(0.0, min(1.0, percentage))

    @staticmethod
    @sim_only(on_sim=_mock_battery_percentage) #todo: 仿真读取方式该从消息读取
    def _get_battery_percentage() -> float:
        try:
            percentage = Battery.getPercentage()
        except Exception:
            percentage = 0.0
        if percentage is None:
            return 0.0
        out = float(percentage)
        if out < 0.0:
            return 0.0
        if out > 1.0:
            return 1.0
        return out

    @sim_only(on_sim=lambda *_args, **_kwargs: True)
    def _battery_exists(self, _percentage: float) -> bool:
        """通过 RPC getState 返回的 JSON 判断电池信息是否存在。"""
        if _percentage == 0.0:
            return False
        try:
            battery_keys = RobotParam.getDeviceList("Battery")
            return battery_keys is not None and len(battery_keys) > 0
        except Exception:
            return False

    @staticmethod
    def _battery_to_rgbw_name(percentage: float) -> LedColor:
        if percentage >= 0.70:
            return LedColor.Green
        if percentage >= 0.40:
            return LedColor.Yellow
        if percentage >= 0.20:
            return LedColor.ChargeYellow
        return LedColor.RedDark

    @staticmethod
    def _turn_to_led_idx(turn_left_or_right: int) -> List[int]:
        """按物理方向显式分组：d<2 为左侧(左前+左后)，d>=2 为右侧(右前+右后)。
        左右数量不一时也能正确分离。未知方向返回空列表(不闪)，
        避免错误地闪两侧。
        """
        left_idx: List[int] = []
        right_idx: List[int] = []
        max_idx = int(ConfigParams.light_total_num)
        for d, (pos, num) in enumerate(zip(ConfigParams.turn_pos, ConfigParams.turn_num)):
            pos_i = int(pos)
            num_i = int(num)
            if pos_i <= 0 or num_i <= 0:
                continue
            idxs = [i for i in range(pos_i, pos_i + num_i) if i <= max_idx]
            if d < 2:
                left_idx.extend(idxs)
            else:
                right_idx.extend(idxs)

        if turn_left_or_right == 1:
            return left_idx
        if turn_left_or_right == 2:
            return right_idx
        return []

    def handle_movement_effect(self, percentage: float) -> None:
        """处理运动状态的灯效。"""
        speeds = NavSpeed.getSpeeds()
        if not speeds:
            return
        vx, _, vw = speeds
        turn = NavStatus.getTurn(vx, vw)
        if turn == 0:
            if ConfigParams.is_back_breath and vx < 0:
                self._send_led(
                    LedLightType.MutableBreath,
                    LedColor.White,
                    period=3200,
                    reason="moving_rotation_back",
                )
            else:
                self._send_led(
                    LedLightType.MutableBreath,
                    LedColor.BlueCobalt,
                    period=3200,
                    reason="moving_rotation",
                )
            return

        if turn == 3:
            # 原地自转(左/右旋且无平移)：全部 LED 闪烁
            self._send_led(
                LedLightType.Blink,
                LedColor.Yellow,
                period=1000,
                reason="moving_spin_all",
            )
            return

        led_idx = self._turn_to_led_idx(turn)
        # 该侧未配置灯时不发送转向闪烁
        if not led_idx:
            return
        self._send_led(
            LedLightType.Blink,
            LedColor.Yellow,
            period=1000,
            led_idx=led_idx,
            reason="moving_turn",
        )

    def handle_battery_effects(self, percentage: float) -> None:
        """处理静止状态的电池相关灯效。"""
        if ConfigParams.show_charging and Battery.getIsCharging():
            self._send_led(
                LedLightType.MutableBreath,
                LedColor.ChargeYellow,
                period=3200,
                reason="charging",
            )
            return

        if (
            RobotConfig.automatic_shutdown == "on"
            and RobotConfig.shutdown_percentage >= 0
            and percentage * 100.0 <= RobotConfig.shutdown_percentage
        ):
            self._send_led(
                LedLightType.MutableBreath,
                LedColor.Red,
                period=3200,
                reason="shutdown_threshold",
            )
            return

        if (
            RobotConfig.low_battery_warning == "on"
            and RobotConfig.warning_percentage >= 0
            and percentage * 100.0 <= RobotConfig.warning_percentage
        ):
            self._send_led(
                LedLightType.MutableHorseRace,
                LedColor.RedDark,
                period=2000,
                reason="low_battery",
            )
            return

        if ConfigParams.show_battery:
            rgbw = self._battery_to_rgbw_name(percentage)
            self._send_led(
                LedLightType.ConstantLight,
                rgbw,
                period=1000,
                reason="battery_display",
            )
            return

        self._send_led(
            LedLightType.ConstantLight,
            LedColor.BlueCobalt,
            period=1000,
            reason="normal_idle",
        )

    def tick(self) -> None:
        """主逻辑函数，根据当前状态和电量决定灯效。"""
        percentage = self._get_battery_percentage()
        battery_exist = self._battery_exists(percentage)

        if self.is_alarm():
            self._send_led(
                LedLightType.Flow,
                LedColor.Red,
                period=625,
                reason="alarm",
            )
            return

        elif IS_SRC2000_PLATFORM and Controller.getEmc():
            self._send_led(
                LedLightType.Flow,
                LedColor.RedDark,
                period=10,
                reason="emc",
            )
            return

        elif IS_SRC2000_PLATFORM and NavStatus.getBlock():
            self._send_led(
                LedLightType.MutableHorseRace,
                LedColor.PinkPurple,
                period=1000,
                reason="blocked",
            )
            return

        try:
            chassis_stop = NavStatus.getChassisStop()
        except Exception:
            chassis_stop = True
            if not self._chassis_stop_rpc_warned:
                self._chassis_stop_rpc_warned = True
                _trace_log(
                    "chassis stop rpc unavailable, fallback chassis_stop=True",
                    name=f"{LOG_MODULE}.err",
                )
        else:
            if self._chassis_stop_rpc_warned:
                self._chassis_stop_rpc_warned = False
                _trace_log("chassis stop rpc recovered", name=LOG_MODULE)

        if not chassis_stop:
            if sum(ConfigParams.turn_num) <= 0:
                self._send_led(
                    LedLightType.MutableBreath,
                    LedColor.BlueCobalt,
                    period=3200,
                    reason="moving_no_turn_cfg",
                )
            else:
                self.handle_movement_effect(percentage)
            return
        # todo: 功能安全车型是否需要独立灯效
        if battery_exist:
            self.handle_battery_effects(percentage)
            return

        self._send_led(
            LedLightType.Rainbow,
            LedColor.Black,
            period=1000,
            reason="battery_error",
        )

    def run(self) -> None:
        rpc = self._rpc
        if not self._use_legacy_dmx:
            for attempt in range(1, self.STARTUP_CONFIG_RETRY_MAX + 1):
                connected = bool(rpc.is_connected()) if rpc is not None else False
                ecal_rpc_config_ok = apply_ecal_rpc_config(rpc=rpc)
                if connected and ecal_rpc_config_ok:
                    _trace_log(
                        f"startup ecal rpc config ready attempt={attempt}",
                        name=f"{LOG_MODULE}.cfg",
                    )
                    break
                if attempt < self.STARTUP_CONFIG_RETRY_MAX:
                    time.sleep(self.STARTUP_CONFIG_RETRY_INTERVAL_SEC)
            else:
                _trace_log(
                    "startup ecal rpc config not fully ready after retries",
                    name=f"{LOG_MODULE}.err",
                )
        _trace_log("task start script=behav_led", name=LOG_MODULE)
        try:
            while True:
                self.tick()
                time.sleep(1)
        finally:
            if not self._use_legacy_dmx:
                self._rpc.call("setLedDmxEnabled", False)
            _trace_log("task end script=behav_led", name=LOG_MODULE)

ConfigParams.init()

def main() -> None:

    Module.init()
    ScriptParam.setConfigChangeCallBack(script_config_callback)
    RobotParam.setConfigChangeCallBack(robot_config_change_callback)

    RobotConfig.load_robot_config_params()
    Dmx512NativeBehav().run()


if __name__ == "__main__":
    main()
