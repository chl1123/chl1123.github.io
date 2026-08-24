# Module 日志记录规范

> 适用范围：标准车型脚本（顶升车、料箱车、叉车、清洁车等）的公共日志约束，以及 MF（MoveFactory）与脚本之间的 Action 队列日志协议。

本文定义可被其他模块、语言和日志分析器直接消费的约束。`ActionTask`、`ActionBase`、MF logger 等实现细节不属于本文；脚本实现见 [ActionTask 开发指南](../development/action_task.md)，MF 实现请参考 MoveFactory 仓库中的 `docs/04-task-reference.md` 和 `docs/08-development-guide.md`。

## 版本与兼容性

| 版本 | 状态 | 说明 |
|------|------|------|
| v4 | 当前 | Action 队列统一使用 `taskActions` 通道（MF）或 `{xxx}.taskActions` 通道（脚本）；通过 `event` 区分五类当前事件。 |
| v3 | 已废弃 | `Trace.chart` 迁移到 `Trace.log`。 |
| v2 | 已废弃 | 旧版 Action 队列字段和并行模型。 |
| v1 | 已废弃 | 旧版顺序队列事件和整型动作索引。 |

当前协议只保证 v4 名称和字段。新代码不得写入旧名称，也不要求当前适配器兼容旧日志中的 `<module>.action`、`actionFinished`、`queueBuild`、`queueExtend` 或 `queueDone`。

## 1. 公共日志接口

### 1.1 日志类别

| 类别 | 是否落盘 | 是否上报调度 | 用途 |
|------|----------|--------------|------|
| 结构化运行日志 | 是 | 否 | 事件、状态变化、异常和可检索上下文。 |
| 数值时序日志 | 是 | 否 | 高度、速度、电流等随时间变化的数据。 |
| `Module.reportInfo` | 否 | 是 | 调度和 Roboshop 使用的实时业务状态。 |
| `print()` | 否 | 否 | 仅限受控调试输出，生产代码不得直接使用。 |

### 1.2 `Trace.log` 公共约束

`Trace.log` 接受字符串或结构化对象，并将记录写入指定 `name` 通道。

```text
Trace.log(msg, output_console=True, output_time=False, *, name="", debug=False)
```

`name` 和 `debug` 是关键字参数；新代码必须显式传入稳定的 `name`，不得依赖默认裸通道 `log`。

| 参数 | 约束 |
|------|------|
| `msg` | 字符串用于人读事件描述；对象用于结构化事件或数值时序。字符串记录在日志中表现为 `{"log":"..."}`。 |
| `name` | 必须显式指定；必须是稳定、可枚举的业务通道名，不得包含动态 `taskId`、`actionId` 或时间戳。 |
| `output_console` | 普通事件可保留默认值；高频数值时序应关闭终端输出。 |
| `output_time` | 默认关闭；仅在需要终端二次对时时临时开启。 |
| `debug` | 仅用于生产环境默认沉默的诊断数据；必须事件不得依赖 debug 模式才能落盘。 |

同一逻辑通道的记录必须始终使用相同 `name`。不得依赖默认裸通道 `log`，不得把同一事件同时写成字符串和结构化对象。

字符串消息在结构化日志中表现为 `{"log":"..."}`；结构化对象按字段原样记录。数值时序不得用字符串拼接 `key=value` 代替。

`Trace.chart` 已废弃。数值和图表数据统一使用 `Trace.log(dict, output_console=False, name="...")`；新代码不得使用 `Trace.chart`。

`debug=True` 的记录可在非 debug 运行模式下被抑制；它只适合高频或低优先级诊断数据。必须记录的业务事件必须使用常规日志，并且同一逻辑通道不要混用两种模式。

常见写法：

```python
Trace.log("status IDLE -> RUNNING", name="jack")
Trace.log({"event": "motorTimeout", "motorId": "lift", "elapsedMs": 1200}, name="jack.err")
Trace.log({"jackHeight": 1.25, "jackTarget": 1.30}, output_console=False, name="jack.motor")
```

### 1.3 通道命名

普通业务日志按“模块.子主题”组织：

