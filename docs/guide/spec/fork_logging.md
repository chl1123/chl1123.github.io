# 叉车脚本日志重构规格

> 适用范围：`tasks/v3/standard/fork.py`、`tasks/v3/standard/fork_utils.py` 及 `tasks/v3/standard/module/` 下的叉车车型脚本。
> 公共约束以 [Module 日志记录规范](logging.md) 和 [ActionTask 开发指南](../development/action_task.md) 为准，本文只定义叉车特有的补充与收敛项。

## 1. 背景与目标

叉车脚本经过多轮车型扩展（`pickFork`、`liftFork`、`singleFork`、`straddleLiftFork`、`reachFork` 等），日志已经能覆盖大部分执行过程，但通道语义、字段类型和生命周期边界不统一，导致现场用 trace 还原任务时经常需要交叉比对代码才能确定"当时下发的是什么"。

本次重构的目标是建立一套可按**任务 → 阶段 → 动作 → 电机**四层还原现场执行的日志协议，重点覆盖：

1. 脚本级生命周期：任务接收、参数校验、启动、暂停、恢复、取消、超时、完成、失败。
2. 阶段级生命周期：当前处于取货、放货、识别、进叉、退叉、离库位、货叉升降等哪个阶段。
3. 动作级生命周期：动作入队、启动、状态变化、完成、失败、耗时、失败原因。
4. 电机级生命周期：命令下发、目标位置、当前位置、方向、速度、限位 DI、到位、停止、超时。
5. 机构级状态：货叉高度、货物状态、最小安全高度、到位标志、联动电机同步状态。
6. **策略级生命周期**：导航避障策略的下发、覆盖、恢复与清除，以及策略值的三层来源。
7. 参数与决策：原始参数、归一化参数、关键默认值、限幅值和最终执行参数。

非目标：

- 不改变动作控制语义、状态机业务分支和硬件时序。
- 不把完整点云、完整容器对象、完整识别结果或大数组放入日志。
- 不依赖 `print()`，不新增拼接 `taskId` / `actionId` / 时间戳的动态通道名。

## 2. 现状审计

### 2.1 已有基础

- `ForkActionQueue` 继承 `syspy/lib/action_task.py` 的 `ActionTask`，已具备 `taskBuild` / `taskExtend` / `actionStateChanged` / `taskFinished` / `taskFailed` 协议能力，并已向 `fork.taskActions` 通道落盘。
- `ActionBase` 能自动生成 `actionParameters` 摘要，可选覆写 `result_description()`。
- `OperationFlow` 已将 operation 的批次推进从车型逻辑中抽出。
- `Fork.period_run()` 已按固定周期写 `fork.task` / `fork.motor` 数值快照，并经 `self.*_trace_channel` 属性下发，通道名可被车型覆写。
- 多数电机动作具备 `_trace_state()`，可用于动作级状态快照。
- `RunMotorByPosition` 已维护动作开始时间、当前位置、目标位置、到位检查和复位逻辑。
- `elevator.py` 已落地结构化策略通道 `elevator.policy`，可作为跨车型先例。

### 2.2 主要问题

**（1）通道语义重叠。** `fork.task` 同时承载任务快照、阶段日志、导航日志、参数、识别结果、clear region 和电机事件；`fork.script` 写的是动作队列状态快照，与 `fork.task` 字段高度重叠，脚本生命周期与动作队列生命周期边界不清。`fork.nav` 的 4 处写入中，有 2 处实际是策略下发日志（`vx:{vx},set forward policy:{...}`）。

**（2）Action 事件存在重复写。** `ActionTask` 基础设施已向 `fork.taskActions` 落盘，但业务代码仍在 8 处显式写 `fork.action`，同一批动作事件被记了两遍，且两套字段并不一致。

**（3）裸通道残留。** 有 8 处 `Trace.log` 未指定 `name`，落入运行时默认通道，无法按通道筛选。其中 7 处在 `LiveRec` 相关动作内，1 处在叉车计数逻辑内。

**（4）结构化与文本混用。** 同一类事件时而字符串拼接（`motor=..., position=...`），时而结构化 dict；同一语义存在 `position`、`target_position`、`forkHeight`、`cur_fork_height` 等多种命名；单位、方向、状态和耗时隐含在文本中，分析器无法稳定解析。

**（5）生命周期不完整。** Action 队列有标准生命周期，但脚本、阶段、策略三层没有统一事件。`set_status()` 只记录状态迁移文本，未同时记录 `taskId`、operation、当前 action、耗时和原因。`OperationFlow` 的批次推进、生成器 `yield`、动作队列替换之间缺少关联标识。

**（6）耗时信息不完整。** ActionTask 终态有 `elapsedMs`，但电机命令、识别、导航、阶段和脚本任务不一致。电机超时日志有 timeout，但缺少统一的 `elapsedMs`、起始位置、目标位置、最后位置和限位状态。

