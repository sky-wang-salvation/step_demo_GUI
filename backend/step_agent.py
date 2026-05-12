"""
Step Agent — Core Agent Loop
step-3.7-flash (多模态) 直接看截图，一次调用完成：
  看图理解屏幕内容 + 规划下一步动作 + GUI Grounding (坐标定位)
架构：截图→压缩→step-3.7-flash(图+文)→正则解析动作JSON(含坐标)→坐标还原→ADB执行→循环
"""

import asyncio
import json
import logging
import re
from typing import Callable, Awaitable, Optional

from openai import OpenAI
from config import (
    STEP_API_KEY, STEP_BASE_URL, MODEL_AGENT, MAX_STEPS, ACTION_DELAY_SEC,
    AGENT_TEMPERATURE, AGENT_TOP_P, AGENT_FREQ_PENALTY, AGENT_MAX_TOKENS,
    SCREENSHOT_SCALE, STATE_COMPRESS_INTERVAL, STATE_COMPRESS_KEEP,
)
from adb_controller import ADBController
from audio_client import speak

logger = logging.getLogger(__name__)
_client = OpenAI(api_key=STEP_API_KEY, base_url=STEP_BASE_URL)

# ── System Prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
你是一个 Android 手机 GUI 操控 Agent（设备：vivo S19，Android 15）。
每一轮你会收到手机屏幕的截图，你需要：看图理解当前状态，规划并执行下一步最佳动作。

=== 屏幕信息 ===
图片分辨率：{display_w}×{display_h} 像素（坐标原点在左上角）
所有坐标必须基于此图片分辨率。

=== 可用动作 ===
tap        — 点击 UI 元素。必须提供 "x" 和 "y"（元素中心像素坐标）。
type       — 在已聚焦输入框中输入文字。必须提供 "text"。
swipe_up   — 向上滑动（查看下方内容）。
swipe_down — 向下滑动（查看上方内容）。
swipe_left — 向左滑动。
swipe_right— 向右滑动。
back       — 按 Android 返回键。
home       — 按 Android Home 键，回到桌面。
enter      — 按确认/回车键。
wait       — 等待页面/动画完成。
done       — 任务已完成。必须提供中文 "summary" 描述结果。

=== 输出格式（严格 JSON，不加任何其他文字）===
{{
  "action": "<动作名>",
  "x": <整数>,          // tap 必填：元素中心 x 像素坐标
  "y": <整数>,          // tap 必填：元素中心 y 像素坐标
  "text": "<字符串>",   // type 必填
  "reason": "<一句话说明原因>",
  "summary": "<中文结果摘要>"  // done 必填
}}