| 通道 | 用途 |
|------|------|
| `<module>` | 模块主流程、状态机和任务级文本事件。 |
| `<module>.rec` | 识别启动、识别结果和识别失败。 |
| `<module>.motor` | 机构、电机和执行反馈。 |
| `<module>.nav` | 导航、路径、避障和到达。 |
| `<module>.cfg` | 配置加载和参数变更。 |
| `<module>.err` | 异常、超时和超限。 |
| `<module>.task` | 任务级数值快照。 |

车型前缀使用稳定短名：`jack`（顶升车）、`ctu`（料箱车）、`fork`（叉车）、`clean`（清洁车）等。

Action 队列使用 §4 规定的专用通道，不得使用 `<module>.action`。

### 1.4 事件记录原则

- 只记录状态变化、关键决策、关键动作完成、异常和配置结果。
- 同一执行路径中的同一事件只记录一次；状态未变化时不得重复记录。
- 循环内不得无条件写文本日志；高频变化改用数值时序通道。
- 异常记录应包含足以定位问题的上下文，但不得直接塞入完整点云、容器列表或其他大对象。
- 异常在同一层级只记录一次；上层可以引用错误标识，不要重复打印同一堆栈或同一原因。

必须记录的事件包括：

| 事件类别 | 推荐通道 | 记录内容 |
|----------|----------|----------|
| 任务开始 / 结束 | `<module>` | 任务标识、动作类型和最终结果。 |
| 状态机切换 | `<module>` | 旧状态和新状态。 |
| 关键动作完成 | `<module>.motor` / `<module>.nav` | 目标值、实际值和耗时。 |
| 异常 / 超时 / 超限 | `<module>.err` | 错误上下文、重试次数和错误码。 |
| 配置加载 / 变更 | `<module>.cfg` | 配置结果和关键参数摘要。 |
| 重试 / 恢复 / 急停恢复 | `<module>` | 触发原因、尝试次数和恢复结果。 |

禁止记录的内容包括：循环内每次迭代的重复状态、无变化的轮询结果、用文本记录的高频数值序列，以及与上一条完全相同的信息。

## 2. 数值时序规范

数值时序使用结构化对象写入 `<module>.task`、`<module>.motor` 或 `<module>.nav` 等稳定通道。

### 2.1 字段规则

- 同一 `name` 下，同一 key 的类型必须稳定；不得在整数、浮点数、布尔值和字符串之间切换。
- 数值字段使用 `int` 或 `float`；状态开关使用 JSON 布尔值；需要嵌套时使用本节定义的命名对象类型。
- 同一 payload 中的字段可以按场景增减，但已出现的 key 必须保持类型稳定。
- 缺省字段表示该时刻没有上报该指标，不得被解释为状态变化；图表消费者按约定将缺省数值显示为 `0`。
- 高频时序必须关闭终端输出，并建议集中在主循环的固定位置上报。
- 数值通道不得承载 Action 事件；Action 事件统一走 §4 的 `taskActions` 通道。

数值字段只允许 `int`、`float`、JSON 布尔值和命名嵌套对象；禁止 `str`、`None`、`list` 和不可序列化对象。同一 key 一旦使用某种类型，整个通道生命周期内不得切换类型。

### 2.2 推荐任务快照字段

脚本或模块需要提供队列数值快照时，使用 `<module>.task` 通道。字段均为整数，缺省字段不得被解释为新的状态。

| 字段 | 语义 |
|------|------|
| `scriptStatus` | 脚本状态值。 |
| `total` | 当前任务动作总数。 |
| `runningCount` | 当前运行中的动作数量。 |
| `waitingCount` | 已入队但尚未启动的动作数量。 |
| `finishedCount` | 已完成动作数量。 |
| `failedCount` | 已失败动作数量。 |
| `suspendedCount` | 已暂停动作数量。 |

这些字段描述当前快照，不替代 `taskBuild`、`actionStateChanged` 或终态事件。

### 2.3 各车型数值通道与字段

以下字段是标准车型的公共数值上报约束。字段可缺省时，消费者按 §2.1 处理；字段一旦出现，类型必须保持稳定。