**（7）参数可追溯性不足。** `_init_args()` 会从多来源读取参数并做默认、类型转换和限幅，但只有零散的 `script args` / `move task` / `check ok, args` 日志，无法稳定区分**原始入参、归一化参数、平台配置值、最终下发参数**。大对象（完整 config、识别结果、shape、move task）被整体打印，造成噪声。

**（8）策略变更不可追溯。** `Fork._apply_policy()` 与 `_ReachMovingDevicePolicy._policy()` 直接调用 `Navigation.appendCustomPolicy()`，**没有任何日志**。因此 `initialPolicy`、`forwardPolicy`、`policy`、`reachFinalPolicy`、`nearMotionPolicy`、`reachMotorMovingDeviceShieldPolicy` / `RestorePolicy` 的下发与恢复在 trace 中完全不可见；`apply_default_navigation_policy()` 同样无日志。唯一有记录的是 `_sync_motion_policy()` 写入 `fork.nav` 的两条自由文本。

这一缺口会直接造成现场误判。典型场景：取货近货阶段脚本把 `navigation.obstacleStop.obsStopLoad.loadObsStopDist` 从配置值改为 0.2 m，随后叉尖激光在 0.19 m 读数上触发 `STATE_BLOCKED`。由于脚本侧没有任何策略事件，trace 里只能看到 `fork.task` 的一条 `policy :{...}` 文本，真正生效的时序要去 RBK 侧 `config_changed_subscriber` 才看得到，脚本无法自证"我下发了什么、何时恢复、恢复成了什么"。

### 2.3 量化基线

对两份文件做 AST 静态统计（排除注释）：

| 文件 | `Trace.log` 调用数 |
| --- | --- |
| `tasks/v3/standard/fork.py` | 66 |
| `tasks/v3/standard/fork_utils.py` | 98 |
| **合计** | **164** |

按目标通道归一化后的分布：

| 通道 | 调用数 | 备注 |
| --- | --- | --- |
| `fork.task` | 88 | 绝对主力，语义最杂 |
| `fork.err` | 30 | |
| `fork.cfg` | 15 | |
| `fork.action` | 8 | 与 `fork.taskActions` 重复 |
| `fork.nav` | 4 | 其中 2 处实为策略日志 |
| `fork.motor` | 2 | 其中 1 处是叉车累计计数，非电机语义 |
| `fork.rec` | 1 | |
| `fork.script` | 1 | 以 `self.script_trace_channel` 属性下发 |
| 未指定 `name` | 8 | 落入默认裸通道 |

另有 7 处通过 `log_name` 形参或 `self.*_trace_channel` 属性间接指定通道，静态解析时需按调用方取值。

> 注意：代码中大量出现的 `action_name="RunMotor"`、`action_name="RecPallet"`、`action_name="NavForkHeight"` 等是**动作名**，不是日志通道。不要把它们计入通道清单。

## 3. 日志通道设计

所有通道名必须稳定，不得拼接 `taskId`、`actionId`、时间戳或动态动作名。

| 通道 | 类型 | 责任 | 是否高频 |
| --- | --- | --- | --- |
| `fork` | 事件 | 脚本生命周期、阶段切换、任务级决策 | 否 |
| `fork.taskActions` | 事件协议 | Action 队列 `taskBuild` / `taskExtend` / `actionStateChanged` / `taskFinished` / `taskFailed` | 否 |
| `fork.task` | 数值 | 任务级数值快照 | 是 |
| `fork.motor` | 事件 + 数值 | 电机命令、到位、停止、超时、货叉机构事件和状态快照 | 数值高频 |
| `fork.nav` | 事件 + 数值 | 导航/路径启动、目标、到达、接触 DI、避障和导航状态 | 数值可高频 |
| `fork.policy` | 事件 | 策略下发、覆盖、恢复、清除，以及策略值与默认值的差异 | 否 |
| `fork.rec` | 事件 | 识别启动、重试、结果摘要、校验和失败 | 否 |
| `fork.cfg` | 事件 | 配置加载、配置摘要、设备模型摘要、参数变更 | 否 |
| `fork.err` | 事件 | 错误、超时、超限、命令拒绝、清理失败 | 否 |

### 3.1 废弃与迁移

| 项 | 处理 | 迁移目标 |
| --- | --- | --- |
| `fork.action`（8 处） | **已删除** | `fork.taskActions`（`ActionTask` 已在写，删除旧调用即可） |
| `fork.script`（1 处） | **已删除**；动作队列字段以 `scriptTaskLen` / `scriptCurrentAction` / `scriptCurrentActionStatus` 并入 `fork.task` 快照 | `fork.task` |
| `fork.nav` 中的策略日志（2 处） | **已迁出** | `fork.policy` |
| `fork.motor` 中的累计计数（1 处） | **已迁出** | `fork.cfg` |
| 裸通道调用（8 处） | **已补齐 `name`** | `fork.rec` / `fork.err` / `fork.nav` |
| `fork.motor` 的 `forkHeightInPlace` | **已删除**，统一用 `forkInPlace`（`reportInfo` 的对外字段不受影响） | `forkInPlace` |

