import math
import logging
import json
from enum import IntEnum
import time

from syspy.script_data import ScriptData
from syspy import Navigation, Loc, Abnormal, Logger, Module, ScriptStatus, Trace
from syspy.lib.module import Pos2World
from tasks.standard import goPath

log = logging.getLogger("rbk.script")

class GoBezierWorld:
    """
        走贝塞尔曲线
    """
    def __init__(self, target_world, back_dist=0.0, adjust_dist_for_curvature_limit=2, min_ahead_dist=0.0, is_backwards=False, is_hold_dir=None,
                 max_speed=0.3, max_accele=0.3, max_decele=0.2, decele_dist=0.1, curvature_limit=1.3, path_dist_accuracy=0.01, path_angle_accuracy=0.5,alpha = 0.2):
        del target_world[3:]
        self.action_name = self.__class__.__name__

        self.target_world = target_world
        self.end_position_world = [0,0,0]
        self.robot_loc = None
        self.robot_final_loc = None

        self.back_dist = back_dist
        self.adjust_dist_for_curvature_limit = adjust_dist_for_curvature_limit
        self.min_ahead_dist = min_ahead_dist
        self.is_backwards = is_backwards
        self.is_hold_dir = is_hold_dir
        self.max_speed = max_speed
        self.max_accele = max_accele
        self.max_decele = max_decele
        self.decele_dist = decele_dist
        self.curvature_limit = curvature_limit
        self.path_dist_accuracy = path_dist_accuracy
        self.path_angle_accuracy = path_angle_accuracy

        self.action_status = ScriptStatus.NONE
        self.init = True
        self.target_robot = [0, 0, 0]
        self.control_point = None
        self.param = {}
        self.is_set_min_speed = False

        # bezier路径相关参数
        self.is_first_path_reached = False
        self.xs = []
        self.ys = []
        self.xs_ret = []
        self.ys_ret = []
        self.initial_point_world = None
        self.bezier_path_world = None
        self.initial_point_world_return = None
        self.bezier_path_world_return = None
        self.bezier_end_x = None
        self.bezier_end_y = None
        self.offset_dist = 0.0
        self.k_max = 0 #定义曲率

        Navigation.resetPath()

        # 获取机器人位置（world系）
        self.robot_loc = [Loc.get_pose()["x"], Loc.get_pose()["y"], math.radians(Loc.get_pose()["yaw"])]
        # self.robot_loc = [Loc.get_position()[0], Loc.get_position()[1], math.radians(Loc.get_angle()[0])]
        # 计算终点
        self.end_position_world = Pos2World([-self.back_dist, 0, 0], self.target_world)
        self.target_world = Pos2World([self.min_ahead_dist, 0, 0], self.target_world)

        success = False
        max_offset = self.adjust_dist_for_curvature_limit
        offset_step = 0.1
        p0_xy = p1_xy = p2_xy = p3_xy = [0, 0]

        while self.offset_dist <= max_offset:
            # 起点从(0, 0)往后移，作为新的P0
            if self.is_backwards:
                P0 = [self.offset_dist, 0, math.pi]
            else:
                P0 = [-self.offset_dist, 0, 0]
            P0 = Pos2World(P0, self.robot_loc)
            P3 = self.target_world

            # 生成贝塞尔曲线控制点与路径
            p0, p1, p2, p3, p4, p5 = self.compute_bezier_controls_5th(P0, P3,alpha,alpha)
            self.xs, self.ys = self.bezier_points(p0, p1, p2, p3, p4, p5)
            self.bezier_end_x, self.bezier_end_y = self.xs[-1], self.ys[-1]

            # 直线起点和终点
            x1, y1 = self.bezier_end_x, self.bezier_end_y
            x2, y2 = self.end_position_world[0], self.end_position_world[1]

            # 直线插值点数量
            num_points = 500

            # 生成离散点
            for i in range(num_points):
                t = i / (num_points - 1)  # 从0到1均匀分布
                x = x1 + (x2 - x1) * t
                y = y1 + (y2 - y1) * t
                # 添加末端直线路径
                self.xs.append(round(x,5))
                self.ys.append(round(y,5))

            # 判断曲率是否超限
            self.k_max = self.bezier_curvature(p0, p1, p2, p3, p4, p5)
            Trace.log(f"bezier curv:{self.k_max}")
            if self.k_max <= self.curvature_limit:
                success = True
                break
            self.offset_dist += offset_step
        Trace.log(f"ahead dist:{self.offset_dist}")
        Trace.log(f"bezier path:x{self.xs},y:{self.ys}")

        if not success:
            Abnormal.setTask(53900, f"curvature limit exceeded. max_curvature={self.k_max}",
                             "The positions of the robot and the target point cannot generate a Bezier curve",
                             "Adjust the robot's position before running this task",
                             "GoBezierWorld")
            Module.set_status(ScriptStatus.FAILED)
        if self.k_max >= 30:
            Abnormal.setTask(53901, f"wrong path. max_curvature={self.k_max}",
                             "",
                             "",
                             "GoBezierWorld")
            Module.set_status(ScriptStatus.FAILED)
        # 成功构造路径,需要将路径分为2段，第一段后退至贝塞尔起始点
        self.control_point = [p0_xy, p1_xy, p2_xy, p3_xy]
        # 记录第一个倒退点
        self.initial_point_world = [self.xs[0], self.ys[0]]
        self.bezier_path_world = [self.xs, self.ys]

        # 此处记录返回路径
        self.xs_ret = self.xs[::-1]
        self.ys_ret = self.ys[::-1]
        self.initial_point_world_return = self.robot_loc
        self.bezier_path_world_return = [self.xs_ret, self.ys_ret, self.robot_loc[2]]

    def run(self):
        self.action_status = ScriptStatus.RUNNING
        if self.init:
            self.init = False
            # 规划第一段倒退路线参数
            Navigation.resetPath()
            Navigation.setPathReachAngle(math.radians(self.path_angle_accuracy))  # 到位精度
            Navigation.setPathReachDist(self.path_dist_accuracy)
            Navigation.setPathBackMode(not self.is_backwards)  # 设置正走倒走
            if self.is_hold_dir:
                Navigation.setPathHoldDir(self.is_hold_dir) # 用于全向车
            Navigation.setPathMaxSpeed(self.max_speed)
            Navigation.setPathOnWorld([self.robot_loc[0], self.xs[0]],
                                      [self.robot_loc[1], self.ys[0]],
                                      self.robot_loc[2])
            self.param["maxAcc"] = float(self.max_accele)
            self.param["maxDec"] = float(self.max_decele)
            Navigation.goPathParam(self.param)

        # 行走到第一个倒退点后规划贝塞尔路径参数
        if not self.is_first_path_reached and self.action_status != ScriptStatus.FAILED: # 走第一段路线到曲率合适的贝塞尔起点
            self.is_first_path_reached = Navigation.isPathReached()
            log.info(f"self.is_first_path_reached={self.is_first_path_reached}")
            if self.is_first_path_reached:
                Navigation.resetPath()
                Navigation.setPathReachAngle(self.path_angle_accuracy)
                Navigation.setPathReachDist(self.path_dist_accuracy)
                Navigation.setPathBackMode(self.is_backwards)  # 设置正走倒走
                if self.is_hold_dir:
                    Navigation.setPathHoldDir(self.is_hold_dir) # 用于全向车
                Navigation.setPathMaxSpeed(self.max_speed)
                if not self.is_backwards:
                    self.end_position_world[2] += math.pi
                    self.end_position_world[2] = (self.end_position_world[2] + math.pi) % (2 * math.pi) - math.pi
                Navigation.setPathOnWorld(self.xs, self.ys, self.end_position_world[2])
                self.param["maxAcc"] = float(self.max_accele)
                self.param["maxDec"] = float(self.max_decele)
                Navigation.goPathParam(self.param)

        # 行走第二段贝塞尔路径
        if self.is_first_path_reached and self.action_status != ScriptStatus.FAILED: # 走贝塞尔到终点
            is_reached = Navigation.isPathReached()
            log.info(f"is_reached={is_reached}")
            if is_reached:
                self.action_status = ScriptStatus.FINISHED
            else:
                self.action_status = ScriptStatus.RUNNING

            robot_current_loc = [Loc.get_pose()["x"], Loc.get_pose()["y"], math.radians(Loc.get_pose()["yaw"])]
            # robot_current_loc = [Loc.get_position()[0], Loc.get_position()[1], math.radians(Loc.get_angle()[0])]
            dist_cur_loc_end_loc = math.hypot(
                self.end_position_world[0] - robot_current_loc[0],
                self.end_position_world[1] - robot_current_loc[1]
            )
            if dist_cur_loc_end_loc < self.decele_dist and not self.is_set_min_speed:
                self.is_set_min_speed = True
                Navigation.setPathMaxSpeed(0.1)

            # 获取机器人位置（world系）
            self.robot_final_loc = [Loc.get_pose()["x"], Loc.get_pose()["y"], math.radians(Loc.get_pose()["yaw"])]
            # self.robot_final_loc = [Loc.get_position()[0], Loc.get_position()[1], math.radians(Loc.get_angle()[0])]
            # 将贝塞尔的路径数据传入scriptData
            ScriptData.set("goBezier",{"bezier_path_world_return":self.bezier_path_world_return,
                                       "initial_point_world_return":self.initial_point_world_return,
                                       "robot_final_loc": self.robot_final_loc})
            log.info(f"bezier_path_world_return[0][-1]={self.bezier_path_world_return[0][-1]}")
        return self.action_status

    def reset(self):
        Navigation.resetPath()
        self.action_status = ScriptStatus.RUNNING

    def compute_bezier_controls_5th(self, p0, p5, alpha1=0.2, alpha2=0.2):
        x0, y0, th0 = p0
        x5, y5, th5 = p5

        dist = math.hypot(x5 - x0, y5 - y0)

        # 1阶控制点距离
        d1 = alpha1 * dist
        # 2阶控制点距离
        d2 = alpha2 * dist

        p1 = [x0 + d1 * math.cos(th0), y0 + d1 * math.sin(th0)]
        p2 = [x0 + d2 * math.cos(th0), y0 + d2 * math.sin(th0)]

        p4 = [x5 + d1 * math.cos(th5), y5 + d1 * math.sin(th5)]
        p3 = [x5 + d2 * math.cos(th5), y5 + d2 * math.sin(th5)]

        return p0, p1, p2, p3, p4, p5

    def bezier_points(self, p0, p1, p2, p3, p4, p5, steps=1000):
        """
        生成五次 (6 控制点) Bezier 曲线采样点
        :param
            p0~p5 : [x, y]
            steps : 采样分段数，返回 steps+1 个点
        :return
            (xs, ys)
        """
        xs, ys = [], []
        for i in range(steps + 1):
            t = i / steps
            one_t = 1 - t

            # 五次 Bezier 伯恩斯坦基函数
            b0 = one_t ** 5
            b1 = 5 * one_t ** 4 * t
            b2 = 10 * one_t ** 3 * t ** 2
            b3 = 10 * one_t ** 2 * t ** 3
            b4 = 5 * one_t * t ** 4
            b5 = t ** 5

            # 计算坐标
            x = (b0 * p0[0] + b1 * p1[0] + b2 * p2[0] +
                 b3 * p3[0] + b4 * p4[0] + b5 * p5[0])
            y = (b0 * p0[1] + b1 * p1[1] + b2 * p2[1] +
                 b3 * p3[1] + b4 * p4[1] + b5 * p5[1])

            xs.append(x)
            ys.append(y)

        return xs, ys

    def bezier_curvature(self, p0, p1, p2, p3, p4, p5, steps=500):
        """
        基于导数计算五次贝塞尔曲线最大曲率
        p0~p5: 控制点[x, y]
        return 最大曲率
        """
        k_max = 0.0

        for i in range(steps + 1):
            t = i / steps
            one_t = 1 - t

            # 一阶导数 dx/dt, dy/dt
            dx_dt = 5 * (
                    (p1[0] - p0[0]) * one_t ** 4 +
                    4 * (p2[0] - p1[0]) * one_t ** 3 * t +
                    6 * (p3[0] - p2[0]) * one_t ** 2 * t ** 2 +
                    4 * (p4[0] - p3[0]) * one_t * t ** 3 +
                    (p5[0] - p4[0]) * t ** 4
            )
            dy_dt = 5 * (
                    (p1[1] - p0[1]) * one_t ** 4 +
                    4 * (p2[1] - p1[1]) * one_t ** 3 * t +
                    6 * (p3[1] - p2[1]) * one_t ** 2 * t ** 2 +
                    4 * (p4[1] - p3[1]) * one_t * t ** 3 +
                    (p5[1] - p4[1]) * t ** 4
            )

            # 二阶导数 ddx/dt, ddy/dt
            ddx_dt = 20 * (
                    (p2[0] - 2 * p1[0] + p0[0]) * one_t ** 3 +
                    3 * (p3[0] - 2 * p2[0] + p1[0]) * one_t ** 2 * t +
                    3 * (p4[0] - 2 * p3[0] + p2[0]) * one_t * t ** 2 +
                    (p5[0] - 2 * p4[0] + p3[0]) * t ** 3
            )
            ddy_dt = 20 * (
                    (p2[1] - 2 * p1[1] + p0[1]) * one_t ** 3 +
                    3 * (p3[1] - 2 * p2[1] + p1[1]) * one_t ** 2 * t +
                    3 * (p4[1] - 2 * p3[1] + p2[1]) * one_t * t ** 2 +
                    (p5[1] - 2 * p4[1] + p3[1]) * t ** 3
            )

            # 曲率公式
            numerator = abs(dx_dt * ddy_dt - dy_dt * ddx_dt)
            denominator = (dx_dt ** 2 + dy_dt ** 2) ** 1.5
            if denominator == 0:
                continue

            k = numerator / denominator
            k_max = max(k_max, k)

        return k_max


