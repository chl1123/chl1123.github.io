#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DMX512 灯光逻辑（BehavFactory 新接口版）。

接口约束（与 BehavFactory.cpp 对齐）：
- light_type: ConstantLight/Steady/MutableBreath/MutableHorseRace/Flow/Rainbow/Blink/Uint/Off
- rgbw: Red/RedDark/PinkPurple/Green/Blue/BlueCobalt/Yellow/ChargeYellow/White/Off
todo: 增加灯效定制文档，说明各灯效类型和颜色的视觉效果，以及参数配置方式，包括src2000平台的兼容说明
状态优先级（从高到低）：
1) `dmx_test_flag`：`MutableBreath + Red`
2) 报警：`MutableBreath + Red`
3) 急停：`Flow + RedDark`
4) 阻挡：`MutableHorseRace + PinkPurple`
5) 运动：
   - 无转向：`MutableBreath + BlueCobalt`（后退且 `is_back_breath=True` 时用 `White`）
   - 转向：`Blink + Yellow`，并按 `turn_pos/turn_num` 生成 `led_idx`
6) 静止且有电池：
   - 充电：`MutableBreath + ChargeYellow`
   - 低于关机阈值：`MutableBreath + Red`
   - 低于低电阈值：`MutableHorseRace + RedDark`
   - 正常电量显示：`ConstantLight + (Green/Yellow/ChargeYellow/RedDark)`
7) 无电池：`Rainbow + Off`

