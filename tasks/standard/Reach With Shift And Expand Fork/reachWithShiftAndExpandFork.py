# -*- coding: utf-8 -*-
# @Time : 2025/07/08
# @Author : xu
# @File : reachWithShiftAndExpandFork.py
# @Request : 可调间距横移前移叉车机器人脚本
# @Version: 1.0.0
# @Description: 新建

import os
import json
import time
import sys
from enum import IntEnum
import math
from collections import defaultdict
from datetime import datetime
from syspy import (Module, ParamServer, Logger, battery, Di, Motor, Do,
                   Navigation, Abnormal, ScriptStatus, Odometer, controller)

log = Logger("reachFork_robot")

"""
####BEGIN DEFAULT ARGS####
{
    "operation":{
        "value": "zero",
        "default_value":[
            "zero", 
            "unload", 
            "simple_unload",
            "load", 
            "goStationWithFork", 
            "lift", 
            "lift_load",
            "lift_unload",
            "pitch",
            "stretch",
            "lateral",
            "expand", 
            "goStationList", 
            "rec",
            "getMassage",
            "weightGood",
            "stepLift",
            "stepStretch",
            "unloadHeightDetect",
            "test",
            "locDetectMid",
            "locDetectBackLaser",
            "goodsCheck",
            "update_data"
            ],
        "tips": "动作类型",
        "type": "complex"        
    },
    "stationList" :{
        "value": ["LM1", "LM2", "LM3"],
        "type": "json",
        "tips": "站点列表"
    },
    "checkDi":{
        "value": false,
        "tips": "是否检测到位DI",
        "type": "bool"
    },
    "useLoadRecHeight":{
        "value": false,
        "tips": "是否使用取货时的识别结果高度",
        "type": "bool"
    },
    "stretchLength": {
        "value": 0.42,
        "tips": "货叉伸出长度",
        "type": "float",
        "unit": "m"
    },
    "startHeight": {
        "value": 0.8,
        "tips": "开始时货叉高度，如需识别，则在识别前前调整货叉高度，会在此高度进行识别",
        "type": "float",
        "unit": "m"
    },
    "endHeight": {
        "value": 0.8,
        "tips": "结束时货叉高度",
        "type": "float",
        "unit": "m"
    },
    "expand_position1": {
        "value": 0.3,
        "tips": "开合电机1目标位置",
        "type": "float",
        "unit": "m"
    },
    "expand_position2": {
        "value": 0.3,
        "tips": "开合电机2目标位置",
        "type": "float",
        "unit": "m"
    },
    "endLateralPos": {
        "value": 0.0,
        "tips": "结束时货叉横移目标位置",
        "type": "float",
        "unit": "m"
    },
    "stepHeight": {
        "value": 0.02,
        "tips": "货叉步进升降调整高度值，正值为上升，负值为下降",
        "type": "float",
        "unit": "m"
    },
    "stepLength": {
        "value": 0.02,
        "tips": "货叉步进伸缩调整高度值，正值为伸出，负值为收回",
        "type": "float",
        "unit": "m"
    },
    "forkMidHeight": {
        "value": 0.8,
        "tips": "行走过程中的货叉高度",
        "type": "float",
        "unit": "m"
    },
    "liftUpHeight":{
        "value": 0.0,
        "tips": "取货类操作会在startHeight基础上再上升此距离",
        "type": "double",
        "unit": "m"
    },
    "loadMoveHeight":{
        "value": 0.0,
        "tips": "完成取货后行走前调整到的高度，即叉车行走高度",
        "type": "double",
        "unit": "m"
    },
    "loadMoveHeightOn":{
        "value": false,
        "tips": "取货流程完成后是否调整货叉高度至安全高度",
        "type": "bool"
    },
    "liftDownHeight":{
        "value": 0.0,
        "tips": "放货时 在liftHeight基础上，再下降此距离",
        "type": "double",
        "unit": "m"
    },
    "stretchMode":{
        "value": "zero",
        "default_value":[
            "max", 
            "zero"
            ],
        "tips": "货叉前移或收回",
        "type": "complex"        
    },
    "pitchMode":{
        "value": "forward",
        "default_value":[
            "forward", 
            "backward"
            ],
        "tips": "货叉俯仰类型：forward前倾、backwards后仰",
        "type": "complex"        
    },
    "loadPitch":{
        "value": false,
        "tips": "取放货过程中是否调整货叉俯仰",
        "type": "bool"
    },
    "loadAll":{
        "value": true,
        "tips": "取货过程中是否取所有货物，false为取解垛时使用",
        "type": "bool"
    },
    "readjust": {
        "value": true,
        "tips": "是否开启二次识别调整取货，以提高取货精度",
        "type": "bool"
    },
    "forwardDist":{
        "value": 0.0,
        "tips": "机器人整体前进距离，沿X正方向",
        "type": "double",
        "unit": "m"
    },
    "leaveLoc": {
        "value": true,
        "tips": "取放货完成后是否前进脱离库位",
        "type": "bool"
    },
    "forkMoveMode":{
        "value": 6,
        "tips": "边走边升降货叉任务结束模式",
        "type": "int"        
    },
    "adjustDirFirst": {
        "value": false,
        "tips": "识别前是否调整方向",
        "type": "bool"
    },
    "recFile": {
        "value": "plt/p4.plt",
        "tips": "识别文件",
        "type": "string"
    },
    "locName": {
        "value": "loc-1",
        "tips": "库位货物有无检测的库位名称",
        "type": "string"
    },
    "stationId": {
        "value": 0,
        "tips": "目标站点ID",
        "type": "int"
    },
    "recFileId": {
        "value": 0,
        "tips": "识别文件ID",
        "type": "int"
    },
    "massageName": {
        "value": "",
        "tips": "消息名称",
        "type": "string"
    },
    "adjustHeight": {
        "value": false,
        "tips": "是否根据识别结果调整高度",
        "type": "bool"
    },
    "doubleLift": {
        "value": false,
        "tips": "取货时是否两次调整高度",
        "type": "bool"
    },
    "loadLiftUpHeight1":{
        "value": 0.0,
        "tips": "取货时两次调整高度，第1次高度",
        "type": "double",
        "unit": "m"
    },
    "loadLiftUpHeight2":{
        "value": 0.0,
        "tips": "取货时两次调整高度，第2次高度",
        "type": "double",
        "unit": "m"
    },
    "goodsCheckOn": {
        "value": false,
        "tips": "是否启用货物有无及超限检测",
        "type": "bool"
    },
    "unStackNum" :{
        "value": 1,
        "tips": "每次解垛叉取的空栈板数量",
        "type": "int"
    }
}
####END DEFAULT ARGS####
"""


class ConfigParams:
    """生成和定义脚本全局配置参数"""
    param_server = ParamServer(__file__)
    # 底盘类型，是否为全向
    omni_model = param_server.loadParam("omniModel", type="bool", default=False, group="basic",
                                             comment="底盘类型是否为全向omni")
    camera_on_fork = param_server.loadParam("camera_on_fork", type="bool", default=False, group="basic",
                                                 comment="相机是否标定在叉尖")
    fork_width = param_server.loadParam("fork_width", type="float", default=0.08, minValue=0.05, maxValue=0.5,
                                             unit="m",
                                             group="basic", comment="单个货叉宽度，识别取货时用于确认是否可以插进栈板")
    fork_offset_x = param_server.loadParam("forkOffsetX", type="float", default=0, minValue=-2, maxValue=2,
                                                unit="m",
                                                group="basic", comment="货叉在X方向偏置距离")
    fork_offset_y = param_server.loadParam("forkOffsetY", type="float", default=0, minValue=-3, maxValue=3,
                                                unit="m",
                                                group="basic", comment="货叉叉尖在Y方向偏置距离")
    fork_offset_theta = param_server.loadParam("forkOffsetTheta", type="float", default=0, minValue=-180,
                                                    maxValue=180,
                                                    unit="°", group="basic", comment="货叉相对里程中心旋转角度")
    pallet2odo = param_server.loadParam("pallet2odo", type="float", default=0.6, minValue=0, maxValue=2, unit="m",
                                             group="basic",
                                             comment="取货后栈板前表面与里程的距离，有货物到位di则是到位DI与里程中心距离")
    if camera_on_fork:
        fork2robot = [fork_offset_x, fork_offset_y,
                           math.radians(fork_offset_theta)]  # 叉尖相对里程中心的位置
    else:
        fork2robot = [0.0, 0.0, 0.0]
    # 货叉升降机构参数
    lift_motor = param_server.loadParam("liftMotor", type="str", default="None",
                                             group="module-lift", comment="升降电机")
    lift_zero = param_server.loadParam("liftZero", type="float", default=0.075, minValue=0, maxValue=10, unit="m",
                                            group="module-lift", comment="货叉升降机构的零位")
    lift_vel = param_server.loadParam("liftVel", type="float", default=0.4, minValue=0, maxValue=10, unit="m/s",
                                           group="module-lift", comment="lift电机的规划最大速度")
    lift_max_height = param_server.loadParam("liftMaxHeight", type="float", default=0.4, minValue=0, maxValue=10,
                                                  unit="m",
                                                  group="module-lift", comment="lift电机的最大高度")
    lift_up_reach_di = param_server.loadParam("liftUpReachDI", type="int", default=-1, minValue=-1, maxValue=100,
                                                   group="module-lift", comment="货叉升降到位DI的ID")
    lift_precision = param_server.loadParam("lift_precision", type="float", default=0.001, minValue=0.0,
                                                 maxValue=0.01, unit="m", group="module-lift",
                                                 comment="货叉升降电机位置控制精度")

    # 货叉开合机构参数
    expand_motor1 = param_server.loadParam("expand_motor1", type="str", default="None",
                                                group="module-expand", comment="开合电机1")
    expand_motor2 = param_server.loadParam("expand_motor2", type="str", default="None",
                                                group="module-expand", comment="开合电机1")

    expand_vel = param_server.loadParam("expand_vel", type="float", default=0.4, minValue=0, maxValue=10,
                                             unit="m/s",
                                             group="module-expand", comment="开合电机的规划最大速度")
    expand_motor1_zero_position = param_server.loadParam("expand_motor1_zero_position", type="float",
                                                              default=0.1375,
                                                              minValue=0, maxValue=10, unit="m",
                                                              group="module-expand", comment="货叉开合电机1的零位")
    expand_motor1_max_position = param_server.loadParam("expand_motor1_max_position", type="float", default=0.3125,
                                                             minValue=0, maxValue=10, unit="m",
                                                             group="module-expand", comment="货叉开合电机1的最大位置")
    expand_motor2_zero_position = param_server.loadParam("expand_motor2_zero_position", type="float",
                                                              default=0.1375,
                                                              minValue=0, maxValue=10, unit="m",
                                                              group="module-expand",
                                                              comment="货叉开合电机2的零位，相对机器人中心的横向距离")
    expand_motor2_max_position = param_server.loadParam("expand_motor2_max_position", type="float", default=0.3125,
                                                             minValue=0, maxValue=10, unit="m",
                                                             group="module-expand",
                                                             comment="货叉开合电机2的最大位置，相对机器人中心的横向距离")
    expand_motor1_max_limit_di = param_server.loadParam("expand_motor1_max_limit_di", type="int", default=-1,
                                                             minValue=-1,
                                                             maxValue=100,
                                                             group="module-expand",
                                                             comment="货叉开合电机1最大位置限位DI的ID")
    expand_motor2_max_limit_di = param_server.loadParam("expand_motor2_max_limit_di", type="int", default=-1,
                                                             minValue=-1,
                                                             maxValue=100,
                                                             group="module-expand",
                                                             comment="货叉开合电机2最大位置限位DI的ID")
    expand_motor1_zero_limit_di = param_server.loadParam("expand_motor1_zero_limit_di", type="int", default=-1,
                                                              minValue=-1, maxValue=100,
                                                              group="module-expand",
                                                              comment="货叉开合电机1最小位置限位DI的ID")
    expand_motor2_zero_limit_di = param_server.loadParam("expand_motor2_zero_limit_di", type="int", default=-1,
                                                              minValue=-1, maxValue=100,
                                                              group="module-expand",
                                                              comment="货叉开合电机2最小位置限位DI的ID")

    # 货叉横移机构参数
    lateral_motor = param_server.loadParam("lateral_motor", type="str", default="None",
                                                group="module-lateral", comment="横移电机")
    lateral_zero = param_server.loadParam("lateral_zero", type="float", default=0.0, minValue=-10, maxValue=10,
                                               unit="m",
                                               group="module-lateral", comment="货叉横移机构的零位")
    lateral_min_pos = param_server.loadParam("lateral_min_pos", type="float", default=0.0, minValue=-10,
                                                  maxValue=10,
                                                  unit="m",
                                                  group="module-lateral", comment="货叉横移机构的最小位置")
    lateral_vel = param_server.loadParam("lateral_vel", type="float", default=0.0, minValue=0, maxValue=10,
                                              unit="m/s",
                                              group="module-lateral", comment="横移电机的规划最大速度")
    lateral_max_pos = param_server.loadParam("lateral_max_pos", type="float", default=0.0, minValue=0, maxValue=10,
                                                  unit="m",
                                                  group="module-lateral", comment="横移电机的最大位置")
    lateral_left_reachDI = param_server.loadParam("lateral_left_reachDI", type="int", default=-1, minValue=-1,
                                                       maxValue=100,
                                                       group="module-lateral", comment="货叉横移左限位到位DI的ID")
    lateral_right_reachDI = param_server.loadParam("lateral_right_reachDI", type="int", default=-1, minValue=-1,
                                                        maxValue=100,
                                                        group="module-lateral", comment="货叉横移右限位到位DI的ID")
    lateral_precision = param_server.loadParam("lateral_precision", type="float", default=0.001, minValue=0.0,
                                                    maxValue=0.01, unit="m", group="module-lateral",
                                                    comment="货叉横移电机位置控制精度")
    # 货叉伸缩机构参数
    stretch_motor = param_server.loadParam("stretchMotor", type="str", default="None",
                                                group="module-stretch", comment="前后电机")
    stretch_zero = param_server.loadParam("stretchZero", type="float", default=0.02, minValue=0.0, maxValue=10,
                                               unit="m",
                                               group="module-stretch", comment="伸出机构的零位")
    stretchZeroDi = param_server.loadParam("stretchZeroDi", type="int", default=-1, minValue=-1, maxValue=100,
                                                group="module-stretch", comment="货叉前移零位DI")
    stretchMaxDi = param_server.loadParam("stretchMaxDi", type="int", default=-1, minValue=-1, maxValue=100,
                                               group="module-stretch", comment="货叉前移极限DI")
    stretchVel = param_server.loadParam("stretchVel", type="float", default=0.02, minValue=0.0, maxValue=1.5,
                                             unit="m/s",
                                             group="module-stretch", comment="stretch电机的规划最大速度")
    stretchMaxLength = param_server.loadParam("stretchMaxLength", type="float", default=0.41, minValue=0.0,
                                                   maxValue=3,
                                                   unit="m",
                                                   group="module-stretch", comment="货叉伸出最大距离")
    stretchType = param_server.loadParam("stretchType", type="str", default="position",
                                              group="module-stretch",
                                              comment="叉尺前后伸展电机控制类型，速度控制[speed]、位置控制[position]、DO控制[DO]")
    stretch_out_do = param_server.loadParam("stretchOutDo", type="int", default=-1, minValue=-1, maxValue=100,
                                                 group="module-stretch", comment="货叉前移伸出控制DO")
    stretch_in_do = param_server.loadParam("stretchInDo", type="int", default=-1, minValue=-1, maxValue=100,
                                                group="module-stretch", comment="货叉前移收回控制DO")
    stretch_slow_down_dist = param_server.loadParam("stretch_slow_down_dist", type="float", default=0.1,
                                                         minValue=0.0,
                                                         maxValue=0.3,
                                                         unit="m", group="module-stretch",
                                                         comment="货叉运动时减速距离（距离目标位置）")
    stretch_slow_down_vel = param_server.loadParam("stretch_slow_down_vel", type="float", default=0.05,
                                                        minValue=0.0,
                                                        maxValue=0.3, unit="m/s", group="module-stretch",
                                                        comment="货叉运动时末端速度")
    stretch_precision = param_server.loadParam("stretch_precision", type="float", default=0.001, minValue=0.0,
                                                    maxValue=0.01, unit="m", group="module-stretch",
                                                    comment="货叉前后伸展电机位置控制精度")

    # 俯仰机构参数
    pitchMotor = param_server.loadParam("pitchMotor", type="str", default="None",
                                             group="module-pitch", comment="俯仰电机")
    pitchVel = param_server.loadParam("pitchVel", type="float", default=0.4, minValue=0.0, maxValue=1.5,
                                           unit="m/s",
                                           group="module-pitch", comment="pitch电机的规划最大速度")
    pitchZeroDi = param_server.loadParam("pitchZeroDi", type="int", default=-1, minValue=-1, maxValue=100,
                                              group="module-pitch", comment="货叉俯仰零位DI")
    pitchMaxDi = param_server.loadParam("pitchMaxDi", type="int", default=-1, minValue=-1, maxValue=100,
                                             group="module-pitch", comment="货叉俯仰极限DI")

    # 到位DI
    # reachDi = param_server.loadParam("reachDi", type="int", default=8, comment="货物到位DI的ID")
    reachDI1 = param_server.loadParam("reachDI1", type="int", default=-1, minValue=-1, maxValue=100,
                                           group="basic", comment="货物到位DI1的ID")
    reachDI2 = param_server.loadParam("reachDI2", type="int", default=-1, minValue=-1, maxValue=100,
                                           group="basic", comment="货物到位DI2的ID")
    multiReachDI = [reachDI1, reachDI2]
    checkAllDi = param_server.loadParam("checkAllDi", type="bool", default=False,
                                             group="basic", comment="是否检测全部货物到位DI")
    # back_slow_down_dist = param_server.loadParam("back_slow_down_dist", type="float", default=0.1, minValue=0.0,
    #                                        maxValue=0.3,
    #                                        unit="m", group="basic", comment="倒车取货运动时减速距离（距离目标位置）")
    back_slow_down_vel = param_server.loadParam("back_slow_down_vel", type="float", default=0.05, minValue=0.0,
                                                     maxValue=0.3, unit="m/s", group="basic",
                                                     comment="倒车取货运动时末端速度")

    # 距离传感器
    distanceNodeId1 = param_server.loadParam("distanceNodeId1", type="int", default=-1, minValue=-1, maxValue=100,
                                                  group="basic", comment="distanceNode1的ID号")
    distanceNodeId2 = param_server.loadParam("distanceNodeId2", type="int", default=-1, minValue=-1, maxValue=100,
                                                  group="basic", comment="distanceNode1的ID号")
    obsStopDist = param_server.loadParam("ObsStopDist", type="float", default=0.25, minValue=0.0, maxValue=2,
                                              unit="m",
                                              group="basic",
                                              comment="# 报警距离， 这个距离传感器的死区为0.2m，因此不能配置成小于0.2m")
    distanceNodeId = (distanceNodeId1, distanceNodeId2)  # distanceNode的ID号

    # 尾部激光
    backLaserId1 = param_server.loadParam("backLaserId1", type="int", default=-1, minValue=-1, maxValue=100,
                                               group="basic", comment="后置激光1id")
    backLaserId2 = param_server.loadParam("backLaserId2", type="int", default=-1, minValue=-1, maxValue=100,
                                               group="basic", comment="后置激光2id")
    backLaser = [backLaserId1, backLaserId2]

    # 叉尖碰撞DI
    fork_tail_di1 = param_server.loadParam("fork_tail_di1", type="int", default=-1, minValue=-1, maxValue=100,
                                                group="basic", comment="叉尖碰撞DI1的id")
    fork_tail_di2 = param_server.loadParam("fork_tail_di2", type="int", default=-1, minValue=-1, maxValue=100,
                                                group="basic", comment="叉尖碰撞DI2的id")

    # 识别调整参数
    recFile1 = param_server.loadParam("recFile1", type="str", default="plt/p0001.plt",
                                           group="recognization", comment="modbus脚本识别文件1")
    recFile2 = param_server.loadParam("recFile2", type="str", default="plt/p0002.plt",
                                           group="recognization", comment="modbus脚本识别文件2")
    recFile3 = param_server.loadParam("recFile3", type="str", default="plt/p0003.plt",
                                           group="recognization", comment="modbus脚本识别文件3")
    aheadDist = param_server.loadParam("AheadDist", type="float", default=0.6, minValue=0.0, maxValue=2, unit="m",
                                            group="recognization",
                                            comment="双折线识别调整时，调整距离不够时，第二段折线长度")
    minAheadDist = param_server.loadParam("minAheadDist", type="float", default=0.6, minValue=-3.0, maxValue=3.0,
                                               unit="m",
                                               group="recognization",
                                               comment="识别调整偏差后进栈板前，里程中心在栈板前的直线距离")
    backDist = param_server.loadParam("backDist", type="float", default=0.6, minValue=-3.0, maxValue=3.0, unit="m",
                                           group="recognization",
                                           comment="识别调整结束时，里程中心在栈板后的直线距离，不进入栈板为负")
    adjustForStr = param_server.loadParam("adjustForStr", type="float", default=0.3, minValue=0, maxValue=3.0,
                                               unit="m",
                                               group="recognization", comment="识别调整不足时，前进距离")
    recBeizer = param_server.loadParam("recBeizer", type="bool", default=True,
                                            group="recognization",
                                            comment="识别调整时是否使用贝塞尔曲线行驶，beizer、straight")
    beizerDist = param_server.loadParam("beizerDist", type="float", default=1, minValue=0, maxValue=3.0, unit="m",
                                             group="recognization",
                                             comment="识别后贝塞尔曲线调整时是否需要先向前行驶的最小调整距离，机器人当前位置与栈板前置点（minAheadDist）之间的距离")
    reachDist = param_server.loadParam("reachDist", type="float", default=0.1,
                                            group="recognization", comment="检测货物到位DI时的位置范围")
    reachAngle = param_server.loadParam("reachAngle", type="float", default=1, minValue=0, maxValue=10, unit="°",
                                             group="recognization", comment="检测货物到位DI时的角度范围")
    liftUpHeight = param_server.loadParam("liftUpHeight", type="float", default=0.3, minValue=0, maxValue=1.0,
                                               unit="m",
                                               group="recognization", comment="取货时取到货后抬升高度")
    liftDownHeight = param_server.loadParam("liftDownHeight", type="float", default=0.3, minValue=0, maxValue=3.0,
                                                 unit="m",
                                                 group="recognization", comment="放货时到点后下降高度")
    readjust = param_server.loadParam("readjust", type="bool", default=False,
                                           group="recognization", comment="是否开启二次识别调整取货，以提高取货精度 ")
    adjustMaxTimes = param_server.loadParam("adjustMaxTimes", type="int", default=3, minValue=0, maxValue=5,
                                                 group="recognization", comment="二次识别调整次数 ")
    distPrecision = param_server.loadParam("distPrecision", type="float", default=0.02, minValue=0, maxValue=0.05,
                                                unit="m",
                                                group="recognization", comment="识别调整位置精度")
    anglePrecision = param_server.loadParam("anglePrecision", type="float", default=0.5, minValue=0, maxValue=5,
                                                 unit="°",
                                                 group="recognization", comment="识别调整角度精度")
    readjustForwardDist = param_server.loadParam("readjustForwardDist", type="float", default=1,
                                                      minValue=0, maxValue=2, unit="m",
                                                      group="recognization", comment="二次识别调整前进距离")
    adjustDirFirst = param_server.loadParam("adjustDirFirst", type="bool", default=True,
                                                 group="recognization", comment="是否开启识别前角度调整")
    leaveLoc = param_server.loadParam("leaveLoc", type="bool", default=True,
                                           group="recognization", comment="取货完成后是否先脱离库位后再调整货叉")
    load_stretch_first = param_server.loadParam("loadStretchFirst", type="bool", default=True,
                                                     group="recognization", comment="取货调整完成后，先伸货叉再倒车")
    adjust_speed = param_server.loadParam("adjustSpeed", type="float", default=0.2,
                                               minValue=0, maxValue=0.5, unit="m/s",
                                               group="recognization", comment="识别后调整的最大速度")
    minus_result_filter = param_server.loadParam("minus_result_filter", type="bool", default=False,
                                                      group="recognization",
                                                      comment="识别时过滤掉高度结果为的负值或者0的数据")

    # 解垛参数
    classifyRang = param_server.loadParam("classifyRang", type="float", default=0.03, minValue=0, maxValue=1,
                                               unit="m",
                                               group="unstack", comment="解垛分类宽度差范围")
    errorRang = param_server.loadParam("errorRang", type="float", default=0.03, minValue=0, maxValue=1, unit="m",
                                            group="unstack", comment="解垛类别判断宽度差范围")
    palletNormalCount = param_server.loadParam("palletNormalCount", type="int", default=8, minValue=0, maxValue=50,
                                                    group="unstack", comment="解垛最大栈板层数")
    palletCheck = param_server.loadParam("palletCheck", type="bool", default=False,
                                              group="unstack", comment="解垛过程是否检查栈板类型及数量")

    # 称重参数
    weightGoodOn = param_server.loadParam("weightGoodOn", type="bool", default=False,
                                               group="weight", comment="是否启用称重检测")
    maxWeightDetectTimes = param_server.loadParam("maxWeightDetectTimes", type="int", default=3, minValue=0,
                                                       maxValue=10,
                                                       group="weight", comment="重量检测最大次数")
    detectPeriodTime = param_server.loadParam("detectPeriodTime", type="float", default=0.1, minValue=0,
                                                   maxValue=1,
                                                   unit="s",
                                                   group="weight", comment="重量检测时间间隔")
    maxWeight = param_server.loadParam("maxWeight", type="float", default=1000, minValue=0, maxValue=9999,
                                            unit="kg",
                                            group="weight", comment="重量上限")


