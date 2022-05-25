import time,socket,sys
class udpDebug:
    def __init__(self):
        try:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        except Exception as e:
            pass
        
    def write(self, str1):
        try:
            str1 = str1.strip("\n")
            self.udp_socket.sendto(str1.encode("utf-8"), ("192.168.192.255", 20000))
        except Exception as e:
            pass
    
    def flush(self):
        pass

    def close(self):
        self.udp_socket.close()

if __name__ == "__main__":
    pass