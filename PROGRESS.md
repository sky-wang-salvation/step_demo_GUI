# 开发进度记录

> 项目：Step AI 手机屏幕操控 Agent Demo
> 设备：vivo S19 · Android 15
> 模型：step-1o-turbo-vision · step-3.7-flash · stepaudio-2.5-asr · stepaudio-2.5-tts

---

## v0.3 — 2026-05-12 ✅ 模型架构重构：统一使用 step-3.7-flash

- [x] `step-1o-turbo-vision` 全部替换为 `step-3.7-flash`（多模态模型）
- [x] `step_agent.py` 重构：将原来的 描述屏幕(vision) + 规划(planner) + Grounding(vision) 三步合并为**单次多模态调用**
  - 截图直接传入 step-3.7-flash，模型同时输出动作类型 + 像素坐标
  - 每个 Step 从 2~3 次 API 调用降为 **1 次**，延迟更低
- [x] `vision_client.py` 更新：模型改为 step-3.7-flash
- [x] `config.py` 更新：移除 `MODEL_VISION`，新增 `MODEL_AGENT = "step-3.7-flash"`
- [x] `App.tsx` 前端更新：模型 Badge 和工作原理说明
- [x] `README.md` / `CONTEXT.md` 架构图和模型说明同步更新

---

## v0.2 — 2026-05-12 ✅ 环境配置完成 / ADB 无线连接成功

- [x] Python 依赖安装成功（openai 2.36.0, websockets 16.0 等）
- [x] 前端 npm install 成功（67个包）
- [x] ADB 安装成功（brew install android-platform-tools）
- [x] 手机无线 ADB 已配对并连接：`10.142.19.212:39297 device`
- [x] 后端服务首次启动成功：`ws://localhost:8766`
- [x] start.sh 路径 bug 已修复（`cd ../front_end` → `cd front_end`）

---

## v0.1 — 2026-05-12 ✅ 基础框架搭建完成

### 已完成

#### 项目基础
- [x] `.env` — API Key 配置（step API key 已填入）
- [x] `.env.example` — 配置模板（供 git 版本管理）
- [x] `.gitignore` — 排除 `.env`、`node_modules`、截图缓存等
- [x] `requirements.txt` — Python 依赖：openai, websockets, pillow, python-dotenv, aiohttp
- [x] `start.sh` — 一键启动后端+前端脚本

#### 后端
- [x] `backend/config.py` — 统一模型名、端口、延迟等配置
- [x] `backend/adb_controller.py` — ADB 封装：截图、tap、swipe、type（含中文支持）、返回/主页键、滚动
- [x] `backend/vision_client.py` — step-1o-turbo-vision 封装：`describe_screen()` + `ground_element()`
- [x] `backend/audio_client.py` — stepaudio-2.5-asr `transcribe()` + stepaudio-2.5-tts `speak()`
- [x] `backend/step_agent.py` — 核心 Agent Loop：截图→理解→规划→定位→执行，支持循环检测、TTS 播报
- [x] `backend/api_server.py` — WebSocket 服务器，管理 Agent 生命周期，广播截图/日志/音频

#### 前端
- [x] React + TypeScript + Vite 项目初始化
- [x] `App.tsx` — 三栏布局：左(控制面板) + 中(手机镜像) + 右(日志流)
  - 手机 Frame 组件：实时截图镜像 + 点击涟漪动画
  - 实时日志面板：颜色分级（info/warn/error/success）
  - 任务输入：文字 + 语音（按住录音，松开识别）
  - 快捷任务预设
  - ADB 连接状态指示
  - TTS 播报状态指示
  - WebSocket 自动重连

#### 文档
- [x] `README.md` — 架构说明、快速开始、演示场景
- [x] `PROGRESS.md` — 本文件

---

## 待完成 / 下一步

### 优先级 高

- [ ] **安装依赖并验证**
  ```bash
  pip3 install -r requirements.txt
  cd front_end && npm install
  ```
- [ ] **ADB 无线连接测试**
  ```bash
  adb connect <手机IP>:<端口>
  adb devices
  ```
- [ ] **后端单测**：单独测试截图 → vision_client → step API 链路
- [ ] **前端调试**：`npm run dev`，检查 WebSocket 连接

### 优先级 中

- [ ] **TTS Voice 确认**：确认 `stepaudio-2.5-tts` 可用的 voice 参数名称（当前用 `灿灿`，如报错需调整）
- [ ] **截图 Grounding 精度测试**：验证坐标定位在 vivo S19 (1080×2400) 上的准确性
- [ ] **前端 Ripple 优化**：将 tap 坐标从后端 log 解析并映射到手机框内坐标系

### 优先级 低（演示增强）

- [ ] 演示录屏（OBS/QuickTime）
- [ ] 添加 `step-image-edit-2` 用于截图标注（高亮即将点击的元素）
- [ ] 多 Agent 变体：规划 agent + 执行 agent 分离展示
- [ ] 添加任务耗时统计和每步延迟显示

---

## 已知问题 / 注意事项

| 问题 | 说明 | 状态 |
|------|------|------|
| vivo 无线 ADB 每次需重新配对 | 每次开关无线调试后 IP/端口会变 | 已知，使用时重新 connect |
| 中文输入需要 ADB Keyboard | 需手机安装 ADB Keyboard APK | 待安装 |
| TTS voice 参数未确认 | stepaudio-2.5-tts API voice 枚举需查官方文档 | 待确认 |
| 系统 UI 手势拦截 | vivo Android 15 的 back 手势可能失效，已改用 keyevent 4 | 已处理 |

---

## 文件清单（当前）

```
step_demo_GUI/
├── .env                          ✅
├── .env.example                  ✅
├── .gitignore                    ✅
├── requirements.txt              ✅
├── start.sh                      ✅
├── README.md                     ✅
├── PROGRESS.md                   ✅ (本文件)
├── backend/
│   ├── config.py                 ✅
│   ├── adb_controller.py         ✅
│   ├── vision_client.py          ✅
│   ├── audio_client.py           ✅
│   ├── step_agent.py             ✅
│   └── api_server.py             ✅
└── front_end/
    ├── package.json              ✅
    ├── vite.config.ts            ✅
    ├── tsconfig.json             ✅
    ├── tsconfig.node.json        ✅
    ├── index.html                ✅
    └── src/
        ├── main.tsx              ✅
        ├── App.tsx               ✅
        └── index.css             ✅
```

总计：19 个文件