| 车型 | `name` | 字段 | 类型 | 可缺省 |
|------|--------|------|------|--------|
| 顶升车 `jack` | `jack.task` | `scriptStatus`、`total`、`runningCount`、`waitingCount`、`finishedCount`、`failedCount`、`suspendedCount` | int | 否 |
|  | `jack.motor` | `jackHeight`、`jackTarget`、`jackInPlace` | float / float / bool | 否 |
|  | `jack.motor` | `jackMotorCurrent` | float | 是 |
| 料箱车 `ctu` | `ctu.task` | `scriptStatus`、`total`、`runningCount`、`waitingCount`、`finishedCount`、`failedCount`、`suspendedCount` | int | 否 |
|  | `ctu.motor` | `ctuHeight`、`ctuTarget` | float | 否 |
|  | `ctu.motor` | `ctuInPlace`、`containerCount` | bool / int | 否 |
| 叉车 `fork` | `fork.task` | `scriptStatus`、`total`、`runningCount`、`waitingCount`、`finishedCount`、`failedCount`、`suspendedCount` | int | 否 |
|  | `fork.motor` | `forkHeight`、`forkTarget`、`forkMileage` | float | 否 |
|  | `fork.motor` | `forkInPlace` | bool | 否 |
| 清洁车 `clean` | `clean.task` | `scriptStatus`、`cleanState`、`taskState` | int | 否 |
|  | `clean.motor` | `brushSpeed`、`waterLevel` | float | 否 |

最小任务快照示例：

```json
{"scriptStatus":2,"total":3,"runningCount":1,"waitingCount":1,"finishedCount":1,"failedCount":0,"suspendedCount":0}
```

## 3. `Module.reportInfo` 与调试输出

### 3.1 `Module.reportInfo`

`Module.reportInfo` 只用于实时业务状态，不写入动作队列日志，也不能替代 `Trace.log`。

- 不打印、不落盘，仅供调度系统和 Roboshop 实时展示。
- 同一时刻的相关数据合并为一次上报。
- 每次调用都必须携带 `containers`，包括空载状态。
- 在任务状态变更、关键动作完成或需要调度介入的异常发生时上报。
- 字段应表达当前业务状态，不要把完整内部对象直接透传。

`reportInfo` 的公共字段如下；业务可以增加动作相关的 `detail` 字段，但不得改变字段类型。

| JSON 路径 | 类型 | 必填 | 语义 |
|-----------|------|------|------|
| `action` | string | 否 | 当前动作名称。 |
| `status` | string | 否 | `running`、`finished` 或 `failed`。 |
| `progress` | float | 否 | 当前动作进度，范围 `0.0` 到 `1.0`。 |
| `detail` | ReportDetail | 否 | 动作相关的小型结构化摘要。 |
| `error` | string | 否 | 失败或异常描述；仅在需要时提供。 |
| `containers` | array[ContainerInfo] | 是 | 当前所有容器位的载货状态，包括空载位。 |

`ReportDetail` 是业务自定义的小型 JSON 对象；其键和值必须保持稳定、可序列化，不得直接透传完整内部对象。

`containers` 为容器位数组，每个元素是 `ContainerInfo`：

| JSON 路径 | 类型 | 必填 | 语义 |
|-----------|------|------|------|
| `containers[].containerId` | string | 是 | 容器位标识。 |
| `containers[].desc` | string | 否 | 货物描述，通常为空。 |
| `containers[].goodsName` | string | 否 | 货物名称。 |
| `containers[].hasGoods` | boolean | 是 | 当前容器位是否有货。 |

车型 `containerId` 约定：

| 车型 | 约定 |
|------|------|
| 料箱车背篓 | `"0"`、`"1"`、`"2"`，按背篓位递增。 |
| 料箱车货叉 | `"999"`。 |
| 顶升车、叉车、辊筒车 | 通常使用 `"0"`。 |

示例：

```json
{
  "action": "Pick",
  "status": "finished",
  "progress": 1.0,
  "detail": {"distance": 0.42, "elapsedMs": 860},
  "containers": [
    {"containerId": "0", "goodsName": "bin-001", "hasGoods": true}
  ]
}
```

不要拆分同一时刻的状态字段；错误示例：

```python
Module.reportInfo({"goStraightStatus": "finished"})
Module.reportInfo({"goDist": dist})
```

应合并为一次上报，并始终携带 `containers`：

```python
Module.reportInfo({
    "action": "GoStraightDist",
    "status": "finished",
    "distance": dist,
    "elapsed": elapsed,
    "containers": Container.getContainers(),
})
```

