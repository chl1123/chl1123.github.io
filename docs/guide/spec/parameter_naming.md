# 参数命名与层级规范

> 适用范围：脚本任务参数、脚本配置参数、设备与模型参数、Proto 消息与字段、NetProtocol API 请求与响应字段。
>
> 本规范中的 key 用于程序内部；name 和 desc 面向 Roboshop 等用户界面。

---

## 一、通用原则

### 1.1 参数可见性

1. 关闭 debug 开关时，禁止显示调试参数和低频参数。
2. 开启 debug 开关后，才允许显示调试参数和低频参数。
3. debug 开关本身属于配置参数，推荐使用：

| 属性 | 值 |
|------|----|
| key | isDebug |
| name | Is Debug |

### 1.2 参数不得重复

配置参数和任务参数的字段不得重复。

同一字段同时具备配置属性和任务属性时，只保留在配置参数中，不得在两个区域重复展示。

### 1.3 参数必须有明确归属

| 参数类型 | 定义 | 示例 |
|----------|------|------|
| 任务参数 | 每次任务可能不同，由任务指令决定 | operation、取货高度、放货高度 |
| 配置参数 | 与现场环境或机器人配置相关，实施完成后通常不再频繁修改 | 速度限制、传感器阈值、通信地址 |
| 调试/低频参数 | 只用于问题定位、测试或极少调整 | getLM、laserAreaDeduction |
| 模型派生参数 | 已存在于模型文件或设备模型中，脚本只读取，不让用户重复配置 | 背篓数量、设备模块 ID |

### 1.4 模型参数优先

已经能够从模型文件、设备模型或其他正式配置源读取的值，不得再次暴露为脚本参数。

示例：

1. 背篓数量应从设备模型中的对应模块配置读取，不应让用户在脚本参数中重复填写。
2. 手指 DO、DI 已能通过设备配置实现时，脚本中不应再次提供同义配置项。

### 1.5 key、name 和 desc

所有参数必须遵循：

1. key 遵循小驼峰规范。
2. name 遵循英文界面名称规范。
3. desc 使用完整、可理解的英文说明。
4. name 和 desc 需要支持国际化翻译。

---

## 二、小驼峰规范

### 2.1 基本格式

小驼峰（lower camel case）要求：

1. 首字母必须小写。
2. 后续每个单词的首字母大写。
3. 不得使用下划线、连字符或空格。
4. key 必须是连续的 ASCII 字母和数字组合。
5. key 应表达明确语义，不使用拼音或难以理解的临时缩写。

错误与正确示例：

| 错误写法 | 正确写法 | 问题 |
|----------|----------|------|
| UserName | userName | 首字母不应大写 |
| user_name | userName | 不应使用下划线 |
| User-Name | userName | 不应使用连字符 |
| user name | userName | 不应使用空格 |
| USERNAME | userName | 不应使用全大写单词 |

### 2.2 单词边界

多个英文单词组成 key 时：

1. 第一个单词全部按普通小写单词处理。
2. 第二个及后续单词首字母大写。
3. 不保留原始名称中的分隔符。

| 原始词组 | 正确 key |
|----------|----------|
| user name | userName |
| minimum angle | minimumAngle |
| maximum moving speed | maximumMovingSpeed |
| device model | deviceModel |
| install position | installPosition |

### 2.3 连续大写字母

全大写缩写词或专有名词，例如 USA、ID、HTML、XML，应视为一个语义单元。

转换规则：

1. 缩写位于 key 开头时，全部转为小写。
2. 缩写位于 key 中间或末尾时，转为首字母大写、其余字母小写。
3. 不在 key 中保留连续全大写形式。

| 错误写法 | 正确写法 |
|----------|----------|
| USA | usa |
| xxxUSA | xxxUsa |
| parseHTML | parseHtml |
| XMLParser | xmlParser |
| deviceID | deviceId |
| IDList | idList |

说明：本规则只约束内部 key。对外显示的 name 可以保留用户熟悉的缩写，例如 Device ID、HTML Parser、IMU Status。

### 2.4 数字前缀

当参数以“数字 + 字母组合”开头，例如 2d、3D、4K，并紧接一个大写单词时：

1. 将数字前缀移动到核心单词末尾。
2. 字母部分统一转为小写。
3. 最终结果仍遵循小驼峰。

