from syspy import Battery, Module
from syspy.v4.lib.rbk import logger, datapool
import google.protobuf.message as base_message
import sys
import time


def msg_cb(msg: base_message, timestamp: int):
    logger.LogInfo(f"callback, temperature: {msg.temperature}, timestamp: {timestamp}")


def subscribe_and_unsubscribe():
    import syspy.v4.protobuf.message.messageV4_battery_pb2 as message_battery

    flag = True
    while True:
        if flag:
            datapool.subscribe("Battery-000", message_battery.MessageV4_Battery, msg_cb)
        else:
            datapool.unsubscribe("Battery-000", message_battery.MessageV4_Battery)
        flag = not flag
        time.sleep(5)


def get_msg():
    channel_name_0 = "Battery-000"
    channel_name_1 = "Battery-001"

    while True:
        # 默认topic为Battery-000
        print(f"{channel_name_0} get_temperature", Battery.get_temperature())
        print(f"{channel_name_0} get_percentage", Battery.get_percentage())

        # 指定topic为Battery-001
        channel_name_1 = "Battery-001"
        print(
            f"{channel_name_1} get_temperature",
            Battery.get_temperature(topic=channel_name_1),
        )
        print(
            f"{channel_name_1} get_percentage",
            Battery.get_percentage(topic=channel_name_1),
        )

        time.sleep(1)


def main():
    name = "pyDatapoolExampleReader"
    Module.init(name)

    if len(sys.argv) == 1:
        get_msg()
    else:
        subscribe_and_unsubscribe()


if __name__ == "__main__":
    main()
