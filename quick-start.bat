@echo off
REM NeuroMatrix AI 报告系统 - 快速检查和启动脚本

setlocal enabledelayedexpansion

echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║   NeuroMatrix AI 报告系统 - 快速检查和启动              ║
echo ╚════════════════════════════════════════════════════════╝
echo.

REM 检查 Node.js
echo [检查环境]
node --version >nul 2>&1
if errorlevel 1 (
    echo ✗ Node.js 未安装 - 请从 https://nodejs.org 下载安装
    exit /b 1
) else (
    for /f "tokens=*" %%i in ('node --version') do echo ✓ Node.js %%i
)

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ✗ Python 未安装 - 请从 https://www.python.org 下载安装
    exit /b 1
) else (
    for /f "tokens=*" %%i in ('python --version') do echo ✓ %%i
)

REM 检查 npm 依赖
echo.
echo [检查依赖]
if exist "node_modules" (
    echo ✓ node_modules 已安装
) else (
    echo 🔄 npm 包缺失，正在安装...
    call npm install
    if errorlevel 1 (
        echo ✗ npm 安装失败
        exit /b 1
    )
)

REM 检查编译文件
echo.
echo [检查编译]
if exist "static/dist/index.html" (
    echo ✓ static/dist/index.html 已编译
) else (
    echo 🔄 生产文件缺失，正在编译...
    call npm run build
    if errorlevel 1 (
        echo ✗ 编译失败
        exit /b 1
    )
)

REM 显示启动说明
echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║  ✅ 环境检查完成！准备启动...                            ║
echo ╚════════════════════════════════════════════════════════╝
echo.

echo 启动选项:
echo   1. 开发模式 (推荐) - 快速热更新
echo   2. 生产模式 - 使用编译后的文件
echo   3. 退出
echo.

set /p choice="请选择 (1-3): "

if "%choice%"=="1" (
    echo.
    echo [开发模式] - 启动中...
    echo.
    echo 将在两个新窗口中启动:
    echo   • Vite 开发服务器 (http://localhost:5173)
    echo   • Flask 后端 (http://localhost:5000)
    echo.
    echo 报告页面: http://localhost:5000/report/1?file_id=test123
    echo.
    echo 按 Ctrl+C 停止任何一个服务
    echo.
    
    start "Vite Dev Server" cmd /k "npm run dev"
    timeout /t 3
    start "Flask Backend" cmd /k "set FLASK_ENV=development && python run.py"
) else if "%choice%"=="2" (
    echo.
    echo [生产模式] - 启动中...
    echo.
    echo Flask 后端在运行...
    echo 访问: http://localhost:5000/report/1?file_id=test123
    echo.
    echo 按 Ctrl+C 停止
    echo.
    python run.py
) else (
    echo 退出
    exit /b 0
)