class GoBezierWorldReturn:
    """
        走记录过的贝塞尔曲线返回的路径
    """
    def __init__(self, is_backwards=True, is_hold_dir=None, max_speed=0.3, max_accele=1, max_decele=0.7, decele_dist=0.1):
        self.end_position_world = [0,0,0]
        self.end_position_robot = [0,0,0]
        self.action_name = self.__class__.__name__

        self.go_bezier_data = None
        self.bezier_target_pos_return = None
        self.bezier_path_world_return = None
        self.go_bezier_final_pos = None

        self.is_backwards = is_backwards
        self.is_hold_dir = is_hold_dir
        self.max_speed = max_speed
        self.max_accele = max_accele
        self.max_decele = max_decele
        self.decele_dist = decele_dist

        self.action_status = ScriptStatus.NONE
        self.init = True
        self.target_robot = [0, 0, 0]
        self.robot_loc = [0, 0, 0]
        self.control_point = None
        self.param = {}
        self.is_set_min_speed = False
        # 第一段线到位标识
        self.is_first_path_reached = False

    def run(self):
        self.action_status = ScriptStatus.RUNNING
        if self.init:
            self.init = False
            # self.go_bezier_data = json.loads(ScriptData.get("goBezier")) #后续在ScriptData.get格式改为dict后删除json.loads
            self.go_bezier_data = ScriptData.get("goBezier") #后续在ScriptData.get格式改为dict后删除json.loads
            self.bezier_target_pos_return = self.go_bezier_data["initial_point_world_return"]
            self.bezier_path_world_return = self.go_bezier_data["bezier_path_world_return"]
            self.go_bezier_final_pos = self.go_bezier_data["robot_final_loc"]
            self.robot_loc = [Loc.get_pose()["x"], Loc.get_pose()["y"], math.radians(Loc.get_pose()["yaw"])]
            # self.robot_loc = [Loc.get_position()[0], Loc.get_position()[1], math.radians(Loc.get_angle()[0])]
            dist_bias = math.sqrt((self.go_bezier_final_pos[0] - self.robot_loc[0])**2 + (self.go_bezier_final_pos[1] - self.robot_loc[1])**2)
            if dist_bias >= 0.1:
                self.action_status = ScriptStatus.FAILED

            # 规划第一段倒退路线参数
            Navigation.resetPath()
            Navigation.setPathReachAngle(0.05)  # 到位精度
            Navigation.setPathReachDist(0.01)
            Navigation.setPathBackMode(self.is_backwards)  # 设置正走倒走
            if self.is_hold_dir:
                Navigation.setPathHoldDir(self.is_hold_dir) # 用于全向车
            Navigation.setPathMaxSpeed(self.max_speed)
            Navigation.setPathMaxRot(10)
            Navigation.setPathOnWorld(self.bezier_path_world_return[0], self.bezier_path_world_return[1],
                                      self.bezier_path_world_return[2])
            self.param["maxAcc"] = float(self.max_accele)
            self.param["maxDec"] = float(self.max_decele)
            Navigation.goPathParam(self.param)

        if not self.is_first_path_reached and self.action_status != ScriptStatus.FAILED: # 走第一段路线到曲率合适的贝塞尔起点
            self.is_first_path_reached = Navigation.isPathReached()
            if self.is_first_path_reached:
                Navigation.resetPath()
                Navigation.setPathReachAngle(0.05)
                Navigation.setPathReachDist(0.01)
                Navigation.setPathBackMode(not self.is_backwards)
                if self.is_hold_dir:
                    Navigation.setPathHoldDir(self.is_hold_dir)  # 用于全向车
                Navigation.setPathMaxSpeed(self.max_speed)
                Navigation.setPathOnWorld([0, self.bezier_target_pos_return[0]], [0, self.bezier_target_pos_return[1]],
                                          self.bezier_target_pos_return[2])
                self.param["maxAcc"] = float(self.max_accele)
                self.param["maxDec"] = float(self.max_decele)
                Navigation.goPathParam(self.param)

        if self.is_first_path_reached and self.action_status != ScriptStatus.FAILED: # 走贝塞尔到终点
            is_reached = Navigation.isPathReached()
            if is_reached:
                ScriptData.set("goBezier", {})
                self.action_status = ScriptStatus.FINISHED
            else:
                self.action_status = ScriptStatus.RUNNING

            robot_current_loc = [Loc.get_pose()["x"], Loc.get_pose()["y"], math.radians(Loc.get_pose()["yaw"])]
            # robot_current_loc = [Loc.get_position()[0], Loc.get_position()[1], math.radians(Loc.get_angle()[0])]
            dist_cur_loc_end_loc = math.hypot(
                self.end_position_world[0] - robot_current_loc[0],
                self.end_position_world[1] - robot_current_loc[1]
            )
            if dist_cur_loc_end_loc < self.decele_dist and not self.is_set_min_speed:
                self.is_set_min_speed = True
                Navigation.setPathMaxSpeed(0.15)

        return self.action_status

    def reset(self):
        self.action_status = ScriptStatus.RUNNING
        Navigation.resetPath()

