import time
import sys
sys.path.append('/opt/.data/rbk/resources/scripts/')
from syspy import Battery, Di, Do, Controller, Move, NavSpeed, Motor
from syspy.rpc import Rpc

def test_battery():
    Battery.update()
    print("Battery.get_data()", Battery.get_data())
    # print("charge_current", Battery.charge_current)
    # print(Battery.percentage)
    # print(Battery.temperature)

def test_di():
    Di.update()
    print("Di.get_data()", Di.get_data())
    # print("Di.node", Di.node)
    # print("Di.max_node", Di.max_node)
    # print("Di.get_di(1)", Di.get_di(1))

def test_do():
    Do.update()
    print("Do.get_data()", Do.get_data())
    # print("Do.node", Do.node)
    # print("Do.max_node", Do.max_node)
    # print("Do.get_do(1)", Do.get_do(1))

def test_controller():
    Controller.update()
    print("Controller.get_data()", Controller.get_data())
    # print("Controller.emc: ", Controller.emc)

def test_move():
    Move.update()
    print("Move.get_data()", Move.get_data())
    # print("Move.blocked: ", Move.blocked)

def test_nav_speed():
    NavSpeed.update()
    print("NavSpeed.get_data()", NavSpeed.get_data())
    # print("NavSpeed: ", NavSpeed.x, NavSpeed.y, NavSpeed.rotate)

def test_message():
    while True:
        test_battery()
        test_di()
        test_do()
        test_controller()
        test_move()
        test_nav_speed()
        time.sleep(1)

"""
目录分类
"""
def test_motor():
    jack_motor_name = "Motor-003"
    report_info = dict()
    motor_speed = 0.1
    zero_pos = 0.0
    up_di = 6
    zero_di = 3
    height = 0.05
    while True:
        print("motor.setMotorPositionRPC", Motor.setMotorPositionRPC(jack_motor_name, height, motor_speed, up_di))
        print("motor.isMotorStop()", Motor.isMotorStop(jack_motor_name))
        if Di.get_di(zero_di) or Motor.setMotorPositionRPC(jack_motor_name):
            print("finish")
        time.sleep(0.05)

def test_multi_params():
    print("Rpc.multiParams 1: ", Rpc.multiParams("hello", "2", "3"))
    print("Rpc.multiParams 2: ", Rpc.multiParams("hello", "2"))

def main():
    while True:
        test_message()
        test_motor()
        test_multi_params()
        time.sleep(1)


if __name__ == '__main__':
    main()