class Robot:
    def __init__(self):
        super(self).__init__()
        # 脚本运行module类全局参数
        self._init_globalParams()

    def _init_globalParams(self):
        self.init = True
        # 任务参数 打印数据
        self.task = Module.get_task_args
        self.startConnectTime = None
        self.startTime = None
        self.state = dict()
        self.pyName = os.path.basename(__file__).split(".")[0]

        # 是否配置了电机
        self.isLiftMotor = False
        self.isStretchMotor = False
        self.isPitchMotor = False
        self.is_lateral_motor = False
        self.is_expand_motor1 = False
        self.is_expand_motor2 = False

        # 电机的实时位置
        self.stretchPos = 0.0
        self.liftPos = 0.0
        self.pitchPos = 0.0
        self.lateral_pos = 0.0
        self.expand_pos1 = 0.0
        self.expand_pos2 = 0.0

        # 电机的实时速度
        self.stretchSpeed = 0.0
        self.liftSpeed = 0.0
        self.pitchSpeed = 0.0
        self.lateral_speed = 0.0
        self.expand1_speed = 0.0
        self.expand2_speed = 0.0

        # 电机初始位置
        self.initStretchPos = 0.0
        self.initLiftPos = 0.0
        self.initPitchPos = 0.0
        self.init_lateral_pos = 0.0
        self.init_expand_pos1 = 0.0
        self.init_expand_pos2 = 0.0

        # 识别&运动
        self.recognize = False
        self.recTaskInit = True
        self.adjustTask1Init = True
        self.adjustTask2Init = True
        self.evaluateTaskInit = True
        self.goods_opt_task_init = True
        self.recTaskStatus = False
        self.adjustTask1Status = False
        self.adjustTask2Status = False
        self.evaluateTaskStatus = False
        self.goods_opt_task_status = False
        self.adjustTimes = 0
        self.pallet_pocket_width = 0.0

        self.recFailedTime = 0
        self.maxRecTime = 20
        self.recResult = None
        self.recResultToRobot = {}
        self.recParams = {}
        self.palletParams = {}
        self.recPos = [0, 0, 0]

        self.loadLiftHeight = 0.0
        self.unloadLiftHeight = 0.0
        self.loadLiftUpHeight = 0.0
        self.firstAdjust = True

        # 路径导航
        self.goPath = goPath.Module(r, dict())

        # operation
        self.taskList = []
        self.taskId = 0
        self.action_status = ActionStatus.NONE
        self.cur_task_list = []
        self.adjust_angle = 0.0
        self.target = [0, 0, 0, -1]

        # 解垛
        self.width_data = []
        self.height_data = []
        self.get_rec_result_id = 1
        self.unstack_error_type = None
        self.errors_pallet = None
        self.rec_result_pallet_num = 0

        self.testRecFile = None

        # 获取任务参数
        self.operation = self.task("operation", None)
        self.startHeight = self.task("startHeight", None)
        self.endHeight = self.task("endHeight", None)
        self.end_lateral_pos = self.task("endLateralPos", None)
        self.forkMidHeight = self.task("forkMidHeight", None)
        self.liftUpHeight = self.task("liftUpHeight", ConfigParams.liftUpHeight)
        self.liftDownHeight = self.task("liftDownHeight", ConfigParams.liftDownHeight)
        self.stretchLength = self.task("stretchLength", 0.0)
        self.useLoadRecHeight = self.task("useLoadRecHeight", False)
        self.stretchMode = self.task("stretchMode", None)
        self.pitchMode = self.task("pitchMode", None)
        self.loadPitch = self.task("loadPitch", False)
        self.forwardDist = self.task("forwardDist", 0.0)
        self.checkDi = self.task("checkDi", False)
        self.loadAll = self.task("loadAll", True)
        self.readjust = self.task("readjust", ConfigParams.readjust)
        self.loadMoveHeightOn = self.task("loadMoveHeightOn", False)
        self.loadMoveHeight = self.task("loadMoveHeight", False)
        self.adjustHeight = self.task("adjustHeight", False)
        self.forkMoveMode = self.task("forkMoveMode", 6)
        self.unStackNum = self.task("unStackNum", None)
        self.recFile = self.task("recFile", None)
        self.stationList = self.task("stationList", None)
        self.massageName = self.task("massageName", None)
        self.goodsCheckOn = self.task("goodsCheckOn", False)
        self.stepHeight = self.task("stepHeight", None)
        self.stepLength = self.task("stepLength", None)
        self.locName = self.task("locName", None)
        self.leaveLoc = self.task("leaveLoc", ConfigParams.leaveLoc)
        self.adjustDirFirst = self.task("adjustDirFirst", ConfigParams.adjustDirFirst)
        self.stationId = self.task("stationId", True)
        self.recFileId = self.task("recFileId", None)
        self.double_lift = self.task("doubleLift", False)
        self.load_lift_up_height1 = self.task("loadLiftUpHeight1", None)
        self.load_lift_up_height2 = self.task("loadLiftUpHeight2", None)
        self.expand_position1 = self.task("expand_position1", None)
        self.expand_position2 = self.task("expand_position2", None)

        if self.double_lift and (self.load_lift_up_height1 is None or self.load_lift_up_height2 is None):
            r.setError(f"load need to double_lift, but there is no loadLiftUpHeight1 or loadLiftUpHeight2")

        if self.recFileId == 1:
            self.recFile = self.recFile1
        elif self.recFileId == 2:
            self.recFile = self.recFile2
        elif self.recFileId == 3:
            self.recFile = self.recFile3

        for p in r.moveTask()["params"]:
            if p["key"] == "recognize":
                self.recognize = p["bool_value"]
            if p["key"] == "recFile":
                self.recFile = p["str_value"]

        # 更新车型参数
        if self.lift_motor != "None":
            self.isLiftMotor = True
        if self.stretch_motor != "None" or self.stretch_out_do != -1:
            self.isStretchMotor = True
            if self.stretchType == "speed" and (self.stretchZeroDi == -1 or self.stretchMaxDi == -1):
                r.setError(f"stretchType is speed-control, but not config the stretchZeroDi or the stretchMaxDi. "
                           f"please check the file of params/{self.pyName}.json !")
                self.status = MoveStatus.FAILED
                return self.status
        if self.pitchMotor != "None":
            self.isPitchMotor = True
            if self.pitchZeroDi == -1 or self.pitchMaxDi == -1:
                r.setError(f"Not config the pitchZeroDi or the pitchMaxDi. "
                           f"please check the file of params/{self.pyName}.json !")
                self.status = MoveStatus.FAILED
                return self.status
        if self.lateral_motor != "None":
            self.is_lateral_motor = True
        if self.expand_motor1 != "None":
            self.is_expand_motor1 = True
        if self.expand_motor2 != "None":
            self.is_expand_motor2 = True

        # 更新识别参数
        if self.recFile:
            # 获取识别文件信息
            recFile = r.getRecFile(self.recFile)
            self.testRecFile = r.getRecFile(self.recFile)
            # 遍历device_params下的array_param中的params
            for param in recFile.get("device_params", []):
                if "array_param" in param:
                    for item in param["array_param"].get("params", []):
                        key = item["key"]
                        if "double_value" in item:
                            value = item["double_value"]
                        elif "bool_value" in item:
                            value = item["bool_value"]
                        else:
                            continue
                        # 添加到recParams中
                        self.recParams[key] = value
                if param["key"] == "template_type":
                    childKey = param["combo_param"].get("child_key", "")
                    for item in param["combo_param"].get("child_params", []):
                        if item["key"] == childKey:
                            for autoParam in item.get("params", []):
                                key = autoParam["key"]
                                if "double_value" in autoParam:
                                    value = autoParam["double_value"]
                                elif "bool_value" in autoParam:
                                    value = autoParam["bool_value"]
                                else:
                                    continue
                                # 添加到recParams中
                                self.recParams[key] = value
            # 添加坐标系名称 recCoordinate
            if self.recParams.get('in_global_framework', None):
                self.recParams['recCoordinate'] = "world"
            elif not self.recParams.get('in_global_framework', None):
                self.recParams['recCoordinate'] = "robot"
            if self.recParams.get('enable_back_dist', None):
                self.backDist = self.recParams['back_dist']
            if not self.recParams.get('enable_cargoContactDI', None):
                self.reachDI1 = -1
                self.reachDI2 = -1
                self.multiReachDI = [self.reachDI1, self.reachDI2]
            if self.recParams.get('pallet_width', 0) == 0:
                self.status = MoveStatus.FAILED
                r.setError(f"识别文件 {self.recFile} 中pallet_width为 0")
                return self.status
        else:
            self.recognize = False

    # 任务参数检查
    def _init_checkArgs(self, r: SimModule, args):
        if self.operation == "":
            r.setError("operation is empty!!!")
            self.status = MoveStatus.FAILED
            return self.status
        if self.operation == "lift" and self.endHeight is None:
            r.setError("请输入endHeight")
            self.status = MoveStatus.FAILED
            return self.status
        r.logDebug("[SFL-scripts][{}]".format(self.task))

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        # 实时数据获取
        self.getMessage(r)
        # 运行前车体数据初始化
        self.initData(r, args)
        # 任务执行
        self.OPT(r)
        # 电机运动执行
        r.publishSpeed()
        # 数据上报
        self.logUpdate(r)
        return self.status

    def main(self):
        while True:
            # 脚本任务状态管理
            status = Module.get_status()
            if status is ScriptStatus.RUNNING:
                self.run()
            elif status in (ScriptStatus.FAILED, ScriptStatus.FINISHED, ScriptStatus.NONE):
                Module.set_status(ScriptStatus.NONE)
                return
            self.print_info()
            time.sleep(0.1)
    def getMessage(self, r: SimModule):
        odo = r.odo()
        # r.logDebug(str(odo))
        # 获取点击初始位置
        for motorInfo in odo.get('motor_info', []):
            motorName = motorInfo.get('motor_name', "")
            if self.lift_motor == motorName:
                self.liftPos = motorInfo.get('position', 0)
                self.liftSpeed = motorInfo.get('speed', 0)
            elif self.stretch_motor == motorName:
                self.stretchPos = motorInfo.get('position', 0)
                self.stretchSpeed = motorInfo.get('speed', 0)
            elif self.pitchMotor == motorName:
                self.pitchPos = motorInfo.get('position', 0)
                self.pitchSpeed = motorInfo.get('speed', 0)
            elif self.lateral_motor == motorName:
                self.lateral_pos = motorInfo.get('position', 0)
                self.lateral_speed = motorInfo.get('speed', 0)
            elif self.expand_motor1 == motorName:
                self.expand_pos1 = motorInfo.get('position', 0)
                self.expand1_speed = motorInfo.get('speed', 0)
            elif self.expand_motor2 == motorName:
                self.expand_pos2 = motorInfo.get('position', 0)
                self.expand2_speed = motorInfo.get('speed', 0)
        r.logDebug("[fork_data][{}|{}|{}|{}|{}|{}|{}|{}|{}|{}]".format(self.liftPos, self.liftSpeed,
                                                                       self.stretchPos, self.stretchSpeed,
                                                                       self.pitchPos, self.pitchSpeed,
                                                                       self.lateral_pos, self.lateral_speed,
                                                                       self.expand_pos1, self.expand1_speed,
                                                                       self.expand_pos2, self.expand2_speed))

    def print_info(self):
        # 打印当前任务队列、当前任务、当前任务id、当前任务状态
        log.info(f"{Module.get_task_args()=}")
        log.info(f"{Module.get_task_id()=}")
        log.info(f"{Module.get_status()=}")

    def initData(self, r: SimModule, args):
        if self.init:
            self.init = False
            self.task = args
            self.initLiftPos = self.liftPos
            self.initStretchPos = self.stretchPos
            self.initPitchPos = self.pitchPos
            self.init_expand_pos1 = self.expand_pos1
            self.init_expand_pos2 = self.expand_pos2

            moveTask = r.moveTask()
            dispatcherArgs = {}
            for p in moveTask["params"]:
                if p["key"] == "dispatcherArgs":
                    ss = p["string_value"]
                    dispatcherArgs = json.loads(ss)
            if "targetLoc" in dispatcherArgs:
                self.target = r.getLM(dispatcherArgs['targetLoc'], True)
            elif "targetLoc" not in dispatcherArgs and 'target_x' in moveTask:
                # self.state["moveTask"] = r.moveTask()
                # self.state["target"] = self.target
                strState = json.dumps(self.state)
                r.setInfo(strState)
                self.target = [
                    moveTask['target_x'], moveTask['target_y'], moveTask['target_angle'],
                    moveTask['target_name']
                ]
            else:
                self.target = [r.loc()["x"], r.loc()["y"], r.loc()["angle"], -1]

            if self.target[3] != -1:
                self.adjust_angle = self.target[2] - r.loc()['angle']

            r.resetRec()  # 重置识别模块
            r.clearNotice(57300)
            r.logDebug("[SFLInit][{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}]".format(
                self.operation, self.startHeight, self.endHeight, self.forkMidHeight, self.liftUpHeight,
                self.liftDownHeight, self.stretchLength, self.stretchMode, self.pitchMode, self.loadPitch,
                self.forwardDist, self.checkDi, self.loadAll, self.readjust, self.loadMoveHeightOn,
                self.loadMoveHeight, self.adjustHeight, self.forkMoveMode, self.unStackNum, self.recFile,
                self.recognize))

    def OPT(self, r: SimModule):
        speed_dict = {}
        if self.operation == "":
            self.status = MoveStatus.FINISHED
        elif self.operation == "load":
            self.load(r)
        elif self.operation == "unload":
            self.unload(r)
        elif self.operation == "simple_unload":
            self.simple_unload(r)
        elif self.operation == "lift":
            self.lift(r)
        elif self.operation == "lift_load":
            self.lift_load(r)
            if self.action_status == MoveStatus.FINISHED:
                r.forkGoods(True, "")
        elif self.operation == "lift_unload":
            self.lift_unload(r)
            if self.action_status == MoveStatus.FINISHED:
                r.forkGoods(False, "")
        elif self.operation == "stretch":
            self.stretch(r)
        elif self.operation == "pitch":
            self.pitch(r)
        elif self.operation == "lateral":
            self.lateral(r)
        elif self.operation == "expand":
            self.expand(r)
        elif self.operation == "stepLift":
            self.stepLift(r)
        elif self.operation == "stepStretch":
            self.stepStretch(r)
        elif self.operation == "zero":
            self.zero(r)
        elif self.operation == "rec":
            self.rec(r)
        elif self.operation == "goStationWithFork":
            self.goStationWithFork(r)
        elif self.operation == "goStationList":
            self.goStationList(r)
        elif self.operation == "weightGood":
            self.weightGood(r)
        elif self.operation == "unloadHeightDetect":
            self.unloadHeightDetect(r)
        elif self.operation == "getMassage":
            self.getMassage(r)
        elif self.operation == "locDetectMid":
            self.locDetectMid(r)
        elif self.operation == "locDetectBackLaser":
            self.locDetectBackLaser(r)
        elif self.operation == "goodsCheck":
            self.goodsCheck(r)
        elif self.operation == "test":
            self.test(r)
            # speed_dict = r.getNextSpeed()
        elif self.operation == "update_data":
            self.update_data(r)

        else:
            r.setError(f"operation 参数错误:{self.operation}")
            self.status = MoveStatus.FAILED
        if self.action_status == MoveStatus.FINISHED:
            # r.clearNotice(57300)
            self.status = MoveStatus.FINISHED
        elif self.action_status == MoveStatus.FAILED:
            self.status = MoveStatus.FAILED
        if self.status is MoveStatus.FAILED:
            r.stopRobot(True)
        self.cur_task_list = []
        for task in self.taskList:
            self.cur_task_list.append(task.opt_info)
        # controller = r.controller()
        # self.state["speed_dict"] = speed_dict
        # self.state["controller"] = controller
        self.state["cur_task_list"] = self.cur_task_list

    def logUpdate(self, r: SimModule):

        self.state["MoveStatus"] = self.status
        self.state["recParams"] = self.recParams
        if self.isLiftMotor and (self.operation == "lift" or self.operation == "load"
                                 or self.operation == "unload" or self.operation == "stepLift"
                                 or self.operation == "zero" or self.operation == "goStationWithFork"):
            lift_status = dict()
            lift_status["isLiftMotor"] = self.isLiftMotor
            lift_status["liftPos"] = self.liftPos
            lift_status["liftSpeed"] = self.liftSpeed
            lift_status["minPos"] = self.lift_zero
            lift_status["maxPos"] = self.lift_max_height
            self.state["lift_status"] = lift_status

        if self.isStretchMotor and (self.operation == "stretch" or self.operation == "load"
                                    or self.operation == "unload" or self.operation == "stepStretch"
                                    or self.operation == "zero" or self.operation == "goStationWithFork"):
            stretch_status = dict()
            stretch_status["method"] = self.stretchType
            stretch_status["isStretchMotor"] = self.isStretchMotor
            stretch_status["stretchPos"] = self.stretchPos
            stretch_status["stretchSpeed"] = self.stretchSpeed
            stretch_status["minPos"] = self.stretch_zero
            stretch_status["maxPos"] = self.stretchMaxLength
            zero_di = dict()
            zero_di["id"] = self.stretchZeroDi
            zero_di["status"] = ModuleTool.check_DI(r, self.stretchZeroDi)
            stretch_status["zeroDi"] = zero_di
            max_di = dict()
            max_di["id"] = self.stretchMaxDi
            max_di["status"] = ModuleTool.check_DI(r, self.stretchMaxDi)
            stretch_status["maxDi"] = max_di
            self.state["stretch_status"] = stretch_status

        if self.isPitchMotor and (self.operation == "pitch" or self.operation == "load"
                                  or self.operation == "unload" or self.operation == "zero"):
            pitch_status = dict()
            pitch_status["pitchPos"] = self.pitchPos
            pitch_status["pitchSpeed"] = self.pitchSpeed
            self.state["pitch_status"] = pitch_status

        if self.is_lateral_motor and (self.operation == "lateral" or self.operation == "load"
                                      or self.operation == "unload" or self.operation == "zero"):
            lateral_status = dict()
            lateral_status["lateral_pos"] = self.lateral_pos
            lateral_status["lateral_speed"] = self.lateral_speed
            self.state["lateral_status"] = lateral_status

        # self.state["lift_reach_state"] = r.isMotorReached(self.liftMotor)
        # self.state["testRecFile"] = self.testRecFile
        self.state["args"] = self.task
        # self.state["moveTask"] = r.moveTask()
        # self.state["recognize"] = self.recognize
        strState = json.dumps(self.state)
        r.setInfo(strState)
        r.logDebug("[SFLState][{}]".format(strState))
        r.logDebug("[SFLState][{}|{}|{}|{}|{}]".format(
            self.liftPos, self.stretchPos, self.status, self.taskId, self.action_status))

    def lift(self, r: SimModule):
        if self.endHeight is None:
            r.setError("endHeight is empty {}".format(json.dumps(self.task)))
            self.status = MoveStatus.FAILED
        else:
            if self.action_status == MoveStatus.NONE:
                self.action_status = MoveStatus.RUNNING
                if self.startHeight:
                    self.taskList = [
                        lift(self.lift_motor, self.startHeight),
                        lift(self.lift_motor, self.endHeight, self.lift_up_reach_di)
                    ]
                else:
                    self.taskList = [
                        lift(self.lift_motor, self.endHeight, self.lift_up_reach_di)
                    ]
                self.taskId = 0
            else:
                self.runTaskList(r)
            curState = dict()
            curState["state"] = self.action_status
            curState["liftPos"] = self.liftPos
            curState["liftSpeed"] = self.liftSpeed
            curState["taskId"] = self.taskId
            self.state["lift"] = curState

    def expand(self, r: SimModule):
        if self.expand_position1 is None and self.expand_position2 is None:
            r.setError("expand_position is empty {}".format(json.dumps(self.task)))
            self.status = MoveStatus.FAILED
        else:
            if self.action_status == MoveStatus.NONE:
                self.action_status = MoveStatus.RUNNING
                if (self.is_expand_motor1 and self.expand_position1
                        and self.is_expand_motor2 and self.expand_position2):
                    self.taskList = [
                        expand(self.expand_motor1, self.expand_position1, self.expand_motor2, self.expand_position2)
                    ]
                elif (self.is_expand_motor1 and self.expand_position1
                      and (not self.is_expand_motor2 or not self.expand_position2)):
                    self.taskList = [
                        expand(self.expand_motor1, self.expand_position1)
                    ]
                elif (self.is_expand_motor2 and self.expand_position2
                      and (not self.is_expand_motor1 or not self.expand_position1)):
                    self.taskList = [
                        expand(self.expand_motor2, self.expand_position2)
                    ]
                else:
                    r.setError("args error {}".format(json.dumps(self.task)))
                self.taskId = 0
            else:
                self.runTaskList(r)
            curState = dict()
            curState["state"] = self.action_status
            curState["taskId"] = self.taskId
            self.state["expand"] = curState

    def lift_load(self, r: SimModule):
        if self.action_status == MoveStatus.NONE:
            if r.hasGoods():
                self.state["load"] = "Fork has goods, cannot load"
                r.setError(f"Fork has goods, cannot load")
                self.status = MoveStatus.FAILED
                return self.status
            self.action_status = MoveStatus.RUNNING
            if self.endHeight is None:
                r.setNotice("endHeight is empty {}".format(json.dumps(self.task)))
                self.taskList = [
                ]
            else:
                self.taskList = [
                    lift(self.lift_motor, self.endHeight, self.lift_up_reach_di)
                ]
            self.taskId = 0
        else:
            self.runTaskList(r)
        curState = dict()
        curState["operationStatus"] = self.action_status
        curState["liftPos"] = self.liftPos
        curState["liftSpeed"] = self.liftSpeed
        curState["taskId"] = self.taskId
        self.state["lift_load"] = curState

    def lift_unload(self, r: SimModule):
        if self.action_status == MoveStatus.NONE:

            self.action_status = MoveStatus.RUNNING
            if self.endHeight is None:
                r.setNotice("endHeight is empty {}".format(json.dumps(self.task)))
                self.taskList = [
                ]
            else:
                self.taskList = [
                    lift(self.lift_motor, self.endHeight, self.lift_up_reach_di)
                ]
            self.taskId = 0
        else:
            self.runTaskList(r)
        curState = dict()
        curState["operationStatus"] = self.action_status
        curState["liftPos"] = self.liftPos
        curState["liftSpeed"] = self.liftSpeed
        curState["taskId"] = self.taskId
        self.state["lift_unload"] = curState

    def lateral(self, r: SimModule):
        if self.end_lateral_pos is None:
            r.setError("end_lateral_pos is empty {}".format(json.dumps(self.task)))
            self.status = MoveStatus.FAILED
        else:
            if self.action_status == MoveStatus.NONE:
                self.action_status = MoveStatus.RUNNING
                self.taskList = [
                    lateral(self.lateral_motor, self.end_lateral_pos)
                ]
                self.taskId = 0
            else:
                self.runTaskList(r)
            curState = dict()
            curState["state"] = self.action_status
            curState["lateral_pos"] = self.lateral_pos
            curState["lateral_speed"] = self.lateral_speed
            curState["taskId"] = self.taskId
            self.state["lateral"] = curState

    def stepLift(self, r: SimModule):
        if self.stepHeight is None:
            r.setError("stepHeight is empty {}".format(json.dumps(self.task)))
            self.status = MoveStatus.FAILED
        elif self.initLiftPos >= self.lift_max_height and self.stepHeight > 0:
            r.setNotice("Current fork height is liftMaxHeight, can not lift up! "
                        "forkHeight：{}".format(self.initLiftPos))
            self.status = MoveStatus.FINISHED
        elif self.initLiftPos <= self.lift_zero and self.stepHeight < 0:
            r.setNotice("Current fork height is liftZero, can not lift down! "
                        "forkHeight：{}".format(self.initLiftPos))
            self.status = MoveStatus.FINISHED
        else:
            if self.action_status == MoveStatus.NONE:
                self.action_status = MoveStatus.RUNNING
                self.endHeight = self.initLiftPos + self.stepHeight
                stepLiftHeight = self.initLiftPos + self.stepHeight
                if self.endHeight > self.lift_max_height:
                    self.endHeight = self.lift_max_height
                    r.setNotice(f"endHeight{stepLiftHeight} is higher than liftMaxHeight{self.lift_max_height}")
                if self.endHeight < self.lift_zero:
                    self.endHeight = self.lift_zero
                    r.setNotice(f"endHeight{stepLiftHeight} is lower than liftZero{self.lift_zero}")
                self.taskList = [
                    lift(self.lift_motor, self.endHeight, self.lift_up_reach_di)
                ]
                self.taskId = 0
            else:
                self.runTaskList(r)
            curState = dict()
            curState["state"] = self.action_status
            curState["liftPos"] = self.liftPos
            curState["liftSpeed"] = self.liftSpeed
            curState["taskId"] = self.taskId
            self.state["stepLift"] = curState

    def stretch(self, r: SimModule):
        if self.isStretchMotor is False:
            r.setError("stretch motor1 name is {}".format(self.stretch_motor))
            self.status = MoveStatus.FAILED
            return
        if self.stretchType == "speed" and self.stretchMode == "":
            r.setError("请输入stretchMode")
            self.status = MoveStatus.FAILED
            return self.status
        elif self.stretchType == "position" and self.stretchLength is None:
            r.setError("请输入stretchLength")
            self.status = MoveStatus.FAILED
            return self.status
        else:
            if self.action_status == MoveStatus.NONE:
                self.action_status = MoveStatus.RUNNING
                reachDI = -1
                if self.stretchType == "speed" or self.stretchType == "DO":
                    if self.stretchMode == "max":
                        reachDI = self.stretchMaxDi
                    elif self.stretchMode == "zero":
                        reachDI = self.stretchZeroDi
                    else:
                        r.setError("stretchMode is not chosen")
                        self.action_status = MoveStatus.FAILED
                else:
                    if self.stretchLength < self.stretch_zero:
                        self.stretchLength = self.stretch_zero
                        r.setNotice(f"stretchLength 小于货叉最小伸缩位置{self.stretch_zero}")
                    elif self.stretchLength > self.stretchMaxLength:
                        self.stretchLength = self.stretchMaxLength
                        r.setNotice(f"stretchLength 大于货叉最大伸缩位置{self.stretchMaxLength}")
                self.taskList = [stretch(self.stretch_motor, self.stretchMode,
                                         self.stretchLength, self.checkAllDi, [reachDI])]
                self.taskId = 0
            else:
                self.runTaskList(r)
            curState = dict()
            curState["state"] = self.action_status
            curState["taskId"] = self.taskId
            curState["stretchPos"] = self.stretchPos
            curState["stretchSpeed"] = self.stretchSpeed
            if self.stretchType == "speed":
                curState["stretchZeroDi"] = ModuleTool.check_DI(r, self.stretchZeroDi)
                curState["stretchMaxDi"] = ModuleTool.check_DI(r, self.stretchMaxDi)
            self.state["stretch"] = curState

    def stepStretch(self, r: SimModule):
        if self.stepLength is None:
            r.setError("stepLength is empty {}".format(json.dumps(self.task)))
            self.status = MoveStatus.FAILED
        elif not self.isStretchMotor:
            r.setError("no stretchMotor")
            self.status = MoveStatus.FAILED
        elif self.stretchType != "position":
            r.setError("stretchType is not position")
            self.status = MoveStatus.FAILED
        elif self.initStretchPos >= self.stretchMaxLength and self.stepLength > 0:
            r.setNotice("Current stretch length is stretchMaxLength, can not stretch out! "
                        "stretchLength：{}".format(self.initStretchPos))
            self.status = MoveStatus.FINISHED
        elif self.initStretchPos <= self.stretch_zero and self.stepLength < 0:
            r.setNotice("Current stretch length is stretchZero, can not stretch in! "
                        "stretchLength：{}".format(self.initStretchPos))
            self.status = MoveStatus.FINISHED
        else:
            if self.action_status == MoveStatus.NONE:
                self.action_status = MoveStatus.RUNNING
                self.stretchLength = self.initStretchPos + self.stepLength
                stepStretchHeight = self.initStretchPos + self.stepLength
                if self.stretchLength > self.stretchMaxLength:
                    self.stretchLength = self.stretchMaxLength
                    r.setNotice(
                        f"stretchLength{stepStretchHeight} is larger than stretchMaxLength{self.stretchMaxLength}")
                if self.stretchLength < self.stretch_zero:
                    self.stretchLength = self.stretch_zero
                    r.setNotice(f"stretchLength{stepStretchHeight} is smaller than stretchZero{self.stretch_zero}")
                self.taskList = [
                    stretch(self.stretch_motor, "", self.stretchLength, False, [-1])
                ]
                self.taskId = 0
            else:
                self.runTaskList(r)
            curState = dict()
            curState["state"] = self.action_status
            curState["stretchPos"] = self.stretchPos
            curState["stretchSpeed"] = self.stretchSpeed
            curState["taskId"] = self.taskId
            self.state["stepStretch"] = curState

    def pitch(self, r: SimModule):
        if self.isPitchMotor is False:
            r.setError("pitchMotor name is {}".format(self.stretch_motor))
            self.status = MoveStatus.FAILED
            return
        else:
            if self.action_status == MoveStatus.NONE:
                self.action_status = MoveStatus.RUNNING
                self.taskList = [(pitch(self.pitchMode))]
                self.taskId = 0
            else:
                self.runTaskList(r)
            curState = dict()
            curState["state"] = self.action_status
            curState["taskId"] = self.taskId
            curState["pitchPos"] = self.pitchPos
            curState["pitchZeroDi"] = ModuleTool.check_DI(r, self.pitchZeroDi)
            curState["pitchMaxDi"] = ModuleTool.check_DI(r, self.pitchMaxDi)
            self.state["pitch"] = curState

    def rec(self, r: SimModule):
        if "recFile" not in self.task:
            r.setError("recFile is empty {}".format(json.dumps(self.task)))
            self.status = MoveStatus.FAILED
        else:
            if self.action_status == MoveStatus.NONE:
                self.action_status = MoveStatus.RUNNING
                self.taskList = [recPallet(r)]
                self.taskId = 0
            else:
                self.runTaskList(r)
            curState = dict()
            curState["state"] = self.action_status
            curState["taskId"] = self.taskId
            curState["rec_result"] = self.recResult
            curState["target"] = self.target
            self.state["rec"] = curState

    def goMapPathDi(self, r: SimModule):
        if self.action_status == MoveStatus.NONE:
            self.action_status = MoveStatus.RUNNING
            self.taskList = [goMapPathDi()]
            self.taskId = 0
        else:
            self.runTaskList(r)
        curState = dict()
        curState["state"] = self.action_status
        curState["taskId"] = self.taskId
        curState["moveTask"] = r.moveTask()
        self.state["goMapPathDi"] = curState

    def goStationList(self, r: SimModule):
        if self.action_status == MoveStatus.NONE:
            self.action_status = MoveStatus.RUNNING
            self.taskList = [
                goStationList(r)]
            self.taskId = 0
        else:
            self.runTaskList(r)
        curState = dict()
        curState["state"] = self.action_status
        curState["taskId"] = self.taskId
        self.state["goStation"] = curState

    def test(self, r: SimModule):
        if self.action_status == MoveStatus.NONE:
            self.action_status = MoveStatus.RUNNING
        #     self.taskList = [
        #         # GoStraight(r, 0.3, straightMoveMode.backward, "y")
        #         adjustGo(r, False, "robot", -0.4405861496925354, 0.010898426175117493, 0.24683302640914917,
        #                  -0.08, 0.1, 0.0, False, [0, -1])
        #     ]
        #     self.taskId = 0
        # else:
        #     self.runTaskList(r)
        # odo = r.odo()

        # id(ModuleTool.delay(5))

        # if not self.init:
        #     speed_dict = r.getNextSpeed()
        #     speed_x = speed_dict.get("x", 0.0)
        #     speed_y = speed_dict.get("y", 0.0)
        #     speed_rotate = speed_dict.get("rotate", 0.0)
        #     if speed_x != 0 and speed_rotate == 0:
        #         r.setUserWarning(55900, f"伸叉状态下不允许前进/后退（x方向）运动")
        #     elif speed_x == 0 and speed_rotate != 0:
        #         r.setUserWarning(55901, f"伸叉状态下不允许原地旋转")
        #     elif speed_x != 0 and speed_rotate != 0:
        #         r.setUserWarning(55902, f"伸叉状态下不允许前进/后退（x方向）运动、原地旋转")
        #     elif speed_x == 0.0 and speed_rotate == 0.0:
        #         r.clearWarning(55900)
        #         r.clearWarning(55901)
        #         r.clearWarning(55902)
        #         self.status = MoveStatus.FINISHED
        # self.start_time1 = time.time()
        # self.start_time2 = time.time()
        # robotFile = r.getRobotFile()

        # r.forkGoods(True, self.task.get("recFile", ""))
        # width = max(self.recParams['pallet_width'], self.recParams['goodsWidth'])
        # length = max(self.recParams['pallet_length'], self.recParams['goodsLength'])
        # if self.fork_offset_theta != 0:
        #     r.setGoodsShape(width / 2,
        #                     width / 2,
        #                     length)
        # else:
        #     r.setGoodsShape(self.pallet2odo,
        #                     length - self.pallet2odo,
        #                     width)
        curState = dict()
        # DI = r.Di()
        # allDiStatus1 = None
        # reachDi = [0, -1]
        # if len(reachDi) < 4:
        #     # 最多支持4个到位DI，不足时补全
        #     num2Add = 4 - len(reachDi)
        #     # 使用None补全列表
        #     reachDi.extend([-1] * num2Add)
        # DI = r.Di()
        # nodes = DI.get('node', list())
        # allDiStatus = [item["status"] for item in nodes if item["id"] in reachDi]
        # if self.checkAllDi:
        #     if all(allDiStatus):
        #         allDiStatus1 = True
        # else:
        #     if any(allDiStatus):
        #         allDiStatus1 = True

        # if self.useLoadRecHeight:
        #     set_info_data = dict()
        #     end_height_data = r.getGData()
        #     self.endHeight = r.getGData().get('loadLiftHeight', None)
        #     end_height_data_time = r.getGData().get('end_height_data_time', None)
        #     set_info_data["end_height_data"] = end_height_data
        #     set_info_data["loadLiftHeight"] = self.endHeight
        #     set_info_data["end_height_data_time"] = end_height_data_time
        #     self.state["end_height_data"] = set_info_data
        #     if self.endHeight is None or end_height_data_time is None:
        #         r.setError(f"loadLiftHeight is not in globalData")
        # else:
        #     data_raw = r.getGData()
        #     end_height_data_time = self.seqGenerate()
        #     loadLiftHeight = {
        #         "loadLiftHeight": 0.3,
        #         "end_height_data_time": end_height_data_time
        #     }
        #     r.setGData(loadLiftHeight)
        #     data_new = r.getGData()
        #     curState["data_new"] = data_new
        #     curState["data_raw"] = data_raw
        #     curState["end_height_data_time"] = end_height_data_time
        # curState["state"] = self.operationStatus
        # curState["taskId"] = self.taskId
        # curState["odo"] = odo
        # curState["robotFile"] = robotFile
        # curState["start_time2_id"] = id(self.start_time2)
        # curState["delay_id"] = id(ModuleTool.delay(5))
        # curState["controller"] = r.controller()
        self.state["test"] = r.getLM("1FZKSPZCB006", True)

    def update_data(self, r: SimModule):
        self.status = MoveStatus.FINISHED

    def load(self, r: SimModule):
        if self.action_status == MoveStatus.NONE:

            if r.hasGoods():
                self.state["load"] = "Fork has goods, cannot load"
                r.setError(f"Fork has goods, cannot load")
                self.status = MoveStatus.FAILED
                return self.status
            if self.startHeight is None \
                    and self.endHeight is None \
                    and self.liftUpHeight is None \
                    and self.stretchLength is None:
                self.state["load"] = "startHeight & endHeight & liftUpHeight & stretchLength is missing"
                r.setError(f"startHeight & endHeight & liftUpHeight & stretchLength is missing")
                self.status = MoveStatus.FAILED
                return
            elif self.startHeight is None:
                self.startHeight = self.initLiftPos
            if self.stretchLength:
                if self.stretchLength > self.stretchMaxLength:
                    r.setError(
                        f"stretchLength {self.stretchLength} is larger than stretchMaxLength {self.stretchMaxLength}")
                    self.status = MoveStatus.FAILED
                    return
                elif self.stretchLength < self.stretch_zero:
                    self.stretchLength = self.stretch_zero

            self.action_status = MoveStatus.RUNNING
        elif self.action_status == MoveStatus.RUNNING:
            # 识别后取货
            if self.recognize:
                # 识别前调整任务：货叉放平（forward）、收回货叉、调整货叉高度至识别高度
                if self.recTaskInit:
                    self.taskList = []
                    if self.target[3] != -1 and self.adjustDirFirst:
                        self.taskList.append(dirAdjust(r, self.adjust_angle))
                    if self.isPitchMotor:
                        self.taskList.append(pitch("forward"))
                    if self.isStretchMotor:
                        self.taskList.append(stretch(self.stretch_motor, "zero",
                                                     self.stretch_zero, self.checkAllDi, [self.stretchZeroDi]))
                    # 调整货叉高度至识别高度
                    self.taskList.append(lift(self.lift_motor, self.startHeight))
                    # 识别及二次识别
                    if self.firstAdjust:
                        self.taskList.append(recPallet(r))
                        self.firstAdjust = False
                    else:
                        if self.omni_model:
                            pass
                        else:
                            self.taskList.extend([
                                GoStraight(r, self.readjustForwardDist, straightMoveMode.forward),
                                recPallet(r)
                            ])
                    self.taskId = 0
                    self.recTaskInit = False
                if self.readjust:
                    # 识别后调整
                    if self.adjustTask1Init and not self.recTaskInit and self.recTaskStatus:
                        pos2robotTarget = []
                        if self.recParams['recCoordinate'] == "world":
                            robot2world = [r.loc()["x"], r.loc()["y"], r.loc()["angle"]]  # 获取机器人在世界坐标系下的位置
                            Target = [self.recResult['x'], self.recResult['y'], self.recResult['yaw']]  # 目标点在世界坐标系的位置
                            pos2robotTarget = Pos2Base(Target, robot2world)  # 转换识别结果到机器人坐标系
                            shelf_center2target = [-0.5, 0, 0]  # 货架中心在识别结果坐标系下的位置（根据识别文件设置的长宽）
                            shelf_center2robot = Pos2World(shelf_center2target, pos2robotTarget)  # 计算实际货架中心在机器人坐标系下的位置
                        elif self.recParams['recCoordinate'] == "robot":
                            pos2robotTarget = [self.recResult['x'], self.recResult['y'],
                                               self.recResult['yaw']]  # 目标点在机器人坐标系的位置
                        pos2robotForwardX = pos2robotTarget[0] + self.minAheadDist * math.cos(pos2robotTarget[2])
                        pos2robotForwardY = pos2robotTarget[1] + self.minAheadDist * math.sin(pos2robotTarget[2])
                        pos2robotForward = [pos2robotForwardX, pos2robotForwardY, pos2robotTarget[2]]
                        self.state["pos2robotForward"] = pos2robotForward
                        self.taskList = [
                            adjustGo(r, self.omni_model, "robot",
                                     pos2robotForward[0], pos2robotForward[1], pos2robotForward[2],
                                     0, 0, 0, False, [-1]),
                            recPallet(r)
                        ]
                        self.taskId = 0
                        self.adjustTask1Init = False
                    # 二次调整判断
                    if self.evaluateTaskInit and not self.adjustTask1Init and self.adjustTask1Status:
                        self.taskList = [
                            precisionEvaluate(r)
                        ]
                        self.taskId = 0
                        self.evaluateTaskInit = False
                    if (self.adjustTask2Init
                            and not self.evaluateTaskInit and self.evaluateTaskStatus
                            and not self.adjustTask1Init and self.adjustTask1Status):
                        if self.is_expand_motor1 and self.is_expand_motor2:
                            dist = self.pallet_pocket_width / 2
                            self.taskList = [
                                expand(self.expand_motor1, dist, self.expand_motor2, dist),
                                lift(self.lift_motor, self.loadLiftHeight)
                            ]
                        else:
                            self.taskList = [lift(self.lift_motor, self.loadLiftHeight)]
                        # 有前移机构
                        if self.isStretchMotor:
                            # 如果需要伸出插齿取叉货物
                            if self.stretchLength > self.stretch_zero or self.stretchType == "speed" or self.stretchType == "DO":
                                # 先伸货叉再倒车取货
                                if self.load_stretch_first:
                                    self.taskList.extend([
                                        stretch(self.stretch_motor, "max",
                                                self.stretchLength, self.checkAllDi, [-1]),
                                        adjustGo(r, self.omni_model, "robot", -self.minAheadDist,
                                                 0, 0, self.backDist, 0, 0,
                                                 self.checkAllDi, self.multiReachDI)
                                    ])

                                else:
                                    self.taskList.extend([
                                        adjustGo(r, self.omni_model, "robot", -self.minAheadDist,
                                                 0, 0, self.backDist, 0, 0,
                                                 self.checkAllDi, [-1]),
                                        stretch(self.stretch_motor, "max",
                                                self.stretchLength, self.checkAllDi, self.multiReachDI)
                                    ])
                            # 不需要伸出插齿去取叉货
                            else:
                                self.taskList.extend([
                                    stretch(self.stretch_motor, "zero",
                                            self.stretch_zero, self.checkAllDi, [self.stretchZeroDi]),
                                    adjustGo(r, self.omni_model, "robot", -self.minAheadDist,
                                             0, 0, self.backDist, 0, 0,
                                             self.checkAllDi, [-1])
                                ])
                        # 无前移机构
                        else:
                            self.taskList = [
                                # lift(self.liftMotor, self.loadLiftHeight),
                                adjustGo(r, self.omni_model, "robot",
                                         -self.minAheadDist, 0, 0, self.backDist,
                                         0, 0, self.checkAllDi, self.multiReachDI),
                            ]
                        self.taskId = 0
                        self.adjustTask2Init = False
                else:
                    if self.adjustTask2Init and not self.recTaskInit and self.recTaskStatus:
                        if self.is_expand_motor1 and self.is_expand_motor2:
                            dist = self.pallet_pocket_width / 2
                            self.taskList = [
                                expand(self.expand_motor1, dist, self.expand_motor2, dist),
                                lift(self.lift_motor, self.loadLiftHeight)
                            ]
                        else:
                            self.taskList = [lift(self.lift_motor, self.loadLiftHeight)]
                        pos2robotTarget = []
                        if self.recParams['recCoordinate'] == "world":
                            robot2world = [r.loc()["x"], r.loc()["y"], r.loc()["angle"]]
                            Target = [self.recResult['x'], self.recResult['y'], self.recResult['yaw']]  # 目标点在世界坐标系的位置
                            pos2robotTarget = Pos2Base(Target, robot2world)
                        elif self.recParams['recCoordinate'] == "robot":
                            pos2robotTarget = [self.recResult['x'], self.recResult['y'],
                                               self.recResult['yaw']]  # 目标点在机器人坐标系的位置
                        if self.isStretchMotor:
                            # 如果需要伸出插齿取叉货物
                            if self.stretchLength > self.stretch_zero or self.stretchType == "speed" or self.stretchType == "DO":
                                if self.load_stretch_first:
                                    # 先伸货叉再倒车取货
                                    self.taskList.extend([
                                        stretch(self.stretch_motor, "max",
                                                self.stretchLength, self.checkAllDi, [-1]),
                                        adjustGo(r, self.omni_model, "robot",
                                                 pos2robotTarget[0], pos2robotTarget[1], pos2robotTarget[2],
                                                 self.backDist, self.minAheadDist, self.aheadDist,
                                                 self.checkAllDi, self.multiReachDI)
                                    ])
                                else:
                                    self.taskList.extend([
                                        adjustGo(r, self.omni_model, "robot",
                                                 pos2robotTarget[0], pos2robotTarget[1], pos2robotTarget[2],
                                                 self.backDist, self.minAheadDist, self.aheadDist,
                                                 self.checkAllDi, [-1]),
                                        stretch(self.stretch_motor, "max",
                                                self.stretchLength, self.checkAllDi, [-1])
                                    ])
                            # 不需要伸出插齿去取叉货
                            else:
                                self.taskList.extend([
                                    stretch(self.stretch_motor, "zero",
                                            self.stretch_zero, self.checkAllDi, [self.stretchZeroDi]),
                                    adjustGo(r, self.omni_model, "robot",
                                             pos2robotTarget[0], pos2robotTarget[1], pos2robotTarget[2],
                                             self.backDist, self.minAheadDist, self.aheadDist,
                                             self.checkAllDi, self.multiReachDI)
                                ])
                        # 无前移机构
                        else:
                            self.taskList.append(
                                adjustGo(r, self.omni_model, "robot",
                                         pos2robotTarget[0], pos2robotTarget[1], pos2robotTarget[2],
                                         self.backDist, self.minAheadDist, self.aheadDist,
                                         self.checkAllDi, self.multiReachDI)
                            )
                        self.taskId = 0
                        self.adjustTask2Init = False
                        self.evaluateTaskInit = False
                        self.evaluateTaskStatus = True
                if self.goods_opt_task_init and not self.adjustTask2Init and self.adjustTask2Status:
                    if not self.double_lift:
                        self.taskList = [
                            backCheckDi(r, self.checkAllDi, self.multiReachDI)
                        ]
                        if self.endHeight:
                            self.taskList.append(lift(self.lift_motor, self.endHeight, self.lift_up_reach_di))
                        else:
                            self.taskList.append(lift(self.lift_motor, self.startHeight + self.liftUpHeight,
                                                      self.lift_up_reach_di))
                        self.taskList = [
                            backCheckDi(r, self.checkAllDi, self.multiReachDI),
                            lift(self.lift_motor, self.loadLiftUpHeight, self.lift_up_reach_di)
                        ]
                        # 俯仰机构是否动作
                        if self.isPitchMotor and self.loadPitch:
                            self.taskList.append(pitch("backward"))
                        # 收回货叉
                        if self.isStretchMotor:
                            self.taskList.extend([
                                stretch(self.stretch_motor, "zero",
                                        self.stretch_zero, self.checkAllDi, [self.stretchZeroDi])
                            ])
                        # 脱离库位
                        if self.leaveLoc:
                            if self.fork_offset_theta != 0:
                                self.taskList.append(GoStraight(r, self.forwardDist, straightMoveMode.backward, "y"))
                            else:
                                self.taskList.append(GoStraight(r, self.forwardDist, straightMoveMode.forward))
                    else:
                        self.taskList = [
                            backCheckDi(r, self.checkAllDi, self.multiReachDI),
                            lift(self.lift_motor, self.load_lift_up_height1, self.lift_up_reach_di)
                        ]
                        # 俯仰机构是否动作
                        if self.isPitchMotor and self.loadPitch:
                            self.taskList.append(pitch("backward"))
                        if self.fork_offset_theta != 0:
                            self.taskList.append(GoStraight(r, self.forwardDist, straightMoveMode.backward, "y"))
                        else:
                            self.taskList.append(GoStraight(r, self.forwardDist, straightMoveMode.forward))
                        self.taskList.append(lift(self.lift_motor, self.load_lift_up_height2, self.lift_up_reach_di))
                        # 收回货叉
                        if self.isStretchMotor:
                            self.taskList.extend([
                                stretch(self.stretch_motor, "zero",
                                        self.stretch_zero, self.checkAllDi, [self.stretchZeroDi])
                            ])
                    # 是否调整货叉高度至行走高度
                    if self.loadMoveHeightOn:
                        self.taskList.append(lift(self.lift_motor, self.loadMoveHeight))
                    self.taskId = 0
                    self.goods_opt_task_init = False
            # 不识别，盲叉取货
            else:
                # 任务动作初始化
                if self.goods_opt_task_init:
                    # 有前移机构
                    if self.isStretchMotor:
                        # 需要伸出插齿取叉货物，且先伸货叉
                        if self.stretchLength > self.stretch_zero or self.stretchType == "speed" or self.stretchType == "DO":
                            if self.load_stretch_first:
                                self.taskList = [
                                    lift(self.lift_motor, self.startHeight),
                                    stretch(self.stretch_motor, "max",
                                            self.stretchLength, self.checkAllDi, [-1]),
                                    goMapPathDi()
                                ]
                            else:
                                # 需要伸出插齿取叉货物，且后伸货叉
                                if self.stretchLength > self.stretch_zero or self.stretchType == "speed" or self.stretchType == "DO":
                                    self.taskList = [
                                        lift(self.lift_motor, self.startHeight),
                                        goMapPathDi(False),
                                        stretch(self.stretch_motor, "max",
                                                self.stretchLength, self.checkAllDi, self.multiReachDI),
                                        backCheckDi(r, self.checkAllDi, self.multiReachDI)
                                    ]
                        # 不需要伸出插齿取叉货
                        else:
                            self.taskList = [
                                lift(self.lift_motor, self.startHeight),
                                stretch(self.stretch_motor, "zero",
                                        self.stretch_zero, self.checkAllDi, [self.stretchZeroDi]),
                                goMapPathDi()
                            ]
                    # 无前移机构
                    else:
                        self.taskList = [
                            lift(self.lift_motor, self.startHeight),
                            goMapPathDi()
                        ]
                    if not self.double_lift:
                        # r.setError()
                        if self.endHeight:
                            self.taskList.append(lift(self.lift_motor, self.endHeight, self.lift_up_reach_di))
                        else:
                            self.taskList.append(lift(self.lift_motor, self.startHeight + self.liftUpHeight,
                                                      self.lift_up_reach_di))
                        # 俯仰机构是否动作
                        if self.isPitchMotor and self.loadPitch:
                            self.taskList.append(pitch("backward"))
                        # 收回货叉
                        if self.isStretchMotor:
                            self.taskList.append(
                                stretch(self.stretch_motor, "zero",
                                        self.stretch_zero, self.checkAllDi, [self.stretchZeroDi])
                            )
                        # 脱离库位
                        if self.leaveLoc:
                            if self.fork_offset_theta != 0:
                                self.taskList.append(GoStraight(r, self.forwardDist, straightMoveMode.backward, "y"))
                            else:
                                self.taskList.append(GoStraight(r, self.forwardDist, straightMoveMode.forward))
                    else:
                        # 第一次抬升
                        self.taskList.append(lift(self.lift_motor, self.load_lift_up_height1))
                        # 俯仰机构是否动作
                        if self.isPitchMotor and self.loadPitch:
                            self.taskList.append(pitch("backward"))
                        # 脱离库位
                        if self.fork_offset_theta != 0:
                            self.taskList.append(GoStraight(r, self.forwardDist, straightMoveMode.backward, "y"))
                        else:
                            self.taskList.append(GoStraight(r, self.forwardDist, straightMoveMode.forward))
                        # 第二次抬升
                        self.taskList.append(lift(self.lift_motor, self.load_lift_up_height2))
                        # 收回货叉
                        if self.isStretchMotor:
                            self.taskList.append(
                                stretch(self.stretch_motor, "zero",
                                        self.stretch_zero, self.checkAllDi, [self.stretchZeroDi])
                            )
                    # 是否调整货叉高度至行走高度
                    if self.loadMoveHeightOn:
                        self.taskList.append(lift(self.lift_motor, self.loadMoveHeight))
                    self.taskId = 0
                    self.goods_opt_task_init = False
            self.runTaskList(r)
        if (not self.recTaskInit and not self.recTaskStatus
                and self.action_status == MoveStatus.FINISHED):
            self.recTaskStatus = True
            self.action_status = MoveStatus.RUNNING
            r.setNotice("recTask Finish")
        if not self.adjustTask1Init and not self.adjustTask1Status and self.action_status == MoveStatus.FINISHED:
            self.adjustTask1Status = True
            self.action_status = MoveStatus.RUNNING
            r.setNotice("adjustTask1 Finish")
        if not self.adjustTask2Init and not self.adjustTask2Status and self.action_status == MoveStatus.FINISHED:
            self.adjustTask2Status = True
            self.action_status = MoveStatus.RUNNING
            r.setNotice("adjustTask2 Finish")
        if not self.goods_opt_task_init and not self.goods_opt_task_status and self.action_status == MoveStatus.FINISHED:
            self.goods_opt_task_status = True
            r.forkGoods(True, self.task("recfile", ""))
            if self.recFile:
                width = max(self.recParams['pallet_width'], self.recParams['goodsWidth'])
                length = max(self.recParams['pallet_length'], self.recParams['goodsLength'])
                if self.fork_offset_theta != 0:
                    r.setGoodsShape(width / 2, width / 2, length)
                else:
                    r.setGoodsShape(self.pallet2odo, length - self.pallet2odo, width)
            r.setNotice("moveTask Finish")
            self.status = MoveStatus.FINISHED
        if self.action_status == MoveStatus.FAILED:
            self.status = MoveStatus.FAILED

        curState = dict()
        curState["state"] = self.action_status
        curState["liftPos"] = self.liftPos
        curState["stretchPos"] = self.stretchPos
        curState["pitchPos"] = self.pitchPos
        if self.isStretchMotor and self.stretchType == "speed":
            curState["stretchZeroDi"] = ModuleTool.check_DI(r, self.stretchZeroDi)
            curState["stretchMaxDi"] = ModuleTool.check_DI(r, self.stretchMaxDi)
        if self.isPitchMotor:
            curState["pitchZeroDi"] = ModuleTool.check_DI(r, self.pitchZeroDi)
            curState["pitchMaxDi"] = ModuleTool.check_DI(r, self.pitchMaxDi)
        curState["recTaskInit"] = self.recTaskInit
        curState["adjustTaskInit"] = self.adjustTask1Init
        curState["evaluateTaskInit"] = self.evaluateTaskInit
        curState["moveTaskInit"] = self.goods_opt_task_init

        curState["recTaskStatus"] = self.recTaskStatus
        curState["adjustTaskStatus"] = self.adjustTask1Status
        curState["evaluateTaskStatus"] = self.evaluateTaskStatus
        curState["moveTaskStatus"] = self.goods_opt_task_status
        curState["adjustTimes"] = self.adjustTimes
        curState["recResultToRobot"] = self.recResultToRobot  # 叉取的栈板识别结果
        # curState["recPos"] = self.recPos
        curState["backDist"] = self.backDist
        curState["loadLiftHeight"] = self.loadLiftHeight  # 栈板叉取时货叉高度
        curState["loadLiftUpHeight"] = self.loadLiftUpHeight  # 栈板叉取后的货叉高度
        if not self.loadAll:
            curState["widthData"] = self.width_data
            curState["unstackErrorType"] = self.unstack_error_type
            curState["errorsPallet"] = self.errors_pallet
            curState["recResultPalletNum"] = self.rec_result_pallet_num  # 识别结果中栈板的数量
            curState["palletNormalCount"] = self.palletNormalCount  # 栈板正常数量
            curState["palletHeight"] = self.height_data
        curState["taskId"] = self.taskId
        self.state["load"] = curState

    def unload(self, r: SimModule):
        if self.action_status == MoveStatus.NONE:
            self.action_status = MoveStatus.RUNNING
            if self.startHeight is None \
                    and self.endHeight is None \
                    and self.liftDownHeight is None \
                    and self.stretchLength is None:
                self.state["load"] = "startHeight & endHeight & liftDownHeight & stretchLength is missing"
                r.setError(f"startHeight & endHeight & liftDownHeight & stretchLength is missing")
                self.status = MoveStatus.FAILED
                return
            if self.startHeight:
                if 0 <= self.startHeight < self.lift_zero:
                    self.startHeight = self.lift_zero
                    r.setNotice(f"startHeight 小于货叉最小起升高度{self.lift_zero}")
                elif self.startHeight > self.lift_max_height:
                    self.startHeight = self.lift_max_height
                    r.setNotice(f"startHeight 大于货叉最大起升高度{self.lift_max_height}")
            else:
                self.startHeight = self.liftPos
            if self.useLoadRecHeight:
                set_info_data = dict()
                end_height_data = r.getGData()
                self.endHeight = r.getGData().get('loadLiftHeight', None)
                end_height_data_time = r.getGData().get('end_height_data_time', None)
                # set_info_data["end_height_data"] = end_height_data
                set_info_data["loadLiftHeight"] = self.endHeight
                set_info_data["end_height_data_time"] = end_height_data_time
                self.state["unload_end_height_data"] = set_info_data
                if self.endHeight is None or end_height_data_time is None:
                    r.setError(f"loadLiftHeight is not in globalData")
            if self.endHeight:
                if 0 <= self.endHeight < self.lift_zero:
                    self.endHeight = self.lift_zero
                    r.setNotice(f"endHeight 小于货叉最小起升高度{self.lift_zero}")
                elif self.endHeight > self.lift_max_height:
                    self.endHeight = self.lift_max_height
                    r.setNotice(f"endHeight 大于货叉最大起升高度{self.lift_max_height}")
            else:
                if not self.double_lift:
                    r.setError(f"endHeight is missing")
                    self.status = MoveStatus.FAILED
                    return self.status
            if self.stretchLength:
                if 0 <= self.stretchLength < self.stretch_zero:
                    self.stretchLength = self.stretch_zero
                elif self.stretchLength > self.stretchMaxLength:
                    self.stretchLength = self.stretchMaxLength
                    r.setNotice(f"stretchLength 大于货叉最大伸缩位置{self.stretchMaxLength}")
            else:
                self.stretchLength = self.stretchPos
        elif self.action_status == MoveStatus.RUNNING:
            if self.recTaskInit:
                self.taskList = []
                if self.target[3] != -1 and self.adjustDirFirst:
                    self.taskList.append(dirAdjust(r, self.adjust_angle))
                if self.isPitchMotor:
                    self.taskList.append(pitch("forward"))
                if self.isStretchMotor:
                    self.taskList.append(stretch(self.stretch_motor, "zero",
                                                 self.stretch_zero, self.checkAllDi, [self.stretchZeroDi]))
                # 调整货叉高度至识别高度并识别
                self.taskList.append(lift(self.lift_motor, self.startHeight))
                # 是否识别放货
                if self.recognize:
                    self.taskList.append(recPallet(r))
                elif not self.recognize or not self.adjustHeight:
                    self.unloadLiftHeight = self.startHeight
                self.taskId = 0
                self.recTaskInit = False
            if self.goods_opt_task_init and not self.recTaskInit and self.recTaskStatus:
                self.taskList = [lift(self.lift_motor, self.unloadLiftHeight)]
                if self.recognize:
                    self.taskList.append(
                        adjustGo(r, self.omni_model, self.recParams['recCoordinate'],
                                 self.recResult['x'], self.recResult['y'], self.recResult['yaw'],
                                 self.backDist, self.minAheadDist, self.aheadDist, False, [-1])
                    )
                    if self.isStretchMotor:
                        if self.stretchLength > self.stretch_zero or self.stretchType == "speed" or self.stretchType == "DO":
                            self.taskList.append(stretch(self.stretch_motor, "max",
                                                         self.stretchLength, self.checkAllDi, [-1]))
                        elif 0 <= self.stretchLength <= self.stretch_zero and self.stretchType == "position":
                            self.taskList.append(stretch(self.stretch_motor, "zero",
                                                         self.stretch_zero, self.checkAllDi, [self.stretchZeroDi]))
                    self.taskList.append(lift(self.lift_motor, self.endHeight, self.lift_up_reach_di))
                else:
                    if not self.double_lift:
                        self.taskList.append(goMapPathDi())
                        if self.isStretchMotor:
                            if self.stretchLength > self.stretch_zero or self.stretchType == "speed" or self.stretchType == "DO":
                                self.taskList.append(stretch(self.stretch_motor, "max",
                                                             self.stretchLength, self.checkAllDi, [-1]))
                            elif 0 <= self.stretchLength <= self.stretch_zero and self.stretchType == "position":
                                self.taskList.append(stretch(self.stretch_motor, "zero",
                                                             self.stretch_zero, self.checkAllDi, [self.stretchZeroDi]))
                        self.taskList.append(lift(self.lift_motor, self.endHeight, self.lift_up_reach_di))
                    else:
                        if self.isStretchMotor:
                            if self.stretchLength > self.stretch_zero or self.stretchType == "speed" or self.stretchType == "DO":
                                self.taskList.append(stretch(self.stretch_motor, "max",
                                                             self.stretchLength, self.checkAllDi, [-1]))
                            elif 0 <= self.stretchLength <= self.stretch_zero and self.stretchType == "position":
                                self.taskList.append(stretch(self.stretch_motor, "zero",
                                                             self.stretch_zero, self.checkAllDi, [self.stretchZeroDi]))
                        self.taskList.append(lift(self.lift_motor, self.load_lift_up_height1))
                        self.taskList.append(goMapPathDi())
                        self.taskList.append(lift(self.lift_motor, self.load_lift_up_height2))
                if self.isStretchMotor:
                    self.taskList.append(stretch(self.stretch_motor, "zero",
                                                 self.stretch_zero, self.checkAllDi, [self.stretchZeroDi]))
                if self.leaveLoc:
                    if self.fork_offset_theta != 0:
                        self.taskList.append(GoStraight(r, self.forwardDist, straightMoveMode.backward, "y"))
                    else:
                        self.taskList.append(GoStraight(r, self.forwardDist, straightMoveMode.forward))
                if self.loadMoveHeightOn:
                    self.taskList.append(lift(self.lift_motor, self.loadMoveHeight))
                self.taskId = 0
                self.goods_opt_task_init = False
            self.runTaskList(r)
        if (not self.recTaskInit and not self.recTaskStatus
                and self.action_status == MoveStatus.FINISHED):
            self.recTaskStatus = True
            self.action_status = MoveStatus.RUNNING
            r.setNotice("recTask Finish")
        if not self.goods_opt_task_init and not self.goods_opt_task_status and self.action_status == MoveStatus.FINISHED:
            self.goods_opt_task_status = True
            r.forkGoods(False, "")
            r.setNotice("moveTask Finish")
            self.status = MoveStatus.FINISHED
        curState = dict()
        curState["state"] = self.action_status
        curState["liftPos"] = self.liftPos
        curState["stretchPos"] = self.stretchPos
        curState["pitchPos"] = self.pitchPos
        if self.isStretchMotor and self.stretchType == "speed" or self.stretchType == "DO":
            curState["stretchZeroDi"] = ModuleTool.check_DI(r, self.stretchZeroDi)
            curState["stretchMaxDi"] = ModuleTool.check_DI(r, self.stretchMaxDi)
        if self.isPitchMotor:
            curState["pitchZeroDi"] = ModuleTool.check_DI(r, self.pitchZeroDi)
            curState["pitchMaxDi"] = ModuleTool.check_DI(r, self.pitchMaxDi)
        curState["taskId"] = self.taskId
        self.state["unload"] = curState

    def simple_unload(self, r: SimModule):
        if self.action_status == MoveStatus.NONE:
            self.action_status = MoveStatus.RUNNING
            self.taskList = []
            if self.isStretchMotor:
                if self.stretchLength:
                    if 0 <= self.stretchLength < self.stretch_zero:
                        self.stretchLength = self.stretch_zero
                    elif self.stretchLength > self.stretchMaxLength:
                        self.stretchLength = self.stretchMaxLength
                        r.setNotice(f"stretchLength 大于货叉最大伸缩位置{self.stretchMaxLength}")
                    self.taskList.append(stretch(self.stretch_motor, "",
                                                 self.stretchLength, self.checkAllDi, [-1]))
                elif self.stretchMode and (self.stretchType == "speed" or self.stretchType == "DO"):
                    self.taskList.append(stretch(self.stretch_motor, self.stretchMode,
                                                 self.stretchLength, self.checkAllDi, [-1]))
            if self.endHeight:
                if 0 <= self.endHeight < self.lift_zero:
                    self.endHeight = self.lift_zero
                    r.setNotice(f"endHeight 小于货叉最小起升高度{self.lift_zero}")
                elif self.endHeight > self.lift_max_height:
                    self.endHeight = self.lift_max_height
                    r.setNotice(f"endHeight 大于货叉最大起升高度{self.lift_max_height}")
                self.taskList.append(lift(self.lift_motor, self.endHeight, self.lift_up_reach_di))
            self.taskId = 0
        elif self.action_status == MoveStatus.RUNNING:
            self.runTaskList(r)
        elif self.action_status == MoveStatus.FINISHED:
            r.forkGoods(False, "")
            self.status = MoveStatus.FINISHED
        curState = dict()
        curState["state"] = self.action_status
        curState["liftPos"] = self.liftPos
        curState["stretchPos"] = self.stretchPos
        if self.isStretchMotor and self.stretchType == "speed" or self.stretchType == "DO":
            curState["stretchZeroDi"] = ModuleTool.check_DI(r, self.stretchZeroDi)
            curState["stretchMaxDi"] = ModuleTool.check_DI(r, self.stretchMaxDi)
        curState["taskId"] = self.taskId
        self.state["simple_unload"] = curState

    def goStationWithFork(self, r: SimModule):

        if self.action_status == MoveStatus.NONE:
            self.action_status = MoveStatus.RUNNING
            self.taskList = [GoMapWithFork(self.forkMidHeight, self.stretchMode, self.stretchLength, self.forkMoveMode)]
            self.taskId = 0
        else:
            self.runTaskList(r)
        curState = dict()
        curState["state"] = self.action_status
        curState["liftPos"] = self.liftPos
        curState["stretchPos"] = self.stretchPos
        curState["pitchPos"] = self.pitchPos
        if self.isStretchMotor and self.stretchType == "speed" or self.stretchType == "DO":
            curState["stretchZeroDi"] = ModuleTool.check_DI(r, self.stretchZeroDi)
            curState["stretchMaxDi"] = ModuleTool.check_DI(r, self.stretchMaxDi)
        if self.isPitchMotor:
            curState["pitchZeroDi"] = ModuleTool.check_DI(r, self.pitchZeroDi)
            curState["pitchMaxDi"] = ModuleTool.check_DI(r, self.pitchMaxDi)
        curState["taskId"] = self.taskId
        self.state["goStationWithLift"] = curState

    def zero(self, r: SimModule):
        if r.hasGoods() or ModuleTool.check_DI(r, self.reachDI1) or ModuleTool.check_DI(r, self.reachDI2):
            r.setError(f"Fork has goods, cannot cannot run operation of zero")
            self.status = MoveStatus.FAILED
            return
        if self.action_status == MoveStatus.NONE:
            self.action_status = MoveStatus.RUNNING
            reachDI = -1
            self.stretchMode = "zero"
            self.taskList = []

            if self.isStretchMotor:
                self.taskList.append(
                    stretch(self.stretch_motor, self.stretchMode, self.stretch_zero, self.checkAllDi, [reachDI])
                )
            if self.is_lateral_motor:
                self.taskList.append(
                    lateral(self.lateral_motor, self.lateral_zero)
                )
            self.taskList.append(lift(self.lift_motor, self.lift_zero))
            self.taskId = 0
        else:
            self.runTaskList(r)
        curState = dict()
        curState["state"] = self.action_status
        curState["liftPos"] = self.liftPos
        curState["stretchPos"] = self.stretchPos
        curState["pitchPos"] = self.pitchPos
        curState["lateral_pos"] = self.lateral_pos
        if self.isStretchMotor and self.stretchType == "speed" or self.stretchType == "DO":
            curState["stretchZeroDi"] = ModuleTool.check_DI(r, self.stretchZeroDi)
            curState["stretchMaxDi"] = ModuleTool.check_DI(r, self.stretchMaxDi)
        if self.isPitchMotor:
            curState["pitchZeroDi"] = ModuleTool.check_DI(r, self.pitchZeroDi)
            curState["pitchMaxDi"] = ModuleTool.check_DI(r, self.pitchMaxDi)
        curState["taskId"] = self.taskId
        self.state["zero"] = curState

    def weightGood(self, r: SimModule):
        if self.action_status == MoveStatus.NONE:
            self.action_status = MoveStatus.RUNNING
            self.taskList = [weightGood()]
            self.taskId = 0
        else:
            self.runTaskList(r)
        curState = dict()
        curState["state"] = self.action_status
        curState["taskId"] = self.taskId
        self.state["weightGood"] = curState

    def goodsCheck(self, r: SimModule):
        if self.action_status == MoveStatus.NONE:
            self.action_status = MoveStatus.RUNNING
            self.taskList = [goodsCheck(self.recFile)]
            self.taskId = 0
        else:
            self.runTaskList(r)
        curState = dict()
        curState["state"] = self.action_status
        curState["taskId"] = self.taskId
        self.state["goodsCheck"] = curState

    def unloadHeightDetect(self, r: SimModule):
        if self.action_status == MoveStatus.NONE:
            self.action_status = MoveStatus.RUNNING
            self.taskList = [unloadHeightDetect(self.lift_motor, 0.5, 3)]
            self.taskId = 0
        else:
            self.runTaskList(r)
        curState = dict()
        curState["state"] = self.action_status
        curState["taskId"] = self.taskId
        self.state["unloadHeightDetect"] = curState

    def getMassage(self, r: SimModule):
        if self.action_status == MoveStatus.NONE:
            self.action_status = MoveStatus.RUNNING
            self.taskList = [getMassage(f"rbk.protocol.{self.massageName}")]
            self.taskId = 0
        else:
            self.runTaskList(r)
        curState = dict()
        curState["state"] = self.action_status
        curState["taskId"] = self.taskId
        self.state["weightGood"] = curState

    def locDetectMid(self, r: SimModule):
        if self.action_status == MoveStatus.NONE:
            self.action_status = MoveStatus.RUNNING
            self.taskList = [locDetectMid(self.locName, self.recFile)]
            self.taskId = 0
        else:
            self.runTaskList(r)
        curState = dict()
        curState["state"] = self.action_status
        curState["taskId"] = self.taskId
        self.state["locDetectMid"] = curState

    def locDetectBackLaser(self, r: SimModule):

        if self.action_status == MoveStatus.NONE:
            self.action_status = MoveStatus.RUNNING
            dispatcherArgs = {}
            moveTask = r.moveTask()
            for p in moveTask["params"]:
                if p["key"] == "dispatcherArgs":
                    ss = p["string_value"]
                    dispatcherArgs = json.loads(ss)
            if "targetLoc" in dispatcherArgs:
                if dispatcherArgs["targetLoc"] != "":
                    self.locName = dispatcherArgs["targetLoc"]
            self.target = r.getLM(self.locName, True)
            self.adjust_angle = self.target[2] - r.loc()['angle']
            if self.target[3] != -1:
                self.taskList = [
                    dirAdjust(r, self.adjust_angle),
                    lift(self.lift_motor, self.endHeight),
                    locDetectBackLaser(self.locName)
                ]
            else:
                r.setError(f"{self.locName} does not exist")
                self.status = MoveStatus.FAILED
            self.taskId = 0
        else:
            self.runTaskList(r)
        curState = dict()
        curState["state"] = self.action_status
        curState["adjustAngle"] = self.adjust_angle
        curState["target"] = self.target
        curState["taskId"] = self.taskId
        self.state["locDetectBackLaser"] = curState

    def runTaskList(self, r: SimModule):
        if self.taskId < len(self.taskList):
            if self.taskList[self.taskId].status == MoveStatus.NONE:
                self.taskList[self.taskId].reset(r)
            elif self.taskList[self.taskId].status == MoveStatus.FINISHED:
                self.taskId = self.taskId + 1
            elif self.taskList[self.taskId].status == MoveStatus.FAILED:
                self.action_status = MoveStatus.FAILED
            else:
                self.taskList[self.taskId].run(r, self)
        else:
            self.action_status = MoveStatus.FINISHED

    def forkCollision(self, r: SimModule, leftDist: float) -> tuple:
        """
        货叉尖端距离传感器的碰撞检测
        :param r: rbk
        :param leftDist: 剩余距离
        :return: bool, obsDist
        """
        sensor = r.getDistanceSensor()
        obsDist = -1.0
        if "node" not in sensor:
            r.setNotice("distanceSensor empty")
            return False, obsDist
        nodeSs = ""
        for data in sensor["node"]:
            if data.get('id', -1) in self.distanceNodeId \
                    and data.get('valid', False) == True \
                    and data.get('forbidden', True) == False \
                    and 'dist' in data:
                if obsDist < 0:
                    obsDist = data['dist']
                else:
                    obsDist = min(obsDist, data['dist'])
            nodeSs = "{}|{}|{}|{}|{}".format(data.get('id', -1), data.get('valid', False), data.get('forbidden', True),
                                             data.get('dist', -1), obsDist)
            r.logDebug("[distanceNode][{}]".format(nodeSs))

        if obsDist < 0:
            return False, obsDist
        if leftDist < obsDist:
            return False, obsDist
        elif self.obsStopDist < obsDist:
            return False, obsDist
        return True, obsDist

    def backLaserCheck(self, r: SimModule) -> bool:
        """
        :param r:
        :return: 是否碰撞
        """
        if r.laserCollision(self.backLaser):
            return True
        return False

    def safeCheck(self, r: SimModule):
        tor = 0.1
        if (self.stretchPos + tor > 1.8) or (self.stretchPos - tor < 0.28):
            self.status = MoveStatus.FINISHED
            self.action_status = MoveStatus.FINISHED
        else:
            self.status = MoveStatus.FAILED
            self.action_status = MoveStatus.FAILED
            r.setError(
                "The stretchPosition position {} is not safe".format(self.stretchPos))
        curState = dict()
        curState["state"] = self.status
        self.state["safeCheck"] = curState

    def move(self, r, moveArgs) -> bool:
        if self.goPath.status != 3 or self.goPath.status != 4:
            self.goPath.run(r, moveArgs)
        if self.goPath.status == MoveStatus.FINISHED:
            self.goPath.reset()
            return True
        return False

    def seqGenerate(self):
        # 获取当前时间
        currentTime = datetime.now()

        # 提取年、月、日、小时、分钟、秒、毫秒
        year = currentTime.year
        month = currentTime.month
        day = currentTime.day
        hour = currentTime.hour
        minute = currentTime.minute
        second = currentTime.second
        millisecond = currentTime.microsecond // 1000  # 将微秒转换为毫秒

        # 将时间信息合并成一个字符串
        # 格式为：年月日时分秒毫秒
        currentTimeSeq = int(f"{year:04d}{month:02d}{day:02d}{hour:02d}{minute:02d}{second:02d}{millisecond:03d}")
        return currentTimeSeq

    def reset(self, r: SimModule):
        self.status = MoveStatus.RUNNING
        self.startTime = time.time()
        self.init = True
        self.state = dict()
        self.taskId = 0
        self.action_status = MoveStatus.NONE

    def cancel(self, r: SimModule):
        r.stopRobot(True)
        r.logInfo("script cancel")
        self.status = MoveStatus.NONE

    def suspend(self, r: SimModule):
        r.stopRobot(True)
        r.logInfo("script suspended")
        self.status = MoveStatus.SUSPENDED
        self.startConnectTime = time.time()


