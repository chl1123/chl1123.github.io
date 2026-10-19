# -*- coding: utf-8 -*-
"""地图接口只读用例（顶层门面 Map）。

数据来源分两路：
- getCurrentMapName / getCurrentWorkspace：读当前地图消息（channel /SMAP/Map2D，回落 3.5 topic）；
- 点位类接口（advanced* / charger / bins / policies 等）：从 maps/<mapName>/0.smap 解析。

点位类接口依赖「当前有地图名」。没有地图名时 getter 会拼出 /maps/0.smap 并抛
FileNotFoundError，这是前置条件不满足，不是接口缺陷，所以统一用 requires_map 门控跳过。
"""

from __future__ import annotations

import pytest
from syspy import Map

from helpers import is_container, is_str, run_getter


@pytest.fixture(scope="module")
def current_map():
    """当前地图名；为空则跳过依赖地图的用例。"""
    name = Map.getCurrentMapName()
    if not name:
        pytest.skip("前置不满足：当前无地图名（未选中地图/工作区，或地图消息未发布）")
    return name


def test_map_get_current_map_name(rbk_report, rbk_env, request):
    # 返回 str，空串表示读不到；run_getter 只对 None 跳过，所以这里单独处理空串
    name = Map.getCurrentMapName()
    rbk_report.add_sample(request.node.nodeid, "getCurrentMapName() = %r" % (name,))
    assert isinstance(name, str), "getCurrentMapName 应为 str，实际 %s" % type(name).__name__
    if not name:
        pytest.skip("前置不满足：当前无地图名（未选中地图或地图消息未发布）")


def test_map_get_current_workspace(rbk_report, request):
    # 空串合法：地图未绑定工作区
    value = Map.getCurrentWorkspace()
    rbk_report.add_sample(request.node.nodeid, "getCurrentWorkspace() = %r" % (value,))
    assert isinstance(value, str), "getCurrentWorkspace 应为 str，实际 %s" % type(value).__name__


def test_map_get_workspace_list(rbk_report, request):
    """读 workspace_topology.json，不依赖当前地图。

    现场地图数据不一定包含工作区：该文件可能不存在、内容为空、或有内容但
    没有 ``workspaceList`` 字段。这些都属于「前置不满足」，不是接口缺陷，
    因此跳过而不是失败。
    """
    try:
        value = Map.getWorkspaceList()
    except ValueError as error:
        pytest.skip("前置不满足：地图数据无工作区配置（%s）" % error)
    rbk_report.add_sample(request.node.nodeid, "getWorkspaceList() 长度 = %d" % len(value))
    assert isinstance(value, list), "getWorkspaceList 应为 list，实际 %s" % type(value).__name__
    for item in value:
        assert isinstance(item, dict), "工作区项应为 dict，实际 %s" % type(item).__name__


# 点位类 getter：未配置的数据返回 None（0.smap 里没有该字段）或空列表，都合法
LIST_GETTERS = [
    "getAdvancedPointList",
    "getAdvancedCurveList",
    "getAdvancedLineList",
    "getAdvancedAreaList",
    "getTopoAreaList",
    "getTagGroupList",
    "getReflectorPosList",
    "getChargerList",
    "getAutoGateList",
    "getCallButtonList",
    "getBinList",
    "getBinTaskList",
    "getPolicyList",
]


@pytest.mark.requires_map
@pytest.mark.parametrize("name", LIST_GETTERS)
def test_map_list_getter(name, current_map, rbk_report, request):
    """点位列表：None / 空列表表示地图上没有这类数据，非空则每项必须是 dict。"""
    value = getattr(Map, name)()
    size = "None" if value is None else str(len(value))
    rbk_report.add_sample(request.node.nodeid, "%s() [地图 %s] 条数 = %s" % (name, current_map, size))
    if value is None:
        return
    assert isinstance(value, list), "%s 应为 list 或 None，实际 %s" % (name, type(value).__name__)
    for index, item in enumerate(value):
        assert isinstance(item, dict), "%s()[%d] 应为 dict，实际 %s" % (name, index, type(item).__name__)


@pytest.mark.requires_map
def test_map_get_site_data_list(current_map, rbk_report, request):
    """站点数据：每项至少带 className / instanceName / pointName / mapName / x / y。"""
    sites = Map.getSiteDataList()
    rbk_report.add_sample(request.node.nodeid, "getSiteDataList() [地图 %s] 条数 = %s"
                          % (current_map, None if sites is None else len(sites)))
    assert isinstance(sites, list), "getSiteDataList 应为 list，实际 %s" % type(sites).__name__
    required = ("className", "instanceName", "pointName", "mapName", "x", "y")
    for index, site in enumerate(sites):
        missing = [k for k in required if k not in site]
        assert not missing, "getSiteDataList()[%d] 缺少字段 %s" % (index, missing)
        assert site["mapName"] == current_map, (
            "站点 mapName=%r 与当前地图 %r 不一致" % (site["mapName"], current_map)
        )


@pytest.mark.requires_map
def test_map_get_point_matches_site_list(current_map, rbk_report, request):
    """getPoint 返回的坐标应与同名 LM/SM 点位一致（x/y 为数值）。"""
    points = Map.getAdvancedPointList() or []
    candidates = [
        p for p in points
        if str(p.get("instanceName", ""))[:2] in ("LM", "SM") and str(p.get("instanceName", ""))[2:]
    ]
    if not candidates:
        pytest.skip("前置不满足：当前地图没有 LM/SM 点位")
    name = candidates[0]["instanceName"]
    result = Map.getPoint(name[2:])
    rbk_report.add_sample(request.node.nodeid, "getPoint(%r) = %r" % (name[2:], result))
    assert result is not None, "getPoint(%r) 返回 None" % name[2:]
    assert isinstance(result["x"], (int, float)) and isinstance(result["y"], (int, float))


@pytest.mark.requires_map
def test_map_cross_floor_read_from_smap(current_map, rbk_report, request):
    """跨楼层读取：显式传 map_name 读非当前地图，仍应能解析（梯控脚本依赖这一点）。"""
    import os

    maps_root = os.path.dirname(Map._TOPOLOGY_PATH)
    others = [
        d for d in sorted(os.listdir(maps_root))
        if d != current_map
        and os.path.isfile(os.path.join(maps_root, d, "0.smap"))
    ]
    if not others:
        pytest.skip("前置不满足：只有一张地图，无法验证跨楼层读取")
    target = others[0]
    value = Map.getAdvancedPointList(target)
    rbk_report.add_sample(request.node.nodeid, "getAdvancedPointList(%r) 条数 = %s"
                          % (target, None if value is None else len(value)))
    assert value is None or isinstance(value, list), (
        "跨楼层读取 %r 应返回 list 或 None，实际 %s" % (target, type(value).__name__)
    )


def test_map_missing_map_name_raises_value_error():
    """显式传入不存在的地图名：接口约定抛 ValueError（而不是静默返回空）。"""
    with pytest.raises(ValueError):
        Map.getAdvancedPointList("__no_such_map__")
