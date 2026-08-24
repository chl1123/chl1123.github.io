# ActionTask 开发指南

> 本文是脚本仓库的实现指南。公共日志字段、通道名和生命周期约束以 [Module 日志记录规范](../spec/logging.md) 为准；本文不扩展 wire 协议。

## 1. 适用范围

标准车型脚本使用 `syspy.lib.action_task.ActionTask` 管理需要排队、并行、暂停、恢复或取消的动作。业务动作继承 `ActionBase`，模块负责装配队列并在主循环中推进。

实现目标：

- 业务动作只表达一个可观察的步骤；
- 队列负责动作顺序、阻塞关系、状态转移和终态；
- 结构化日志由队列基础设施统一产生，业务动作不手写 Action 事件；
- 业务代码只提供动作参数、执行反馈、结果摘要和必要的硬件补偿。

一个队列实例对应一个公共协议中的 `TaskStream`；事件顺序、通道和字段以 [Module 日志记录规范](../spec/logging.md) 第 4 节为准。

## 2. 基本类型

### 2.1 `ActionStatus`

`ActionStatus` 是脚本内部使用的状态枚举，对外日志会转换为字符串：

| 内部状态 | 日志 status |
|----------|-------------|
| `INIT` | `init` |
| `RUNNING` | `running` |
| `FINISHED` | `finished` |
| `FAILED` | `failed` |
| `SUSPENDED` | `suspended` |

业务动作通过修改 `action_status` 表达状态结果，不直接调用 `Trace.log` 写 `actionStateChanged`。

### 2.2 `ActionBase`

动作类通常实现以下成员：

| 成员 | 用途 |
|------|------|
| `__init__(...)` | 保存动作所需的关键输入。参数名与同名实例属性保持一致时，可自动生成 `ActionParameters` 摘要。 |
| `run(ctx)` | 每个主循环 tick 推进动作；成功时设为 `FINISHED`，失败时设为 `FAILED` 并填写 `fail_reason`。 |
| `result_description()` | 可选；动作完成时返回小型 `ResultDescription`。 |
| `action_description()` | 可选；返回人读补充说明。 |
| `suspend()` / `resume()` | 可选；覆写时先调用父类，再处理硬件停止或重发指令。 |
| `cancel()` | 可选；覆写时必须释放本动作持有的硬件或资源。 |

动作类不声明 `blocking_type` 作为业务固有属性。同一个动作在不同任务中可以按不同阻塞类型装配。

## 3. 队列装配

### 3.1 创建队列

模块创建队列时传入稳定车型前缀：

```python
from syspy.lib.action_task import ActionBase, ActionStatus, ActionTask


class Jack(ModuleBase):
    MOD = "jack"

    def __init__(self):
        super().__init__()
        self.queue = ActionTask(mod=self.MOD)
```

队列的结构化事件会写入 `{MOD}.taskActions`。不要在业务代码中另建 `.action` 通道。

### 3.2 `build()`

`build()` 建立一轮新的动作队列并产生 `taskBuild`。支持：

- 单个 `ActionBase`；
- `ActionBase` 列表；
- `(action, "HARD")`、`(action, "SOFT")` 或 `(action, "NONE")` 元组；
- `blocking_type=` 作为整批动作的默认值，默认是 `"HARD"`。

```python
self.queue.build([
    JackHeight("jackMotor", 1.25),
    Spin(math.pi / 2, "robot"),
])

self.queue.build(
    [JackHeight("jackMotor", 1.25), Spin(math.pi / 2, "robot")],
    blocking_type="NONE",
)

self.queue.build([
    (FillLight(enabled=True), "NONE"),
    RecShelf("shelf.rec"),
])
```

### 3.3 `extend()`

`extend()` 只能向运行中队列的尾部追加动作，并产生 `taskExtend`。如果队列尚未建立或已经结束，基础设施会将调用转为新一轮 `build()`，避免产生没有起点的孤立扩展事件。

```python
self.queue.extend(BindContainer(container_id))
self.queue.extend(
    [(MotorA(...), "NONE"), (MotorB(...), "NONE")]
)
```

业务代码不得直接修改 `action_list` 追加动作，也不得在动作进入日志后重新设置 `action_id`。

## 4. 阻塞调度

队列按动作的 `blocking_type` 决定待执行动作何时启动：

| blocking type | 行为 |
|---------------|------|
| `HARD` | 独占队列；只有当前没有 active 动作时才能启动。 |
| `SOFT` | 当前没有 `HARD` 动作时可与其他非 `HARD` 动作并行。 |
| `NONE` | 在没有 `HARD` 动作阻塞时可并行启动。 |

