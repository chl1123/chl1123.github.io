# -*- coding: utf-8 -*-
"""声音播放动作用例（dangerous：会实际播放音频）。

仿真现状（已实测）：BehavFactory 加载，setSound/stopSound 调用不抛异常，
但 /behave/sound channel 无数据，getter 全为 None——所以状态断言只在
getter 有数据的环境（实车）执行，仿真下退化为「动作不抛异常」。

用例结束后停止播放，不留声音。
"""

from __future__ import annotations

import time

import pytest
from syspy import Sound

TEST_SOUND_NAME = "Error.wav"


@pytest.mark.dangerous
def test_sound_play_and_stop_cycle(rbk_report, request):
    """播放 → （有状态时）确认在播 → 停止 → （有状态时）确认已停。"""
    try:
        Sound.setSound(TEST_SOUND_NAME, False)
        deadline = time.time() + 4
        playing_seen = None
        while time.time() < deadline:
            status = Sound.getStatus()
            name = Sound.getSoundName()
            if status is not None:
                playing_seen = (status, name)
                if status != 0 or (name or "") != "":
                    break
            time.sleep(0.3)
        if playing_seen is None:
            pytest.skip("前置不满足：当前环境声音状态不可观测（getter 返回 None）")
        rbk_report.add_sample(
            request.node.nodeid,
            "setSound 后 status=%r name=%r" % playing_seen,
        )
        assert playing_seen[0] != 0 or (playing_seen[1] or "") != "", (
            "setSound 后未观测到播放状态: %r" % (playing_seen,)
        )
    finally:
        Sound.stopSound(True)
        deadline = time.time() + 4
        stopped_seen = None
        while time.time() < deadline:
            status = Sound.getStatus()
            if status is not None:
                stopped_seen = status
                if status == 0:
                    break
            time.sleep(0.3)
        if stopped_seen is not None:
            rbk_report.add_sample(request.node.nodeid, "stopSound 后 status=%r" % (stopped_seen,))
            assert stopped_seen == 0, "stopSound 后仍在播放: %r" % (stopped_seen,)


@pytest.mark.dangerous
def test_sound_set_count_no_raise(rbk_report, request):
    """setSoundCount 不抛异常；结束停止播放。"""
    try:
        Sound.setSoundCount(TEST_SOUND_NAME, 1)
    finally:
        Sound.stopSound(True)
