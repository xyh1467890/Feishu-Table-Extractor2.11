#!/bin/bash
# 飞书多维表格管理工具 — macOS 一键打包脚本
# 在 macOS 终端中依次执行:
#   1) chmod +x build_mac.sh
#   2) ./build_mac.sh
#
# 打包完成后会在 dist/ 目录生成 "飞书多维表格管理工具.app"

set -e

echo "============================================"
echo "  飞书多维表格管理工具 - macOS 打包"
echo "============================================"
echo ""

cd "$(dirname "$0")"

# 1. 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 python3，请先安装 Python 3.10+"
    echo "   下载地址: https://www.python.org/downloads/"
    exit 1
fi
echo "✅ 检测到 Python: $(python3 --version)"
echo ""

# 2. 安装依赖（含 PyInstaller）
echo "[1/3] 安装 Python 依赖..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
python3 -m pip install pyinstaller
echo "✅ 依赖安装完成"
echo ""

# 3. 清理旧构建
echo "[2/3] 清理旧的构建文件..."
rm -rf build dist
echo "✅ 清理完成"
echo ""

# 4. 执行 PyInstaller 打包
echo "[3/3] 开始打包 .app（通常需要 1~3 分钟，请耐心等待）..."
python3 -m PyInstaller --noconfirm build_mac.spec
echo ""

echo "============================================"
echo "  ✅ 打包成功！"
echo "     产物: dist/飞书多维表格管理工具.app"
echo "============================================"
echo ""
echo "▸ 直接在 Finder 里双击即可运行"
echo ""
echo "▸ 如果 macOS 提示『无法打开』，请在终端执行一次:"
echo "    xattr -dr com.apple.quarantine dist/飞书多维表格管理工具.app"
echo ""
echo "▸ 也可以在『系统设置 → 隐私与安全性』中点击『仍要打开』"
echo ""
echo "▸ 分发给其他 Mac 用户建议进行签名/公证:"
echo "    codesign --deep --force --sign - dist/飞书多维表格管理工具.app"
echo ""