| 错误写法 | 正确写法 |
|----------|----------|
| 2dLaser | laser2d |
| 3DCamera | camera3d |
| 4KVideo | video4k |

对应的对外 name 可以使用行业常见格式：

| key | name |
|-----|------|
| laser2d | 2D Laser |
| camera3d | 3D Camera |
| video4k | 4K Video |

### 2.5 小驼峰检查步骤

提交参数前依次检查：

1. key 是否以小写字母开头。
2. key 是否包含下划线、连字符或空格。
3. 是否存在连续大写缩写。
4. 数字前缀是否已经移动到核心单词末尾。
5. key 是否能让其他开发者直接理解。
6. 同一概念在不同模块中是否使用了相同 key。

---

## 三、key、name 与 desc 命名

### 3.1 key

key 是程序内部使用的稳定标识。

要求：

1. 必须遵循小驼峰。
2. 使用准确、完整的英文语义。
3. 同一个概念在不同模块中使用相同 key。
4. 不包含界面展示文字、单位或中文。
5. key 一旦对外发布，不得因界面文案调整而随意改变。

示例：

| 含义 | key |
|------|-----|
| 最小检测角度 | minAngle |
| 最大移动速度 | maxSpeed |
| 设备品牌 | deviceBrand |
| 设备型号 | deviceModel |
| 是否开启调试 | isDebug |

### 3.2 name

name 是用户主要看到的界面名称，也是多语言翻译的索引来源。

要求：

1. 使用可理解的英文短语。
2. 每个普通单词首字母大写，即 Title Case。
3. 不直接把 key 机械拆词后作为 name；需要表达真实业务含义。
4. 常见专有名词和缩写可以保持行业通用大写形式，例如 ID、IMU、GNSS、TCP、IP。
5. name 中不加入结尾句号。
6. 同级参数使用一致的语言风格。

示例：

| key | 不推荐 name | 推荐 name |
|-----|-------------|-----------|
| minAngle | Min Angle | Minimum Detection Angle |
| maxSpeed | Max Speed | Maximum Moving Speed |
| deviceBrand | Brand | Device Brand |
| deviceModel | Model | Device Model |
| laser2d | Laser 2d | 2D Laser |

“所有单词字母大写”在本规范中指每个普通单词首字母大写，不是将整段文字写成全大写。

### 3.3 desc

desc 是参数的详细英文说明，必须让不了解代码的用户也能理解参数用途。

desc 应按需要包含：

1. 用途：场景、作用对象、原因、目的和使用方法。
2. 依赖关系：依赖哪些设备、模型或其他参数。
3. 推荐配置：适用场景和建议值。
4. 风险提示：配置过大、过小或错误时的风险。
5. 关联参数：与当前参数共同生效的其他参数。

除“用途”外，其余部分在没有相关内容时可以省略。

desc 要求：

1. 使用完整英文句子。
2. 首字母大写并使用正确标点。
3. 不重复 name，而是解释 name 无法承载的信息。
4. 不使用只有代码作者才能理解的缩写。
5. 不写“设置此参数”之类没有业务信息的空泛描述。

### 3.4 maxSpeed 示例

| 属性 | 示例 |
|------|------|
| key | maxSpeed |
| name | Maximum Moving Speed |
| desc | Limits the maximum linear speed of the robot to prevent localization loss or collisions caused by overspeed. Increase this value only in simple environments where safety has been verified. An excessively high value may reduce motion stability and increase stopping distance. |

如果需要显式表达结构，可以在设计评审材料中拆分为：

1. 用途：限制机器人直线运动最大速度，避免超速导致定位丢失或碰撞。
2. 依赖关系：受底盘能力、定位质量和安全区域配置约束。
3. 推荐配置：仅在环境简单且完成安全验证后提高。
4. 风险提示：过高会降低运动稳定性并增加制动距离。
5. 关联参数：加速度、减速度、旋转速度等运动参数。

最终写入 desc 时应整理为自然、连贯的英文句子，而不是简单拼接标签。

---

## 四、任务参数与配置参数

### 4.1 任务参数

每次任务可能变化、由任务目标决定的字段放在任务参数中。

典型示例：

- operation
- startHeight
- endHeight
- recognize
- 取货高度
- 放货高度

### 4.2 配置参数

与现场环境、机器人设备或实施配置相关，现场实施完成后通常无需频繁修改的字段放在配置参数中。

典型示例：

