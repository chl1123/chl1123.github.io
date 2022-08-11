# -*- coding: utf-8 -*-
# @Time : 2022/5/13
# @Author : qiangsheng，zhong
# @File :SFL-R16S.py based on zhiche.py
# @Request : test_center#964 SFL-R16S叉车脚本
# @Version: 2.4
# @Description: 增加action和取放不动货叉

import json
import time
import sys

sys.path.append("..")
sys.path.append("../syspy")
from syspy.rbkSim import SimModule
from syspy.rbk import MoveStatus, BasicModule, Pos2World, normalize_theta, ParamServer
import math
import syspy.goPath as goPath

"""
####BEGIN DEFAULT ARGS####
{
    "operation":{
        "value": "zero",
        "default_value":[
        "zero","unload","load","lift","rotate","stretch","rec","recAdjust", "goPath", "action"
        ],
        "tips": "tips",
        "type": "complex"        
    },
    "stretchLength": {
        "value": 0.3,
        "tips": "货叉伸出长度",
        "type": "float",
        "unit": "m"
    },
    "liftHeight": {
        "value": 0.8,
        "tips": "货叉升降高度",
        "type": "float",
        "unit": "m"
    },
    "liftUpHeight":{
        "value": 0.,
        "tips": "load lift up hight",
        "type": "double",
        "unit": "m"
    },
    "liftDownHeight":{
        "value": 0.,
        "tips": "unload lift down hight",
        "type": "double",
        "unit": "m"
    },
    "rotate": {
        "value": 0.,
        "tips": "rotate dir. > 0 down; < 0 up",
        "type": "double",
        "unit": ""
    },
    "recfile": {
        "value": "tag/t0001.tag",
        "tips": "识别文件",
        "unit": "",
        "type": "string"
    }
}
####END DEFAULT ARGS####
"""

