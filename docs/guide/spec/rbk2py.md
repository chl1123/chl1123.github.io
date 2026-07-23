# RBK 插件 RPC 接口接入规范

> 适用范围：将 RBK（C++）插件方法开放给 Python 脚本调用，并在 `syspy` SDK 中新增对应接口。
> 以 `DSPChassis::publishBattery`（发布电池数据）为例，贯穿全文。

本规范在「把 RBK 插件方法暴露给 Python」原始流程基础上，补全 **SDK 抽象层接口** 的写法——
原始说明只覆盖了 `syspy/v3` 实现层，缺少 `syspy/<mod>.py` 抽象层这一步。

---

## 一、整体流程

新增一个可供脚本调用的 RBK 能力，需要三步、跨两端：

| 步骤 | 端 | 文件 | 职责 |
|------|----|------|------|
| 1. 插件注册 | RBK（C++） | 插件源码（如 `DSPChassis.cpp`） | `RpcServer::bind` 把成员方法注册为 RPC 方法 |
| 2. 抽象层接口 | SDK（Python） | `syspy/<mod>.py` | 版本无关的对外接口 `XxxInterface`，承载文档与默认行为 |
| 3. 实现层接口 | SDK（Python） | `syspy/v3/<mod>.py`、`syspy/v4/<mod>.py` | 各 RBK 版本的实际 RPC 调用 `XxxV3` / `XxxV4` |

接口归属按语义划分到对应模块：`publishBattery` 是发布电池数据，属于电池模块，因此落到
`syspy/battery.py`（抽象层）+ `syspy/v3/battery.py`、`syspy/v4/battery.py`（实现层）。

---

## 二、RBK 插件注册（C++ 侧）

以 `DSPChassis::publishBattery` 为例，要将其开放给 Python 调用：

头文件 `DSPChassis.h` 中声明接口，并使用 Doxygen 文档注释说明接口用途、参数和返回值：

```cpp
/**
 * @brief 发布由 protobuf 消息转换得到的 JSON 格式电池信息
 *
 * @param msg msgBattery 消息对应的 JSON 字符串
 * @return 0 发布成功
 * @return -1 JSON 解析失败或发布失败
 */
int publishBattery(std::string msg);
```

源文件 `DSPChassis.cpp` 中实现接口：

```cpp
int DSPChassis::publishBattery(std::string msg){
    google::protobuf::util::JsonParseOptions parseOption;
    parseOption.ignore_unknown_fields = true;
    rbk::protocol::Message_Battery battery;
    google::protobuf::util::Status status = google::protobuf::util::JsonStringToMessage(msg, &battery, parseOption);
    if (google::protobuf::util::Status::OK == status){
        handleBatteryInfo(battery);
        return 0;
    }
    return -1;
}
```

### 2.1 注册 RPC 方法

```cpp
#include <robokit/utils/rpc/rpcServer.h>

void DSPChassis::setSubscriberCallBack() {
    rbk::utils::RpcServer::Instance().bind("publishBattery", &DSPChassis::publishBattery, this);
}
```

`bind` 第一个参数 `"publishBattery"` 是 RPC 方法名（SDK 实现层将以此名调用），后两个参数是成员函数指针与 `this`。

### 2.2 CMake 链接 utils_rpc

```cmake
target_link_libraries(${PROJECT_NAME}
    utils_rpc
)
```

---

## 三、脚本 SDK 两层接口架构

`syspy` 对每个模块采用 **抽象层 + 实现层** 两层结构：

| 层 | 文件 | 类 | 基类 | 装饰器 | 方法体 |
|----|------|----|------|--------|--------|
| 抽象层 | `syspy/<mod>.py` | `XxxInterface` | `ABC, Service` | 无 | 完整 docstring + `raise RBKVersionError()` |
| 实现层 | `syspy/v3/<mod>.py` | `XxxV3(XxxInterface)` | `XxxInterface` | `@default_plugin` / `@call_service` | 不写 docstring；方法体为 `pass` 或版本实现 |
| 实现层 | `syspy/v4/<mod>.py` | `XxxV4(XxxInterface)` | `XxxInterface` | 同上 | 同上 |