现有 `fork.task` / `fork.motor` 的业务消费者需要兼容旧字段，字段替换采用双写过渡，至少保留一个完整版本周期。禁止新代码使用默认裸通道 `log`、动态 `name` 或 `Trace.chart()`。

**已决定保留**：`fork.task` 快照的 `scriptStatus` / `actionStatus` / `actionIndex` / `actionCount`（下游表单与看板仍在消费）。

### 3.3 载荷体积与完整数据

`Trace.log` 的 `output_console` **只控制终端打印**，不影响落盘：任何非 `debug=True` 的记录都会经 `Trace` 服务写入 trace。因此体积治理的正确手法是「终端静默、落盘保留」，而不是删字段：

- 需要减少终端噪声时，用 `output_console=False`，**不要**把完整数据换成计数。
- 摘要字段与完整值**同时落盘**：摘要供人快速阅读，完整值供回放。例：`executionParametersResolved` 同时带 `skillName`/`target`/`paramKeys` 摘要与完整 `moveTask`。
- 仅在载荷确实巨大（点云级）时才截断，且**必须显式标注** `truncated: true` 与 `totalCount`，绝不静默丢数据。
- 因不可序列化而丢弃的字段数记入 `_droppedFields`，使读者知道本次载荷做过减法。

判定基准：读日志的人能否在不看代码、不重新跑任务的前提下复原现场输入。做不到就不能算「已摘要」。

### 3.2 通道语义边界

四条判据用于消除争议：

1. **事件 vs 数值**：只发生一次的状态变化写事件通道（`fork`、`fork.policy`、`fork.err`、`fork.rec`、`fork.cfg`、`fork.taskActions`）；随周期或位置连续变化的写数值通道（`fork.task`、`fork.motor`、`fork.nav`）。
2. **任务 vs 动作**：任务级写 `fork` / `fork.task`；动作队列写 `fork.taskActions`；两者通过 `taskId` 与 `actionId` 关联，不互相承载对方字段。
3. **业务 vs 策略**：任何对 `Navigation.appendCustomPolicy` / `clearPolicy` / `goPathParam` 的调用都写 `fork.policy`，不写 `fork.nav`。
4. **脚本 vs 平台**：脚本只记录"我下发了什么"；RBK 侧的生效值与平台默认值作为对照字段随事件一起记录，不反向要求平台日志。

## 4. 公共上下文与字段

建议在 `Fork` 实例中维护统一 `TraceContext`，每条结构化事件自动附带：

```json
{
  "taskId": "RunScript-xxx",
  "scriptName": "fork.py",
  "modelType": "liftFork",
  "operation": "load",
  "phase": "approach",
  "phaseId": "approach-1",
  "actionId": "GoPath-abc",
  "actionType": "GoPathWithContactDi",
  "event": "phaseStarted"
}
```

约束：

- `taskId` 为空时使用空字符串，不使用 `None`，也不临时生成。
- `actionId` 没有动作上下文时使用空字符串。
- `phase` 使用固定枚举，不写自由文本。
- `event` 使用固定 camelCase 枚举；详细说明另放 `reason`、`detail` 或结构化字段。
- 字段类型必须稳定；单位通过字段名或 `unit` 约定，不在同一 key 中混用字符串和数字。
- 顶层事件统一带 `traceSchemaVersion`（数值快照不带，避免放大体积）。

### 4.1 phase 枚举

保持精简，并与 `OperationFlow` 批次、动作类型一一对应。无法在现场稳定区分的细分阶段不列入枚举，改用 `reason` 或 `detail` 表达。

| phase | 含义 | 与动作/批次的关系 |
| --- | --- | --- |
| `received` | 任务接收 | 脚本进入，尚无动作 |
| `validated` | 参数校验完成 | `_init_args()` 结束 |
| `prepare` | 起始位姿、货叉高度、DO 准备 | 起始动作批次 |
| `recognition` | 识别与校验 | `Rec` / `RecPallet` / `RecCage` / `GoLiveRec` |
| `approach` | 接近目标点 | `GoPath` / `GoBezier` |
| `adjust` | 姿态与横向调整 | `RunReachMotorsByPosition`、对准动作 |
| `insert` | 进叉 / 伸出 | `RunMotorByPosition`、`extendReachMotors` |
| `contact` | 接触 DI 与后撤 | `GoPathWithContactDi` |
| `lift` | 货叉升降 | 升降电机动作 |
| `release` | 放货 / 落叉 | 卸货动作批次 |
| `retract` | 退叉 / 收回 | `retractReachMotors` |
| `leaveLocation` | 离库位 | 离库位动作批次 |
| `navigation` | 站间导航 | `RunScript` 之外的路径任务 |
| `finished` | 正常结束 | 终态 |
| `failed` | 失败 | 终态 |
| `cancelled` | 取消 | 终态 |