禁止手工改写容器字段名或只在有货时上报 `containers`；空载状态也必须上报。

### 3.2 `print()`

生产代码禁止裸 `print()`。调试输出必须通过受 debug 开关控制的统一封装，并在提交前清理临时输出。

推荐使用统一的调试封装，且不得将其当作生产日志：

```python
def debug_print(*args, **kwargs):
    if ConfigParams.debug_mode:
        print("[DEBUG]", *args, **kwargs)
```

## 4. Action 队列对外协议

本节是 MF 与脚本之间的公共 wire 契约。适配方只需要依赖通道名、JSON 字段、事件顺序和不变量，不需要知道日志由哪个类或调度循环写出。

### 4.1 协议速览

`TaskStream`（队列事件流）是一轮 Action 队列从建立到结束产生的完整日志序列。每条日志记录携带一个 JSON 事件；同一轮的所有事件使用相同的 `taskId`，并通过 `event` 表示当前阶段。

一轮队列的结构是：

```text
TaskStream :=
    taskBuild
    (taskExtend | actionStateChanged)*
    (taskFinished | taskFailed)
```

含义：

- `taskBuild` 是起点，每轮只能有 1 次。
- `taskExtend` 和 `actionStateChanged` 是中间事件，出现次数可以为 0 次或多次，二者可以交错出现。
- `taskFinished` 与 `taskFailed` 是终态事件，只能二选一，并且每轮只能有 1 次。
- 终态事件之后不再产生该轮的 Action 事件；重新建队表示开始新的 `TaskStream`。

事件树如下：

```text
TaskStream
├─ taskBuild                         1 次
│  └─ actions: array[ActionDescriptor]
├─ 中间事件                          0..N 次，任意顺序
│  ├─ taskExtend
│  │  └─ appended: array[ActionDescriptor]
│  └─ actionStateChanged
│     └─ actionId + status
└─ 终态事件                          1 次，二选一
   ├─ taskFinished
   └─ taskFailed
```

事件索引：

| 阶段 | `event` | 作用 | 主要字段 |
|------|---------|------|----------|
| 起点 | `taskBuild` | 建立本轮完整的初始动作队列。 | `actions: array[ActionDescriptor]` |
| 中间 | `taskExtend` | 向队列尾部追加动作。 | `appended: array[ActionDescriptor]`、`total` |
| 中间 | `actionStateChanged` | 记录一个动作的一次状态转移。 | `actionId`、`actionType`、`status` |
| 终态 | `taskFinished` | 本轮所有动作成功完成。 | `total`、`elapsedMs` |
| 终态 | `taskFailed` | 本轮因动作失败、取消或外部错误终止。 | `total`、`elapsedMs`、`failedAt`、`reason` |

### 4.2 通道与父子任务关联

MF 和脚本分别维护自己的 `TaskStream`。二者通过 MF 的 `RunScript` action 关联，而不是共享同一个外层任务 ID：

```text
MF TaskStream
name   = taskActions
taskId = MF 外层任务 ID
  └─ RunScript.actionId
       │
       │ 传给脚本后作为脚本 taskId
       ▼
脚本 TaskStream
name   = {xxx}.taskActions，例如 jack.taskActions
taskId = MF RunScript.actionId
```

关联规则：

1. MF 外层任务 `taskId` 和脚本队列 `taskId` 属于不同层级，不得直接当作同一个 ID。
2. 先在 MF `taskActions` 中找到 `actionType` 为 `RunScript` 的动作，再用该动作的 `actionId` 匹配脚本通道中的 `taskId`。
3. 脚本队列内部的 `actionId` 只用于定位脚本自己的动作，不能替代 MF 的 `RunScript.actionId`。
4. `name` 只用于选择日志通道，不得拼接动态任务或动作 ID。

| 产生日志的模块 | 队列日志 `name` | 本层 `taskId` | 本层 `actionId` |
|---------------|-----------------|---------------|----------------|
| MF（MoveFactory） | `taskActions` | MF 任务 ID，string | MF action ID，string；同一 MF 队列内稳定唯一 |
| 标准脚本 | `{xxx}.taskActions`，例如 `jack.taskActions` | MF `RunScript.actionId`，string | 脚本队列内的动作 ID，string；只在本脚本队列内稳定唯一 |

