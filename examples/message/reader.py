import os.path
import sys
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../")

from syspy.v4.include.rbk import core, logger, datapool
import syspy.v4.include.protocol.messageV4_battery_pb2 as message_battery
import syspy.v4.include.google.protobuf.message as base_message
from syspy import Battery, Motor
from syspy.battery import BatteryInterface

def msg_cb(msg: base_message, timestamp: int):
    logger.LogInfo(f"callback, temperature: {msg.temperature}, timestamp: {timestamp}")


def subscribe_and_unsubscribe():
    flag = True
    while True:
        if flag:
            datapool.subscribe("battery", message_battery.MessageV4_Battery, msg_cb)
        else:
            datapool.unsubscribe("battery", message_battery.MessageV4_Battery)
        flag = not flag
        time.sleep(5)


def get_msg():
    while True:
        # 4.0电池消息channel不固定
        battery1 = BatteryInterface("battery1")
        print(f"{battery1.get_temperature()=}")
        print(f"{battery1.get_percentage()=}")
        logger.LogInfo(f"temperature: {battery1.get_temperature()}")
        logger.LogInfo(f"percentage: {battery1.get_percentage()}")
        # 3.5 TOPIC固定
        # print(f"{Battery.get_temperature()}")
        # print(f"{Battery.get_percentage()=}")

        motor_pos = Motor.get_motor_pos("Motor-001")
        print("motor_pos=", motor_pos)
        logger.LogInfo(f"motor_pos={motor_pos}")
        time.sleep(0.1)


name = "DatapoolExampleReader"
core.Init(name)

if len(sys.argv) == 1:
    get_msg()
else:
    subscribe_and_unsubscribe()
