from syspy import Battery
from syspy import Module
from syspy.v4.lib.rbk import logger
import syspy.v4.protobuf.message.messageV4_battery_pb2 as message_battery
import time


def main():
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
        logger.LogInfo(f"{channel_name_0}, temperature: {msg_battery.temperature}")

        msg_battery.temperature = -temperature
        msg_battery.percetage = -temperature - 1
        Battery.publish(msg_battery, topic=channel_name_1)
        logger.LogInfo(f"{channel_name_1}, temperature: {msg_battery.temperature}")

        time.sleep(1)


if __name__ == "__main__":
    main()