为什么分两层：

- **版本无关的对外契约**：脚本侧只 `from syspy import Battery`，不感知 RBK 版本；抽象层定义统一签名与文档。
- **文档单一来源**：mkdocstrings 配置 `inherited_members: true`（见 `mkdocs.yml`），实现层继承抽象层的 docstring，因此**文档只在抽象层维护一次**。
- **版本差异隔离**：v3 / v4 的 RPC 细节、proto 类型差异都封装在实现层，互不污染。

抽象层文件末尾负责按 `RBK_VERSION` 选择实现类并导出单例：

```python
from syspy import RBK_VERSION
if RBK_VERSION == 3:
    from syspy.v3.charger import ChargerV3
    Charger: ChargerInterface = ChargerV3()
elif RBK_VERSION == 4:
    from syspy.v4.charger import ChargerV4
    Charger: ChargerInterface = ChargerV4()
else:
    raise ValueError(f"Unsupported RBK version: {RBK_VERSION}")
```

---

## 四、抽象层接口（`syspy/<mod>.py`）

> 这是原始流程缺失、本规范重点补全的部分。

### 4.1 标准模式：继承式（推荐）

绝大多数模块（`charger` / `dio` / `led` / `bin` / `loc` …）采用此模式：抽象类继承 `ABC, Service`，
每个方法是 `@classmethod`，写**完整 Google 风格 docstring**，方法体 `raise RBKVersionError()`（表示该版本未实现时显式报错）。

以 `syspy/charger.py` 为真实示例：

```python
from abc import ABC
from syspy.core.rbk_rpc import Service, RBKVersionError


class ChargerInterface(ABC, Service):
    """充电桩类"""

    @classmethod
    def disconnectCharger(cls, name: str) -> bool:
        """与充电桩断开通信连接

        Args:
            name (str): 充电桩名称

        Returns:
            (bool): True 断连成功；False 断连失败
        """
        raise RBKVersionError()
```

要点：

- 类名 `XxxInterface`，继承 `ABC, Service`（`Service` 提供 `client()` / `server()`）。
- 方法用 `@classmethod`，签名（参数名、类型注解、返回注解）即对外契约。
- **docstring 只在抽象层写**，实现层继承；文档由此单点维护。
- 方法体 `raise RBKVersionError()`：当某 RBK 版本未覆写该方法时，调用会显式抛出版本不兼容异常，而非静默返回 `None`。
- 仅在部分版本可用的接口，docstring 追加 `Compatibility:` 段说明（见 `syspy/battery.py` 的 `getSoh` / `getIsManuallyConnected`）。

### 4.2 委托门面变体（`battery` / `laser`）

当抽象层需要做**额外处理**（如对入参做转换、聚合多个 child 调用）时，采用委托门面：
抽象类不继承 `Service`，`__init__` 内按版本实例化 `self.child`，每个方法委托给 `self.child`。

以 `syspy/battery.py` 为真实示例：

```python
class BatteryInterface:
    """电池模块接口定义"""

    def __init__(self):
        if RBK_VERSION == 3:
            from syspy.v3.battery import BatteryV3
            self.child = BatteryV3()
        elif RBK_VERSION == 4:
            from syspy.v4.battery import BatteryV4
            self.child = BatteryV4()
        else:
            raise ValueError(f"Unsupported RBK version: {RBK_VERSION}")

    def publish(self, battery_info: "msgBattery", *, topic: str = "Battery-000") -> int:
        """发布电池信息

        Args:
            battery_info ("msgBattery"): proto 消息

        Returns:
            (int): -1: 发布失败; 0: 发布成功
        """
        return self.child.publish(battery_info, topic=topic)


Battery: BatteryInterface = BatteryInterface()
```

两种模式取舍：

- **继承式（4.1）**：默认选择。结构最简，docstring 单点维护，新模块一律用它。
- **委托门面（4.2）**：仅当抽象层确有额外逻辑时使用；此时 docstring 只在抽象层维护，实现层不重复编写。

### 4.3 抽象层约定

