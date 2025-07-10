#!/bin/bash

# 检查参数
if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    echo "Usage: $0 <version> [architecture]"
    exit 1
fi

VERSION="$1"
ARCH="all"
SRC=""

# 设置架构
if [ "$#" -eq 2 ]; then
    case "$2" in
        x86)
            ARCH="amd64"
            SRC="-2000"
            ;;
        arm)
            ARCH="arm64"
            SRC="-880-1000-3000"
            ;;
        *)
            echo "错误: 不支持的架构 '$2'. 支持的架构: x86, arm"
            exit 1
            ;;
    esac
fi

TIMESTAMP=$(date +"%Y%m%d%H%M%S")
FILE_NAME="SRC-Scripts${SRC}-v${VERSION}-${TIMESTAMP}"
DEB_NAME="${FILE_NAME}.deb"

# 创建临时构建目录
BUILD_ROOT=$(mktemp -d)
BUILD_DIR="${BUILD_ROOT}/build_dir"
INSTALL_DIR="/opt/.data/rbk/resources/scripts"

echo "构建临时目录: ${BUILD_ROOT}"

# 检查syspy目录是否存在
if [ ! -d "syspy" ]; then
    echo "错误: 当前目录下找不到'syspy'文件夹!"
    rm -rf "${BUILD_ROOT}"
    exit 1
fi

# 创建目录结构
mkdir -p "${BUILD_DIR}/DEBIAN"
mkdir -p "${BUILD_DIR}/${INSTALL_DIR}"

# 复制文件到临时构建目录
cp -r syspy "${BUILD_DIR}/${INSTALL_DIR}/"

# 创建preinst安装前脚本
cat > "${BUILD_DIR}/DEBIAN/preinst" <<EOF
#!/bin/bash
set -e

# 处理script-syspy冲突
if dpkg -s script-syspy >/dev/null 2>&1; then
    echo "检测到冲突包: script-syspy"
    echo "正在准备卸载冲突包..."

    # 使用dpkg命令卸载冲突包
    dpkg -r --force-depends script-syspy || {
        echo "警告: 无法正常卸载冲突包，尝试强制移除"
        dpkg --purge --force-all script-syspy
    }
fi

# 不删除整个目录，仅准备覆盖更新
echo "准备更新syspy SDK到目录: ${INSTALL_DIR}"
EOF

# 创建postinst安装后脚本
cat > "${BUILD_DIR}/DEBIAN/postinst" <<EOF
#!/bin/bash
set -e

# 确保目标目录存在
mkdir -p ${INSTALL_DIR}

# 设置文件权限
chmod -R 777 ${INSTALL_DIR}/syspy

# 验证安装结果
if [ -d "${INSTALL_DIR}/syspy" ]; then
    echo "syspy SDK 已成功更新到 ${INSTALL_DIR}"
    echo "更新策略: 仅覆盖同名文件，保留其他文件"
else
    echo "错误: 安装失败!"
    exit 1
fi
EOF

# 创建prerm卸载前脚本
cat > "${BUILD_DIR}/DEBIAN/prerm" <<EOF
#!/bin/bash
# 保留所有用户数据 - 不删除任何文件
if [ "\$1" = "remove" ] || [ "\$1" = "deconfigure" ]; then
    echo "保留所有syspy目录内容: ${INSTALL_DIR}/syspy"
fi
EOF

# 设置脚本权限
chmod 755 "${BUILD_DIR}/DEBIAN/preinst"
chmod 755 "${BUILD_DIR}/DEBIAN/postinst"
chmod 755 "${BUILD_DIR}/DEBIAN/prerm"

# 创建control文件（添加冲突解决机制）
cat > "${BUILD_DIR}/DEBIAN/control" <<EOF
Package: src-scripts
Version: ${VERSION}
Section: base
Priority: optional
Architecture: ${ARCH}
Maintainer: SEER
Conflicts: script-syspy
Replaces: script-syspy
Description: syspy Python SDK
 此软件包将syspy SDK部署到${INSTALL_DIR}目录
 包含冲突解决机制，自动移除旧包
 更新策略: 仅覆盖同名文件，保留目录中的其他文件
EOF

# 构建deb包到临时目录
dpkg-deb --build "${BUILD_DIR}" "${BUILD_ROOT}/${DEB_NAME}"

# 创建 ./deb 目录（如果不存在）
mkdir -p "./deb"

# 将生成的deb文件移动到当前目录的 ./deb 子目录
mv "${BUILD_ROOT}/${DEB_NAME}" "./deb/"

# 压缩deb文件为zip格式
cd "./deb" || exit
zip "${FILE_NAME}.zip" "${DEB_NAME}"

# 清理所有临时文件
rm -rf "${BUILD_ROOT}"

echo "----------------------------------------"
echo "成功生成: ${DEB_NAME}"
echo "安装命令: sudo dpkg -i --force-overwrite ${DEB_NAME}"
echo "临时文件已完全清理"
echo "更新策略: 安装时仅覆盖同名文件，保留syspy目录中的其他文件"