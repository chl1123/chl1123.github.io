import time
from syspy import Battery, Controller, Move, NavSpeed, Bin


def get_battery():
    print("battery percentage: ", Battery.get_percentage())
    print("is charging: ", Battery.get_is_charge())
    print("battery datas: ", Battery.get_data())
    print("battery datas percetage is_charging: ", Battery.get_data(["percetage", "is_charging"]))


def get_controller():
    print("controller: ", Controller.get_emc())


def get_move():
    print("move: ", Move.get_block())


def get_navigation():
    print("navigation: ", NavSpeed.get_speed())


def get_bin():
    print("Bin.get_bin(): ", Bin.get_bins())

def main():
    while True:
        get_battery()
        get_controller()
        get_move()
        get_navigation()
        get_bin()
        time.sleep(1)


if __name__ == '__main__':
    main()
