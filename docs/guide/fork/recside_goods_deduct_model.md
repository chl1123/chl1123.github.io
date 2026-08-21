# LiftFork 识别面转换与货物模型加载逻辑

## 1. 范围

1. 获取任务传入的识别面；
2. 根据识别面转换载具轮廓、货物轮廓和障碍物扣除区；
3. 取货抬升完成后，将模型转换到机器人坐标系并加载；
4. 全文的形状仅支持矩形。

## 2. 核心数据结构

### 2.1 识别参数
```pseudo
requestedRecSide = taskArgs.get("recSide")
effectiveRecSide = requestedRecSide or "D"
```

`recSide` 任务传参，货物模型和扣除区只使用 `effectiveRecSide` 做 A/B/C/D 矩阵转换；识别取货任务参数和识别文件配置的识别面做检验

### 2.2 载具轮廓

载具轮廓是以载具中心为原点的矩形:

```pseudo
carrierShape = [
    {"x": +carrierLength / 2, "y": +carrierWidth / 2},
    {"x": -carrierLength / 2, "y": +carrierWidth / 2},
    {"x": -carrierLength / 2, "y": -carrierWidth / 2},
    {"x": +carrierLength / 2, "y": -carrierWidth / 2}
]
```

`carrierLength` 对齐车体 X 轴，`carrierWidth` 对齐车体 Y 轴，使载具轮廓与识别文件中的 `goodsShape`、`deductShape` 使用相同的轴向约定。

### 2.3 货物轮廓

```pseudo
// 识别文件中 goodsShape 的原始结构
goodsShape = [
    {"x": x1, "y": y1},
    {"x": x2, "y": y2},
    ...
]
```

### 2.4 障碍物扣除区

```pseudo
// 识别文件中 deductShape 的原始结构
deductShape = [
    {
        "points": [
            {"x": 0.4, "y": 0.6},
            {"x": -0.4, "y": 0.6},
            {"x": -0.4, "y": -0.6},
            {"x": 0.4, "y": -0.6}
        ],
        "shape": "rectangle"
    }
]

// 脚本将 deductShape 转成以下结构后，再执行识别面转换和加载
palletDeductInfos = [
    {
        "deduct_device": ["Laser-001", "Laser-002"],
        "areas": [
            {
                "x": [0.4, -0.4, -0.4, 0.4],
                "y": [0.6, 0.6, -0.6, -0.6]
            }
        ]
    }
]
```

`deduct_device` 表示扣除区作用的设备列表；`areas` 表示对应的一个或多个多边形区域。

## 3. 总体流程

```pseudo
function preparePalletModel(requestedRecSide):
    effectiveRecSide = requestedRecSide or "D"

    carrierShape = transformShapeByRecSide(
        carrierShape,
        effectiveRecSide
    )

    goodsShape = transformShapeByRecSide(
        goodsShape,
        effectiveRecSide
    )

    palletDeductInfos = transformDeductInfosByRecSide(
        palletDeductInfos,
        effectiveRecSide
    )

    return {
        "rec_side": effectiveRecSide,
        "carrier_shape": carrierShape,
        "goods_shape": goodsShape,
        "pallet_deduct_infos": palletDeductInfos
    }
```

## 4. 识别面参数获取

```pseudo
function getEffectiveRecSide(taskArgs):
    recSide = taskArgs.get("recSide")

    if recSide is empty:
        return "D"

    if uppercase(recSide) not in ["A", "B", "C", "D"]:
        reportTaskError("RecSideError", "不支持的识别面")
        return null

    return uppercase(recSide)
```

选择规则：

1. 任务显式指定 `recSide` 时，直接使用传入的 A/B/C/D；
2. 未指定 `recSide` 时使用 `D`；
3. 识别取货和非识别取货使用相同的参数规则；
4. 不从识别文件获取或校验 `recSide`。

## 5. 识别面坐标转换

### 5.1 单点转换

```pseudo
function transformPointByRecSide(point, recSide):
    x = point["x"]
    y = point["y"]

    switch lowercase(recSide):
        case "a":
            // 顺时针旋转 90°
            return {"x": y, "y": -x}

        case "b":
            // 旋转 180°
            return {"x": -x, "y": -y}

        case "c":
            // 逆时针旋转 90°
            return {"x": -y, "y": x}

        case "d":
            // D 面是基准面
            return {"x": x, "y": y}

        default:
            reportTaskError("RecSideError", "不支持的识别面")
            return null
```



