# -*- coding: utf-8 -*-
from syspy import _TR
from syspy.utils.param_server import ParamType

from standard.fork_utils import (
    create_end_height_param,
    create_rec_param,
    create_start_height_param,
)
from standard.fork import HeavyFork, cage_stack_config_builder, cage_stack_config_reload


class StraddleLiftFork(HeavyFork):
    falling_down_detect_default = True
    config_builder_hook = staticmethod(cage_stack_config_builder)
    config_reload_hook = staticmethod(cage_stack_config_reload)

    @staticmethod
    def extend_custom_operation_inputs(input_cls, builder, min_height: float, max_height: float):
        with builder.CHILD(key="cageStack", name=_TR("Cage Stack"), desc=_TR("Stack the cage")):
            builder.TYPE(ParamType.ARRAY)
            with builder.CHILDREN():
                create_start_height_param(builder, min_height, max_height)
                create_end_height_param(builder, min_height, max_height)
                create_rec_param(builder, input_cls.extend_recognize_on_params)

    @classmethod
    def custom_action_templates(cls):
        return [
            {"action_name": _TR("Cage Stack"), "operation": "cageStack", "stage": 3},
        ]

    def custom_operations(self):
        return {
            "cageStack": self.cage_stack,
        }

    def custom_cleanup_operations(self):
        return {"cageStack"}


robot = StraddleLiftFork(__file__)


if __name__ == "__main__":
    robot.main()
