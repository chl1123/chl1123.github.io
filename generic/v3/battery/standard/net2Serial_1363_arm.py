
import os
import threading
#导入电池基类
import syspy.battery_Serial.battery_base as bb
#处理字符的工具类，处理字符的工具类，如将uint16_t的数据转换成int16_t,
#用途:负号转换，将两个字节数据组合成一个16位的数据，其他数据处理需要自行编写。
import syspy.lib.char_utility as cu
#其他工具类,如定时器
import syspy.lib.misc_utility as mu
from syspy import Logger
from syspy.utils.param_server import ParamType, ScriptParam
from syspy import Trace, RobotParam, Module, ScriptStatus
from syspy.lib.module import ModuleBase
from typing import List, Dict, Any
import signal
import sys
from syspy import Trace

param_loader = ScriptParam(__file__) 
class ConfigParams:
    config = {}
    """配置管理器，用于管理动态配置参数"""
    devName = None
    baudrate = None
    timeoutThreshold = None
    def __init__(self):
        self._build_and_load_config()

    @classmethod
    def _build_and_load_config(cls):
        """构建并加载配置参数"""
        builder = param_loader.builderConfig()

        with builder.GROUPS():
            with builder.GROUP(key="devName", name="Serial Port", desc="串行端口对应的设备名"):
                builder.TYPE(ParamType.STRING)
                builder.DEFAULTVALUE("/dev/RS485_0")
            with builder.GROUP(key="baudrate", name="Baudrate", desc="波特率"):
                builder.TYPE(ParamType.UINT)
                builder.DEFAULTVALUE(9600)  
            with builder.GROUP(key="timeoutThreshold", name="timeoutThreshold", desc="超时时间阈值(ms)"):
                builder.TYPE(ParamType.UINT)
                builder.DEFAULTVALUE(2000)
        builder.save(merge=True)
        
        cls.reload_config()

    @classmethod
    def reload_config(cls):
        """重新加载配置参数"""
        Trace.log("Reloading config parameters")
        cls.config = param_loader.loadConfig()
        Trace.log(f"Loaded config: {cls.config}")
        cls.devName = cls.config.get("devName")
        cls.baudrate = cls.config.get("baudrate")
        cls.timeoutThreshold = cls.config.get("timeoutThreshold")

        Trace.log(f"Updated config: {cls.config}")
        #Trace.log("dev_name=" + str(self.devName) + " baudrate=" + str(self.baudrate) + " timeoutThreshold=" + str(self.timeoutThreshold))


# 创建全局配置管理器实例
config_params = ConfigParams()

