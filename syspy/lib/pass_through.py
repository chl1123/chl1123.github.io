import threading, zmq, time, sys
import syspy.lib.udp_debug as ud

# 导入protobuf定义
try:
    from syspy.v3.protobuf.message import CanFrame_pb2
except ImportError:
    print("Warning: CanFrame_pb2 not found, falling back to bytes comparison")



class callBack:
    def handleData(self, msg):
        pass


class passThrough:
    def __init__(self,pass_type):
        self.context = zmq.Context()
        self.__client_sock = self.context.socket(zmq.DEALER)
        
        
        self.__addr = ""
        self.__conn_id = ""
        self.__msg_thread = None
        self.__should_close = False
        self.__callback = None
        self.__lock = threading.Lock()  # 创建锁对象
        self.__pass_type = None
        if pass_type == "can":
            self.__pass_type = True
            print("Use Can Pass")
        elif pass_type == "serial":
            self.__pass_type = False
            print("Use Serial Pass")
        else:
            print("passThrough type error.It should be 'can' or 'serial'")
        print("passThrough start with real-time message settings (HWM=1)")

    def close(self):
        print("close the socket")
        self.__should_close = True
        time.sleep(0.01)
        try:
            self.__client_sock.close(0)  # 立即关闭
        except Exception as e:
            print("socket close error:", e)
        if self.__msg_thread and self.__msg_thread.is_alive():
            self.__msg_thread.join(timeout=0.1)
        
        try:
            self.context.term()
        except Exception as e:
            print("context term error:", e)
        print("passThrough closed.")


    def setCallBack(self, callback):
        self.__callback = callback

    def serialConnect(self, addr):
        self.__addr = addr
        now = time.time()
        self.__conn_id = "py_client_" + str(now)
        self.__msg_thread = threading.Thread(target=self.__run, name="run",daemon=True)
        self.__msg_thread.start()  # FIXME: when to join?

    def canConnect(self, addr, connid):
        self.__addr = addr
        self.__conn_id = connid
        self.__msg_thread = threading.Thread(target=self.__run, name="run",daemon=True)
        self.__msg_thread.start()  # FIXME: when to join?

    def __run(self):
        identity = self.__conn_id
        self.__client_sock.identity = identity.encode("utf8")
        self.__client_sock.connect(self.__addr)
        poll = zmq.Poller()
        poll.register(self.__client_sock, zmq.POLLIN)
        try:
            while not self.__should_close:
                # 使用更短的轮询间隔以获得更好的实时性 (5ms)
                sockets = dict(poll.poll(5))
                if self.__client_sock in sockets:
                    self.__receive()
        except Exception as e:
            print("passThrough exception:", e)

        finally:
            print("finished passThrough")

    def __receive(self):
        with self.__lock:
            if self.__pass_type:
                latest_msg = {}
                # 持续读取直到队列为空
                while True:
                    try:
                        # 非阻塞接收
                        msg = self.__client_sock.recv(zmq.NOBLOCK)
                        rec_canframe = CanFrame_pb2.CanFrame()
                        rec_canframe.ParseFromString(msg)
                        latest_msg[rec_canframe.id]=msg
                    except zmq.Again:
                        # 队列已空，跳出循环
                        break

                if len(latest_msg) > 0:
                    #print(f"实时消息: 收到{len(latest_msg)}种类型")
                    for msg_data in latest_msg.values():
                        if not self.__callback is None:
                            self.__callback(msg_data)
            else:
                msg = self.__client_sock.recv(zmq.NOBLOCK)
                if not self.__callback is None:
                    self.__callback(msg)


    def send(self, data):
        with self.__lock:
            self.__client_sock.send(data)


if __name__ == "__main__":
    pass
