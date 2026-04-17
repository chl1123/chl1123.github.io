#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DMX512 灯光逻辑（BehavFactory 新接口版）。

接口约束（与 BehavFactory.cpp 对齐）：
- light_type: ConstantLight/Steady/MutableBreath/MutableHorseRace/Flow/Rainbow/Blink/Uint/Off
- rgbw: Red/RedDark/PinkPurple/Green/Blue/BlueCobalt/Yellow/ChargeYellow/White/Off

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

import atexit
import json
import signal
import time
from typing import Any, Dict, List, Optional, Tuple

from syspy import (
    Abnormal,
    Battery,
    Controller,
    Module,
    NavSpeed,
    NavStatus,
    RobotParam,
    ScriptParam,
    Trace,
)
from syspy.behavs import _core
from syspy.behavs.led import led
from syspy.utils.param_server import ParamType

script_param = ScriptParam(__file__)
LED_CMD_TOPIC = "/rbk/behav/action/led"
_STOP = False


def _safe_trace(text: str) -> None:
    try:
        Trace.log(text)
    except Exception:
        print(text)


def _request_stop(_signum, _frame) -> None:
    global _STOP
    _STOP = True
    _safe_trace("[behav_led] stop requested")


def _to_float(value: Any, default: float) -> float:
    try:
        out = float(value)
    except Exception:
        return default
    return out


def _to_int(value: Any, default: int) -> int:
    try:
        out = int(value)
    except Exception:
        return default
    return out


def _to_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        text = value.strip().lower()
        if text in ("1", "true", "yes", "on"):
            return True
        if text in ("0", "false", "no", "off"):
            return False
    try:
        return bool(value)
    except Exception:
        return default