模型加载以 `D` 面对应的 `+X` 为基准，因此需要把所选识别面的外法向旋转到 `+X`：

| 识别面 | 原外法向 | 转到 `+X` 所需旋转 | 转换矩阵 |
| --- | --- | --- | --- |
| `A` | `+Y` | 顺时针 90° | `[[0, 1], [-1, 0]]` |
| `B` | `-X` | 180° | `[[-1, 0], [0, -1]]` |
| `C` | `-Y` | 逆时针 90° | `[[0, -1], [1, 0]]` |
| `D` | `+X` | 不旋转 | `[[1, 0], [0, 1]]` |

因此上述矩阵与“`D` 面为默认基准面”的约定一致。

### 5.2 普通轮廓转换

```pseudo
function transformShapeByRecSide(points, recSide):
    transformedPoints = []

    for point in points:
        transformedPoints.append(
            transformPointByRecSide(point, recSide)
        )

    return transformedPoints
```

该函数同时用于 `carrierShape` 和 `goodsShape`。

### 5.3 扣除区转换


```pseudo
function transformDeductInfosByRecSide(
    palletDeductInfos,
    recSide
):
    transformedInfos = []

    for info in palletDeductInfos:
        transformedAreas = []

        for area in info["areas"]:
            transformedAreaX = []
            transformedAreaY = []

            for i from 0 to length(area["x"]) - 1:
                transformedPoint = transformPointByRecSide(
                    {
                        "x": area["x"][i],
                        "y": area["y"][i]
                    },
                    recSide
                )

                transformedAreaX.append(
                    transformedPoint["x"]
                )
                transformedAreaY.append(
                    transformedPoint["y"]
                )

            transformedAreas.append({
                "x": transformedAreaX,
                "y": transformedAreaY
            })

        transformedInfos.append({
            // 设备列表保持不变，只转换区域坐标。
            "deduct_device": info["deduct_device"],
            "areas": transformedAreas
        })

    return transformedInfos
```

## 6. 取货后的模型加载

模型加载发生在 `upFork` 完成后，最终货物模型使用转换后的 `carrierShape`。

```pseudo
palletPoseInRobot = [moduleX - carrierLength / 2, 0, 0]

goodsPointsInRobot = transformPoints(carrierShape, palletPoseInRobot)
set_deduct_area(palletDeductInfos, palletPoseInRobot, ROBOT)
Navigation.setGoodsPolyShape(goodsPointsInRobot, recfile)
```

`carrierShape` 和 `palletDeductInfos` 先按识别面旋转，再通过 `palletPoseInRobot` 转到机器人坐标系。载具矩形必须按 `x=±carrierLength/2`、`y=±carrierWidth/2` 构造，并与 `goodsShape`、`deductShape` 使用相同轴向。

## 7. A/B/C/D 面计算示例

### 7.1 公共输入

```pseudo
carrierWidth = 1.2
carrierLength = 0.8
moduleX = 1.2

carrierShape = [
    {"x": 0.4, "y": 0.6},
    {"x": -0.4, "y": 0.6},
    {"x": -0.4, "y": -0.6},
    {"x": 0.4, "y": -0.6}
]

goodsShape = [
    {"x": 0.4, "y": 0.6},
    {"x": -0.4, "y": 0.6},
    {"x": -0.4, "y": -0.6},
    {"x": 0.4, "y": -0.6}
]

palletDeductInfos = [
    {
        "deduct_device": ["Laser-001", "Laser-002"],
        "areas": [
            {
                "x": [0.4, -0.4, -0.4, 0.4],
                "y": [0.6, 0.6, -0.6, -0.6]
            }
        ]
    }
]
```

加载基准位姿为：

```pseudo
palletPoseInRobot 
= [1.2 - 0.8 / 2, 0, 0]
= [0.8, 0, 0]
```

### 7.2 传入 A 面

识别面转换结果：

```pseudo
carrierShape = [
    {"x": 0.6, "y": -0.4},
    {"x": 0.6, "y": 0.4},
    {"x": -0.6, "y": 0.4},
    {"x": -0.6, "y": -0.4}
]

goodsShape = [
    {"x": 0.6, "y": -0.4},
    {"x": 0.6, "y": 0.4},
    {"x": -0.6, "y": 0.4},
    {"x": -0.6, "y": -0.4}
]

palletDeductInfos = [
    {
        "deduct_device": ["Laser-001", "Laser-002"],
        "areas": [
            {
                "x": [0.6, 0.6, -0.6, -0.6],
                "y": [-0.4, 0.4, 0.4, -0.4]
            }
        ]
    }
]
```