`manualMotor`、`weightCheck`、`cleanup`、`unload` 等不再单列为 phase：手动电机操作归入其发生时的 phase 并置 `manual: true`；称重以 `weightCheck` 事件而非 phase 表达；清理作为 `finished` / `failed` 事件的 `cleanup` 子对象；卸货的放货与退叉已由 `release` / `retract` 覆盖。

## 5. 各层生命周期协议

### 5.1 脚本级 `fork`

```json
{"event":"scriptStarted","taskId":"...","operation":"load","elapsedMs":0}
{"event":"scriptStatusChanged","taskId":"...","from":"none","to":"running","elapsedMs":120}
{"event":"scriptFinished","taskId":"...","operation":"load","elapsedMs":8600}
```

失败与取消：

```json
{
  "event":"scriptFailed",
  "taskId":"...",
  "operation":"load",
  "elapsedMs":3200,
  "errorCode":"ForkMoveTimeout",
  "reason":"lift motor timeout",
  "phase":"lift",
  "actionId":"RunMotor-abc"
}
```

规则：

- 一次脚本任务最多一个 `scriptStarted` 和一个终态事件。
- `set_status()` 只在实际变化时打印 `scriptStatusChanged`。
- `reset_task_state()` 不伪造业务任务终态；如需记录，使用 debug 事件或新的 task context。
- 任务开始时记录 `taskId`、operation、关键参数摘要和当前货物状态。

### 5.2 阶段级 `fork`

```json
{
  "event":"phaseChanged",
  "taskId":"...",
  "operation":"load",
  "from":"recognition",
  "to":"approach",
  "phaseId":"approach-1",
  "elapsedMs":1450,
  "trigger":"recognitionAccepted"
}
```

```json
{
  "event":"phaseFinished",
  "taskId":"...",
  "operation":"load",
  "phase":"approach",
  "phaseId":"approach-1",
  "elapsedMs":2300,
  "actionCount":2,
  "result":"arrived"
}
```

`OperationFlow` 每次 `start`、`advance`、`close` 都应产生阶段事件，至少标明 batch index、batch size 和生成器是否耗尽。不把生成器内部实现细节输出为大量文本。

### 5.3 动作级 `fork.taskActions`

严格遵守 [Module 日志记录规范](logging.md) §4 的 ActionTask 协议，只写五类事件。补充要求：

- 所有动作必须有稳定的 `actionId` 和 `actionType`。
- `actionParameters` 只保留小型参数摘要。
- `actionStateChanged` 的终态必须包含 `elapsedMs`。
- 电机实时位置、导航距离等变化不写入 action 事件，写入 `fork.motor` / `fork.nav` 数值通道。
- 失败只由最接近根因的一层写完整错误；上层只引用 `errorCode`、`failedAt` 和 `actionId`。
- 删除 `fork.action` 的全部写入，`_trace_log()` 辅助函数一并移除或改为写入 `fork.taskActions`。

## 6. 策略日志协议 `fork.policy`

这是本次重构新增的核心通道，用于消除 §2.2（8）的追溯缺口。

### 6.1 事件

| event | 触发点 |
| --- | --- |
| `policyApplied` | `Navigation.appendCustomPolicy()` 成功下发后 |
| `policyRestored` | 临时策略恢复为原始值时 |
| `policyCleared` | `Navigation.clearPolicy()` 后 |
| `policySkipped` | 策略值未变化、下发被跳过时（可选，默认不记） |

### 6.2 载荷

```json
{
  "event": "policyApplied",
  "taskId": "RunScript-b004bc39",
  "operation": "load",
  "phase": "approach",
  "actionId": "GoPath-abc",
  "actionType": "GoPathWithContactDi",
  "policyName": "reachMovingDeviceShieldPolicy",
  "trigger": "reachPhaseEnter",
  "changedKeys": ["navigation.obstacleStop.obsStopLoad.loadObsStopDist"],
  "before": {"navigation.obstacleStop.obsStopLoad.loadObsStopDist": 1.5},
  "after":  {"navigation.obstacleStop.obsStopLoad.loadObsStopDist": 0.2},
  "platformDefaults": {"navigation.obstacleStop.obsStopLoad.loadObsStopDist": 0.05},
  "resetPath": true,
  "policyValueCount": 5,
  "elapsedMs": 12
}
```

字段说明：

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `policyName` | string | 传入 `appendCustomPolicy` 的策略名，如 `policy`、`forwardPolicy`、`initialPolicy`、`reachFinalPolicy`、`reachMovingDeviceShieldPolicy` |
| `trigger` | string | 触发原因枚举，如 `scriptStart`、`reachPhaseEnter`、`velocitySignChanged`、`actionFinished` |
| `changedKeys` | string[] | 本次实际发生变化的策略键；为空表示无变化 |
| `before` / `after` | object | 仅含 `changedKeys` 对应键的前后值 |
| `platformDefaults` | object | 策略 JSON 中对应键的 `defaultValue`，用于区分"脚本意图值"与"平台默认值" |
| `resetPath` | bool | 是否同时调用 `Navigation.goPathParam(dict())` 重置路径 |
| `policyValueCount` | int | 本次策略包含的键总数（替代整体打印 `self.policy`） |

