import threading, zmq, time, sys

from syspy.lib.trace import Trace


# 导入protobuf定义
try:
    from syspy.v3.protobuf.message import CanFrame_pb2
except ImportError:
    Trace.log("CanFrame_pb2 not found, falling back to bytes comparison", name="syspy.passThrough.err")



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
            Trace.log("Use Can Pass", name="syspy.passThrough")
        elif pass_type == "serial":
            self.__pass_type = False
            Trace.log("Use Serial Pass", name="syspy.passThrough")
        else:
            Trace.log("passThrough type error.It should be 'can' or 'serial'",
                      name="syspy.passThrough.err")
        Trace.log("passThrough start with real-time message settings (HWM=1)",
                  name="syspy.passThrough")

    def close(self):
        Trace.log("close the socket", name="syspy.passThrough")
        self.__should_close = True
        if self.__msg_thread and self.__msg_thread.is_alive():
            self.__msg_thread.join(timeout=1.0)
        try:
            self.__client_sock.close(0)
        except Exception as e:
            Trace.log(f"socket close error: {e}", name="syspy.passThrough.err")
        try:
            self.context.term()
        except Exception as e:
            Trace.log(f"context term error: {e}", name="syspy.passThrough.err")
        Trace.log("passThrough closed.", name="syspy.passThrough")


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
            Trace.log(f"passThrough exception: {e}", name="syspy.passThrough.err")

        finally:
            Trace.log("finished passThrough", name="syspy.passThrough")

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
