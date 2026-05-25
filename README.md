# Syspy Scripts 仓库上手指南

## 1. 仓库定位

这个仓库包含两类核心内容：

- `syspy/`：机器人 Python SDK（统一接口 + RBK3/RBK4 版本适配 当前版本为3.5.X）。
- `tasks/`：任务脚本（以 `tasks/v3/standard/` 为主，含示例、标定、业务模块）。

可以把它理解为：

- SDK 提供“能力接口层”（导航、定位、电机、识别、参数、异常、日志等）。
- tasks 提供“业务编排层”（把能力按状态机/动作链组织成可执行任务）。

## 2. 目录速览

- `syspy/__init__.py`：对外统一导出模块，并按 `RBK_VERSION` 注入 v3/v4 实现。
- `syspy/config.py`：从 `/opt/.data/rbk/private/version/robokit.json` 读取版本，失败默认 v3。
- `syspy/core/rbk_rpc.py`：RPC 抽象层（`Service`/`Message`、`@call_service`、v3/v4 客户端差异屏蔽）。
- `syspy/lib/module.py`：任务脚本运行时核心（`Module`、`ModuleBase`、`ScriptStatus`、安全检查/Modbus事件）。
- `syspy/lib/action_task.py`：Action 队列调度器（`ActionBase` / `ActionStatus` / `ActionTask`），按 VDA5050 §6.8/§6.11/§6.12 风格调度并产出结构化事件流（`taskBuild` / `actionStateChanged` / `taskFinished` / `taskFailed`）。
- `docs/guide/spec/logging.md`：日志与队列事件落盘规范（`Trace.log` / `Trace.chart` / `Module.reportInfo` / Action 队列协议）。新增脚本必须遵循此规范。
- `syspy/utils/param_server.py`：参数系统（配置参数、输入参数、动作模板、参数校验）。
- `tasks/v3/standard/example/`：脚本模板与参数示例（建议从 `template.py` 开始）。
- `tasks/v3/standard/module/`：复杂业务脚本（如 `jack.py`，使用动作链编排）。
- `tasks/v3/standard/calib/`：标定脚本，偏“单任务小状态机”写法。

## 3. SDK 开发范式（`syspy`）

### 3.1 统一接口 + 版本适配

典型模式是“三层”：

1. `syspy/<module>.py`：定义 `XXXInterface`（抽象接口）。
2. `syspy/v3/<module>.py` 与 `syspy/v4/<module>.py`：分别实现。
3. `syspy/<module>.py` 底部按 `RBK_VERSION` 绑定实例导出（调用方无感知版本差异）。

这保证了业务脚本只写：

```python
from syspy import Navigation, Loc, Motor
```

而不需要显式区分 v3/v4。

### 3.2 Service/Message 双模型

- **Service 类接口**：通过 RPC 调服务（如 `Navigation.resetPath()`）。
- **Message 类接口**：订阅消息并缓存（如 `Controller.getVoltage()`）。

`@default_plugin` + `@call_service` 在 v3/v4 间做参数打包方式适配（v3 偏位置参数，v4 偏关键字参数）。

### 3.3 强状态驱动

`ScriptStatus` 作为任务脚本统一状态枚举：`NONE -> RUNNING -> (FINISHED/FAILED)`，含 `SUSPENDED`。

`Module` 负责：

- 任务参数接收（`Module.getTaskArgs()`）
- 状态上报（`Module.setStatus()`）
- 信息上报（`Module.reportInfo()`）
- 取消/暂停/恢复回调注册
- 安全检查与 Modbus 事件分发

### 3.4 参数系统范式

`ScriptParam`/`ParamBuilder` 提供三种参数资产：

- 配置参数（`builderConfig`，支持 `save(merge=True)` 增量合并）
- 输入参数（`builderInput`，用于任务入参 UI/校验）
- 动作模板（`addAction` + `saveAction`）

脚本运行时常用流程：

1. 全局创建参数定义并保存。
2. `ParamValidator` 或 `script_param.loadInput()` 校验入参。
3. `script_param.loadConfig()` 读取配置。
4. 配置变更回调中热加载配置。

## 4. 任务脚本开发范式（`tasks`）

仓库里主要有 3 种范式，建议按复杂度递进：

### 4.1 最小脚本（校准类常见）

- `Module.init()`
- 注册 `cancel` 回调
- `while True` 轮询执行，`sleep(0.1)`
- 终态后退出或置 `NONE`

适合一次性动作、简单流程。

### 4.2 标准任务脚本（推荐默认）

以 `example/template.py` 为标准形态：

1. 全局定义 Config/Input 参数（必须在全局，便于系统加载）。
2. 继承 `ModuleBase`，实现 `suspend/resume/cancel`（必须）。
3. 主循环按状态机分支：
   - `NONE`：取任务参数并校验，再 `init_args`
   - `RUNNING`：执行 `run`
   - `SUSPENDED`：等待恢复
   - `FAILED/FINISHED`：清理并回到 `NONE`
4. 每次循环上报状态与 `report_info`。

### 4.3 动作链编排脚本（复杂业务）

以 `example/template.py` 为代表：

- 主类负责参数解析、动作队列构建、事件入口。
- 每个动作独立成 `ActionBase` 子类（`run/reset`），由 `syspy/lib/action_task.py` 提供。
- 用 `ActionTask.build()` / `extend()` 装配队列；`blocking_type`（`HARD` / `SOFT` / `NONE`）由调用方在装配时按本次任务指派，动作类本身不携带（同一动作可串可并）。
- 主循环每 tick 调 `task.step(self)`；队列内部按 `docs/guide/spec/logging.md §四` 自动产出 `taskBuild` / `actionStateChanged` / `taskFinished` / `taskFailed` 结构化事件。
- 通过 `Navigation.setTaskError()` / `Navigation.setDeviceError()` 标准化异常上报（`Abnormal` 异常码机制已废弃）

