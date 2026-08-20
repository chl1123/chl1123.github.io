import os
import threading
#导入电池基类
import syspy.battery_Serial.battery_base as bb
#其他工具类,如定时器
import syspy.lib.misc_utility as mu
from syspy.utils.param_server import ParamType, ScriptParam
from syspy import Trace, Module

from syspy.battery_runner import run_battery_script

class Battery(bb.batteryBase):
    """
    继承电池基类
    """
    def __init__(self):
        #初始化基类,必须做
        super(Battery,self).__init__()
        self.port = self.getBatterySerialPort()
        self.baudrate = self.getBatterySerialBaudrate()
        self.timeoutThreshold = 2000
        self.createSerial(self.port, self.baudrate)
        Trace.log(f'Create Serial Finished')
        #创建一个超时定时器
        self.connect_timeout_t = mu.Timer(self.timeoutThreshold)
        self.reset_timeout_t = mu.Timer(self.timeoutThreshold + 8000)
        #创建一个列表用来缓冲接收数据
        self.data_buff = []
        #用来表示数据是否已经正确接收
        self.msg_ok = False
        self._stop_event = threading.Event()
        self._send_event = threading.Event()

        self._send_event.set()
        Trace.log(f'Class Init Finished')

    FRAME_MIN = 30            # 响应帧最小长度(远小于真实帧,用于滤除短噪声)
    REQ_ECHO_LEN = 20        # 回显的请求帧字节数(透传会把本机发出的请求也透传回来)
    DEBUG = False

    def handleData(self, msg:list):
        if self._stop_event.is_set():
            return

        if self.DEBUG:
            raw = msg if isinstance(msg, bytes) else bytes(msg)
            Trace.log(f"[dbg] recv len={len(raw)} hex={raw.hex()} buff={len(self.data_buff)}")

        self.data_buff.extend(msg)
        while len(self.data_buff) >= self.REQ_ECHO_LEN:
            if self.data_buff[0] != 0x7E:
                if self.DEBUG:
                    Trace.log(f"[dbg] skip byte=0x{self.data_buff[0]:02X} buff_first3={self.data_buff[:3]}")
                self.data_buff.pop(0)
                self._send_event.set()   # 解锁发送
                continue
            end = 1
            while end < len(self.data_buff) and self.data_buff[end] != 0x0D:
                end += 1
            if end >= len(self.data_buff):
                # 整帧尚未到齐,等待后续数据
                break
            frame_len = end + 1
            frame = self.data_buff[:frame_len]
            del self.data_buff[:frame_len]
            if frame_len == self.REQ_ECHO_LEN:
                if self.DEBUG:
                    Trace.log(f"[dbg] drop cmd echo frame={bytes(frame).hex()}")
                continue
            if frame_len < self.FRAME_MIN:
                if self.DEBUG:
                    Trace.log(f"[dbg] short len={frame_len} hex={bytes(frame).hex()}")
                continue
            try:
                body = frame[1:-1]
                result = []
                for i in range(0, len(body), 2):
                    if i + 1 < len(body):
                        combined_value = int(chr(body[i]) + chr(body[i + 1]) ,16)
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
                self.clearTimeout()
                self.msg_ok = True
                Trace.log("Receive Success")
            except Exception as e:
                Trace.log(f"Error in handleData: {e}")
            finally:
                self._send_event.set()

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
    run_battery_script(Battery)
