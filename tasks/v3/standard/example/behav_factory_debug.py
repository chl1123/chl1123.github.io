# -*- coding: utf-8 -*-
# @Date: 2026/04/02
# @Project: BehavFactory Debug (clean version)

import json
import time
from typing import Any, Dict

from syspy import Module, ModuleBase, ScriptStatus, ScriptParam, Trace, Abnormal
from syspy.lib.module import SafeMoveStatus
from syspy.behavs import led, tricolor, audio, trigger, state
from syspy.utils.param_server import ParamType


start_time = time.time()
script_param = ScriptParam(__file__)

def log(msg: str) -> None:
    text = f"[behav_factory_debug] {msg}"
    try:
        Trace.log(text)
    except Exception:
        print(f"log: {text}")


def _to_int(value: Any, default: int, minimum: int | None = None, maximum: int | None = None) -> int:
    try:
        out = int(value)
    except Exception:
        out = default
    if minimum is not None and out < minimum:
        out = minimum
    if maximum is not None and out > maximum:
        out = maximum
    return out


def _to_float(value: Any, default: float, minimum: float | None = None, maximum: float | None = None) -> float:
    try:
        out = float(value)
    except Exception:
        out = default
    if minimum is not None and out < minimum:
        out = minimum
    if maximum is not None and out > maximum:
        out = maximum
    return out


