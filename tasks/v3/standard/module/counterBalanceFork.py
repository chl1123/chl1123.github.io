# -*- coding: utf-8 -*-
import syspy
from standard.fork import HeavyFork


class CounterBalanceFork(HeavyFork):
    falling_down_detect_default = True


robot = CounterBalanceFork(__file__)


if __name__ == "__main__":
    robot.main()