适合取放货、识别+导航+执行器组合流程。

## 5. 仓库内已形成的代码规范（观察总结）

### 5.1 命名与组织

- 类名：`PascalCase`
- 方法/变量：以 `snake_case` 为主；外部参数字段常见 `camelCase`（因对接配置/UI字段）
- 常量：全大写（如异常码范围、路径常量）
- 异常码机制已废弃，更新为errors字典，value为`xx@xxx`格式，如`ms@TargetId`

### 5.2 导入与依赖

- 常见顺序：标准库 -> 第三方 -> `syspy` -> 本地模块
- 任务脚本常在头部记录 `start_time = time.time()` 用于运行时长统计

### 5.3 状态与时序

- 强制显式维护 `ScriptStatus`
- 主循环通常 `time.sleep(0.1)`，避免高 CPU 占用
- 终态后必须重置内部状态，防止下一任务残留

### 5.4 日志与可观测性

- 日志/图表/上报规范以 `docs/guide/spec/logging.md` 为准（含通道命名、`Trace.log/chart` 类型约束、Action 队列结构化事件协议、检查清单），新增或修改脚本前请先对照。
- 过程日志：`Trace.log(...)` / `Logger(...)`
- 结构化上报：`Module.reportInfo(dict)`
- 异常上报（RBK3.5 推荐）：
- 任务异常：`Navigation.setTaskError(key, desc)`
- 设备模型异常：`Navigation.setDeviceError(key, desc, param="")`
- 异常清除：`Navigation.clearTaskError(key)` / `Navigation.clearDeviceError(key)`
- 存在性判断：`Navigation.errorExists(key)`（任务异常或设备异常任一存在即返回 `True`）
- 约定说明（基于 `syspy/navigation.py` 与 `syspy/v3/navigation.py`）：
- `key` 由脚本侧定义，要求同一脚本内稳定且唯一；底层会统一做命名空间封装，脚本层只需传业务 key。
- `desc` 应写“可执行”的排障信息（现象 + 原因 + 建议动作），避免仅写 `failed`/`unknown`。
- `param` 用于设备模型定位（可选），建议传具体设备参数路径，便于实施和售后快速定位。
- 使用建议：
- 可恢复告警：先 `set*Error`，恢复后显式 `clear*Error`，避免异常残留。
- 不可恢复故障：`set*Error` 后进入 `FAILED`，由上层重新下发任务或人工处理。
- 高频循环内上报同一异常前，建议先 `errorExists(key)` 判重，避免重复刷屏。

```python
from syspy import Navigation

# 任务异常：识别失败
if not rec_ok:
    if not Navigation.errorExists("RecFailed"):
        Navigation.setTaskError("RecFailed", "识别失败，请检查识别距离、光照和识别文件配置")

# 故障恢复后清除
if rec_ok and Navigation.errorExists("RecFailed"):
    Navigation.clearTaskError("RecFailed")

# 设备模型异常：电机配置缺失
if not has_lift_motor:
    Navigation.setDeviceError(
        "LIFT_MOTOR_NOT_FOUND",
        "顶升电机未配置，请检查模型文件 Device.Model",
        "Device.Model.liftMotor",
    )
```

### 5.5 参数与配置

- 参数定义尽量集中到 `ConfigParams`/`InputParams`
- 输入参数进入业务前先校验（`ParamValidator` 或 `loadInput`）
- 配置参数支持热更新回调

## 6. 新人上手建议路径

1. 先读 `tasks/v3/standard/example/template.py`，理解标准生命周期。
2. 再看 `tasks/v3/standard/goPath.py`，掌握最小导航脚本写法。
3. 再看 `tasks/v3/standard/module/jack.py`，理解动作链架构；配套阅读 `syspy/lib/action_task.py` 了解 `ActionBase` / `ActionTask` 的调度与事件协议。
4. 通读 `docs/guide/spec/logging.md`，掌握日志/图表/Action 队列结构化事件的落盘规范（提交代码前对照检查清单自查）。
5. 按需查 `syspy/lib/module.py` 与 `syspy/utils/param_server.py` 两个核心基础设施。

## 7. 运行与发布注意事项

- 该代码默认运行环境路径是 `/opt/.data/rbk/resources/scripts/`（见 `syspy/utils/__init__.py`），很多参数文件读写依赖该路径。
- `build_deb.sh` + `build_dir.conf` 用于打增量脚本包，安装目标同样是 `/opt/.data/rbk/resources/scripts`。
- 本地纯 PC 调试可做静态分析/语法检查，但完整联调依赖机器人运行时服务。

## 8. 仿真环境脚本开发推荐（RBK3.5）

### 8.1 先区分“实机能力”和“业务状态机”

- 建议把脚本拆成两层：
- 业务层：状态机、参数解析、异常流转、日志结构。
- 设备层：真实硬件接口调用（传感器、执行器、识别等）。
- 仿真主要替换“设备层输入”，尽量不改“业务层逻辑”，这样实机一致性最好。

### 8.2 优先使用 `@sim_only(on_sim=...)` 做最小替换

- 推荐写法：为“真实接口读取函数”提供同签名 mock，并用 `@sim_only(on_sim=mock_func)` 挂接。
- 实机环境自动走原函数，仿真环境自动走 mock，避免主流程里写大量 `if is_simulation()` 分支。
- 参考文件：
- `syspy/sim.py`：`is_simulation()` 与 `@sim_only` 定义。
- `tasks/v3/standard/example/sim_only_demo.py`：最小示例。


