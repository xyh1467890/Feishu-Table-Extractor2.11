@echo off
chcp 65001 >nul
setlocal

echo ============================================
echo   飞书多维表格管理工具 - Windows 打包脚本
echo ============================================
echo.

cd /d "%~dp0"

rem 检查 PyInstaller 是否已安装
echo [1/3] 检查 Python 环境...
py -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo   PyInstaller 未安装，正在安装...
    py -m pip install pyinstaller
    if errorlevel 1 (
        echo   错误：PyInstaller 安装失败，请检查网络或 pip 配置
        pause
        exit /b 1
    )
    echo   PyInstaller 安装成功
) else (
    echo   PyInstaller 已就绪
)
echo.

rem 清理旧的构建目录
echo [2/3] 清理旧的构建文件...
if exist "build" rd /s /q "build"
if exist "dist" rd /s /q "dist"
echo   清理完成
echo.

rem 使用 spec 文件打包
echo [3/3] 开始打包 exe...
py -m PyInstaller --noconfirm build_exe.spec
if errorlevel 1 (
    echo.
    echo   错误：打包失败，请查看上方错误信息
    pause
    exit /b 1
)

echo.
echo ============================================
echo   打包成功！
echo   可执行文件位置：dist\飞书多维表格管理工具.exe
echo ============================================
echo.
pause
