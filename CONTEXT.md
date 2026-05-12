# 项目背景与阶段性成果
> 供下一轮 Agent 对话使用的上下文文档
> 最后更新：2026-05-12 16:05

---

## 项目定位

**为阶跃星辰（Step AI）新模型发布做宣传 Demo**，展示以下核心能力：
- 多模态图像理解（手机截图 → 内容解析）
- GUI Grounding（自然语言 → 精确像素坐标）
- 多步 Agentic 任务执行（长程规划）
- 实时语音交互（ASR + TTS）

Demo 形式：用户说出/输入一句话指令，AI 自动控制 Android 手机完成任务，全程在浏览器界面实时呈现。

---

## 技术架构

```
用户语音指令
    ↓
stepaudio-2.5-asr (语音→文字)
    ↓
┌──────────────── Agent Loop ─────────────────┐
│  ADB 截图                                   │
│      ↓                                      │
│  step-3.7-flash (多模态，单次调用)           │
│  ├─ 看图理解当前屏幕内容                     │
│  ├─ 规划下一步动作                           │
│  └─ GUI Grounding → 返回像素坐标 (x, y)     │
│      ↓                                      │
│  ADB 执行 (tap x,y / swipe / type / back)   │
│      ↓ 循环                                 │
└─────────────────────────────────────────────┘
    ↓ 任务完成
stepaudio-2.5-tts (播报结果)
```

**架构亮点**：step-3.7-flash 是多模态模型，一次 API 调用同时完成原来需要两次调用才能完成的工作（视觉理解 + 规划 + Grounding），降低延迟，提升效率。

---

## 使用的模型

| 模型 | 用途 |
|------|------|
| `step-3.7-flash` | **多模态统一处理**：截图理解 + GUI Grounding（坐标定位）+ 任务规划，一次调用完成 |
| `stepaudio-2.5-asr` | 语音输入识别 |
| `stepaudio-2.5-tts` | 任务结果语音播报 |

API Key：`D5oHFtxLh4LEetPQXRKMjn11e00hEKeMJZuHXmQpcQse43jH4nUljILMLBiMuFrC`
Base URL：`https://api.stepfun.com/v1`

---

## 硬件环境

| 设备 | 信息 |
|------|------|
| 手机 | vivo S19 · Android 15 · 1080×2400 |
| 电脑 | MacBook（macOS · Apple Silicon） |
| 网络 | 同一 WiFi：JYXC-Renzheng |
| 手机 IP | `10.142.19.212` |
| 电脑 IP | `10.142.22.34` |

---

## 当前进度（截至 2026-05-12 16:05）

### ✅ 已完成

#### 环境配置
- [x] Python 3.13 可用
- [x] Node.js v24 / npm 11 可用
- [x] ffmpeg 已安装（brew）
- [x] `pip3 install -r requirements.txt` 成功
  - openai 2.36.0、websockets 16.0、pillow 12.2.0、aiohttp 3.13.5 等
- [x] `npm install`（front_end）成功，67 个包
- [x] ADB 已安装（brew install android-platform-tools）
- [x] **手机无线 ADB 已配对并连接**
  - 连接命令：`adb connect 10.142.19.212:39297`
  - 确认命令：`adb devices` → `10.142.19.212:39297  device` ✅

#### 项目文件（22个，全部创建完毕）
```
step_demo_GUI/
├── .env                    ✅ API Key 已填入
├── .env.example            ✅
├── .gitignore              ✅
├── requirements.txt        ✅
├── start.sh                ✅ (路径bug已修复)
├── README.md               ✅
├── PROGRESS.md             ✅
├── CONTEXT.md              ✅ (本文件)
├── backend/
│   ├── config.py           ✅ 模型名/端口/延迟配置
│   ├── adb_controller.py   ✅ ADB封装(截图/tap/swipe/type/键盘)
│   ├── vision_client.py    ✅ 屏幕理解 + GUI Grounding
│   ├── audio_client.py     ✅ ASR transcribe + TTS speak
│   ├── step_agent.py       ✅ 核心Agent Loop
│   └── api_server.py       ✅ WebSocket服务器
└── front_end/
    ├── package.json        ✅
    ├── vite.config.ts      ✅
    ├── tsconfig.json       ✅
    ├── tsconfig.node.json  ✅
    ├── index.html          ✅
    └── src/
        ├── main.tsx        ✅
        ├── App.tsx         ✅ 三栏布局(控制+手机镜像+日志)
        └── index.css       ✅
```

#### 服务状态
- [x] 后端已启动：`ws://localhost:8766`（`python backend/api_server.py` 运行中）
- [ ] 前端尚未启动（start.sh bug已修复，需重新启动）

---

## 待完成 / 下一步

### 立即可做

1. **启动前端**（重新运行 start.sh 或手动启动）
   ```bash
   # 终端1: 后端（如已运行跳过）
   cd ~/Desktop/step_demo_GUI/backend && python api_server.py

   # 终端2: 前端
   cd ~/Desktop/step_demo_GUI/front_end && npm run dev
   ```
   浏览器打开 `http://localhost:5173`

2. **ADB 重连**（如端口变了）
   ```bash
   # 进手机「开发者选项 → 无线调试」查新端口
   adb connect 10.142.19.212:新端口
   ```

3. **首次端到端测试**：在界面输入简单任务如「打开设置」，验证全链路

### 已知待确认问题

| 问题 | 说明 |
|------|------|
| TTS voice 参数 | `stepaudio-2.5-tts` 的 voice 枚举未确认，当前用 `灿灿`，如报错需查官方文档调整 |
| ADB Keyboard | 处理中文输入需安装 ADB Keyboard APK（目前未安装，会影响中文文字输入类任务） |
| 端口每次变化 | vivo 每次开关无线调试端口会变，需重新 connect |

### 后续优化方向

- [ ] 前端 Ripple 动画：将 tap 坐标从后端 log 解析并精确映射到手机框坐标系
- [ ] 演示场景脚本化（美团订单查询完整流程录制）
- [ ] 添加步骤耗时统计（每步 latency 显示）
- [ ] Multi-agent 变体：规划 agent + 执行 agent 分离，展示「多 Agent team」能力

---

## 关键文件路径

| 文件 | 绝对路径 |
|------|----------|
| 项目根目录 | `/Users/jyxc-dz-0100672/Desktop/step_demo_GUI/` |
| Agent 核心逻辑 | `backend/step_agent.py` |
| 视觉模型调用 | `backend/vision_client.py` |
| ADB 控制 | `backend/adb_controller.py` |
| WebSocket 服务 | `backend/api_server.py` |
| 前端主界面 | `front_end/src/App.tsx` |
| 启动脚本 | `start.sh` |

---

## 本次对话参考链接

- [GUI-Stride 原项目](https://github.com/bseazh/GUI-Stride)（作者自有，ADB基础设施参考）
- [AppAgent](https://github.com/TencentQQGYLab/AppAgent)（Tencent开源，Agent Loop模式参考）
- [阶跃视觉模型文档](https://platform.stepfun.com/docs/zh/guides/models/vision)
- [阶跃语音模型文档](https://platform.stepfun.com/docs/zh/guides/models/audio)