### 4.3 完整事件流示例

下面是一轮脚本 `TaskStream` 的成功示例。日志筛选 `name=jack.taskActions` 后，可以按 `taskId` 看到完整生命周期；中间的 `taskExtend` 和 `actionStateChanged` 按实际产生时间交错出现。

```jsonl
{"event":"taskBuild","taskId":"RunScript-abc123","total":2,"actions":[{"actionId":"JackHeight-def456","actionType":"JackHeight","blockingType":"HARD","actionParameters":{"motor":"lift","target":1.25}},{"actionId":"Navigate-ghi789","actionType":"Navigate","blockingType":"SOFT","actionParameters":{"station":"S-01"}}]}
{"event":"actionStateChanged","taskId":"RunScript-abc123","actionId":"JackHeight-def456","actionType":"JackHeight","status":"running"}
{"event":"actionStateChanged","taskId":"RunScript-abc123","actionId":"JackHeight-def456","actionType":"JackHeight","status":"finished","elapsedMs":1200,"resultDescription":{"actualHeight":1.25}}
{"event":"taskExtend","taskId":"RunScript-abc123","appended":[{"actionId":"Place-jkl012","actionType":"Place","blockingType":"NONE","actionParameters":{"containerId":"0"}}],"total":3}
{"event":"actionStateChanged","taskId":"RunScript-abc123","actionId":"Navigate-ghi789","actionType":"Navigate","status":"running"}
{"event":"actionStateChanged","taskId":"RunScript-abc123","actionId":"Navigate-ghi789","actionType":"Navigate","status":"finished","elapsedMs":2500,"resultDescription":{"station":"S-01"}}
{"event":"actionStateChanged","taskId":"RunScript-abc123","actionId":"Place-jkl012","actionType":"Place","status":"running"}
{"event":"actionStateChanged","taskId":"RunScript-abc123","actionId":"Place-jkl012","actionType":"Place","status":"finished","elapsedMs":800}
{"event":"taskFinished","taskId":"RunScript-abc123","total":3,"elapsedMs":4600}
```

失败时，最后一条记录使用 `taskFailed`，并可携带触发失败的动作和终止原因：

```json
{"event":"taskFailed","taskId":"RunScript-abc123","total":3,"elapsedMs":3200,"failedAt":"Navigate-ghi789","reason":"obstacle"}
```

### 4.4 JSON 层级与类型记法

字段表使用 JSON 路径描述层级：

- `taskId` 表示事件 JSON 的顶层字段。
- `actions` 表示顶层数组字段；`actions[].actionId` 表示数组中每个元素的字段。
- 类型使用协议中的命名类型，例如 `ActionDescriptor`、`ActionParameters` 和 `ResultDescription`；数组使用 `array[类型]` 表示。

协议中复用的嵌套类型如下：

| 类型名 | 使用路径 | 字段定义 |
|--------|----------|----------|
| `ActionDescriptor` | `actions[]`、`appended[]` | `actionId`、`actionType`、`blockingType`、`actionParameters` 为必填；`actionDescription` 可选。 |
| `ActionParameters` | `actions[].actionParameters`、`appended[].actionParameters` | 动作参数摘要。只保留站点、目标值、数量、方向、超时等小型字段；无参数时为 `{}`。 |
| `ResultDescription` | `resultDescription` | 动作完成结果摘要，例如实际高度、识别结果摘要或最终位置；无结果时省略。 |

`ActionParameters` 和 `ResultDescription` 的键由具体动作定义，但值必须是可序列化的 JSON 基本值或小型嵌套 JSON；禁止放入完整容器、点云、轨迹或其他大对象。枚举和自定义对象应先转换为协议支持的 JSON 值。

### 4.5 通用字段

以下字段位于五类事件 JSON 的顶层：

| JSON 路径 | 类型 | 必填 | 语义 |
|-----------|------|------|------|
| `event` | string | 是 | 当前事件类型，只能取 §4.1 列出的值。 |
| `taskId` | string | 是 | 当前队列任务 ID。同一 `TaskStream` 从 `taskBuild` 到终态保持不变。 |

### 4.6 各事件字段

每类事件都在通用字段之外追加以下顶层字段。数组元素的字段通过 `字段[]` 路径明确列出，例如 `actions[].actionId`。

