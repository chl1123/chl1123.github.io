import json
import socket
import struct

PACK_FMT_STR = '!BBHLH6s'


class rbklib:
    def __init__(self, ip, timeout_s=0.2):
        self.ip = ip
        self.RBK_VERSION = 0
        self.rbk_full_version = ""
        try:
            # 机器人状态 socket
            self.so_19204 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.so_19204.connect((self.ip, 19204))
            self.so_19204.settimeout(timeout_s)
        except:
            self.so_19204 = None
            print("RBK client error")

    def request(self, msgType, reqId=1, msg=None,
                sock=None):
        """
        发送请求

        :param msgType: 报文类型
        :param reqId: 序号
        :param msg: 消息体/数据区
        :param so:  使用指定的socket
        :return: 响应，包含报文头和报文体的元组，报文头[2：序号 3：报文体长度 4：报文类型]
        """
        if sock:
            # 如果指定了socket，则使用指定的socket,否则使用报文类型对应的socket
            so = sock
        elif 1000 <= msgType < 2000:
            so = self.so_19204
        else:
            # 如果报文类型不在范围内，则抛出异常
            raise ValueError("没有与报文类型对应的socket,或者需要指定一个socket")
        ################################################################################################################
        # 打印socket信息
        # print("*" * 20, "socket信息", "*" * 20)
        # print(f"{'socket:':>10}\tserver{so.getpeername()},local{so.getsockname()}")
        # print()
        ################################################################################################################
        # 封装报文
        if msg is not None:
            # 如果报文体不为空，则使用报文体
            if isinstance(msg, (dict, list)):
                # 如果报文体是dict或者list，则转换成字节
                body = bytearray(json.dumps(msg), "ascii")
            else:
                # 如果报文体是bytes或者bytearray，则直接使用
                body = msg
            msgLen = len(body)
        else:
            msgLen = 0
        rawMsg = struct.pack(PACK_FMT_STR, 0x5A, 0x01, reqId, msgLen, msgType, b'\x00\x00\x00\x00\x00\x00')
        ################################################################################################################
        # 打印请求报文信息
        # print("*" * 20, "请求信息", "*" * 20)
        # print(f"{'时间:':　>6}\t", datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"), sep='')
        # print(f"{'报文类型:':　>6}\t{msgType}\t{msgType:#06X}")
        # print(f"{'序号:':　>6}\t{reqId}\t{reqId:#06X}")
        # print(f"{'报文体长度:':　>6}\t{msgLen}\t{msgLen:#010X}")
        # if msgLen == 0:
        #     print(f"{'报文体:':　>6}\t无")
        # else:
        #     print(f"{'报文体:':　>6}\t{body[:1000]}")
        #     if msgLen > 1000:
        #         print("...")
        # print()
        ################################################################################################################
        # 发送报文
        if msgLen > 0:
            rawMsg += body
        totalsent = 0
        while totalsent < msgLen + 16:
            sent = so.send(rawMsg[totalsent:])
            if sent == 0:
                raise RuntimeError("socket connection broken")
            totalsent = totalsent + sent
        # 接收报文头
        headData = so.recv(16)
        # 解析报文头
        header = struct.unpack(PACK_FMT_STR, headData)
        # 获取报文体长度
        bodyLen = header[3]
        readSize = 1024
        recvData = b''
        while (bodyLen > 0):
            recv = so.recv(readSize)
            recvData += recv
            bodyLen -= len(recv)
            if bodyLen < readSize:
                readSize = bodyLen
        ################################################################################################################
        # 打印响应报文信息
        # print("*" * 20, "响应信息", "*" * 20)
        # print(f"{'时间:':　>6}\t", datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"), sep='')
        # print(f"{'报文类型:':　>6}\t{header[4]}\t{header[4]:#06X}")
        # print(f"{'序号:':　>6}\t{header[2]}\t{header[2]:#06X}")
        # print(f"{'报文体长度:':　>6}\t{header[3]}\t{header[3]:#010X}")
        # print(f"{'报文体:':　>6}\t{recvData[:1000]}")
        # if header[3] > 1000:
        #     print("...")
        # print()
        ################################################################################################################
        return header, recvData

    def request_rbk_version(self):
        """
        查询机器人信息
        """
        try:
            if self.so_19204:
                rbk_info = json.loads(self.request(1000)[1].decode())
                self.rbk_full_version = rbk_info.get("version", "")
                if self.rbk_full_version:
                    self.RBK_VERSION = int(self.rbk_full_version.split("v")[1].split(".")[0])
                else:
                    self.RBK_VERSION = rbk_info.get("version", 0)
        except socket.timeout:
            print("socket timeout")
        if self.RBK_VERSION == 0:
            try:
                with open('/etc/srcname', 'r') as f:
                    output = f.read().strip()
                    if output.startswith("SRC5000"):
                        self.RBK_VERSION = 4
                    else:
                        self.RBK_VERSION = 3  # 默认版本
            except FileNotFoundError:
                self.RBK_VERSION = 3

    def get_rbk_version(self):
        return self.RBK_VERSION

    def get_full_version(self):
        return self.rbk_full_version


r = rbklib("127.0.0.1", 0.2)
r.request_rbk_version()

RBK_VERSION = r.get_rbk_version()
RBK_FULL_VERSION = r.get_full_version()
print(f"{RBK_VERSION=}")
print(f"{RBK_FULL_VERSION=}")
