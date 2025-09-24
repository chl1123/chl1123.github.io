import sys

if len(sys.argv) != 2 or not sys.argv[1] in ["get", "callback"]:
    print("Usage: python3 reader.py <get|callback>")
    sys.exit(1)


from syspy import Battery, Module
from syspy.v4.lib.rbk import logger, datapool
import google.protobuf.message as base_message
import syspy.v4.protobuf.message.messageV4_battery_pb2 as message_battery
import time


def msg_cb(msg: base_message, timestamp: int):
    logger.LogInfo(f"[callback|temperature|{msg.temperature}|timestamp|{timestamp}]")


def subscribe_and_unsubscribe():
    flag = True
    while True:
        if flag:
            datapool.subscribe(
                "/BatteryInfo/Battery-000", message_battery.MessageV4_Battery, msg_cb
            )
        else:
            datapool.unsubscribe(
                "/BatteryInfo/Battery-000", message_battery.MessageV4_Battery
            )
        flag = not flag
        time.sleep(5)


def get_msg():
    channel_name_0 = "Battery-000"
    channel_name_1 = "Battery-001"

    while True:
        # 默认topic为Battery-000
        temperature = Battery.get_temperature()
        percentage = Battery.get_percentage()
        logger.LogInfo(
            f"[get|{channel_name_0}|temperature|{temperature}|percentage|{percentage}]"
        )

        # 指定topic为Battery-001
        temperature = Battery.get_temperature(topic=channel_name_1)
        percentage = Battery.get_percentage(topic=channel_name_1)
        logger.LogInfo(
            f"[get|{channel_name_1}|temperature|{temperature}|percentage|{percentage}]"
        )

        time.sleep(1)


name = "pyDatapoolExampleReader"
Module.init(name)

if sys.argv[1] == "get":
    get_msg()
else:
    subscribe_and_unsubscribe()
