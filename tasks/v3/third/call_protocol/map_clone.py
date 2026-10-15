from syspy import Map


def query_sites():
    """查询当前 workspace 绑定的地图下所有 className 为 "SwitchMap" 的站点。

    返回:
        list[dict]: 站点原始数据列表; 无有效 workspace 时返回 []。
    """
    workspace = Map.getCurrentWorkspace()
    print(f"当前地图绑定的 workspace: {workspace}")

    if not workspace:
        print("错误：当前没有有效的 workspace，无法继续。")
        return []

    map_name = Map.getMapNameByWorkspace(workspace)
    print(f"workspace '{workspace}' 绑定的地图名: {map_name}")

    site_list = Map.getSiteDataList(
        workspace=workspace
        # class_name="SwitchMap"          # 只筛选 SwitchMap 类型站点
    )
    print(f"\n共找到 {len(site_list)} 个 SwitchMap 站点：")
    return site_list


def print_sites(site_list):
    """打印站点列表的字段信息。"""
    for idx, site in enumerate(site_list, 1):
        print(f"\n--- SwitchMap 站点 {idx} ---")
        print(f"  className    : {site.get('className')}")
        print(f"  instanceName : {site.get('instanceName')}")
        print(f"  pointName    : {site.get('pointName')}")
        print(f"  workspace    : {site.get('workspace')}")
        print(f"  mapName      : {site.get('mapName')}")
        print(f"  坐标 (x, y)   : ({site.get('x')}, {site.get('y')})")
        print(f"  朝向 dir     : {site.get('dir')}")
        print(f"  尺寸 (宽,长,高): ({site.get('width')}, {site.get('length')}, {site.get('height')})")
        if site.get('jsonObject'):
            print(f"  扩展 JSON    : {site.get('jsonObject')}")


def resolve_scene():
    """判断当前是单楼层还是跨楼层场景, 返回 (mode, workspace, map_name)。

    - 跨楼层: 拓扑里能把当前地图对应到唯一的 workspace, 此时
      getCurrentWorkspace() 返回非空, 该 workspace 就是站点/导航要用的。
    - 单楼层: 地图没有绑定 workspace, getCurrentWorkspace() 为空, 只能靠
      getCurrentMapName() 定位当前地图; workspace 留空, 导航任务里不下发该
      字段 (见 navigation.build_working_tasks)。

    mode 取 "crossFloor" / "singleFloor" / "unavailable"(地图不可用)。
    """
    workspace = ""
    map_name = ""
    try:
        workspace = str(Map.getCurrentWorkspace() or "").strip()
    except Exception as error:
        print("读取当前 workspace 失败: {}".format(error))
    try:
        map_name = str(Map.getCurrentMapName() or "").strip()
    except Exception as error:
        print("读取当前地图名失败: {}".format(error))

    if workspace:
        return "crossFloor", workspace, map_name
    if map_name:
        return "singleFloor", "", map_name
    return "unavailable", "", ""


def _site_list(workspace, map_name):
    """查一张地图的 CallButton 站点; 取不到返回 []。

    跨楼层必须走按地图名读接口 (getCallButtonList / getMapDataList): 它们直接
    读目标地图的 0.smap 文件, 所以能取到非当前楼层。
    getSiteDataList 只覆盖"当前已加载的那张地图", 站点上的 workspace/mapName
    是它按当前地图盖的戳; 拿别的楼层的 workspace 去过滤, 一条都匹配不上,
    这就是跨楼层查不到的原因。因此它只作为最后兜底。
    """
    sites = []
    try:
        if map_name and hasattr(Map, "getCallButtonList"):
            sites = Map.getCallButtonList(map_name) or []
        elif map_name and hasattr(Map, "getMapDataList"):
            sites = Map.getMapDataList("callButtonList", map_name) or []
        else:
            # 兜底: 无地图名, 或机器人上的 syspy 还没有按地图名读的接口。
            if map_name:
                print("警告: syspy 无按地图名读站点的接口, 地图 '{}' "
                      "只能查当前地图, 结果可能不完整".format(map_name))
            sites = Map.getSiteDataList(
                workspace = workspace,
                class_name = "CallButton"
            ) or []
    except Exception as error:
        print("查询地图 (workspace={} map={}) 站点失败: {}".format(
            workspace, map_name, error))
        return []

    buttons = []
    for site in sites:
        # 按地图名读接口不保证回填 className, 没有该字段时按类型命中处理。
        class_name = str(site.get("className") or "")
        if class_name and class_name.lower() != "callbutton":
            continue
        buttons.append(dict(site))
    return buttons


