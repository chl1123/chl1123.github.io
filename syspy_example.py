import time
import sys

sys.path.append('/opt/.data/rbk/resources/scripts/')
from syspy import *
from syspy.abnormal import Abnormal
from syspy.trace import Trace


def test_battery():
    Battery.update()
    print("Battery.get_data()", Battery.get_data())


def test_bin():
    Bin.update()
    print("type(bin): ", type(Bin))
    print("Bin.data: ", Bin.data)
    if Bin.data is not None:
        print("Bin.data.bins: ", Bin.data.bins)


def test_camera():
    Camera.update()
    print("Camera.data: ", Camera.data)


def test_can():
    Can.update()
    print("Can.data: ", Can.data)


def test_controller():
    Controller.update()
    print("Controller.get_data()", Controller.get_data())


def test_di():
    Di.update()
    print("Di.get_data()", Di.get_data())


def test_do():
    Do.update()
    print("Do.get_data()", Do.get_data())


def test_distance():
    Distance.update()
    print("Distance.get_data()", Distance.get_data())


def test_laser():
    Laser.update()
    print("Laser.get_data()", Laser.get_data())


def test_loc():
    Loc.update()
    print("Loc.get_data()", Loc.get_data())


def test_magnetic():
    Magnetic.update()
    print("Magnetic.get_data()", Magnetic.get_data())


def test_move():
    Move.update()
    print("Move.get_data()", Move.get_data())


def test_nav_speed():
    NavSpeed.update()
    print("NavSpeed.get_data()", NavSpeed.get_data())


def test_odometer():
    Odometer.update()
    print("Odometer.get_data()", Odometer.get_data())


def test_pgv():
    Pgv.update()
    print("Pgv.get_data()", Pgv.get_data())


def test_rfid():
    RFID.update()
    print("RFID.get_data()", RFID.get_data())


def test_sound():
    Sound.update()
    print("Sound.get_data()", Sound.get_data())


def test_message():
    test_battery()
    test_bin()
    test_camera()
    test_can()
    test_controller()
    test_di()
    test_do()
    test_distance()
    test_laser()
    test_loc()
    test_magnetic()
    test_move()
    test_nav_speed()
    test_odometer()
    test_pgv()
    test_sound()

def test_motor():
    jack_motor_name = "Motor-003"
    report_info = dict()
    motor_speed = 0.1
    zero_pos = 0.0
    up_di = 6
    zero_di = 3
    height = 0.05
    print("motor.setMotorPosition", Motor.setMotorPosition(jack_motor_name, height, motor_speed, up_di))
    print("motor.isMotorStop()", Motor.isMotorStop(jack_motor_name))
    if Di.get_di(zero_di) or Motor.isMotorReached(jack_motor_name):
        print("finish")


def test_abnormal():
    print("Abnormal.exists", Abnormal.exists(24500))
    print("Abnormal.setTask", Abnormal.setTask(24500, "task error", "reboot", "setTaskAbnormal", "task 123"))
    print("Abnormal.setMap", Abnormal.setMap(24501, "map error", "reboot", "setMapAbnormal", "map 123", "2D", "elementType", "elementName","param"))
    print("Abnormal.setModel", Abnormal.setModel(24502, "chassis error", "reboot", "setChassisAbnormal", "chassis 123"))
    print("Abnormal.setApp", Abnormal.setApp(24503, "task error", "reboot", "setTaskAbnormal", "task", "123"))
    print("Abnormal.setSystem", Abnormal.setSystem(24504, "task error", "reboot", "setTaskAbnormal", "task 123"))
    print("Abnormal.setSRC", Abnormal.setSRC(24505, "task error", "reboot", "setTaskAbnormal"))
    print("Abnormal.setEnvironment", Abnormal.setEnvironment(24506, "task error", "reboot", "setTaskAbnormal"))
    print("Abnormal.setDevice", Abnormal.setDevice(24507, "task error", "reboot", "setTaskAbnormal", "task 123"))
    print("Abnormal.setConnect", Abnormal.setConnect(24508, "task error", "reboot", "setTaskAbnormal", "task 123"))
    print("Abnormal.setCalibration", Abnormal.setCalibrate(24509, "task error", "reboot", "setTaskAbnormal", "task 123"))
    print("Abnormal.setAPI", Abnormal.setAPI(24510, "task error", "reboot", "setTaskAbnormal", 2453))
    print("Abnormal.setLicense", Abnormal.setLicense(24511, "task error", "reboot", "setTaskAbnormal", "task 123"))
    print("Abnormal.setChassis", Abnormal.setChassis(24512, "task error", "reboot", "setTaskAbnormal"))


def test_trace():
    print("Trace.scriptEventInstant", Trace.event("script event instant"))
    print("Trace.scriptLog", Trace.log("setTrace", "trace 123"))


def main():
    while True:
        test_message()
        test_motor()
        test_abnormal()
        test_trace()
        time.sleep(0.01)


if __name__ == '__main__':
    main()