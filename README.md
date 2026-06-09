# Syspy Scripts 仓库上手指南

## 1. 仓库定位

这个仓库包含两类核心内容：

- `syspy/`：机器人 Python SDK（统一接口 + RBK3/RBK4 版本适配 当前版本为3.5.X）。
- `tasks/`：任务脚本（以 `tasks/v3/standard/` 为主，含示例、标定、业务模块）。

可以把它理解为：

- SDK 提供"能力接口层"（导航、定位、电机、识别、参数、异常、日志等）。
- tasks 提供"业务编排层"（把能力按状态机/动作链组织成可执行任务）。

## 2. 目录速览

- `syspy/__init__.py`：对外统一导出模块，并按 `RBK_VERSION` 注入 v3/v4 实现。
- `syspy/config.py`：从 `/opt/.data/rbk/private/version/robokit.json` 读取版本，失败默认 v3。
- `syspy/core/rbk_rpc.py`：RPC 抽象层（`Service`/`Message`、`@call_service`、v3/v4 客户端差异屏蔽、二进制消息通道 `BinMsgClient`）。
- `syspy/lib/module.py`：任务脚本运行时核心（`Module`、`ModuleBase`、`ScriptStatus`、安全检查/Modbus事件）。
- `syspy/lib/action_task.py`：Action 队列调度器（`ActionBase` / `ActionStatus` / `ActionTask`），按 VDA5050 §6.8/§6.11/§6.12 风格调度并产出结构化事件流（`taskBuild` / `actionStateChanged` / `taskFinished` / `taskFailed`）。
- `syspy/lib/robot.py`：机器人参数与系统错误接口（`RobotParam` / `RobotError`），提供配置/设备参数读取、碰撞检测模型获取、系统错误管理。
- `syspy/lib/trace.py`：统一日志接口（`Trace.log`），已取代 `Trace.chart`。
- `docs/guide/spec/logging.md`：日志与队列事件落盘规范（`Trace.log` / `Module.reportInfo` / Action 队列协议）。新增脚本必须遵循此规范。
- `syspy/utils/param_server.py`：参数系统（配置参数、输入参数、动作模板含 `stage` 字段、参数校验）。
- `tasks/v3/standard/example/`：脚本模板与参数示例（建议从 `template.py` 开始）。
- `tasks/v3/standard/module/`：复杂业务脚本（如 `jack.py`，使用动作链编排）。
- `tasks/v3/standard/calib/`：标定脚本，偏"单任务小状态机"写法。

## 3. SDK 开发范式（`syspy`）

### 3.1 统一接口 + 版本适配

典型模式是"三层"：

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

#### 二进制消息通道

V3 RPC 客户端新增独立 ZMQ 二进制通道（`BinMsgClient`），绕过 JSON-RPC + protobuf JSON 双重序列化，直接传输 protobuf 二进制数据，显著降低 CPU 占用。默认模式为 `"raw"`，失败时自动降级为 `"json"` 模式。

```python
# 内部机制（调用方无感知）
class V3RpcClient(RpcClient):
    _MODE: str = "raw"  # "raw" = 二进制; "json" = JSON-RPC 降级

    def get_message(self, topic, model_class, plugin="RBKSim"):
        if V3RpcClient._MODE == "raw":
            bin_data = self._get_bin_client().get_message(topic, plugin)
            msg = model_class()
            msg.ParseFromString(bin_data)  # 直接 protobuf 二进制反序列化
            return msg
```

#### 系统错误接口（`RobotError`）

`RobotError` 提供机器人系统错误管理，与 `Navigation.setTaskError/setDeviceError`（任务/设备异常）互补，用于上报脚本侧检测到的系统级错误：

```python
from syspy import RobotError

# 设置系统错误（clear=True 时可清除，clear=False 时需人工介入）
RobotError.setSystemError("LiftTimeout", "顶升超时，请检查电机状态", clear=True)

# 查询系统错误是否存在
if RobotError.existSystemError("LiftTimeout"):
    pass

# 清除系统错误
RobotError.clearSystemError("LiftTimeout")
```

**key 命名空间规则**：`clear=True` 时底层自动加 `py@` 前缀（可清除），`clear=False` 时加 `ss@Py` 前缀（不可清除，需人工介入）。脚本层只需传业务 key。

#### Message 接口返回值约定

所有 Message 类接口的 getter 方法（即通过 `self.update()` 获取数据的模式）返回值类型统一标注为 `Optional[T]`。当数据不可用（如机器人未启动、消息未到达）时，方法返回 `None`而非零值或空集合，避免语义混淆。