### 6.3 三层值语义

策略排查困难的根因是三个数长得像但来源不同，落盘时必须能区分：

| 层 | 来源 | 记录字段 |
| --- | --- | --- |
| 脚本意图值 | `self.policy[...]` | `after` |
| RBK 当前生效值 | `RobotParam.getConfig("navigation", key)` | `before`（下发前读取）或独立的 `currentConfig` 字段 |
| 平台默认值 | 策略 JSON 的 `defaultValue` | `platformDefaults` |

### 6.4 约束

1. **只记变化。** `_sync_motion_policy()` 每个周期都在判断 `set_policy` / `clear_policy` 标志位，直接加日志会高频刷屏。必须做 `before` / `after` 差异检测，无变化时不落盘（与 `elevator.policy` 的 `policy_changed` 判断一致）。
2. **不打印整个策略对象。** 用 `changedKeys` + `before` / `after` 替代 `{self.policy}`，避免大对象和高频写入。
3. **`resetPath` 必须记录。** `_apply_policy(reset_path=True)` 会额外重置路径，缺失该字段会导致策略变更与路径重置对不上账。
4. **恢复要对账。** `_finish_reach_moving_device_policy()` / `_finish_policy()` 用 `policyRestored` 记录恢复后的值，理想情况下应等于进入前的 `before`；不相等时记 `fork.err`。

### 6.5 待治理的风险点

`appendCustomPolicy` 当前使用 `policy`、`forwardPolicy` 等极短策略名反复下发，不同车型、不同动作可能互相覆盖。重构期间应确认该接口的幂等性与覆盖语义，并在 `fork.policy` 中记录 `policyName`，以便事后判断是否发生过意外覆盖。

## 7. 电机与货叉

### 7.1 电机事件

```json
{
  "event":"motorCommanded",
  "taskId":"...",
  "actionId":"RunMotor-abc",
  "actionType":"RunMotorByPosition",
  "motor":"liftMotor",
  "motorType":"lift",
  "mode":"position",
  "direction":"up",
  "startPosition":0.10,
  "targetPosition":0.80,
  "commandSpeed":0.05,
  "stopDi":"DI-001",
  "loaded":false,
  "timeoutMs":30000
}
```

```json
{
  "event":"motorReached",
  "motor":"liftMotor",
  "startPosition":0.10,
  "targetPosition":0.80,
  "actualPosition":0.795,
  "delta":0.695,
  "elapsedMs":12400,
  "stopReason":"positionReached"
}
```

```json
{
  "event":"motorFailed",
  "motor":"liftMotor",
  "targetPosition":0.80,
  "actualPosition":0.31,
  "elapsedMs":30040,
  "errorCode":"ForkMoveTimeout",
  "stopReason":"timeout",
  "upLimitDi":false,
  "downLimitDi":false
}
```

必须区分六种状态：`commanded`（命令是否成功下发）、`running`（执行中，不逐 tick 打文本）、`reached`（位置到位或 DI 提前完成）、`stopped`（调用 `resetMotor`，记录原因）、`failed`（失败与错误码）、`cancelled`（取消导致停止）。

`stopReason` 为固定枚举：`positionReached`、`stopDi`、`timeout`、`cancelled`、`reset`、`error`。

### 7.2 数值快照

周期性 `fork.motor` payload：

```json
{
  "forkHeight":0.795,
  "forkTarget":0.80,
  "forkInPlace":true,
  "forkMoving":false,
  "forkDirection":"up",
  "forkSpeed":0.0,
  "forkMileage":12.3,
  "forkMileageUp":7.1,
  "forkMileageDown":5.2,
  "minSafeHeight":0.30,
  "loaded":false
}
```

`fork.motor` 快照统一使用 `forkInPlace`（`forkHeightInPlace` 已删除）。`forkDirection` 无方向时用固定字符串 `idle`，不使用 `None`。

### 7.3 多电机同步

`RunReachMotorsByPosition` 至少记录：

- 电机名称列表。
- 各自目标位置与当前位置。
- 各自相对伸出量。
- `maxRelativeDiff` 与 `syncTolerance`。
- 触发 DI、全部到位、不同步失败和整组停止的原因。

位置数组属于小型固定长度数据，可放在事件摘要；长期轨迹不得放入事件日志。

## 8. 导航、识别与参数

### 8.1 导航

把现有 `go path target pos`、`goBezier target`、`method:bezier` 等文本迁移为 `fork.nav` 结构化事件：

- `navigationCommanded`
- `navigationStarted`
- `navigationProgress`（debug 或限频）
- `navigationArrived`
- `navigationBlocked`
- `navigationFailed`
- `navigationCancelled`