- 最大速度
- 传感器检测阈值
- 通信地址
- 机构动作限制

### 4.3 调试参数和低频参数

配置参数区域应提供 debug 开关。

关闭 debug：

- 不显示调试参数。
- 不显示低频参数。
- 不显示仅供研发定位问题的内部参数。

开启 debug：

- 显示调试参数和低频参数。
- 参数仍须提供规范的 key、name 和 desc。

例如 getLM、laserAreaDeduction 等参数，未开启 debug 时禁止显示。

### 4.4 配置和任务参数冲突

如果一个字段已经作为配置参数存在，不得再作为任务参数重复出现。

处理顺序：

1. 确认字段是否随每次任务变化。
2. 确认字段是否由现场配置决定。
3. 两者冲突时保留在配置参数。
4. 调用方通过配置读取，不在任务请求中重复传递。

---

## 五、通用参数与非通用参数

### 5.1 通用 operation

相同业务含义应使用统一 operation，不在不同机构中创建同义名称。

推荐层级：

~~~text
operation
├── load
│   ├── startHeight
│   ├── endHeight
│   └── recognize
├── unload
│   ├── startHeight
│   ├── endHeight
│   └── recognize
├── zero
└── calib
~~~

统一示例：

| 原写法 | 统一值 |
|--------|--------|
| JackLoad | load |
| JackUnload | unload |
| isRecognize | recognize |

operation 的枚举值同样使用小驼峰；单个普通单词全部小写。

### 5.2 非通用参数

参数只适用于某一机构且无法抽象为通用含义时，使用：

~~~text
机构标识 + 参数功能标识
~~~

示例：

- jackUpReachDi
- jackDownReachDi

要求：

1. 机构标识放在开头。
2. 参数功能必须完整、可区分。
3. 整体仍遵循小驼峰。
4. 不为了缩短 key 而使用无法理解的字母组合。

---

## 六、参数顺序与层级

参数界面按以下顺序组织：

1. 安装位置：Install Position。
2. 品牌和型号：Device Brand、Device Model。
3. 通信参数：Communication Parameters。
4. 功能参数。
5. 其他参数，例如 External Encoder。

同一个参数组中：

1. 基础身份信息在前。
2. 必填参数在可选参数前。
3. 常用参数在调试、低频参数前。
4. debug 关闭时，调试和低频参数整体隐藏，不留空组。

---

## 七、品牌和型号字段

### 7.1 品牌

| 属性 | 值 |
|------|----|
| key | deviceBrand |
| name | Device Brand |

### 7.2 型号

| 属性 | 值 |
|------|----|
| key | deviceModel |
| name | Device Model |

禁止在不同设备中分别使用 brand、manufacturer、modelName 等同义字段代替标准字段。确有不同业务语义时，应在评审中说明。

---

## 八、安装位置

安装位置参数组的 name：

~~~text
Install Position
~~~

组内字段：

| key | name |
|-----|------|
| x | X |
| y | Y |
| z | Z |
| roll | Roll |
| pitch | Pitch |
| yaw | Yaw |

要求：

1. key 使用小写。
2. name 使用行业通用坐标名称。
3. 单位必须在参数类型或 desc 中明确。
4. Roll、Pitch、Yaw 的坐标系和旋转方向必须在 desc 中解释。

---

## 九、国际化

### 9.1 name 和 desc

所有面向用户显示的 name 和 desc 都应通过翻译接口处理。

示例：

~~~python
from syspy import _TR

with builder.CHILD(
    key="isDebug",
    name=_TR("Is Debug"),
    desc=_TR(
        "Controls whether debug and low-frequency parameters are visible."
    ),
):
    builder.TYPE(ParamType.BOOL)
    builder.DEFAULTVALUE(False)
~~~

### 9.2 错误描述

脚本设置的用户可见错误描述也应使用翻译接口。

~~~python
from syspy import Navigation, _TR

Navigation.setTaskError(
    "ModbusConnectFail",
    _TR(f"Modbus TCP connection failed: {error}"),
)
~~~

错误 key 不是参数 key，可遵循项目现有错误码约定；错误描述必须是完整、可理解的英文句子。

### 9.3 翻译字符串约束

1. _TR 中使用稳定英文原文。
2. 动态值使用格式化占位，保持出现顺序稳定。
3. 中文翻译使用相同编号的占位符。
4. 避免在一个 _TR 字符串中使用分号；现有提取流程可能按分号截断字符串。
5. name 使用英文短语，desc 和错误描述使用完整英文句子。

