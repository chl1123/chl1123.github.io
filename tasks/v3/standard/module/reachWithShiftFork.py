# -*- coding: utf-8 -*-
import syspy
from standard.fork import ReachFork


class ReachWithShiftFork(ReachFork):
    pass


robot = ReachWithShiftFork(__file__)


if __name__ == "__main__":
    robot.main()
