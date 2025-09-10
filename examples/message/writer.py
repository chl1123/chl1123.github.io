import time
from syspy import Module
from syspy.v4.include.rbk import logger, datapool
import syspy.v4.include.protocol.messageV4_battery_pb2 as message_battery
from syspy import Battery

def main():
    name = "DatapoolExampleWriter"
    Module.init(name)

    # datapool.publish("Odom", messageV4_movetask_pb2.MessageV4_Odo)

    temperature = 0
    count = 0
    while True:
        count += 1
        temperature += 1
        battery = message_battery.MessageV4_Battery()
        battery.temperature = temperature
        battery.percetage = temperature + 1
        print("battery: ", battery)
        Battery.publish(battery, topic="Battery-000")
        battery.temperature = -temperature
        battery.percetage = -temperature - 1
        Battery.publish(battery, topic="Battery-001")
        logger.LogInfo(f"put, temperature: {battery.temperature}")

        # 创建并填充 MessageV4_Odo 消息
        # odo = messageV4_movetask_pb2.MessageV4_Odo()
        # odo.header.sequence = 1  # 假设 header 已定义
        # odo.cycle = 100
        # odo.x = 1.2
        # odo.y = 3.4
        # odo.angle = 0.785  # 45 degrees in radians
        # odo.is_stop = False
        # odo.vel_x = 0.5
        # odo.vel_y = 0.0
        # odo.vel_rotate = 0.1

        # # 添加多个 motor_info
        # for i in range(3):
        #     motor = odo.motor_info.add()
        #     motor.header.sequence = i
        #     motor.motor_name = f"Motor-00{i}"
        #     motor.can_router = 0x10 + i
        #     motor.can_id = 0x20 + i
        #     motor.position = count * i * 0.1
        #     motor.speed = 0.2 * i
        #     motor.current = 1.5
        #     motor.voltage = 24.0
        #     motor.stop = False
        #     motor.error_code = 0
        #     motor.err = False
        #     motor.emc = False
        #     motor.temperature = 30.0 + i
        #     motor.encoder = 1000 + i * 10
        #     motor.type = messageV4_movetask_pb2.MessageV4_MInfo.MotorType.Value('WALK')  # 使用枚举值
        #     motor.passive = False
        #     motor.calib = True
        #     motor.follow_err = False
        #     motor.raw_position = motor.position
        # print("odo", odo)
        # datapool.put("Odom", odo)
        time.sleep(1)

if __name__ == '__main__':
    main()