```python
# 签名示例
def getSpeeds(self) -> Optional[Tuple[float, float, float]]:
    if self.update():
        return self.data.x, self.data.y, self.data.rotate

# 调用方必须对 None 做防御
speeds = NavSpeed.getSpeeds()
if speeds is None:
    # 数据不可用，走安全逻辑
    return
vx, _, vw = speeds
```

**涉及模块**：Battery、Controller、NavStatus、NavSpeed、Odometer、Loc、Di、Do、Sound、Laser3D、Rfid、Magnetic、CodeScanner、Bin、ScriptData。

**不返回 Optional 的方法**（有自身 fallback 逻辑或非 update 模式）：

- `Di.getDi()` / `Do.getDo()`：数据不可用时返回 `False`
- `NavStatus.getChassisStop()`：RPC 调用，非 update 模式
- `NavStatus.getTurn()`：纯计算方法，永远返回 `int`
- `Message.getData()`：数据不可用时返回 `{}`

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

#### 动作模板 `stage` 字段

`addAction` 的 `stage` 参数定义脚本执行阶段，控制脚本与导航的时序关系：

| stage | 含义 |
|-------|------|
| 0 | 在前置点执行脚本，脚本完成后开始导航 |
| 1 | 在前置点执行脚本，脚本和导航同时运行 |
| 2 | 在目标点执行脚本（默认） |
| 3 | 在前置点执行脚本，后续导航由脚本控制 |

```python
param_loader.addAction(
    action_name="load",
    policy={"goodsDir": 90},
    args={"operation": "load", "operation.load.height": 0.02},
    config={"load.recognize": "on"},
    stage=3  # 前置点执行，脚本控制后续导航
)
```

#### `RobotParam` 机器人参数接口

`RobotParam` 提供机器人配置/设备参数读取、碰撞检测模型获取、参数变更回调等能力：

```python
from syspy import RobotParam

# 读取配置参数
rec_obj = RobotParam.getConfig("recognition", "recognitionObject")

# 读取设备模型参数
lift_motor = RobotParam.getDevice("Model-000", "moduleType.liftFork.liftMotor")

# 获取启用的设备列表
laser_list = RobotParam.getDeviceList("Laser")

# 获取碰撞检测模型 / 扣除模型 / DO区域
collision = RobotParam.getCollisionModel()
deduct = RobotParam.getDeductModel()
do_region = RobotParam.getDoRegion()

# 配置参数变更回调（支持延迟注册）
RobotParam.setConfigChangeCallBack(on_config_changed)

# 设备参数变更回调（支持延迟注册）
RobotParam.setDeviceChangeCallBack(on_device_changed)
```

脚本运行时常用流程：

1. 全局创建参数定义并保存。
2. `ParamValidator` 或 `script_param.loadInput()` 校验入参。
3. `script_param.loadConfig()` 读取配置。
4. 配置变更回调中热加载配置。

### 3.5 国际化支持（`_TR`）

`_TR` 提供脚本文本翻译接口，运行时直接返回原文，翻译由 RBK 系统层在编译时完成：

```python
from syspy import _TR

# 简单文本
print(_TR("Hello World"))  # 运行时返回 "Hello World"

# f-string 参数化（编译后 rbk.ts 中为 "Hello World, {1}, {2}"）
param1, param2 = 1, 2
print(_TR(f"Hello World, {param1=}, {param2=}"))
```

RBK 编译后 `rbk.ts` 文件自动增加翻译条目，手动编辑即可完成翻译：

```
Hello World ~-~ 你好，世界
Hello World, {1}, {2} ~-~ 你好，世界, {1}, {2}
```

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
- 异常码机制已废弃，更新为errors字典，value为`xx@xxx`格式，如`py@TargetId`
- 错误码前缀：脚本侧上报的系统错误自动加 `py@` 前缀，不可清除的加 `ss@Py` 前缀

### 5.2 导入与依赖

- 常见顺序：标准库 -> 第三方 -> `syspy` -> 本地模块
- 任务脚本常在头部记录 `start_time = time.time()` 用于运行时长统计
- 国际化文本使用 `_TR()` 包裹，RBK 编译时自动提取到 `rbk.ts` 翻译文件

### 5.3 状态与时序

- 强制显式维护 `ScriptStatus`
- 主循环通常 `time.sleep(0.1)`，避免高 CPU 占用
- 终态后必须重置内部状态，防止下一任务残留

### 5.4 日志与可观测性

- 日志/图表/上报规范以 `docs/guide/spec/logging.md` 为准（含通道命名、`Trace.log` 类型约束、Action 队列结构化事件协议、检查清单），新增或修改脚本前请先对照。
- **`Trace.chart()` 已弃用**，统一改用 `Trace.log()`：
  - `Trace.log` 的 `msg` 参数同时支持 `str`（文本日志）和 `dict`（数值时序/图表数据），传 str 时自动包装为 `{"log": msg}` 落盘
  - `output_console` 默认值从 `chart` 的 `False` 改为 `log` 的 `True`
  - 数值图表数据改用 `Trace.log(dict, output_console=False, name="xxx")` 上报
  - 按 `name` 参数分通道落盘
  - `debug=True` 时仅在 debug 模式下落盘
