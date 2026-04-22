# -*- coding: utf-8 -*-
"""
sim_only 使用示例
"""

from syspy import sim_only, is_simulation


def _mock_add(a: int, b: int) -> int:
    """
    仿真环境下 add_two_numbers 的替代实现
    tips: 建议保持与原函数同签名和类型注解，方便仿真环境的正确使用和类型检查
    """
    return 1000 + a + b


@sim_only(reason="真实设备接口，仿真默认跳过", skip_return=False)
def open_real_device() -> bool:
    """
    原函数逻辑示例，仿真环境默认跳过并返回 False
    """
    return True


@sim_only(on_sim=_mock_add)
def add_two_numbers(a: int, b: int) -> int:
    """
    原函数逻辑示例
    仿真环境执行 _mock_add，实机环境执行原函数
    """
    return a + b


if __name__ == "__main__":
    print("is_simulation =", is_simulation())
    print("open_real_device =", open_real_device())
    print("add_two_numbers(1, 2) =", add_two_numbers(1, 2))

