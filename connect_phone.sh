#!/bin/bash
# 快速连接手机无线 ADB
# 用法：bash connect_phone.sh [端口号]
# 例如：bash connect_phone.sh 39297
# 若不传端口，脚本会提示你输入

PHONE_IP="10.142.19.212"

if [ -n "$1" ]; then
    PORT=$1
else
    echo "📱 手机 IP: $PHONE_IP"
    echo "👉 请在手机「开发者选项 → 无线调试」详情页查看端口号"
    read -p "输入端口号: " PORT
fi

echo ""
echo "▶ 连接中: adb connect $PHONE_IP:$PORT"
adb connect "$PHONE_IP:$PORT"

echo ""
echo "▶ 当前设备列表:"
adb devices

# 判断是否连接成功
if adb devices | grep -q "$PHONE_IP:$PORT.*device"; then
    echo ""
    echo "✅ 连接成功！请点击浏览器前端界面左上角「刷新」按钮确认。"
    # 保存端口到文件，下次可以直接用
    echo "$PORT" > .last_adb_port
    echo "（端口 $PORT 已保存，下次运行 bash connect_phone.sh 会自动读取）"
else
    echo ""
    echo "❌ 连接失败，请检查："
    echo "   1. 手机和电脑在同一 WiFi (JYXC-Renzheng)"
    echo "   2. 端口号是否正确（手机「无线调试」详情页查看）"
    echo "   3. 是否已完成配对（首次需要 adb pair）"
fi
