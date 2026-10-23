# -*- coding: utf-8 -*-
"""电机状态接口只读用例（顶层门面 Motor / Odometer）。

背景：RBK 3.6 起电机状态改由逐电机 channel ``/MotorInfo/<deviceKey>`` 提供
（``msgMotorInfo``），``msgOdometer.motorInfo`` 已计划弃用。这里验证迁移后的
接口在真机/仿真上都能读到数据，且 3.6 的 ``msgMotorCmd`` 字段差异（``key``/
``value`` -> ``motorKey``/``motorName``）不会再让 ``getMotorSpeed`` 抛异常。

不 assert 具体数值：电机静止时 speed=0、位置因车而异。
"""

from __future__ import annotations

import pytest
from syspy import Motor, Odometer, RobotParam
from syspy.config import IS_RBK_VERSION_35

from helpers import is_container, is_float, is_int, run_getter


def _motor_keys():
    try:
        return list(RobotParam.getDeviceList("Motor") or [])
    except Exception:  # 老插件没有该 RPC
        return []


def test_motor_get_motor_infos(rbk_report, rbk_env, request):
    """Motor.getMotorInfos() 返回容器，且 3.6 下不应为空（读的是 /MotorInfo/<key>）。"""
    infos = run_getter(
        rbk_report, request.node.nodeid, "Motor.getMotorInfos()", Motor.getMotorInfos,
        is_container, "容器", simulation=rbk_env["simulation"],
    )
    if not IS_RBK_VERSION_35:
        assert len(infos) > 0, "RBK 3.6 下 /MotorInfo/<key> 应有数据，实际为空"


def test_motor_get_motor_infos_by_key(rbk_report, rbk_env, request):
    """传入 key 时只返回该电机，且元素 key 与入参一致。"""
    keys = _motor_keys()
    if not keys:
        pytest.skip("前置不满足：模型里没有 Motor 设备")
    key = keys[0]
    infos = Motor.getMotorInfos(key)
    rbk_report.add_sample(request.node.nodeid, "Motor.getMotorInfos(%r) = %d 条" % (key, len(infos)))
    assert len(infos) <= 1
    for info in infos:
        assert info.key == key


def test_motor_get_motor_info(rbk_report, rbk_env, request):
    """getMotorInfo(key) 返回 msgMotorInfo 或 None；存在的电机必须有 key。"""
    keys = _motor_keys()
    if not keys:
        pytest.skip("前置不满足：模型里没有 Motor 设备")
    for key in keys[:2]:
        motor = Motor.getMotorInfo(key)
        rbk_report.add_sample(request.node.nodeid, "Motor.getMotorInfo(%r) = %r" % (key, motor))
        if motor is not None:
            assert motor.key == key
            # 3.6 的 /MotorInfo/<key> 消息应带 message_header
            assert motor.header is not None


def test_motor_get_motor_info_unknown_key():
    """未配置的 key 返回 None，而不是抛异常。"""
    assert Motor.getMotorInfo("Motor-not-exist") is None


def test_motor_get_motor_info_rejects_channel_path():
    """传 channel 路径属于误用，应显式报错而不是静默返回 None。"""
    with pytest.raises(ValueError):
        Motor.getMotorInfo("/MotorInfo/Motor-000")


def test_motor_speed_and_pos(rbk_report, rbk_env, request):
    """getMotorPos / getMotorSpeed 返回数值（3.6 曾因 msgMotorCmd 缺 key 抛异常）。"""
    keys = _motor_keys()
    if not keys:
        pytest.skip("前置不满足：模型里没有 Motor 设备")
    def _is_number(value):
        # 位置/速度可能来自 protobuf float（float）或整型指令值（int），-1 表示读不到
        return is_float(value) or is_int(value)

    for key in keys[:2]:
        pos = run_getter(
            rbk_report, request.node.nodeid, "Motor.getMotorPos(%r)" % key,
            lambda k=key: Motor.getMotorPos(k), _is_number, "数值", simulation=rbk_env["simulation"],
        )
        speed = run_getter(
            rbk_report, request.node.nodeid, "Motor.getMotorSpeed(%r)" % key,
            lambda k=key: Motor.getMotorSpeed(k), _is_number, "数值", simulation=rbk_env["simulation"],
        )
        assert pos != -1 or speed != -1  # 两者同为 -1 说明这个 key 没被任何来源识别


def test_motor_control_mode(rbk_report, rbk_env, request):
    """getMotorControlMode 返回 int；proto 里还没有 controlMode 字段时返回 -1。"""
    keys = _motor_keys()
    if not keys:
        pytest.skip("前置不满足：模型里没有 Motor 设备")
    key = keys[0]
    mode = Motor.getMotorControlMode(key)
    rbk_report.add_sample(request.node.nodeid, "Motor.getMotorControlMode(%r) = %r" % (key, mode))
    assert is_int(mode)
    if IS_RBK_VERSION_35:
        assert mode == -1
    else:
        assert mode == -1 or 0 <= mode <= 10  # msgMotorInfo.mode 的枚举范围


def test_odometer_get_data_motor_info(rbk_report, rbk_env, request):
    """兼容老读法：Odometer.getData()["motorInfo"] 在 3.6 下也来自 /MotorInfo channel。"""
    data = Odometer.getData()
    rbk_report.add_sample(request.node.nodeid, "Odometer.getData() motorInfo = %r"
                          % [m.get("key") for m in data.get("motorInfo", [])])
    if not data:
        pytest.skip("前置不满足：Odometer 无数据")
    motor_info = data.get("motorInfo", [])
    assert isinstance(motor_info, list)
    if IS_RBK_VERSION_35:
        pytest.skip("3.5 仍读 msgOdometer.motorInfo")
    assert sorted(m.get("key") for m in motor_info) == sorted(
        m.key for m in (Motor.getMotorInfos() or []))
    # 老脚本依赖字段：key / calib / stop
    for item in motor_info[:1]:
        assert "key" in item
    assert set(Odometer.getData(["motorInfo"]).keys()) <= {"motorInfo"}


def test_odometer_motor_infos_delegates(rbk_report, rbk_env, request):
    """Odometer.getMotorInfos() 在 3.6 下应转发到 /MotorInfo channel，结果与 Motor 一致。"""
    odo_infos = run_getter(
        rbk_report, request.node.nodeid, "Odometer.getMotorInfos()",
        Odometer.getMotorInfos, is_container, "容器", simulation=rbk_env["simulation"],
    )
    if IS_RBK_VERSION_35:
        pytest.skip("3.5 无 /MotorInfo channel，仍读 msgOdometer.motorInfo")
    motor_keys = sorted(m.key for m in (Motor.getMotorInfos() or []))
    odo_keys = sorted(m.key for m in odo_infos)
    assert odo_keys == motor_keys
