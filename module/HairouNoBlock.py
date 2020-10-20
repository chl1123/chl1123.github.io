from enum import Enum, IntEnum
import struct
import socket
import json
import crc

class MessageType(IntEnum):
    ROBOT_INIT_REQ = 0
    ROBOT_INFO_REPORT = 10
    ROBOT_LIFT_RESET = 20
    ROBOT_LIFT_REQ = 21
    ROBOT_ROTATE_RESET = 30
    ROBOT_ROTATE_REQ = 31
    ROBOT_STRETCH_RESET = 40
    ROBOT_STRETCH_REQ = 41
    ROBOT_FINGER_RESET = 50
    ROBOT_FINGER_REQ = 51
    ROBOT_VISION_RESET = 60
    ROBOT_VISION_REQ = 61
    ROBOT_VISION_RECORD = 62
    ROBOT_INDICATOR_REQ = 70
    ROBOT_COMM_RESP = 255

class RunMode(IntEnum):
    ROBOT_WORKING = 1
    ROBOT_RECOVER = 2
    ROBOT_DEBUG = 3
    ROBOT_RESERVED = 4

class ModuleState(IntEnum):
    INIT = 0,
    RESET = 1
    IDLE = 2
    WORKING = 3
    ERROR = 4

class TargetType(IntEnum):
    SHELF = 1
    BOX = 2

class BinType(IntEnum):
    DM_MARKED = 0
    MARKERLESS = 10

class ErrorMessage:
    def __init__(self):
        self.errorcode = dict()
        self.errorcode[0] =["OK","成功，无错误"]
        self.errorcode[0x80000001] = ["E_SEQUENCE","指令序号错误"]
        self.errorcode[0x80000002] = ["E_PARSE","指令解析错误"]
        self.errorcode[0x80000003] = ["E_UNSUPPORT", "不支持的功能"]
        self.errorcode[0x80000004] = ["E_PARAMETER", "错误的参数"]
        self.errorcode[0x80000005] = ["E_OVERLIMIT","目标超出限制"]
        self.errorcode[0x80000006] = ["E_ABNORMAL","设备状态异常"]
        self.errorcode[0x800000FF] = ["E_UNKNOWN","未知错误"]
        self.errorcode[0x80000200] = ["E_SAFE_MANUAL","手动保护"]
        self.errorcode[0x80000201] = ["E_SAFE_STOPPER", "限位保护"]
        self.errorcode[0x80000202] = ["E_SAFE_LOCKING","限位保护"]
        self.errorcode[0x80000203] = ["E_SAFE_LOCKING","锁定保护"]
        self.errorcode[0x80000204] = ["E_SAFE_CONTROL","失控保护"]
        self.errorcode[0x80000300] = ["E_DEV_COM","设备通讯错误"]
        self.errorcode[0x80000301] = ["E_DEV_BUSY","设备已被占用"]
        self.errorcode[0x80000302] = ["E_DEV_SUPPORT","设备不能支持"]
        self.errorcode[0x80000303] = ["E_DEV_FAILURE","设备功能失效"]
        self.errorcode[0x80000304] = ["E_DEV_ABNORMAL","设备数据异常"]

