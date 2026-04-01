#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""三色灯行为脚本示例。"""
import time
from syspy.behavs.state import state
from syspy.behavs.tricolor import tricolor


def run():
    print("三色灯脚本启动，等待连接...")
    time.sleep(2)
    print("开始运行")

    count = 0
    while state.ok():
        raw = state.raw
        battery = raw.get('battery', {})
        pct = battery.get('percentage') or 100

        print(f"[{count}] battery={pct}%", end=" ")

        if pct > 50:
            tricolor.trySet(False, False, True)
            print("-> requestTricolor(R=0,Y=0,G=1)")
        elif pct > 20:
            tricolor.trySet(False, True, False)
            print("-> requestTricolor(R=0,Y=1,G=0)")
        else:
            tricolor.trySet(True, False, False)
            print("-> requestTricolor(R=1,Y=0,G=0)")

        state.sleep(1.0)
        count += 1


if __name__ == "__main__":
    run()
