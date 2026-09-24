# -*- coding: utf-8 -*-
from syspy import Trace
from syspy.lib.robot import RobotParam
from standard.fork import ConfigParams, Fork
from standard.fork_utils import (
    LiftForkMotorByPosition,
    clear_goods_shape_when_lift_fork_low,
)


def _lift_fork_period_run(robot, fork_height):
    clear_goods_shape_when_lift_fork_low(robot, fork_height, ConfigParams)


class LiftFork(Fork):
    fork_count_enabled = True
    lift_fork_model_limits = True
    period_run_hook = staticmethod(_lift_fork_period_run)
    # 搬运车叉车电机为二位式（按中间值自动判断到最高/最低）
    fork_motor_action_class = LiftForkMotorByPosition
    # 搬运车无 lift 电机点动
    lift_jog_support = False

    @staticmethod
    def on_device_model_param_loaded(cfg):
        """设备模型参数加载后：搬运车变轴距车型检测（依赖底盘类型，运行时从设备模型读取）。"""
        Trace.log(f"chassis_type:{cfg.chassis_type}", name="fork.cfg")
        if cfg.chassis_type in ("variableWheelbaseSingleStandardSteer", "variableWheelbaseSingleDifferentialSteer"):
            cfg.base_shift = True
            cfg.base_shift_length = float(
                RobotParam.getDevice("Model-000", f"chassisType.{cfg.chassis_type}.wheelBaseShiftLength") or 0
            )


robot = LiftFork(__file__, rec_check_qr=True)


if __name__ == "__main__":
    robot.main()