class Module(BasicModule):
    def __init__(self, r:SimModule, args):
        super(Module, self).__init__()
        p = ParamServer(__file__)
        self.status = MoveStatus.RUNNING

        # 四个电机的实时位置
        self.stretch_pos = 0.
        self.lift_pos = 0.
        self.rotate_pos = 0.
        self.vy_motor_pos = 0.

        # 四个电机初始位置
        self.init_stretch_pos = 0.
        self.init_lift_pos = 0.
        self.init_rotate_pos = 0.
        self.init_vy_motor_pos = 0.
        self.rec_file = ""
        self.init = True
        self.task = dict()
        self.state = dict()
        self.task_list = []
        self.task_id = 0
        self.operation_status = MoveStatus.NONE
        #operation
        self.operation = ""


        ## 下列参数需要使用前配置
        # 四个电机对应模型文件的名称
        self.lift_motor = "motor2"
        self.stretch_motor = "qianhouyi"
        self.rotate_motor = "qianhouqing"
        self.vy_motor = "zuoyouyi"
        # 货叉机构，伸出机构，旋转机构的零位
        self.lift_zero = 0.075
        self.stretch_zero = 0.01
        self.rotate_zero = 1 #向下旋转就是归0
        self.rotate_up = -1 # 向上转
        self.moveY_zero = 0
        # 四类电机的规划最大速度
        self.lift_vel = 0.4
        self.stretch_vel = 0.2
        self.rotate_vel = 0.1
        self.moveY_vel = 0.1
        # 到位DI
        self.reachDI = -1
        # 距离传感器
        self.distanceNodeId = (1,2) # distanceNode的ID号
        self.obsStopDist = 0.25 # 报警距离， 这个距离传感器的死区为0.2m，因此不能配置成小于0.2m
        # 倾斜延时
        self.rotate_time = 4.0 # 倾斜电机旋转3s
        # 激光尾部激光
        self.back_laser = (-1,-1)
        # 有货物后的货叉伸出距离
        self.load_stretch_safe_length = 0.01
        # 货叉伸出最大距离
        self.stretch_max_length = 0.418
        # 货叉伸出最大距离时的识别倒退距离
        self.back_dist = 100
        # 货叉伸出最大距离时的最小前置距离
        self.min_ahead_dist = 1.5
        # 货叉识别调整最大前移距离
        self.max_ahead_dist = 0


    def reset(self, r:SimModule):
        self.status = MoveStatus.RUNNING
        self.start_time = time.time()
        self.init = True
        self.task = dict()
        self.state = dict()
        self.task_list = []
        self.task_id = 0
        self.operation_status = MoveStatus.NONE

    def getMessage(self, r:SimModule):
        odo = r.odo()
        # r.logDebug(str(odo))
        for motor_info in odo.get('motor_info',[]):
            motor_name = motor_info.get('motor_name',"")
            if self.lift_motor == motor_name:
                self.lift_pos = motor_info.get('position', 0)
            elif self.stretch_motor == motor_name:
                self.stretch_pos = motor_info.get('position', 0)
            elif self.rotate_motor == motor_name:
                self.rotate_pos = motor_info.get('position', 0)
            elif self.vy_motor_pos == motor_name:
                self.vy_motor_pos = motor_info.get('position', 0)

    def run(self, r:SimModule,args):
        self.status = MoveStatus.RUNNING
        self.state = dict()
        self.getMessage(r)
        if self.init:
            self.init = False
            self.init_lift_pos = self.lift_pos
            self.init_stretch_pos = self.stretch_pos
            self.init_rotate_pos = self.rotate_pos
            self.init_vy_motor_pos = self.vy_motor_pos  # 初始化后视激光检测
            self.task = args
            self.rec_file = args.get("recfile","")
            self.operation_status = MoveStatus.NONE
            if "operation" not in self.task:
                r.setError("operation is empty!!!")
                self.status = MoveStatus.FAILED
                return self.status

        operation = self.task.get("operation","")
        self.operation = operation
        if operation == "":
            self.status = MoveStatus.FINISHED
        elif operation == "load":
            self.load(r)
        elif operation == "unload":
            self.unload(r)
        elif operation == "zero":
            self.zero(r)
        elif operation == "recAdjust":
            self.recAdjust(r)
        elif operation == "lift":
            self.lift(r)
        elif operation == "stretch":
            self.stretch(r)
        elif operation == "rotate":
            self.rotate(r)
        elif operation == "moveY":
            self.moveY(r)
        elif operation == "rec":
            self.rec(r)
        elif operation == "goPath":
            self.goPath(r)
        elif operation == "action":
            self.action(r)
        else:
            r.setError("operation is wrong {}".format(str(operation)))
            self.status = MoveStatus.FAILED
        if self.operation_status == MoveStatus.FINISHED:
            self.status = MoveStatus.FINISHED
        self.state["MoveStatus"] = self.status
        self.state["task"] = self.task
        str_state = json.dumps(self.state)
        r.setInfo(str_state)
        r.logDebug("[SFLState][{}]".format(str_state))
        if self.status is MoveStatus.FAILED:
            r.stopRobot(True)
        r.publishSpeed()
        r.logDebug("[SFLR16][{}|{}|{}|{}|{}|{}|{}|{}]".format(
        self.lift_pos, self.stretch_pos, self.rotate_pos, self.vy_motor_pos,
        self.status, self.task_id, len(self.task_list), self.operation_status))
        return self.status

    def fork_collision(self, r: SimModule, left_dist:float) ->tuple:
        """
        货叉尖端距离传感器的碰撞检测
        :param r: rbk
        :param left_idst: 剩余距离
        :return: bool, obs_dist
        """
        sensor = r.getDistanceSensor()
        obs_dist = -1.0
        if "node" not in sensor:
            r.setNotice("distanceSensor empty")
            return False, obs_dist
        node_ss = ""
        for data in sensor["node"]:
            if data.get('id', -1) in self.distanceNodeId \
                and data.get('valid', False) == True \
                    and data.get('forbidden', True) == False\
                        and 'dist' in data:
                if obs_dist < 0:
                    obs_dist = data['dist']
                else:
                    obs_dist = min(obs_dist, data['dist'])
            node_ss = "{}|{}|{}|{}|{}".format(data.get('id', -1),data.get('valid', False),data.get('forbidden', True), data.get('dist',-1), obs_dist)
            r.logDebug("[distanceNode][{}]".format(node_ss))
        
        if obs_dist < 0:
            return False, obs_dist
        if left_dist < obs_dist:
            return False, obs_dist
        elif self.obsStopDist < obs_dist:
            return False, obs_dist
        return True, obs_dist

    def back_laser_check(self, r: SimModule) -> bool:
        """
        :param r:
        :return: 是否碰撞
        """
        if r.laserCollision(self.back_laser):
            return True
        return False


    def action(self, r: SimModule):
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            if "liftHeight" in self.task:
                self.task_list.append(lift(self.lift_motor, self.task["liftHeight"]))
            if "stretchLength" in self.task:
                self.task_list.append(stretch(self.stretch_motor, self.task["stretchLength"]))
            self.task_id = 0
        else:
            self.runTakList(r)
        cur_state = dict()
        cur_state["state"] = self.operation_status
        cur_state["task_id"] = self.task_id
        self.state["action"] = cur_state

    def lift(self, r: SimModule):
        if "liftHeight" not in self.task:
            r.setError("lift height is empty {}".format(json.dumps(self.task)))
            self.status = MoveStatus.FAILED
        else:
            if self.operation_status == MoveStatus.NONE:
                self.operation_status = MoveStatus.RUNNING
                self.task_list = [lift(self.lift_motor, self.task["liftHeight"])]
                self.task_id = 0
            else:
                self.runTakList(r)
            cur_state = dict()
            cur_state["state"] = self.operation_status
            cur_state["task_id"] = self.task_id
            self.state["lift"] = cur_state        
  
    def stretch(self, r: SimModule):
        if "stretchLength" not in self.task:
            r.setError("stretch length is empty {}".format(json.dumps(self.task)))
            self.status = MoveStatus.FAILED    
        else:
            if self.operation_status == MoveStatus.NONE:
                self.operation_status = MoveStatus.RUNNING
                self.task_list = [stretch(self.stretch_motor, self.task["stretchLength"])]
                self.task_id = 0
            else:
                self.runTakList(r)
            cur_state = dict()
            cur_state["state"] = self.operation_status
            cur_state["task_id"] = self.task_id
            self.state["stretch"] = cur_state

    def rotate(self, r: SimModule):
        if "rotate" not in self.task:
            r.setError("rotate length is empty {}".format(json.dumps(self.task)))
            self.status = MoveStatus.FAILED  
        else:
            if self.operation_status == MoveStatus.NONE:
                self.operation_status = MoveStatus.RUNNING
                self.task_list = [rotate(self.rotate_motor, self.task["rotate"])]
                self.task_id = 0
            else:
                self.runTakList(r)
            cur_state = dict()
            cur_state["state"] = self.operation_status
            cur_state["task_id"] = self.task_id
            self.state["rotate"] = cur_state     


    def rec(self,r: SimModule):
        if "recfile" not in self.task:
            r.setError("recfile is empty {}".format(json.dumps(self.task)))
            self.status = MoveStatus.FAILED 
        else:
            if self.operation_status == MoveStatus.NONE:
                self.operation_status = MoveStatus.RUNNING
                self.task_list = [rec(self.task["recfile"])]
                self.task_id = 0
            else:
                self.runTakList(r)
            cur_state = dict()
            cur_state["state"] = self.operation_status
            cur_state["task_id"] = self.task_id
            self.state["rec"] = cur_state

    def goPath(self, r:SimModule):
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            self.task_list = [goPath(r)]
            self.task_id = 0
        else:
            self.runTakList(r)
        cur_state = dict()
        cur_state["state"] = self.operation_status
        cur_state["task_id"] = self.task_id
        self.state["goPath"] = cur_state       

    def safeCheck(self, r: SimModule):
        tor = 0.1
        if (self.stretch_pos + tor > 1.8 and self.rotate_pos + tor > math.pi) \
            or (self.stretch_pos - tor < 0.28 and self.rotate_pos - tor < 0):
            self.status = MoveStatus.FINISHED
            self.operation_status = MoveStatus.FINISHED
        else:
            self.status = MoveStatus.FAILED
            self.operation_status = MoveStatus.FAILED
            r.setError("The stretch position {} and rotation angle {} is not safe".format(self.stretch_pos, self.rotate_pos))
        cur_state = dict()
        cur_state["state"] = self.status
        self.state["safeCheck"] = cur_state

    def recAdjust(self,r: SimModule):   
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            self.task_list = [recAdjust(r)]
            self.task_id = 0
        else:
            self.runTakList(r)
        cur_state = dict()
        cur_state["state"] = self.operation_status
        cur_state["task_id"] = self.task_id
        self.state["recAdjust"] = cur_state

    def load(self,r:SimModule):
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            if r.hasGoods():
                self.state["load"] = "Fork has goods, cannot load"
                r.setError(f"Fork has goods, cannot load")
                return
            if "liftHeight" not in self.task\
                 and "liftUpHeight" not in self.task\
                     and "stretchLength" not in self.task:
                self.task_list = [
                    recAdjust(r)
                ]
            else:      
                if "liftHeight" not in self.task:
                    self.state["load"] = "liftHeight is missing"
                    r.setError(f"liftHeight is missing")
                    return
                if "liftUpHeight" not in self.task:
                    self.state["load"] = "liftUpHeight is missing"
                    r.setError(f"liftUpHeight is missing")
                    return                
                stretch_length = self.stretch_max_length
                if "stretchLength" in self.task:
                    stretch_length =  self.task["stretchLength"]
                if stretch_length > self.load_stretch_safe_length:
                    # 如果需要伸出插齿取叉货物
                    self.task_list = [
                        rotate(self.rotate_motor, self.rotate_zero), # 货叉前后角度水平
                        lift(self.lift_motor, self.task["liftHeight"]),
                        stretch(self.stretch_motor, stretch_length, self.reachDI),
                        recAdjust(r),
                        lift(self.lift_motor, self.task["liftUpHeight"]),
                        stretch(self.stretch_motor, self.load_stretch_safe_length)
                    ]
                else:
                    # 不需要伸出插齿去取叉货
                    self.task_list = [
                        rotate(self.rotate_motor, self.rotate_zero), # 货叉前后角度水平
                        lift(self.lift_motor, self.task["liftHeight"]),
                        stretch(self.stretch_motor, self.load_stretch_safe_length, self.reachDI),
                        recAdjust(r),
                        lift(self.lift_motor, self.task["liftUpHeight"])
                    ]           
            self.task_id = 0
        else:
            self.runTakList(r)
        if self.operation_status == MoveStatus.FINISHED:
            r.forkGoods(True, self.task.get("recfile",""))
        cur_state = dict()
        cur_state["state"] = self.operation_status
        cur_state["task_id"] = self.task_id
        self.state["load"] = cur_state

    def unload(self,r: SimModule):
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            self.vision_status = MoveStatus.FINISHED
            if "liftHeight" not in self.task\
                 and "liftDownHeight" not in self.task\
                     and "stretchLength" not in self.task:
                self.task_list = [
                    goPath(self)
                ]
            else:
                if "liftHeight" not in self.task:
                    self.state["load"] = "liftHeight is missing"
                    r.setError(f"liftHeight is missing")
                    return
                if "liftDownHeight" not in self.task:
                    self.state["load"] = "liftDownHeight is missing"
                    r.setError(f"liftDownHeight is missing")
                    return    
                stretch_length = self.stretch_max_length
                if "stretchLength" in self.task:
                    stretch_length =  self.task["stretchLength"]
                if stretch_length > self.stretch_zero:
                    # 如果需要伸出插齿放叉货物
                    self.task_list = [
                        lift(self.lift_motor, self.task['liftHeight']),
                        stretch(self.stretch_motor, stretch_length),
                        goPath(self),
                        rotate(self.rotate_motor, self.rotate_zero),
                        lift(self.lift_motor, self.task["liftDownHeight"]),
                        stretch(self.stretch_motor, self.stretch_zero)
                    ]
                else:
                    # 不需要伸出插齿去放叉货
                    self.task_list = [
                        lift(self.lift_motor, self.task['liftHeight']),
                        stretch(self.stretch_motor, stretch_zero),
                        goPath(self),
                        rotate(self.rotate_motor, self.rotate_zero),
                        lift(self.lift_motor, self.task["liftDownHeight"])
                    ]           
            self.task_id = 0
        else:
            self.runTakList(r)
        if self.operation_status == MoveStatus.FINISHED:
            r.forkGoods(False, "")
        cur_state = dict()
        cur_state["state"] = self.operation_status
        cur_state["task_id"] = self.task_id
        self.state["unload"] = cur_state             

    def zero(self,r):
        if r.hasGoods():
            self.state["load"] = "Fork has goods, cannot load"
            r.setError(f"Fork has goods, cannot load")
            return
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            self.task_list = [
                stretch(self.stretch_motor, self.stretch_zero),
                lift(self.lift_motor, self.lift_zero),
                rotate(self.rotate_motor, self.rotate_zero)
            ]
            self.task_id = 0
        else:
            self.runTakList(r)
        cur_state = dict()
        cur_state["state"] = self.operation_status
        cur_state["task_id"] = self.task_id
        self.state["zero"] = cur_state  

    def runTakList(self, r):
        if self.task_id < len(self.task_list):
            if self.task_list[self.task_id].status == MoveStatus.NONE:
                self.task_list[self.task_id].reset(r)
            elif self.task_list[self.task_id].status == MoveStatus.FINISHED:
                self.task_id = self.task_id + 1
            elif self.task_list[self.task_id].status == MoveStatus.FAILED:
                self.operation_status = MoveStatus.FAILED
            else:
                self.task_list[self.task_id].run(r, self)
        else:
            self.operation_status = MoveStatus.FINISHED

    def cancel(self, r:SimModule):
        r.stopRobot(True)
        r.logInfo("script cancel")
        self.status = MoveStatus.NONE
    def suspend(self, r:SimModule):
        r.stopRobot(True)
        r.logInfo("script suspended")
        self.status = MoveStatus.SUSPENDED
        self.start_connect_time = time.time()