加载到机器人坐标系后的最终结果：

```pseudo
goodsPointsInRobot = [
    {"x": 1.4, "y": -0.4},
    {"x": 1.4, "y": 0.4},
    {"x": 0.2, "y": 0.4},
    {"x": 0.2, "y": -0.4}
]

deductAreaInRobot = {
    "x": [1.4, 1.4, 0.2, 0.2],
    "y": [-0.4, 0.4, 0.4, -0.4]
}
```

### 7.3 传入 B 面

识别面转换结果：

```pseudo
carrierShape = [
    {"x": -0.4, "y": -0.6},
    {"x": 0.4, "y": -0.6},
    {"x": 0.4, "y": 0.6},
    {"x": -0.4, "y": 0.6}
]

goodsShape = [
    {"x": -0.4, "y": -0.6},
    {"x": 0.4, "y": -0.6},
    {"x": 0.4, "y": 0.6},
    {"x": -0.4, "y": 0.6}
]

palletDeductInfos = [
    {
        "deduct_device": ["Laser-001", "Laser-002"],
        "areas": [
            {
                "x": [-0.4, 0.4, 0.4, -0.4],
                "y": [-0.6, -0.6, 0.6, 0.6]
            }
        ]
    }
]
```

加载到机器人坐标系后的最终结果：

```pseudo
goodsPointsInRobot = [
    {"x": 0.4, "y": -0.6},
    {"x": 1.2, "y": -0.6},
    {"x": 1.2, "y": 0.6},
    {"x": 0.4, "y": 0.6}
]

deductAreaInRobot = {
    "x": [0.4, 1.2, 1.2, 0.4],
    "y": [-0.6, -0.6, 0.6, 0.6]
}
```

### 7.4 传入 C 面

识别面转换结果：

```pseudo
carrierShape = [
    {"x": -0.6, "y": 0.4},
    {"x": -0.6, "y": -0.4},
    {"x": 0.6, "y": -0.4},
    {"x": 0.6, "y": 0.4}
]

goodsShape = [
    {"x": -0.6, "y": 0.4},
    {"x": -0.6, "y": -0.4},
    {"x": 0.6, "y": -0.4},
    {"x": 0.6, "y": 0.4}
]

palletDeductInfos = [
    {
        "deduct_device": ["Laser-001", "Laser-002"],
        "areas": [
            {
                "x": [-0.6, -0.6, 0.6, 0.6],
                "y": [0.4, -0.4, -0.4, 0.4]
            }
        ]
    }
]
```

加载到机器人坐标系后的最终结果：

```pseudo
goodsPointsInRobot = [
    {"x": 0.2, "y": 0.4},
    {"x": 0.2, "y": -0.4},
    {"x": 1.4, "y": -0.4},
    {"x": 1.4, "y": 0.4}
]

deductAreaInRobot = {
    "x": [0.2, 0.2, 1.4, 1.4],
    "y": [0.4, -0.4, -0.4, 0.4]
}
```

### 7.5 传入 D 面或未传识别面

`D` 是基准面，不执行旋转。未传 `recSide` 时也按 `D` 处理。

识别面转换结果：

```pseudo
carrierShape = [
    {"x": 0.4, "y": 0.6},
    {"x": -0.4, "y": 0.6},
    {"x": -0.4, "y": -0.6},
    {"x": 0.4, "y": -0.6}
]

goodsShape = [
    {"x": 0.4, "y": 0.6},
    {"x": -0.4, "y": 0.6},
    {"x": -0.4, "y": -0.6},
    {"x": 0.4, "y": -0.6}
]

palletDeductInfos = [
    {
        "deduct_device": ["Laser-001", "Laser-002"],
        "areas": [
            {
                "x": [0.4, -0.4, -0.4, 0.4],
                "y": [0.6, 0.6, -0.6, -0.6]
            }
        ]
    }
]
```

加载到机器人坐标系后的最终结果：

```pseudo
goodsPointsInRobot = [
    {"x": 1.2, "y": 0.6},
    {"x": 0.4, "y": 0.6},
    {"x": 0.4, "y": -0.6},
    {"x": 1.2, "y": -0.6}
]

deductAreaInRobot = {
    "x": [1.2, 0.4, 0.4, 1.2],
    "y": [0.6, 0.6, -0.6, -0.6]
}
```

