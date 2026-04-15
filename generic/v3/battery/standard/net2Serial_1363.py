
#导入电池基类
import syspy.battery_Serial.battery_base as bb
#处理字符的工具类  
import syspy.lib.char_utility as cu 
#其他工具类,如定时器 
import syspy.lib.misc_utility as mu
import syspy.lib.udp_debug as ud
from syspy import Trace
import threading
import os
import signal
import sys
from syspy import RobotParam, Module, ScriptStatus
class Battery(bb.batteryBase):
    def __init__(self):
        super(Battery,self).__init__()
        self.connect_timeout_t = mu.Timer(6000)
        self.data_buff = [] 
        self.msg_ok = False
        
        self._stop_event = threading.Event()
        self._send_event = threading.Event()  # 允许发送

        self._send_event.set()  # 初始允许发送
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
                Trace.log(f'send set')
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
                Trace.log(f'send set')
                self._send_event.set()
                
                self.clearTimeout()
                self.data_buff.clear()
                self.msg_ok = True

    def judgeMsgok(self):
        if self.msg_ok:
            self.msg_ok = False
            self.connect_timeout_t.reset()
        else:
            if self.connect_timeout_t.isTimeUp():
                self.setTimeout()
                Trace.log(f"Connection timeout")

    def loop(self):
        while True:
            request = [0x7E, 0x32, 0x30, 0x30, 0x31, 0x34, 0x36, 0x34, 0x32, 0x45, 0x30, 0x30, 0x32, 0x30, 0x31, 0x46,
                       0x44, 0x33, 0x35, 0x0D]
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