class lift:
    def __init__(self, motor_name, dist):
        self.status = MoveStatus.NONE
        self.motor = motor_name
        self.dist = dist

    def run(self, r:SimModule, agv:Module):
        self.status = MoveStatus.RUNNING
        collision = False

        if self.dist < agv.init_lift_pos:
            # 货叉下降需要检查一下，货叉下降是否安全
            if agv.back_laser_check(r):
                collision = True
            else:
                r.setMotorPosition(self.motor, self.dist, agv.lift_vel, -1)
        else:
            r.setMotorPosition(self.motor, self.dist, agv.lift_vel, -1)
        if collision == False and  r.isMotorReached(self.motor):
            self.status = MoveStatus.FINISHED
            r.resetMotor(self.motor)

        cur_state = dict()
        cur_state['lift_state'] = self.status
        cur_state['dist'] = self.dist
        agv.state['lift_org'] = cur_state

    def reset(self, r):
        r.resetMotor(self.motor)
        self.status = MoveStatus.RUNNING

class stretch:
    def __init__(self, motor_name, dist, reachDI = -1):
        self.status = MoveStatus.NONE
        self.motor = motor_name
        self.dist = dist
        self.reachDI = reachDI
    def run(self, r:SimModule, agv:Module):
        self.status = MoveStatus.RUNNING
        left_dist = self.dist - agv.stretch_pos
        collision = False
        obs_dist = -1
        if self.dist > agv.init_stretch_pos:
            collision, obs_dist = agv.fork_collision(r,left_dist)
        if collision:
            if not r.errorExits(53000):
                r.setError("fork tail collision error. obs distance is {}".format(obs_dist))
            r.resetMotor(self.motor)
        else:
            if r.errorExits(53000):
                r.clearError(53000)
            r.setMotorPosition(self.motor, self.dist, agv.stretch_vel, self.reachDI)
            if r.isMotorReached(self.motor):
                self.status = MoveStatus.FINISHED
                r.resetMotor(self.motor)
        cur_state = dict()
        cur_state['stretch_state'] = self.status
        cur_state['dist'] = self.dist
        agv.state['stretch_org'] = cur_state

    def reset(self, r):
        r.resetMotor(self.motor)
        self.status = MoveStatus.RUNNING

