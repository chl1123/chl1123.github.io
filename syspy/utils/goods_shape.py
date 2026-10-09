"""货物形状的纯坐标变换（识别文件以 D 面为基准）。"""


def transform_goods_shape(points, recognition_side=None):
    """按栈板识别面旋转点列表；未指定识别面时保持原坐标。

    与 Fork 的 transform_pallet_point_by_rec_side 约定一致：
    A 顺时针 90°，B 180°，C 逆时针 90°，D 不旋转。
    不修改输入点；非法识别面抛出 ValueError，由解析入口记录并返回空形状。
    """
    side = recognition_side.upper() if isinstance(recognition_side, str) else recognition_side
    if side not in (None, "", "A", "B", "C", "D"):
        raise ValueError("invalid recognitionSide: {!r}".format(recognition_side))
    result = []
    for point in points:
        x, y = point["x"], point["y"]
        if side == "A":
            x, y = y, -x
        elif side == "B":
            x, y = -x, -y
        elif side == "C":
            x, y = -y, x
        result.append({"x": x, "y": y})
    return result