- 对外可枚举的可选参数（如 `topic`）建议设为**关键字参数**（`*, topic="Battery-000"`），与实现层保持一致。
- 抽象层方法签名必须与实现层一致（参数名、顺序、默认值），否则委托/继承会错位。
- 新增模块时，在 `syspy/__init__.py` 中按需导出单例，使脚本可 `from syspy import Xxx`。

---

## 五、实现层接口（`syspy/v3/<mod>.py`、`syspy/v4/<mod>.py`）

实现层是各 RBK 版本对插件方法的实际 RPC 调用。接口 docstring 统一写在抽象层，实现层不重复编写注释。

### 5.1 装饰器直通（常见情形）

入参可直接透传给 RPC 方法时，用 `@call_service` 自动转发，方法体 `pass`。
以 `syspy/v3/charger.py` 为真实示例：

```python
from syspy.core.rbk_rpc import call_service, default_plugin
from syspy.charger import ChargerInterface


@default_plugin("ChargerAdapter")
class ChargerV3(ChargerInterface):
    @classmethod
    @call_service()
    def disconnectCharger(cls, name: str) -> bool:
        pass
```

- `@default_plugin("ChargerAdapter")`：本类方法默认调用该 RBK 插件。
- `@call_service()`：把 Python 方法调用转发到 RBK 插件方法；`plugin_name` 缺省取 `@default_plugin`，`func_name` 缺省与 Python 方法同名。
- 方法体 `pass`：实际逻辑由 `@call_service` 注入；docstring 继承自抽象层。

### 5.2 需要转换时手写方法体

当入参需要转换（如 proto 对象转 JSON 字符串）后才能交给 RPC，**不要用 `@call_service`**，
而是手写方法体调用 `self.client().call_service(plugin, method, ...)`。

`publishBattery` 正属此类：C++ 侧 `publishBattery(std::string msg)` 收的是 JSON 字符串，
而 SDK 对外暴露的是 proto 对象，需先 `MessageToJson`。以 `syspy/v3/battery.py` 真实代码：

```python
from google.protobuf.json_format import MessageToJson
from syspy.core.rbk_rpc import default_plugin, Message


@default_plugin("DSPChassis")
class BatteryV3(Message):
    def publish(self, battery_msg: "msgBattery", *, topic: str = "Battery-000") -> int:
        return self.client().call_service("DSPChassis", "publishBattery", MessageToJson(battery_msg))
```

v4 实现位于 `syspy/v4/battery.py`，走 datapool 发布，体现版本差异被隔离在实现层：

```python
def publish(self, battery_msg: "MessageV4_Battery", *, topic: str = "Battery-000"):
    if not self.is_publish:
        datapool.publish("/BatteryInfo/" + topic, MessageV4_Battery)
        self.is_publish = True
    datapool.put("/BatteryInfo/" + topic, battery_msg)
```

---

## 六、装饰器参考

| 装饰器 | 作用 | 参数 |
|--------|------|------|
| `@default_plugin(name)` | 声明本类方法默认调用的 RBK 插件 | `name`：RBK 插件名 |
| `@call_service(plugin_name=None, func_name=None)` | 将方法调用转发到指定 RBK 插件方法 | `plugin_name`：缺省取 `@default_plugin`；`func_name`：缺省与 Python 方法同名 |

- `@call_service` 自动按 RBK 版本组织参数（v3 转位置参数、v4 转关键字参数），见 `syspy/core/rbk_rpc.py`。
- 当 Python 方法名与 RBK 方法名不同，用 `@call_service(func_name="rbkMethodName")` 指定。

---

## 七、注释规范（Google 风格）

Python 接口 docstring 只在抽象层编写，须符合 Google 规范，便于自动生成接口文档与查看。
实现层保持相同的方法签名，但不重复编写 docstring。**`Args:` 与 `Returns:` 前都要有空行。**

抽象层通用模板：

```python
@classmethod
def setXXX(cls, param1: str, param2: float) -> bool:
    """接口名XXX

    Args:
        param1 (str): 参数1解释XXX
        param2 (float): 参数2解释XXX

    Returns:
        (bool): 返回值解释XXX
    """
    raise RBKVersionError()
```