class rotate:
    def __init__(self, motor_name, a):
        self.status = MoveStatus.NONE
        self.motor = motor_name
        self.rot_dir = a
        self.start_time = time.time()
    def run(self, r:SimModule, agv:Module):
        self.status = MoveStatus.RUNNING
        rot_vel = agv.rotate_vel
        if self.rot_dir < 0:
            rot_vel = - agv.rotate_vel
        r.setMotorSpeed(self.motor, rot_vel, -1)
        cur_time = time.time()
        if (cur_time - self.start_time) > agv.rotate_time:
            r.resetMotor(self.motor)
            self.status = MoveStatus.FINISHED
        cur_state = dict()
        cur_state['rotate_state'] = self.status
        cur_state['rot_dir'] = self.rot_dir
        cur_state['rot_time'] = cur_time - self.start_time
        agv.state['rotate_org'] = cur_state

    def reset(self, r):
        self.start_time = time.time()
        r.resetMotor(self.motor)
        self.status = MoveStatus.RUNNING

class moveY:
    def __init__(self, motor_name, dist):
        self.status = MoveStatus.NONE
        self.motor = motor_name
        self.dist = dist
    def run(self, r:SimModule, agv:Module):
        self.status = MoveStatus.RUNNING
        r.setMotorPosition(self.motor, self.dist, agv.moveY_vel, -1)
        if r.isMotorReached(self.motor):
            self.status = MoveStatus.FINISHED
            r.resetMotor(self.motor)
        cur_state = dict()
        cur_state['rotate_state'] = self.status
        cur_state['angle'] = self.angle
        agv.state['rotate_org'] = cur_state

    def reset(self, r):
        r.resetMotor(self.motor)
        self.status = MoveStatus.RUNNING

