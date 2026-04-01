#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Trigger 行为脚本示例。"""
import time
from syspy.behavs.state import state
from syspy.behavs.trigger import trigger


def run():
    print("Trigger 脚本启动，等待连接...")
    time.sleep(2)
    print("开始运行")

    count = 0
    while state.ok():
        raw = state.raw
        nav = raw.get('navigation', {})
        ts = nav.get('taskStatus', 0)

        print(f"[{count}] taskStatus={ts}", end=" ")

        trigger.trySet("slow_light", ts == 5)
        print(f"-> requestTrigger(slow_light, {ts == 5})")

        state.sleep(0.2)
        count += 1


if __name__ == "__main__":
    run()