四种签名形态：

1) 无入参、无返回值：

```python
@classmethod
def resetPath(cls):
    """让agv沿着规划的线路行驶"""
    raise RBKVersionError()
```

2) 有入参、无返回值：

```python
@classmethod
def setIncreaseSpinAngle(cls, angle: float):
    """设置增量旋转角度

    Args:
        angle (float):
    """
    raise RBKVersionError()
```

3) 无入参、有返回值：

```python
@classmethod
def hasGoods(cls) -> bool:
    """获取身上是否有货物的状态

    Returns:
        (bool): 是否有货物
    """
    raise RBKVersionError()
```

4) 有入参、有返回值：

```python
@classmethod
def setMotorPosition(cls, motor_name: str, pos: float, maxVel: float, stopDI: int) -> bool:
    """控制线性电机到特定位置

    Args:
        motor_name (str): 模型文件中的电机名称
        pos (float): 发送目标点位置也可能是角度
        maxVel (float): 运行过程中的最大速度不能超过模型文件中的最大速度
        stopDI (int): 如果这个StopDI触发则表示运动到位

    Returns:
        (bool): 如果不存在这个电机，则返回False
    """
    raise RBKVersionError()
```

对应的实现层只保留装饰器、相同签名和实现逻辑，不写 docstring：

```python
@classmethod
@call_service()
def setXXX(cls, param1: str, param2: float) -> bool:
    pass
```

---

## 八、完整示例：publishBattery 端到端

把 `DSPChassis::publishBattery` 接入脚本 SDK，最终落在三处（均为仓库真实代码）：

1. **抽象层** `syspy/battery.py` —— `BatteryInterface.publish`（对外契约 + docstring，委托给 child）：

```python
def publish(self, battery_info: "msgBattery", *, topic: str = "Battery-000") -> int:
    """发布电池信息

    Args:
        battery_info ("msgBattery"): proto 消息

    Returns:
        (int): -1: 发布失败; 0: 发布成功
    """
    return self.child.publish(battery_info, topic=topic)
```

2. **实现层 v3** `syspy/v3/battery.py` —— `BatteryV3.publish`（proto→JSON 后调用 RBK `publishBattery`）：

```python
@default_plugin("DSPChassis")
class BatteryV3(Message):
    def publish(self, battery_msg: "msgBattery", *, topic: str = "Battery-000") -> int:
        return self.client().call_service("DSPChassis", "publishBattery", MessageToJson(battery_msg))
```

3. **实现层 v4** `syspy/v4/battery.py` —— `BatteryV4.publish`（走 datapool）。

脚本侧调用方式（版本无关）：

```python
from syspy import Battery
# battery_msg 为 msgBattery proto 对象
ret = Battery.publish(battery_msg)   # 0 成功 / -1 失败
```

---

## 九、新增接口检查清单

- [ ] RBK（C++）侧：插件方法已通过 `RpcServer::bind("<method>", &Cls::method, this)` 注册，CMake 链接 `utils_rpc`
- [ ] 接口按语义归属到正确模块（如发布电池数据 → `battery`）
- [ ] 抽象层 `syspy/<mod>.py`：新增方法，签名 + 完整 Google docstring，方法体 `raise RBKVersionError()`（继承式）或委托 `self.child`（门面式）
- [ ] 实现层 `syspy/v3/<mod>.py`、`syspy/v4/<mod>.py`：各版本实现；入参可直通用 `@call_service()`，需转换则手写 `self.client().call_service(...)`
- [ ] `@default_plugin` 指向正确的 RBK 插件名；`func_name` 在方法名与 RBK 方法名不一致时显式指定
- [ ] 抽象层与实现层方法签名一致（参数名 / 顺序 / 默认值 / 关键字参数）
- [ ] 仅部分版本可用的接口，docstring 写明 `Compatibility:`
- [ ] 注释符合 Google 规范：`Args:` / `Returns:` 前有空行
- [ ] 抽象层文件末尾按 `RBK_VERSION` 实例化并导出单例；必要时在 `syspy/__init__.py` 导出
