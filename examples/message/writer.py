from syspy import Battery, Module
from syspy.v4.lib.rbk import logger
import syspy.v4.protobuf.message.messageV4_battery_pb2 as message_battery
import time


name = "pyDatapoolExampleWriter"
Module.init(name)

channel_name_0 = "Battery-000"
channel_name_1 = "Battery-001"

temperature = 0
while True:
    msg_battery = message_battery.MessageV4_Battery()
    temperature += 1

    msg_battery.temperature = temperature
    msg_battery.percetage = temperature + 1
    Battery.publish(msg_battery, topic=channel_name_0)
    logger.LogInfo(
        f"[put|{channel_name_0}|temperature|{msg_battery.temperature}|percentage|{msg_battery.percetage}]"
    )

    msg_battery.temperature = -temperature
    msg_battery.percetage = -temperature - 1
    Battery.publish(msg_battery, topic=channel_name_1)
    logger.LogInfo(
        f"[put|{channel_name_1}|temperature|{msg_battery.temperature}|percentage|{msg_battery.percetage}]"
    )

    time.sleep(1)
