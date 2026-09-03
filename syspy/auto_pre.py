# -*- coding: utf-8 -*-
"""AutoPre（边走边动）脚本 SDK。

封装 MoveFactory（MF）插件提供的 3 个真实 C++ RPC 接口：

    bool autoPreReportStatus(uint64_t task_id, int status)
    double autoPreRemainingTime(uint64_t task_id, std::string station, bool include_rotation)
    bool autoPreStopAtPreStation(uint64_t task_id, bool stop)

真实接口与业务脚本使用的门面之间有三处转换，均由本模块内部完成：
  1. `task_id` 是显式参数，业务脚本无感——由 `_AutoPre` 缓存并自动注入。
  2. `remainingTime` 返回裸 `double`，负数表示不可计算——转换为 `Optional[float]`。
  3. `status` 是裸 `int`，不是枚举对象——`AutoPreStatus` 在转发前显式 `int()`。

详见 docs/multiSegmentNav/边走边动设计说明（详细）.md §1.3.2、§1.8.1。
"""
from enum import IntEnum
from typing import Dict, Optional

from syspy.core.rbk_rpc import Service
from syspy.lib.trace import Trace
import math

from syspy.lib.action_task import ActionBase, ActionStatus, ActionTask
from syspy.lib.module import Module


class AutoPreStatus(IntEnum):
    """脚本向 MF 上报的预动作状态（与 ActionStatus 同样跳过值 2）。"""

    WAITING = 0
    RUNNING = 1
    FINISHED = 3
    FAILED = 4
    SUSPENDED = 5


class _AutoPre:
    """AutoPre 真实 RPC 的内部适配层，缓存当前 task_id。

    模块私有：业务脚本不直接使用本类，只通过模块级单例 `AutoPre`
    （供 `AutoPreSequenceAction` 内部调用）或公开门面 `AutoPreInterface`
    （供业务脚本调用）访问。
    """

    def __init__(self):
        self._task_id: Optional[int] = None

    def begin_task(self, task_id: int) -> None:
        """TASK 到达时缓存 task_id。"""
        self._task_id = task_id

    def end_task(self) -> None:
        """TASK 结束/取消时清空缓存，并清理该 task_id 的 startAction 锁存。"""
        if self._task_id is not None:
            _start_action_latch.pop(self._task_id, None)
        self._task_id = None

    def _resolve_task_id(self, task_id: Optional[int]) -> Optional[int]:
        resolved = task_id if task_id is not None else self._task_id
        if resolved is None:
            Trace.log("auto-pre call with no active task_id", name="autoPre.err")
        return resolved

    def report_status(self, status: "AutoPreStatus", task_id: Optional[int] = None) -> bool:
        """调用 autoPreReportStatus(task_id, int(status))。"""
        tid = self._resolve_task_id(task_id)
        if tid is None:
            return False
        try:
            return bool(
                Service.client().call_service(
                    "MoveFactory", "autoPreReportStatus", tid, int(status)
                )
            )
        except Exception as e:
            Trace.log(f"autoPreReportStatus failed error={e}", name="autoPre.err")
            return False

    def remaining_time(
            self, station: str, include_rotation: bool, task_id: Optional[int] = None
    ) -> Optional[float]:
        """调用 autoPreRemainingTime(...)；负数转换为 None。"""
        tid = self._resolve_task_id(task_id)
        if tid is None:
            return None
        try:
            value = Service.client().call_service(
                "MoveFactory", "autoPreRemainingTime", tid, station, include_rotation
            )
        except Exception as e:
            Trace.log(f"autoPreRemainingTime failed error={e}", name="autoPre.err")
            return None
        value = float(value)
        return None if value < 0.0 else value

    def stop_at_pre_station(self, stop: bool, task_id: Optional[int] = None) -> bool:
        """调用 autoPreStopAtPreStation(task_id, stop)。"""
        tid = self._resolve_task_id(task_id)
        if tid is None:
            return False
        try:
            return bool(
                Service.client().call_service(
                    "MoveFactory", "autoPreStopAtPreStation", tid, stop
                )
            )
        except Exception as e:
            Trace.log(f"autoPreStopAtPreStation failed error={e}", name="autoPre.err")
            return False


# 模块级单例：AutoPreSequenceAction 与其他内部编排逻辑通过此变量访问真实 RPC 层
AutoPre = _AutoPre()


# ============================================================================
# startAction：MF -> 脚本通知回调（按 task_id 幂等锁存）
# ============================================================================
_start_action_latch: Dict[int, bool] = {}


