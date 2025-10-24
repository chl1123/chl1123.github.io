#!/bin/bash

# 检查参数
if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    echo "Usage: $0 <version> [config_file]"
    echo "Example: $0 1.0.1"
    exit 1
fi

VERSION="$1"
CONFIG_FILE="${2:-build_dir.conf}"  # 默认配置文件名

# 读取配置文件中的脚本列表
if [ -f "$CONFIG_FILE" ]; then
    SCRIPT_FILES=$(cat "$CONFIG_FILE" | grep -v "^#" | grep -v "^$" | tr '\n' ' ')
    echo "从配置文件读取脚本列表: $SCRIPT_FILES"
else
    echo "错误: 配置文件 '$CONFIG_FILE' 不存在!"
    exit 1
fi

# 定义架构数组
ARCHITECTURES=("x86" "arm")

# 保存当前目录
ORIGINAL_DIR=$(pwd)

echo "开始构建所有架构版本..."

# 为每个架构构建deb包
for arch in "${ARCHITECTURES[@]}"; do
    echo "========================================"
    echo "正在构建 ${arch} 架构版本..."
    echo "========================================"

    # 重置变量
    ARCH="all"
    SRC=""

    # 设置架构特定变量
    case "${arch}" in
        x86)
            ARCH="amd64"
            SRC="-2000-5000"
            ;;
        arm)
            ARCH="arm64"
            SRC="-880-1000-3000"
            ;;
    esac

    TIMESTAMP=$(date +"%Y%m%d%H%M%S")
    FILE_NAME="SRC-Scripts${SRC}-incremental-v${VERSION}-${TIMESTAMP}"
    DEB_NAME="${FILE_NAME}.deb"

    # 创建临时构建目录
    BUILD_ROOT=$(mktemp -d)
    BUILD_DIR="${BUILD_ROOT}/build_dir"
    INSTALL_DIR="/opt/.data/rbk/resources/scripts"

    echo "构建临时目录: ${BUILD_ROOT}"

    # 检查脚本文件是否存在，并支持目录
    EXPANDED_SCRIPT_FILES=""
    for item in ${SCRIPT_FILES}; do
        if [ -d "${item}" ]; then
            # 如果是目录，获取其中所有.py文件
            for pyfile in $(find "${item}" -name "*.py" -type f); do
                EXPANDED_SCRIPT_FILES="${EXPANDED_SCRIPT_FILES} ${pyfile}"
            done
        elif [ -f "${item}" ]; then
            # 如果是文件，直接添加
            EXPANDED_SCRIPT_FILES="${EXPANDED_SCRIPT_FILES} ${item}"
        else
            echo "错误: '${item}' 不存在且不是有效目录!"
            rm -rf "${BUILD_ROOT}"
            exit 1
        fi
    done

    # 更新SCRIPT_FILES为展开后的实际文件列表
    SCRIPT_FILES=$(echo $EXPANDED_SCRIPT_FILES | tr ' ' '\n' | grep -v "^$" | tr '\n' ' ')

    if [ -z "$SCRIPT_FILES" ]; then
        echo "错误: 没有找到有效的脚本文件!"
        rm -rf "${BUILD_ROOT}"
        exit 1
    fi

    # 创建目录结构
    mkdir -p "${BUILD_DIR}/DEBIAN"
    mkdir -p "${BUILD_DIR}/${INSTALL_DIR}"

    # 创建目标子目录并复制文件（保留目录结构）
    for script in ${SCRIPT_FILES}; do
        # 获取文件的目录部分
        script_dir=$(dirname "${script}")
        # 在目标目录中创建相应的子目录
        mkdir -p "${BUILD_DIR}/${INSTALL_DIR}/${script_dir}"
        # 复制文件到对应目录
        cp "${script}" "${BUILD_DIR}/${INSTALL_DIR}/${script_dir}/"
    done

    # 创建preinst安装前脚本
    cat > "${BUILD_DIR}/DEBIAN/preinst" <<EOF
#!/bin/bash
set -e

echo "准备安装增量更新..."
EOF

    # 创建postinst安装后脚本
    cat > "${BUILD_DIR}/DEBIAN/postinst" <<EOF
#!/bin/bash
set -e

# 设置文件权限
for script in ${SCRIPT_FILES}; do
    if [ -f "${INSTALL_DIR}/\${script}" ]; then
        chmod 755 "${INSTALL_DIR}/\${script}"
        echo "已更新脚本: \${script}"
    fi
done

echo "增量更新安装完成"
EOF

    # 创建prerm卸载前脚本
    cat > "${BUILD_DIR}/DEBIAN/prerm" <<EOF
#!/bin/bash
# 增量更新卸载不删除文件
echo "卸载增量更新包"
EOF

    # 设置脚本权限
    chmod 755 "${BUILD_DIR}/DEBIAN/preinst"
    chmod 755 "${BUILD_DIR}/DEBIAN/postinst"
    chmod 755 "${BUILD_DIR}/DEBIAN/prerm"

    # 创建control文件
    cat > "${BUILD_DIR}/DEBIAN/control" <<EOF
Package: src-scripts-incremental
Version: ${VERSION}
Section: base
Priority: optional
Architecture: ${ARCH}
Maintainer: SEER
Description: syspy Scripts Incremental Update
 此软件包提供对${INSTALL_DIR}目录下脚本文件的增量更新
 包含以下文件: ${SCRIPT_FILES}
EOF

    # 构建deb包到临时目录
    dpkg-deb --build "${BUILD_DIR}" "${BUILD_ROOT}/${DEB_NAME}"

    # 创建 ./deb 目录（如果不存在）
    mkdir -p "./deb"

    # 将生成的deb文件移动到当前目录的 ./deb 子目录
    mv "${BUILD_ROOT}/${DEB_NAME}" "./deb/"

    # 进入deb目录压缩deb文件为zip格式
    cd "./deb" || exit
    zip "${FILE_NAME}.zip" "${DEB_NAME}"

    # 返回原始目录
    cd "${ORIGINAL_DIR}" || exit

    # 清理临时文件
    rm -rf "${BUILD_ROOT}"

    echo "----------------------------------------"
    echo "成功生成 ${arch} 架构增量更新包: ${DEB_NAME}"
    echo "包含脚本文件: ${SCRIPT_FILES}"
    echo "安装命令: sudo dpkg -i --force-all deb/${DEB_NAME}"
    echo "----------------------------------------"
done

echo "========================================"
echo "所有架构版本构建完成!"
echo "生成的文件位于 ./deb/ 目录中"
echo "临时文件已完全清理"