class BaseAction:
    """定义动作的基类"""

    def __init__(self, action_name: str = None):
        self.action_name = action_name or self.__class__.__name__
        self.start_time = time.time()
        self.action_status = ActionStatus.INIT
        self.action_state = {}

    def run(self, m):
        self.action_state["action_runtime"] = time.time() - self.start_time
        pass

    def reset(self):
        pass

    def __str__(self):
        return json.dumps({
            "class_name": self.__class__.__name__
        })


class lift(BaseAction):
    def __init__(self, motorName: str, dist: float, reachDi=-1):
        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"
        self.status = MoveStatus.NONE
        self.init = True
        self.motor = motorName
        self.dist = dist
        self.detectTimes = 0
        self.weightData = []
        self.weightResult = 0
        self.initPos = 0
        self.weightGoodFlag = True
        self.taskContinue = True
        self.resetInit = True
        self.reachDi = reachDi

    def run(self, r: SimModule, agv: Module):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.initPos = agv.liftPos
            r.clearNotice(57300)
            r.clearError(53901)
            if self.dist < agv.lift_zero:
                r.setWarning(f"升降电机目标位置: {self.dist}, 低于最小高度: {agv.lift_zero}")
                self.dist = agv.lift_zero
            elif self.dist > agv.lift_max_height:
                r.setWarning(f"升降电机目标位置: {self.dist}, 高于最大高度: {agv.lift_max_height}")
                self.dist = agv.lift_max_height
            self.init = False
        collision = False
        if self.weightGood(r, agv) and agv.weightGoodOn and self.dist > self.initPos:
            # if ModuleTool.check_DI(r, 15):
            self.taskContinue = False
        if self.taskContinue:
            if self.dist < self.initPos:
                # 货叉下降需要检查一下，货叉下降是否安全
                if agv.backLaserCheck(r):
                    collision = True
                    r.stopRobot(True)
                    r.setWarning(f"后置激光检测到碰撞")
                elif ModuleTool.check_DI(r, agv.fork_tail_di1) or ModuleTool.check_DI(r, agv.fork_tail_di2):
                    collision = True
                    r.stopRobot(True)
                    r.setWarning(f"叉尖DI检测到碰撞，"
                                 f"DI {agv.fork_tail_di1}:{ModuleTool.check_DI(r, agv.fork_tail_di1)},"
                                 f"DI {agv.fork_tail_di2}:{ModuleTool.check_DI(r, agv.fork_tail_di2)}")
                else:
                    r.setMotorPosition(self.motor, self.dist, agv.lift_vel, -1)
            else:
                r.setMotorPosition(self.motor, self.dist, agv.lift_vel, -1)
            if (collision == False and (
                    r.isMotorReached(self.motor) or r.isMotorPositionReached(self.motor, self.dist, -1)
                    or (abs(agv.liftPos - self.dist) <= agv.lift_precision))):
                self.status = MoveStatus.FINISHED
                r.resetMotor(self.motor)
        else:
            if self.resetInit:
                r.resetMotor(self.motor)
                self.resetInit = False
            else:
                r.setMotorPosition(self.motor, self.initPos, agv.lift_vel, -1)
                if (r.isMotorReached(self.motor) or r.isMotorPositionReached(self.motor, self.dist, -1)
                        or (abs(agv.liftPos - self.dist) <= agv.lift_precision)):
                    self.status = MoveStatus.FAILED
                    r.setError(f"weight of good is {self.weightResult} kg, Heavier than {agv.maxWeight} kg")
                    r.resetMotor(self.motor)
        curState = dict()
        curState['liftState'] = self.status
        curState['dist'] = self.dist
        curState['initPos'] = self.initPos
        curState["weightData"] = self.weightData
        curState["weightResult"] = self.weightResult
        curState["maxWeight"] = agv.maxWeight
        agv.state['liftOrg'] = curState

    def reset(self, r):
        r.resetMotor(self.motor)
        self.status = MoveStatus.RUNNING

    def weightGood(self, r, agv):
        fork = r.getMsg("rbk.protocol.Message_Fork")
        weightTmp = fork["pressure_actual"]
        if self.weightGoodFlag:
            if self.detectTimes < agv.maxWeightDetectTimes:
                # 延时处理
                if ModuleTool.delay(agv.detectPeriodTime):
                    self.detectTimes = self.detectTimes + 1
                    self.weightData.append(weightTmp)
            elif self.detectTimes >= agv.maxWeightDetectTimes:
                self.weightResult = sum(self.weightData) / len(self.weightData)
                if self.weightResult >= agv.maxWeight:
                    return True
                else:
                    self.detectTimes = 0
                    self.weightData = []
                    r.setNotice(f"weight of good is {self.weightResult} kg, lighter than {agv.maxWeight} kg")
                    return False
        if ModuleTool.delay(0.1):
            self.weightGoodFlag = not self.weightGoodFlag
        return False


