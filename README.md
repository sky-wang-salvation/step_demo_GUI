# Step AI · 手机屏幕操控 Agent Demo

> 基于阶跃星辰（Step AI）多模态大模型的 Android 手机 GUI Agent 演示系统

---

## 演示效果

用户说出或输入一句话指令（如："帮我打开美团查一下最近的订单"），系统自动：

1. **step-3.7-flash**（多模态）直接看截图，一次调用同时完成：
   - 理解当前屏幕内容
   - 规划下一步动作
   - GUI Grounding：定位目标元素的精确像素坐标
2. **ADB** 执行点击/滑动/文字输入等操作
3. 循环执行直到任务完成，最后由 **stepaudio-2.5-tts** 语音播报结果

---

## 核心能力展示点

| 能力 | 模型 | 说明 |
|------|------|------|
| 图像理解 + GUI Grounding + 规划 | **step-3.7-flash** | 多模态，一次调用看图→理解→规划→定位坐标 |
| 语音输入 | stepaudio-2.5-asr | 说话即可下达任务指令 |
| 语音播报 | stepaudio-2.5-tts | 任务结果自然语音反馈 |

---

## 系统架构

```
用户语音/文字指令
        ↓
  stepaudio-2.5-asr (语音→文字)
        ↓
  ┌──────────────── Agent Loop ────────────────┐
  │                                            │
  │  ADB Screenshot                            │
  │       ↓                                    │
  │  step-3.7-flash (多模态，单次调用)          │
  │  ├─ 看图理解当前屏幕                        │
  │  ├─ 规划下一步动作                          │
  │  └─ GUI Grounding → 返回像素坐标 (x, y)    │
  │       ↓                                    │
  │  ADB Execute (tap x,y / swipe / type ...)  │
  │       ↓                                    │
  │  循环，直到 action=done                     │
  └────────────────────────────────────────────┘
        ↓
  stepaudio-2.5-tts (播报结果)
```

---

## 目录结构

```
step_demo_GUI/
├── .env                      # API Key 配置（不上传 git）
├── .env.example              # 配置模板
├── .gitignore
├── requirements.txt          # Python 依赖
├── start.sh                  # 一键启动脚本
├── README.md
├── PROGRESS.md               # 开发进度记录
│
├── backend/
│   ├── config.py             # 全局配置（模型名、端口等）
│   ├── adb_controller.py     # ADB 设备控制封装
│   ├── vision_client.py      # 视觉模型调用（理解+Grounding）
│   ├── audio_client.py       # 语音模型调用（ASR+TTS）
│   ├── step_agent.py         # Agent 主循环逻辑
│   └── api_server.py         # WebSocket 服务器
│
└── front_end/
    ├── package.json
    ├── vite.config.ts
    ├── index.html
    └── src/
        ├── main.tsx
        ├── App.tsx            # 主界面：左控制面板+中手机镜像+右日志
        └── index.css
```

---

## 快速开始

### 1. 环境要求

- macOS / Linux
- Python 3.10+
- Node.js 16+
- Android 手机（开发者模式 + USB调试）
- ADB 工具：`brew install android-platform-tools`

### 2. 安装依赖

```bash
# Python 依赖
pip3 install -r requirements.txt

# 前端依赖
cd front_end && npm install
```

### 3. 手机配置（vivo S19 / Android 15）

1. 设置 → 关于手机 → 连点「版本号」7次 → 开启开发者模式
2. 开发者选项 → USB调试 → 开启 → 选「始终允许」
3. 开发者选项 → 无线调试 → 开启 → 记录 IP:端口
4. 安装 ADB Keyboard（处理中文输入）

```bash
# 无线连接手机
adb connect 192.168.x.x:端口
adb devices   # 确认已连接
```

### 4. 启动服务

```bash
# 方法 1：一键启动
bash start.sh

# 方法 2：分别启动
# 终端 1
cd backend && python api_server.py

# 终端 2
cd front_end && npm run dev
```

### 5. 访问界面

浏览器打开 http://localhost:5173

---

## 推荐演示场景

| 场景 | 指令示例 |
|------|----------|
| 外卖订单查询 | "打开美团，查看最近订单状态" |
| 消息查看 | "打开微信，告诉我最新一条消息" |
| 支付查询 | "打开支付宝，查询账户余额" |
| 通用任务 | 任意自然语言描述手机操作 |

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 视觉理解 + GUI Grounding + 规划 | **Step-3.7-Flash**（多模态，统一处理） |
| 语音识别 | StepAudio-2.5-ASR |
| 语音合成 | StepAudio-2.5-TTS |
| 设备控制 | ADB (Android Debug Bridge) |
| 前端 | React + TypeScript + Vite |
| 后端 | Python asyncio + WebSockets |

---

## 注意事项

- `.env` 文件含 API Key，已加入 `.gitignore`，**请勿提交**
- 首次运行建议用简单场景（如"打开设置"）测试 ADB 连通性
- 演示时建议使用无线 ADB（手机自由摆放在支架上）
