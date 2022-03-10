# -*- coding: utf-8 -*-
# @Time : 2022/3/10
# @Author : qiangsheng，zhong
# @File :SFL-R16S.py based on zhiche.py
# @Request : test_center#964 SFL-R16S叉车脚本
# @Version: 2.1

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
        "zero","unload","load","lift","rotate","stretch","moveY","rec","recAdjust", "safeCheck"
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
    "stretch_back": {
        "value": 0.,
        "tips": "stretch back length",
        "type": "double",
        "unit": "m"
    }, 
    "rotate": {
        "value": 0.,
        "tips": "rotate angle",
        "type": "double",
        "unit": "m"
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
def Pos2Base(pos2world, base2world):
    """将基于世界坐标系的两个位姿，转换为基于base的位姿

    Args:
        pos2world ([3]): 被转换的位姿，基于世界坐标系,0:x, 1:y, 2: theta
        base2world ([3]): 基准，基于世界坐标系,0:x, 1:y, 2: theta
    Returns:
        [3]: pos2base
    """
    pos2base = [0.,0.,0.]
    x = pos2world[0] - base2world[0]
    y = pos2world[1] - base2world[1]
    pos2base[0] = x * math.cos(base2world[2]) + y * math.sin(base2world[2])
    pos2base[1] = -x * math.sin(base2world[2]) + y * math.cos(base2world[2])
    pos2base[2] = normalize_theta(pos2world[2] - base2world[2])
    return pos2base

class Module(BasicModule):
    def __init__(self, r:SimModule, args):
        super(Module, self).__init__()
        p = ParamServer(__file__)
        self.status = MoveStatus.RUNNING
        self.lift_motor = "motor2"
        self.stretch_motor = "qianhouyi"
        self.rotate_motor = "qianhouqing"
        self.vy_motor = "zuoyouyi"

        self.stretch_warn_dist = 6.5
        self.reachDI = 1

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

        self.lift_zero = 0.3
        self.stretch_zero = 0.28
        self.rotate_zero = 0
        self.moveY_zero = 0

        self.rec_file = ""
        self.init = True
        self.task = dict()
        self.state = dict()
        self.task_list = []
        self.task_id = 0
        self.operation_status = MoveStatus.NONE

        #识别调整相关的参数
        self.rotate_yaw = 0.0  # 货叉0度,横移位置为0度时，货叉在小车坐标系下的角度
        self.rotate_x0 = 0.0  #货叉0度,横移位置为0度时，货叉旋转中心，在小车坐标系下x
        self.rotate_y0 = 0.0 #货叉0度,横移位置为0度时，货叉旋转中心，在小车坐标系下y
        self.fork_L0 = 1.0 #货叉末端离旋转中心的距离
        self.rec_offz = 0.0 #货叉高度的调整量

        #此处修改的是默认值，最终执行请在“zhiche.json"里进行更改
        p = ParamServer(__file__)
        self.lift_vel = p.loadParam("liftVel", type="float", default = 0.1, maxValue = 10000.0, minValue = 0.001, unit = "m/s", comment = "升降电机最大速度")
        self.stretch_vel = p.loadParam("stretchVel", type="float", default = 0.1, maxValue = 10000.0, minValue = 0.001, unit = "m/s", comment = "伸缩电机最大速度")
        self.rotate_vel = p.loadParam("rotateVel", type="float", default = 0.1, maxValue = 10000.0, minValue = 0.001, unit = "rad/s", comment = "倾斜电机最大速度")
        self.moveY_vel = p.loadParam("Vy", type = "float", default = 0.1, maxValue = 10000.0, minValue = 0.001, unit = "m/s", comment = "水平电机最大速度")
        
        #距离传感器
        self.distanceNodeId = (1,2) # distanceNode的ID号
        self.obsStopDist = 0.1 # 报警距离

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
            self.init_vy_motor_pos = self.vy_motor_pos
            r.initForkCollisionCheck()   # 初始化后视激光检测
            self.task = args
            self.rec_file = args.get("recfile","")
            self.operation_status = MoveStatus.NONE
            if "operation" not in self.task:
                r.setError("operation is empty!!!")
                self.status = MoveStatus.FAILED
                return self.status

        operation = self.task.get("operation","")
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
        elif operation == "safeCheck":
            self.safeCheck(r)
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
        :return: bool
        """
        sensor = r.sensorPointCloud()
        if 'local_cluster' not in sensor:
            return False, -1.0
        obs_dist = -1.0
        for data in sensor['local_cluster']:
            # r.logInfo("distanceNode {}".format(data))
            if data.get('id', -1) in self.distanceNodeId \
                and data.get('valid', False) and data.get('forbidden', False)\
                    and 'dist' in data:
                if obs_dist < 0:
                    obs_dist = data['dist']
                else:
                    obs_dist = min(obs_dist, data['dist'])
        r.logInfo("dist for distanceNode {} {} {}".format(obs_dist, self.obsStopDist, left_dist))
        
        if obs_dist < 0:
            return False, obs_dist
        if left_dist < obs_dist:
            return False, obs_dist
        elif self.obsStopDist < obs_dist:
            return False, obs_dist
        return True, obs_dist

    def back_laser_check(self, r: SimModule) -> bool:
        """
        后视激光检测, 有阻挡会自动报错52200, 需先调用一次initForkCollisionCheck
        :param r:
        :return:
        """
        if self.get_motor_pos(r, self.lift_motor_name) > self.laser_valid_height:
            if r.forkCollisionCheck():
                r.setError(f"back laser block!")
                return True
        return False


    def lift(self, r):
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
  
    def stretch(self, r):
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

    def rotate(self, r):
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


    def rec(self,r):
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

    def safeCheck(self, r):
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

    def recAdjust(self,r):
        if "recfile" not in self.task:
            r.setError("recfile is empty {}".format(json.dumps(self.task)))
            self.status = MoveStatus.FAILED 
        else:        
            if self.operation_status == MoveStatus.NONE:
                self.operation_status = MoveStatus.RUNNING
                self.task_list = [recAdjust(r, self.task["recfile"])]
                self.task_id = 0
            else:
                self.runTakList(r)
            cur_state = dict()
            cur_state["state"] = self.operation_status
            cur_state["task_id"] = self.task_id
            self.state["rec"] = cur_state

    def load(self,r:SimModule):
        if self.operation_status == MoveStatus.NONE:
            if r.hasGoods():
                self.state["load"] = "Fork has goods, cannot load"
                r.setError(f"Fork has goods, cannot load")
                return
            self.operation_status = MoveStatus.RUNNING
            if "recfile" in self.task:
                self.task_list = [
                    rotate(self.rotate_motor, self.task["rotate"]),
                    lift(self.lift_motor, self.task["liftHeight"]),
                    recAdjust(r, self.task["recfile"]),
                    stretch(self.stretch_motor, self.task["stretchLength"], self.reachDI),
                    lift(self.lift_motor, self.task["liftUpHeight"] + self.task["liftHeight"]),
                    stretch(self.stretch_motor, self.task["stretch_back"]),
                    lift(self.lift_motor, self.lift_zero),
                ]
            else:
                self.task_list = [
                    rotate(self.rotate_motor, self.task["rotate"]),
                    lift(self.lift_motor, self.task["liftHeight"]),
                    stretch(self.stretch_motor, self.task["stretchLength"], self.reachDI),
                    lift(self.lift_motor, self.task["liftUpHeight"] + self.task["liftHeight"]),
                    stretch(self.stretch_motor, self.task["stretch_back"]),
                    lift(self.lift_motor, self.lift_zero),
                ]
            self.task_id = 0
        else:
            self.runTakList(r)
        if self.operation_status == MoveStatus.FINISHED:
            r.setGoodsShape(0,0,0)
        cur_state = dict()
        cur_state["state"] = self.operation_status
        cur_state["task_id"] = self.task_id
        self.state["load"] = cur_state

    def unload(self,r):
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            self.vision_status = MoveStatus.FINISHED
            self.task_list = [
                rotate(self.rotate_motor, self.task["rotate"]),
                lift(self.lift_motor, self.task['liftHeight']),
                stretch(self.stretch_motor, self.task["stretchLength"]),
                lift(self.lift_motor, -self.task["liftDownHeight"] + self.task["liftHeight"]),
                stretch(self.stretch_motor, self.task["stretch_back"]),
                lift(self.lift_motor, self.lift_zero),
            ]
            self.task_id = 0
        else:
            self.runTakList(r)
        if self.operation_status == MoveStatus.FINISHED:
            r.clearGoodsShape()
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
                rotate(self.rotate_motor, self.rotate_zero),
                lift(self.lift_motor, self.lift_zero)
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
        if agv.stretch_pos > agv.stretch_warn_dist:
            r.setError("Cannot lift when strech {} larger than {}."
            .format(agv.stretch_pos,agv.stretch_warn_dist))
            self.status = MoveStatus.FAILED
        else:
            if self.dist < agv.init_lift_pos:
                # 货叉下降需要检查一下，货叉下降是否安全
                if agv.back_laser_check(r):
                    r.resetMotor(self.motor)
                else:
                    r.setMotorPosition(self.motor, self.dist, agv.lift_vel, -1)
            else:
                r.setMotorPosition(self.motor, self.dist, agv.lift_vel, -1)
            if r.isMotorReached(self.motor):
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
        flag, obs_dist = agv.fork_collision(r,left_dist)
        if flag:
            if not r.errorExits(53000):
                r.setError("fork tail collision error. obs distance is {}".format(obs_dist))
            r.resetMotor(self.motor)
        else:
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
        self.angle = a
    def run(self, r:SimModule, agv):
        self.status = MoveStatus.RUNNING
        if agv.stretch_pos > agv.stretch_warn_dist:
            r.setError("Cannot rotate when strech {} larger than {}."
            .format(agv.stretch_pos,agv.stretch_warn_dist))
            self.status = MoveStatus.FAILED
        else:
            r.setMotorPosition(self.motor, self.angle, agv.rotate_vel, -1)
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
    def __init__(self, r, filename):
        self.status = MoveStatus.NONE
        self.rec = rec(filename)
        self.result = []
        self.max_rec_fail_times = 10
        self.max_adjust_time = 10
        self.rec_fail_time = 0
        self.adjust_count = 0
        self.go_args = dict()
        self.ok = False
        self.plan_status = MoveStatus.NONE
        self.goPath = goPath.Module(r, dict())
        self.lift_pos = 0
        self.rot_theta = 0
        self.init = True
    def run(self, r:SimModule, agv:Module):
        self.status = MoveStatus.RUNNING
        if self.plan_status is not MoveStatus.FINISHED:
            self.plan_status = MoveStatus.RUNNING
            if self.rec.status is MoveStatus.RUNNING or self.rec.status is MoveStatus.NONE:
                self.rec.run(r,agv)
            elif self.rec.status is MoveStatus.FAILED:
                self.rec_fail_time = self.rec_fail_time + 1
                if self.rec_fail_time < self.max_rec_fail_times:
                    self.rec.reset(r)
                    self.rec.run(r,agv)
                else:
                    self.status = MoveStatus.FAILED
                    r.setError("rec fails!!! reach max times. {}".format(self.max_rec_fail_times))
                r.setNotice("rec fail!!! {}".format(self.rec_fail_time))
            elif self.rec.status is MoveStatus.FINISHED:
                self.rec_fail_time = 0
                code2rotate = [self.rec.result['x'], self.rec.result['y'], self.rec.result['yaw']]
                rotate2robot = [agv.rotate_x0, agv.rotate_y0 + agv.stretch_pos, agv.rotate_yaw + agv.rotate_pos]
                code2robot = Pos2World(code2rotate, rotate2robot)
                self.lift_pos = self.rec.result['z'] + agv.rec_offz
                self.rot_theta = normalize_theta(code2robot[2] + math.pi)

                rot_goal = normalize_theta(self.rot_theta - agv.rotate_yaw)
                self.rotate = rotate(agv.rotate_motor, rot_goal)
                lift_goal = agv.lift_pos + self.lift_pos
                self.lift = lift(agv.lift_motor, lift_goal)

                forkHead2rotate = [agv.fork_L0, 0, 0]
                idealRotate2robot = [agv.rotate_x0, agv.rotate_y0 + agv.stretch_pos, self.rot_theta]
                forkHead2robot = Pos2World(forkHead2rotate, idealRotate2robot)
                dx = code2robot[0] - forkHead2robot[0]
                self.go_args["coordinate"] = "robot"
                self.go_args["x"] = dx
                self.go_args["y"] = 0
                self.go_args["theta"] = 0
                self.go_args["reachAngle"] = math.pi
                self.go_args["useOdo"] = 1
                self.go_args["reachDist"] = 0.002

                r.logDebug("[recAdjust][{}|{}|{}|{}|{}|{}|{}|{}|{}]".format(
                self.rot_theta, agv.rotate_yaw, rot_goal, 
                self.lift_pos, agv.rec_offz, lift_goal, 
                code2robot[0],forkHead2robot[0], dx))
                
                if self.go_args["x"] < 0:
                    self.go_args["backMode"] = 1
                ok_x = 0.005
                ok_z = 0.005
                ok_theta = 0.017
                if abs(self.go_args['x']) < ok_x\
                    and abs(self.lift_pos) < ok_z\
                        and abs(self.rot_theta) < ok_theta:
                    self.status = MoveStatus.FINISHED
                else:
                    if self.adjust_count >= self.max_adjust_time:
                        self.status = MoveStatus.FAILED
                        r.setError("recAdjust fails!!! reach max times.")
                self.plan_status = MoveStatus.FINISHED
                self.rec.reset(r)
        elif self.status is not MoveStatus.FINISHED and self.status is not MoveStatus.FAILED:
            if self.goPath.status != MoveStatus.FINISHED\
                and self.goPath.status != MoveStatus.FAILED:
                if abs(self.go_args["x"]) < 0.003:
                    self.goPath.status = MoveStatus.FINISHED
                else:
                    self.goPath.run(r,self.go_args)
            
            if self.lift.status != MoveStatus.FINISHED\
                and self.lift.status != MoveStatus.FAILED:
                self.lift.run(r, agv)
            
            if self.rotate.status != MoveStatus.FINISHED\
                and self.rotate.status != MoveStatus.FAILED:
                self.rotate.run(r, agv)

            if self.goPath.status == MoveStatus.FAILED\
                or self.lift.status == MoveStatus.FAILED\
                    or self.rotate.status == MoveStatus.FAILED:
                self.status = MoveStatus.FAILED
            elif self.goPath.status == MoveStatus.FINISHED\
                and self.lift.status == MoveStatus.FINISHED\
                    and self.rotate.status == MoveStatus.FINISHED:
                self.adjust_count = self.adjust_count + 1
                self.rec_count = 0
                self.goPath.reset()
                self.lift = None
                self.rotate = None
                self.lift_pos = 0
                self.rot_theta = 0
                self.status = MoveStatus.RUNNING
                self.go_args = dict()
                self.plan_status = MoveStatus.NONE
        cur_state = dict()
        cur_state["goaPathStatus"] = self.goPath.status
        cur_state["planStatus"] = self.plan_status
        cur_state["go_args"] = self.go_args
        cur_state["rec_fail_time"] = self.rec_fail_time
        cur_state["ajdust_time"] = self.adjust_count
        cur_state["status"] = self.status
        cur_state["lif_pos"] = self.lift_pos
        cur_state["rot_theta"] = self.rot_theta
        agv.state["recAdjust_org"] = cur_state

    def reset(self, r):
        self.rec.reset(r)
        self.status = MoveStatus.RUNNING
        self.rec_fail_time = 0
        self.adjust_count = 0
        self.goPath.reset()
        self.lift = None
        self.rotate = None
        self.lift_pos = 0
        self.rot_theta = 0

if __name__ == '__main__':
    import syspy.rbkSim
    r = syspy.rbkSim.SimModule()
    m = Module(r,None)
    
    num = [1]
    def testNum(num):
        print(f"*****{num[0]}*****")
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