字段包含 `target`、`coordinate`、`backMode`、`speed`、`reachDist`、`reachAngle`、`contactDi`、`elapsedMs`、`reason`。目标坐标保留合理精度，避免完整对象透传。

`navigationBlocked` 应记录触发设备、距离读数、当前生效的停车阈值和该阈值的来源策略，便于区分"物理阻挡"与"阈值配置导致"。

### 8.2 识别

`fork.rec` 只记录摘要：

- `recognitionStarted`：recfile、recSide、重试上限、识别高度。
- `recognitionRetry`：attempt、状态、简短原因。
- `recognitionAccepted`：目标坐标、角度、宽度、高度等关键结果。
- `recognitionRejected`：校验项、阈值、实际值。
- `recognitionFinished` / `recognitionFailed`：耗时和错误码。

禁止默认打印完整 `results_list`、完整 pallet shape、点云和完整 config。需要诊断时使用明确 debug 开关和摘要/哈希。

### 8.3 参数生命周期

`_init_args()` 分三次记录，不揉成一条：

1. `taskArgsReceived`：输入键名与小型值摘要，必要时标记来源。
2. `taskArgsNormalized`：默认值、类型转换、限幅后的关键参数。
3. `executionParametersResolved`：最终传给 action 的目标位置、速度、timeout、stopDi、识别和安全策略。

敏感与大字段规则：

- `recfile`、站点名、operation 可记录。
- 完整 `move_task`、完整 config、完整 shape、完整容器数组不得放入普通事件。
- 对象过大时记录 `fieldCount`、`keys`、`digest` 和必要摘要。

## 9. 实现建议

### 9.1 统一 Trace facade

在 `fork_utils.py` 或独立公共模块提供：

```python
def emit_event(event, *, channel="fork", ctx=None, **fields):
    payload = {"event": event, "traceSchemaVersion": 1,
               **trace_context(ctx), **fields}
    Trace.log(payload, output_console=False, name=channel)


def emit_policy(policy_name, *, before, after, trigger, ctx=None, **rest):
    changed = {k: after[k] for k in after if before.get(k) != after[k]}
    if not changed:
        return
    emit_event("policyApplied", channel="fork.policy", ctx=ctx,
               policyName=policy_name, trigger=trigger,
               changedKeys=sorted(changed),
               before={k: before.get(k) for k in changed},
               after=changed, **rest)


def emit_error(error_code, reason, *, ctx=None, channel="fork.err", **fields):
    emit_event("error", channel=channel, ctx=ctx,
               errorCode=error_code, reason=str(reason), **fields)
```

封装层负责：

- 注入 `taskId` / operation / phase / actionId。
- 过滤 `None`、大对象和不可序列化值。
- 统一耗时字段和状态 wire 值。
- 对高频日志做限频或变化检测。
- 保证事件与数值快照的 `output_console` 策略一致。

### 9.2 ActionBase 补充字段

建议在 `ActionBase` 或叉车 action mixin 中补充：`phase`、`phase_id`、`start_ts`、`end_ts`、`last_trace_status`、`trace_context()`、`result_description()`。

`ForkActionQueue` 负责把 phase 上下文传给动作，不由每个 action 自己推断当前 operation。

### 9.3 失败去重

- 硬件/SDK 根因：动作或电机层写 `fork.motor` / `fork.err`。
- Action 队列终止：`fork.taskActions` 写 `taskFailed`。
- 脚本终止：`fork` 写 `scriptFailed`，只引用 `failedAt`、`errorCode`。
- 同一个 `errorCode` 不在三层重复输出完整 reason。

## 10. 分阶段实施

| 阶段 | 内容 | 风险 | 状态 |
| --- | --- | --- | --- |
| **Phase 0** | 统计现有 Trace 调用、通道、字段与位置；为 load / unload / recognition / forkHeight / manualMotor / reach / timeout / cancel / suspend-resume / policy 建立最小回放样例；固化旧日志样本，确认消费者依赖字段 | 无 | 已完成（AST 统计：164 处调用，见 §2.3） |
| **Phase 1** | 增加统一事件 facade 与字段过滤器；新增 `fork` 脚本/阶段生命周期事件与 `fork.policy` 通道；保留旧 `fork.task` / `fork.motor` 字段 | 低 | **已实施** |
| **Phase 2** | 统一电机动作的 commanded / reached / stopped / failed 事件，补齐参数、实际位置、耗时、方向、限位 DI 和停止原因；收敛重复日志到公共 mixin | 中 | **已实施** |
| **Phase 3** | 迁移 `fork.task` 中的导航/识别文本到 `fork.nav` / `fork.rec`；策略日志迁出 `fork.nav`；裸通道补齐 `name`；识别结果与路径参数摘要化 | 中 | **已实施** |
| **Phase 4** | 删除 `fork.action` / `fork.script` / `forkHeightInPlace`；`scriptStatus` 等快照字段保留 | 高 | 部分完成（见下方待验证清单） |

### 10.1 实施进度与验证状态

