#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""LED 行为脚本示例。"""
import sys
import time

from syspy.behavs.state import state
from syspy.behavs.led import led


def run():
    print("LED 脚本启动，等待连接...")
    time.sleep(2)
    print("开始运行")

    count = 0
    while state.ok():
        raw = state.raw
        battery = raw.get('battery', {})
        loc = raw.get('location', {})

        print(f"[{count}] battery={battery.get('level', '?')} loc=({loc.get('x', 0):.2f},{loc.get('y', 0):.2f})", end=" ")

        if state.taskStatus == 5:
            led.trySet("green", "breath")
            print("-> tryLed(green, breath)")
        else:
            led.trySet("blue", "steady")
            print("-> tryLed(blue, steady)")

        state.sleep(1)
        count += 1


if __name__ == "__main__":
    run()
