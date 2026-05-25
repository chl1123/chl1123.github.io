from syspy import Trace, Module
import inspect
import time
import uuid
from enum import IntEnum
from typing import Dict, List, Union

# ============================================================================
# Action 队列基础设施（参见 docs/guide/spec/logging.md §四）
# 协议特点：
#   - actionId 为字符串（UUID 后缀），全队稳定唯一
#   - blocking_type 声明式并行调度（HARD / SOFT / NONE，默认 HARD）
#   - 状态转移统一走单事件 actionStateChanged
#   - taskBuild / taskExtend / taskFinished / taskFailed 包络任务生命周期
# ============================================================================
class ActionStatus(IntEnum):
    INIT = 0
    RUNNING = 1
    FINISHED = 3
    FAILED = 4
    SUSPENDED = 5


# ActionStatus -> wire 字符串（与 logging.md §4.3 一致）
_STATUS_TO_WIRE = {
    ActionStatus.INIT: "init",
    ActionStatus.RUNNING: "running",
    ActionStatus.FINISHED: "finished",
    ActionStatus.FAILED: "failed",
    ActionStatus.SUSPENDED: "suspended",
}

_BLOCKING_VALUES = ("HARD", "SOFT", "NONE")

_ARG_SCALAR_TYPES = (int, float, bool, str)
_ARG_RESERVED_NAMES = frozenset({"self", "action_name", "action_type", "args", "kwargs"})


def _is_loggable_arg(v) -> bool:
    """判断值是否适合放入 actionParameters（拒绝大对象 / 不可 JSON 序列化的对象）。"""
    if v is None or isinstance(v, _ARG_SCALAR_TYPES):
        return True
    if isinstance(v, (list, tuple)):
        return len(v) <= 8 and all(_is_loggable_arg(x) for x in v)
    if isinstance(v, dict):
        return len(v) <= 8 and all(_is_loggable_arg(x) for x in v.values())
    return False


class ActionBase:
    """动作基类。

    子类约定：
      - `__init__` 中保存关键入参为同名实例属性（actionParameters 自动捕获）
      - `run(ctx)` 推进状态机；FINISHED 表示成功，FAILED 配 fail_reason 表示失败
      - `result_description()` 可选覆写：FINISHED 时随 actionStateChanged 落盘

    blocking_type（HARD / SOFT / NONE）由 ActionTask 在 build()/extend() 时按
    队列装配方式指定；动作类本身不参与决定，便于同一动作在不同任务中切换串/并行。
    """

    # 由 __init_subclass__ 在类定义时一次性提取，运行时零反射成本
    _arg_field_names: tuple = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        try:
            sig = inspect.signature(cls.__init__)
            cls._arg_field_names = tuple(
                name
                for name, p in sig.parameters.items()
                if name not in _ARG_RESERVED_NAMES
                and p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
            )
        except (TypeError, ValueError):
            cls._arg_field_names = ()

    def __init__(self, action_name: str = None):
        self.action_type: str = action_name or self.__class__.__name__
        # action_name 作为同义别名保留（历史代码大量使用 self.action_name）
        self.action_name: str = self.action_type
        # actionId 在 ActionTask.build()/extend() 时分配；也允许子类构造时显式覆写
        self.action_id: str = ""
        self.action_status: ActionStatus = ActionStatus.INIT
        self.fail_reason: str = ""
        self.error_code: str = ""
        # 阻塞类型默认 HARD；ActionTask 在装配时按队列约定改写
        self.blocking_type: str = "HARD"

    def args_summary(self) -> dict:
        """送入 taskBuild / taskExtend 的 actionParameters。

        基于 __init__ 形参名自动捕获实例属性；非 JSON 友好值自动跳过。
        子类需要自定义命名 / 单位 / 计算字段时覆写。
        """
        summary = {}
        for name in self._arg_field_names:
            if not hasattr(self, name):
                continue
            v = getattr(self, name)
            if _is_loggable_arg(v):
                summary[name] = v
        return summary

    def action_description(self) -> str:
        """taskBuild / taskExtend 中可选的人读补充说明（默认空串则不落盘）。"""
        return ""

    def result_description(self) -> dict:
        """FINISHED 时随 actionStateChanged 落盘的业务结果摘要（可选覆写）。"""
        return {}

    def reset(self):
        """INIT -> RUNNING 时调用一次，子类可重置内部状态。"""
        self.action_status = ActionStatus.RUNNING

    def cancel(self):
        """主动取消（外部触发）：默认置 FAILED。子类可覆写释放资源。"""
        self.action_status = ActionStatus.FAILED
        if not self.fail_reason:
            self.fail_reason = "cancelled"

    def suspend(self):
        """暂停当前动作：仅在 RUNNING 时切到 SUSPENDED。子类按需覆写硬件副作用。"""
        if self.action_status == ActionStatus.RUNNING:
            self.action_status = ActionStatus.SUSPENDED

    def resume(self):
        """恢复当前动作：仅在 SUSPENDED 时切回 RUNNING。子类按需覆写。"""
        if self.action_status == ActionStatus.SUSPENDED:
            self.action_status = ActionStatus.RUNNING

    def run(self, ctx):
        """每 tick 调用一次，子类必须实现。ctx 为模块上下文（一般是模块主类实例）。"""
        raise NotImplementedError


