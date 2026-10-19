#!/usr/bin/env bash
#
# RBK 3.6.0 接口测试入口。
#
# 用法：
#   ./run_tests.sh                      # 全部只读用例
#   ./run_tests.sh tests/unit/test_battery.py
#   ./run_tests.sh -k battery           # 透传给 pytest 的参数
#   RUN_DANGEROUS=1 ./run_tests.sh      # 启用会写状态的用例（第一轮没有）
#
# 设计要点：
# 1) 绝不 cd 到 scripts 目录。symlink 安装下 __file__ 会解析成真实路径，
#    syspy 的 param_server._get_prefix_dir 会因路径校验失败抛
#    "script path error"。统一在 /tmp 下启动，只用 PYTHONPATH 暴露逻辑路径。
# 2) RBK 的 IPC socket 属 root，非 root 运行时自动 sudo 重入（沿用旧版行为）。
# 3) pytest 不是目标机器的系统包。优先用已装的 pytest，其次安装到本仓库
#    .test_deps/（gitignore），避免污染系统 Python。
set -uo pipefail

SCRIPT_ROOT="/opt/.data/rbk/resources/scripts"
DEPS_DIR="$SCRIPT_ROOT/.test_deps"
REPORT_DIR="${RBK_TEST_REPORT_DIR:-$SCRIPT_ROOT/test-reports}"

# ---- 非 root 时自动提权重入（保留需要透传的环境变量）----
if [ "$(id -u)" -ne 0 ]; then
    exec sudo env \
        RUN_DANGEROUS="${RUN_DANGEROUS:-}" \
        RBK_TEST_REPORT_DIR="$REPORT_DIR" \
        RBK_TEST_LOG="${RBK_TEST_LOG:-}" \
        /bin/bash "$0" "$@"
fi

# ---- 找到可用的 pytest ----
PYTEST_ARGS=()
pytest_available() {
    PYTHONPATH="$DEPS_DIR:$SCRIPT_ROOT" python3 -c "import pytest" >/dev/null 2>&1
}

if ! pytest_available; then
    echo "[run_tests] 未检测到 pytest，尝试安装到 $DEPS_DIR（不污染系统 Python）"
    mkdir -p "$DEPS_DIR"
    if ! python3 -m pip install --target "$DEPS_DIR" --upgrade "pytest<9" >/tmp/rbk_pytest_install.log 2>&1; then
        echo "[run_tests] pytest 安装失败，日志：/tmp/rbk_pytest_install.log" >&2
        tail -n 15 /tmp/rbk_pytest_install.log >&2
        echo "" >&2
        echo "可手动安装后重试：" >&2
        echo "  python3 -m pip install --target $DEPS_DIR 'pytest<9'" >&2
        exit 2
    fi
fi

if ! pytest_available; then
    echo "[run_tests] pytest 仍不可用，请检查 $DEPS_DIR" >&2
    exit 2
fi

# ---- RBK IPC 前置检查（只警告，交给用例如实记录失败）----
for sock in /tmp/python2cpp_rpc.ipc /tmp/python2cpp_binmsg.ipc; do
    [ -S "$sock" ] || echo "[run_tests] 警告：未找到 RBK IPC socket $sock（RBK 未运行？）"
done

# ---- 默认收集 tests/unit，可被显式参数覆盖 ----
if [ "$#" -eq 0 ]; then
    PYTEST_ARGS=("$SCRIPT_ROOT/tests/unit")
else
    PYTEST_ARGS=("$@")
fi

mkdir -p "$REPORT_DIR"
export RBK_TEST_REPORT_DIR="$REPORT_DIR"
export RBK_TEST_LOG="${RBK_TEST_LOG:-$REPORT_DIR/results.log}"
export RUN_DANGEROUS="${RUN_DANGEROUS:-}"

echo "============================================================"
echo "RBK 3.6.0 接口测试（只读用例）"
echo "报告目录：$REPORT_DIR"
echo "============================================================"

# 关键：离开 scripts 目录再启动，避免 symlink 路径被 pytest 抢先解析。
# PYTHONDONTWRITEBYTECODE：以 root 运行会在仓库里留下 root 属主的 __pycache__，
# 之后普通用户无法编译/清理，所以直接禁用字节码写入。
cd /tmp || exit 2
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH="$DEPS_DIR:$SCRIPT_ROOT${PYTHONPATH:+:$PYTHONPATH}" \
    python3 -m pytest \
    -c "$SCRIPT_ROOT/tests/pytest.ini" \
    -p no:cacheprovider \
    -s -v \
    "${PYTEST_ARGS[@]}"
status=$?

echo ""
if [ -f "$REPORT_DIR/latest.md" ]; then
    echo "Markdown 报告：$REPORT_DIR/latest.md"
fi
echo "pytest 退出码：$status"
exit "$status"
