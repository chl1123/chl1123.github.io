import sys,ctypes

def merge2bytesTo1(byte1, byte2):
    '''
    将两个字节数据组合成一个16位的数据
    '''
    temp1 = byte1 << 8 & 0xFF00
    temp2 = byte2 & 0x00FF
    return temp1 | temp2

def merge4bytesTo1(byte1, byte2, byte3, byte4):
    temp1 = byte1 << 24 & 0xFF000000
    temp2 = byte2 << 16 & 0x00FF0000
    temp3 = byte3 << 8 &  0x0000FF00
    temp4 = byte4 & 0x000000FF
    return temp1 | temp2 | temp3 | temp4


def u16Toint16(u16t):
    '''
    将uint16_t的数据转换成int16_t,用途:负号转换
    '''
    return ctypes.c_int16(u16t).value

def u8Toint8(u8t):
    return ctypes.c_int8(u8t).value


if __name__ == "__main__":
    print(hex(merge2bytesTo1(0x12,0x33)))