class Hairou:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.tcp_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_client.setblocking(False)
        self.max_try_times = 20
        self.seqNum_req = 0
        self.isconnect = False
        self.msg_init = {"msgType":MessageType.ROBOT_INIT_REQ.value,
        "seqNum":0}
        self.msg_lift_reset = {"msgType":MessageType.ROBOT_LIFT_RESET.value,
        "seqNum":0}
        self.msg_lift_req = {"msgType":MessageType.ROBOT_LIFT_REQ.value,
        "seqNum":0,
        "liftPosition":0.0}
        self.msg_rot_rest = {"msgType":MessageType.ROBOT_ROTATE_RESET.value,
        "seqNum":0}
        self.msg_rot_req = {"msgType":MessageType.ROBOT_ROTATE_REQ.value,
        "seqNum":0,
        "rotatePosition":0.0}
        self.msg_stretch_reset = {"msgType":MessageType.ROBOT_STRETCH_RESET.value,
        "seqNum":0}
        self.msg_stretch_req = {"msgType":MessageType.ROBOT_STRETCH_REQ.value,
        "seqNum":0,
        "stretchPosition":0.0}
        self.msg_finger_reset = {"msgType":MessageType.ROBOT_FINGER_RESET.value,
        "seqNum":0}
        self.msg_finger_req = {"msgType":MessageType.ROBOT_FINGER_REQ.value,
        "seqNum":0,
        "position":0}      
        self.msg_vision_reset = {"msgType":MessageType.ROBOT_VISION_RESET.value,
        "seqNum":0}
        self.msg_vision_req = {"msgType":MessageType.ROBOT_VISION_REQ.value,
        "seqNum":0,
        "targetType":0,
        "binType":0}
        self.msg_vision_record = {"msgType":MessageType.ROBOT_VISION_RECORD.value,
        "seqNum":0,
        "imageId":"last"}
        self.msg_indicator_req = {"msgType":MessageType.ROBOT_INDICATOR_REQ.value,
        "seqNum":0,
        "chassisLedFront":0,
        "chassisLedBack":0,
        "buzzer":0,
        "headLedRed":0,
        "headLedYellow":0,
        "headLedGreen":0,
        "headLedFreq":0
        }
    def connect(self):
        try:
            self.tcp_client.connect((self.ip, self.port))
        except BlockingIOError:
            pass
    def disconnect(self):
        self.tcp_client.close()
    def getMsg(self, r):
        total_data = b""
        try:
            total_data = self.tcp_client.recv(1024)
        except:
            if r is not None: r.logDebug("ctu recv error!!!")
            return dict()                
        else:
            total_hex = total_data.hex()
            ind = total_hex.find("addecefa")
            if ind + 32 <= len(total_hex):
                head_hex = total_hex[ind:ind+32]
                fmt = "@IIII"
                try:
                    usMagic, usSize, crcBody, crcHead = struct.unpack(fmt, bytes.fromhex(head_hex))
                except:
                    out = dict()
                    out["error"] =  "length head {}".format(len(head_hex))
                    return out
                last_info = total_hex[ind+32:]
                # print("ind ", ind , "usSize", usSize, len(last_info))
                if usSize * 2 <= len(last_info):
                    body_hex = last_info[0:usSize*2]
                    fmt = "@"+str(usSize)+"s"
                    body = struct.unpack(fmt,bytes.fromhex(body_hex))
                    out = dict()
                    try:
                        out = json.loads(body[0])
                    except:
                        print("loads error!!!", body)
                        if r is not None: r.logDebug("ctu loads error!!! {}".format(body))
                        return out
                    else:
                        return out
        return dict()
    def initDevice(self, r):
        res =  self.sendMessage(self.msg_init, r)
        self.isconnect = res["flag"]
    def getReport(self, r):
        msg = self.getMsg(r)
        if 'msgType' not in msg or msg['msgType'] != MessageType.ROBOT_INFO_REPORT:
            print(" no report!!!")
            if r is not None: r.logDebug("ctu no report!!!")
            msg = dict()
            msg["flag"] = False
            msg["error"] = "no report!!!"
        return msg    
    def sendMessage(self, msg, r):
            usMagic = 0xFACEDEAD
            str_data = json.dumps(msg,separators=(',',':'))
            byte_data = str_data.encode()

            usSize = len(byte_data)
            crcBody = crc.crcbytes(byte_data)
            # print(byte_data, byte_data.hex())
            head_fmt = "@III"
            head_bytes = struct.pack(head_fmt, usMagic, usSize,crcBody)
            # print(head_bytes.hex())
            crcHead = crc.crcbytes(head_bytes)

            fmt = "@IIII"+str(usSize)+"s"
            # print(fmt)
            sends = struct.pack(fmt,usMagic,usSize,crcBody,crcHead,byte_data)
            if r is not None: r.logDebug(sends.hex())
            res_msg = dict()
            try:
                self.tcp_client.sendall(sends)
                res_msg["flag"] = True
            except:
                res_msg["flag"] = False
                res_msg["content"] = "send fail"
            return res_msg
    def liftReset(self, r):
        msg = self.msg_lift_reset
        self.seqNum_req = self.seqNum_req + 1
        msg["seqNum"] = self.seqNum_req
        return self.sendMessage(msg, r)
    def liftPos(self, height, r):
        msg = self.msg_lift_req
        self.seqNum_req = self.seqNum_req + 1
        msg["seqNum"] = self.seqNum_req
        msg["liftPosition"] = height
        return self.sendMessage(msg, r)
    def rotateReset(self, r):
        msg = self.msg_rot_rest
        self.seqNum_req = self.seqNum_req + 1
        msg["seqNum"] = self.seqNum_req
        return self.sendMessage(msg, r)
    def rotateAngle(self, theta, r):
        msg = self.msg_rot_req
        self.seqNum_req = self.seqNum_req + 1
        msg["seqNum"] = self.seqNum_req
        msg["rotatePosition"] = theta
        return self.sendMessage(msg, r)
    def stretchReset(self, r):
        msg = self.msg_stretch_reset
        self.seqNum_req = self.seqNum_req + 1
        msg["seqNum"] = self.seqNum_req
        return self.sendMessage(msg, r)
    def stretchPos(self, value, r):
        msg = self.msg_stretch_req
        self.seqNum_req = self.seqNum_req + 1
        msg["seqNum"] = self.seqNum_req
        msg["stretchPosition"] = value
        return self.sendMessage(msg, r)
    def fingerReset(self, r):
        msg = self.msg_finger_reset
        self.seqNum_req = self.seqNum_req + 1
        msg["seqNum"] = self.seqNum_req
        return self.sendMessage(msg, r)
    def fingerPos(self,value, r):
        msg = self.msg_finger_req
        self.seqNum_req = self.seqNum_req + 1
        msg["seqNum"] = self.seqNum_req
        msg["position"] = value
        self.sendMessage(msg, r)
        return msg
    def visionReset(self, r):
        msg = self.msg_vision_reset
        self.seqNum_req = self.seqNum_req + 1
        msg["seqNum"] = self.seqNum_req
        return self.sendMessage(msg, r)
    def visionReq(self, targetType, binType, r):
        msg = self.msg_vision_req
        self.seqNum_req = self.seqNum_req + 1
        msg["seqNum"] = self.seqNum_req
        msg["targetType"] = targetType
        msg["binType"] = binType
        return self.sendMessage(msg, r)
    def visionRecord(self, r):
        msg = self.msg_vision_record
        self.seqNum_req = self.seqNum_req + 1
        msg["seqNum"] = self.seqNum_req
        return self.sendMessage(msg, r)
    def indicatorReq(self, chassisLedFront = None, chassisLedBack = None, buzzer = None, headLedRed = None, headLedYellow = None, headLedGreen = None, headLedFreq = None, r= None):
        msg = self.msg_indicator_req
        self.seqNum_req = self.seqNum_req + 1
        msg["seqNum"] = self.seqNum_req
        if chassisLedFront is not None: 
            msg["chassisLedFront"] = chassisLedFront
        else:
            del msg["chassisLedFront"]
        if chassisLedBack is not None:
            msg["chassisLedBack"] = chassisLedBack
        else:
            del msg["chassisLedBack"]
        if buzzer is not None:
            msg["buzzer"] = buzzer
        else:
            del msg["buzzer"]
        if headLedRed is not None:
            msg["headLedRed"] = headLedRed
        else:
            del msg["headLedRed"]
        if headLedYellow is not None:
            msg["headLedYellow"] = headLedYellow
        else:
            del msg["headLedYellow"]
        if headLedGreen is not None:
            msg["headLedGreen"] = headLedGreen
        else:
            del msg["headLedGreen"]
        if headLedFreq is not None:
            msg["headLedFreq"] = headLedFreq
        else:
            del msg["headLedFreq"]
        return self.sendMessage(msg, r)

if __name__ == "__main__":
    h = Hairou("192.168.192.20",4172)
    r = None
    if h.connect():
        h.initDevice(r)
        h.indicatorReq(headLedRed = 1)
        state = h.getReport(r)
        print(state)
        h.disconnect()

