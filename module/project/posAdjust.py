# -*- coding: utf-8 -*-
# @Date : 2022/9/7
# @Author : zhong
# @File :posAdjust.py
# @Version : 1.1

import json
import math

from rbkSim import SimModule
from rbk import MoveStatus, BasicModule, Pos2Base, ParamServer
import goPath
from robot import ModuleTool

"""
####BEGIN DEFAULT ARGS####
{
    "recfile": {
            "value": "tag/t0001.tag",
            "tips": "识别文件",
            "type": "string"
        }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        self.init = True
        self.status = MoveStatus.NONE
        self.report_info = dict()
        self.robot_move = goPath.Module(r, args)
        self.rec_file = "tag/t0001.tag"
        self.rec_adjust_obj = None
        r.logInfo(f"init args: {args}")

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            self.rec_file = args.get("recfile", "")
            self.rec_adjust_obj = RecAdjust(r, self.rec_file)
            if not bool(self.rec_file):
                r.setError(f"recfile is empty: {args}")
                self.status = MoveStatus.FAILED

        if self.rec_adjust_obj.status != MoveStatus.FAILED and self.rec_adjust_obj.status != MoveStatus.FINISHED:
            self.rec_adjust_obj.run(r)
        elif self.rec_adjust_obj.status == MoveStatus.FAILED:
            self.status = MoveStatus.FAILED
        elif self.rec_adjust_obj.status == MoveStatus.FINISHED:
            self.status = MoveStatus.FINISHED

        self.report_info['script_args'] = args
        self.report_info['rec_adjust'] = self.rec_adjust_obj.state
        self.report_info['task_status'] = self.status
        r.setInfo(json.dumps(self.report_info))
        r.logInfo(json.dumps(self.report_info))
        return self.status


class RecAdjust:
    def __init__(self, r, file):
        self.file = file
        self.status = MoveStatus.NONE
        self.rec_failed_time = 0
        self.max_rec_time = 10
        self.adjust_count = 1
        self.max_adjust_times = 10
        self.go_path = goPath.Module(r, dict())
        self.move_args = dict()
        self.state = dict()
        self.start_time = None
        self.rec_result = self.do_rec(r, self.file)
        p = ParamServer(__file__)
        self.x_dist = p.loadParam("x_dist", type="float", default=0.003, comment="x 坐标精度")
        self.y_dist = p.loadParam("y_dist", type="float", default=0.003, comment="y 坐标精度")
        self.theta_dist = p.loadParam("theta_dist", type="float", default=0.0088, comment="theta 角度精度")
        self.x_code2robot = p.loadParam("x_code2robot", type="float", default=0.0, comment="相机距离AGV里程中心的x偏差")
        self.y_code2robot = p.loadParam("y_code2robot", type="float", default=0.0, comment="相机距离AGV里程中心的y偏差")
        self.theta_code2robot = p.loadParam("theta_code2robot", type="float", default=0.0, comment="相机与AGV的角度偏差, 弧度值")

    def run(self, r):
        self.status = MoveStatus.RUNNING
        if self.rec_result:  # 识别成功，获取识别结果
            if self.go_path.status == MoveStatus.NONE:
                self.go_path.status = MoveStatus.RUNNING
                pos2world = [self.rec_result['x'], self.rec_result['y'], self.rec_result['yaw']]  # 目标点在世界坐标系的位置
                robot2world = [r.loc()['x'], r.loc()['y'], r.loc()['angle']]  # 小车在世界坐标系的位置
                pos2robot = Pos2Base(pos2world, robot2world)  # 目标点相对小车的位置
                self.state['pos2robot'] = pos2robot
                self.state['pos2world'] = pos2world
                self.state['robot2world'] = robot2world
                # 目标点相对小车的位置小于阈值时，识别调整完成
                if abs(pos2robot[0]) < (self.x_dist+self.x_code2robot) and abs(math.pi - abs(pos2robot[2])) < self.theta_dist:
                    self.status = MoveStatus.FINISHED
                    return True
                self.move_args['coordinate'] = 'robot'
                self.move_args['x'] = pos2robot[0] - self.x_code2robot
                self.move_args['y'] = 0
                self.move_args['theta'] = self.rec_result['yaw'] - math.pi    # 角度调整
                self.move_args['reachAngle'] = self.theta_dist
                self.move_args['useOdo'] = 1
                self.move_args['reachDist'] = 0.003
                self.state['move_args'] = self.move_args
                if self.move_args["x"] < 0:
                    self.move_args["backMode"] = 1
            elif self.go_path.status == MoveStatus.RUNNING:
                self.go_path.run(r, self.move_args)
            elif self.go_path.status == MoveStatus.FINISHED:
                self.adjust_count = self.adjust_count + 1
                self.reset(r)
                # self.status = MoveStatus.FINISHED                      # 只调整一次
                if self.adjust_count > self.max_adjust_times:
                    r.setError(f"rec adjust failed over the max times")
                    self.status = MoveStatus.FAILED
            elif self.go_path.status == MoveStatus.FAILED:
                r.setError(f"adjust failed, goPath has error. {self.move_args}")
                self.status = MoveStatus.FAILED
        else:   # 识别失败
            if ModuleTool.delay(0.5):
                self.rec_result = self.do_rec(r, self.file)
                self.rec_failed_time += 1
                if self.rec_failed_time > self.max_rec_time:
                    r.setError(f"rec failed over the max times, {self.rec_result}")
                    self.status = MoveStatus.FAILED
        self.state['rec_result'] = self.rec_result
        self.state['rec_file'] = self.file
        self.state['rec_adjust_status'] = self.status
        self.state['rec_count'] = self.rec_failed_time
        self.state['adjust_count'] = self.adjust_count

    def reset(self, r):
        self.status = MoveStatus.RUNNING
        r.resetRec()
        self.rec_failed_time = 0
        self.go_path.reset()
        self.rec_result = self.do_rec(r, self.file)
        r.logInfo(f"RecAdjust reset")

    def do_rec(self, r: SimModule, file):
        """
        识别文件, 识别成功返回识别数据，否则返回 False
        :param r:
        :param file:
        :return:
        """
        rec_status = r.getRecStatus()   # 0: 初始化；1: 识别中 ； 2: 获得结果； 3：识别出错；-1： 未知错误
        self.state['rec_status'] = rec_status
        if rec_status == 2:
            return r.getRecResult()
        elif rec_status == 3 or rec_status == -1:
            r.resetRec()
        else:
            r.doRec(file)
        return None


if __name__ == '__main__':
    r = SimModule()
    args = {}
    m = Module(r, args)
    while m.status is not MoveStatus.FAILED and m.status is not MoveStatus.FINISHED:
        m.run(r, args)