日志策略：
- 仅在状态变化时打印 `robot_status`；
- 仅在灯效命令变化时打印结构化下发日志（含 `light_type/rgbw/period/led_idx` 与 `reason/context`）。
"""

import json
import time
from typing import Any, Dict, List, Optional, Tuple

from syspy import (
    Battery,
    Controller,
    Module,
    NavSpeed,
    NavStatus,
    RobotParam,
    ScriptParam,
    Trace,
    sim_only,
)
from syspy.behavs import _core
from syspy.behavs.led import led
from syspy.dmx512.dmx512_base import LightType, dmx512Base
from syspy.utils.param_server import ParamType

script_param = ScriptParam(__file__) # 以脚本文件名为命名空间加载配置参数，文件路径见 /opt/.data/rbk/resources/scripts/params/tasks/v3/standard/
LOG_MODULE = "LED"


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


def _rgbw_name_to_values(rgbw_name: str) -> Tuple[int, int, int, int]:
    table = {
        "Red": (255, 0, 0, 0),
        "RedDark": (170, 20, 0, 0),
        "PinkPurple": (30, 0, 30, 0),
        "Green": (0, 255, 0, 0),
        "Blue": (0, 0, 255, 0),
        "BlueCobalt": (0, 80, 164, 0),
        "Yellow": (255, 180, 0, 0),
        "ChargeYellow": (255, 120, 0, 0),
        "White": (255, 250, 250, 0),
        "Off": (0, 0, 0, 0),
    }
    return table.get(str(rgbw_name), (0, 0, 0, 0))


class LegacyDmxOutput:
    """复用 dmx512_pass 旧消息机制，兼容 SRC2000 平台。"""

    def __init__(self) -> None:
        self._dmx = dmx512Base()

    def send(
        self,
        light_type: str,
        rgbw: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        msg = self._dmx.createDmx512Message()
        context = context or {}

        battery_pct = float(context.get("battery_pct", 100.0))
        msg.battery = int(max(0.0, min(100.0, battery_pct)))

        # 旧消息机制中，电量显示优先使用 Battery 类型。
        reason = str(context.get("reason", ""))
        if reason == "battery_display":
            msg.type = LightType.Battery.value
            self._dmx.sendDmx512(msg)
            return

        type_map = {
            "ConstantLight": LightType.ConstantLight.value,
            "Steady": LightType.ConstantLight.value,
            "MutableBreath": LightType.MutableBreath.value,
            "MutableHorseRace": LightType.MutableHorseRace.value,
            "Flow": LightType.FlowCalculator.value,
            "Rainbow": LightType.Rainbow.value,
            "Blink": LightType.MutableBreath.value,
            "Uint": LightType.ConstantLight.value,
            "Off": LightType.ConstantLight.value,
        }
        msg.type = type_map.get(light_type, LightType.ConstantLight.value)

        if light_type == "MutableBreath" and rgbw == "ChargeYellow":
            msg.type = LightType.Charging.value

        turn = int(context.get("turn", 0))
        msg.turnLeftOrRight = turn if turn in (0, 1, 2, 3) else 0

        red, green, blue, white = _rgbw_name_to_values(rgbw)
        msg.colorRed = int(red)
        msg.colorGreen = int(green)
        msg.colorBlue = int(blue)
        msg.colorWhite = int(white)
        self._dmx.sendDmx512(msg)


class ConfigParams:
    """脚本配置参数。"""

    resend_interval_sec = 2.0

    dmx_test_flag = False
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
            with builder.GROUP(key="logic", name="Logic", desc="LED logic config"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    with builder.CHILD(key="resendIntervalSec", name="Resend Interval", desc="同一灯效周期性重发间隔(秒)"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(2.0, min_value=0.0, max_value=30.0)
                        builder.SINGLESTEP(0.1)
                        builder.UNIT("s")
                    with builder.CHILD(key="dmxTestFlag", name="DMX Test Flag", desc="开启后固定红色呼吸灯"):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(False)
                    with builder.CHILD(key="showCharging", name="Show Charging", desc="是否显示充电状态"):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(True)
                    with builder.CHILD(key="showBattery", name="Show Battery", desc="是否显示电量状态"):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(True)
                    with builder.CHILD(key="isBackBreath", name="Back Breath", desc="后退时显示白色呼吸"):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(False)
                    with builder.CHILD(key="lightTotalNum", name="Light Total Num", desc="灯条总数"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(4)

            with builder.GROUP(key="turnPos", name="Turn Pos", desc="左前/左后/右前/右后 转向灯起始位置"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    with builder.CHILD(key="turnPosLeftFront", name="Left Front", desc="左前"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(4, min_value=1, max_value=256)
                    with builder.CHILD(key="turnPosLeftRear", name="Left Rear", desc="左后"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(3, min_value=1, max_value=256)
                    with builder.CHILD(key="turnPosRightFront", name="Right Front", desc="右前"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(1, min_value=1, max_value=256)
                    with builder.CHILD(key="turnPosRightRear", name="Right Rear", desc="右后"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(2, min_value=1, max_value=256)

            with builder.GROUP(key="turnNum", name="Turn Num", desc="左前/左后/右前/右后 转向灯数量"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    with builder.CHILD(key="turnNumLeftFront", name="Left Front", desc="左前数量"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(1, min_value=0, max_value=256)
                    with builder.CHILD(key="turnNumLeftRear", name="Left Rear", desc="左后数量"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(1, min_value=0, max_value=256)
                    with builder.CHILD(key="turnNumRightFront", name="Right Front", desc="右前数量"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(1, min_value=0, max_value=256)
                    with builder.CHILD(key="turnNumRightRear", name="Right Rear", desc="右后数量"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(1, min_value=0, max_value=256)

        builder.save(merge=True)
        cls.reload()

    @classmethod
    def reload(cls) -> None:
        cfg = script_param.loadConfig()
        cls.resend_interval_sec = max(0.0, float(cfg.get("resendIntervalSec", 2.0)))
        cls.dmx_test_flag = bool(cfg.get("dmxTestFlag", False))
        cls.show_charging = bool(cfg.get("showCharging", True))
        cls.show_battery = bool(cfg.get("showBattery", True))
        cls.is_back_breath = bool(cfg.get("isBackBreath", False))

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

        _trace_log(
            "config reload "
            f"resend={cls.resend_interval_sec:.2f}s "
            f"test={cls.dmx_test_flag} charging={cls.show_charging} battery={cls.show_battery} "
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
            )
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
            )
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

    if "lowBatteryManage.lowBatteryWarning" in diff_map:
        RobotConfig.low_battery_warning = str(diff_map.get("lowBatteryManage.lowBatteryWarning") or "off")
        if RobotConfig.low_battery_warning != "on":
            RobotConfig.warning_percentage = -1.0

    if "lowBatteryManage.lowBatteryWarning.on.warningPercentage" in diff_map:
        RobotConfig.warning_percentage = float(diff_map.get("lowBatteryManage.lowBatteryWarning.on.warningPercentage"))

    if "lowBatteryManage.automaticShutdown" in diff_map:
        RobotConfig.automatic_shutdown = str(diff_map.get("lowBatteryManage.automaticShutdown") or "off")
        if RobotConfig.automatic_shutdown != "on":
            RobotConfig.shutdown_percentage = -1.0

    if "lowBatteryManage.automaticShutdown.on.shutdownPercentage" in diff_map:
        RobotConfig.shutdown_percentage = float(diff_map.get("lowBatteryManage.automaticShutdown.on.shutdownPercentage"))


def script_config_callback() -> None:
    ConfigParams.reload()
    ok = apply_runtime_config()
    if not ok:
        _trace_log("runtime config apply failed in script_config_callback", name=f"{LOG_MODULE}.err")


def apply_runtime_config() -> bool:
    rpc = _core.get_rpc()
    total_ok = rpc.call("setLightTotalNum", int(ConfigParams.light_total_num)) is not None
    enable_ok = rpc.call("setLedDmxEnabled", True) is not None
    ok = total_ok and enable_ok
    _trace_log(
        "runtime config applied "
        f"light_total_num={ConfigParams.light_total_num} "
        f"total_ok={total_ok} enable_ok={enable_ok}",
        name=f"{LOG_MODULE}.cfg",
    )
    return ok


class Dmx512NativeBehav:
    STARTUP_CONFIG_RETRY_MAX = 10 #脚本启动时 SDK的behav插件可能还没完全就绪，增加重试机制
    STARTUP_CONFIG_RETRY_INTERVAL_SEC = 0.2 # 每次重试间隔，单位秒

    def __init__(self) -> None:
        self.robot_status = ""
        self.pre_robot_status = ""
        self._rpc = _core.get_rpc()
        self._use_legacy_dmx = _is_src2000_platform()
        self._legacy_dmx = LegacyDmxOutput() if self._use_legacy_dmx else None
        self._last_payload = ""
        self._last_send_time = 0.0
        self._last_log_signature = ""
        self._last_turn = 0
        self._last_led_idx: List[int] = []
        self._chassis_stop_rpc_warned = False
        _trace_log(
            f"dmx output mode={('legacy_message' if self._use_legacy_dmx else 'behav_factory')}",
            name=f"{LOG_MODULE}.cfg",
        )

    def _send_led(
        self,
        light_type: str,
        rgbw: str,
        period: int = 1000,
        led_idx: Optional[List[int]] = None,
        reason: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        payload = {"light_type": light_type, "rgbw": rgbw, "period": int(period)}
        idx: List[int] = []
        if led_idx:
            idx = [int(v) for v in led_idx if int(v) > 0]
            if idx:
                payload["led_idx"] = idx

        payload_text = json.dumps(payload, sort_keys=True)
        now = time.time()
        if payload_text == self._last_payload and ConfigParams.resend_interval_sec > 0:
            if now - self._last_send_time < ConfigParams.resend_interval_sec:
                return

        self._last_payload = payload_text
        self._last_send_time = now

        context_send = dict(context or {})
        context_send["reason"] = reason
        if self._use_legacy_dmx and self._legacy_dmx is not None:
            self._legacy_dmx.send(light_type, rgbw, context=context_send)
        else:
            led.trySet(light_type, rgbw, int(period), idx)

        log_signature = f"{reason}|{payload_text}"
        if log_signature != self._last_log_signature:
            self._last_log_signature = log_signature
            led_idx_text = payload.get("led_idx", "ALL")
            context_text = json.dumps(context or {}, ensure_ascii=False, sort_keys=True)
            _trace_log(
                "led command "
                f"reason={reason} "
                f"light_type={light_type} rgbw={rgbw} period={int(period)} "
                f"led_idx={led_idx_text} context={context_text}",
                name=f"{LOG_MODULE}.action",
            )
            print(
                "led command "
                f"reason={reason} "
                f"light_type={light_type} rgbw={rgbw} period={int(period)} "
                f"led_idx={led_idx_text} context={context_text}"
            )

    def is_alarm(self) -> bool:
        try:
            ret = self._rpc.call("isAlarm")
            if isinstance(ret, bool):
                return ret
            return str(ret).strip().lower() == "true"
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
    def _battery_to_rgbw_name(percentage: float) -> str:
        if percentage >= 0.70:
            return "Green"
        if percentage >= 0.40:
            return "Yellow"
        if percentage >= 0.20:
            return "ChargeYellow"
        return "RedDark"


    @staticmethod
    def _turn_to_led_idx(turn_left_or_right: int) -> List[int]:
        all_idx: List[int] = []
        max_idx = int(ConfigParams.light_total_num)
        for pos, num in zip(ConfigParams.turn_pos, ConfigParams.turn_num):
            pos_i = int(pos)
            num_i = int(num)
            if pos_i <= 0 or num_i <= 0:
                continue
            all_idx.extend(i for i in range(pos_i, pos_i + num_i) if i <= max_idx)

        half = len(all_idx) // 2
        if turn_left_or_right == 1:
            return all_idx[:half]
        if turn_left_or_right == 2:
            return all_idx[half:]
        return all_idx

    def _set_status(self, status: str) -> None:
        self.robot_status = status
        if self.robot_status != self.pre_robot_status:
            _trace_log(
                f"status {self.pre_robot_status or 'INIT'} -> {self.robot_status}",
                name=LOG_MODULE,
            )
            self.pre_robot_status = self.robot_status

    def handle_movement_effect(self, percentage: float) -> None:
        """处理运动状态的灯效。"""
        vx, _, vw = NavSpeed.getSpeeds()
        turn = NavStatus.getTurn(vx, vw)
        if turn == 0:
            self._set_status("MovingRotation")
            if ConfigParams.is_back_breath and vx < 0:
                self._send_led(
                    "MutableBreath",
                    "White",
                    period=3200,
                    reason="moving_rotation_back",
                    context={
                        "status": self.robot_status,
                        "battery_pct": round(percentage * 100.0, 1),
                        "vx": round(vx, 3),
                        "vw": round(vw, 3),
                        "turn": turn,
                    },
                )
            else:
                self._send_led(
                    "MutableBreath",
                    "BlueCobalt",
                    period=3200,
                    reason="moving_rotation",
                    context={
                        "status": self.robot_status,
                        "battery_pct": round(percentage * 100.0, 1),
                        "vx": round(vx, 3),
                        "vw": round(vw, 3),
                        "turn": turn,
                    },
                )
            return

        self._set_status("MovingTurn")
        if turn != self._last_turn:
            self._last_turn = turn
            self._last_led_idx = self._turn_to_led_idx(turn)
        led_idx = self._last_led_idx if self._last_led_idx else None
        self._send_led(
            "Blink",
            "Yellow",
            period=1000,
            led_idx=led_idx,
            reason="moving_turn",
            context={
                "status": self.robot_status,
                "battery_pct": round(percentage * 100.0, 1),
                "vx": round(vx, 3),
                "vw": round(vw, 3),
                "turn": turn,
            },
        )

    def handle_battery_effects(self, percentage: float) -> None:
        """处理静止状态的电池相关灯效。"""
        if ConfigParams.show_charging and Battery.getIsCharging():
            self._set_status("Charging")
            self._send_led(
                "MutableBreath",
                "ChargeYellow",
                period=3200,
                reason="charging",
                context={"status": self.robot_status, "battery_pct": round(percentage * 100.0, 1)},
            )
            return

        if (
            RobotConfig.automatic_shutdown == "on"
            and RobotConfig.shutdown_percentage >= 0
            and percentage * 100.0 <= RobotConfig.shutdown_percentage
        ):
            self._set_status("Alarm")
            self._send_led(
                "MutableBreath",
                "Red",
                period=3200,
                reason="shutdown_threshold",
                context={
                    "status": self.robot_status,
                    "battery_pct": round(percentage * 100.0, 1),
                    "shutdown_pct": RobotConfig.shutdown_percentage,
                },
            )
            return

        if (
            RobotConfig.low_battery_warning == "on"
            and RobotConfig.warning_percentage >= 0
            and percentage * 100.0 <= RobotConfig.warning_percentage
        ):
            self._set_status("LowBattery")
            self._send_led(
                "MutableHorseRace",
                "RedDark",
                period=2000,
                reason="low_battery",
                context={
                    "status": self.robot_status,
                    "battery_pct": round(percentage * 100.0, 1),
                    "warning_pct": RobotConfig.warning_percentage,
                },
            )
            return

        if ConfigParams.show_battery:
            self._set_status("Battery")
            rgbw = self._battery_to_rgbw_name(percentage)
            self._send_led(
                "ConstantLight",
                rgbw,
                period=1000,
                reason="battery_display",
                context={"status": self.robot_status, "battery_pct": round(percentage * 100.0, 1)},
            )
            return

        self._set_status("Normal")
        self._send_led(
            "ConstantLight",
            "BlueCobalt",
            period=1000,
            reason="normal_idle",
            context={"status": self.robot_status, "battery_pct": round(percentage * 100.0, 1)},
        )

    def tick(self) -> None:
        """主逻辑函数，根据当前状态和电量决定灯效。"""
        percentage = self._get_battery_percentage()
        battery_exist = self._battery_exists(percentage)

        if ConfigParams.dmx_test_flag:
            self._set_status("DmxTest")
            self._send_led(
                "MutableBreath",
                "Red",
                period=3200,
                reason="dmx_test",
                context={"status": self.robot_status, "battery_pct": round(percentage * 100.0, 1)},
            )
            return
        elif self.is_alarm():
            self._set_status("Alarm")
            self._send_led(
                "MutableBreath",
                "Red",
                period=3200,
                reason="alarm",
                context={"status": self.robot_status, "battery_pct": round(percentage * 100.0, 1)},
            )
            return
        elif Controller.getEmc():
            self._set_status("EStop")
            self._send_led(
                "Flow",
                "RedDark",
                period=10,
                reason="emc",
                context={"status": self.robot_status, "battery_pct": round(percentage * 100.0, 1)},
            )
            return
        elif NavStatus.getBlock():
            self._set_status("Blocked")
            self._send_led(
                "MutableHorseRace",
                "PinkPurple",
                period=1000,
                reason="blocked",
                context={"status": self.robot_status, "battery_pct": round(percentage * 100.0, 1)},
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
                self._set_status("Moving")
                self._send_led(
                    "MutableBreath",
                    "BlueCobalt",
                    period=3200,
                    reason="moving_no_turn_cfg",
                    context={"status": self.robot_status, "battery_pct": round(percentage * 100.0, 1)},
                )
            else:
                self.handle_movement_effect(percentage)
            return
        # todo: 功能安全车型是否需要独立灯效
        if battery_exist:
            self.handle_battery_effects(percentage)
            return

        self._set_status("NoBattery")
        self._send_led(
            "Rainbow",
            "Off",
            period=1000,
            reason="no_battery",
            context={"status": self.robot_status, "battery_pct": round(percentage * 100.0, 1)},
        )

    def run(self) -> None:
        rpc = _core.get_rpc()
        for attempt in range(1, self.STARTUP_CONFIG_RETRY_MAX + 1):
            is_connected = getattr(rpc, "is_connected", None)
            if callable(is_connected):
                connected = bool(is_connected())
            else:
                connected = True
            ok = apply_runtime_config()
            if connected and ok:
                _trace_log(
                    f"startup runtime config ready attempt={attempt}",
                    name=f"{LOG_MODULE}.cfg",
                )
                break
            if attempt < self.STARTUP_CONFIG_RETRY_MAX:
                time.sleep(self.STARTUP_CONFIG_RETRY_INTERVAL_SEC)
        else:
            _trace_log(
                "startup runtime config not fully ready after retries",
                name=f"{LOG_MODULE}.err",
            )
        _trace_log("task start script=behav_led", name=LOG_MODULE)
        try:
            while True:
                self.tick()
                time.sleep(1)
        finally:
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