- 过程日志：`Trace.log(...)` / `Logger(...)`
- 结构化上报：`Module.reportInfo(dict)`
- 异常上报（RBK3.5 推荐）：
  - 任务异常：`Navigation.setTaskError(key, desc)`
  - 设备模型异常：`Navigation.setDeviceError(key, desc, param="")`
  - 系统错误：`RobotError.setSystemError(key, desc, clear=True)`
  - 异常清除：`Navigation.clearTaskError(key)` / `Navigation.clearDeviceError(key)` / `RobotError.clearSystemError(key)`
  - 存在性判断：`Navigation.errorExists(key)` / `RobotError.existSystemError(key)`
- 约定说明（基于 `syspy/navigation.py` 与 `syspy/v3/navigation.py`）：
  - `key` 由脚本侧定义，要求同一脚本内稳定且唯一；底层会统一做命名空间封装，脚本层只需传业务 key。
  - `desc` 应写"可执行"的排障信息（现象 + 原因 + 建议动作），避免仅写 `failed`/`unknown`。
  - `param` 用于设备模型定位（可选），建议传具体设备参数路径，便于实施和售后快速定位。
- 使用建议：
  - 可恢复告警：先 `set*Error`，恢复后显式 `clear*Error`，避免异常残留。
  - 不可恢复故障：`set*Error` 后进入 `FAILED`，由上层重新下发任务或人工处理。
  - 高频循环内上报同一异常前，建议先 `errorExists(key)` 判重，避免重复刷屏。

```python
from syspy import Navigation, RobotError

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

# 系统错误：顶升超时
RobotError.setSystemError("LiftTimeout", "顶升超时，请检查电机状态", clear=True)
if RobotError.existSystemError("LiftTimeout"):
    RobotError.clearSystemError("LiftTimeout")
```

### 5.5 参数与配置

- 参数定义尽量集中到 `ConfigParams`/`InputParams`
- 输入参数进入业务前先校验（`ParamValidator` 或 `loadInput`）
- 配置参数支持热更新回调（`setConfigChangeCallBack` / `setDeviceChangeCallBack`）

## 6. 新人上手建议路径

1. 先读 `tasks/v3/standard/example/template.py`，理解标准生命周期。
2. 再看 `tasks/v3/standard/goPath.py`，掌握最小导航脚本写法。
3. 再看 `tasks/v3/standard/module/jack.py`，理解动作链架构；配套阅读 `syspy/lib/action_task.py` 了解 `ActionBase` / `ActionTask` 的调度与事件协议。
4. 通读 `docs/guide/spec/logging.md`，掌握日志/图表/Action 队列结构化事件的落盘规范（提交代码前对照检查清单自查）。
5. 按需查 `syspy/lib/module.py` 与 `syspy/utils/param_server.py` 两个核心基础设施。

## 7. 运行与发布注意事项

- 该代码默认运行环境路径是 `/opt/.data/rbk/resources/scripts/`（见 `syspy/utils/__init__.py`），很多参数文件读写依赖该路径。
- 增量包打包当前使用 `build_deb.yml` + `build_deb.sh`。
- 本地纯 PC 调试可做静态分析/语法检查，但完整联调依赖机器人运行时服务。

### 7.1 使用 `submit_pr.sh` 提交 PR

仓库根目录下的 `submit_pr.sh` 适合处理以下 4 类常见场景：

1. 普通 commit PR：从当前分支或指定分支挑一个或多个 commit，自动创建临时 worktree、提交 submit 分支并发起 PR。
2. 单文件 PR：通过 `--path` 只提交某个文件在指定快照下的内容，适合"只提 `syspy/actions.py`"这类场景。
3. 多文件 PR：通过多个 `--path` 把一组相关脚本、配置和文档一起打成一个 PR。
4. 更新已有 PR：通过 `--reuse-branch --update-pr <编号>` 复用已有 submit 分支，强推并同步更新 PR 标题/正文。

常用命令示例：