class rec:
    def __init__(self, filename):
        self.status = MoveStatus.NONE
        self.filename = filename
        self.rec_times = 0
        self.max_rec_times = 10
        self.result = dict()
    def run(self, r:SimModule,agv:Module):
        self.status = MoveStatus.RUNNING
        rec_status = r.getRecStatus()
        loc = r.loc()
        r.logDebug("rec_status: {}".format(rec_status))
        if rec_status == 3:
            self.rec_times = self.rec_times + 1
            if self.rec_times > self.max_rec_times:
                r.setError("rec fail. reach max times {}".format(self.max_rec_times))
                self.status = MoveStatus.FAILED
            else:
                r.doRecWithAngle(self.filename,0.0)
        elif rec_status == 0 or rec_status == 1:
            r.doRecWithAngle(self.filename,0.0)
        elif rec_status == 2:
            self.result = r.getRecResult()
            r.logDebug("rec_result:{}".format(self.result))
            self.status = MoveStatus.FINISHED
        cur_state = dict()
        cur_state['rec_result'] = self.result
        cur_state['rec_state'] = self.status
        cur_state['rec_status'] = rec_status
        cur_state['file'] = self.filename
        agv.state['rec_org'] = cur_state
        r.logDebug(json.dumps(agv.state))

    def reset(self, r):
        r.resetRec()
        self.status = MoveStatus.RUNNING

