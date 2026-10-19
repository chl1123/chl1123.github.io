# RBK 3.6.0 接口测试

只读接口测试，自动采样实际读数并生成 Markdown 报告。

## 快速开始

```bash
# 在 RBK 目标机器上（3.6.0.0026+）
cd /opt/.data/rbk/resources/scripts
./tests/run_tests.sh

# 查看报告
cat test-reports/latest.md
```

`run_tests.sh` 自动处理：
- 非 root 自动 `sudo` 重入（RBK IPC socket 属 root）；
- pytest 未安装时自动装到 `.test_deps/`，不污染系统 Python；
- 路径修复（symlink 安装下避开 syspy 的 `script path error`）；
- 禁用字节码写入（避免在仓库里留下 root 属主的 `__pycache__`）；
- 生成 Markdown 报告与逐用例日志。

## 运行指定用例

```bash
# 单个文件（注意：参数是相对仓库逻辑根的路径或绝对路径）
./tests/run_tests.sh tests/unit/test_battery.py
./tests/run_tests.sh /opt/.data/rbk/resources/scripts/tests/unit/test_battery.py

# 按关键词过滤
./tests/run_tests.sh -k battery

# pytest 参数透传
./tests/run_tests.sh -v -x
```

## 报告产物

- `test-reports/latest.md` —— 最近一次的 Markdown 报告；
- `test-reports/rbk-<版本>-<时间>.md` —— 带时间戳归档；
- `test-reports/results.log` —— 逐用例文本日志（失败详情在这里）。

报告分组在 `report.py` 的 `CATEGORY_BY_FILE` 里维护，新增测试文件时同步加一行。

## 覆盖范围（第一轮：只读接口）

| 文件 | 接口 | 说明 |
|---|---|---|
| test_battery.py | Battery | 12 个 getter + device_key 语义 |
| test_dio.py | Di / Do | 列表、maxNode、未知 key 行为 |
| test_loc.py | Loc | 位姿 / 置信度 / 定位状态 |
| test_odometer.py | Odometer | 位置 / 速度 / 里程 / 电机信息 |
| test_laser.py | Laser / Laser3D | 聚合读取 + 参数校验 |
| test_sound.py | Sound | 播放状态（只读） |
| test_map.py | Map | 地图名 / 站点 / 跨楼层 0.smap 读取 |
| test_navigation.py | NavStatus / NavSpeed | MoveStatus / NavSpeed + getTurn 纯逻辑 |
| test_controller.py | Controller | 控制器状态 |
| test_unsupported.py | Magnetic / Rfid / CodeScanner / Bin | 未迁移或未配置，只验证不抛异常 |

**刻意不测**（第二轮 dangerous 用例）：电机动、导航指令、声音播放、DO 写等会改变
机器人状态的接口。骨架已留好：`@pytest.mark.dangerous` + `RUN_DANGEROUS=1` 门控，
conftest 会自动跳过未启用的 dangerous 用例。

**dangerous 动作用例（需 `RUN_DANGEROUS=1`）**：

| 文件 | 内容 | 仿真可测性 |
|---|---|---|
| test_error_action.py | RobotError 注入/清除闭环、任务错误注入/清除、stopRobot(False) | ✅ 闭环可验证（已实测） |
| test_sound_action.py | 播放/停止循环、setSoundCount | ⚠️ 动作不抛异常可测；状态断言仅实车可观测 |

```bash
RUN_DANGEROUS=1 ./tests/run_tests.sh
```

错误 key 均带 `rbk-test-` 前缀且 finally 必清理；清理失败视为用例失败。

## 断言口径（全项目统一）

1. **不 assert 具体数值**：电量、温度、位置因车而异，只采样记录；
2. **空 str / 空 bytes 合法**：如 `getExtra()==''`、`getCanPort()==''`；
3. **-1 等语义值合法**：如 `SoH=-1` 表示无效；
4. **读不到（None）跳过而不是失败**：跳过原因分「未迁移/未配置」「前置不满足」「未启用」三类；
5. **仿真特例**：仿真没加载 DSPChassis，RPC 报「方法未注册」时跳过；实车上同类失败必须算失败。

## 已知行为备忘（来自联调）

- `Di.getDi / Do.getDo`：未知 key 返回 `False`，不抛异常——无法区分「无数据」和「状态为 False」；
- `Map` 点位接口：依赖当前地图名，无地图时会拼出 `/maps/0.smap` 抛 FileNotFoundError，属前置不满足；
- `Laser.getData(channel=...)` 与 `device_key` 互斥，传错会抛 `ValueError`（接口约定）。

## 扩展新接口

复制 `test_battery.py` 改名，在 `report.py` 的 `CATEGORY_BY_FILE` 加映射，用 `run_getter` 写
类型/范围断言即可；需要参数校验类断言的参考 `test_laser.py`。
