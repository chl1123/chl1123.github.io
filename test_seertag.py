import base64
import json

import cv2
import numpy as np
from APILib.rbklib import getIP, rbklib
import time

# 插件名称
PluginName = "IRCameraPose"


def send_req(rbk, req: dict) -> dict:
    """发送请求
    rbk: rbklib实例
    req: 待发送的请求

    return: 请求的应答
    """
    # 准备请求的数据
    seertag_req = {
        "call_pytest": [{
            PluginName: req
        }]
    }
    # 发送pytest请求
    _, data = rbk.request(1851, 1, seertag_req)
    # 获取返回值
    response = json.loads(data)['return_data']
    return json.loads(response)


def test_seertag():
    # 连接rbk
    rbk = rbklib(getIP())
    # 查询启用的设备个数
    # response = send_req(rbk, {'cmd': 0})
    # print(response)
    # # 确认应答正确
    # if response.get("seertag_family_id") == 1:
    #     print("SEERTAG家族设置正确")
    # else:
    #     print(" seertag_family_id ERROR")
    # if response.get("infrared"):
    #     print("打开红外相机成功")
    # else:
    #     print("开启红外相机失败")
    # if response.get("seertag_size") == 0.02:
    #     print("二维码大小设置成0.02")
    # else:
    #     print("二维码大小设置失败")
    #
    # # # 开启二维码检测
    # response = send_req(rbk, {'cmd': 1})
    # # # 确认应答正确
    # print(response)
    # if response.get("detector_status"):
    #     print("检测二维码检测器成功")
    # else:
    #     print("打开二维码检测器失败")
    # time.sleep(2)
    #
    # # 关闭二维码检测
    # response = send_req(rbk, {'cmd': 2})
    # # 确认应答正确
    # if response.get("detector_status"):
    #     print("二维码检测器关闭成功")
    # else:
    #     print("二维码检测器关闭失败")
    # time.sleep(2)
    #
    # # 开启二维码建图
    # response = send_req(rbk, {'cmd': 3})
    # # 确认应答正确
    #
    # if response.get("slam_status"):
    #     print("二维码建图打开成功")
    # else:
    #     print("二维码建图打开失败")
    # time.sleep(2)
    # # 关闭二维码建图
    # response = send_req(rbk, {'cmd': 4})
    # if response.get("slam_status"):
    #     print("二维码建图关闭成功")
    # else:
    #     print("二维码建图关闭失败")
    #
    # # 检查图像传输是否正常
    # response = send_req(rbk, {'cmd': 5})
    # # 确认应答正确
    # if response.get("video_status"):
    #     print("图像传输正常")
    # else:
    #     print("图像传输出现问题")
    #
    # # 检查是否可以检测到二维码
    # response = send_req(rbk, {'cmd': 6})
    # # 确认应答正确
    # if response.get("find_tags"):
    #     print("找到二维码")
    # else:
    #     print("没有发现二维码")

    response = send_req(rbk, {'cmd': 7})
    print("res",response)
    # 确认应答正确
    print(response.get('img'))
    base64.decode(response.get('img'))
    nparr = np.fromstring(response.get('img'), np.uint8)
    # print("s1")
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    # print("2")
    # cv2.imshow('test',image)
    cv2.imwrite("q.jpg",image)
    cv2.waitKey(0)
    # print(img)
# def test_seertag():
#     rbk = rbklib(getIP())
#     response = send_req(rbk, {'cmd': 7})
#     print(response)
#     # 确认应答正确
#     img =response.get("img")
#     print(img)
