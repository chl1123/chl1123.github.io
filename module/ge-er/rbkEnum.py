"""
  该类主要是解决rbksim类中无法解决的问题通过使用Tcp/ip的方式来进行解决
"""

import json
import struct
from rbkSim import SimModule
from rbk import MoveStatus, BasicModule
from enum import Enum


class RbkNetProtocol(Enum):
    """
      机器人netprotocol的相关端口枚举常量
    """
    port_robod = 19200
    aport_state = 19204
    port_ctrl = 19205
    port_task = 19206
    port_config = 19207
    port_kernel = 19208
    port_other = 19210

    """
       机器人相关操作的编号，如果有未列出的可以添加枚举常量进行操作
    """
    robot_config_di = 3106 
    """
      协议头中的一些固定常量，例如协议头格式fmt(首先确定是大端通信方式)，以及保留数据区的枚举常量
      代表协议头的组合方式是同步头（1byte）+协议版本号(1byte)+客户端协议序号(2byte)+数据区长度(4byte)+报文类型(2byte)+保留数据区(6byte)
      客户端协议需要代表的含义是：客户端发送什么服务端跟着发送什么以代表的意思就请求回复响应一致，方便多指令发起的命令分类
    """
    # 协议格式约束
    netProtocol_fmt = '!cbhIh6s'
    # 协议头
    netProtocol_head = 'Z'.encode('ascii')
    # 协议版本
    netProtocol_version = 1
    # 协议保留数据区
    netPortocol_reserved = b'\x00\x00\x00\x00\x00\x00'

    """
      方法作用：将客户端请求体进行满足SEER的netProtocol格式进行打包
      clientSeqNum(str):客户端序号，响应和请求保持一致
      requestMsg(dist):请求体封装的json格式可以在module类进行约束
      isExistBody(bool):是否存在请求体
      r:simModule实例化
      return 返回封装好的请求体
    """

    @staticmethod
    def pack_byte_array(client_seq_num: int, request_msg: dict or None, rbk_num_type, r: SimModule) -> bytes:
        request_body_json_str = json.dumps(request_msg, separators=(',', ':'))
        request_msg_bytes_len = len(request_body_json_str)
        if not request_msg:
            r.setInfo("request_msg is None,so request data area is null")
            request_head = struct.pack(RbkNetProtocol.netProtocol_fmt.value, RbkNetProtocol.netProtocol_head.value,
                                       RbkNetProtocol.netProtocol_version.value, client_seq_num, 0,
                                       rbk_num_type.value,
                                       RbkNetProtocol.netPortocol_reserved.value)
        else:
            r.setInfo("request_msg is not Nome area is {}".format(request_body_json_str))
            fmt = RbkNetProtocol.netProtocol_fmt.value + str(request_msg_bytes_len) + 's'
            request_head = struct.pack(fmt, RbkNetProtocol.netProtocol_head.value,
                                       RbkNetProtocol.netProtocol_version.value, client_seq_num, request_msg_bytes_len,
                                       rbk_num_type.value,
                                       RbkNetProtocol.netPortocol_reserved.value,
                                       bytearray(request_body_json_str, 'ascii'))
            print(request_head)
        return request_head

    """
     该方法用于对Seer的netProtocol协议的响应进行解析
     res_msg(bytes):响应体的bytes
     success_info:请求成功的标志数据
     r:simModule实例化
    """
    @staticmethod
    def unpack_byte_array(res_msg, success_info: str, r: SimModule):
        fmt = RbkNetProtocol.netProtocol_fmt.value + str(len(res_msg) - 16) + 's'
        result = struct.unpack(fmt, res_msg)
        r.setInfo("result response is{}".format(str(result[6])))
        return str(result[6]).find(success_info)