## 8. 识别取货按实际栈板宽度和位姿加载模型

### 8.1 适用范围

- 仅用于识别取货；非识别取货仍使用第 6 节的固定加载基准；
- `carrierShape`、`goodsShape` 和 `palletDeductInfos` 使用同一个识别面矩阵；
- `palletWidth` 来自选中的 `Recognize.getRecResults()` 结果。

```pseudo
type Point2D = {"x": Number, "y": Number}
type Shape = List[Point2D]

type PalletShapes = {
    "carrierShape": Shape,
    "goodsShape": Shape,
    "deductShapes": List[Shape]
}
```

### 8.3 将局部原点移到前表面中心

识别面转换后，栈板在 X 方向的长度直接由转换后的 `carrierShape` 计算：

```pseudo
palletLengthInX = max(point["x"]) - min(point["x"])
centerPoseInFrontSurface = [-palletLengthInX / 2, 0, 0]
```

### 8.4 使用识别位姿计算加载基准

识别取货使用选中识别结果的前表面中心世界位姿

```pseudo
palletFrontSurfacePoseInWorld = selectedRecResult["worldResult"]
palletWidth = selectedRecResult["palletWidth"]
```

`enableTcp` 开启时，先用 `calTCPTrans()` 修正该位姿。

`upFork` 完成后再获取机器人定位；

```pseudo
robotPoseInWorldAfterPath = get_r_loc()
// T_robot_front = inverse(T_world_robot) * T_world_front
palletFrontSurfacePoseInRobot = pos2Base(
    palletFrontSurfacePoseInWorld,
    robotPoseInWorldAfterPath
)
```

`pos2Base()` 计算的是前表面在机器人坐标系中的位姿 `T_robot_front`，不是它的逆变换。最后以该位姿为基准，把前表面局部坐标转换到机器人坐标系。

### 8.5 加载货物模型和扣除区

```pseudo
function loadRecognizedPalletModel(
    recfile,
    requestedRecSide,
    selectedRecResult,
    carrierShape,
    goodsShape,
    palletDeductInfos
):
    effectiveRecSide = requestedRecSide or "D"
    palletWidth = selectedRecResult["palletWidth"]
    palletFrontSurfacePoseInWorld = selectedRecResult["worldResult"]

    // worldResult 后续作为唯一的前表面世界位姿来源。
    if enableTcp:
        palletFrontSurfacePoseInWorld = calTCPTrans(
            palletFrontSurfacePoseInWorld
        )

    // 先按任务 recSide 旋转；宽度修正必须在旋转之后。
    carrierShape = transformShapeByRecSide(
        carrierShape,
        effectiveRecSide
    )
    goodsShape = transformShapeByRecSide(
        goodsShape,
        effectiveRecSide
    )

    palletDeductInfos = transformDeductInfosByRecSide(
        palletDeductInfos,
        effectiveRecSide
    )

    // 使用识别宽度统一三类轮廓的 Y 边界，X 坐标不变。
    carrierShape = resizeYByPalletWidth(
        carrierShape,
        palletWidth
    )
    goodsShape = resizeYByPalletWidth(
        goodsShape,
        palletWidth
    )
    palletDeductInfos = resizeDeductYByPalletWidth(
        palletDeductInfos,
        palletWidth
    )

    // 从转换后的点集计算 X 向长度，兼容全部识别面。
    palletLengthInX = max(p["x"] for p in carrierShape)
                     - min(p["x"] for p in carrierShape)

    // 三类轮廓一起从矩形中心坐标系移到前表面中心坐标系。
    carrierShape, goodsShape, palletDeductInfos =
        moveOriginFromCenterToFrontSurface(
            carrierShape,
            goodsShape,
            palletDeductInfos,
            palletLengthInX
        )

    // 此函数在 upFork 完成后调用；变轴距车型必须使用此时的定位。
    robotPoseInWorldAfterPath = get_r_loc()

    // 计算前表面在机器人坐标系中的位姿 T_robot_front。
    palletFrontSurfacePoseInRobot = pos2Base(
        palletFrontSurfacePoseInWorld,
        robotPoseInWorldAfterPath
    )

    // 统一转换到机器人坐标系；设备列表保持不变。
    goodsPointsInRobot = transformPoints(
        carrierShape,
        palletFrontSurfacePoseInRobot
    )
    deductInfosInRobot = transformDeductInfos(
        palletDeductInfos,
        palletFrontSurfacePoseInRobot
    )

    // 此处坐标已经是 ROBOT，直接加载，禁止再次套用 basePose。
    for infoIndex, info in enumerate(deductInfosInRobot):
        for areaIndex, area in enumerate(info["areas"]):
            Navigation.setClearRegion(
                name = "PalletRobotDeductArea"
                       + (infoIndex + 1)
                       + "_"
                       + (areaIndex + 1),
                x = area["x"],
                y = area["y"],
                devices = info["deduct_device"],
                coordinate = ROBOT
            )

    Navigation.setGoodsPolyShape(
        points = goodsPointsInRobot,
        goodsName = recfile
    )
```

