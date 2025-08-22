import time
from syspy import Module

def main():
    name = "ServiceExampleClient"
    Module.init(name)

    from syspy import Motor, Navigation

    while True:
        motor_position = Motor.setMotorPosition("Motor-001", 0.1, 1, -1)
        print("motor_position=", motor_position)
        # print("ok=", ok)

        Navigation.runOdoMove({"move_dist": 1, "speed_x": 0.25, "action_name": "GoStraightForward"})
        time.sleep(1)

if __name__ == '__main__':
    main()