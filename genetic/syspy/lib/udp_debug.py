import time,socket,sys
class udpDebug:
    def __init__(self):
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    def write(self, str1):
        self.udp_socket.sendto(str1.encode("utf-8"), ('<broadcast>', 20000))
    
    def flush(self):
        pass

    def close(self):
        self.udp_socket.close()

if __name__ == "__main__":
    pass