class ActionTask:
    """可复用的 Action 任务调度器（VDA5050 风格）。

    一次 ActionTask 实例对应一次 taskBuild..taskFinished/taskFailed 事件流：
    维护 action 列表、按 blocking_type 调度、检测状态转移并落结构化事件。

    职责：
      1. 维护 action 列表 + 每条 action 的状态
      2. 按 blocking_type 调度：HARD 独占；SOFT/NONE 可与非 HARD 并行
      3. 检测状态转移并落 actionStateChanged；任务起止落 taskBuild / taskFinished / taskFailed
      4. 提供 status_counts() 给 chart 端做时序快照

    使用模式：
        self.task = ActionTask(mod="jack")
        self.task.build([JackHeight(...), FillLight(...)])
        while not self.task.is_done:
            self.task.step(self)
    """

    def __init__(self, mod: str):
        self.mod = mod
        self.action_list: List[ActionBase] = []
        # 每条 action 的进入 RUNNING 时间戳（用于 elapsedMs）
        self._action_start_ts: Dict[str, float] = {}
        # 上一次发出 actionStateChanged 的状态（用于检测转移）
        self._last_status: Dict[str, ActionStatus] = {}
        # 队列时序
        self.queue_start_ts: float = 0.0
        # 终态标记（taskFinished / taskFailed 只发一次）
        self._task_done_logged: bool = False
        self._status: ActionStatus = ActionStatus.INIT
        self._failed_at: str = ""
        # 任务 id 快照（在 build() 时刻取一次，整队复用）
        self.task_id: str = ""

    # -------- 工具 --------
    @staticmethod
    def _snapshot_task_id() -> str:
        try:
            tid = Module.getTaskId()
        except Exception:
            return ""
        return "" if tid is None else str(tid)

    @staticmethod
    def _gen_action_id(action_type: str) -> str:
        return f"{action_type}-{uuid.uuid4().hex[:8]}"

    def _assign_ids(self, actions: List[ActionBase]):
        """为新加入的 action 分配 actionId（已显式设置则保留）。"""
        existing = {a.action_id for a in self.action_list if a.action_id}
        for a in actions:
            if not a.action_id:
                aid = self._gen_action_id(a.action_type)
                while aid in existing:
                    aid = self._gen_action_id(a.action_type)
                a.action_id = aid
            existing.add(a.action_id)

    def _descriptor(self, a: ActionBase) -> dict:
        d = {
            "actionId": a.action_id,
            "actionType": a.action_type,
            "blockingType": a.blocking_type,
            "actionParameters": a.args_summary(),
        }
        desc = a.action_description()
        if desc:
            d["actionDescription"] = desc
        return d

    # -------- 状态查询 --------
    @property
    def status(self) -> ActionStatus:
        return self._status

    @property
    def is_done(self) -> bool:
        return self._status in (ActionStatus.FINISHED, ActionStatus.FAILED)

    @property
    def is_suspended(self) -> bool:
        return self._status == ActionStatus.SUSPENDED

    @property
    def total(self) -> int:
        return len(self.action_list)

    @property
    def active(self) -> List[ActionBase]:
        """当前处于 RUNNING / SUSPENDED 的 action（已启动未终态）。"""
        return [
            a for a in self.action_list
            if a.action_status in (ActionStatus.RUNNING, ActionStatus.SUSPENDED)
        ]

    @property
    def pending(self) -> List[ActionBase]:
        """尚未启动的 action（保持队列顺序）。"""
        return [a for a in self.action_list if a.action_status == ActionStatus.INIT]

    @property
    def current(self):
        """兼容旧接口：返回首个 active action（无则返回首个 pending）。"""
        for a in self.action_list:
            if a.action_status in (ActionStatus.RUNNING, ActionStatus.SUSPENDED):
                return a
        for a in self.action_list:
            if a.action_status == ActionStatus.INIT:
                return a
        return None

    def status_counts(self) -> Dict[str, int]:
        """供 chart 使用的状态分布（key 类型稳定为 int 计数）。"""
        counts = {"init": 0, "running": 0, "finished": 0, "failed": 0, "suspended": 0}
        for a in self.action_list:
            counts[_STATUS_TO_WIRE[a.action_status]] += 1
        return counts

    # -------- 队列装配 --------
    @staticmethod
    def _normalize(
        actions: "Union[ActionBase, tuple, List]",
        default_blocking: str,
    ) -> List[ActionBase]:
        """规整 build()/extend() 入参为 ActionBase 列表，同时按 item 形态设置 blocking_type。

        允许的 item 形态：
          - `ActionBase`                     —— blocking_type 取 default_blocking
          - `(ActionBase, "HARD"|"SOFT"|"NONE")` —— blocking_type 取 tuple 第二项
        允许的容器形态：单个 item 或 list/tuple of items。
        """
        if default_blocking not in _BLOCKING_VALUES:
            raise ValueError(
                f"blocking_type={default_blocking!r} invalid, must be one of {_BLOCKING_VALUES}"
            )

        def _resolve(item) -> ActionBase:
            if isinstance(item, ActionBase):
                item.blocking_type = default_blocking
                return item
            # (action, blocking_type)
            if isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], ActionBase):
                action, bt = item
                if bt not in _BLOCKING_VALUES:
                    raise ValueError(
                        f"blocking_type={bt!r} invalid, must be one of {_BLOCKING_VALUES}"
                    )
                action.blocking_type = bt
                return action
            raise TypeError(
                f"action item must be ActionBase or (ActionBase, blocking_type) tuple, got {item!r}"
            )

        # 单个 action / 单个 tuple
        if isinstance(actions, ActionBase):
            return [_resolve(actions)]
        if isinstance(actions, tuple) and len(actions) == 2 and isinstance(actions[0], ActionBase):
            return [_resolve(actions)]
        return [_resolve(item) for item in actions]

    def build(
        self,
        actions: "Union[ActionBase, tuple, List]",
        *,
        blocking_type: str = "HARD",
    ):
        """首次装配 action_list，发 taskBuild 事件，切到 RUNNING。

        `actions` 接受单个 action、`(action, blocking_type)` 元组，或它们的列表。
        `blocking_type` 关键字参数为本次装配的缺省阻塞类型（默认 `"HARD"`），
        被 tuple 形态的逐项设置覆盖。
        """
        self.action_list = self._normalize(actions, blocking_type)
        self._action_start_ts = {}
        self._last_status = {}
        self._task_done_logged = False
        self._status = ActionStatus.RUNNING
        self._failed_at = ""
        self.queue_start_ts = time.time()
        self.task_id = self._snapshot_task_id()
        self._assign_ids(self.action_list)
        # 初始化 last_status 快照（INIT），之后 step() 检测转移
        for a in self.action_list:
            self._last_status[a.action_id] = ActionStatus.INIT
        Trace.log(
            {
                "event": "taskBuild",
                "taskId": self.task_id,
                "total": len(self.action_list),
                "actions": [self._descriptor(a) for a in self.action_list],
            },
            output_time=True,
            name=f"{self.mod}.action",
        )

    def extend(
        self,
        new_actions: "Union[ActionBase, tuple, List]",
        *,
        blocking_type: str = "HARD",
    ):
        """运行中向尾部追加动作。

        入参形态与 `build()` 一致；单个动作时可省略 `[ ]`。
        若当前未活跃（INIT 或终态），自动促级到 build() 发出 taskBuild。
        """
        new_actions: List[ActionBase] = self._normalize(new_actions, blocking_type)
        if not new_actions:
            return
        if self._status not in (ActionStatus.RUNNING, ActionStatus.SUSPENDED):
            self.build(new_actions, blocking_type=blocking_type)
            return
        self._assign_ids(new_actions)
        self.action_list.extend(new_actions)
        for a in new_actions:
            self._last_status[a.action_id] = ActionStatus.INIT
        Trace.log(
            {
                "event": "taskExtend",
                "taskId": self.task_id,
                "appended": [self._descriptor(a) for a in new_actions],
                "total": len(self.action_list),
            },
            output_time=True,
            name=f"{self.mod}.action",
        )

    # -------- 状态转移事件 --------
    def _emit_state_changed(self, a: ActionBase, new_status: ActionStatus):
        """发一条 actionStateChanged，并维护 _action_start_ts / _last_status。"""
        payload = {
            "event": "actionStateChanged",
            "taskId": self.task_id,
            "actionId": a.action_id,
            "actionType": a.action_type,
            "status": _STATUS_TO_WIRE[new_status],
        }
        # 终态填 elapsedMs（自该 action 进入 RUNNING 起算）
        if new_status in (ActionStatus.FINISHED, ActionStatus.FAILED):
            t0 = self._action_start_ts.get(a.action_id)
            if t0 is not None:
                payload["elapsedMs"] = int((time.time() - t0) * 1000)
        if new_status == ActionStatus.FINISHED:
            try:
                rd = a.result_description()
            except Exception:
                rd = {}
            if rd:
                payload["resultDescription"] = rd
        if new_status == ActionStatus.FAILED:
            if a.fail_reason:
                payload["reason"] = a.fail_reason
            if a.error_code:
                payload["errorCode"] = a.error_code
        if new_status == ActionStatus.SUSPENDED and a.fail_reason:
            payload["reason"] = a.fail_reason
        Trace.log(payload, output_time=True, name=f"{self.mod}.action")
        self._last_status[a.action_id] = new_status

    # -------- 调度推进 --------
    def step(self, ctx=None):
        """推进队列一步。每 tick 调用一次。

        Args:
            ctx: 透传给 action.run(ctx) 的上下文对象（一般是模块主类实例）。
        """
        if self._status != ActionStatus.RUNNING:
            return

        # 1) 启动 pending：按队列顺序遍历，按 blocking_type 决策
        active_has_hard = any(a.blocking_type == "HARD" for a in self.active)
        active_count = len(self.active)
        for a in self.action_list:
            if a.action_status != ActionStatus.INIT:
                continue
            if a.blocking_type == "HARD":
                # HARD 必须 active 为空才能启动；启动后通过 break 挡住后续 pending
                if active_count == 0:
                    self._action_start_ts[a.action_id] = time.time()
                    a.reset()  # INIT -> RUNNING
                    self._emit_state_changed(a, ActionStatus.RUNNING)
                break
            else:
                # SOFT / NONE：active 中没有 HARD 就能启动
                if active_has_hard:
                    break
                self._action_start_ts[a.action_id] = time.time()
                a.reset()
                self._emit_state_changed(a, ActionStatus.RUNNING)
                active_count += 1
                # 继续尝试启动后续 SOFT/NONE

        # 2) 推进 active 状态机；检测转移并发事件
        for a in list(self.action_list):
            if a.action_status == ActionStatus.RUNNING:
                a.run(ctx)
            last = self._last_status.get(a.action_id, ActionStatus.INIT)
            if a.action_status != last:
                self._emit_state_changed(a, a.action_status)

        # 3) 任一 action 失败：取消其他 active，整队落 taskFailed
        failed = next((a for a in self.action_list if a.action_status == ActionStatus.FAILED), None)
        if failed is not None:
            self._failed_at = failed.action_id
            for other in self.action_list:
                if other is failed:
                    continue
                if other.action_status in (ActionStatus.RUNNING, ActionStatus.SUSPENDED):
                    other.cancel()
                    if other.action_status == ActionStatus.FAILED:
                        self._emit_state_changed(other, ActionStatus.FAILED)
            self._finalize_failed()
            return

        # 4) 全部进入 FINISHED：落 taskFinished
        if all(a.action_status == ActionStatus.FINISHED for a in self.action_list):
            self._finalize_finished()

    def cancel(self, reason: str = "cancelled"):
        """外部取消队列：把所有 active 推到 FAILED，整队落 taskFailed。"""
        if self.is_done:
            return
        for a in self.action_list:
            if a.action_status in (ActionStatus.RUNNING, ActionStatus.SUSPENDED, ActionStatus.INIT):
                if not a.fail_reason:
                    a.fail_reason = reason
                a.cancel()
                self._emit_state_changed(a, ActionStatus.FAILED)
                if not self._failed_at:
                    self._failed_at = a.action_id
        self._finalize_failed(reason=reason)

    # -------- 暂停 / 恢复 --------
    def suspend(self):
        """暂停队列：把所有 RUNNING action 切到 SUSPENDED。"""
        if self._status != ActionStatus.RUNNING:
            return
        for a in self.action_list:
            if a.action_status == ActionStatus.RUNNING:
                a.suspend()
                if a.action_status == ActionStatus.SUSPENDED:
                    self._emit_state_changed(a, ActionStatus.SUSPENDED)
        self._status = ActionStatus.SUSPENDED
        Trace.log(
            f"queue suspend active={len(self.active)}/{len(self.action_list)}",
            output_time=True,
            name=self.mod,
        )

    def resume(self):
        """恢复队列：把所有 SUSPENDED action 切回 RUNNING。"""
        if self._status != ActionStatus.SUSPENDED:
            return
        for a in self.action_list:
            if a.action_status == ActionStatus.SUSPENDED:
                a.resume()
                if a.action_status == ActionStatus.RUNNING:
                    self._emit_state_changed(a, ActionStatus.RUNNING)
        self._status = ActionStatus.RUNNING
        Trace.log(
            f"queue resume active={len(self.active)}/{len(self.action_list)}",
            output_time=True,
            name=self.mod,
        )

    def reset(self):
        """清空队列状态（任务结束后调用）。"""
        self.action_list = []
        self._action_start_ts = {}
        self._last_status = {}
        self._task_done_logged = False
        self._status = ActionStatus.INIT
        self._failed_at = ""
        self.task_id = ""

    # -------- 内部：终态事件 --------
    def _finalize_finished(self):
        if self._task_done_logged:
            self._status = ActionStatus.FINISHED
            return
        Trace.log(
            {
                "event": "taskFinished",
                "taskId": self.task_id,
                "total": len(self.action_list),
                "elapsedMs": int((time.time() - self.queue_start_ts) * 1000),
            },
            output_time=True,
            name=f"{self.mod}.action",
        )
        self._task_done_logged = True
        self._status = ActionStatus.FINISHED

    def _finalize_failed(self, reason: str = ""):
        if self._task_done_logged:
            self._status = ActionStatus.FAILED
            return
        payload = {
            "event": "taskFailed",
            "taskId": self.task_id,
            "total": len(self.action_list),
            "elapsedMs": int((time.time() - self.queue_start_ts) * 1000),
        }
        if self._failed_at:
            payload["failedAt"] = self._failed_at
        if reason:
            payload["reason"] = reason
        Trace.log(payload, output_time=True, name=f"{self.mod}.action")
        self._task_done_logged = True
        self._status = ActionStatus.FAILED
