import os.path
import sys
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../")

from syspy.v4.include.rbk import core

name = "ServiceExampleClient"
core.Init(name)

from syspy import Motor, Navigation

while True:
    motor_position = Motor.setMotorPosition("Motor-001", 0.1, 1, -1)
    print("motor_position=", motor_position)
    # print("ok=", ok)

    Navigation.runOdoMove({"move_dist": 1, "speed_x": 0.25, "action_name": "GoStraightForward"})
    time.sleep(1)