`transformPoints()` 和 `transformDeductInfos()` 都对每个点执行 `pos2World(point, palletFrontSurfacePoseInRobot)`。传给 `Navigation.setClearRegion()` 的坐标已经是机器人坐标，不能再调用第 6 节会重复应用 `basePose` 的 `set_deduct_area()`。

### 8.6 完整实例（D 面）

沿用 7.1 的公共输入，识别结果取 `palletWidth = 0.9`，`recSide = D`：

```pseudo
carrierShape = [
    {"x": 0.4,  "y": 0.6},
    {"x": -0.4, "y": 0.6},
    {"x": -0.4, "y": -0.6},
    {"x": 0.4,  "y": -0.6}
]
```

**① 识别面转换**（D 面为基准面，不旋转）：

```pseudo
carrierShape = [
    {"x": 0.4,  "y": 0.6},
    {"x": -0.4, "y": 0.6},
    {"x": -0.4, "y": -0.6},
    {"x": 0.4,  "y": -0.6}
]
```

**② `palletWidth` 修正**（`halfPalletWidth = 0.45`）：

```pseudo
carrierShape = [
    {"x": 0.4,  "y": 0.45},
    {"x": -0.4, "y": 0.45},
    {"x": -0.4, "y": -0.45},
    {"x": 0.4,  "y": -0.45}
]
```

**③ 计算 `palletLengthInX`**：

```pseudo
palletLengthInX = max(p["x"]) - min(p["x"]) = 0.4 - (-0.4) = 0.8
centerPoseInFrontSurface = [-0.4, 0, 0]
```

**④ 矩形中心 → 前表面中心坐标系**（`pos2World(point, [-0.4, 0, 0])`，X 平移 −0.4）：

```pseudo
carrierShape = [
    {"x": 0,    "y": 0.45},
    {"x": -0.8, "y": 0.45},
    {"x": -0.8, "y": -0.45},
    {"x": 0,    "y": -0.45}
]
```

**⑤ 计算前表面在机器人坐标系中的位姿**。取 `upFork` 抬升完成后的车体位姿，识别结果取同向（yaw 相等），便于手工验算：

```pseudo
robotPoseInWorldAfterPath = [0.8, 0.3, 0.4]
worldResult = [2.0, 0.3, 0.4]

palletFrontSurfacePoseInRobot = pos2Base(worldResult, robotPoseInWorldAfterPath)
                              = [1.2, 0, 0]
```

**⑥ 前表面局部坐标 → 机器人坐标**（`pos2World(point, [1.2, 0, 0])`，X 平移 +1.2）：

```pseudo
goodsPointsInRobot = [
    {"x": 1.2, "y": 0.45},
    {"x": 0.4, "y": 0.45},
    {"x": 0.4, "y": -0.45},
    {"x": 1.2, "y": -0.45}
]

deductAreaInRobot = {
    "x": [1.2, 0.4, 0.4, 1.2],
    "y": [0.45, 0.45, -0.45, -0.45]
}
```

若 `recSide = A`，① 旋转后 X 向跨度是 `carrierWidth = 1.2`，③ 的点集公式直接得到 `palletLengthInX = 1.2`，无需手工区分 A/C 与 D/B。

### 8.7 分支边界

```pseudo
if recognize == true:
    按 8.2～8.5 节使用识别宽度和前表面位姿加载
else:
    按第 6 节使用固定 basePose 加载
```

根据车体结构生成的碰撞检测区域不受此分支影响，不使用 `palletWidth` 或识别栈板位姿。
