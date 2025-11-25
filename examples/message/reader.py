from syspy import Battery, Module
from syspy.v4.lib.rbk import logger, datapool
import google.protobuf.message as base_message
import syspy.v4.protobuf.message.messageV4_battery_pb2 as message_battery
import time


def msg_cb(msg: base_message, timestamp: int):
    logger.LogInfo(f"[callback|temperature|{msg.temperature}|timestamp|{timestamp}]")


name = "pyDatapoolExampleReader"
Module.init(name)

datapool.subscribe(
    "/BatteryInfo/Battery-000", message_battery.MessageV4_Battery, msg_cb
)

channel_name_0 = "Battery-000"
channel_name_1 = "Battery-001"

while True:
    # 默认topic为Battery-000
    temperature = Battery.getTemperature()
    percentage = Battery.getPercentage()
    logger.LogInfo(
        f"[get|{channel_name_0}|temperature|{temperature}|percentage|{percentage}]"
    )

    # 指定topic为Battery-001
    temperature = Battery.getTemperature(topic=channel_name_1)
    percentage = Battery.getPercentage(topic=channel_name_1)
    logger.LogInfo(
        f"[get|{channel_name_1}|temperature|{temperature}|percentage|{percentage}]"
    )

    time.sleep(1)