class expand(BaseAction):
    def __init__(self, motorName1: str, dist1: float, motorName2=None, dist2=None):
        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"
        self.status = MoveStatus.NONE
        self.init = True
        self.motor1 = motorName1
        self.motor2 = motorName2
        self.dist1 = dist1
        self.dist2 = dist2
        self.initPos1 = 0
        self.initPos2 = 0
        self.org_start_time = 0.0
        self.org_time_out = 120
        self.resetInit = True
        self.motor1_reach = False
        self.motor2_reach = False

    def run(self, r: SimModule, agv: Module):
        self.status = MoveStatus.RUNNING
        if self.init:
            r.clearError(53000)
            if agv.is_expand_motor1 and self.motor1:
                self.initPos1 = agv.expand_pos1
                # 参数检查
                if not self.dist1:
                    r.setError(f"电机1目标位置缺失")
                    self.status = MoveStatus.FAILED
                if self.dist1 < agv.expand_motor1_zero_position or self.dist1 > agv.expand_motor1_max_position:
                    r.setError(f"开合电机1目标位置: {self.dist1} 超过极限位置, "
                               f"零位 {agv.expand_motor1_zero_position}、最大极限 {agv.expand_motor1_max_position}")
                    self.status = MoveStatus.FAILED
            if agv.is_expand_motor2 and self.motor2:
                self.initPos2 = agv.expand_pos2
                if not self.dist1:
                    r.setError(f"电机2目标位置缺失")
                    self.status = MoveStatus.FAILED
                if self.dist2 < agv.expand_motor2_zero_position or self.dist2 > agv.expand_motor2_max_position:
                    r.setError(f"开合电机1目标位置: {self.dist2} 超过极限位置, "
                               f"零位 {agv.expand_motor2_zero_position}、最大极限 {agv.expand_motor2_max_position}")
                    self.status = MoveStatus.FAILED
            self.org_start_time = time.time()
            self.init = False
        else:
            if agv.is_expand_motor1 and self.motor1 and self.dist1:
                r.setMotorPosition(self.motor1, self.dist1, agv.expand_vel, -1)
                if r.isMotorReached(self.motor1) or r.isMotorPositionReached(self.motor1, self.dist1, -1):
                    self.motor1_reach = True
                if (self.dist1 < agv.expand_motor1_max_position
                        and ModuleTool.check_DI(r, agv.expand_motor1_zero_limit_di)):
                    r.setError(f"开合电机1负限位DI触发，"
                               f"电机1负极限DI{agv.expand_motor1_zero_limit_di}:"
                               f"{ModuleTool.check_DI(r, agv.expand_motor1_zero_limit_di)}"
                               f"电机1正极限DI{agv.expand_motor1_max_limit_di}:"
                               f"{ModuleTool.check_DI(r, agv.expand_motor1_max_limit_di)}"
                               f"电机2负极限DI{agv.expand_motor2_zero_limit_di}:"
                               f"{ModuleTool.check_DI(r, agv.expand_motor2_zero_limit_di)}"
                               f"电机2正极限DI{agv.expand_motor2_max_limit_di}:"
                               f"{ModuleTool.check_DI(r, agv.expand_motor2_max_limit_di)}")
                    self.status = MoveStatus.FAILED
                if (self.dist1 > agv.expand_motor1_zero_position
                        and ModuleTool.check_DI(r, agv.expand_motor1_max_limit_di)):
                    r.setError(f"开合电机1正限位DI触发，"
                               f"电机1正极限DI{agv.expand_motor1_max_limit_di}:"
                               f"{ModuleTool.check_DI(r, agv.expand_motor1_max_limit_di)}"
                               f"电机1负极限DI{agv.expand_motor1_zero_limit_di}:"
                               f"{ModuleTool.check_DI(r, agv.expand_motor1_zero_limit_di)}"
                               f"电机2负极限DI{agv.expand_motor2_zero_limit_di}:"
                               f"{ModuleTool.check_DI(r, agv.expand_motor2_zero_limit_di)}"
                               f"电机2正极限DI{agv.expand_motor2_max_limit_di}:"
                               f"{ModuleTool.check_DI(r, agv.expand_motor2_max_limit_di)}")
                    self.status = MoveStatus.FAILED
            if agv.is_expand_motor2 and self.motor2 and self.dist2:
                r.setMotorPosition(self.motor2, self.dist2, agv.expand_vel, -1)
                if r.isMotorReached(self.motor2) or r.isMotorPositionReached(self.motor2, self.dist2, -1):
                    self.motor2_reach = True
                if (self.dist2 < agv.expand_motor2_max_position
                        and ModuleTool.check_DI(r, agv.expand_motor2_zero_limit_di)):
                    r.setError(f"开合电机2负限位DI触发，"
                               f"电机2负极限DI{agv.expand_motor2_zero_limit_di}:"
                               f"{ModuleTool.check_DI(r, agv.expand_motor2_zero_limit_di)}"
                               f"电机2正极限DI{agv.expand_motor2_max_limit_di}:"
                               f"{ModuleTool.check_DI(r, agv.expand_motor2_max_limit_di)}"
                               f"电机1负极限DI{agv.expand_motor1_zero_limit_di}:"
                               f"{ModuleTool.check_DI(r, agv.expand_motor1_zero_limit_di)}"
                               f"电机1正极限DI{agv.expand_motor1_max_limit_di}:"
                               f"{ModuleTool.check_DI(r, agv.expand_motor1_max_limit_di)}")
                    self.status = MoveStatus.FAILED
                if (self.dist2 > agv.expand_motor2_zero_position
                        and ModuleTool.check_DI(r, agv.expand_motor2_max_limit_di)):
                    r.setError(f"开合电机2正限位DI触发，"
                               f"电机2正极限DI{agv.expand_motor2_max_limit_di}:"
                               f"{ModuleTool.check_DI(r, agv.expand_motor1_max_limit_di)}"
                               f"电机2负极限DI{agv.expand_motor2_zero_limit_di}:"
                               f"{ModuleTool.check_DI(r, agv.expand_motor1_zero_limit_di)}"
                               f"电机1负极限DI{agv.expand_motor1_zero_limit_di}:"
                               f"{ModuleTool.check_DI(r, agv.expand_motor1_zero_limit_di)}"
                               f"电机1正极限DI{agv.expand_motor1_max_limit_di}:"
                               f"{ModuleTool.check_DI(r, agv.expand_motor1_max_limit_di)}")
                    self.status = MoveStatus.FAILED
            if time.time() - self.org_start_time > self.org_time_out:
                r.setError(f"开合电机动作超过{self.org_time_out}s未完成，"
                           f"电机1位置{agv.expand_pos1}，电机2位置{agv.expand_pos2}")
                self.status = MoveStatus.FAILED
            if self.motor1 and self.motor2 and self.motor1_reach and self.motor2_reach:
                self.status = MoveStatus.FINISHED
                r.resetMotor(self.motor1)
                r.resetMotor(self.motor2)
            elif self.motor1 and not self.motor2 and self.motor1_reach:
                self.status = MoveStatus.FINISHED
                r.resetMotor(self.motor1)
            elif self.motor2 and not self.motor1 and self.motor2_reach:
                self.status = MoveStatus.FINISHED
                r.resetMotor(self.motor2)
        curState = dict()
        curState['expandState'] = self.status
        curState['expand_motor1_target_position'] = self.dist1
        curState['expand_motor2_target_position'] = self.dist2
        curState['expand_motor1_init_pos'] = self.initPos1
        curState['expand_motor2_init_pos'] = self.initPos2
        curState['expand_motor1_cur_pos'] = agv.expand_pos1
        curState['expand_motor2_cur_pos'] = agv.expand_pos2
        curState['motor1_reach'] = self.motor1_reach
        curState['motor2_reach'] = self.motor2_reach
        agv.state['expandOrg'] = curState

    def reset(self, r):
        if self.motor1:
            r.resetMotor(self.motor1)
        if self.motor2:
            r.resetMotor(self.motor2)
        self.status = MoveStatus.RUNNING