已实现内容以提交为准，验证分为两个层次：

| 层次 | 手段 | 覆盖 | 尚未覆盖 |
| --- | --- | --- | --- |
| 静态与单元 | `tools/test_fork_logging.py`（10 项）、`tools/smoke_fork_import.py` | 通道白名单、裸通道、旧通道/旧字段不再出现、facade 行为（只记变化、不静默截断）、未解析名字 | 真实 RBK 交互 |
| 仿真实测 | `tests/fork_flow.py`（需在仿真 RBK 上运行） | load / unload / forkHeight / autoPre / 识别注入全流程、`expectStatus` 校验 | 无相机识别、物理到位 DI |
| 实车 | 见 §10.2 清单 | 真实传感器、电机限位、策略对上游影响 | — |

### 10.2 实车验证清单

以下能力在仿真下无法覆盖（仿真无相机、无物理到位 DI、运动学简化），必须在实车验证本次改动未影响功能。测试重点不是「日志长什么样」，而是「行为与基线一致」：

**识别与相机路径**

- [ ] 识别取货（`recognize=true`）：`Rec` 全流程与识别结果解析，确认 `fork.rec` 的 `recognitionAccepted` / `recognitionProgress` 记录真实结果。
- [ ] 二次识别调整（`readjust`）：`recognitionTargetComputed` 的 `angleToAp` 与实际对准偏差一致。
- [ ] 库位 3D 检测（`LocDetectGoods`）：真实相机下的重试与 `TargetFilled` / `TargetNotFilled` 判定。
- [ ] `GoLiveRec` 边走边识别：确认 `fork.rec` 的 `liveRecPathPlanned` 不携带超大路径数组。

**电机与机构**

- [ ] 货叉升降到位：确认 `motorReached` 的 `stopReason` 为 `positionReached` 或 `stopDi`，且 `actualPosition` 与示教值一致。
- [ ] 货叉超时（`ForkMoveTimeout`）：确认落 `motorFailed` + `stopReason=timeout`，且未影响原有的 `setSystemError` 行为。
- [ ] 限位 DI：`upLimitDi` / `downLimitDi` 在真实限位处为 `true`。
- [ ] DO 电机（开合）：`stopReason=stopDi` 路径与 `isMotorReached` 跳过逻辑未被破坏。
- [ ] 多电机同步（`RunReachMotorsByPosition`）：不同步失败与整组停止仍能正确触发。
- [ ] 货叉 base shift：`chassisBaseShiftChanged` 与真实 `wheelBaseShift` 调用时机一致。

**策略与导航**

- [ ] 近货策略切换：`fork.policy` 的 `before`/`after` 与 RBK 侧实际生效值一致（建议对照 `config_changed_subscriber` 回读）。
- [ ] `resetPath=true` 的策略下发：路径重置时机未被日志改动影响。
- [ ] 碰撞设备屏蔽与恢复：`collisionDeviceLoaded` 列表与 `_restore_policy` 对账一致。
- [ ] 接触 DI 取货（`GoPathWithContactDi`）：真实 DI 触发与 `_check_di_active` 逻辑未变。
- [ ] 避障阻挡场景：`navigationBlocked` 能带出设备与距离读数（对应历史 21:47:37 类问题）。

**生命周期与边界**

- [ ] 暂停 / 恢复 / 取消：`scriptStatusChanged` 与 `scriptCancelled` 顺序正确，且 `start_time` 补偿逻辑未受影响。
- [ ] 智能取消：`smartCancelIgnored` 行为与 `cancel_allowed` 一致。
- [ ] 超时收尾：`scriptFailed` 的 `errorCode` 指向根因动作。
- [ ] `fork.taskActions` 与 `fork.task` 的 `taskId` / `actionId` 可关联。

**回归重点**

- [ ] 所有 load / unload 用例的实际行为（动作序列、时序、终态）与改动前一致 —— 日志改动不应改变任何控制流。
- [ ] 每轮测试后按 `taskId` 在 trace 里能还原完整过程（本次重构的核心目标）。

## 11. 推荐首批改造清单

按"风险最低、收益最大"排序：

1. **删除 `fork.action` 的 8 处写入**，动作队列完全依赖 `fork.taskActions`。`ActionTask` 已向该通道落盘，属于删旧代码，收益最大、风险最低。
2. **新增 `fork.policy` 通道**，在 `_apply_policy()`、`_policy()`、`apply_default_navigation_policy()` 三个下发点接入 `emit_policy()`，并把 `fork.nav` 中 2 处策略文本迁入。
3. `Fork.set_status()`：改为统一 `scriptStatusChanged` 事件。
4. `Fork._init_args()`：拆分为 received / normalized / resolved 三类参数事件。
5. `ForkActionQueue`：统一 queue / phase / action 关联与失败终止上下文。
6. `RunMotorByPosition` 的 `_start_motion()`、`run()`、`on_step_end()`：补齐 motorCommanded / motorReached / motorStopped / motorFailed。
7. `RunReachMotorsByPosition`：补齐同步状态与整组停止事件。
8. `_fork_configure_motion()`、`_fork_before_reach_check()`、`_fork_after_reached()`：统一 DO、timeout、limit DI 与货叉完成事件。
9. `period_run()`：保留高频数值通道，补充稳定字段，去除不必要文本；把叉车累计计数从 `fork.motor` 迁出。
10. `LiveRec` 系列动作：补齐 7 处裸通道 `name`，识别结果只保留摘要。

