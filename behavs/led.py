#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""LED 灯带行为脚本示例。"""
import time

from syspy.behavs.ecal_rpc import get_ecal_rpc
from syspy.led import Led


def run():
    ecal_rpc = get_ecal_rpc()
    print("LED 脚本启动，等待 BehavFactory...")
    while ecal_rpc.is_running() and not ecal_rpc.is_connected():
        time.sleep(0.2)

    count = 0
    while ecal_rpc.is_running():
        if count % 2 == 0:
            Led.trySet("MutableBreath", "BlueCobalt", 3200)
            print("tryLed(MutableBreath, BlueCobalt, 3200)")
        else:
            Led.trySet("Blink", "Yellow", 1000)
            print("tryLed(Blink, Yellow, 1000)")
        time.sleep(3)
        count += 1


if __name__ == "__main__":
    run()