#### `taskBuild`

| JSON 路径 | 类型 | 必填 | 语义与约束 |
|-----------|------|------|------------|
| `total` | non-negative integer | 是 | 初始动作总数。 |
| `actions` | array[ActionDescriptor] | 是 | 完整初始动作列表；数组长度必须等于 `total`。 |
| `actions[].actionId` | string | 是 | 队列内稳定唯一；分配后不得改变。 |
| `actions[].actionType` | string | 是 | 动作类型或业务名称。 |
| `actions[].blockingType` | string | 是 | 只能是 `HARD`、`SOFT` 或 `NONE`。 |
| `actions[].actionParameters` | ActionParameters | 是 | 关键参数摘要；无参数时为 `{}`。 |
| `actions[].actionDescription` | string | 否 | 人读补充说明；为空时省略。 |

#### `taskExtend`

| JSON 路径 | 类型 | 必填 | 语义与约束 |
|-----------|------|------|------------|
| `appended` | array[ActionDescriptor] | 是 | 本次追加的动作，只能追加到队列尾部。 |
| `appended[].actionId` | string | 是 | 队列内稳定唯一；不得与已有动作重复。 |
| `appended[].actionType` | string | 是 | 动作类型或业务名称。 |
| `appended[].blockingType` | string | 是 | 只能是 `HARD`、`SOFT` 或 `NONE`。 |
| `appended[].actionParameters` | ActionParameters | 是 | 关键参数摘要；无参数时为 `{}`。 |
| `appended[].actionDescription` | string | 否 | 人读补充说明；为空时省略。 |
| `total` | non-negative integer | 是 | 追加后的动作总数。 |

#### `actionStateChanged`

| JSON 路径 | 类型 | 必填 | 语义与约束 |
|-----------|------|------|------------|
| `actionId` | string | 是 | 要变更状态的动作 ID，必须已在 `taskBuild.actions` 或 `taskExtend.appended` 中声明。 |
| `actionType` | string | 是 | 对应动作的类型或业务名称。 |
| `status` | string | 是 | 只能是 §4.8 定义的状态值。 |
| `elapsedMs` | non-negative integer | 否 | `finished` / `failed` 时表示该动作耗时。 |
| `resultDescription` | ResultDescription | 否 | 只用于 `finished`；无结果时省略。 |
| `reason` | string | 否 | 用于 `failed` / `suspended` 的原因说明。 |
| `errorCode` | string | 否 | 用于 `failed` 的错误码。 |

#### `taskFinished`

| JSON 路径 | 类型 | 必填 | 语义与约束 |
|-----------|------|------|------------|
| `total` | non-negative integer | 是 | 本轮队列的动作总数。 |
| `elapsedMs` | non-negative integer | 是 | 从 `taskBuild` 到任务成功完成的耗时。 |

#### `taskFailed`

| JSON 路径 | 类型 | 必填 | 语义与约束 |
|-----------|------|------|------------|
| `total` | non-negative integer | 是 | 本轮队列的动作总数。 |
| `elapsedMs` | non-negative integer | 是 | 从 `taskBuild` 到任务失败的耗时。 |
| `failedAt` | string | 否 | 触发失败的 action ID。 |
| `reason` | string | 否 | 队列终止原因。 |

### 4.7 `blockingType` 语义

`blockingType` 描述动作在本轮队列中的调度关系，不是动作类的固有属性：

| 值 | 语义 |
|----|------|
| `HARD` | 独占队列；只有当前没有 active 动作时才能启动。 |
| `SOFT` | 在没有 `HARD` 动作阻塞时，可以与其他非 `HARD` 动作并行。 |
| `NONE` | 在没有 `HARD` 动作阻塞时，可以并行启动。 |

默认值为 `HARD`。同一个动作类型在不同队列中可以使用不同的 `blockingType`。

### 4.8 状态字段

`actionStateChanged.status` 使用以下字符串：

| status | 语义 |
|--------|------|
| `init` | 已加入队列但尚未启动。 |
| `running` | 已启动，业务正在推进。 |
| `finished` | 成功完成。 |
| `failed` | 执行失败或被取消。 |
| `suspended` | 暂停中。 |

合法状态转移：

```text
init      -> running
running   -> finished
running   -> failed
running   <-> suspended
suspended -> failed
init      -> failed
```

