# -*- coding: utf-8 -*-
import syspy
from standard.fork import Fork
from standard.fork_utils import GoodsAwareForkMotorByPosition


class SingleFork(Fork):
    fork_count_enabled = True
    # 单叉车叉车电机为载货感知实现
    fork_motor_action_class = GoodsAwareForkMotorByPosition


robot = SingleFork(__file__)


if __name__ == "__main__":
    robot.main()