def _collect_buttons(workspace, map_name, button_list):
    """把一张地图查到的 CallButton 补全 workspace/mapName 后并入结果。"""
    buttons = _site_list(workspace, map_name)
    for site in buttons:
        # 站点列表不一定回填这两个字段, 用查询上下文补上
        if not site.get("workspace"):
            site["workspace"] = workspace
        if not site.get("mapName"):
            site["mapName"] = map_name
        button_list.append(site)
    return buttons


def query_call_buttons():
    """按场景查出所有 CallButton 站点。

    - 跨楼层: 遍历工作空间列表 (Map.getWorkspaceList), 逐张地图查;
    - 单楼层: 地图没有 workspace, 只查 getCurrentMapName() 返回的当前地图,
      站点的 workspace 字段保持为空, 导航时由调用方走兜底 workspace。

    返回:
        list[dict]: 呼叫器站点列表, 每项含 pointName(被呼叫后前往的目标站点名);
                    取不到时返回 []。
    """
    mode, workspace, map_name = resolve_scene()
    print("地图场景: {}  workspace={}  map={}".format(
        mode, workspace or "(无)", map_name or "(无)"))

    button_list = []
    if mode == "singleFloor":
        # 单楼层: 只查当前地图, 不能依赖 workspace 过滤 (传空即不过滤)。
        buttons = _collect_buttons("", map_name, button_list)
        print("单楼层地图 '{}' 共 {} 个 CallButton 站点".format(map_name, len(buttons)))
        print("共找到 {} 个 CallButton 站点:".format(len(button_list)))
        return button_list

    if mode == "unavailable":
        print("错误：既取不到 workspace 也取不到地图名，无法查询站点。")
        return []

    # 跨楼层: workspace 非空, 遍历拓扑里的工作空间逐张地图查。
    try:
        if not hasattr(Map, "getWorkspaceList"):
            raise AttributeError("syspy 无 getWorkspaceList 接口")
        workspace_list = Map.getWorkspaceList() or []
    except Exception as error:
        print("读取工作空间列表失败: {}".format(error))
        workspace_list = []
    # 拓扑读不到时兜底查当前地图, 否则整个功能会因为一次读文件失败而停摆。
    if not workspace_list:
        print("工作空间列表为空, 退回只查当前地图 (workspace={})".format(workspace))
        _collect_buttons(workspace, map_name, button_list)
        print("共找到 {} 个 CallButton 站点:".format(len(button_list)))
        return button_list

    print("\n共 {} 个工作空间(地图):".format(len(workspace_list)))
    for item in workspace_list:
        print("  workspace={}  map={}".format(item.get("workspace"), item.get("map")))

    for item in workspace_list:
        item_workspace = item.get("workspace")
        item_map_name = item.get("map")
        if not item_workspace or not item_map_name:
            print("\n跳过: workspace={} map={}".format(item_workspace, item_map_name))
            continue

        # 站点列表要按地图名取, 不能只查当前地图(跨楼层查不到)
        buttons = _collect_buttons(item_workspace, item_map_name, button_list)
        print("\n地图 '{}' (workspace={}) 找到 CallButton {} 个".format(
            item_map_name, item_workspace, len(buttons)))

    print("\n共找到 {} 个 CallButton 站点:".format(len(button_list)))
    return button_list


def print_buttons(button_list):
    """打印呼叫器站点的字段信息, 重点是 pointName 和 workspace。"""
    for idx, site in enumerate(button_list, 1):
        print(f"\n--- CallButton 站点 {idx} ---")
        print(f"  pointName    : {site.get('pointName')}      <- 目标站点名")
        print(f"  workspace    : {site.get('workspace')}      <- 所属工作区")
        print(f"  className    : {site.get('className')}")
        print(f"  instanceName : {site.get('instanceName')}")
        print(f"  channel      : {site.get('loraChannel')}")
        print(f"  address      : {site.get('loraAddress')}")
        print(f"  mapName      : {site.get('mapName')}")
        print(f"  坐标 (x, y)   : ({site.get('x')}, {site.get('y')})")
        print(f"  朝向 dir     : {site.get('dir')}")
        if site.get('jsonObject'):
            print(f"  扩展 JSON    : {site.get('jsonObject')}")


def main():
    # print_sites(query_sites())
    print_buttons(query_call_buttons())


if __name__ == "__main__":
    main()