class lateral(BaseAction):
    def __init__(self, motorName: str, dist: float, reachDi=-1):
        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"
        self.status = MoveStatus.NONE
        self.init = True
        self.motor = motorName
        self.dist = dist
        self.initPos = 0
        self.resetInit = True
        self.reachDi = reachDi

    def run(self, r: SimModule, agv: Module):
        self.status = MoveStatus.RUNNING
        if self.init:
            r.clearNotice(57300)
            r.clearError(53901)
            self.init = False
        r.setMotorPosition(self.motor, self.dist, agv.lateral_vel, -1)
        if (r.isMotorReached(self.motor) or r.isMotorPositionReached(self.motor, self.dist, self.reachDi)
                or (abs(agv.lateral_pos - self.dist) <= agv.lateral_precision)):
            self.status = MoveStatus.FINISHED
            r.resetMotor(self.motor)

        # curState = dict()
        # curState['lateralState'] = self.status
        # curState['dist'] = self.dist
        # agv.state['lateralOrg'] = curState

    def reset(self, r):
        r.resetMotor(self.motor)
        self.status = MoveStatus.RUNNING


class unloadHeightDetect(BaseAction):
    def __init__(self, motorName, dist, laserId: int):
        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"
        self.status = MoveStatus.NONE
        self.init = True
        self.motor = motorName
        self.dist = dist
        self.detectTimes = 0
        self.weightData = []
        self.weightResult = 0
        self.initPos = 0
        self.weightGoodFlag = True
        self.taskContinue = True
        self.resetInit = True
        self.laserId = laserId
        self.laserData = None

    def run(self, r: SimModule, agv: Module):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.initPos = agv.liftPos
            r.clearNotice(57300)
            r.clearError(53901)
            self.init = False
        collision = False
        self.laserCheck(r, agv)
        if self.weightGood(r, agv) and agv.weightGoodOn:
            self.taskContinue = False
        # if self.taskContinue:
        #     # r.setMotorPosition(self.motor, self.dist, agv.liftVel, -1)
        #
        #     if r.isMotorReached(self.motor):
        #         self.status = MoveStatus.FAILED
        #         r.resetMotor(self.motor)
        # else:
        #     if self.resetInit:
        #         r.resetMotor(self.motor)
        #         self.resetInit = False
        #     else:
        #         r.setMotorPosition(self.motor, self.initPos, agv.liftVel, -1)
        #         if r.isMotorReached(self.motor):
        #             self.status = MoveStatus.FAILED
        #             r.setError(f"weight of good is {self.weightResult} kg, Heavier than {agv.maxWeight} kg")
        #             r.resetMotor(self.motor)
        curState = dict()
        curState['unloadHeightDetectState'] = self.status
        curState['dist'] = self.dist
        curState['initPos'] = self.initPos
        curState["laserData"] = self.laserData
        agv.state['unloadHeightDetectOrg'] = curState

    def reset(self, r):
        r.resetMotor(self.motor)
        self.status = MoveStatus.RUNNING

    def laserCheck(self, r, agv):
        self.laserData = r.getNearestLaserPoint(self.laserId)

    def weightGood(self, r, agv):
        fork = r.getMsg("rbk.protocol.Message_Fork")
        weightTmp = fork["pressure_actual"]
        if self.weightGoodFlag:
            if self.detectTimes < agv.maxWeightDetectTimes:
                # 延时处理
                if ModuleTool.delay(agv.detectPeriodTime):
                    self.detectTimes = self.detectTimes + 1
                    self.weightData.append(weightTmp)
            elif self.detectTimes >= agv.maxWeightDetectTimes:
                self.weightResult = sum(self.weightData) / len(self.weightData)
                # if self.weightResult >= agv.maxWeight:
                if ModuleTool.check_DI(r, 1):
                    return True
                else:
                    self.detectTimes = 0
                    self.weightData = []
                    r.setNotice(f"weight of good is {self.weightResult} kg, lighter than {agv.maxWeight} kg")
                    return False
        if ModuleTool.delay(0.1):
            self.weightGoodFlag = not self.weightGoodFlag
        return False


class stretch(BaseAction):
    def __init__(self, motorName, speedMoveType: str, stretchLength: float, checkAllDi: bool, reachDi: list):
        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"
        self.status = MoveStatus.NONE
        self.motor = motorName
        self.speedMoveType = speedMoveType
        self.stretchVel = 0
        self.reachDi = reachDi
        self.checkAllDi = checkAllDi
        self.allDiStatus = [False] * len(reachDi)
        self.zeroLimitDiStatus = False
        self.maxLimitDiStatus = False
        self.allDiStatusDict = dict()
        self.stretchLength = stretchLength
        self.init_org_stretch_pos = None
        self.init = True
        self.collision = False

    def run(self, r: SimModule, agv: Module):

        if not self.collision:
            if agv.stretchType == "speed":
                if self.init:
                    self.status = MoveStatus.RUNNING
                    if self.speedMoveType == "max":
                        self.stretchVel = agv.stretchVel
                    if self.speedMoveType == "zero":
                        self.stretchVel = -agv.stretchVel
                    r.resetMotor(self.motor)
                    self.init = False
                if self.status == MoveStatus.RUNNING:
                    if agv.operation == "load":
                        if self.reachDi[0] != -1 and agv.checkDi:
                            if self.forkGoodsReach(r):  # 电机前后移到位
                                self.status = MoveStatus.FINISHED
                                r.resetMotor(self.motor)
                                r.stopRobot(True)
                            else:
                                if self.speedMoveType == "max" and self.maxLimitCheck(r, agv):
                                    if ModuleTool.delay(0.2):
                                        r.setError("stretch motor is reached but goods is not reached")
                                        self.status = MoveStatus.FAILED
                                else:
                                    r.setMotorSpeed(self.motor, self.stretchVel, -1)
                        else:
                            if self.speedMoveType == "max" and self.maxLimitCheck(r, agv):
                                if ModuleTool.delay(0.2):
                                    self.status = MoveStatus.FINISHED
                                    r.resetMotor(self.motor)
                                    r.stopRobot(True)
                            else:
                                r.setMotorSpeed(self.motor, self.stretchVel, -1)
                    else:
                        if ((self.forkGoodsReach(r) and self.reachDi[0] != -1) or (
                                self.speedMoveType == "max" and self.maxLimitCheck(r, agv))
                                or (self.speedMoveType == "zero" and self.zeroLimitCheck(r, agv))):
                            self.status = MoveStatus.FINISHED
                            r.resetMotor(self.motor)
                            r.stopRobot(True)
                        else:
                            r.setMotorSpeed(self.motor, self.stretchVel, -1)
                curState = dict()
                curState['stretchState'] = self.status
                curState['stretchVel'] = self.stretchVel
                curState['reachDI'] = self.reachDi
                agv.state['stretchOrg'] = curState
            elif agv.stretchType == "DO":
                if self.status == MoveStatus.RUNNING:
                    if self.speedMoveType == "max":
                        r.setDO(agv.stretch_out_do, True)
                        r.setDO(agv.stretch_in_do, False)
                    elif self.speedMoveType == "zero":
                        r.setDO(agv.stretch_out_do, False)
                        r.setDO(agv.stretch_in_do, True)
                    if agv.operation == "load":
                        if self.reachDi[0] != -1 and agv.checkDi and self.forkGoodsReach(r):  # 电机前后移到位
                            r.setDO(agv.stretch_out_do, False)
                            r.setDO(agv.stretch_in_do, False)
                            self.status = MoveStatus.FINISHED
                        else:
                            if self.speedMoveType == "max" and self.maxLimitCheck(r, agv):
                                if ModuleTool.delay(0.2):
                                    if self.reachDi[0] != -1 and not self.forkGoodsReach(r):
                                        r.setDO(agv.stretch_out_do, False)
                                        r.setDO(agv.stretch_in_do, False)
                                        r.setError("stretch motor is reached but goods is not reached")
                                        self.status = MoveStatus.FAILED
                    else:
                        if (self.reachDi[0] != -1 and self.forkGoodsReach(r) or (
                                self.speedMoveType == "max" and self.maxLimitCheck(r, agv))
                                or (self.speedMoveType == "zero" and self.zeroLimitCheck(r, agv))):
                            r.setDO(agv.stretch_out_do, False)
                            r.setDO(agv.stretch_in_do, False)
                            self.status = MoveStatus.FINISHED
                curState = dict()
                curState['stretchState'] = self.status
                curState['reachDI'] = self.reachDi
                agv.state['stretchOrg'] = curState
            elif agv.stretchType == "position":
                if self.init:
                    self.status = MoveStatus.RUNNING
                    self.init_org_stretch_pos = agv.stretchPos
                    self.init = False
                leftDist = abs(self.stretchLength - agv.stretchPos)
                collision = False
                obsDist = -1
                if self.stretchLength > self.init_org_stretch_pos:
                    collision, obsDist = agv.forkCollision(r, leftDist)
                if collision:
                    if not r.errorExits(53000):
                        r.setError("fork tail collision error. obs distance is {}".format(obsDist))
                        r.stopRobot(True)
                        # self.status = MoveStatus.FAILED
                    r.resetMotor(self.motor)
                else:
                    if r.errorExits(53000):
                        r.clearError(53000)
                    if leftDist < agv.stretch_slow_down_dist:
                        r.setMotorPosition(self.motor, self.stretchLength, agv.stretch_slow_down_vel, -1)
                    else:
                        r.setMotorPosition(self.motor, self.stretchLength, agv.stretchVel, -1)
                    if (r.isMotorReached(self.motor) or r.isMotorPositionReached(self.motor, self.stretchLength, -1)
                            or (abs(agv.stretchPos - self.stretchLength) <= agv.stretch_precision)):
                        if ModuleTool.delay(0.2):
                            if self.reachDi[0] != -1 and agv.checkDi and not self.forkGoodsReach(r):
                                r.setWarning("stretch motor is reached but goods is not reached")
                                r.stopRobot(True)
                                r.stopMotor()
                                r.resetMotor(self.motor)
                                self.status = MoveStatus.FINISHED
                            else:
                                r.stopRobot(True)
                                r.stopMotor()
                                r.resetMotor(self.motor)
                                self.status = MoveStatus.FINISHED
                    if self.reachDi[0] != -1 and self.forkGoodsReach(r):
                        r.stopRobot(True)
                        r.stopMotor()
                        r.resetMotor(self.motor)
                        self.status = MoveStatus.FINISHED
                # curState = dict()
                # curState['stretchState'] = self.status
                # curState['dist'] = self.stretchLength
                # agv.state['stretchOrg'] = curState
        # 货叉安全检查
        if agv.backLaserCheck(r):
            self.collision = True
            r.stopRobot(True)
            r.setWarning(f"后置激光检测到碰撞")
        elif ModuleTool.check_DI(r, agv.fork_tail_di1) or ModuleTool.check_DI(r, agv.fork_tail_di2):
            self.collision = True
            r.stopRobot(True)
            r.setWarning(f"叉尖DI检测到碰撞，"
                         f"DI {agv.fork_tail_di1}:{ModuleTool.check_DI(r, agv.fork_tail_di1)},"
                         f"DI {agv.fork_tail_di2}:{ModuleTool.check_DI(r, agv.fork_tail_di2)}")
        else:
            self.collision = False
            r.clearWarning(55300)

    def forkGoodsReach(self, r: SimModule) -> bool:
        """
        货叉到位DI检测
        :param r:
        :return: bool
        """
        if len(self.reachDi) < 4:
            # 最多支持4个到位DI，不足时补全
            num2Add = 4 - len(self.reachDi)
            # 使用None补全列表
            self.reachDi.extend([-1] * num2Add)
        DI = r.Di()
        nodes = DI.get('node', list())
        self.allDiStatus = [item["status"] for item in nodes if item["id"] in self.reachDi]
        for node in nodes:
            if node["id"] in self.reachDi:
                self.allDiStatusDict[node["id"]] = node["status"]
        if self.checkAllDi:
            if all(self.allDiStatus):
                return True
        else:
            if any(self.allDiStatus):
                return True
        return False

    def zeroLimitCheck(self, r: SimModule, agv: Module) -> bool:
        """
        货叉到位DI检测
        :param r:
        :param agv:
        :return: bool
        """
        DI = r.Di()
        nodes = DI.get('node', list())
        for node in nodes:
            if node["id"] == agv.stretchZeroDi:
                if node['status']:
                    return True
        return False

    def maxLimitCheck(self, r: SimModule, agv: Module) -> bool:
        """
        货叉到位DI检测
        :param r:
        :param agv:
        :return: bool
        """
        DI = r.Di()
        nodes = DI.get('node', list())
        for node in nodes:
            if node["id"] == agv.stretchMaxDi:
                if node['status']:
                    return True
        return False

    def reset(self, r):
        r.resetMotor(self.motor)
        self.status = MoveStatus.RUNNING


