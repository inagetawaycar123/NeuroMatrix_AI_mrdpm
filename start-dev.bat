@echo off
REM NeuroMatrix AI 报告系统启动脚本（Windows）

echo ================================
echo  NeuroMatrix AI 报告系统启动
echo ================================
echo.

REM 设置环境变量
set FLASK_ENV=development
set FLASK_APP=app.py

REM 启动 Vite 开发服务器
echo [1/2] 启动 Vite 开发服务器 (http://localhost:5173)...
echo.
start "Vite Dev Server" cmd /k "npm run dev"

REM 等待 Vite 启动
timeout /t 3

REM 启动 Flask 后端
echo [2/2] 启动 Flask 后端 (http://localhost:5000)...
echo.
python run.py

echo.
echo ================================
echo 访问: http://localhost:5000
echo ================================
pause