class recAdjust:
    def __init__(self, r:SimModule):
        self.init = True
        self.task = None
        self.status = MoveStatus.NONE
    def run(self, r:SimModule, agv:Module):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            self.task = r.moveTask()
            if "params" not in self.task:
                self.task["params"] = []
            has_op = False
            has_rec = False
            has_rec_file = False
            for p in self.task["params"]:
                if p["key"] == "operation":
                    has_op = True
                    if agv.operation == "unload":
                        p["string_value"] = "ForkUnload"
                    else:
                        p["string_value"] = "ForkLoad"
                elif p["key"] == "recognize":
                    has_rec = True
                elif p["key"] == "recfile":
                    has_rec_file = True
                    if "recfile" in agv.task:
                        p["string_value"] = agv.task["recfile"]
            if has_op == False:
                p = dict()
                p["key"] = "operation"
                if agv.operation == "load":
                    p["string_value"] = "ForkLoad"
                elif agv.operation == "unload":
                    p["string_value"] = "ForkUnload"
                else:
                    p["string_value"] = ""
                self.task["params"].append(p)
            if has_rec_file == False:
                if "recfile" in agv.task:
                    p = dict()
                    p["key"] = "recfile"
                    p["string_value"] = agv.task["recfile"]
                    self.task["params"].append(p)
            if has_rec == False:
                if "recfile" in agv.task:
                    p = dict()
                    p["key"] = "recognize"
                    p["bool_value"] = True
                    self.task["params"].append(p) 
                    has_rec = True               
            if has_rec:
                p1 = dict()
                p1["key"] = "rec_back_dist"
                p1["double_value"] = agv.back_dist + (agv.stretch_max_length - agv.stretch_pos)
                self.task["params"].append(p1)
                p2 = dict()
                p2["key"] = "rec_min_ahead_dist"
                p2["double_value"] = agv.min_ahead_dist - (agv.stretch_max_length - agv.stretch_pos)
                self.task["params"].append(p2)    
                p3 = dict()
                p3["key"] = "rec_ahead_dist"
                p3["double_value"] = agv.max_ahead_dist
                self.task["params"].append(p3)                                
        r.logInfo("recAdjust task {}".format(str(self.task)))
        self.status = r.recAndGoPathDi(json.dumps(self.task))
        return self.status

    def reset(self, r:SimModule):
        r.logInfo("reset recAdjust")
        self.status = MoveStatus.RUNNING
        r.resetRecAndGoPathDi()

