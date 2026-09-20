# -*- coding: utf-8 -*-
import syspy
from standard.fork import Fork
from standard.fork_utils import GoodsAwareForkMotorByPosition


class PickFork(Fork):
    fork_count_enabled = True
    use_recfile_collision_policy = True
    # 夹抱车叉车电机为载货感知实现
    fork_motor_action_class = GoodsAwareForkMotorByPosition
    # 夹抱车无 lift 电机点动
    lift_jog_support = False


robot = PickFork(__file__)


if __name__ == "__main__":
    robot.main()