---

## 十、与日志规范的关系     

参数 key、name、desc 遵循本文档。

Trace.log 的通道名、日志字段和日志显示描述遵循：

~~~text
docs/guide/spec/logging.md
~~~

不要把参数界面 name 的 Title Case 规则直接用于日志字典 key。日志结构化字段仍应使用小驼峰。

---

## 十一、完整示例     

~~~python
from syspy import _TR

with builder.CHILD(
    key="deviceBrand",
    name=_TR("Device Brand"),
    desc=_TR(
        "Specifies the manufacturer of the connected device."
    ),
):
    builder.TYPE(ParamType.STRING)

with builder.CHILD(
    key="deviceModel",
    name=_TR("Device Model"),
    desc=_TR(
        "Specifies the model of the connected device. Select a model "
        "that is supported by the configured device brand."
    ),
):
    builder.TYPE(ParamType.STRING)

with builder.CHILD(
    key="maxSpeed",
    name=_TR("Maximum Moving Speed"),
    desc=_TR(
        "Limits the maximum linear speed of the robot to prevent "
        "localization loss or collisions caused by overspeed. "
        "Increase this value only after the operating environment "
        "has passed a safety assessment."
    ),
):
    builder.TYPE(ParamType.DOUBLE)

with builder.CHILD(
    key="isDebug",
    name=_TR("Is Debug"),
    desc=_TR(
        "Controls whether debug and low-frequency parameters are visible."
    ),
):
    builder.TYPE(ParamType.BOOL)
    builder.DEFAULTVALUE(False)
~~~

---

## 十一、评审清单     

### 11.1 key

- [ ] 首字母为小写。
- [ ] 使用小驼峰。
- [ ] 不含下划线、连字符和空格。
- [ ] 缩写词已按位置正确转换。
- [ ] 数字前缀已移动到核心单词末尾。
- [ ] 语义明确，不使用拼音或临时缩写。
- [ ] 同义参数没有重复 key。

### 11.2 name

- [ ] 使用可理解的英文短语。
- [ ] 普通单词使用 Title Case。
- [ ] 常见专有缩写保持行业写法。
- [ ] name 表达业务语义，不是 key 的机械拆分。
- [ ] 已使用 _TR。

### 11.3 desc

- [ ] 使用完整英文句子。
- [ ] 说明使用场景、作用对象、原因和目的。
- [ ] 必要时说明依赖、推荐配置、风险和关联参数。
- [ ] 没有仅重复 name。
- [ ] 没有难以理解的缩写。
- [ ] 已使用 _TR。
- [ ] 避免使用会影响翻译提取的分号。

### 11.4 分类和层级

- [ ] 任务参数和配置参数没有重复。
- [ ] 模型可派生参数没有重复暴露给用户。
- [ ] debug 关闭时调试和低频参数不可见。
- [ ] 参数顺序符合安装位置、品牌型号、通信、功能、其他参数的顺序。
- [ ] 品牌和型号使用 deviceBrand、deviceModel。
- [ ] 安装位置使用 X、Y、Z、Roll、Pitch、Yaw。

### 11.5 协议

- [ ] Proto 文件名保持 message_xxx.proto。
- [ ] Proto message、字段和枚举遵循小驼峰。
- [ ] NetProtocol 请求和响应字段遵循小驼峰。
- [ ] 嵌套 message 和 repeated 字段符合相同规则。

---

## 十一、错误与正确示例汇总

| 场景 | 错误 | 正确 |
|------|------|------|
| 普通 key | UserName | userName |
| 下划线 | user_name | userName |
| 连字符 | User-Name | userName |
| 开头缩写 | XMLParser | xmlParser |
| 末尾缩写 | parseHTML | parseHtml |
| ID 缩写 | deviceID | deviceId |
| 数字前缀 | 2dLaser | laser2d |
| 数字前缀 | 3DCamera | camera3d |
| 品牌 key | brand | deviceBrand |
| 型号 key | modelName | deviceModel |
| name 过度简写 | Min Angle | Minimum Detection Angle |
| Proto message | Message_Bin | msgBin |
| Proto 字段 | dis_connect | disConnect |
| API 字段 | map_name | mapName |
| 安装位置拼写 | Picth | Pitch |