```bash
# 1) 普通 commit PR
./submit_pr.sh --source-branch mazj 4e8ce316

# 2) 只提交一个文件
./submit_pr.sh \
  --source-branch mazj \
  --path syspy/actions.py \
  --title "feat: m-6998182168 refactor actions rotate flow" \
  HEAD

# 3) 只提交多个文件
./submit_pr.sh \
  --source-branch mazj \
  --path submit_pr.sh \
  --path build_deb.sh \
  --path build_deb.yml \
  --path README.md \
  --title "chore: update pr helper and packaging docs" \
  HEAD

# 4) 更新已有 PR：复用 submit 分支并同步改标题/正文
./submit_pr.sh \
  --source-branch mazj \
  --submit-branch mazj-actions-release-v2 \
  --path syspy/actions.py \
  --reuse-branch \
  --update-pr 8 \
  --title "feat: m-6998182168 refactor actions rotate flow" \
  --body-file pr.md \
  HEAD
```

补充说明：

- `--path` 模式不会 cherry-pick commit，而是把指定文件从源快照复制到 base 分支后生成一个新提交。
- `--path` 模式当前只支持一个 commit/ref，适合"只提一个文件"或"把几个相关文件打成一个 PR"的场景。
- `--base` 默认是 `release`，通常保持默认即可；只有明确要对其他远端分支提 PR 时才需要手动指定。
- `--reuse-branch` 会对 submit 分支执行 `push --force-with-lease`，适合 amend / rebase 后更新已有 PR。

### 7.2 增量包打包方法

当前增量包打包方式是：

- 配置文件：`build_deb.yml`
- 打包脚本：`build_deb.sh`

基本用法：

```bash
./build_deb.sh
./build_deb.sh build_deb.yml
./build_deb.sh /absolute/path/to/your_build.yml
```

`build_deb.yml` 里最常用的字段如下：

```yaml
PackageID: your-package-id
version: 2026.06.09.160000   # 可省略，缺省时自动使用当前时间戳
description: your hotfix
node: master
arch:
  - arm64

files:
  - type: script
    source: ./syspy/actions.py
  - type: script
    source: ./tasks/v3/standard/example/template.py
    # target 可省略；tasks/generic 下会自动去掉 v3/v4 目录层
```

字段说明：

- `PackageID`：增量包唯一标识，必填。
- `version`：包版本号；不填时自动生成时间戳版本。
- `description`：包描述，会体现在最终产物命名里。
- `node`：默认 `master`。
- `arch`：支持 `arm64`、`amd64`、`all`。其中二进制库文件通常不应使用 `all`。
- `files`：要打进增量包的文件列表。

`files` 每项支持两种类型：

- `type: script`
  - `target` 可省略
  - 显式指定时，`target` 相对于 `/opt/.data/rbk/resources/scripts/`
  - 省略时，默认使用 `source` 相对于仓库根目录的路径
  - 如果 `source` 在 `tasks/v3/`、`tasks/v4/`、`generic/v3/`、`generic/v4/` 下，会自动去掉中间这层版本目录
    - 例如 `./tasks/v3/standard/example/template.py` 会自动落到 `tasks/standard/example/template.py`
    - 例如 `./generic/v3/led/standard/behav_led.py` 会自动落到 `generic/led/standard/behav_led.py`
- `type: lib`
  - `target` 必填
  - `target` 相对于 `/opt/data/rbk/`

打包脚本会自动做这些事：

- 校验配置字段和源文件是否存在
- 对 `lib` 文件按 `arch` 做二进制架构检查
- 将文件暂存到 payload 目录后打成 zip
- 调用 `/tmp/rms-plugin-zip/build_package.sh` 生成最终增量包

首次打包时，如本机没有 RMS 打包工具，`build_deb.sh` 会自动从：

```text
https://cnb.cool/seer-robotics/src/tools/rms-plugin-zip.git
```

拉取到：

```text
/tmp/rms-plugin-zip
```

产物默认输出到仓库根目录下形如：

```text
dist_rms_arm64_YYYYMMDDHHMMSS/
```

的目录中。实际使用时建议先复制一份 `build_deb.yml` 再按本次热修或增量内容修改 `files` 列表。

## 8. 仿真环境脚本开发推荐（RBK3.5）

### 8.1 先区分"实机能力"和"业务状态机"

- 建议把脚本拆成两层：
- 业务层：状态机、参数解析、异常流转、日志结构。
- 设备层：真实硬件接口调用（传感器、执行器、识别等）。
- 仿真主要替换"设备层输入"，尽量不改"业务层逻辑"，这样实机一致性最好。

### 8.2 优先使用 `@sim_only(on_sim=...)` 做最小替换

- 推荐写法：为"真实接口读取函数"提供同签名 mock，并用 `@sim_only(on_sim=mock_func)` 挂接。
- 实机环境自动走原函数，仿真环境自动走 mock，避免主流程里写大量 `if is_simulation()` 分支。
- 参考文件：
- `syspy/sim.py`：`is_simulation()` 与 `@sim_only` 定义。
- `tasks/v3/standard/example/sim_only_demo.py`：最小示例。