=== 规则 ===
1. 只输出合法 JSON，不加 markdown 代码块，不加 JSON 之外的任何文字。
2. tap 时仔细识别图中元素位置，输出其精确中心坐标。
3. 若连续 3 次相同动作无进展，尝试其他方式或报告失败原因后输出 done。
4. 如果任务需要读取屏幕信息（订单状态、余额等），提取后放入 summary。
5. reason 保持简短，一句话。
"""

# ── State Compression ─────────────────────────────────────────────────────────

def _compress_action_history(history: list) -> list:
    """保留最近 STATE_COMPRESS_KEEP 步的详情，更早的合并为摘要条目。"""
    if len(history) <= STATE_COMPRESS_KEEP:
        return history
    old = history[:-STATE_COMPRESS_KEEP]
    recent = history[-STATE_COMPRESS_KEEP:]
    summary = {
        "step": "summary",
        "action": f"已完成 {len(old)} 步操作（已压缩）",
        "steps": [f"步{h['step']}:{h['action']}" for h in old if isinstance(h.get("step"), int)],
    }
    return [summary] + recent


def _extract_json(text: str) -> Optional[dict]:
    """从模型输出中提取 JSON，兼容思维链 <think>...</think> 前缀。"""
    # 去掉 <think>...</think> 块
    cleaned = re.sub(r'<think>[\s\S]*?</think>', '', text, flags=re.IGNORECASE).strip()
    # 找最外层 {...}
    match = re.search(r'\{[\s\S]*\}', cleaned)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    # 降级：直接在原文中找
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


# ── Agent ─────────────────────────────────────────────────────────────────────

class StepAgent:
    def __init__(self):
        self.adb = ADBController()
        self.running = False
        self.screen_w = 1080
        self.screen_h = 2400
        # 发送给模型的图片分辨率（压缩后）
        self.display_w = int(1080 * SCREENSHOT_SCALE)
        self.display_h = int(2400 * SCREENSHOT_SCALE)

    async def run(
        self,
        task: str,
        log_cb: Callable[[str, str], Awaitable[None]],
        screenshot_cb: Optional[Callable[[str], Awaitable[None]]] = None,
        action_cb: Optional[Callable[[dict], Awaitable[None]]] = None,
        tts_cb: Optional[Callable[[bytes], Awaitable[None]]] = None,
    ):
        self.running = True

        async def log(msg: str, level: str = "info"):
            logger.info(f"[{level}] {msg}")
            await log_cb(msg, level)

        await log(f"任务开始: {task}")

        # ADB check
        if not await asyncio.to_thread(self.adb.is_connected):
            await log("ADB 未连接，请检查手机无线/USB连接", "error")
            self.running = False
            return

        # 获取真实屏幕分辨率
        try:
            self.screen_w, self.screen_h = await asyncio.to_thread(self.adb.get_screen_size)
            self.display_w = int(self.screen_w * SCREENSHOT_SCALE)
            self.display_h = int(self.screen_h * SCREENSHOT_SCALE)
            await log(f"屏幕分辨率: {self.screen_w}×{self.screen_h}（发送给模型: {self.display_w}×{self.display_h}）")
        except Exception as e:
            await log(f"获取屏幕尺寸失败，使用默认值: {e}", "warn")

        system_prompt = SYSTEM_PROMPT.format(
            display_w=self.display_w,
            display_h=self.display_h,
        )

        history: list[dict] = []
        action_history: list[dict] = []
        consecutive_same = 0
        last_action = None

        for step in range(1, MAX_STEPS + 1):
            if not self.running:
                await log("任务被用户停止", "warn")
                break

            await log(f"── Step {step}/{MAX_STEPS} ──────────────────")

            # ── 1. 截图（压缩后发送给模型）──
            try:
                await log("截取屏幕...")
                screenshot_b64 = await asyncio.to_thread(
                    self.adb.screenshot_b64, SCREENSHOT_SCALE
                )
                if screenshot_cb:
                    # 前端展示用原图（1:1），重新截一次不压缩
                    display_b64 = await asyncio.to_thread(self.adb.screenshot_b64, 1.0)
                    await screenshot_cb(display_b64)
            except Exception as e:
                await log(f"截图失败: {e}", "error")
                break

            # ── 2. 多模态单次调用：视觉理解 + 规划 + Grounding ──
            await log(f"step-3.7-flash 分析屏幕并规划动作（temperature={AGENT_TEMPERATURE}）...")

            user_content = [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{screenshot_b64}"}
                },
                {
                    "type": "text",
                    "text": (
                        f"用户任务: {task}\n"
                        f"已执行步骤（{len(action_history)} 步）: "
                        f"{json.dumps(action_history, ensure_ascii=False) if action_history else '无'}\n\n"
                        "请看截图，决定下一步动作，只输出 JSON。"
                    )
                }
            ]

            messages = (
                [{"role": "system", "content": system_prompt}]
                + history
                + [{"role": "user", "content": user_content}]
            )

            try:
                resp = await asyncio.to_thread(
                    lambda: _client.chat.completions.create(
                        model=MODEL_AGENT,
                        messages=messages,
                        temperature=AGENT_TEMPERATURE,
                        top_p=AGENT_TOP_P,
                        frequency_penalty=AGENT_FREQ_PENALTY,
                        max_tokens=AGENT_MAX_TOKENS,
                        # 不设 response_format：step-3.7-flash thinking 模式不兼容 json_object
                    )
                )
                raw_text = resp.choices[0].message.content.strip()
                action = _extract_json(raw_text)

                if action is None:
                    await log(f"模型输出无法解析为 JSON（原文前200字）: {raw_text[:200]}", "error")
                    break

                # 历史只保存文字摘要，不重复放图片（控制 token）
                history.append({
                    "role": "user",
                    "content": f"[Step {step}] 截图已分析，任务: {task}"
                })
                history.append({"role": "assistant", "content": json.dumps(action, ensure_ascii=False)})

                # 保留最近 20 条对话历史
                if len(history) > 20:
                    history = history[-20:]

            except Exception as e:
                await log(f"模型调用失败: {e}", "error")
                break

            action_name = action.get("action", "wait")
            reason = action.get("reason", "")
            await log(f"决策: [{action_name}] {reason}")

            if action_cb:
                await action_cb(action)

            # 重复动作防护
            if action_name == last_action:
                consecutive_same += 1
                if consecutive_same >= 3:
                    await log("检测到重复动作，尝试滑动寻找新内容...", "warn")
                    await asyncio.to_thread(self.adb.scroll_down, self.screen_w, self.screen_h)
                    consecutive_same = 0
                    await asyncio.sleep(ACTION_DELAY_SEC)
                    continue
            else:
                consecutive_same = 0
                last_action = action_name

            # ── 3. 任务完成 ──
            if action_name == "done":
                summary = action.get("summary", "任务完成")
                await log(f"✅ {summary}", "success")
                if tts_cb:
                    try:
                        audio_bytes = await asyncio.to_thread(speak, summary)
                        await tts_cb(audio_bytes)
                    except Exception as e:
                        await log(f"TTS 播报失败: {e}", "warn")
                break

            # ── 4. 执行动作 ──
            await self._execute(action, log)

            action_history.append({
                "step": step,
                "action": action_name,
                "reason": reason[:80],
            })

            # State compression：每 STATE_COMPRESS_INTERVAL 步压缩一次历史
            if step % STATE_COMPRESS_INTERVAL == 0 and len(action_history) > STATE_COMPRESS_KEEP:
                action_history = _compress_action_history(action_history)
                await log(f"历史已压缩，保留最近 {STATE_COMPRESS_KEEP} 步详情", "info")

            await asyncio.sleep(ACTION_DELAY_SEC)

        self.running = False
        await log("Agent 执行结束")

    async def _execute(self, action: dict, log):
        name = action.get("action", "")

        if name == "tap":
            # 模型坐标基于压缩后图片（display_w × display_h），还原到真实分辨率
            x_disp = int(action.get("x", 0))
            y_disp = int(action.get("y", 0))
            x = int(x_disp / SCREENSHOT_SCALE)
            y = int(y_disp / SCREENSHOT_SCALE)
            # 钳制到真实屏幕边界
            x = max(0, min(x, self.screen_w))
            y = max(0, min(y, self.screen_h))
            await log(f"点击 ({x_disp},{y_disp}) → 还原为真实坐标 ({x},{y})")
            await asyncio.to_thread(self.adb.tap, x, y)

        elif name == "type":
            text = action.get("text", "")
            await log(f"输入: {text}")
            await asyncio.to_thread(self.adb.type_text, text)

        elif name == "swipe_up":
            await log("向上滑动（查看下方内容）")
            await asyncio.to_thread(self.adb.scroll_down, self.screen_w, self.screen_h)

        elif name == "swipe_down":
            await log("向下滑动（查看上方内容）")
            await asyncio.to_thread(self.adb.scroll_up, self.screen_w, self.screen_h)

        elif name == "swipe_left":
            await log("向左滑动")
            await asyncio.to_thread(self.adb.scroll_left, self.screen_w, self.screen_h)

        elif name == "swipe_right":
            await log("向右滑动")
            await asyncio.to_thread(self.adb.scroll_right, self.screen_w, self.screen_h)

        elif name == "back":
            await log("返回")
            await asyncio.to_thread(self.adb.back)

        elif name == "home":
            await log("回到桌面")
            await asyncio.to_thread(self.adb.home)

        elif name == "enter":
            await log("按确认键")
            await asyncio.to_thread(self.adb.enter)

        elif name == "wait":
            await log("等待页面加载...")
            await asyncio.sleep(2.0)

    def stop(self):
        self.running = False