class Battery(bb.batteryBase):
    """
    继承电池基类
    """
    def __init__(self):
        #初始化基类,必须做
        super(Battery,self).__init__()
        # aarch64穿透需要初始化串口信息，880控制器串口uart0对应/dev/ttyS8
        self.createSerial(config_params.devName, config_params.baudrate)
        Trace.log(f'Create Serial Finished')
        #创建一个超时定时器
        self.connect_timeout_t = mu.Timer(config_params.timeoutThreshold)
        self.reset_timeout_t = mu.Timer(config_params.timeoutThreshold + 8000)
        #创建一个列表用来缓冲接收数据
        self.data_buff = []
        #用来表示数据是否已经正确接收
        self.msg_ok = False
        self._stop_event = threading.Event()
        self._send_event = threading.Event()

        self._send_event.set() 
        Trace.log(f'Class Init Finished')

    def handleData(self, msg:list):
        if self._stop_event.is_set():
            return
        # #存入收到的数据到缓冲中
        # if len(self.data_buff)==0 or len(self.data_buff)>112:
        #     if len(self.data_buff)>112:
        #         self.data_buff = []
        #         Trace.log(f'sema_a release')
        #         self.sema_a.release()
        #     Trace.log(f'sema_b acquire')
        #     self.sema_b.acquire()
            
            
        self.data_buff.extend(msg)
        #print(len(self.data_buff))
        while len(self.data_buff) >= 112:
            if self.data_buff[0] != 0x7E:
                self.data_buff.clear()
                Trace.log(f'send set 1')
                self._send_event.set()   # 解锁发送
                return
            try:
                self.data_buff=self.data_buff[1:-1]
                result = []
                for i in range(0, len(self.data_buff), 2):  
                    if i + 1 < len(self.data_buff): 
                        combined_value = int(chr(self.data_buff[i]) + chr(self.data_buff[i + 1]) ,16) 
                        result.append(combined_value)   
                cell_num=result[8]
                temper_base=8+2*cell_num+1
                temper_num=result[temper_base]
                pack_base=temper_base+2*temper_num+1

                current=(result[pack_base] << 8 & 0xFF00)|(result[pack_base+1]& 0x00FF)
                if current >= 0x8000:
                    current -= 0x10000
                current*=(0.01)


                voltage=(result[pack_base+2] << 8 & 0xFF00)|(result[pack_base+3]& 0x00FF)
                voltage*=(0.001)

                percentage=(result[pack_base+4] << 8 & 0xFF00)|(result[pack_base+5]& 0x00FF)

                percentage/=(result[pack_base+7] << 8 & 0xFF00)|(result[pack_base+8]& 0x00FF)
                circle=(result[pack_base+9] << 8 & 0xFF00)|(result[pack_base+10]& 0x00FF)
                temp16_0=(result[temper_base+1] << 8 & 0xFF00)|(result[temper_base+2]& 0x00FF)
                temp16_1=(result[temper_base+3] << 8 & 0xFF00)|(result[temper_base+4]& 0x00FF)
                temp16_2=(result[temper_base+5] << 8 & 0xFF00)|(result[temper_base+6]& 0x00FF)

                temperature=max(temp16_0,temp16_1,temp16_2)-40


                battery_info = self.createBatteryMessage()
                #解析后塞入相应字段
                battery_info.percentage = percentage
                battery_info.temperature = temperature
                battery_info.cycle=circle
                battery_info.chargeCurrent = current
                battery_info.chargeVoltage = voltage
                battery_info.SOH = int(100)
                #发步电池数据给rbk
                self.publish(battery_info)
                Trace.log("Receive Success")
            except Exception as e:
                    Trace.log(f"Error in handleData: {e}")
            finally:
                Trace.log(f'send set 2')
                self._send_event.set()
                
                self.clearTimeout()
                self.data_buff.clear()
                self.msg_ok = True



    def judgeMsgok(self):
        if self.msg_ok:
            self.msg_ok = False
            self.connect_timeout_t.reset()
            self.reset_timeout_t.reset()
        else:
            if self.connect_timeout_t.isTimeUp():
                self.setTimeout()
                Trace.log(f"Connection timeout")
            if self.reset_timeout_t.isTimeUp():
                self.closeSerial()
                self.__init__()

    def loop(self):
        """
        循环,处理发送及超时逻辑
        """
        while not self._stop_event.is_set():
            if self._stop_event.is_set():
                break
            request = [0x7E, 0x32, 0x30, 0x30, 0x31, 0x34, 0x36, 0x34, 0x32, 0x45, 0x30, 0x30, 0x32, 0x30, 0x31, 0x46,
                       0x44, 0x33, 0x35, 0x0D]
            if self._send_event.wait(timeout=5):
                self.send(request)
            self.judgeMsgok()
            mu.sleepS(2)
    def stop(self):
        Trace.log("Stopping thread...")
        self._stop_event.set()
        os._exit(1)  # 直接杀掉进程,以顺利退出
        self._send_event.set()


if __name__ == '__main__':
    Trace.log(f"Scripts Start.")
    Module.init()
    client = Battery()
    
    def handle_exit(signum, frame):
        Trace.log("Exit detected, stopping client...")
        client.stop()
        sys.exit(0)  #当主线程阻塞时退出方式无效
    
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    try:
        client.loop()
    except KeyboardInterrupt:
        handle_exit(None, None)