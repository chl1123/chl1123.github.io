#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""音频行为脚本示例。"""
import time
from syspy.behavs.state import state
from syspy.behavs.audio import audio


def run():
    print("音频脚本启动，等待连接...")
    time.sleep(2)
    print("开始运行")

    last_arrived = False
    count = 0
    while state.ok():
        raw = state.raw
        nav = raw.get('navigation', {})
        arrived = (nav.get('taskStatus') == 4)

        print(f"[{count}] taskStatus={nav.get('taskStatus')} arrived={arrived}", end=" ")

        if arrived and not last_arrived:
            audio.tryPlay("arrive.wav")
            print("-> requestAudio(arrive.wav)")
        elif not arrived and last_arrived:
            audio.tryStop()
            print("-> requestAudioStop()")
        else:
            print("-> (no change)")

        last_arrived = arrived
        state.sleep(0.5)
        count += 1


if __name__ == "__main__":
    run()
