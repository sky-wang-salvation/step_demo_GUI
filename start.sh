#!/bin/bash
# Step Demo GUI - 一键启动脚本

echo "🚀 启动 Step Demo GUI..."
echo ""

# 检查 ADB
if ! command -v adb &> /dev/null; then
    echo "⚠️  ADB 未安装，请运行: brew install android-platform-tools"
    echo ""
fi

# 启动后端
echo "▶ 启动后端 WebSocket 服务 (端口 8766)..."
python backend/api_server.py &
BACKEND_PID=$!
echo "  后端 PID: $BACKEND_PID"

sleep 1

# 启动前端
echo "▶ 启动前端开发服务器 (端口 5173)..."
cd front_end && npm run dev &
FRONTEND_PID=$!
echo "  前端 PID: $FRONTEND_PID"

echo ""
echo "✅ 服务已启动："
echo "   前端: http://localhost:5173"
echo "   后端: ws://localhost:8766"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 等待并清理
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo '服务已停止'" EXIT
wait