同一 action 的相同状态不得重复发 `actionStateChanged`。`running` 持续期间的数值变化走数值通道，不重复发状态事件。

### 4.9 生命周期不变量

- `taskBuild` 是一轮 `TaskStream` 的起点；队列重跑必须重新开始一轮。
- 同一轮所有事件的 `taskId` 完全相同。
- 每个 `actionId` 在所属队列内稳定唯一，状态事件不得引用未出现在 `taskBuild` 或 `taskExtend` 中的 ID。
- `taskExtend` 只能出现在 `taskBuild` 之后，并且只能做尾部追加。
- `taskExtend` 必须先于该次追加动作的任何 `actionStateChanged`；状态事件不得引用尚未声明的动作。
- 每个状态转移最多产生一条 `actionStateChanged`。
- `actionStateChanged.actionType` 应与动作描述符中的 `actionType` 保持一致，便于从中途开始读取日志的分析器识别动作。
- 失败发生后，其他仍在执行的动作必须被停止或转入失败处理，不能继续产生正常完成事件。
- 一轮队列最多产生一个终态事件，且终态之后不得再产生该轮的动作状态事件。
- 事件按产生时间顺序落盘；同一队列的分析器应按时间排序处理，不能依赖文件行号以外的实现细节。

## 5. 日志分级

日志级别由通道和消息语义共同表达：

| 级别 | 约定 |
|------|------|
| INFO | 常规业务事件，使用模块主通道或子主题通道。 |
| WARN | 可恢复异常或需要关注的偏差；消息中应明确标注告警语义。 |
| ERROR | 无法正常完成的异常、超时或超限；优先使用 `<module>.err` 通道。 |

`*.err` 通道用于异常事件的筛选和告警对接，不要把正常状态变化写入错误通道。

## 6. 适配检查清单

### 通道

- [ ] MF 使用 `taskActions`。
- [ ] 脚本使用 `{xxx}.taskActions`，`xxx` 为稳定车型前缀。
- [ ] 不使用 `<module>.action`，不把 ID 或事件名拼入 `name`。

### 字段

- [ ] 每条 Action 事件包含 `event` 和字符串 `taskId`。
- [ ] `actionId` 是字符串，且在所属队列内稳定唯一。
- [ ] `status` 只使用 `init` / `running` / `finished` / `failed` / `suspended`。
- [ ] `total`、`elapsedMs` 是非负整数；`actions` / `appended` 使用 `array[ActionDescriptor]`。
- [ ] `actions[].actionParameters` / `appended[].actionParameters` 使用 `ActionParameters`，且是精简摘要，不包含大对象。
- [ ] `actionStateChanged.resultDescription` 使用 `ResultDescription`，无结果时省略。

### 生命周期

- [ ] 每轮有且只有一个 `taskBuild` 起点。
- [ ] 动态追加只发 `taskExtend`，且只追加到尾部。
- [ ] 状态只在发生转移时发 `actionStateChanged`。
- [ ] `taskFinished` / `taskFailed` 至多一个，且终态后不再发该轮事件。
- [ ] 脚本 `taskId` 与 MF `RunScript.actionId` 一致；MF 外层 `taskId` 不直接写入脚本队列。

### 其他日志

- [ ] 每条 `Trace.log` 都显式使用 `name=`，不依赖裸 `log` 通道。
- [ ] 事件文本使用字符串，结构化事件和数值时序使用 JSON 对象；不混用同一事件的两种记录形式。
- [ ] 不使用 `Trace.chart`；数值时序关闭高频终端输出。
- [ ] `debug=True` 只用于可按需开启的诊断数据，必须事件不依赖 debug 模式；同一通道不混用 debug 和常规日志。
- [ ] 同一异常在同一层级只记录一次；循环内没有无条件文本日志。
- [ ] 数值时序使用稳定通道，关闭高频终端输出，并保持 key 类型稳定。
- [ ] 数值字段只使用 `int` / `float` / `bool` / 命名嵌套对象，不使用 `None` / `str` / `list`。
- [ ] 每次 `Module.reportInfo` 都携带 `containers`。
- [ ] 生产代码没有裸 `print()`。
- [ ] 新代码不产生 v1/v2/v3 已废弃的通道名或事件名。
