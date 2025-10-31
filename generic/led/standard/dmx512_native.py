import signal
import time
from typing import Optional
from syspy import Module, Trace
from syspy import Battery, Controller, NavStatus, NavSpeed
from syspy import Logger
from syspy.utils.param_server import ParamType, ScriptParam
from syspy.leds.led_base import LedBase
from syspy.leds.light_type import LightType, Color
from typing import List, Dict, Any
log = Logger("led_arm")

param_loader = ScriptParam(__file__)


def signal_handler(signal, frame):
    exit(0)

class ConfigParams:
    config = {}
    """配置管理器，用于管理动态配置参数"""
    devName = None
    rgbwColor = [0,0,0,0]
    rgbwChannel = [0,0,0,0]

    turnPos = [0,0,0,0]
    turnNum = [0,0,0,0]
    lightTotalNum = None
    
    is_show_charging = None
    is_show_battery = None
    is_back_breath = None
    dmx_test_flag = None
    

    def __init__(self):
        self._build_and_load_config()

    @classmethod
    def _build_and_load_config(cls):
        """构建并加载配置参数"""
        builder = param_loader.builder_config()

        with builder.GROUPS():
            with builder.GROUP(key="devName", name="Serial Port", desc="串行端口对应的设备名"):
                builder.TYPE(ParamType.STRING)
                builder.DEFAULTVALUE("/dev/ttyS8")
            with builder.GROUP(key="rgbwColor", name="RGBW Color", desc="RGBW十进制代码"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    with builder.CHILD(key="rColor", name="Red",
                                       desc="Red"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(Color.BlueCobalt.value[0], min_value=0, max_value=255)
                        builder.REQUIRED(True)
                    with builder.CHILD(key="gColor", name="Green",
                                       desc="Green"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(Color.BlueCobalt.value[1], min_value=0, max_value=255)
                        builder.REQUIRED(True)
                    with builder.CHILD(key="bColor", name="Blue",
                                       desc="Blue"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(Color.BlueCobalt.value[2], min_value=0, max_value=255)
                        builder.REQUIRED(True)
                    with builder.CHILD(key="wColor", name="Write",
                                       desc="Write"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(Color.BlueCobalt.value[3], min_value=0, max_value=255)
                        builder.REQUIRED(True)
                #builder.DEFAULTVALUE(Color.BlueCobalt.value)
            with builder.GROUP(key="rgbwChannel", name="RGBW Channel", desc="RGBW通道"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    with builder.CHILD(key="rChannel", name="Red Channel",
                                        desc="Red Channel"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(0, min_value=0, max_value=3)
                        builder.REQUIRED(True)
                    with builder.CHILD(key="gChannel", name="Green Channel",
                                        desc="Green Channel"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(2, min_value=0, max_value=3)
                        builder.REQUIRED(True)
                    with builder.CHILD(key="bChannel", name="Blue Channel",
                                        desc="Blue Channel"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(3, min_value=0, max_value=3)
                        builder.REQUIRED(True)
                    with builder.CHILD(key="wChannel", name="Write Channel",
                                        desc="Write Channel"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(1, min_value=0, max_value=3)
                        builder.REQUIRED(True)
                #builder.DEFAULTVALUE([0, 2, 3, 1])
            with builder.GROUP(key="turnPos", name="Turn Pos", desc="左前/左后/右前/右后方向的灯的位置"):
                builder.TYPE(ParamType.ARRAY)
                #builder.DEFAULTVALUE([4, 3, 1, 2])
                with builder.CHILDREN():
                    with builder.CHILD(key="turnPosLeftFront", name="Left Front",
                                        desc="Left front turn led pos"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(4, min_value=0, max_value=99)
                        builder.REQUIRED(True)
                    with builder.CHILD(key="turnPosLeftRear", name="Left Rear",
                                        desc="Left rear turn led pos"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(3, min_value=0, max_value=99)
                        builder.REQUIRED(True)
                    with builder.CHILD(key="turnPosRightFront", name="Right Front",
                                        desc="Right front turn led pos"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(1, min_value=0, max_value=99)
                        builder.REQUIRED(True)
                    with builder.CHILD(key="turnPosRightRear", name="Right Rear",
                                        desc="Right rear turn led pos"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(2, min_value=0, max_value=99)
                        builder.REQUIRED(True)
            with builder.GROUP(key="turnNum", name="Turn Num", desc="左前/左后/右前/右后方向的灯的灯条数"):
                builder.TYPE(ParamType.ARRAY)
                #builder.DEFAULTVALUE([1, 1, 1, 1])
                with builder.CHILDREN():
                    with builder.CHILD(key="turnNumLeftFront", name="Left Front",
                                        desc="Left front turn led num"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(1, min_value=0, max_value=99)
                        builder.REQUIRED(True)
                    with builder.CHILD(key="turnNumLeftRear", name="Left Rear",
                                        desc="Left rear turn led num"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(1, min_value=0, max_value=99)
                        builder.REQUIRED(True)
                    with builder.CHILD(key="turnNumRightFront", name="Right Front",
                                        desc="Right front turn led num"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(1, min_value=0, max_value=99)
                        builder.REQUIRED(True)
                    with builder.CHILD(key="turnNumRightRear", name="Right Rear",
                                        desc="Right rear turn led num"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(1, min_value=0, max_value=99)
                        builder.REQUIRED(True)
            with builder.GROUP(key="lightTotalNum", name="Light Total Num", desc="灯条总数"):
                builder.TYPE(ParamType.INT)
                builder.DEFAULTVALUE(4)  
            with builder.GROUP(key="showCharging", name="Show Charging", desc="是否显示充电状态"):
                builder.TYPE(ParamType.BOOL)
                builder.DEFAULTVALUE(True)
            with builder.GROUP(key="showBattery", name="Show Battery", desc="是否显示电池状态"):
                builder.TYPE(ParamType.BOOL)
                builder.DEFAULTVALUE(True)          
            with builder.GROUP(key="isBackBreath", name="IS Back Breath", desc="是否后退时亮白色呼吸灯"):
                builder.TYPE(ParamType.BOOL)
                builder.DEFAULTVALUE(False) 
            with builder.GROUP(key="DmxTestFlag", name="Dmx Test Flag", desc="DMX测试标志"):
                builder.TYPE(ParamType.BOOL)
                builder.DEFAULTVALUE(False) 
        builder.save(merge=True)
        
        cls.reload_config()

    @classmethod
    def reload_config(cls):
        """重新加载配置参数"""
        Trace.log("Reloading config parameters")
        cls.config = param_loader.load_config()
        Trace.log(f"Loaded config: {cls.config}")
        cls.devName = cls.config.get("devName")
        cls.rgbwColor[0] = cls.config.get("rColor")
        cls.rgbwColor[1] = cls.config.get("gColor")
        cls.rgbwColor[2] = cls.config.get("bColor")
        cls.rgbwColor[3] = cls.config.get("wColor")
        cls.rgbwChannel[0] = cls.config.get("rChannel")
        cls.rgbwChannel[1] = cls.config.get("gChannel")
        cls.rgbwChannel[2] = cls.config.get("bChannel")
        cls.rgbwChannel[3] = cls.config.get("wChannel")

        cls.turnPos[0] = cls.config.get("turnPosLeftFront")
        cls.turnPos[1] = cls.config.get("turnPosLeftRear")
        cls.turnPos[2] = cls.config.get("turnPosRightFront")
        cls.turnPos[3] = cls.config.get("turnPosRightRear")
        
        cls.turnNum[0] = cls.config.get("turnNumLeftFront")
        cls.turnNum[1] = cls.config.get("turnNumLeftRear")
        cls.turnNum[2] = cls.config.get("turnNumRightFront")
        cls.turnNum[3] = cls.config.get("turnNumRightRear")
        cls.lightTotalNum = cls.config.get("lightTotalNum")
        
        cls.is_show_charging = cls.config.get("showCharging")
        cls.is_show_battery = cls.config.get("showBattery")
        cls.is_back_breath = cls.config.get("isBackBreath")
        cls.dmx_test_flag = cls.config.get("DmxTestFlag")


        Trace.log(f"Updated config: {cls.config}")


# 创建全局配置管理器实例
config_params = ConfigParams()

def script_config_changed():
    Trace.log("Reloading script config parameters")
    config_params.reload_config()

class LedChassis(LedBase):
    def __init__(self):
        self.robot_status = None
        self.pre_robot_status = None
        super().__init__(config_params)

    def run(self):
        if self.init():
            while True:
                self.set_light_type()
                time.sleep(0.1)

    def set_light_type(self):
        percentage = Battery.get_percentage()
        if int(percentage * 100.0) == 0:
            battery_exist = False
        else:
            battery_exist = True
        self.handle_light_effects(percentage, battery_exist)
        if config_params.dmx_test_flag:
            self.set_effect(LightType.MutableBreath, rgbw=Color.Red, period=3200)

    def handle_light_effects(self, dmx_battery: Optional[float], battery_exist: bool):
        """
        根据当前状态处理灯光效果。

        :param dmx_battery: 电池电量
        :param battery_exist: 是否存在电池
        """

        # 报警状态下红色呼吸
        if self.is_alarm():
            self.robot_status = "Alarm"
            self.set_effect(
                LightType.MutableBreath, rgbw=Color.Red, period=3200
            )
        # 急停状态下暗红色流水
        elif Controller.get_emc():
            self.robot_status = "EStop"
            self.set_effect(
                LightType.Flow, rgbw=Color.RedDark, period=10
            )
        # 被阻挡状态下粉紫色跑马
        elif NavStatus.get_block():
            self.robot_status = "Blocked"
            self.set_effect(
                LightType.MutableHorseRace, rgbw=Color.PinkPurple, period=1000
            )
        # 机器移动时的灯光效果
        elif not NavStatus.getChassisStop():
            self.robot_status = "Moving"
            self.handle_movement_effect()
        # 电池相关的灯光效果
        elif battery_exist:
            self.handle_battery_effects(dmx_battery)
        # 其他情况
        else:
            self.set_effect(LightType.Rainbow)
            log.warning("Effect set to Rainbow.")

        # 仅在状态变化时打印
        if self.robot_status != self.pre_robot_status:
            log.info("robot_status=" + self.robot_status)
            self.pre_robot_status = self.robot_status

    def handle_movement_effect(self) -> None:
        """
        处理机器移动时的灯光效果。
        """
        v_x, _, v_w = NavSpeed.get_speeds()
        turn = NavStatus.get_turn(v_x, v_w)
        if turn == 0:
            self.robot_status = "MovingRotation"
            if config_params.is_back_breath and v_x < 0:
                self.set_effect(LightType.MutableBreath, rgbw=Color.White, period=3200)
            else:
                self.set_effect(LightType.MutableBreath, period=3200)
        else:
            self.robot_status = "MovingTurn"
            led_idx = self.turn_to_led_idx(turn)
            self.set_effect(LightType.Blink, rgbw=Color.Yellow, led_idx=led_idx)

    def handle_battery_effects(self, dmx_battery: Optional[float]) -> None:
        """
        处理电池相关的灯光效果。

        :param dmx_battery: 电池电量
        """
        #### # 充电中为呼吸灯，颜色根据电池电量变化    废弃，保持与DSP一致
        # 黄色 R255 B165
        if config_params.is_show_charging and Battery.get_is_charging():
            self.robot_status = "Charging"
            rgbw = self.battery_to_color(dmx_battery)
            self.set_effect(
                LightType.MutableBreath, rgbw=Color.ChargeYellow, period=3200
            )
        # 电量过低为暗红色跑马灯
        elif dmx_battery * 100 < 10:
            self.robot_status = "LowBattery"
            self.set_effect(
                LightType.MutableHorseRace, rgbw=Color.RedDark,period=2000
            )
        # 常亮灯，颜色根据电池电量变化
        elif config_params.is_show_battery:
            self.robot_status = "Battery"
            rgbw = self.battery_to_color(dmx_battery)
            self.set_effect(
                LightType.ConstantLight, rgbw=rgbw
            )
        # 蓝色常亮
        else:
            self.robot_status = "Normal"
            self.set_effect(LightType.ConstantLight)


if __name__ == "__main__":
    ScriptParam.setConfigChangeCallBack(script_config_changed)
    signal.signal(signal.SIGINT, signal_handler)
    Module.init()
    tape_light = LedChassis()
    tape_light.run()