`HARD` 是默认值，适用于需要保持历史顺序语义的动作。阻塞类型由队列装配方决定，不由动作类决定。

## 5. 主循环推进

模块每个 tick 调用一次 `step()`，把模块实例作为上下文传给动作：

```python
def run(self):
    self.queue.step(self)
    if self.queue.is_done:
        self.status = (
            ScriptStatus.FAILED
            if self.queue.status == ActionStatus.FAILED
            else ScriptStatus.FINISHED
        )
```

`step()` 负责：

1. 按阻塞关系启动 `INIT` 动作；
2. 调用 active 动作的 `run(ctx)`；
3. 检测状态转移并产生 `actionStateChanged`；
4. 失败时取消其他 active 动作并产生 `taskFailed`；
5. 全部成功时产生 `taskFinished`。

动作的 `run()` 必须依据真实反馈推进状态，不能只因为命令已经发送就设为 `FINISHED`。

## 6. 暂停、恢复和取消

模块将生命周期操作委托给队列：

```python
def suspend(self):
    self.queue.suspend()

def resume(self):
    self.queue.resume()

def cancel(self):
    self.queue.cancel()
```

业务动作覆写这些方法时，必须同时处理硬件副作用：

- `suspend()` 先停止会继续产生运动或输出的设备；
- `resume()` 重新发送必要的指令，并等待反馈恢复；
- `cancel()` 释放动作持有的资源，使动作不会在队列终态后继续运行。

队列取消会把尚未完成的动作推进到失败处理，并以 `taskFailed` 收尾。终态之后不得继续提交动作状态变化。

## 7. 参数与结果摘要

### 7.1 `actionParameters`

自动摘要只收集 `__init__` 中与实例属性同名的关键参数。需要改名、换单位、增加计算字段或排除运行时大对象时，覆写 `args_summary()`：

```python
class JackHeight(ActionBase):
    def __init__(self, motor_name: str, target_height: float):
        super().__init__()
        self.motor_name = motor_name
        self.target_height = target_height

    def args_summary(self) -> dict:
        return {
            "motor": self.motor_name,
            "target": float(self.target_height),
        }
```

摘要必须符合公共协议中的 `ActionParameters`，是小型、可序列化的 JSON 结构。不要放入完整容器、轨迹、点云、protobuf 或自定义对象。

### 7.2 `resultDescription`

`result_description()` 只返回公共协议中的 `ResultDescription`，即完成动作所需的小型结果摘要，例如实际高度、识别结果摘要或最终位置。失败信息使用 `fail_reason` 和 `error_code`，不要把错误文本重复写入多个日志通道。

## 8. 任务 ID 与 Action ID

脚本队列的 `taskId` 来自 MF 通过 `scriptExecute` 传入的字符串。队列建立时锁存该值，之后该轮所有事件复用同一个值。

脚本队列中的 `actionId` 由基础设施在 `build()` / `extend()` 时分配为字符串。它只在脚本队列内要求唯一，不等于 MF 外层任务 ID，也不等于 MF 的 `RunScript.actionId`。跨层关联规则和日志字段以 [公共日志规范](../spec/logging.md) §4 为准。

## 9. 数值快照

队列事件描述“何时发生了什么”，数值通道描述“当前是什么状态”。需要图表或实时趋势时，在模块主循环固定位置输出 `<MOD>.task` 快照；建议包含：

- `scriptStatus`；
- `total`；
- `runningCount`；
- `waitingCount`；
- `finishedCount`；
- `failedCount`；
- `suspendedCount`。

所有字段类型必须稳定，数值快照不得代替状态转移事件。

## 10. 开发检查清单

- [ ] 动作只实现业务步骤和真实反馈，不手写 Action 结构化日志。
- [ ] 动作类不携带固定 `blocking_type`，由 `build()` / `extend()` 装配时指定。
- [ ] `actionParameters` 是精简、可 JSON 序列化的摘要。
- [ ] `run()` 可在重复 tick 中安全推进，并在完成或失败时明确设置状态。
- [ ] `suspend()`、`resume()`、`cancel()` 处理硬件和资源副作用。
- [ ] 动态追加走 `extend()`，不直接改 `action_list`。
- [ ] 不修改已经分配的 `action_id`。
- [ ] 每个模块使用稳定的 `{MOD}.taskActions` 通道。
- [ ] 每个任务从建立到终态复用同一个脚本 `taskId`。
- [ ] 取消、暂停、恢复、失败和重复任务都不会留下继续运行的动作或设备输出。