class ConfigParams:
    """脚本配置参数。"""

    update_interval_sec = 0.1
    resend_interval_sec = 2.0

    dmx_test_flag = False
    show_charging = True
    show_battery = True
    is_back_breath = False

    turn_pos = [4, 3, 1, 2]  # 左前/左后/右前/右后
    turn_num = [1, 1, 1, 1]  # 左前/左后/右前/右后

    @classmethod
    def init(cls) -> None:
        builder = script_param.builderConfig()
        with builder.GROUPS():
            with builder.GROUP(key="logic", name="Logic", desc="LED logic config"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    with builder.CHILD(key="updateIntervalSec", name="Update Interval", desc="状态刷新周期(秒)"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.1, min_value=0.02, max_value=2.0)
                        builder.SINGLESTEP(0.01)
                        builder.UNIT("s")
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
        cls.update_interval_sec = max(0.02, _to_float(cfg.get("updateIntervalSec"), 0.1))
        cls.resend_interval_sec = max(0.0, _to_float(cfg.get("resendIntervalSec"), 2.0))
        cls.dmx_test_flag = _to_bool(cfg.get("dmxTestFlag"), False)
        cls.show_charging = _to_bool(cfg.get("showCharging"), True)
        cls.show_battery = _to_bool(cfg.get("showBattery"), True)
        cls.is_back_breath = _to_bool(cfg.get("isBackBreath"), False)

        cls.turn_pos = [
            _to_int(cfg.get("turnPosLeftFront"), 4),
            _to_int(cfg.get("turnPosLeftRear"), 3),
            _to_int(cfg.get("turnPosRightFront"), 1),
            _to_int(cfg.get("turnPosRightRear"), 2),
        ]
        cls.turn_num = [
            _to_int(cfg.get("turnNumLeftFront"), 1),
            _to_int(cfg.get("turnNumLeftRear"), 1),
            _to_int(cfg.get("turnNumRightFront"), 1),
            _to_int(cfg.get("turnNumRightRear"), 1),
        ]

        _safe_trace(
            "[behav_led] config reload: "
            f"update={cls.update_interval_sec:.2f}s resend={cls.resend_interval_sec:.2f}s "
            f"test={cls.dmx_test_flag} charging={cls.show_charging} battery={cls.show_battery} "
            f"back_breath={cls.is_back_breath} turn_pos={cls.turn_pos} turn_num={cls.turn_num}"
        )


class RobotConfig:
    """电池低电阈值参数（来自 RobotParam）。"""

    error_percentage = 20.0
    automatic_shutdown = "OFF"
    shutdown_percentage = -1.0


def load_robot_config_params() -> None:
    try:
        RobotConfig.error_percentage = _to_float(
            RobotParam.getConfig("power", "lowBatteryManage.errorPercentage", default=20.0),
            20.0,
        )
        RobotConfig.automatic_shutdown = str(
            RobotParam.getConfig("power", "lowBatteryManage.automaticShutdown", default="OFF") or "OFF"
        )
        if RobotConfig.automatic_shutdown == "ON":
            RobotConfig.shutdown_percentage = _to_float(
                RobotParam.getDevice(
                    "power",
                    "lowBatteryManage.automaticShutdown.on.shutdownPercentage",
                    default=-1.0,
                ),
                -1.0,
            )
        else:
            RobotConfig.shutdown_percentage = -1.0
    except Exception as exc:
        _safe_trace(f"[behav_led] load_robot_config_params failed: {exc}")

    _safe_trace(
        "[behav_led] robot config: "
        f"error={RobotConfig.error_percentage} "
        f"auto_shutdown={RobotConfig.automatic_shutdown} "
        f"shutdown={RobotConfig.shutdown_percentage}"
    )


def robot_config_change_callback(diff_map: Dict[str, Any]) -> None:
    if not isinstance(diff_map, dict):
        return

    if "lowBatteryManage.errorPercentage" in diff_map:
        RobotConfig.error_percentage = _to_float(diff_map.get("lowBatteryManage.errorPercentage"), RobotConfig.error_percentage)

    if "lowBatteryManage.automaticShutdown" in diff_map:
        RobotConfig.automatic_shutdown = str(diff_map.get("lowBatteryManage.automaticShutdown") or "OFF")
        if RobotConfig.automatic_shutdown != "ON":
            RobotConfig.shutdown_percentage = -1.0

    if "lowBatteryManage.automaticShutdown.on.shutdownPercentage" in diff_map:
        RobotConfig.shutdown_percentage = _to_float(
            diff_map.get("lowBatteryManage.automaticShutdown.on.shutdownPercentage"),
            RobotConfig.shutdown_percentage,
        )


def script_config_callback() -> None:
    ConfigParams.reload()


class LedSender:
    """多路径下发 LED 命令（topic + tryLed + setAction + Python 封装）。"""

    def __init__(self) -> None:
        self._topic_pub = None
        self._topic_send = None
        self._last_payload = ""
        self._last_send_time = 0.0
        self._last_log_signature = ""

        self._setup_topic_publisher()
        atexit.register(self.close)

    def _setup_topic_publisher(self) -> bool:
        try:
            import ecal.nanobind_core as ecal_core
        except Exception:
            return False

        try:
            if not ecal_core.ok():
                cfg = ecal_core.Configuration()
                cfg.registration.local.transport_type = ecal_core.LocalTransportType.SHM
                ecal_core.initialize(cfg, "behav_led_led_pub")
        except Exception:
            return False

        try:
            from ecal.msg.string.core import Publisher as StringPublisher

            pub_cfg = ecal_core.PublisherConfiguration()
            pub_cfg.layer.shm.enable = True
            pub_cfg.layer.udp.enable = False
            pub_cfg.layer.tcp.enable = False
            self._topic_pub = StringPublisher(LED_CMD_TOPIC, pub_cfg)
        except Exception:
            return False

        send_fn = None
        for name in ("send", "Send", "publish", "Publish"):
            fn = getattr(self._topic_pub, name, None)
            if callable(fn):
                send_fn = fn
                break
        if send_fn is None:
            self._topic_pub = None
            return False

        self._topic_send = send_fn
        _safe_trace(f"[behav_led] topic publisher ready: {LED_CMD_TOPIC}")
        return True

    def close(self) -> None:
        if self._topic_pub is not None:
            try:
                if hasattr(self._topic_pub, "destroy"):
                    self._topic_pub.destroy()
            except Exception:
                pass
        self._topic_pub = None
        self._topic_send = None

    def send(
        self,
        light_type: str,
        rgbw: str,
        period: int = 1000,
        led_idx: Optional[List[int]] = None,
        reason: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        payload = {"light_type": light_type, "rgbw": rgbw, "period": int(period)}
        if led_idx:
            payload["led_idx"] = [int(v) for v in led_idx if int(v) > 0]

        payload_text = json.dumps(payload, sort_keys=True)
        now = time.time()
        if payload_text == self._last_payload and ConfigParams.resend_interval_sec > 0:
            if now - self._last_send_time < ConfigParams.resend_interval_sec:
                return

        self._last_payload = payload_text
        self._last_send_time = now

        # 0) Topic
        if self._topic_send is not None:
            try:
                self._topic_send(payload_text)
            except Exception:
                pass

        # 1) tryLed
        rpc = _core.get_rpc()
        idx = payload.get("led_idx", [])
        try:
            rpc.call("tryLed", light_type, rgbw, int(period), idx)
        except Exception:
            pass

        # 2) setAction
        try:
            rpc.set_action("led", payload)
        except Exception:
            pass

        # 3) Python 封装 fallback（兼容签名差异）
        try:
            if idx:
                led.trySet(light_type, rgbw, int(period), idx)
            else:
                led.trySet(light_type, rgbw, int(period))
        except TypeError:
            try:
                led.trySet(light_type, rgbw, int(period))
            except Exception:
                pass
        except Exception:
            pass

        log_signature = f"{reason}|{payload_text}"
        if log_signature != self._last_log_signature:
            self._last_log_signature = log_signature
            led_idx_text = payload.get("led_idx", "ALL")
            context_text = json.dumps(context or {}, ensure_ascii=False, sort_keys=True)
            _safe_trace(
                "[behav_led] led_cmd "
                f"reason={reason} "
                f"light_type={light_type} rgbw={rgbw} period={int(period)} "
                f"led_idx={led_idx_text} context={context_text}\n"
            )


class Dmx512NativeBehav:
    def __init__(self) -> None:
        self.robot_status = ""
        self.pre_robot_status = ""
        self.sender = LedSender()
        self._last_turn = 0
        self._last_led_idx: List[int] = []

    @staticmethod
    def is_alarm() -> bool:
        try:
            ret = _core.get_rpc().call("isAlarm")
            if isinstance(ret, bool):
                return ret
            return str(ret).strip().lower() == "true"
        except Exception:
            return False


    @staticmethod
    def _get_battery_percentage() -> float:
        try:
            percentage = Battery.getPercentage()
        except Exception:
            percentage = 0.0
        if percentage is None:
            return 0.0
        out = _to_float(percentage, 0.0)
        if out < 0.0:
            return 0.0
        if out > 1.0:
            return 1.0
        return out

    @staticmethod
    def _battery_exists(percentage: float) -> bool:
        if int(percentage * 100.0) == 0:
            return False
        try:
            if bool(Abnormal.exists(57040)):
                return False
        except Exception:
            pass
        return True

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
    def _safe_bool_call(func, default: bool = False) -> bool:
        try:
            value = func()
        except Exception:
            return default
        return _to_bool(value, default)

    @staticmethod
    def _safe_speeds() -> Tuple[float, float, float]:
        try:
            vx, vy, vw = NavSpeed.getSpeeds()
            return _to_float(vx, 0.0), _to_float(vy, 0.0), _to_float(vw, 0.0)
        except Exception:
            return 0.0, 0.0, 0.0

    @staticmethod
    def _safe_turn(vx: float, vw: float) -> int:
        try:
            turn = _to_int(NavStatus.getTurn(vx, vw), 0)
        except Exception:
            turn = 0
        # NavStatus.getTurn 约定：
        # 0=无转向, 1=左转, 2=右转, 3=原地旋转
        # turn=3 时应触发转向灯（通常左右同时闪烁），不能降级为 0。
        if turn not in (0, 1, 2, 3):
            return 0
        return turn

    @staticmethod
    def _turn_to_led_idx(turn_left_or_right: int) -> List[int]:
        all_idx: List[int] = []
        for pos, num in zip(ConfigParams.turn_pos, ConfigParams.turn_num):
            pos_i = _to_int(pos, 0)
            num_i = _to_int(num, 0)
            if pos_i <= 0 or num_i <= 0:
                continue
            all_idx.extend(range(pos_i, pos_i + num_i))

        half = len(all_idx) // 2
        if turn_left_or_right == 1:
            return all_idx[:half]
        if turn_left_or_right == 2:
            return all_idx[half:]
        return all_idx

    def _set_status(self, status: str) -> None:
        self.robot_status = status
        if self.robot_status != self.pre_robot_status:
            _safe_trace(f"[behav_led] robot_status={self.robot_status}")
            self.pre_robot_status = self.robot_status

    def handle_movement_effect(self, percentage: float) -> None:
        vx, _, vw = self._safe_speeds()
        turn = self._safe_turn(vx, vw)
        if turn == 0:
            self._set_status("MovingRotation")
            if ConfigParams.is_back_breath and vx < 0:
                self.sender.send(
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
                self.sender.send(
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
        self.sender.send(
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
        if ConfigParams.show_charging and self._safe_bool_call(Battery.getIsCharging, default=False):
            self._set_status("Charging")
            self.sender.send(
                "MutableBreath",
                "ChargeYellow",
                period=3200,
                reason="charging",
                context={"status": self.robot_status, "battery_pct": round(percentage * 100.0, 1)},
            )
            return

        if (
            RobotConfig.automatic_shutdown == "ON"
            and RobotConfig.shutdown_percentage >= 0
            and percentage * 100.0 <= RobotConfig.shutdown_percentage
        ):
            self._set_status("Alarm")
            self.sender.send(
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

        if percentage * 100.0 <= RobotConfig.error_percentage:
            self._set_status("LowBattery")
            self.sender.send(
                "MutableHorseRace",
                "RedDark",
                period=2000,
                reason="low_battery",
                context={
                    "status": self.robot_status,
                    "battery_pct": round(percentage * 100.0, 1),
                    "error_pct": RobotConfig.error_percentage,
                },
            )
            return

        if ConfigParams.show_battery:
            self._set_status("Battery")
            rgbw = self._battery_to_rgbw_name(percentage)
            self.sender.send(
                "ConstantLight",
                rgbw,
                period=1000,
                reason="battery_display",
                context={"status": self.robot_status, "battery_pct": round(percentage * 100.0, 1)},
            )
            return

        self._set_status("Normal")
        self.sender.send(
            "ConstantLight",
            "BlueCobalt",
            period=1000,
            reason="normal_idle",
            context={"status": self.robot_status, "battery_pct": round(percentage * 100.0, 1)},
        )

    def tick(self) -> None:
        percentage = self._get_battery_percentage()
        battery_exist = self._battery_exists(percentage)

        if ConfigParams.dmx_test_flag:
            self._set_status("DmxTest")
            self.sender.send(
                "MutableBreath",
                "Red",
                period=3200,
                reason="dmx_test",
                context={"status": self.robot_status, "battery_pct": round(percentage * 100.0, 1)},
            )
            return

        if self.is_alarm():
            self._set_status("Alarm")
            self.sender.send(
                "MutableBreath",
                "Red",
                period=3200,
                reason="alarm",
                context={"status": self.robot_status, "battery_pct": round(percentage * 100.0, 1)},
            )
            return

        if self._safe_bool_call(Controller.getEmc, default=False):
            self._set_status("EStop")
            self.sender.send(
                "Flow",
                "RedDark",
                period=10,
                reason="emc",
                context={"status": self.robot_status, "battery_pct": round(percentage * 100.0, 1)},
            )
            return

        if self._safe_bool_call(NavStatus.getBlock, default=False):
            self._set_status("Blocked")
            self.sender.send(
                "MutableHorseRace",
                "PinkPurple",
                period=1000,
                reason="blocked",
                context={"status": self.robot_status, "battery_pct": round(percentage * 100.0, 1)},
            )
            return

        if not self._safe_bool_call(NavStatus.getChassisStop, default=True):
            if sum(_to_int(v, 0) for v in ConfigParams.turn_num) <= 0:
                self._set_status("Moving")
                self.sender.send(
                    "MutableBreath",
                    "BlueCobalt",
                    period=3200,
                    reason="moving_no_turn_cfg",
                    context={"status": self.robot_status, "battery_pct": round(percentage * 100.0, 1)},
                )
            else:
                self.handle_movement_effect(percentage)
            return

        if battery_exist:
            self.handle_battery_effects(percentage)
            return

        self._set_status("NoBattery")
        self.sender.send(
            "Rainbow",
            "Off",
            period=1000,
            reason="no_battery",
            context={"status": self.robot_status, "battery_pct": round(percentage * 100.0, 1)},
        )

    def run(self) -> None:
        _safe_trace("[behav_led] start running")
        while not _STOP:
            self.tick()
            sleep_left = ConfigParams.update_interval_sec
            while sleep_left > 0 and not _STOP:
                step = 0.05 if sleep_left > 0.05 else sleep_left
                time.sleep(step)
                sleep_left -= step

        self.sender.send(
            "Off",
            "Off",
            period=0,
            reason="script_stop",
            context={"status": "Stop"},
        )
        self.sender.close()
        _safe_trace("[behav_led] stopped")


ConfigParams.init()

def main() -> None:
    for sig_name in ("SIGINT", "SIGTERM"):
        sig = getattr(signal, sig_name, None)
        if sig:
            try:
                signal.signal(sig, _request_stop)
            except Exception:
                pass

    Module.init()

    ScriptParam.setConfigChangeCallBack(script_config_callback)
    RobotParam.setConfigChangeCallBack(robot_config_change_callback)

    load_robot_config_params()
    Dmx512NativeBehav().run()


if __name__ == "__main__":
    main()