## 12. 验收标准

### 通道

- [ ] 新增日志全部使用固定通道，无拼接 `taskId` / `actionId` / 时间戳的动态通道名。
- [ ] Action 队列只使用 `fork.taskActions`；`fork.action` 不再有任何写入。
- [ ] `fork.script` 不再有任何写入。
- [ ] 无未指定 `name` 的 `Trace.log` 调用。
- [ ] 业务事件、数值快照、Action 协议、错误事件、策略事件互不混用。

### 生命周期

- [ ] 每个任务可还原 `scriptStarted → phaseChanged → action events → script terminal`。
- [ ] 每个 Action 的 start / terminal 和 `elapsedMs` 可关联。
- [ ] 每次 operation 批次推进可定位 phase、batch index 和 action 列表。
- [ ] suspend / resume / cancel / timeout 都能定位当前 action 和原因。

### 策略

- [ ] 每次策略下发、恢复、清除都有 `fork.policy` 事件，含 `policyName`、`trigger`、`changedKeys`、`before`、`after`。
- [ ] 策略事件含三层值来源，可区分脚本意图值、RBK 生效值与平台默认值。
- [ ] 同一 `policyName` 且值未变化时不重复落盘。
- [ ] `resetPath=true` 的策略事件与路径重置时间戳可对上。

### 电机

- [ ] 每次有效电机命令有 `motorCommanded`。
- [ ] 每次结束、失败、取消和超时都有明确 `stopReason`。
- [ ] 电机事件含 start / target / actual / `elapsedMs`，数值快照不产生重复文本。
- [ ] 多电机不同步能看到各电机位置、差值与阈值。

### 参数

- [ ] 能区分 received、normalized、resolved 三类参数。
- [ ] 所有执行目标与速度都有单位和稳定字段。
- [ ] 普通日志不包含完整 config、点云、完整识别结果或大容器对象。

### 质量

- [ ] `py_compile` 通过。
- [ ] `git diff --check` 通过。
- [ ] 现有叉车 flow tests 全部通过。
- [ ] 新增日志协议测试验证事件顺序、字段类型和终态唯一性。
- [ ] 至少完成一次真实或仿真任务的 trace 回放，并能按 `taskId` 还原全过程，包含一次策略变更的完整对账。

## 13. 待确认事项

### 已裁定（本轮）

| 项 | 结论 |
| --- | --- |
| `fork.task` 的 `scriptStatus` / `actionStatus` / `actionIndex` / `actionCount` | **保留**，下游表单与看板仍在消费 |
| `fork.script` | **已删除**，其字段并入 `fork.task`（`scriptTaskLen` / `scriptCurrentAction` / `scriptCurrentActionStatus`） |
| `forkHeightInPlace` | **已删除**，统一用 `forkInPlace`；`reportInfo` 的对外字段不改 |
| 大数组打印 | **落盘保留完整**，仅用 `output_console=False` 静默终端；超限时显式标注 `truncated` / `totalCount` |

### 仍待确认

1. `fork.taskActions` 当前是否已被部署环境消费，还是仅消费旧 `fork.action`。
2. 是否允许在 v3 脚本中直接采用 logging spec 的 v4 Action wire 字段，还是需要适配层。
3. 任务 ID 是否始终来自 `Module.getTaskId()`，以及脚本被 MF `RunScript` 调用时的关联规则。
4. 电机实时位置采样周期与最大 trace 体积要求（截断上限 `_TRACE_MAX_SEQ=256` 需与实际 trace 体积权衡确认）。
5. `Navigation`、`Motor`、`Container` 查询失败时，错误日志归属 SDK 层还是脚本层。
6. `Navigation.appendCustomPolicy` 是否幂等；同名策略反复下发的覆盖语义如何定义；是否需要按车型或动作隔离策略名。
7. 策略值的"RBK 当前生效值"通过 `RobotParam.getConfig` 读取是否存在延迟或缓存，能否作为 `before` 的可靠来源。
8. 本节新增的 `fork.motor` 数值字段（`forkTarget`、`forkMoving`、`forkDirection`、`forkSpeed`、`minSafeHeight`、`loaded`）需要同步修订 [Module 日志记录规范](logging.md) §2.3 的叉车字段表，修订责任人与时间需确认。
9. `tests/fork_flow.py` 与 `tests/fork_sim_inject.py` 目前只在 `origin/mazj` 分支，需确认是否合并到 `release` 以纳入常规仿真回归。