def main():
    Module.init()
    ap_world_pos = Navigation.getLM("LM3", True)  # AP在世界坐标系下的位置
    go_bezier = GoBezierWorld(ap_world_pos,0,2,0.2,True)
    go_bezier_return = GoBezierWorldReturn(False)
    bezier_status = ScriptStatus.NONE
    bezier_return_status = ScriptStatus.NONE
    action_status = ScriptStatus.RUNNING
    while True:
        # 脚本任务状态管理
        if bezier_status in (ScriptStatus.NONE, ScriptStatus.RUNNING):
            bezier_status= go_bezier.run()
            log.info(f"bezier_status={bezier_status}")
        elif bezier_status == ScriptStatus.FAILED:
            action_status = ScriptStatus.FAILED
        elif bezier_status == ScriptStatus.FINISHED:
            if bezier_return_status in (ScriptStatus.NONE, ScriptStatus.RUNNING):
                bezier_return_status = go_bezier_return.run()
            elif bezier_return_status == ScriptStatus.FAILED:
                action_status = ScriptStatus.FAILED
            elif bezier_return_status == ScriptStatus.FINISHED:
                action_status = ScriptStatus.FINISHED
        Module.set_status(action_status)
        time.sleep(0.1)


if __name__ == '__main__':
    from syspy import Logger

    log = Logger("goBezier.py")
    main()