class pitch(BaseAction):
    def __init__(self, pitchMode: str):
        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"
        self.status = MoveStatus.NONE
        self.init = True
        self.motor = ""
        self.motorVel = 0.0
        self.reachDi = -1
        self.pitchMode = pitchMode

    def run(self, r: SimModule, agv: Module):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            self.motor = agv.pitchMotor
            if self.pitchMode == "forward":
                self.motorVel = agv.pitchVel
                self.reachDi = agv.pitchZeroDi
            elif self.pitchMode == "backward":
                self.motorVel = -agv.pitchVel
                self.reachDi = agv.pitchMaxDi
        collision = False
        if self.status == MoveStatus.RUNNING:
            if agv.backLaserCheck(r):
                collision = True
                r.setUserWarning(53901, "fork will be collided，please check")
            if not collision:
                r.clearWarning(53901)
                r.setMotorSpeed(self.motor, self.motorVel, self.reachDi)
                if r.isMotorReached(self.motor):
                    self.status = MoveStatus.FINISHED
                    r.resetMotor(self.motor)
            else:
                r.stopRobot(True)

        curState = dict()
        curState['pitchStatus'] = self.status
        curState['pitchMode'] = self.pitchMode
        curState['motorVel'] = self.motorVel
        curState['motor'] = self.motor
        curState['reachDi'] = self.reachDi
        agv.state['pitchOrg'] = curState

        return self.status

    def reset(self, r):
        r.resetMotor(self.motor)
        self.status = MoveStatus.RUNNING


# class expand:
#     def __init__(self, motor1_name, motor2_name, expand_pos: float, checkAllDi: bool, reachDi: list):
#         kwargs = locals()
#         del kwargs['self']
#         del kwargs['__class__']
#         self.opt_info = f"{__class__.__name__}{kwargs}"
#         self.status = MoveStatus.NONE
#         self.motor1 = motor1_name
#         self.motor2 = motor2_name
#         self.stretchVel = 0
#         self.reachDi = reachDi
#         self.checkAllDi = checkAllDi
#         self.allDiStatus = [False] * len(reachDi)
#         self.zeroLimitDiStatus = False
#         self.maxLimitDiStatus = False
#         self.allDiStatusDict = dict()
#         self.expand_pos = expand_pos
#         self.init = True
#         self.collision = False
#
#     def run(self, r: SimModule, agv: Module):
#
#         if not self.collision:
#             if agv.stretchType == "speed":
#                 if self.init:
#                     self.status = MoveStatus.RUNNING
#                     if self.speedMoveType == "max":
#                         self.stretchVel = agv.stretchVel
#                     if self.speedMoveType == "zero":
#                         self.stretchVel = -agv.stretchVel
#                     r.resetMotor(self.motor1)
#                     self.init = False
#                 if self.status == MoveStatus.RUNNING:
#                     if agv.operation == "load":
#                         if self.reachDi[0] != -1 and agv.checkDi:
#                             if self.forkGoodsReach(r):  # 电机前后移到位
#                                 self.status = MoveStatus.FINISHED
#                                 r.resetMotor(self.motor1)
#                                 r.stopRobot(True)
#                             else:
#                                 if self.speedMoveType == "max" and self.maxLimitCheck(r, agv):
#                                     if ModuleTool.delay(0.2):
#                                         r.setError("stretch motor is reached but goods is not reached")
#                                         self.status = MoveStatus.FAILED
#                                 else:
#                                     r.setMotorSpeed(self.motor1, self.stretchVel, -1)
#                         else:
#                             if self.speedMoveType == "max" and self.maxLimitCheck(r, agv):
#                                 if ModuleTool.delay(0.2):
#                                     self.status = MoveStatus.FINISHED
#                                     r.resetMotor(self.motor1)
#                                     r.stopRobot(True)
#                             else:
#                                 r.setMotorSpeed(self.motor1, self.stretchVel, -1)
#                     else:
#                         if ((self.forkGoodsReach(r) and self.reachDi[0] != -1) or (
#                                 self.speedMoveType == "max" and self.maxLimitCheck(r, agv))
#                                 or (self.speedMoveType == "zero" and self.zeroLimitCheck(r, agv))):
#                             self.status = MoveStatus.FINISHED
#                             r.resetMotor(self.motor1)
#                             r.stopRobot(True)
#                         else:
#                             r.setMotorSpeed(self.motor1, self.stretchVel, -1)
#                 curState = dict()
#                 curState['stretchState'] = self.status
#                 curState['stretchVel'] = self.stretchVel
#                 curState['reachDI'] = self.reachDi
#                 agv.state['stretchOrg'] = curState
#             elif agv.stretchType == "DO":
#                 if self.status == MoveStatus.RUNNING:
#                     if self.speedMoveType == "max":
#                         r.setDO(agv.stretch_out_do, True)
#                         r.setDO(agv.stretch_in_do, False)
#                     elif self.speedMoveType == "zero":
#                         r.setDO(agv.stretch_out_do, False)
#                         r.setDO(agv.stretch_in_do, True)
#                     if agv.operation == "load":
#                         if self.reachDi[0] != -1 and agv.checkDi and self.forkGoodsReach(r):  # 电机前后移到位
#                             r.setDO(agv.stretch_out_do, False)
#                             r.setDO(agv.stretch_in_do, False)
#                             self.status = MoveStatus.FINISHED
#                         else:
#                             if self.speedMoveType == "max" and self.maxLimitCheck(r, agv):
#                                 if ModuleTool.delay(0.2):
#                                     if self.reachDi[0] != -1 and not self.forkGoodsReach(r):
#                                         r.setDO(agv.stretch_out_do, False)
#                                         r.setDO(agv.stretch_in_do, False)
#                                         r.setError("stretch motor is reached but goods is not reached")
#                                         self.status = MoveStatus.FAILED
#                     else:
#                         if (self.reachDi[0] != -1 and self.forkGoodsReach(r) or (
#                                 self.speedMoveType == "max" and self.maxLimitCheck(r, agv))
#                                 or (self.speedMoveType == "zero" and self.zeroLimitCheck(r, agv))):
#                             r.setDO(agv.stretch_out_do, False)
#                             r.setDO(agv.stretch_in_do, False)
#                             self.status = MoveStatus.FINISHED
#                 curState = dict()
#                 curState['stretchState'] = self.status
#                 curState['reachDI'] = self.reachDi
#                 agv.state['stretchOrg'] = curState
#             elif agv.stretchType == "position":
#                 self.status = MoveStatus.RUNNING
#                 leftDist = abs(self.stretchLength - agv.stretchPos)
#                 collision = False
#                 obsDist = -1
#                 if self.stretchLength > agv.initStretchPos:
#                     collision, obsDist = agv.forkCollision(r, leftDist)
#                 if collision:
#                     if not r.errorExits(53000):
#                         r.setError("fork tail collision error. obs distance is {}".format(obsDist))
#                         r.stopRobot(True)
#                         # self.status = MoveStatus.FAILED
#                     r.resetMotor(self.motor1)
#                 else:
#                     if r.errorExits(53000):
#                         r.clearError(53000)
#                     if leftDist < agv.stretch_slow_down_dist:
#                         r.setMotorPosition(self.motor1, self.stretchLength, agv.stretch_slow_down_vel, -1)
#                     else:
#                         r.setMotorPosition(self.motor1, self.stretchLength, agv.stretchVel, -1)
#                     if r.isMotorReached(self.motor1):
#                         if ModuleTool.delay(0.2):
#                             if self.reachDi[0] != -1 and agv.checkDi and not self.forkGoodsReach(r):
#                                 r.setError("stretch motor is reached but goods is not reached")
#                                 r.stopRobot(True)
#                                 r.stopMotor()
#                                 r.resetMotor(self.motor1)
#                                 self.status = MoveStatus.FAILED
#                             else:
#                                 r.stopRobot(True)
#                                 r.stopMotor()
#                                 r.resetMotor(self.motor1)
#                                 self.status = MoveStatus.FINISHED
#                     if self.reachDi[0] != -1 and self.forkGoodsReach(r):
#                         r.stopRobot(True)
#                         r.stopMotor()
#                         r.resetMotor(self.motor1)
#                         self.status = MoveStatus.FINISHED
#                 # curState = dict()
#                 # curState['stretchState'] = self.status
#                 # curState['dist'] = self.stretchLength
#                 # agv.state['stretchOrg'] = curState
#         # 货叉安全检查
#         if agv.backLaserCheck(r):
#             self.collision = True
#             r.stopRobot(True)
#             r.setWarning(f"后置激光检测到碰撞")
#         elif ModuleTool.check_DI(r, agv.fork_tail_di1) or ModuleTool.check_DI(r, agv.fork_tail_di2):
#             self.collision = True
#             r.stopRobot(True)
#             r.setWarning(f"叉尖DI检测到碰撞，"
#                          f"DI {agv.fork_tail_di1}:{ModuleTool.check_DI(r, agv.fork_tail_di1)},"
#                          f"DI {agv.fork_tail_di2}:{ModuleTool.check_DI(r, agv.fork_tail_di2)}")
#         else:
#             self.collision = False
#             r.clearWarning(55300)
#
#     def forkGoodsReach(self, r: SimModule) -> bool:
#         """
#         货叉到位DI检测
#         :param r:
#         :return: bool
#         """
#         if len(self.reachDi) < 4:
#             # 最多支持4个到位DI，不足时补全
#             num2Add = 4 - len(self.reachDi)
#             # 使用None补全列表
#             self.reachDi.extend([-1] * num2Add)
#         DI = r.Di()
#         nodes = DI.get('node', list())
#         self.allDiStatus = [item["status"] for item in nodes if item["id"] in self.reachDi]
#         for node in nodes:
#             if node["id"] in self.reachDi:
#                 self.allDiStatusDict[node["id"]] = node["status"]
#         if self.checkAllDi:
#             if all(self.allDiStatus):
#                 return True
#         else:
#             if any(self.allDiStatus):
#                 return True
#         return False
#
#     def zeroLimitCheck(self, r: SimModule, agv: Module) -> bool:
#         """
#         货叉到位DI检测
#         :param r:
#         :param agv:
#         :return: bool
#         """
#         DI = r.Di()
#         nodes = DI.get('node', list())
#         for node in nodes:
#             if node["id"] == agv.stretchZeroDi:
#                 if node['status']:
#                     return True
#         return False
#
#     def maxLimitCheck(self, r: SimModule, agv: Module) -> bool:
#         """
#         货叉到位DI检测
#         :param r:
#         :param agv:
#         :return: bool
#         """
#         DI = r.Di()
#         nodes = DI.get('node', list())
#         for node in nodes:
#             if node["id"] == agv.stretchMaxDi:
#                 if node['status']:
#                     return True
#         return False
#
#     def reset(self, r):
#         r.resetMotor(self.motor1)
#         self.status = MoveStatus.RUNNING


class rec(BaseAction):
    def __init__(self, filename):
        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"
        self.status = MoveStatus.NONE
        self.filename = filename
        self.recTimes = 0
        self.maxRecTimes = 10
        self.result = dict()

    def run(self, r: SimModule, agv: Module):
        self.status = MoveStatus.RUNNING
        recStatus = r.getRecStatus()
        loc = r.loc()
        r.logDebug("recStatus: {}".format(recStatus))
        if recStatus == 3:
            self.recTimes = self.recTimes + 1
            if self.recTimes > self.maxRecTimes:
                r.setError("rec fail. reach max times {}".format(self.maxRecTimes))
                self.status = MoveStatus.FAILED
            else:
                r.doRecWithAngle(self.filename, 0.0)
        elif recStatus == 0 or recStatus == 1:
            r.doRecWithAngle(self.filename, 0.0)
        elif recStatus == 2:
            self.result = r.getRecResult()
            r.logDebug("recResult:{}".format(self.result))
            self.status = MoveStatus.FINISHED
        curState = dict()
        curState['recResult'] = self.result
        curState['recState'] = self.status
        curState['recStatus'] = recStatus
        curState['file'] = self.filename
        agv.state['recOrg'] = curState
        r.logDebug(json.dumps(agv.state))

        return self.status

    def reset(self, r):
        r.resetRec()
        self.status = MoveStatus.RUNNING


class goMapPathDi(BaseAction):
    def __init__(self, check_di=None):
        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"
        self.init = True
        self.task = dict()
        self.status = MoveStatus.NONE
        self.checkAllDi = False
        self.check_di = check_di
        self.reachDi = []
        self.allDiStatus = []
        self.allDiStatusDict = dict()
        self.backCheckDi = None

    def run(self, r: SimModule, agv: Module):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            self.task = r.moveTask()
            self.checkAllDi = agv.checkAllDi

            if self.check_di is None:
                self.check_di = agv.checkDi
            self.reachDi = agv.multiReachDI
            self.backCheckDi = backCheckDi(r, self.checkAllDi, self.reachDi)
            self.allDiStatus = [False] * len(self.reachDi)
        r.logInfo("goMapPath args {}".format(str(self.task)))
        goMapPathStatus = r.goMapPath(json.dumps(self.task))
        if self.check_di:
            if agv.operation == "load" or agv.operation == "unStack":
                if self.forkGoodsReach(r):
                    r.stopRobot(True)
                    self.status = MoveStatus.FINISHED
                if goMapPathStatus == MoveStatus.FINISHED:
                    if self.reachDi[0] != -1 and not self.forkGoodsReach(r):  # 取货异常
                        self.backCheckDi.run(r, agv)
                        # r.stopRobot(True)
                        # self.status = MoveStatus.FAILED
                        # r.setError("已到达目标点，但未触发到位DI")
                    else:
                        self.status = MoveStatus.FINISHED
                elif goMapPathStatus == MoveStatus.FAILED:
                    self.status = MoveStatus.FAILED
            else:
                self.status = goMapPathStatus
        else:
            self.status = goMapPathStatus
        return self.status

    def reset(self, r: SimModule):
        r.logInfo("reset goMapPath")
        self.status = MoveStatus.RUNNING
        r.resetGoMapPath()

    def forkGoodsReach(self, r: SimModule) -> bool:
        """
        货叉到位DI检测
        :param r:
        :return: bool
        """
        if len(self.reachDi) < 4:
            # 最多支持4个到位DI，不足时补全
            num2Add = 4 - len(self.reachDi)
            # 使用None补全列表
            self.reachDi.extend([-1] * num2Add)
        DI = r.Di()
        nodes = DI.get('node', list())
        self.allDiStatus = [item["status"] for item in nodes if item["id"] in self.reachDi]
        for node in nodes:
            if node["id"] in self.reachDi:
                self.allDiStatusDict[node["id"]] = node["status"]
        if self.checkAllDi:
            if all(self.allDiStatus):
                return True
        else:
            if any(self.allDiStatus):
                return True
        return False


class goStationList(BaseAction):
    def __init__(self, r: SimModule):
        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"
        self.init = True
        self.task = dict()
        self.status = MoveStatus.NONE
        self.state = dict()

    def run(self, r: SimModule, agv: Module):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            if len(agv.stationList) >= 1:
                station = agv.stationList[0]
                stationListNext = agv.stationList[1:]
                # 获取当前文件的完整路径
                currentFilePath = __file__
                # 只获取文件名称
                currentFileName = os.path.basename(currentFilePath)
                self.task = \
                    {
                        "id": station,
                        "operation": "Script",
                        "script_args": {
                            "operation": "goStationList",
                            "stationList": stationListNext,
                        },
                        "script_name": currentFileName,
                    }
        if len(agv.stationList) >= 1:
            r.logInfo("goStation args {}".format(str(self.task)))
            r.addMoveTask(json.dumps(self.task))
        else:
            self.status = MoveStatus.FINISHED
        return self.status

    def reset(self, r: SimModule):
        r.logInfo("reset goStation")
        self.status = MoveStatus.RUNNING


