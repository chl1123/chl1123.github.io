import sys,ctypes

def merge2bytesTo1(byte1, byte2):
    '''
    将两个字节数据组合成一个16位的数据
    '''
    temp1 = byte1 << 8 & 0xFF00
    temp2 = byte2 & 0x00FF
    return temp1 | temp2

def u16Toint16(u16t):
    '''
    将uint16_t的数据转换成int16_t,用途:负号转换
    '''
    return ctypes.c_int16(u16t).value

if __name__ == "__main__":
    print(hex(merge2bytesTo1(0x12,0x33)))