class goPath:
    def __init__(self, r:SimModule):
        self.init = True
        self.task = None
        self.status = MoveStatus.NONE
    def run(self, r:SimModule, agv:Module):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            self.task = r.moveTask()              
        r.logInfo("goPath task {}".format(str(self.task)))
        self.status = r.goMapPath(json.dumps(self.task))
        return self.status

    def reset(self, r:SimModule):
        r.logInfo("reset goPath")
        self.status = MoveStatus.RUNNING
        r.resetGoMapPath()

if __name__ == '__main__':
    import syspy.rbkSim
    r = syspy.rbkSim.SimModule()
    m = Module(r,None)
    
    num = [1]
    def testNum(num, name = None):
        if name == None:
            print(f"*****{num[0]}*****")
        else:
            print(f"*****{name}*****")
        num[0] = num[0] + 1


    testNum(num)
    m.reset(r)
    data = dict()
    data["operation"] = "lift"
    data["lift"] = 1.
    print(m.run(r, data))

    testNum(num)
    m.reset(r)
    data = dict()
    data["operation"] = "rotate"
    data["rotate"] = 1.
    print(m.run(r, data))

    testNum(num)
    m.reset(r)
    data = dict()
    data["operation"] = "stretch"
    data["stretchLength"] = 1.
    print(m.run(r, data))
    print(m.run(r, data))
    print(m.run(r, data))

    testNum(num)
    data = dict()
    data["operation"] = "rec"
    data["recfile"] = "s001.pallet"
    print(m.run(r, data))

    testNum(num)
    m.reset(r)
    data = dict()
    data["operation"] = "recAdjust"
    data["recfile"] = "s001.pallet"
    print(m.run(r, data))

    testNum(num)
    m.reset(r)
    data = dict()
    data["operation"] = "load"
    data["rotate"] = 1.57
    data["liftHeight"] = 1.
    data["stretchLength"] = 1.
    data["recfile"] = "s001.pallet"
    data["liftUpHeight"] = 0.01
    data["stretch_back"] = 0.1
    print(m.run(r, data))

    testNum(num)
    m.reset(r)
    data = dict()
    data["operation"] = "load"
    data["rotate"] = 1.57
    data["liftHeight"] = 1.
    data["stretchLength"] = 1.
    data["liftUpHeight"] = 0.01
    data["stretch_back"] = 0.1
    print(m.run(r, data))

    testNum(num)
    m.reset(r)
    data = dict()
    data["operation"] = "unload"
    data["rotate"] = 1.57
    data["liftHeight"] = 1.
    data["stretchLength"] = 1.
    data["liftDownHeight"] = -0.01
    data["stretch_back"] = 0.1
    print(m.run(r, data))

    testNum(num)
    m.reset(r)
    data = dict()
    data["operation"] = "zero"
    print(m.run(r, data))

    testNum(num)
    m.reset(r)
    data = dict()
    data["operation"] = "safeCheck"
    print(m.run(r, data))


    testNum(num, "action")
    m.reset(r)
    data = dict()
    data["operation"] = "action"
    data["liftHeight"] = 1.
    data["stretchLength"] = 1.
    print(m.run(r, data))
    print(m.run(r, data))

    testNum(num, "load_without_lift")
    m.reset(r)
    data = dict()
    data["operation"] = "load"
    print(m.run(r, data))
    print(m.run(r, data))

    testNum(num, "unload_without_lift")
    m.reset(r)
    data = dict()
    data["operation"] = "unload"
    print(m.run(r, data))
    print(m.run(r, data))