class recPallet(BaseAction):
    def __init__(self, r: SimModule):
        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"
        self.init = True
        self.task = None
        self.status = MoveStatus.NONE
        self.recFailedTime = 0
        self.maxRecTime = 20
        self.recStatus = 0
        self.recLiftPos = 0
        self.getRecResultId = 1
        self.rec_results = []

    def run(self, r: SimModule, agv: Module):
        self.status = MoveStatus.RUNNING
        reportInfo = dict()
        if self.init:
            r.resetRec()
            self.init = False
        if agv.operation == "load" and self.rec(r, agv):
            if agv.loadAll:
                if agv.minus_result_filter:
                    self.rec_results = self.get_all_rec_results(r)
                    agv.recResult = self.filtered_result(self.rec_results)
                else:
                    self.rec_results = self.get_all_rec_results(r)
                    agv.recResult = min(self.rec_results, key=lambda item: item["z"])  # 获取最底层的识别结果
                if agv.is_expand_motor1:
                    self.pocket_width(agv.recResult, agv)
                if agv.adjustHeight:
                    agv.recResult["z"] = agv.recResult["z"] + self.recLiftPos - agv.lift_zero
                    if agv.recResult["z"] < agv.lift_zero:
                        agv.loadLiftHeight = agv.lift_zero
                    elif agv.lift_max_height >= agv.recResult["z"] >= agv.lift_zero:
                        agv.loadLiftHeight = agv.recResult["z"]
                    elif agv.recResult["z"] > agv.lift_max_height:
                        r.setError(f"栈板高度超过货叉最高升降高度")
                        self.status = MoveStatus.FAILED
                    if agv.endHeight is None:
                        agv.loadLiftUpHeight = agv.loadLiftHeight + agv.liftUpHeight
                    else:
                        agv.loadLiftUpHeight = agv.endHeight
                    if agv.loadLiftUpHeight > agv.lift_max_height:
                        agv.loadLiftUpHeight = agv.lift_max_height
                else:
                    agv.loadLiftHeight = agv.startHeight
                    if agv.endHeight is None:
                        agv.loadLiftUpHeight = agv.loadLiftHeight + agv.liftUpHeight
                    else:
                        agv.loadLiftUpHeight = agv.endHeight
                    if agv.loadLiftUpHeight > agv.lift_max_height:
                        agv.loadLiftUpHeight = agv.lift_max_height
                if "palletWidth" in agv.recResult:
                    targetPalletWidth = agv.recResult['palletWidth']
                    dtWidth = abs(targetPalletWidth - agv.recParams.get('pallet_width', None))
                    if dtWidth > 0.3 and agv.palletCheck:
                        r.setError(f"实际栈板宽度{targetPalletWidth}，"
                                   f"与识别文件中pallet_width{agv.recParams.get('pallet_width', None)}不一致，请检查！")
                        self.status = MoveStatus.FAILED
                        return False
                self.status = MoveStatus.FINISHED
            else:
                if agv.palletCheck:
                    # 对数据进行分类
                    classes = self.classifyData(agv.width_data, agv.classifyRang)
                    # 找到数量超过一半的一类数据的中位数
                    halfCount = math.ceil(len(agv.width_data) / 2)
                    # if len(agv.widthData) <= 3:
                    #     halfCount = 1
                    selectedClass = None
                    for key, values in classes.items():
                        if len(values) >= halfCount:
                            selectedClass = values
                            break
                    # 判断数据数量是否超过正常数量，及栈板宽度是否异常
                    if selectedClass is None:
                        # 没有一类栈板的数量超过所有一半，栈板类型过于混乱，或识别结果异常，视为严重异常
                        if len(agv.width_data) > agv.palletNormalCount:
                            reportInfo["palletNum"] = len(agv.width_data)
                            agv.unstack_error_type = 1
                            strState = json.dumps(reportInfo)
                            r.setInfo(strState)
                            r.setError(f"没有一类栈板的数量超过所有一半，"
                                       f"且数量超过正常数量 {agv.palletNormalCount}，实际栈板数量为：{len(agv.width_data)}")
                            self.status = MoveStatus.FAILED
                        else:
                            reportInfo["palletNum"] = len(agv.width_data)
                            agv.unstack_error_type = 2
                            strState = json.dumps(reportInfo)
                            r.setInfo(strState)
                            r.setError(
                                f"没有一类栈板的数量超过所有一半，但数量正常，实际栈板数量为：{len(agv.width_data)}")
                            self.status = MoveStatus.FAILED
                    elif selectedClass is not None:
                        widthMedian = self.calculateMedian(self, selectedClass)
                        # 判断原始数据是否为异常数据
                        agv.errors_pallet = [(i + 1, value) for i, value in enumerate(agv.width_data)
                                             if abs(value - widthMedian) > agv.errorRang]

                        if len(agv.width_data) <= agv.palletNormalCount:
                            if agv.errors_pallet:
                                # 栈板数量正常，但有异常栈板
                                reportInfo["palletNum"] = len(agv.width_data)
                                reportInfo["errorsPallet"] = agv.errors_pallet
                                agv.unstack_error_type = 3
                                strState = json.dumps(reportInfo)
                                r.setInfo(strState)
                                r.setError(f"栈板数量正常 {agv.palletNormalCount}，"
                                           f"实际栈板数量为 {len(agv.width_data)},异常栈板数据:{agv.errors_pallet}")
                                self.status = MoveStatus.FAILED
                            else:
                                # 栈板数量正常，且无异常栈板
                                agv.unstack_error_type = 0
                                if agv.lift_max_height > agv.recResult["z"] > agv.lift_zero:
                                    agv.loadLiftHeight = agv.recResult["z"]
                                elif agv.recResult["z"] > agv.lift_max_height:
                                    r.setError(f"栈板高度超过货叉最高升降高度")
                                    self.status = MoveStatus.FAILED
                                elif agv.recResult["z"] < agv.lift_zero:
                                    agv.loadLiftHeight = agv.lift_zero
                                if agv.endHeight is None:
                                    agv.loadLiftUpHeight = agv.loadLiftHeight + agv.liftUpHeight
                                else:
                                    agv.loadLiftUpHeight = agv.endHeight
                                if agv.loadLiftUpHeight > agv.lift_max_height:
                                    agv.loadLiftUpHeight = agv.lift_max_height
                                self.status = MoveStatus.FINISHED

                        elif len(agv.width_data) > agv.palletNormalCount:
                            if agv.errors_pallet:
                                # 栈板数量超过正常数量
                                reportInfo["palletNum"] = len(agv.width_data)
                                reportInfo["errorsPallet"] = agv.errors_pallet
                                agv.unstack_error_type = 4
                                strState = json.dumps(reportInfo)
                                r.setInfo(strState)
                                r.setError(f"栈板数量超过正常数量 {agv.palletNormalCount}，"
                                           f"实际栈板数量为 {len(agv.width_data)},异常栈板数据:{agv.errors_pallet}")
                                self.status = MoveStatus.FAILED
                            else:
                                # 栈板数量超过正常数量，但宽度没有异常
                                reportInfo["palletNum"] = len(agv.width_data)
                                reportInfo["errorsPallet"] = agv.errors_pallet
                                agv.unstack_error_type = 5
                                strState = json.dumps(reportInfo)
                                r.setInfo(strState)
                                r.setError(f"栈板数量超过正常数量 {agv.palletNormalCount}，"
                                           f"实际栈板数量为 {len(agv.width_data)},没有异常栈板")
                                self.status = MoveStatus.FAILED
                else:
                    agv.unstack_error_type = 0
                    if agv.lift_max_height > agv.recResult["z"] > agv.lift_zero:
                        agv.loadLiftHeight = agv.recResult["z"]
                    elif agv.recResult["z"] > agv.lift_max_height:
                        r.setError(f"栈板高度超过货叉最高升降高度")
                        self.status = MoveStatus.FAILED
                    elif agv.recResult["z"] < agv.lift_zero:
                        agv.loadLiftHeight = agv.lift_zero
                    if agv.endHeight is None:
                        agv.loadLiftUpHeight = agv.loadLiftHeight + agv.liftUpHeight
                    else:
                        agv.loadLiftUpHeight = agv.endHeight
                    if agv.loadLiftUpHeight > agv.lift_max_height:
                        agv.loadLiftUpHeight = agv.lift_max_height
                    self.status = MoveStatus.FINISHED
            if self.status == MoveStatus.FINISHED:
                curState = dict()
                data_raw = r.getGData()
                end_height_data_time = agv.seqGenerate()
                loadLiftHeight = {
                    "loadLiftHeight": agv.loadLiftHeight,
                    "end_height_data_time": end_height_data_time
                }
                r.setGData(loadLiftHeight)
                data_new = r.getGData()
                curState["data_new"] = data_new
                curState["data_raw"] = data_raw
                curState["end_height_data_time"] = end_height_data_time
                agv.state["load_lift_height_data"] = curState
        elif agv.operation == "unload" and self.rec(r, agv):
            agv.recResult = r.getRecResult()  # 获取第一层的识别结果
            agv.recResult["z"] = agv.recResult["z"] + self.recLiftPos - agv.lift_zero
            agv.unloadLiftHeight = agv.recResult["z"] + 0.3
            self.status = MoveStatus.FINISHED
        elif agv.operation == "stack" and self.rec(r, agv):
            agv.recResult = r.getRecResults(1)  # 获取指定层的识别结果
            agv.recResult["z"] = agv.recResult["z"] + self.recLiftPos - agv.lift_zero
            self.status = MoveStatus.FINISHED

        curState = dict()
        recResult_world = []
        curState['recResult'] = agv.recResult
        curState['pallet_pocket_width'] = agv.pallet_pocket_width
        curState['recPalletState'] = self.status
        curState['recPos'] = agv.recPos
        if agv.recResult:
            recResultPos = [agv.recResult['x'], agv.recResult['y'], agv.recResult['yaw']]
            recResult_world = Pos2World(recResultPos, agv.recPos)
            dist = math.sqrt((recResult_world[0] - r.loc()['x']) ** 2 + (recResult_world[1] - r.loc()['y']) ** 2)
            curState['dist'] = dist
        curState['recStatus'] = self.recStatus
        curState['file'] = agv.recFile
        curState['recFailedTime'] = self.recFailedTime
        agv.state['recPalletOrg'] = curState
        r.logDebug(json.dumps(agv.state))

        return self.status

    def filtered_result(self, rec_results):
        filtered_result = [result for result in rec_results if result["z"] > 0.00001]
        if not filtered_result:
            return None
        min_z_item = min(filtered_result, key=lambda item: item["z"])  # 返回高度最小值
        return min_z_item

    def get_all_rec_results(self, r):
        rec_results = []
        while self.getRecResultId <= r.getRecResultSize():
            rec_results.append(r.getRecResults(self.getRecResultId))
            self.getRecResultId += 1
        if rec_results:
            return rec_results

    def rec(self, r, agv: Module):
        self.recStatus = r.getRecStatus()
        if self.recStatus == 3:
            self.recFailedTime = self.recFailedTime + 1
            if self.recFailedTime > self.maxRecTime:
                r.setError("rec fail. reach max times {}".format(self.maxRecTime))
                self.status = MoveStatus.FAILED
                return
            else:
                r.resetRec()
                agv.recPos = [r.loc()["x"], r.loc()["y"], r.loc()["angle"]]
                self.recLiftPos = agv.liftPos
                if agv.target[3] != -1:
                    target2world = [agv.target[0], agv.target[1], agv.target[2]]
                    target2robot = Pos2Base(target2world, agv.recPos)
                    r.doRec(agv.recFile)
                    # r.doRecWithRegion(agv.recFile, target2robot[0], target2robot[1], target2robot[2], 1.5)
                else:
                    r.doRec(agv.recFile)
        elif self.recStatus == 0:
            agv.recPos = [r.loc()["x"], r.loc()["y"], r.loc()["angle"]]
            self.recLiftPos = agv.liftPos
            if agv.target[3] != -1:
                target2world = [agv.target[0], agv.target[1], agv.target[2]]
                target2robot = Pos2Base(target2world, agv.recPos)
                r.doRec(agv.recFile)
                # r.doRecWithRegion(agv.recFile, target2robot[0], target2robot[1], target2robot[2], 1.5)
            else:
                r.doRec(agv.recFile)
            self.status = MoveStatus.RUNNING
        elif self.recStatus == 0 or self.recStatus == 1:
            agv.recPos = [r.loc()["x"], r.loc()["y"], r.loc()["angle"]]
            self.recLiftPos = agv.liftPos
            if agv.target[3] != -1:
                target2world = [agv.target[0], agv.target[1], agv.target[2]]
                target2robot = Pos2Base(target2world, agv.recPos)
                r.doRec(agv.recFile)
                # r.doRecWithRegion(agv.recFile, target2robot[0], target2robot[1], target2robot[2], 1.5)
            else:
                r.doRec(agv.recFile)
            self.status = MoveStatus.RUNNING
        elif self.recStatus == 2:
            if agv.operation == "load" and not agv.loadAll:
                agv.rec_result_pallet_num = r.getRecResultSize()
                if agv.unStackNum is None:
                    r.setError(f"请输入取货数量unStackNum")
                agv.recResult = r.getRecResults(agv.unStackNum)  # 获取指定层的识别结果
                self.pocket_width(agv.recResult, agv)
                agv.recResult["z"] = agv.recResult["z"] + self.recLiftPos - agv.lift_zero
                while agv.get_rec_result_id <= agv.rec_result_pallet_num:
                    recResultTemp = r.getRecResults(agv.get_rec_result_id)
                    agv.width_data.append(recResultTemp['palletWidth'])
                    agv.height_data.append(recResultTemp['z'])
                    agv.get_rec_result_id = agv.get_rec_result_id + 1
                    targetPalletWidth = recResultTemp['palletWidth']
                    dtWidth = abs(targetPalletWidth - agv.recParams.get('pallet_width', None))
                    if dtWidth > 0.3 and agv.palletCheck:
                        r.setError(f"第 {agv.get_rec_result_id} 层栈板实际宽度为{targetPalletWidth}，"
                                   f"与识别文件中pallet_width{agv.recParams.get('pallet_width', None)}不一致，请检查！")
                        self.status = MoveStatus.FAILED
                        return False
            r.logDebug("recResult:{}".format(agv.recResult))
            return True
        if agv.goodsCheckOn:
            if r.warningExits(54906) and r.warningExits(54901):
                r.setUserError(53930, f"栈板货物超限")
                r.clearNotice(57300)
                self.status = MoveStatus.FAILED
                self.goodsError = True
                return False
            elif r.warningExits(54905) and r.warningExits(54901):
                r.setUserError(53931, f"栈板无货物")
                r.clearNotice(57300)
                self.status = MoveStatus.FAILED
                self.goodsError = True
                return False

    def pocket_width(self, rec_result, agv):
        # 从class字段解析出列表数据
        class_data = json.loads(rec_result['class'])

        # 检查是否有两组数据
        if len(class_data) < 2:
            print("错误：class字段中需要至少两组数据")
        else:
            # 提取两组坐标
            coord1 = {'x': class_data[0]['x'], 'y': class_data[0]['y'], 'z': class_data[0]['z']}
            coord2 = {'x': class_data[1]['x'], 'y': class_data[1]['y'], 'z': class_data[1]['z']}

            # 计算距离
            agv.pallet_pocket_width = self.calculate_distance(coord1, coord2)

    def calculate_distance(self, coord1, coord2):
        """计算两个三维坐标点之间的欧几里得距离"""
        dx = coord1['x'] - coord2['x']
        dy = coord1['y'] - coord2['y']
        dz = coord1['z'] - coord2['z']
        return math.sqrt(dx ** 2 + dy ** 2 + dz ** 2)

    @staticmethod
    def calculateMedian(self, calData):
        sortedData = sorted(calData)
        n = len(sortedData)
        if n % 2 == 0:
            # 如果数据个数为偶数，取中间两个数的平均值
            middleLeft = sortedData[n // 2 - 1]
            middleRight = sortedData[n // 2]
            widthMedian = (middleLeft + middleRight) / 2
        else:
            # 如果数据个数为奇数，取中间值
            widthMedian = sortedData[n // 2]
        return widthMedian

    @staticmethod
    def classifyData(classifyData, classifyRang):
        classes = defaultdict(list)
        # 对栈板宽度数据进行分类，宽度差值小于classifyRang 被分为一类
        for value in classifyData:
            classified = False
            for key in classes.keys():
                if abs(value - key) < classifyRang:
                    classes[key].append(value)
                    classified = True
                    break
            if not classified:
                classes[value] = [value]
        return classes

    def reset(self, r: SimModule):
        r.logInfo("reset findErrorPallet")
        self.status = MoveStatus.RUNNING
        r.resetRec()


class GoStraight(BaseAction):
    def __init__(self, r: SimModule, dist: float, mode: int, direction="x"):
        kwargs = locals()
        del kwargs['self']
        del kwargs['r']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"
        self.init = True
        self.task = None
        self.status = MoveStatus.NONE
        self.dist = dist
        self.backMode = mode
        self.goPath = goPath.Module(r, dict())
        self.moveStatus = False
        self.direction = direction
        self.moveArgs = {}

    def run(self, r: SimModule, agv: Module):
        if self.init:
            r.resetPath()
            self.goPath.reset()
            self.init = False
        self.status = MoveStatus.RUNNING
        if self.goPath.status == MoveStatus.NONE:
            self.goPath.status = MoveStatus.RUNNING
            if self.direction == "x":
                self.moveArgs['coordinate'] = 'robot'
                self.moveArgs['y'] = 0
                self.moveArgs['theta'] = 0
                self.moveArgs['reachAngle'] = 0.005
                self.moveArgs['useOdo'] = 0
                self.moveArgs['reachDist'] = 0.003
                self.moveArgs['maxSpeed'] = agv.adjust_speed
                self.moveArgs["backMode"] = self.backMode
                if self.backMode == straightMoveMode.forward:
                    self.moveArgs["x"] = self.dist
                if self.backMode == straightMoveMode.backward:
                    self.moveArgs["x"] = -self.dist
            if self.direction == "y":
                self.moveArgs['coordinate'] = 'robot'
                self.moveArgs['x'] = 0
                self.moveArgs['theta'] = 0
                self.moveArgs['reachAngle'] = 0.005
                self.moveArgs['useOdo'] = 0
                self.moveArgs['reachDist'] = 0.003
                self.moveArgs['maxSpeed'] = agv.adjust_speed
                self.moveArgs["backMode"] = 0
                self.moveArgs['hold_dir'] = (180 / math.pi) * (r.loc()['angle'])
                if self.backMode == straightMoveMode.forward:
                    self.moveArgs["y"] = self.dist
                if self.backMode == straightMoveMode.backward:
                    self.moveArgs["y"] = -self.dist

        elif self.goPath.status == MoveStatus.RUNNING:
            self.goPath.run(r, self.moveArgs)
        elif self.goPath.status == MoveStatus.FINISHED:
            self.goPath.reset()
            self.status = MoveStatus.FINISHED
        elif self.goPath.status == MoveStatus.FAILED:
            self.status = MoveStatus.FAILED

        return self.status

    def reset(self, r: SimModule):
        r.logInfo("reset goStraight")
        self.status = MoveStatus.RUNNING
        self.goPath.reset()


class adjustGo(BaseAction):
    def __init__(self, r: SimModule, omni: bool, coordinate: str, x: float, y: float, angle: float,
                 backDist: float, minAheadDist: float, aheadDist: float, checkAllDi: bool, reachDi: list):
        kwargs = locals()
        del kwargs['self']
        del kwargs['r']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"
        self.init = True
        self.status = MoveStatus.NONE
        self.goForkPathStatus = MoveStatus.NONE
        self.gopath = goPath.Module(r, dict())
        self.moveArgs = dict()
        self.state = dict()
        self.omni = omni
        self.coordinate = coordinate
        self.beizer = True
        self.x = x
        self.y = y
        self.angle = angle
        self.allDiStatusDict = dict()
        self.backDist = backDist
        self.minAheadDist = minAheadDist
        self.aheadDist = aheadDist
        self.pos2world = []
        self.pos2robot = []
        self.robot2worldStart = []
        self.loc = dict
        self.dtDist = 0
        self.dtAngle = 0
        self.adjustDist = 0
        self.forwardStatus = False
        self.goForward = False
        self.goForkPathStart = False
        self.adjustStep = [False] * 2
        self.adjustForStr = 0
        self.checkAllDi = checkAllDi
        self.reachDi = reachDi
        self.check_init = True
        self.target2world = []
        self.fork_holdDir = 0.0

    def run(self, r: SimModule, agv: Module):
        if self.init:
            self.status = MoveStatus.RUNNING
            self.beizer = agv.recBeizer
            self.robot2worldStart = [r.loc()['x'], r.loc()['y'], r.loc()['angle']]  # 小车在世界坐标系的位置
            if self.coordinate == "world":
                self.pos2world = [self.x, self.y, self.angle]
            elif self.coordinate == "robot":
                if agv.camera_on_fork:
                    pos2fork = [self.x, self.y, self.angle]  # 识别结果再货叉坐标系的位置
                    pos2robot = Pos2World(pos2fork, agv.fork2robot)
                    agv.state["pos2robot"] = pos2robot
                    agv.state["pos2fork"] = pos2fork
                    # offset = [agv.fork2robot[1], -agv.fork2robot[0], 0]
                    # pos2fork_offset = Pos2World(offset, pos2fork)
                    # pos2robot_offset_x = pos2robot[0] + agv.fork2robot[1] * math.sin(pos2robot[2] - agv.fork2robot[2])
                    # pos2fork_offset = [pos2fork_offset_x, pos2fork_offset_y, pos2fork[2]]
                    # pos2robot_offset = Pos2World(pos2fork_offset, agv.fork2robot)
                    pos2robot_offset = [pos2robot[0] + (agv.fork2robot[1] * math.sin(pos2fork[2])),
                                        pos2robot[1] - (agv.fork2robot[1] * math.cos(pos2fork[2])),
                                        pos2robot[2]]  # 识别结果相对里程中心位置 + 叉尖偏移量
                    agv.state["pos2robot_offset"] = pos2robot_offset
                    self.pos2world = Pos2World(pos2robot_offset, self.robot2worldStart)  # 偏移后识别结果在世界坐标系下的位置
                else:
                    pos2robot = [self.x, self.y, self.angle]  # 目标点相对里程中心的位置
                    self.pos2world = Pos2World(pos2robot, self.robot2worldStart)  # 目标点在世界坐标系的位置
            r.logInfo(f"robot2worldStart{self.robot2worldStart}")
            if self.minAheadDist > 0:
                self.goForward = self.adjustCheck(r, agv)
            self.gopath.reset()
            # r.resetPath()
            self.init = False
        if self.goForward:
            if not self.adjustStep[0]:
                if self.gopath.status == MoveStatus.NONE:
                    self.gopath.status = MoveStatus.RUNNING
                    if (agv.beizerDist - self.adjustDist) > agv.adjustForStr:
                        r.setError(
                            f"调整距离不足，所需调整距离为{agv.beizerDist - self.adjustDist}m, 请在安全的情况下修改 adjustForStr")
                    else:
                        self.adjustForStr = agv.beizerDist - self.adjustDist
                    self.moveArgs['coordinate'] = 'robot'
                    self.moveArgs["x"] = self.adjustForStr
                    self.moveArgs['y'] = 0
                    self.moveArgs['theta'] = 0
                    self.moveArgs['reachAngle'] = math.pi
                    self.moveArgs['useOdo'] = 0
                    self.moveArgs['reachDist'] = 0.003
                    self.moveArgs['maxSpeed'] = 0.3
                    self.moveArgs["backMode"] = 0
                    if self.moveArgs["x"] < 0:
                        self.moveArgs["backMode"] = 1
                elif self.gopath.status == MoveStatus.RUNNING:
                    self.gopath.run(r, self.moveArgs)
                elif self.gopath.status == MoveStatus.FINISHED:
                    self.gopath.reset()
                    self.adjustStep[0] = True
                elif self.gopath.status == MoveStatus.FAILED:
                    self.status = MoveStatus.FAILED
            elif self.adjustStep[0] and not self.adjustStep[1]:
                self.robot2worldStart = [r.loc()['x'], r.loc()['y'], r.loc()['angle']]  # 小车在世界坐标系的位置
                if self.coordinate == "robot":
                    pos2robot = [self.x - self.adjustForStr, self.y, self.angle]  # 目标点相对小车的位置
                    self.pos2world = Pos2World(pos2robot, self.robot2worldStart)  # 目标点在世界坐标系的位置
                r.resetGoForkPath(self.pos2world[0], self.pos2world[1], self.pos2world[2], self.backDist,
                                  self.minAheadDist, self.aheadDist)
                if self.omni:
                    self.fork_holdDir = math.degrees(self.pos2world[2] - agv.fork2robot[2])
                    # r.setGoForkForkPos(agv.fork2robot[0], agv.fork2robot[1], agv.fork2robot[2], self.fork_holdDir)
                    r.setGoForkForkPos(0, 0, agv.fork2robot[2], self.fork_holdDir)
                if not self.beizer:
                    r.goForkUseStraightLine()
                self.adjustStep[1] = True
                self.goForkPathStart = True
        else:
            if not self.goForkPathStart:
                r.resetGoForkPath(self.pos2world[0], self.pos2world[1], self.pos2world[2], self.backDist,
                                  self.minAheadDist, self.aheadDist)
                r.setPathReachAngle(0.01)
                r.setPathReachDist(0.005)
                if self.omni:
                    self.fork_holdDir = math.degrees(self.pos2world[2] - agv.fork2robot[2])
                    # r.setGoForkForkPos(agv.fork2robot[0], agv.fork2robot[1], agv.fork2robot[2], self.fork_holdDir)
                    r.setGoForkForkPos(0, 0, agv.fork2robot[2], self.fork_holdDir)
                if not self.beizer:
                    r.goForkUseStraightLine()
                self.goForkPathStart = True
                # go_fork_path_args = "{}|{}|{}|{}|{}|{}|{}|{}|{}|{}".format(
                #     self.pos2world[0], self.pos2world[1], self.pos2world[2], self.backDist, self.minAheadDist,
                #     self.aheadDist, 0, 0, agv.fork2robot[2], self.fork_holdDir)
                # r.logDebug("[goForkPathArgs][{}]".format(go_fork_path_args))
        if self.goForkPathStart:
            self.goForkPathStatus = r.goForkPath()
            if self.goForkPathStatus == MoveStatus.FINISHED and not self.reachCheck(r, agv):
                self.status = MoveStatus.FAILED
                r.setError(f"任务结束，但未在到点范围内（{agv.reachDist}、{agv.reachAngle}）! "
                           f"当前与目标点距离为{self.dtDist}，角度差{self.dtAngle}")
            else:
                self.status = self.goForkPathStatus
            if agv.checkDi and self.reachDi[0] != -1 and self.forkGoodsReach(r):
                r.stopRobot(True)
                self.status = MoveStatus.FINISHED

        curState = dict()
        curState['adjustStep'] = self.adjustStep
        curState['forkGoodsReach'] = self.forkGoodsReach(r)
        curState['allDiStatus'] = self.allDiStatus
        agv.state['adjustGo'] = curState
        r.logDebug(json.dumps(agv.state))
        return self.status

    def reachCheck(self, r: SimModule, agv) -> bool:
        if self.check_init:
            self.check_init = False
            self.pos2robot = Pos2Base(self.pos2world, self.robot2worldStart)  # 初始目标点在小车坐标系的位置
            if agv.camera_on_fork:
                pos2fork = [self.x, self.y, self.angle]  # 识别结果再货叉坐标系的位置
                pos2robot = Pos2World(pos2fork, agv.fork2robot)
                # offset = [agv.fork2robot[1], -agv.fork2robot[0], 0]
                # pos2fork_offset = Pos2World(offset, pos2fork)
                # pos2robot_offset_x = pos2robot[0] + agv.fork2robot[1] * math.sin(pos2robot[2] - agv.fork2robot[2])
                # pos2fork_offset = [pos2fork_offset_x, pos2fork_offset_y, pos2fork[2]]
                # pos2robot_offset = Pos2World(pos2fork_offset, agv.fork2robot)
                pos2robot_offset = [pos2robot[0] + (agv.fork2robot[1] * math.sin(pos2robot[2] - agv.fork2robot[2])),
                                    pos2robot[1] - (agv.fork2robot[1] * math.cos(pos2robot[2] - agv.fork2robot[2])),
                                    pos2robot[2]]  # 识别结果相对里程中心位置 + 叉尖偏移量
                pos2world = Pos2World(pos2robot_offset, self.robot2worldStart)  # 偏移后识别结果在世界坐标系下的位置
                self.pos2robot = Pos2Base(pos2world, self.robot2worldStart)  # 目标点相对里程中心位置

            pos2robotNewNewX = self.pos2robot[0] - self.backDist * math.cos(self.pos2robot[2])
            pos2robotNewNewY = self.pos2robot[1] - self.backDist * math.sin(self.pos2robot[2])
            pos2robotNew = [pos2robotNewNewX, pos2robotNewNewY, self.pos2robot[2]]
            self.target2world = Pos2World(pos2robotNew, self.robot2worldStart)  # 增加backDist后的目标点在世界坐标系的位置
        self.dtDist = math.sqrt((self.target2world[0] - r.loc()['x']) ** 2 + (self.target2world[1] - r.loc()['y']) ** 2)
        if agv.fork_offset_theta == 0:
            self.dtAngle = math.degrees(abs(r.loc()['angle'] - self.target2world[2]))
        else:
            self.dtAngle = math.degrees(abs(r.loc()['angle'] - (self.target2world[2] - agv.fork2robot[2])))
        if self.dtAngle > 180:
            self.dtAngle = 360 - self.dtAngle
        # r.logInfo(f"dtDist{self.dtDist},dtAngle{self.dtAngle}")
        if self.dtDist < agv.reachDist and self.dtAngle < agv.reachAngle:
            return True
        return False

    def forkGoodsReach(self, r: SimModule) -> bool:
        """
        货叉到位DI检测
        :param r:
        :return: bool
        """
        DI = r.Di()
        if len(self.reachDi) < 4:
            # 最多支持4个到位DI，不足时补全
            num2Add = 4 - len(self.reachDi)
            # 使用None补全列表
            self.reachDi.extend([-1] * num2Add)
        nodes = DI.get('node', list())
        self.allDiStatus = [item["status"] for item in nodes if item["id"] in self.reachDi]
        for node in nodes:
            if node["id"] in self.reachDi:
                self.allDiStatusDict[node["id"]] = node["status"]
        if self.checkAllDi:
            if all(self.allDiStatus):
                return True
        else:
            if any(self.allDiStatus):
                return True
        return False

    def adjustCheck(self, r: SimModule, agv) -> bool:
        if self.omni:
            return False
        else:
            self.robot2worldStart = [r.loc()['x'], r.loc()['y'], r.loc()['angle']]  # 小车在世界坐标系的位置
            pos2robot = Pos2Base(self.pos2world, self.robot2worldStart)  # 初始目标点在小车坐标系的位置
            pos2robotNewX = pos2robot[0] + self.minAheadDist * math.cos(pos2robot[2])
            pos2robotNewY = pos2robot[1] + self.minAheadDist * math.sin(pos2robot[2])
            pos2robotNew = [pos2robotNewX, pos2robotNewY, pos2robot[2]]

            target2world = Pos2World(pos2robotNew, self.robot2worldStart)  # 增加minAheadDist后的目标点在小车坐标系的位置
            self.adjustDist = math.sqrt((target2world[0] - r.loc()['x']) ** 2 + (target2world[1] - r.loc()['y']) ** 2)
            # r.logInfo(f"dtDist{self.dtDist},dtAngle{self.dtAngle}")
            if self.adjustDist < agv.beizerDist:
                return True
        return False

    def reset(self, r: SimModule):
        r.logInfo("reset adjustGo")
        r.resetPath()
        self.status = MoveStatus.RUNNING
        self.gopath.reset()


class backCheckDi(BaseAction):
    def __init__(self, r: SimModule, checkAllDi: bool, reachDi: list):
        kwargs = locals()
        del kwargs['self']
        del kwargs['r']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"
        self.init = True
        self.task = None
        self.status = MoveStatus.NONE
        self.goForwardDist = 0
        self.gopath = goPath.Module(r, dict())
        self.moveArgs = dict()
        self.reachDi = reachDi
        self.checkAllDi = checkAllDi
        self.allDiStatus = [False] * len(reachDi)
        self.allDiStatusDict = dict()

    def run(self, r: SimModule, agv: Module):
        if self.gopath.status == MoveStatus.NONE:
            if r.warningExits(55300):
                r.clearWarning(55300)
            self.gopath.status = MoveStatus.RUNNING
            self.moveArgs['coordinate'] = 'robot'
            self.moveArgs["x"] = -agv.reachDist
            self.moveArgs['y'] = 0
            self.moveArgs['theta'] = 0
            self.moveArgs['reachAngle'] = math.pi
            self.moveArgs['useOdo'] = 0
            self.moveArgs['reachDist'] = 0.003
            self.moveArgs['maxSpeed'] = agv.back_slow_down_vel
            self.moveArgs["backMode"] = 0
            if self.moveArgs["x"] < 0:
                self.moveArgs["backMode"] = 1

        if self.gopath.status == MoveStatus.RUNNING:
            self.gopath.run(r, self.moveArgs)
        if self.reachDi[0] != -1 and self.forkGoodsReach(r):
            r.stopRobot(True)
            self.status = MoveStatus.FINISHED
        elif self.gopath.status == MoveStatus.FINISHED:
            if self.reachDi[0] != -1 and not self.forkGoodsReach(r):  # 前移取货异常
                r.stopRobot(True)
                self.status = MoveStatus.FAILED
                # r.setError("已到达目标点且货叉前移已到极限，但未触发货物到位DI")
                if agv.isStretchMotor:
                    r.setError("已到达目标点且货叉前移已到极限，但未触发货物到位DI")
                else:
                    r.setError("已到达目标点，但未触发货物到位DI")
            else:
                self.status = MoveStatus.FINISHED
        elif self.gopath.status == MoveStatus.FAILED:
            self.status = MoveStatus.FAILED
        return self.status

    def forkGoodsReach(self, r: SimModule) -> bool:
        """
        货叉到位DI检测
        :param r:
        :return: bool
        """
        DI = r.Di()
        if len(self.reachDi) < 4:
            # 最多支持4个到位DI，不足时补全
            num2Add = 4 - len(self.reachDi)
            # 使用None补全列表
            self.reachDi.extend([-1] * num2Add)
        nodes = DI.get('node', list())
        self.allDiStatus = [item["status"] for item in nodes if item["id"] in self.reachDi]
        if self.checkAllDi:
            if all(self.allDiStatus):
                return True
        else:
            if any(self.allDiStatus):
                return True
        return False

    def reset(self, r: SimModule):
        r.logInfo("reset goForward")
        self.status = MoveStatus.RUNNING
        self.gopath.reset()


class dirAdjust(BaseAction):
    def __init__(self, r: SimModule, angle):
        kwargs = locals()
        del kwargs['self']
        del kwargs['r']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"

        self.init = True
        self.task = None
        self.status = MoveStatus.NONE
        self.goForwardDist = 0
        self.gopath = goPath.Module(r, dict())
        self.angle = angle
        self.moveArgs = dict()

    def run(self, r: SimModule, agv: Module):
        if self.init:
            self.moveArgs['coordinate'] = 'robot'
            self.moveArgs['x'] = 0
            self.moveArgs['y'] = 0
            self.moveArgs['theta'] = self.angle
            self.moveArgs['reachAngle'] = math.radians(0.1)
            self.moveArgs['useOdo'] = 0
            self.moveArgs['reachDist'] = 0.003
            self.moveArgs['maxSpeed'] = 0.3
            self.moveArgs["backMode"] = 0
        self.status = MoveStatus.RUNNING
        if self.move(r, self.moveArgs):
            self.status = MoveStatus.FINISHED
        return self.status

    def move(self, r, moveArgs) -> bool:
        if self.gopath.status != 3 or self.gopath.status != 4:
            self.gopath.run(r, moveArgs)
        if self.gopath.status == MoveStatus.FINISHED:
            self.gopath.reset()
            return True
        return False

    def reset(self, r: SimModule):
        r.logInfo("reset dirAdjust")
        self.status = MoveStatus.RUNNING
        self.gopath.reset()


class GoMapWithFork(BaseAction):
    def __init__(self, liftPos: float, stretchMoveType: str, stretchPos=-1, mode=-1):
        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"
        self.init = True
        self.task = None
        self.status = MoveStatus.NONE
        self.liftMotor = ""
        self.liftPos = liftPos
        self.stretchPos = stretchPos
        self.stretchMotor = ""
        self.stretchMoveType = stretchMoveType
        self.liftVel = 0
        self.stretchVel = 0
        self.finishedMode = mode
        self.stretchZeroDi = -1
        self.stretchMaxDi = -1
        self.goMapStatus = MoveStatus.NONE

    def run(self, r: SimModule, agv: Module):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            self.stretchMotor = agv.stretch_motor
            if agv.stretchType == "DO":
                self.stretchMotor = "DO_type"
            self.liftMotor = agv.lift_motor
            self.liftVel = agv.lift_vel
            self.stretchVel = agv.stretchVel
            self.task = r.moveTask()
            self.stretchZeroDi = agv.stretchZeroDi
            self.stretchMaxDi = agv.stretchMaxDi
            if agv.stretchType == "position":
                self.stretchVel = agv.stretchVel
            elif agv.stretchType == "speed":
                if self.stretchMoveType == "max":
                    self.stretchVel = agv.stretchVel
                elif self.stretchMoveType == "zero":
                    self.stretchVel = -agv.stretchVel
                else:
                    self.stretchVel = 0
        if "target_x" in self.task and "target_y" in self.task and self.status != MoveStatus.FINISHED:
            r.logInfo("goMapPath task {}".format(str(self.task)))
            self.goMapStatus = r.goMapPath(json.dumps(self.task))
        if self.liftPos >= 0:
            r.setMotorPosition(self.liftMotor, self.liftPos, self.liftVel, -1)

        if agv.isStretchMotor and self.stretchVel != 0:
            if agv.stretchType == "position":
                r.setMotorPosition(self.stretchMotor, self.stretchPos, self.stretchVel, -1)
            elif agv.stretchType == "speed":
                r.setMotorSpeed(self.stretchMotor, self.stretchVel, -1)

        self.finishCheck(r, agv)

        if self.goMapStatus == MoveStatus.FAILED:
            self.status = MoveStatus.FAILED

        if self.status == MoveStatus.FINISHED or self.status == MoveStatus.FAILED:
            r.stopRobot(True)
            r.resetMotor(self.liftMotor)
            r.resetMotor(self.stretchMotor)
            r.resetGoMapPath()
        return self.status

    def finishCheck(self, r, agv):
        if (self.finishedMode == forkMoveMode.movePriority  # 底盘运动优先模式：底盘到点后立即结束
                and self.goMapStatus == MoveStatus.FINISHED):
            self.status = MoveStatus.FINISHED
        elif (self.finishedMode == forkMoveMode.liftPriority  # 货叉升降优先模式，升降完成则结束
              and self.motorReach(r, agv, self.liftMotor, self.liftPos)):
            self.status = MoveStatus.FINISHED
        elif (self.finishedMode == forkMoveMode.stretchPriority  # 货叉前移优先模式，前移完成则结束
              and self.motorReach(r, agv, self.stretchMotor, self.stretchPos)):
            self.status = MoveStatus.FINISHED
        elif (self.finishedMode == forkMoveMode.forkAnyPriority  # 货叉优先模式，前移或升降完成则结束
              and (self.motorReach(r, agv, self.stretchMotor, self.stretchPos)
                   or self.motorReach(r, agv, self.liftMotor, self.liftPos))):
            self.status = MoveStatus.FINISHED
        elif (self.finishedMode == forkMoveMode.forkAllPriority  # 货叉优先模式，前移、升降均完成才结束
              and self.motorReach(r, agv, self.stretchMotor, self.stretchPos)
              and self.motorReach(r, agv, self.liftMotor, self.liftPos)):
            self.status = MoveStatus.FINISHED
        elif (self.finishedMode == forkMoveMode.anyFinished and  # 任意动作完成即结束
              (self.motorReach(r, agv, self.stretchMotor, self.stretchPos)
               or self.motorReach(r, agv, self.liftMotor, self.liftPos)
               or self.goMapStatus == MoveStatus.FINISHED)):
            self.status = MoveStatus.FINISHED
        elif (self.finishedMode == forkMoveMode.allFinished  # 全部完成结束
              and self.motorReach(r, agv, self.stretchMotor, self.stretchPos)
              and self.motorReach(r, agv, self.liftMotor, self.liftPos)
              and self.goMapStatus == MoveStatus.FINISHED):
            self.status = MoveStatus.FINISHED

    def motorReach(self, r, agv, motorName, position):
        if motorName == self.liftMotor:
            if r.isMotorPositionReached(motorName, position, -1):
                return True
        elif motorName == self.stretchMotor:
            if agv.stretchType == "position":
                if not agv.isStretchMotor:
                    return True
                else:
                    if r.isMotorPositionReached(motorName, position, -1):
                        return True
            if agv.stretchType == "speed":
                if self.stretchMoveType == "max" and self.maxLimitCheck(r, agv):
                    return True
                if self.stretchMoveType == "zero" and self.zeroLimitCheck(r, agv):
                    return True
            if agv.stretchType == "DO":
                return True
        else:
            return False

    def zeroLimitCheck(self, r: SimModule, agv: Module) -> bool:
        """
        货叉到位DI检测
        :param r:
        :param agv:
        :return: bool
        """
        DI = r.Di()
        nodes = DI.get('node', list())
        for node in nodes:
            if node["id"] == agv.stretchZeroDi:
                if node['status']:
                    return True
        return False

    def maxLimitCheck(self, r: SimModule, agv: Module) -> bool:
        """
        货叉到位DI检测
        :param r:
        :param agv:
        :return: bool
        """
        DI = r.Di()
        nodes = DI.get('node', list())
        for node in nodes:
            if node["id"] == agv.stretchMaxDi:
                if node['status']:
                    return True
        return False

    def reset(self, r: SimModule):
        r.logInfo("reset GoMapWithFork")
        self.status = MoveStatus.RUNNING
        r.resetMotor(self.liftMotor)
        r.resetMotor(self.stretchMotor)
        r.resetGoMapPath()


# ToDo
class GoPathWithFork(BaseAction):
    def __init__(self, liftPos: float, stretchMoveType: str, stretchPos=-1, mode=-1):
        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"
        self.init = True
        self.status = MoveStatus.NONE
        self.liftMotor = ""
        self.liftPos = liftPos
        self.stretchPos = stretchPos
        self.stretchMotor = ""
        self.stretchMoveType = stretchMoveType
        self.liftVel = 0
        self.stretchVel = 0
        self.finishedMode = mode
        self.stretchZeroDi = -1
        self.stretchMaxDi = -1
        self.goMapStatus = MoveStatus.NONE

    def run(self, r: SimModule, agv: Module):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            self.stretchMotor = agv.stretch_motor
            self.liftMotor = agv.lift_motor
            self.liftVel = agv.lift_vel
            self.stretchVel = agv.stretchVel
            self.stretchZeroDi = agv.stretchZeroDi
            self.stretchMaxDi = agv.stretchMaxDi
            if self.stretchMoveType == "max":
                self.stretchVel = agv.stretchVel
            elif self.stretchMoveType == "zero":
                self.stretchVel = -agv.stretchVel
            else:
                self.stretchVel = 0
        if self.liftPos >= 0:
            r.setMotorPosition(self.liftMotor, self.liftPos, self.liftVel, -1)
        if agv.isStretchMotor and self.stretchVel != 0:
            r.setMotorSpeed(self.stretchMotor, self.stretchVel, -1)

        self.finishCheck(r, agv)

        if self.status == MoveStatus.FINISHED or self.status == MoveStatus.FAILED:
            r.stopRobot(True)
            r.resetMotor(self.liftMotor)
            r.resetMotor(self.stretchMotor)
        return self.status

    def finishCheck(self, r, agv):
        if (self.finishedMode == forkMoveMode.movePriority  # 底盘运动优先模式：底盘到点后立即结束
                and self.goMapStatus == MoveStatus.FINISHED):
            self.status = MoveStatus.FINISHED
        elif (self.finishedMode == forkMoveMode.liftPriority  # 货叉升降优先模式，升降完成则结束
              and self.motorReach(r, agv, self.liftMotor, self.liftPos)):
            self.status = MoveStatus.FINISHED
        elif (self.finishedMode == forkMoveMode.stretchPriority  # 货叉前移优先模式，前移完成则结束
              and self.motorReach(r, agv, self.stretchMotor, self.stretchPos)):
            self.status = MoveStatus.FINISHED
        elif (self.finishedMode == forkMoveMode.forkAnyPriority  # 货叉优先模式，前移或升降完成则结束
              and (self.motorReach(r, agv, self.stretchMotor, self.stretchPos)
                   or self.motorReach(r, agv, self.liftMotor, self.liftPos))):
            self.status = MoveStatus.FINISHED
        elif (self.finishedMode == forkMoveMode.forkAllPriority  # 货叉优先模式，前移、升降均完成才结束
              and self.motorReach(r, agv, self.stretchMotor, self.stretchPos)
              and self.motorReach(r, agv, self.liftMotor, self.liftPos)):
            self.status = MoveStatus.FINISHED
        elif (self.finishedMode == forkMoveMode.anyFinished and  # 任意动作完成即结束
              (self.motorReach(r, agv, self.stretchMotor, self.stretchPos)
               or self.motorReach(r, agv, self.liftMotor, self.liftPos)
               or self.goMapStatus == MoveStatus.FINISHED)):
            self.status = MoveStatus.FINISHED
        elif (self.finishedMode == forkMoveMode.allFinished  # 全部完成结束
              and self.motorReach(r, agv, self.stretchMotor, self.stretchPos)
              and self.motorReach(r, agv, self.liftMotor, self.liftPos)
              and self.goMapStatus == MoveStatus.FINISHED):
            self.status = MoveStatus.FINISHED

    def motorReach(self, r, agv, motorName, position):
        if motorName == self.liftMotor:
            if r.isMotorPositionReached(motorName, position, -1):
                return True
        elif motorName == self.stretchMotor and agv.stretchType == "position":
            if not agv.isStretchMotor:
                return True
            else:
                if r.isMotorPositionReached(motorName, position, -1):
                    return True
        elif motorName == self.stretchMotor and agv.stretchType == "speed":
            if self.stretchMoveType == "max" and self.maxLimitCheck(r, agv):
                return True
            if self.stretchMoveType == "zero" and self.zeroLimitCheck(r, agv):
                return True
        else:
            return False

    def zeroLimitCheck(self, r: SimModule, agv: Module) -> bool:
        """
        货叉到位DI检测
        :param r:
        :param agv:
        :return: bool
        """
        DI = r.Di()
        nodes = DI.get('node', list())
        for node in nodes:
            if node["id"] == agv.stretchZeroDi:
                if node['status']:
                    return True
        return False

    def maxLimitCheck(self, r: SimModule, agv: Module) -> bool:
        """
        货叉到位DI检测
        :param r:
        :param agv:
        :return: bool
        """
        DI = r.Di()
        nodes = DI.get('node', list())
        for node in nodes:
            if node["id"] == agv.stretchMaxDi:
                if node['status']:
                    return True
        return False

    def reset(self, r: SimModule):
        r.logInfo("reset GoMapWithFork")
        self.status = MoveStatus.RUNNING
        r.resetMotor(self.liftMotor)
        r.resetMotor(self.stretchMotor)
        r.resetGoMapPath()


class weightGood(BaseAction):
    def __init__(self):
        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"
        self.init = True
        self.task = None
        self.status = MoveStatus.NONE
        self.state = dict()
        self.detectTimes = 0
        self.weightData = []
        self.weightResult = 0

    def run(self, r: SimModule, agv):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            r.clearNotice(57300)
            r.clearError(53901)

        fork = r.getMsg("rbk.protocol.Message_Fork")
        weightTmp = fork["pressure_actual"]
        if self.detectTimes < agv.maxWeightDetectTimes:
            # 延时处理
            if ModuleTool.delay(agv.detectPeriodTime):
                self.detectTimes = self.detectTimes + 1
                self.weightData.append(weightTmp)
        elif self.detectTimes >= agv.maxWeightDetectTimes:
            self.weightResult = sum(self.weightData) / len(self.weightData)
            if self.weightResult >= agv.maxWeight:
                r.setError(f"weight of good is {self.weightResult} kg, Heavier than {agv.maxWeight} kg")
                self.status = MoveStatus.FAILED
            else:
                r.setNotice(f"weight of good is {self.weightResult} kg, lighter than {agv.maxWeight} kg")
                self.status = MoveStatus.FINISHED

        curState = dict()
        curState["weightData"] = self.weightData
        curState["weightResult"] = self.weightResult
        curState["maxWeight"] = agv.maxWeight
        curState["weightGoodStatus"] = self.status
        agv.state['weightGoodOrg'] = curState

        return self.status

    def reset(self, r: SimModule):
        r.logInfo("reset weightGood")
        self.status = MoveStatus.RUNNING


class getMassage(BaseAction):
    def __init__(self, massageName: str):
        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"
        self.init = True
        self.status = MoveStatus.NONE
        self.state = dict()
        self.massageName = massageName
        self.data = dict()

    def run(self, r: SimModule, agv):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            r.clearNotice(57300)
            r.clearError(53901)

        self.data = r.getMsg(self.massageName)

        curState = dict()
        curState["data"] = self.data
        curState["getMassageStatus"] = self.status
        agv.state['getMassageOrg'] = curState

        return self.status

    def reset(self, r: SimModule):
        r.logInfo("reset getMassage")
        self.status = MoveStatus.RUNNING


class locDetectMid(BaseAction):
    def __init__(self, locName: str, recFile: str):
        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"
        self.init = True
        self.status = MoveStatus.NONE
        self.state = dict()
        self.locName = locName
        self.recFile = recFile
        self.target = (0, 0, 0, -1)
        self.detectResult = None
        self.recFailedTime = 0
        self.maxRecTime = 10
        self.recStatus = 0

    def run(self, r: SimModule, agv):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            r.resetRec()
            r.clearNotice(57300)
            self.target = r.getLM(self.locName, True)
        self.recStatus = r.getRecStatus()
        if self.target[3] != -1:
            robot2World = [r.loc()['x'], r.loc()['y'], r.loc()['angle']]
            targetRobot = Pos2Base([self.target[0], self.target[1], self.target[2]], robot2World)
            if self.recStatus == 3:
                self.recFailedTime = self.recFailedTime + 1
                if self.recFailedTime > self.maxRecTime:
                    r.setNotice(f"{self.locName} is not filled")
                    self.status = MoveStatus.FINISHED
                else:
                    r.recTargetObs(targetRobot[0], targetRobot[1], targetRobot[2], self.recFile)
            elif self.recStatus == 0 or self.recStatus == 1:
                r.recTargetObs(targetRobot[0], targetRobot[1], targetRobot[2], self.recFile)
                self.status = MoveStatus.RUNNING
            elif self.recStatus == 2:
                self.detectResult = r.getRecResult()["valid"]
                if self.detectResult:
                    r.setError(f"{self.locName} is filled")
                    self.status = MoveStatus.FAILED
        else:
            r.setError(f"{self.locName} does not exist")
            self.status = MoveStatus.FAILED

        curState = dict()
        curState["locName"] = self.locName
        curState["target"] = self.target
        curState["recFile"] = self.recFile
        curState["detectResult"] = self.detectResult
        curState["locDetectMid70Status"] = self.status
        agv.state['locDetectMid70Org'] = curState

        return self.status

    def reset(self, r: SimModule):
        r.logInfo("reset locDetectMid")
        self.status = MoveStatus.RUNNING


class locDetectBackLaser(BaseAction):
    def __init__(self, locName: str):
        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"
        self.init = True
        self.task = None
        self.status = MoveStatus.NONE
        self.locName = locName
        self.target = (0, 0, 0, -1)
        self.binDetectResult = None
        self.binDetectMatchCount = 0
        self.detectMatchTime = 0.2
        self.detectTime = 0.5  # 库位检测最长时间，不小于detectMatchTime"
        self.seq = 0
        self.time = time.time()
        self.startTime = 0
        self.locFilled = False

    def run(self, r: SimModule, agv):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            r.resetRec()
            r.clearNotice(57300)
            self.target = r.getLM(self.locName, True)
            self.startTime = time.time()
        if time.time() - self.startTime < self.detectTime:
            if self.target[3] != -1:
                if self.binFilled(r, self.locName):
                    self.locFilled = True
                    r.setError(f"loc({self.locName}) is filled")
                    self.status = MoveStatus.FAILED
            else:
                r.setError(f"{self.locName} does not exist")
                self.status = MoveStatus.FAILED
        else:
            self.status = MoveStatus.FINISHED

        curState = dict()
        curState["locName"] = self.locName
        curState["target"] = self.target
        curState['seq'] = self.seq
        curState['locFilled'] = self.locFilled
        curState["binDetectResult"] = self.binDetectResult
        curState["locDetectBackLaserStatus"] = self.status
        agv.state['locDetectBackLaserOrg'] = curState

        return self.status

    def binFilled(self, r: SimModule, targetLoc) -> bool:

        self.seq = self.seqGenerate(r)
        r.binDetection(self.seq)
        self.binDetectResult = r.getBinDetectionResult()
        r.logInfo(f"binDetectResult, {self.binDetectResult}")
        matchingBin = {}
        detectMatchCnt = self.detectMatchTime / 0.02
        if self.binDetectResult["bins"]:
            for binData in self.binDetectResult["bins"]:
                if binData["binId"] == targetLoc:
                    matchingBin = binData
                    break
            if matchingBin:
                # 判断 filled 是否为 True
                if matchingBin["filled"]:
                    self.binDetectMatchCount += 1
                else:
                    self.binDetectMatchCount = 0
            if self.binDetectMatchCount >= detectMatchCnt:
                return True
        return False

    def seqGenerate(self, r: SimModule):
        # 获取当前时间
        currentTime = datetime.now()

        # 提取年、月、日、小时、分钟、秒、毫秒
        year = currentTime.year
        month = currentTime.month
        day = currentTime.day
        hour = currentTime.hour
        minute = currentTime.minute
        second = currentTime.second
        millisecond = currentTime.microsecond // 1000  # 将微秒转换为毫秒

        # 将时间信息合并成一个字符串
        # 格式为：年月日时分秒毫秒
        currentTimeSeq = int(f"{year:04d}{month:02d}{day:02d}{hour:02d}{minute:02d}{second:02d}{millisecond:03d}")
        return currentTimeSeq

    def reset(self, r: SimModule):
        r.logInfo("reset locDetectBackLaser")
        self.status = MoveStatus.RUNNING


class precisionEvaluate(BaseAction):
    def __init__(self, r: SimModule):
        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"
        self.init = True
        self.task = None
        self.pos2world = []
        self.status = MoveStatus.NONE

    def run(self, r: SimModule, agv: Module):
        if self.init:
            self.init = False
            self.status = MoveStatus.RUNNING
            if agv.recResult:
                if agv.recParams['recCoordinate'] == "world":
                    target2world = [agv.recResult["x"], agv.recResult["y"], agv.recResult["yaw"]]
                    robot2world = [agv.recPos[0], agv.recPos[1], agv.recPos[2]]
                    target2Robot = Pos2Base(target2world, robot2world)  # 识别时目标点在小车坐标系的位置
                    agv.recResultToRobot["x"] = target2Robot[0]
                    agv.recResultToRobot["y"] = target2Robot[1]
                    agv.recResultToRobot["yaw"] = target2Robot[2]
                elif agv.recParams['recCoordinate'] == "robot":  # 识别时目标点在小车坐标系的位置
                    agv.recResultToRobot["x"] = agv.recResult["x"]
                    agv.recResultToRobot["y"] = agv.recResult["y"]
                    agv.recResultToRobot["yaw"] = agv.recResult["yaw"]

        if abs(agv.recResultToRobot["y"]) > agv.distPrecision or abs(agv.recResultToRobot["yaw"]) > agv.anglePrecision:
            agv.adjustTimes = agv.adjustTimes + 1
            if agv.adjustTimes > agv.adjustMaxTimes:
                self.status = MoveStatus.FAILED
                r.setError(
                    f"识别调整次数{agv.adjustTimes}，但精度[{self.pos2world[1]}] [{self.pos2world[2]}]仍不满足要求")
            else:
                agv.recTaskInit = True
                agv.recTaskStatus = False
                agv.adjustTask1Init = True
                agv.adjustTask1Status = False
                agv.evaluateTaskInit = True
                agv.evaluateTaskStatus = False
                agv.taskId = 0
        else:
            agv.evaluateTaskStatus = True
            self.status = MoveStatus.FINISHED
        return self.status

    def reset(self, r: SimModule):
        r.logInfo("reset precisionEvaluate")
        self.status = MoveStatus.RUNNING


class goodsCheck(BaseAction):
    def __init__(self, filename):
        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"
        self.status = MoveStatus.NONE
        self.filename = filename
        self.recTimes = 0
        self.maxRecTimes = 5
        self.maxExceedTimes = 3
        self.exceedTimes = 0
        self.maxEmptyTimes = 3
        self.emptyTimes = 0
        self.goodsError = False
        self.result = dict()

    def run(self, r: SimModule, agv: Module):
        if self.status == MoveStatus.NONE:
            r.resetRec()
            self.status = MoveStatus.RUNNING
        curState = dict()
        recStatus = r.getRecStatus()  # 获取识别状态 0: 初始化, 1: 识别中, 2: 获得结果, 3：识别出错, -1: 未知错误
        if recStatus == 2 or recStatus == 3 or recStatus == -1:  # 识别成功或失败
            # r.setNotice("rec failed:{}".format(self.result))
            if ModuleTool.delay(0.1):
                self.recTimes = self.recTimes + 1
                if r.warningExits(54906) and r.warningExits(54901):
                    self.exceedTimes = self.exceedTimes + 1
                elif r.warningExits(54905) and r.warningExits(54901):
                    self.emptyTimes = self.emptyTimes + 1
                if self.exceedTimes > self.maxExceedTimes:
                    r.setUserError(53930, f"栈板货物超限")
                    r.clearNotice(57300)
                    self.status = MoveStatus.FAILED
                    self.goodsError = True
                    return
                if self.emptyTimes > self.maxEmptyTimes:
                    r.setUserError(53931, f"栈板无货物")
                    r.clearNotice(57300)
                    self.status = MoveStatus.FAILED
                    self.goodsError = True
                    return
                else:
                    r.resetRec()
                if self.recTimes > self.maxRecTimes:
                    self.status = MoveStatus.FINISHED
                    r.setNotice(f"检测完成，货物正常，无超限情况")
        else:
            r.setNotice(f"--------------- goodsCheck ----------------")
            r.doRecWithAngle(self.filename, 0.0)

        curState['exceedTimes'] = self.exceedTimes
        curState['emptyTimes'] = self.emptyTimes
        curState['recCount'] = self.recTimes
        curState['goodsCheckStatus'] = self.status
        curState['recStatus'] = recStatus
        curState['file'] = self.filename
        curState["status"] = self.status
        curState['goodsError'] = self.goodsError
        agv.state['goodsCheckOrg'] = curState
        r.logDebug(json.dumps(curState))

    def reset(self, r):
        r.resetRec()
        self.status = MoveStatus.RUNNING


class forkMoveMode(BaseAction):
    movePriority = 0
    liftPriority = 1
    stretchPriority = 2
    forkAnyPriority = 3
    forkAllPriority = 4
    anyFinished = 5
    allFinished = 6
    Error = -1


class straightMoveMode(BaseAction):
    forward = 0
    backward = 1


class ActionStatus(IntEnum):
    """ 动作运行状态枚举，对标 ActionStatus """
    NONE = 0
    RUNNING = 1
    FINISHED = 3
    FAILED = 4
    SUSPENDED = 5

if __name__ == '__main__':
    Module.init()
    r = Robot()
    r.main()
