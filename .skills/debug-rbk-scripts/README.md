# RBK Script Debugging Skill

诊断 RBK 3.x 机器人脚本、RPC、导航、定位、地图与设备问题的排查手册（agent skill）。
**发现问题、补充通道、修正流程，请直接提 PR**。

## 这个 skill 解决什么

给 AI agent（以及人）一套固定排障路径：

1. **先问时间**：任何 RBK 问题都需要一个具体故障时间窗口（含时区）。
2. **再选通道**：按症状选择 trace category/channel，而不是盲目 grep。
3. **定位到第一跳**：用 `Rc`/`Rs` 证明是 SDK 没发、还是脚本没收，再谈业务逻辑。
4. **保留证据**：可复现地采集 trace、日志、taskId。

## 快速开始

```bash
# 1) 先拿时间窗口，生成排查计划（只读，不改机器人状态）
./scripts/rbk-triage.sh --at '2026-09-29 13:47:00' --symptom script --task-id 42

# 2) 按计划执行 ptcat / 日志过滤
# 3) 需要归档证据时
./scripts/collect-rbk-evidence.sh --out /tmp/rbk-evidence --task-id 42 --copy-trace
```

`symptom` 取值：`script` | `nav` | `loc` | `map` | `device` | `crash` | `latency`。

## 目录结构

```text
SKILL.md                      # agent 主入口：triage -> 详细流程 -> 安全红线
references/
  triage.md                   # 时间窗口 + 症状到通道路由（最先读）
  tracing.md                  # insightd / ptcat / 证据固化
  mf-script-rpc.md            # MoveFactory <-> PyIDE <-> syspy RPC 链路
  script-debugging.md         # 脚本/电机/fork/容器排查
  message-latency.md          # DI/传感器/消息延迟测量
  standalone-probes.md        # 不经 MF/PyIDE，用 python3 直接跑脚本探测
  http-api.md                 # RBK HTTP OpenAPI MCP 工作流
scripts/
  rbk-triage.sh               # 由时间窗口生成 ptcat/日志命令
  collect-rbk-evidence.sh     # 固化可交付证据包
agents/openai.yaml            # skill 元信息
```

## 通道速查

| 症状 | Category / channel |
| --- | --- |
| 脚本逻辑 / 脚本下发 / RPC | `rbk.script.utils_rpc` / `Rc` `RcError` `Rs` `RsError` |
| 脚本自定义通道（fork/actions/elevator…） | `rbk.script.utils_rpc` / `<通道名>` |
| 导航、动作编排、`/navigate` 卡住 | `rbk.nav.MoveFactory` |
| 定位、漂移、置信度 | `rbk.loc.MCLoc` |
| 地图加载/切换 | `rbk.loc.BlockMapLoader` / `changeMap` |
| 电机、DI/DO、传感器、电池 | `rbk.device.DSPChassis` |
| RBK 整体崩溃 | `syslog` |
| 脚本进程崩溃 | `logs/ide/*.log` → `logs/scripts/*.log` |
| 单独验证脚本/syspy 改动 | 用 `python3` 直连 RBK，见 [`references/standalone-probes.md`](references/standalone-probes.md) |

权威通道表随 SDK 发布为 `trace.cfg`。位置因机器而异，请用查找而非写死路径：

```bash
find "$HOME" /opt /srv /data -maxdepth 8 -name trace.cfg 2>/dev/null | head
```

找不到时，默认资源路径 `/opt/.data/rbk/resources/` 与实时 trace 仍可发现通道；仍不确定
则向使用者索取 SDK 路径或版本。

## 关键路径

```text
Trace:       /opt/.data/diagnosis/rbk/trace/event/rbk+common_*.pft.zst
Report:      /opt/.data/diagnosis/rbk/trace/event/rbk+report.jsonl
PyIDE 日志:  /opt/.data/diagnosis/rbk/logs/ide/ide_*.log
脚本日志:    /opt/.data/diagnosis/rbk/logs/scripts/<name>_*.log
运行资源:    /opt/.data/rbk/resources/{scripts,params,maps,devices,apps}
模型文件:    /opt/.data/rbk/resources/devices/robot.model
```

## 贡献指南

欢迎所有 RBK / SDK 相关同事改进：

- **新增通道**：若某版本 `trace.cfg` 有变化，更新 `references/triage.md` 的通道表，
  并注明版本。
- **修正路由**：如果某类问题的最优入口通道与文档不符，改 `triage.md` 的对照表并说明依据。
- **新增症状**：在 `triage.md`「Route by symptom class」补充一行，并链接到对应 reference。
- **脚本改进**：`scripts/*.sh` 保持只读规划/采集语义，不要新增修改机器人状态的副作用。

提交前：

```bash
bash -n scripts/*.sh
./scripts/rbk-triage.sh --at "$(date '+%Y-%m-%d %H:%M:%S')" --symptom script
```

PR 描述请写清楚：**依据的 RBK 版本、复现的故障、改动后如何更快定位**。

## 安全红线（摘录）

- `ss@pyCrashed` 是粘性状态，需要整体重启 RBK，不要反复改脚本。
- 停止脚本用 HTTP `/cancelNavigate`，不要 kill 常驻脚本进程。
- 不要为刷新日志而重启 RBK/insightd/traced，用 insightd `/sync`。
- 不要跨时钟域做减法（`dataNsec`/`perf_counter_ns` 与墙钟）。

完整列表见 `SKILL.md` 的 Non-Negotiable Safety Rules。