def _on_start_action(task_id: int) -> bool:
    """MF -> 脚本通知回调：当前 TASK 的正式阶段已到达。

    注册为 RPC server 方法（方法名 "startAction"）。当前 TASK 首次或重复
    通知均幂等返回 True；task_id 与当前脚本 TASK 不匹配时返回 False。

    Args:
        task_id: MF 生成并下发的脚本 TASK ID。

    Returns:
        True 表示已接受（本次或此前已锁存）；False 表示 task_id 不匹配。
    """
    if AutoPre._task_id is None or task_id != AutoPre._task_id:
        Trace.log(
            f"startAction task_id mismatch got={task_id} current={AutoPre._task_id}",
            name="autoPre.err",
        )
        return False
    first_notification = not _start_action_latch.get(task_id, False)
    _start_action_latch[task_id] = True
    if first_notification:
        Trace.log(f"startAction latched task_id={task_id}", name="autoPre.startAction")
    return True


Service.server().register_function(_on_start_action, "startAction", True)


# ============================================================================
# AutoPreInterface：公开门面，业务脚本使用（camelCase，与文档伪代码一致）
# ============================================================================
class AutoPreInterface:
    """业务脚本使用的 AutoPre 门面。不暴露 task_id：内部自动关联当前 TASK。"""

    @classmethod
    def stopAtPreStation(cls, stop: bool) -> bool:
        """动态设置当前 TASK 是否需要在前置点停车。

        Args:
            stop: True 表示请求在前置点停车；False 表示撤销脚本停车请求。

        Returns:
            设置成功返回 True；当前 TASK 无法关联或已晚于安全刹停时机时
            返回 False。
        """
        return AutoPre.stop_at_pre_station(stop)

    @classmethod
    def remainingTime(cls, station: str, includeRotation: bool = True) -> Optional[float]:
        """查询到指定站点语义的实时剩余时间。

        Args:
            station: "preStation" 或 "targetStation"。
            includeRotation: 是否计入该站点规划内的原地旋转，缺省计入。

        Returns:
            预计秒数；不可计算时返回 None。
        """
        return AutoPre.remaining_time(station, includeRotation)

    @classmethod
    def reportStatus(cls, status: AutoPreStatus) -> bool:
        """上报当前 TASK 的预动作状态。

        Args:
            status: WAITING、RUNNING、FINISHED、FAILED 或 SUSPENDED。

        Returns:
            上报成功返回 True。
        """
        return AutoPre.report_status(status)

    @classmethod
    def isStartActionLatched(cls) -> bool:
        """查询当前 TASK 的正式动作通知是否已锁存。

        Returns:
            True 表示 MF 已通知正式阶段到达（幂等，收到后一直为 True，
            直到当前 TASK 结束）；无活动 TASK 或尚未收到通知时返回 False。
        """
        tid = AutoPre._task_id
        if tid is None:
            return False
        return _start_action_latch.get(tid, False)


