#!/bin/bash
# NeuroMatrix AI 报告系统启动脚本（macOS/Linux）

echo "================================"
echo "  NeuroMatrix AI 报告系统启动"
echo "================================"
echo ""

# 设置环境变量
export FLASK_ENV=development
export FLASK_APP=app.py

# 启动 Vite 开发服务器
echo "[1/2] 启动 Vite 开发服务器 (http://localhost:5173)..."
npm run dev &
VITE_PID=$!

# 等待 Vite 启动
sleep 3

# 启动 Flask 后端
echo "[2/2] 启动 Flask 后端 (http://localhost:5000)..."
python run.py &
FLASK_PID=$!

# 等待进程
wait

# 清理
kill $VITE_PID $FLASK_PID 2>/dev/null

echo ""
echo "================================"
echo "系统已停止"
echo "================================"
