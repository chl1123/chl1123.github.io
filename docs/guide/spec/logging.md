# Module 日志记录规范

> 适用范围：`tasks/v3/standard/module/` 下所有标准车型脚本（顶升车、料箱车、叉车、清洁车等）

## 版本更新

| 版本 | 主要变更 |
|------|----------|
| v3（当前） | 弃用 `Trace.chart`，统一使用 `Trace.log`：数值时序 / 图表数据改为 `Trace.log(dict)` 上报，落盘通道即 `name` 本身（缺省 `log`）。`Trace.chart` 保留但标记弃用，调用时提示改用 `Trace.log` |
| v2 | Action 队列协议对齐 [VDA5050 v3.0](https://github.com/VDA5050/VDA5050) §6.8 / §6.11 / §6.12：`actionId` 改为字符串 UUID；引入 `blockingType` 声明式并行调度（`HARD` / `SOFT` / `NONE`）；状态转移统一走单事件 `actionStateChanged`（携带 wire 字符串 `status`）；`actionParameters` 命名与 VDA5050 一致；并行集合用 `runningCount` / `waitingCount` / `finishedCount` / `failedCount` / `suspendedCount` 表达 |
| v1 | 顺序型队列：整型 `id` 索引；三事件 `actionStart` / `actionFinished` / `actionFailed`；单值 `curActionState`；事件名 `queueBuild` / `queueExtend` / `queueDone` |

---

## 一、日志方法定义与职责

| 方法 | 落盘 | 终端打印（默认） | 上报调度 | 用途 |
|------|------|----------|----------|------|
| `Trace.log(msg, output_console=True, output_time=False, *, name="", debug=False)` | Yes | Yes | No | 文本 / 结构化运行日志 + 数值时序，按 name 分通道；`msg` 可为 `str` 或 `dict` |
| `Module.reportInfo(data)` | No | No | Yes | 实时状态上报（调度/Roboshop 可见） |
| `print(msg)` | No | Yes | No | 仅开发调试，禁止在生产代码中使用 |

/// warning | `Trace.chart` 已弃用
`Trace.chart` 已弃用，请统一改用 `Trace.log`。数值时序 / 图表数据用 `Trace.log(dict, name="...")` 上报即可（类型稳定约束见 §三），落盘通道即 `name` 本身（缺省 `log`）。`Trace.chart` 仍可调用但会触发弃用提示，新代码禁止使用。
///

### 1.1 接口签名说明

```python
Trace.log(msg: Union[str, dict], output_console=True, output_time=False, *, name="", debug=False)
```

- `msg`：位置参数，`Trace.log` 接受 `str` 或 `dict`：
    - 传 `str` 时，内部自动包装为 `{"log": "<msg>"}` 后落盘（key 固定为 `"log"`），适合人读事件描述
    - 传 `dict` 时，按字典 key/value 原样落盘，适合结构化事件上下文与数值时序（见 §二、§三）
- `output_console`：是否打印到终端。**log 默认 True**；数值时序等高频数据应手动设为 `False`，避免刷屏淹没关键日志
- `output_time`：是否在终端输出中带时间戳
- `name`：**关键字参数（keyword-only）**，必须写作 `name="xxx"`；默认 `"log"`。落盘通道名即 `name` 本身：
    - `Trace.log(..., name="jack")`  → 落盘通道 `jack`
    - `Trace.log(..., name="jack.motor")` → 落盘通道 `jack.motor`
    - 不传 `name` 时回落为裸通道 `log`（禁止依赖，见 §1.2）
- `debug`：**关键字参数（keyword-only）**，默认 `False`
    - `False`：常规落盘，日志级别为 `[I]`，模块标识为 `rbk.script.utils_rpc`
    - `True`：debug 日志，**仅当系统处于 debug 模式时才会落盘**；日志级别变为 `[D]`，模块标识带 `.d` 后缀（`rbk.script.utils_rpc.d`）。用于生产环境默认沉默、需要时再打开排查的高频或低优先级数据（见 §1.4）

典型调用：

```python
# 文本日志（str）：内部落盘为 {"log": "..."}
Trace.log("status IDLE -> RUNNING", name="jack")                          # 落盘通道 jack
Trace.log(f"motor timeout, {motor_id=}", name="jack.err")                 # 落盘通道 jack.err

# 结构化事件日志（dict）：按 key/value 原样落盘，便于检索
Trace.log({"event": "actionStateChanged", "actionId": "pick-7c4a", "status": "running"}, name="jack.action")

# 数值时序 / 图表数据（dict）：高频，关闭终端打印
Trace.log({"jackHeight": h, "jackTarget": t}, output_console=False, name="jack.motor")   # 落盘通道 jack.motor
```

### 1.2 关于 name 参数

`name` 是日志在系统中的**业务逻辑通道名**，直接作为落盘通道名（缺省回落为 `log`）。落盘日志格式为：

```
# Trace.log(str) —— str 会被包装为 {"log": "..."}
[20260505.11:37:10.554.499.765][rbk.script.utils_rpc][<name>][I]: {"log": "<内容>"}

# Trace.log(dict) —— 按 key/value 原样落盘（结构化事件或数值时序）
[20260505.11:37:10.554.499.765][rbk.script.utils_rpc][<name>][I]: {"event": "...", "id": 3, ...}
[20260505.11:37:10.554.499.765][rbk.script.utils_rpc][<name>][I]: {"jackHeight": 1.25, ...}

# debug=True —— 模块标识带 .d 后缀，级别变为 [D]，仅 debug 模式下落盘
[20260505.11:37:10.554.499.765][rbk.script.utils_rpc.d][<name>][D]: {"log": "<内容>"}
```

- 终端、日志检索、图表绘制都按落盘通道（`<name>`）聚合或筛选
- 业务侧填写的 `name` 即落盘通道名，按"模块.子主题"组织（§2.2）
- 同一通道可同时承载事件日志与数值时序——按 §二的通道命名规范区分子主题（事件走 `<module>` / `<module>.err` 等，数值时序走 `<module>.task` / `<module>.motor` 等）即可天然隔离
- `name` 必须采用稳定可枚举的字符串（不要拼接动态值如 task_id）
- 同一逻辑通道的日志必须使用相同 `name`
- **始终显式指定 `name`**，禁止依赖默认值 `"log"`；缺省时落盘通道回落为裸 `log`，会把所有模块的日志混在同一通道，丧失分组意义

### 1.3 output_console / output_time 使用约定

- `output_console`：
    - 文本 / 事件日志默认 True，保留默认即可；仅高频重复事件可手动设为 False
    - 数值时序 / 图表数据**必须手动设为 False**（高频数据刷终端会淹没关键日志）
- `output_time`：
    - 默认 False，依赖日志前缀时间戳即可
    - 仅在终端实时调试、需要二次对时的场景临时设为 True，提交代码前复位

### 1.4 debug 使用约定

`debug=True` 用于**生产环境默认沉默、需要时再打开排查**的日志/数据：

- 仅当系统处于 debug 模式时才落盘，常规运行时既不落盘也不刷终端日志文件，避免日志体积膨胀
- 落盘时日志级别为 `[D]`，模块标识自动带 `.d` 后缀（`rbk.script.utils_rpc.d`），便于检索时与常规 `[I]` 日志区分
- 适用场景：
    - 高频但偶尔需要的诊断数据（如内部状态、临时中间值、详细的电机/传感器原始读数）
    - 平时无需关注、仅在复现问题时打开的辅助上下文
- **不要**用 `debug=True` 替代 §2.4 列出的必须事件 —— 这些事件必须始终落盘
- 同一逻辑通道不要混用 `debug=True` 和 `debug=False`：要么全程沉默由 debug 模式控制，要么全程落盘，否则检索时只能看到半截事件流

```python
# 常规事件 —— 始终落盘
Trace.log(f"开始顶升 target={target}", name="jack.motor")

# 高频诊断 —— 仅 debug 模式下落盘
Trace.log({"rawHeight": raw, "filtered": filt}, output_console=False, name="jack.motor.raw", debug=True)
Trace.log({"jackMotorCurrent": cur}, output_console=False, name="jack.motor.diag", debug=True)
```

---

## 二、Trace.log 规范

### 2.1 记录原则

- **记录事件类信息**：状态变更、关键决策、异常、配置加载结果；支持文本或结构化字典两种形态（见 §2.3）
- **数值时序也走 `Trace.log(dict)`**：高度、速度、电流等数值型时序用 `Trace.log(dict, output_console=False, ...)` 上报，类型稳定约束见 §三；与事件日志按通道命名（§2.2）区分子主题
- **禁止重复记录事件**：同一事件在同一执行路径中只允许出现一次（数值时序按 tick 周期采样不受此限）
- **必须显式指定 `name=`**，禁止使用默认值 `"log"`（缺省落盘通道为裸 `log`）

### 2.2 name 命名规范

按"模块.子主题"分通道，便于按通道筛日志：

| 通道 name | 用途 | 示例事件 |
|-----------|------|----------|
| `<module>` | 模块主流程（任务、状态机） | 任务开始/结束、状态切换 |
| `<module>.action` | action 队列调度 | 队列开始、动作切换、队列结束 |
| `<module>.rec` | 识别相关 | 识别启动、结果、识别失败 |
| `<module>.motor` | 机构/电机动作 | 顶升、叉举、放货 |
| `<module>.nav` | 导航/路径 | 路径下发、避障、到达 |
| `<module>.cfg` | 配置加载 | 参数加载、参数变更 |
| `<module>.err` | 异常告警 | 异常、超时、超限 |

`<module>` 取值：`jack`（顶升车） / `ctu`（料箱车 cartonTransferUnit） / `fork`（叉车） / `clean`（清洁车） 等。

### 2.3 格式规范

`Trace.log` 支持 `str` 和 `dict` 两种 `msg` 形态，按下列原则选择：

- **默认用 `str`**：人读事件描述；关键上下文以 `key=value` 形式追加。内部会被包装为 `{"log": "<内容>"}` 落盘。
- **需要结构化检索时用 `dict`**：事件字段多、下游需要按字段过滤/聚合（如 action 队列事件、reportInfo 前的结构化快照）。字典按 key/value 原样落盘，便于日志检索系统索引。
- **数值时序也用 `dict`**：高度、速度、电流等数值型时序用 `Trace.log(dict)` 上报，须满足 §三 的类型稳定约束，并设 `output_console=False`；与事件型 `dict` 按通道命名（§2.2）区分子主题。

```python
# str 形态：事件描述 + 上下文 key=value
Trace.log(f"status {prev_state} -> {new_state}", name="jack")
Trace.log(f"up finish, {target=}, {actual=}, {elapsed=}ms", name="jack.motor")
Trace.log(f"motor timeout, {motor_id=}, {elapsed=}ms", name="jack.err")

# dict 形态：结构化事件，下游可按字段检索
Trace.log(
    {"event": "actionStateChanged", "actionId": "pick-7c4a", "actionType": "Pick", "status": "running"},
    name="jack.action",
)
Trace.log(
    {"event": "motorTimeout", "motorId": motor_id, "elapsedMs": elapsed},
    name="jack.err",
)
```

同一事件不要同时用 `str` 和 `dict` 各打一次——选其一，保持单条记录。

### 2.4 必须记录的事件（Must Log）

| 事件类型 | 通道 | 示例 |
|----------|------|------|
| 任务开始/结束 | `<module>` | `任务开始 task_id=xxx action=PICK` |
| 状态机切换 | `<module>` | `状态切换 IDLE -> RUNNING` |
| 关键动作完成 | `<module>.motor` | `顶升完成 target=1200 actual=1198` |
| 异常/错误 | `<module>.err` | `识别超时 retry=3/3` |
| 配置加载 | `<module>.cfg` | `配置加载 fork_speed=500 max_height=2000` |
| 重试/恢复 | `<module>` | `重试导航 attempt=2 reason=obstacle` |
| 急停/恢复 | `<module>` | `EMC触发 saved_state=LIFTING` |
| 队列暂停/恢复 | `<module>` | `queue suspend action_id=2/7 name=JackHeight` |

### 2.5 禁止记录的内容（Must NOT Log）

| 禁止内容 | 原因 | 替代方案 |
|----------|------|----------|
| 循环体内每次迭代的状态 | 大量重复 | 仅记录开始/结束/异常退出 |
| 周期性轮询结果（无变化） | 刷屏 | 仅在状态变化时记录 |
| 用文本 / `key=value` 打数值序列 | 刷屏、不可绘图 | 改用 `Trace.log(dict, output_console=False)` 走数值时序通道（§三） |
| 与上一条相同的信息 | 重复 | 加条件判断去重 |

### 2.6 去重模式

文本日志只记录"发生了什么"（状态跳变、动作开始/结束、异常），**数值的变化过程不应混进文本日志**，应交给数值时序通道用 `Trace.log(dict, output_console=False)` 上报。主循环每 tick 调用一次数值上报，等于天然以 tick 频率采样，不需要在文本日志里再手写边界采样。

```python
# 错误 1：循环内无条件打印 —— 刷屏
while not in_place:
    Trace.log(f"等待到位 current={get_height()}", name="jack.motor")
    time.sleep(0.1)

# 错误 2：用文本日志记录数值变化 —— 数值序列应走数值时序通道
_last_bucket = None
while not in_place:
    bucket = get_height() // 100
    if bucket != _last_bucket:
        Trace.log(f"顶升中 height={get_height()}", name="jack.motor")  # 应走数值时序 dict
        _last_bucket = bucket
    time.sleep(0.1)

# 正确：文本日志只记首尾状态事件；高度的时序由主循环的数值 Trace.log(dict) 覆盖
Trace.log(f"开始顶升 target={target}", name="jack.motor")
t0 = time.time()
while not in_place:
    time.sleep(0.1)  # 高度通过主循环末尾的 Trace.log(dict) 持续上报到 jack.motor
Trace.log(
    f"顶升完成 actual={get_height()} elapsed={int((time.time()-t0)*1000)}ms",
    name="jack.motor",
)

# 主循环末尾（每 tick 调用一次，自然形成高度时序曲线）
Trace.log(
    {
        "jackHeight": float(get_height()),
        "jackTarget": float(target),
        "jackInPlace": bool(in_place),
    },
    output_console=False,
    name="jack.motor",
)
```

如果某个数值型事件确实需要"状态跳变"语义（例如高度越限、触发到位边沿），那是状态事件而不是数值采样，仍可用文本 `Trace.log` 记一次，但消息是"事件描述"而不是"当前值的打印"：

```python
# OK：这是边沿事件，不是数值采样
if get_height() > ConfigParams.max_height:
    Trace.log(
        f"高度越限 height={get_height()} limit={ConfigParams.max_height}",
        name="jack.err",
    )
```

### 2.7 异常日志规范

```python
# 错误：同一异常多次记录
try:
    data = json.loads(raw)
except json.JSONDecodeError as e:
    Trace.log(f"JSON解析失败: {e}",       name="jack.err")
    Trace.log(f"数据异常: {e}",           name="jack.err")
    Trace.log(f"laser_area_deduct: {e}",  name="jack.err")

# 正确：一个异常只记录一次，包含完整上下文
try:
    data = json.loads(raw)
except json.JSONDecodeError as e:
    Trace.log(
        f"laser_area_deduct JSON解析失败 input={raw[:50]} error={e}",
        name="jack.err",
    )
```

---

## 三、数值 / 图表数据规范（`Trace.log(dict)`）

数值时序 / 图表数据统一用 `Trace.log(dict, output_console=False, name="...")` 上报，按 name 分通道（落盘通道即 `name`），图表端按通道聚合绘制。本节约束这类 dict 的字段类型，与 §二的事件型 dict 共用 `Trace.log`，靠通道命名（§3.2）区分。

### 3.1 核心规则

- **同一 key 的值类型必须保持稳定**：同一个 `name` 下某个 `key` 一旦用某种类型（int / float / bool / dict）上报，后续每次上报该 key 都必须是相同类型
    - 不允许某次传 `"jackHeight": 1.25`、下次传 `"jackHeight": "1.25"`
    - 不允许某次传 `"inPlace": True`、下次传 `"inPlace": 1`
- **key 可以动态增减**：某次 payload 缺失某个 key 时，图表渲染端会按 `0` 呈现，不会报错；因此允许按场景只上报相关字段（无需为占位硬塞字段）
- **value 类型只允许**：
    - 数值：`int` / `float`
    - JSON 布尔：Python `True` / `False`（会序列化为 JSON `true` / `false`）
    - JSON 嵌套：`dict`（JSON object），内部字段同样受 "类型稳定" 约束
    - **禁止**：`str` / `None` / `list` / 枚举对象（枚举请显式 `int(x)` 或 `.value` 转 int）
- **关闭终端打印**：数值时序 `output_console=False`，避免高频数据刷屏淹没关键日志
- **调用点建议统一**：同一 `name` 的数值上报推荐在主循环固定末尾位置集中调用（如 `_loop()` / `execute()` 末尾），方便维护；允许多处调用，但须自行保证各调用点满足上述类型稳定约束

### 3.2 多 name 分组

允许使用多个不同的 `name` 拆分图表，每个 name 仍需满足"同 key 类型稳定"约束。建议按机构 / 动作维度分组：

| name | 内容 |
|------|------|
| `<module>.task` | 任务级状态：script_status / action_id / action 总数 |
| `<module>.motor` | 机构状态：高度、目标、电流、到位 |
| `<module>.nav` | 导航状态：速度、里程、避障 |

数值时序与事件日志可复用同一 `<module>.xxx` 子主题（如机构事件与机构数值都落 `jack.motor`），由图表端按 key 自动识别数值序列。

### 3.3 数据结构示例

```python
# 主循环末尾集中调用（推荐） —— 使用 name="jack.task"
# 所有 key 类型稳定：int / bool / dict，任意 tick 可以按需增删 key
counts = self.queue.status_counts()                   # 由 ActionTask 提供
chart_task = {
    "scriptStatus":   int(self.script_status),        # int，稳定
    "total":          int(self.queue.total),          # int，稳定（队列总动作数）
    "runningCount":   int(counts["running"]),         # int，稳定（当前 running 动作数）
    "waitingCount":   int(counts["init"]),            # int，稳定（pending 队列长度）
    "finishedCount":  int(counts["finished"]),        # int，稳定
    "failedCount":    int(counts["failed"]),          # int，稳定
    "suspendedCount": int(counts["suspended"]),       # int，稳定
    "inPlace":        bool(self.in_place),            # bool，稳定（不要和 int 混用）
}
if self.recognize:
    # key 按场景动态增减，缺失时图表端按 0 呈现
    chart_task["recPose"] = {                            # JSON 嵌套对象
        "x":   float(self.rec_world_pos[0]),
        "y":   float(self.rec_world_pos[1]),
        "yaw": float(self.rec_world_pos[2]),
    }
Trace.log(chart_task, output_console=False, name="jack.task")
```

### 3.4 字段命名与类型规范

- 使用 camelCase
- 前缀表示所属机构：`fork*`, `jack*`, `nav*`, `clean*`
- 枚举 / IntEnum：使用 `int(x)` 或 `x.value` 转为 `int`，不要直接塞枚举实例
- 布尔：用 Python `True` / `False`，也可以使用 `0` / `1` 模拟——但是一旦该 key 首次以 int 上报，就会锁定为 int 类型，后续不能再换 bool
- 嵌套 dict：内部字段同样遵守上述类型稳定与允许类型约束
- **禁止**：字符串、`None`、`list`、不可 JSON 序列化的对象

### 3.5 各车型必须包含的数值通道与字段

"类型"列是该 key 在整个生命周期中必须保持的类型；"可缺省"列标识某些场景下允许不上报，图表端会按 0 呈现。

`<MOD>.task` 通道字段统一由 `ActionTask.status_counts()` 派生，并行场景下各车型一致；详见 §4.8。

| 车型 | name | 字段 | 类型 | 可缺省 |
|------|------|------|------|--------|
| 顶升车 jack | `jack.task`  | scriptStatus | int   | 否 |
|             |               | total | int   | 否 |
|             |               | runningCount / waitingCount / finishedCount / failedCount / suspendedCount | int | 否 |
|             | `jack.motor` | jackHeight | float | 否 |
|             |               | jackTarget | float | 否 |
|             |               | jackInPlace | bool  | 否 |
|             |               | jackMotorCurrent | float | 是 |
| 料箱车 ctu（cartonTransferUnit） | `ctu.task`   | scriptStatus / total / runningCount / waitingCount / finishedCount / failedCount / suspendedCount | int   | 否 |
|                                   | `ctu.motor`  | ctuHeight / ctuTarget | float | 否 |
|                                   |               | ctuInPlace | bool  | 否 |
|                                   |               | containerCount | int   | 否 |
| 叉车 fork | `fork.task`    | scriptStatus / total / runningCount / waitingCount / finishedCount / failedCount / suspendedCount | int   | 否 |
|           | `fork.motor`   | forkHeight / forkTarget / forkMileage | float | 否 |
|           |                 | forkInPlace | bool  | 否 |
| 清洁车 clean | `clean.task`  | scriptStatus / cleanState / taskState | int   | 否 |
|             | `clean.motor` | brushSpeed / waterLevel | float | 否 |

---

## 四、Action 队列执行日志规范

模块采用 `action_list` + 阻塞型并行调度模型。所有队列事件统一使用 `Trace.log(dict, ...)` 结构化形式，通道名 `<module>.action`，分析器通过 `event` 字段作为类型判别器，读取事件流即可重建任务 UI。

### 4.1 设计要点

- **action 主键 `actionId` 为字符串**：由 `ActionTask` 在 `build()/extend()` 时生成（短 UUID 或 `<actionType>-xxxx`），全队稳定唯一，与执行顺序无关。并行模式下"已完成索引"语义不成立，因此用稳定字符串 id 引用具体动作。
- **`blockingType` 由队列装配方式决定**：同一个动作类（如 `Spin`）在不同任务中可能串行也可能并行，因此并行能力**不属于动作类**，而是由 `ActionTask.build()` / `extend()` 的调用方按本次任务的语义指派。
  - `NONE`  可与其他 action 完全并行
  - `SOFT`  可与其他 action 并行，但若主类业务上下文要求"独占车体"，由业务自行处理
  - `HARD`  完全独占，active 必须为空才能启动；运行中其他 pending action 不得启动
  - **默认 `HARD`** —— 装配时不指定即为严格顺序，与历史串行队列等价
  - 见 §4.7.2：装配 API 同时支持 `build(actions, blocking_type=...)` 的批量缺省与 `(action, "NONE")` 的逐项指定
- **状态使用 `ActionStatus` 枚举**：`INIT / RUNNING / FINISHED / FAILED / SUSPENDED`。wire 上序列化为枚举名小写字符串。映射关系见 §4.3。
- **单事件 `actionStateChanged`**：每次状态转移发一次，带 `status` 字段。并行模式下多个 action 同时处于不同状态，合并为单事件便于分析器侧做状态机投影。
- **任务级 `taskBuild` / `taskExtend` / `taskFinished` / `taskFailed`**：`taskBuild` 起点、`taskExtend` 动态追加、`taskFinished` 与 `taskFailed` 互斥收尾。

### 4.2 事件模型总览

一次任务 = 一条 `taskBuild` ... `taskFinished` / `taskFailed` 的事件流。**所有事件必须携带 `taskId` 字段**（来自 `Module.getTaskId()`，整队不变），分析器据此把事件聚合到对应任务、跨任务重启时正确隔离、并发任务场景下不串流。

| event                | 触发时机                                          | 关键字段                                                                                                  | 每条队列允许次数 |
|----------------------|-----------------------------------------------|-------------------------------------------------------------------------------------------------------|----------|
| `taskBuild`          | action_list 首次装配完成、首次执行前                       | `taskId`, `total`, `actions[{actionId,actionType,blockingType,actionParameters,actionDescription?}]` | 1        |
| `taskExtend`         | 运行过程中动态追加动作（识别结果、异常恢复等；**仅尾部追加**）             | `taskId`, `appended[{actionId,actionType,blockingType,actionParameters,actionDescription?}]`, `total` | ≥0       |
| `actionStateChanged` | 任一 action 的状态发生转移                              | `taskId`, `actionId`, `actionType`, `status`, `elapsedMs?`, `resultDescription?`, `reason?`, `errorCode?` | 每个 action 多次（每次转移一条） |
| `taskFinished`       | 所有 action 均进入终态，且无 FAILED                     | `taskId`, `total`, `elapsedMs`                                                                       | 0 或 1（与 `taskFailed` 互斥） |
| `taskFailed`         | 任一 action 失败 / 整队取消 / 外部错误终止                  | `taskId`, `total`, `elapsedMs`, `failedAt?`, `reason?`                                              | 0 或 1（与 `taskFinished` 互斥） |

约束：
- **`taskId` 在整队生命周期内严格不变**：`taskBuild` 起算，后续所有事件复用同一个 `taskId`。任务结束后若新任务到达，必须先发 `taskBuild` 再开始携带新 `taskId`。
- **`actionId` 全队稳定唯一**：由 `taskBuild` / `taskExtend` 分配后永不变更；所有 `actionStateChanged` 通过 `actionId` 引用该动作。
- 一次任务以 `taskFinished` 或 `taskFailed` 之一收尾，二者互斥。
- `taskExtend` 只允许向队列尾部追加；不存在中间插入。
- **`taskExtend` 必须出现在某次 `taskBuild` 之后**；在尚未 `taskBuild` 或队列已终态时调用 `ActionTask.extend(...)`，自动促级转发到 `build(...)` 发出 `taskBuild`。
- `total` 在每条事件携带，便于分析器校验状态一致性。
- `actionType` 在 `actionStateChanged` 中冗余写入 —— 即使分析器错过 `taskBuild`（尾读中途介入），也能从任一 `actionStateChanged` 重建动作类型。
- `taskBuild` 是任务生命周期的起点，整队重跑必须再发一次 `taskBuild`，分析器收到后视为 UI 重置。

### 4.3 状态字段

`status` 字段在 wire 上为字符串，与内部 `ActionStatus` 枚举一一对应：

| wire 字符串    | `ActionStatus` 枚举    | 语义 |
|---------------|----------------------|------|
| `"init"`      | `INIT (0)`           | 已入队但 scheduler 还未触发 |
| `"running"`   | `RUNNING (1)`        | 已触发，业务推进中（包含准备阶段与执行阶段） |
| `"finished"`  | `FINISHED (3)`       | 正常完成，可携 `resultDescription` |
| `"failed"`    | `FAILED (4)`         | 失败，带 `reason` / `errorCode` |
| `"suspended"` | `SUSPENDED (5)`      | 暂停（suspend/resume 期间） |

`running` 是单一状态，覆盖动作从触发到完成之间的整个过程。子类内部若区分"发指令、等握手、执行"等阶段，自行跟踪即可，wire 上不区分。

合法的状态转移（每次转移发一条 `actionStateChanged`）：

```
init      -> running                    （scheduler 触发）
running   -> finished                   （成功完成）
running   -> failed                     （运行失败）
running   <-> suspended                 （外部 suspend/resume）
suspended -> failed                     （暂停期间被取消）
init      -> failed                     （排队中被取消）
```

### 4.4 事件字段定义

所有字段键名使用 camelCase；值遵守 §1.1、§三 的类型规则（仅 int / float / bool / str / dict / list）。

**通用字段（每条事件必带）**：
- `event`: str — 事件类型判别器
- `taskId`: str — 任务 ID，来自 `Module.getTaskId()`；整队生命周期内不变；若调度未下发任务则为空串 `""`

```text
taskBuild:
    event:    "taskBuild"
    taskId:   str                       必填；Module.getTaskId() 在 build 时刻的取值
    total:    int                       必填；初始队列长度
    actions:  list[action_descriptor]   必填；长度等于 total
        action_descriptor:
            actionId:           str     必填；短 UUID / "<actionType>-xxxx"，全队稳定唯一
            actionType:         str     必填；action 类名或业务类型
            blockingType:       str     必填；"NONE" | "SOFT" | "HARD"
            actionParameters:   dict    必填；关键参数摘要（见 §4.5）
            actionDescription:  str     可选；人读补充说明

taskExtend:
    event:    "taskExtend"
    taskId:   str                       必填
    appended: list[action_descriptor]   必填；仅追加到尾部
    total:    int                       必填；扩展后队列总长度

actionStateChanged:
    event:             "actionStateChanged"
    taskId:            str               必填
    actionId:          str               必填；对应 taskBuild / taskExtend 中的 actionId
    actionType:        str               必填；冗余字段，便于尾读重建
    status:            str               必填；"init" | "running" | "finished" | "failed" | "suspended"
    elapsedMs:         int (可选)        可选；仅在终态（finished/failed）填，自该 action 进入 running 起算
    resultDescription: dict (可选)       可选；status == "finished" 时业务结果摘要
    reason:            str (可选)        可选；status == "failed" 或 "suspended" 时的人读原因
    errorCode:         str (可选)        可选；status == "failed" 时的异常码

taskFinished:
    event:     "taskFinished"
    taskId:    str                       必填
    total:     int                       必填
    elapsedMs: int                       必填；从 taskBuild 起算

taskFailed:
    event:     "taskFailed"
    taskId:    str                       必填
    total:     int                       必填
    elapsedMs: int                       必填；从 taskBuild 起算
    failedAt:  str (可选)                可选；出错的 actionId（动作失败时由 ActionTask 自动填充）
    reason:    str (可选)                可选；终止原因摘要（取消、外部 setTaskError 等场景）
```

**taskId 取值时机**：`taskBuild` 时一次性快照，整队后续事件复用快照值。不要在每条事件里重新调用 `Module.getTaskId()`，避免任务切换瞬间漂移。

**actionId 生成策略**：`ActionTask` 在 `build()/extend()` 时自动生成 `f"{actionType}-{short_uuid}"`（如 `"jackHeight-7c4a"`）；业务侧通常不需要关心。如需自定义可在 ActionBase 子类构造时显式设 `self.action_id = "..."`。

### 4.5 actionParameters 精简约定

`actionParameters` 直接进入日志落盘并被分析器展示，遵循：

- **只保留能帮助人判断这条动作做了什么的关键字段**（站点 id、目标值、数量、方向、超时等）
- **排除 Container / Pose / 大数组等大对象**，必要时用摘要替代（`"containerCount": 3` 而非整数组）
- **禁止塞入枚举实例、numpy 标量、自定义对象** —— 转为 `int` / `float` / `bool` / `str` 后再塞
- 动作无参数时写 `"actionParameters": {}`，不要省略键

**自动捕获（推荐）**：使用 `syspy.lib.action_task.ActionBase` 时，`args_summary()` 默认基于 `__init__` 形参名反射捕获同名实例属性，并自动过滤大对象 / 非 JSON 友好类型。子类只需遵守 "`__init__` 形参名 = 实例属性名" 的约定，无需手写。仅在以下场景才覆写：

- 入参名与属性名不一致（如入参叫 `target`，存为 `self.height`）
- 摘要需要计算 / 改名 / 加单位（如把 `angle_rad` 转成 `"angleDeg": int(math.degrees(...))`）
- 摘要中需要包含非 `__init__` 的运行时字段

### 4.6 推进规则与并行调度

`ActionTask` 维护三个集合：`pending`（`init` 状态）、`active`（`running` / `suspended`）、`terminal`（`finished` / `failed`）。每 tick 由 scheduler 决定将哪些 `pending` action 转入 `active`：

- 取 `pending` 队首 action，根据其 `blockingType` 决策启动条件：
  - **`HARD`**：`active` 必须为空 → 弹出并启动（`actionStateChanged: init -> running`）
  - **`SOFT` / `NONE`**：`active` 中不存在 `HARD` action，且其前面的 pending action 都已启动 → 弹出并启动
  - 否则：留在 pending 队首，本 tick 不启动
- 已启动的 action 各自在 `run(ctx)` 中推进自己的状态；scheduler 检测到状态转移就发 `actionStateChanged`
- 任一 active action 转 `failed`：scheduler **取消其他 active**（调用 `cur.cancel()`），整队落 `taskFailed`
- 所有 action 都进入 `finished` 终态（且无 `failed`）：落 `taskFinished`

时序保证：
- 同一 actionId 上，`init -> running`、`running -> finished/failed`、`running <-> suspended` 转移**各发一条 `actionStateChanged`**
- 中间态（`running` 持续）**不打事件 Trace.log**，数值时序用 `Trace.log(dict)`（见 §4.8）
- 动态扩展时，先发 `taskExtend`，再按正常规则启动新 action（发对应的 `actionStateChanged: init -> running`）
- 整队重跑：重新调用 `ActionTask.build()` 发新 `taskBuild`；新一轮 `actionId` 重新生成

### 4.7 ActionTask 标准实现

队列调度与全部结构化事件落盘已封装到 `syspy.lib.action_task.ActionTask`，业务侧不再手写事件代码。

#### 4.7.1 ActionBase 子类约定

动作类**不携带** `blocking_type`。同一动作可在不同任务中被装配为串行或并行，由调用方在 `build()/extend()` 时指派。

```python
from syspy.lib.action_task import ActionBase, ActionStatus


class JackHeight(ActionBase):
  def __init__(self, motor_name: str, target_height: float):
    super().__init__()
    self.motor_name = motor_name
    self.target_height = target_height
    # actionParameters 自动产出 {"motor_name": "...", "target_height": 1.25}

  def run(self, m):
    if self.action_status == ActionStatus.RUNNING:
      Motor.setMotorPosition(self.motor_name, self.target_height, ...)
      if Motor.isMotorReached(self.motor_name):
        self.action_status = ActionStatus.FINISHED

  def result_description(self) -> dict:
    """FINISHED 时随 actionStateChanged 落盘的业务结果摘要（可选覆写）。"""
    return {"actualHeight": Motor.getMotorPos(self.motor_name)}

  # 可选：suspend()/resume()/cancel() 默认仅切状态，子类按需覆写硬件副作用
  def suspend(self):
    super().suspend()
    Motor.stopMotor(self.motor_name)
```

约定：
- 不要在动作类里写 `blocking_type` 或在 `super().__init__()` 传它 —— `ActionTask` 装配时会指派
- `__init__` 形参名 = 实例属性名（`actionParameters` 自动捕获）
- 大对象用 `self._xxx`（不被自动收集）
- `run(ctx)` 推进状态：`FINISHED` 表示成功，`FAILED` 配合 `self.fail_reason = "..."` 表示失败

#### 4.7.2 ActionTask 使用模式

`build()` / `extend()` 支持三种逐项形态，可在同一次装配中混用：

| 形态 | 含义 |
|------|------|
| `Action(...)`                              | 取本次调用的 `blocking_type` 缺省值 |
| `(Action(...), "NONE")` / `(Action(...), "SOFT")` / `(Action(...), "HARD")` | 该 action 指派为指定阻塞类型，覆盖缺省 |

调用形式：

```python
from syspy.lib.action_task import ActionTask, ActionStatus


class Jack(ModuleBase):
  MOD = "jack"

  def __init__(self):
    super().__init__()
    self.queue = ActionTask(mod=self.MOD)

  def init_args(self, args):
    # 串行装配（缺省 HARD）：与历史顺序队列等价
    self.queue.build([
      JackHeight("jackMotor", 1.25),
      Spin(math.pi / 2, "robot"),
    ])

    # 并行装配：本次整批默认 NONE（顶升与旋转可同时进行）
    # self.queue.build(
    #     [JackHeight("jackMotor", 1.25), Spin(math.pi / 2, "robot")],
    #     blocking_type="NONE",
    # )

    # 混合装配：批默认 HARD，但其中一条声明为 NONE，可与下一条并行
    # self.queue.build([
    #     (FillLight(enabled=True), "NONE"),    # 与下一条并行
    #     RecShelf("shelf.rec"),                # 取批默认 HARD
    # ])

    # 单个动作时可省略 [ ]
    # self.queue.build(JackHeight("jackMotor", 1.25))

  def on_rec_result(self, result):
    # 运行中追加同样支持三种形态
    self.queue.extend(BindContainer(...))
    # self.queue.extend([(MotorA(...), "NONE"), (MotorB(...), "NONE")])

  def run(self):
    # 每 tick 推进；actionStateChanged / taskFinished / taskFailed 由 step() 内部按需发出
    self.queue.step(self)
    if self.queue.is_done:
      self.status = (ScriptStatus.FAILED
                     if self.queue.status == ActionStatus.FAILED
                     else ScriptStatus.FINISHED)

  def suspend(self): self.queue.suspend()  # 所有 active action 发 running -> suspended

  def resume(self):  self.queue.resume()  # 所有 suspended action 发 suspended -> running

  def cancel(self):  self.queue.cancel()  # 取消所有 active，整队 -> taskFailed
```

#### 4.7.3 ActionTask 行为保证

`ActionTask` 内部保证以下不变量，业务无需自行实现：

- 事件齐全：`taskBuild` 起点、`taskFinished` / `taskFailed` 终点（互斥、只发一次）；每个 `actionId` 在每次状态转移时发一条 `actionStateChanged`
- 字段合规：`total` / `taskId` 在每条事件携带；`actionParameters` 已经过类型过滤（拒绝大对象、非 JSON 类型）
- `actionId` 唯一：`build()` / `extend()` 时自动生成 `f"{actionType}-{short_uuid}"`，全队不重复
- taskId 一致性：`build()` 时一次性快照 `Module.getTaskId()` 到 `self.task_id`，整队事件全部复用该快照
- extend 自动促级：INIT / 终态调用 `extend(...)` 时，自动转发 `build(...)` 发 `taskBuild`，避免 wire 上出现孤立 `taskExtend`
- 并行调度：按 `blocking_type`（`HARD` / `SOFT` / `NONE`）三类分别处理 active 启动条件
- 暂停 / 恢复：`suspend()` 把所有 `running` action 切到 `suspended`（每条发 `actionStateChanged`），`resume()` 反向；同时落一条 `<MOD>` 通道文本日志（§2.4 "队列暂停/恢复"）
- 取消：`cancel()` 把所有 active action 推到 `failed`（各自发 `actionStateChanged: running -> failed`），整队落 `taskFailed`
- 入参形态：`build()` / `extend()` 接受单个 `ActionBase`、`(ActionBase, "HARD"/"SOFT"/"NONE")` 元组，或它们的列表；批默认通过 `blocking_type=` 关键字参数指定（缺省 `"HARD"`）

### 4.8 队列状态走数值通道

事件流描述"什么时候发生了什么"，数值通道描述"现在的快照"。每 tick 主循环末尾：

```python
counts = self.queue.status_counts()      # {"init": int, "running": int, "finished": int, "failed": int, "suspended": int}
Trace.log(
    {
        "scriptStatus":   int(self.script_status),
        "total":          int(self.queue.total),
        "runningCount":   int(counts["running"]),
        "waitingCount":   int(counts["init"]),       # 已入队、未触发
        "finishedCount":  int(counts["finished"]),
        "failedCount":    int(counts["failed"]),
        "suspendedCount": int(counts["suspended"]),
    },
    output_console=False,
    name=f"{self.MOD}.task",
)
```

字段类型稳定为 `int`，与 §3.1 类型约束一致。并行场景下"当前在跑的 action"是集合而非单值，因此用 5 个 count 表达整个队列的状态分布。

### 4.9 反模式（禁止）

```python
# 错误：每个 tick 都打印 action 状态（高频刷屏；数值通道已经表达）
Trace.log({"event": "actionStateChanged", "actionId": id, "status": "running"}, name="jack.action")
# 状态没变化时不要发 actionStateChanged

# 错误：同一状态重复发（必须只在 transition 时发一次）
if cur.action_status == ActionStatus.RUNNING:
    Trace.log({"event": "actionStateChanged", "status": "running", ...}, ...)

# 错误：动态追加动作不发 taskExtend —— 分析器不知道队列被加长
self.queue.action_list.append(new_action)
# 必须走 self.queue.extend([new_action]) 发 taskExtend

# 错误：actionId 漂移 / 重新编号
self.queue.action_list[0].action_id = "new-id"   # 一旦 taskBuild 分配，不得变更

# 错误：actionParameters 塞大对象
Trace.log({"event": "taskBuild", "actions": [{"actionParameters": {"containers": [...long list...]}}]})

# 错误：status 用整数而非字符串
Trace.log({"event": "actionStateChanged", "status": 1, ...})  # 必须是 "running"

# 错误：不写 name= 关键字，走缺省裸通道
Trace.log({"event": "taskBuild", ...})    # 必须加 name="jack.action"
Trace.log({"runningCount": 2}, output_console=False)   # 必须加 name="jack.task"

# 错误：status 用协议未定义的字符串
Trace.log({"event": "actionStateChanged", "status": "initializing", ...})   # 仅允许 init/running/finished/failed/suspended

# 错误：剩余 active action 失败时不取消其他并行 action
# scheduler 必须在 taskFailed 之前把同批 active 全部 cancel()，否则它们会继续运行造成失控
```

---

## 五、Module.reportInfo 规范

### 5.1 记录原则

- **不打印、不落盘**：仅用于调度系统和 Roboshop 实时展示
- **合并上报**：同一时刻的相关数据合并为一次调用，禁止拆分为多次
- **结构化数据**：字典，字段语义明确

### 5.2 调用时机

| 时机 | 说明 |
|------|------|
| 任务状态变更 | running / finished / failed / suspended |
| 关键动作完成 | 取货完成、放货完成、到达站点 |
| 异常上报 | 需要调度介入的异常 |

### 5.3 必须上报的字段：containers

每次 `Module.reportInfo` 调用都必须携带 `containers` 字段（即使无货也要上报空载状态）。该字段由调度软件 / Roboshop 用于实时显示载货状态，**不允许遗漏**。

通过 `Container.getContainers()` 获取，直接赋值即可：

```python
Module.reportInfo({
    ...,
    "containers": Container.getContainers(),
})
```

#### containers 字段结构

`containers` 为 `array[object]`，每个对象描述一个容器位：

| 字段名      | 类型   | 描述 | 可缺省 |
|------------|--------|------|--------|
| containerId | string | 容器编号。<br/>料箱车：背篓多个从 `"0"` 起递增，货叉用 `"999"`；<br/>顶升车 / 叉车 / 辊筒车：通常 1 个，从 `"0"` 起递增 | 否 |
| desc        | string | 货物描述信息（通常为空） | 是 |
| goodsName   | string | 货物名称 | 是 |
| hasGoods    | bool   | 是否有货 | 否 |

#### 各车型 containerId 约定

| 车型 | containerId 约定 |
|------|------------------|
| 料箱车（背篓） | `"0"`, `"1"`, `"2"`, ... 按背篓位递增 |
| 料箱车（货叉） | `"999"` |
| 顶升车 | `"0"`（通常单容器位） |
| 叉车   | `"0"`（通常单容器位） |
| 辊筒车 | `"0"`（通常单容器位） |

### 5.4 格式规范

```python
# 错误：拆分为多次上报，且未携带 containers
Module.reportInfo({"goStraightStatus": "finished"})
Module.reportInfo({"goDist": dist})

# 正确：合并为一次上报，并附带 containers
Module.reportInfo({
    "action":     "GoStraightDist",
    "status":     "finished",
    "distance":   dist,
    "elapsed":    elapsed,
    "containers": Container.getContainers(),
})
```

### 5.5 标准上报结构

```python
Module.reportInfo({
    "action":     str,    # 当前动作名称
    "status":     str,    # "running" | "finished" | "failed"
    "progress":   float,  # 0.0 ~ 1.0 进度（可选）
    "detail":     dict,   # 动作相关详细数据（可选）
    "error":      str,    # 错误描述（仅 failed 时）
    "containers": list,   # 容器/载货状态，必须，使用 Container.getContainers() 获取
})
```

### 5.6 常见反模式

```python
# 错误：手工拼装 containers，字段名/类型可能不一致
Module.reportInfo({
    "action": "Pick",
    "containers": [{"id": "0", "loaded": True}],  # 字段名错误
})

# 错误：仅在有货时才带 containers，空载时漏报
if has_goods:
    Module.reportInfo({"action": "Pick", "containers": Container.getContainers()})
else:
    Module.reportInfo({"action": "Pick"})  # 缺失，调度端无法刷新空载状态

# 正确：无论有无货，containers 字段始终携带
Module.reportInfo({
    "action":     "Pick",
    "status":     "finished",
    "containers": Container.getContainers(),
})
```

---

## 六、print() 规范

### 6.1 核心规则

- **生产代码禁止裸 print()**
- 仅允许通过 `debug_print()` 封装使用，且受 `debug_mode` 开关控制
- 提交代码前应移除所有调试用 print

### 6.2 允许的使用方式

```python
def debug_print(*args, **kwargs):
    """仅在 debug_mode 开启时打印，不落盘"""
    if ConfigParams.debug_mode:
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[DEBUG {timestamp}]", *args, **kwargs)
```

---

## 七、日志分级

通过 name 后缀和文案前缀共同表达级别：

```python
Trace.log("配置加载完成 ...",        name="jack")      # INFO（默认）
Trace.log("警告: 高度偏差过大 ...",   name="jack")      # WARN（msg 内显式标注）
Trace.log("电机通信超时 ...",         name="jack.err")  # ERROR（走 .err 通道）
```

`*.err` 通道用于异常事件，便于检索与告警系统对接。

## 八、实施检查清单

新增或修改代码时按以下清单自查：

- [ ] 每条 `Trace.log` 均以 **关键字参数** 显式指定 `name=`（不依赖默认值 `"log"`，避免落盘到裸 `log` 通道）
- [ ] 业务 `name` 即落盘通道名，按"模块.子主题"组织（不带 `log.` 前缀）
- [ ] `Trace.log` 的 `msg` 形态：事件描述用 `str`；需要按字段检索的结构化事件用 `dict`；数值时序用 `dict` 并设 `output_console=False`（§三）
- [ ] 不再使用已弃用的 `Trace.chart`；数值 / 图表数据统一改用 `Trace.log(dict, output_console=False, name=...)`
- [ ] `debug=True` 仅用于生产默认沉默、按需打开的诊断日志/数据；必须事件（§2.4）保持 `debug=False`；同一通道不混用
- [ ] 每条 Trace.log 都指定明确的 `name` 通道（`<module>` / `<module>.xxx`）
- [ ] 每个状态机切换都有且仅有一条 Trace.log
- [ ] 每个 try/except 块中最多一条 Trace.log 记录异常，走 `<module>.err` 通道
- [ ] 循环体内无无条件文本 Trace.log（使用去重或仅记录首尾）
- [ ] 同一个 `name` 的数值 `Trace.log(dict)` 推荐集中在主循环末尾调用（允许多处，但需保证类型约束）
- [ ] 同一个 `name` 的数值 `Trace.log(dict)` 下，每个 key 的 value 类型保持稳定（不出现类型切换）
- [ ] 数值 `Trace.log(dict)` 的 value 仅为 int / float / bool / dict，无 None / str / list / 枚举对象
- [ ] Action 队列使用 `syspy.lib.action_task.ActionTask`（新脚本一律走 ActionTask，不手写事件代码）
- [ ] Action 队列事件统一使用 `Trace.log(dict, name=f"{MOD}.action")`，每条事件带 `event` 字段作为类型判别器
- [ ] Action 队列：每个 `actionId` 的状态转移（`init -> running`、`running -> finished/failed`、`running <-> suspended`）各发一条 `actionStateChanged`；同一状态不重复发
- [ ] Action 队列：`taskBuild`（起点）/ `taskExtend`（每次动态追加，仅尾部）/ `taskFinished` 或 `taskFailed`（终点，互斥）各司其职，动态追加动作必须先发 `taskExtend`
- [ ] Action 队列：`actionId` 为字符串、`taskBuild`/`taskExtend` 分配后不变；`actionParameters` 精简摘要，不塞大对象（使用 ActionBase 自动捕获时遵守 `__init__` 形参名 = 实例属性名约定）
- [ ] Action 队列：每条事件必带 `taskId`（来自 `Module.getTaskId()`，在 `taskBuild` 时快照，整队复用，不要逐事件重取）
- [ ] Action 队列：`blocking_type` 由 `ActionTask.build()` / `extend()` 调用方按本次任务装配指派（批默认 `blocking_type=` 关键字参数；逐项可用 `(action, "NONE"/"SOFT"/"HARD")` 元组），动作类本身不携带
- [ ] Action 队列：`actionStateChanged.status` 必须是字符串枚举 `"init" / "running" / "finished" / "failed" / "suspended"`，不要传整数
- [ ] Action 队列：暂停/恢复通过 `ActionTask.suspend()/resume()` 委托，不手写结构化事件
- [ ] ActionBase 子类：`suspend()`/`resume()` 覆写时先调 `super()`，再处理硬件副作用（停电机、重发指令等）
- [ ] Module.reportInfo 同一时刻的数据合并为一次调用，且携带 `containers`
- [ ] 无裸 print()，调试打印使用 debug_print 并受开关控制