class AutoPreSequenceAction(ActionBase):
    """按实时剩余时间启动预动作、动态请求停车并等待正式动作通知。

    Args:
        pre_actions: 由业务脚本编排的预动作列表。
        required_time: 预动作保守所需时长，单位为秒。
        advance_time: 提前启动余量，单位为秒，缺省为 1.0。
        station: remainingTime 的查询目标：preStation 或 targetStation。
        include_rotation: 是否计入目标站点规划内的原地旋转，缺省 True。
        must_stop_at_pre_station: 正式动作是否要求前置点停车；仅是脚本
            本地策略，不会在初始化时向 MF 注册。
    """

    def __init__(
            self,
            pre_actions,
            required_time,
            advance_time=1.0,
            station="preStation",
            include_rotation=True,
            must_stop_at_pre_station=False,
    ):
        super().__init__("AutoPreSequence")
        self.pre_actions = pre_actions
        self.required_time = required_time
        self.advance_time = advance_time
        self.station = station
        self.include_rotation = include_rotation
        self.must_stop_at_pre_station = must_stop_at_pre_station
        self.pre_task = None
        self.started = False
        self.stop_requested = False
        self.auto_pre_status = None
        self.status_before_suspend = None

    def reset(self):
        """重置外层 Action；内部预动作队列仍延迟到真正启动时构建。"""
        super().reset()
        AutoPre.begin_task(Module.getTaskId())
        self.pre_task = None
        self.started = False
        self.stop_requested = False
        self.auto_pre_status = None
        self.status_before_suspend = None

    def run(self, ctx):
        """推进实时判断、预动作执行、停车请求和正式动作通知。

        Args:
            ctx: 当前模块脚本实例，透传给内部预动作 ActionTask。
        """
        if not self._parameters_valid():
            self._fail("invalid auto-pre time parameters", report=False)
            return

        if self.auto_pre_status is None:
            if not self._report(AutoPreStatus.WAITING):
                self._fail("auto-pre WAITING rejected", report=False)
                return
        elif not AutoPre.report_status(self.auto_pre_status):
            self._fail("auto-pre heartbeat rejected", report=False)
            return

        if self.must_stop_at_pre_station and not self.stop_requested:
            if not AutoPre.stop_at_pre_station(True):
                self._fail("auto-pre fixed stop request rejected")
                return
            self.stop_requested = True

        remaining_time = AutoPre.remaining_time(
            self.station, self.include_rotation
        )

        if not self.started:
            if remaining_time is None:
                return
            if remaining_time > self.required_time + self.advance_time:
                return
            if not self._report(AutoPreStatus.RUNNING):
                self._fail("auto-pre RUNNING rejected", report=False)
                return
            self.started = True
            self.pre_task = ActionTask(mod="auto_pre")
            self.pre_task.build(self.pre_actions)

        if (
                self.station == "preStation"
                and remaining_time is not None
                and not self.must_stop_at_pre_station
        ):
            unfinished_time = self._estimate_unfinished_time()
            should_stop = unfinished_time > remaining_time
            if should_stop != self.stop_requested:
                if not AutoPre.stop_at_pre_station(should_stop):
                    self._fail("auto-pre stop request rejected")
                    return
                self.stop_requested = should_stop

        if not self.pre_task.is_done:
            self.pre_task.step(ctx)
            if not self.pre_task.is_done:
                return

        if self.pre_task.status == ActionStatus.FAILED:
            self._fail("auto-pre action failed")
            return

        if self.auto_pre_status != AutoPreStatus.FINISHED:
            if not self._report(AutoPreStatus.FINISHED):
                self._fail("auto-pre FINISHED rejected", report=False)
                return
            Trace.log("auto-pre FINISHED reported, waiting startAction", name="autoPre")

        if AutoPreInterface.isStartActionLatched():
            Trace.log("auto-pre startAction latched, sequence finished", name="autoPre")
            self.action_status = ActionStatus.FINISHED
            AutoPre.end_task()

    def _estimate_unfinished_time(self):
        """返回尚未完成的预动作保守预算；具体拆分由业务 Action 提供。"""
        if self.pre_task is None:
            return self.required_time
        return self.pre_task.estimateRemainingDuration(self.required_time)

    def _parameters_valid(self):
        return (
                isinstance(self.required_time, (int, float))
                and math.isfinite(self.required_time)
                and self.required_time >= 0.0
                and isinstance(self.advance_time, (int, float))
                and math.isfinite(self.advance_time)
                and self.advance_time >= 0.0
                and self.station in ("preStation", "targetStation")
                and isinstance(self.include_rotation, bool)
                and isinstance(self.must_stop_at_pre_station, bool)
                and not (
                self.must_stop_at_pre_station
                and self.station != "preStation"
        )
        )

    def _report(self, status):
        """上报并保存最新预动作状态。"""
        if not AutoPre.report_status(status):
            return False
        self.auto_pre_status = status
        return True

    def _fail(self, message, report=True):
        """上报预动作失败并将外层 Action 置为失败。

        Args:
            message: 失败原因。
            report: 是否尝试上报 AutoPreStatus.FAILED。
        """
        if (
                report
                and self.auto_pre_status
                not in (AutoPreStatus.FINISHED, AutoPreStatus.FAILED)
        ):
            self._report(AutoPreStatus.FAILED)
        self.fail_reason = message
        self.action_status = ActionStatus.FAILED
        AutoPre.end_task()

    def suspend(self):
        self.status_before_suspend = self.auto_pre_status
        if self.pre_task is not None and not self.pre_task.is_done:
            self.pre_task.suspend()
        if self.auto_pre_status in (AutoPreStatus.WAITING, AutoPreStatus.RUNNING):
            if not self._report(AutoPreStatus.SUSPENDED):
                self._fail("auto-pre SUSPENDED rejected", report=False)
                return
        self.action_status = ActionStatus.SUSPENDED

    def resume(self):
        if self.auto_pre_status == AutoPreStatus.SUSPENDED:
            if not self._report(self.status_before_suspend):
                self._fail("auto-pre resume status rejected", report=False)
                return
        if (
                self.pre_task is not None
                and self.status_before_suspend == AutoPreStatus.RUNNING
        ):
            self.pre_task.resume()
        self.action_status = ActionStatus.RUNNING

    def cancel(self, reason="task canceled"):
        if self.auto_pre_status not in (
                None,
                AutoPreStatus.FINISHED,
                AutoPreStatus.FAILED,
        ):
            self._report(AutoPreStatus.FAILED)
        if self.pre_task is not None and not self.pre_task.is_done:
            self.pre_task.cancel(reason=reason)
        self.fail_reason = reason
        self.action_status = ActionStatus.FAILED
        AutoPre.end_task()