class ConfigParams:
    report_state_raw = True
    report_rpc_json = True
    state_preview_chars = 600
    settle_sec = 0.05
    query_state_after = True

    @classmethod
    def init(cls) -> None:
        builder = script_param.builderConfig()
        with builder.GROUPS():
            with builder.GROUP(key="debug", name="Debug", desc="BehavFactory debug config"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    with builder.CHILD(key="reportStateRaw", name="Report State Raw", desc="是否上报 state 原始预览"):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(True)

                    with builder.CHILD(key="reportRpcJson", name="Report RPC JSON", desc="是否打印 RPC 请求预览"):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(True)

                    with builder.CHILD(key="statePreviewChars", name="State Preview Chars", desc="state 原始预览长度"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(600, min_value=100, max_value=10000)

                    with builder.CHILD(key="settleSec", name="Settle Seconds", desc="行为执行后等待时间"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.05, min_value=0.0, max_value=3.0)
                        builder.SINGLESTEP(0.01)
                        builder.UNIT("s")

                    with builder.CHILD(key="queryStateAfter", name="Query State After", desc="行为执行后回读状态"):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(True)

        builder.save(merge=True)
        cls.load()

    @classmethod
    def load(cls) -> None:
        cfg = script_param.loadConfig()
        cls.report_state_raw = bool(cfg.get("reportStateRaw", True))
        cls.report_rpc_json = bool(cfg.get("reportRpcJson", True))
        cls.state_preview_chars = _to_int(cfg.get("statePreviewChars", 600), 600, minimum=100, maximum=10000)
        cls.settle_sec = _to_float(cfg.get("settleSec", 0.05), 0.05, minimum=0.0, maximum=3.0)
        cls.query_state_after = bool(cfg.get("queryStateAfter", True))
        log(
            "config loaded: "
            f"report_state_raw={cls.report_state_raw}, "
            f"report_rpc_json={cls.report_rpc_json}, "
            f"state_preview_chars={cls.state_preview_chars}, "
            f"settle_sec={cls.settle_sec}, "
            f"query_state_after={cls.query_state_after}"
        )


ConfigParams.init()


def script_config_callback() -> None:
    log("script_config_callback()")
    ConfigParams.load()


class InputParams:
    builder = script_param.builderInput()

    with builder.GROUPS():
        with builder.CHILD(key="action", name="Action", desc="Behav action"):
            builder.TYPE(ParamType.STRING_COMBO_LIST)
            builder.REQUIRED(True)
            builder.DEFAULTVALUE("LedSet")
            with builder.CHILDREN():
                with builder.CHILD(key="LedSet", name="LedSet", desc="Set LED"):
                    builder.TYPE(ParamType.STRING)
                with builder.CHILD(key="LedOff", name="LedOff", desc="Turn off LED"):
                    builder.TYPE(ParamType.STRING)
                with builder.CHILD(key="TricolorSet", name="TricolorSet", desc="Set tricolor"):
                    builder.TYPE(ParamType.STRING)
                with builder.CHILD(key="TricolorOff", name="TricolorOff", desc="Turn off tricolor"):
                    builder.TYPE(ParamType.STRING)
                with builder.CHILD(key="AudioPlay", name="AudioPlay", desc="Play audio"):
                    builder.TYPE(ParamType.STRING)
                with builder.CHILD(key="AudioStop", name="AudioStop", desc="Stop audio"):
                    builder.TYPE(ParamType.STRING)
                with builder.CHILD(key="TriggerSet", name="TriggerSet", desc="Set trigger"):
                    builder.TYPE(ParamType.STRING)
                with builder.CHILD(key="GetState", name="GetState", desc="Read state only"):
                    builder.TYPE(ParamType.STRING)

        with builder.CHILD(key="color", name="Color", desc="LED color"):
            builder.TYPE(ParamType.STRING_COMBO_LIST)
            builder.DEFAULTVALUE("blue")
            with builder.CHILDREN():
                with builder.CHILD(key="red", name="red", desc="red"):
                    builder.TYPE(ParamType.STRING)
                with builder.CHILD(key="yellow", name="yellow", desc="yellow"):
                    builder.TYPE(ParamType.STRING)
                with builder.CHILD(key="green", name="green", desc="green"):
                    builder.TYPE(ParamType.STRING)
                with builder.CHILD(key="blue", name="blue", desc="blue"):
                    builder.TYPE(ParamType.STRING)
                with builder.CHILD(key="off", name="off", desc="off"):
                    builder.TYPE(ParamType.STRING)

        with builder.CHILD(key="pattern", name="Pattern", desc="LED pattern"):
            builder.TYPE(ParamType.STRING_COMBO_LIST)
            builder.DEFAULTVALUE("steady")
            with builder.CHILDREN():
                with builder.CHILD(key="steady", name="steady", desc="steady"):
                    builder.TYPE(ParamType.STRING)
                with builder.CHILD(key="blink", name="blink", desc="blink"):
                    builder.TYPE(ParamType.STRING)
                with builder.CHILD(key="breath", name="breath", desc="breath"):
                    builder.TYPE(ParamType.STRING)

        with builder.CHILD(key="red", name="Tri Red", desc="Tricolor red"):
            builder.TYPE(ParamType.BOOL)
            builder.DEFAULTVALUE(False)
        with builder.CHILD(key="yellow", name="Tri Yellow", desc="Tricolor yellow"):
            builder.TYPE(ParamType.BOOL)
            builder.DEFAULTVALUE(False)
        with builder.CHILD(key="green", name="Tri Green", desc="Tricolor green"):
            builder.TYPE(ParamType.BOOL)
            builder.DEFAULTVALUE(True)

        with builder.CHILD(key="sound_id", name="Sound ID", desc="Audio file name"):
            builder.TYPE(ParamType.STRING)
            builder.DEFAULTVALUE("alarm.wav")
        with builder.CHILD(key="loop", name="Audio Loop", desc="Audio loop"):
            builder.TYPE(ParamType.BOOL)
            builder.DEFAULTVALUE(False)

        with builder.CHILD(key="key", name="Trigger Key", desc="Trigger key"):
            builder.TYPE(ParamType.STRING)
            builder.DEFAULTVALUE("io_out_1")
        with builder.CHILD(key="value", name="Trigger Value", desc="Trigger value"):
            builder.TYPE(ParamType.BOOL)
            builder.DEFAULTVALUE(True)

        with builder.CHILD(key="repeat", name="Repeat", desc="Repeat count"):
            builder.TYPE(ParamType.INT)
            builder.DEFAULTVALUE(1, min_value=1, max_value=1000)
        with builder.CHILD(key="intervalSec", name="Interval Sec", desc="Interval between repeats"):
            builder.TYPE(ParamType.FLOAT)
            builder.DEFAULTVALUE(0.2, min_value=0.0, max_value=10.0)
            builder.SINGLESTEP(0.05)
            builder.UNIT("s")

    builder.save(merge=False)


def _register_actions() -> None:
    script_param._actions = []
    script_param.addAction(
        action_name="LedSet",
        args={"action": "LedSet", "color": "blue", "pattern": "steady", "repeat": 1, "intervalSec": 0.2},
    )
    script_param.addAction(
        action_name="LedOff",
        args={"action": "LedOff", "repeat": 1, "intervalSec": 0.2},
    )
    script_param.addAction(
        action_name="TricolorSet",
        args={"action": "TricolorSet", "red": False, "yellow": False, "green": True, "repeat": 1, "intervalSec": 0.2},
    )
    script_param.addAction(
        action_name="TricolorOff",
        args={"action": "TricolorOff", "repeat": 1, "intervalSec": 0.2},
    )
    script_param.addAction(
        action_name="AudioPlay",
        args={"action": "AudioPlay", "sound_id": "alarm.wav", "loop": False, "repeat": 1, "intervalSec": 0.2},
    )
    script_param.addAction(
        action_name="AudioStop",
        args={"action": "AudioStop", "repeat": 1, "intervalSec": 0.2},
    )
    script_param.addAction(
        action_name="TriggerSet",
        args={"action": "TriggerSet", "key": "io_out_1", "value": True, "repeat": 1, "intervalSec": 0.2},
    )
    script_param.addAction(
        action_name="GetState",
        args={"action": "GetState", "repeat": 1, "intervalSec": 0.2},
    )
    script_param.saveAction()


_register_actions()


def _rpc_preview(action: str, payload: Dict[str, Any], direct_method: str, channel: str) -> None:
    if not ConfigParams.report_rpc_json:
        return
    preview = {
        "plugin": "BehavFactory",
        "directMethod": direct_method,
        "channel": channel,
        "payload": payload,
    }
    log("rpc request preview: " + json.dumps(preview, ensure_ascii=False, sort_keys=True))


def _state_snapshot() -> Dict[str, Any]:
    raw = state.raw if isinstance(state.raw, dict) else {}
    snapshot = {
        "taskStatus": raw.get("taskStatus"),
        "battery": raw.get("battery"),
        "navigation": raw.get("navigation"),
    }
    if ConfigParams.report_state_raw:
        raw_text = json.dumps(raw, ensure_ascii=False)
        snapshot["rawPreview"] = raw_text[: ConfigParams.state_preview_chars]
    return snapshot


def _extract_script_args(raw_args: Any) -> Dict[str, Any]:
    """支持两种任务入参结构：
    1) 直接 args: {"action": "...", ...}
    2) 动作模板外层: {"policy": ..., "script": {"args": {...}}}
    """
    if not isinstance(raw_args, dict):
        return {}

    if "action" in raw_args:
        return raw_args

    script_obj = raw_args.get("script")
    if isinstance(script_obj, dict):
        script_args = script_obj.get("args")
        if isinstance(script_args, dict):
            return script_args

    nested = raw_args.get("args")
    if isinstance(nested, dict):
        if "action" in nested:
            return nested
        script_obj = nested.get("script")
        if isinstance(script_obj, dict):
            script_args = script_obj.get("args")
            if isinstance(script_args, dict):
                return script_args

    return raw_args


class BehavFactoryDebugTask(ModuleBase):
    def __init__(self):
        super().__init__()
        self.status = ScriptStatus.NONE
        self.args: Dict[str, Any] = {}
        self.report_info: Dict[str, Any] = {}

    def init_args(self, args: Dict[str, Any]) -> None:
        self.args = args or {}
        self.status = ScriptStatus.RUNNING
        self.report_info = {"args": self.args, "status": int(self.status)}
        log(f"task start, args={self.args}")

    def _run_once(self) -> Dict[str, Any]:
        """执行一次行为动作，返回结果字典。"""
        action = str(self.args.get("action", "")).strip()
        if not action:
            raise ValueError("action is empty")

        if action == "LedSet":
            payload = {"color": str(self.args.get("color", "blue")), "pattern": str(self.args.get("pattern", "steady"))}
            _rpc_preview(action, payload, "requestLed", "led")
            led.trySet(payload["color"], payload["pattern"])
            return {"action": action, "rpc": {"method": "requestLed", "channel": "led", "payload": payload}}

        if action == "LedOff":
            payload = {}
            _rpc_preview(action, payload, "requestLed", "led")       
            led.tryOff()
            return {"action": action, "rpc": {"method": "requestLed", "channel": "led", "payload": payload}}

        if action == "TricolorSet":
            payload = {
                "red": bool(self.args.get("red", False)),
                "yellow": bool(self.args.get("yellow", False)),
                "green": bool(self.args.get("green", True)),
            }
            _rpc_preview(action, payload, "requestTricolor", "tricolor")
            tricolor.trySet(payload["red"], payload["yellow"], payload["green"])
            return {"action": action, "rpc": {"method": "requestTricolor", "channel": "tricolor", "payload": payload}}

        if action == "TricolorOff":
            payload = {}
            _rpc_preview(action, payload, "requestTricolor", "tricolor")
            tricolor.tryOff()
            return {"action": action, "rpc": {"method": "requestTricolor", "channel": "tricolor", "payload": payload}}

        if action == "AudioPlay":
            payload = {"sound_id": str(self.args.get("sound_id", "alarm.wav")), "loop": bool(self.args.get("loop", False))}
            _rpc_preview(action, payload, "requestAudio", "audio")
            audio.tryPlay(payload["sound_id"], payload["loop"])
            return {"action": action, "rpc": {"method": "requestAudio", "channel": "audio", "payload": payload}}

        if action == "AudioStop":
            payload = {}
            _rpc_preview(action, payload, "requestAudioStop", "audio")
            audio.tryStop()
            return {"action": action, "rpc": {"method": "requestAudioStop", "channel": "audio", "payload": payload}}

        if action == "TriggerSet":
            payload = {"key": str(self.args.get("key", "io_out_1")), "value": bool(self.args.get("value", True))}
            _rpc_preview(action, payload, "requestTrigger", "trigger")
            trigger.trySet(payload["key"], payload["value"])
            return {"action": action, "rpc": {"method": "requestTrigger", "channel": "trigger", "payload": payload}}

        if action == "GetState":
            return {"action": action, "detail": "read state only"}

        raise ValueError(f"unsupported action: {action}")

    def run(self) -> None:
        try:
            repeat = _to_int(self.args.get("repeat", 1), 1, minimum=1, maximum=1000)
            interval_sec = _to_float(self.args.get("intervalSec", 0.2), 0.2, minimum=0.0, maximum=10.0)

            last_result: Dict[str, Any] = {}
            for index in range(repeat):
                last_result = self._run_once()
                self.report_info.update(last_result)
                self.report_info["repeat"] = repeat
                self.report_info["runIndex"] = index + 1
                Module.reportInfo(self.report_info)
                if index < repeat - 1 and interval_sec > 0.0:
                    time.sleep(interval_sec)

            if ConfigParams.settle_sec > 0.0:
                time.sleep(ConfigParams.settle_sec)

            action = str(self.args.get("action", "")).strip()
            if action == "GetState" or ConfigParams.query_state_after:
                self.report_info["state"] = _state_snapshot()

            self.status = ScriptStatus.FINISHED
            self.report_info["status"] = int(self.status)
            self.report_info["taskTime"] = round(time.time() - start_time, 3)

        except Exception as exc:
            Abnormal.setTask(
                53920,
                f"BehavFactory debug failed: {exc}",
                "behavs call failed",
                "check action/args/behavs plugin status",
                self.args,
            )
            self.status = ScriptStatus.FAILED
            self.report_info.update(
                {
                    "status": int(self.status),
                    "error": str(exc),
                    "taskTime": round(time.time() - start_time, 3),
                }
            )

    def suspend(self):
        self.status = ScriptStatus.SUSPENDED
        log("suspend")

    def resume(self):
        if Module.getStatus() == ScriptStatus.SUSPENDED:
            self.status = ScriptStatus.RUNNING
        log("resume")

    def cancel(self):
        self.status = ScriptStatus.FAILED
        log("cancel")

    def safe_move_check(self):
        self.setSafeMoveStatus(SafeMoveStatus.FINISHED)
        self.event_safe_move_check = False

    def reset(self):
        self.args = {}
        self.report_info = {}
        self.status = ScriptStatus.NONE


def main() -> None:
    Module.init()
    ScriptParam.setConfigChangeCallBack(script_config_callback)

    task = BehavFactoryDebugTask()
    log(f"main loop started")

    while True:
        Module.setStatus(task.status)
        Module.reportInfo(task.report_info)

        if task.event_safe_move_check:
            task.safe_move_check()

        if task.status == ScriptStatus.NONE:
            raw_args = Module.getTaskArgs()
            if raw_args:
                try:
                    input_args = _extract_script_args(raw_args)
                    args = script_param.loadInput(input_args)
                    task.init_args(args)
                except Exception as exc:
                    Abnormal.setTask(
                        53921,
                        f"input validation failed: {exc}",
                        "task args invalid",
                        "check action/repeat/intervalSec and action fields",
                        raw_args,
                    )
                    task.report_info = {
                        "status": int(ScriptStatus.FAILED),
                        "error": str(exc),
                        "rawArgs": raw_args,
                        "inputArgs": _extract_script_args(raw_args),
                    }
                    task.status = ScriptStatus.FAILED

        elif task.status == ScriptStatus.RUNNING:
            task.run()

        elif task.status in (ScriptStatus.FINISHED, ScriptStatus.FAILED):
            task.reset()

        time.sleep(0.1)


if __name__ == "__main__":
    main()
