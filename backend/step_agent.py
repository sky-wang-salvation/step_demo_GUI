"""
Step Agent — Core Agent Loop
step-3.7-flash (多模态) 直接看截图，一次调用完成：
  看图理解屏幕内容 + 规划下一步动作 + GUI Grounding (坐标定位)
架构：截图 → step-3.7-flash(图+文) → 动作JSON(含坐标) → ADB执行 → 循环
"""

import asyncio
import json
import logging
from typing import Callable, Awaitable, Optional

from openai import OpenAI
from config import STEP_API_KEY, STEP_BASE_URL, MODEL_AGENT, MAX_STEPS, ACTION_DELAY_SEC
from adb_controller import ADBController
from audio_client import speak

logger = logging.getLogger(__name__)
_client = OpenAI(api_key=STEP_API_KEY, base_url=STEP_BASE_URL)

# ── System Prompt ─────────────────────────────────────────────────────────────
# step-3.7-flash 是多模态模型，可直接看图 + 规划 + 返回坐标，无需分步调用

SYSTEM_PROMPT = """\
You are a smartphone GUI agent with direct vision. You see the Android phone screen (vivo S19, Android 15) as an image each turn.

Your job: look at the screenshot, understand the current state, and decide the single best next action to complete the user's task.

=== Screen Info ===
Resolution: {screen_w}x{screen_h} pixels. Coordinates start at top-left (0,0).

=== Available Actions ===
tap        — Click a UI element. REQUIRED: provide "x" and "y" pixel coordinates of its center.
type       — Input text into the focused field. REQUIRED: "text" field.
swipe_up   — Scroll down (reveal content below). 
swipe_down — Scroll up (reveal content above).
swipe_left — Swipe left.
swipe_right— Swipe right.
back       — Press Android back button.
home       — Press Android home button.
enter      — Press Enter/confirm key.
wait       — Wait 2s for page/animation to finish.
done       — Task complete. REQUIRED: "summary" in Chinese describing the result.

=== Output Format (STRICT JSON, no extra text) ===
{{
  "action": "<action_name>",
  "x": <int>,          // REQUIRED for tap — pixel x of element center
  "y": <int>,          // REQUIRED for tap — pixel y of element center
  "text": "<string>",  // REQUIRED for type
  "reason": "<one sentence>",
  "summary": "<Chinese result summary>"  // REQUIRED for done
}}

=== Rules ===
1. Output ONLY valid JSON — no markdown fences, no explanation outside JSON.
2. For "tap": carefully identify the element in the image and output its EXACT center pixel coordinates.
3. If you've done the same action 3 times in a row with no progress, try a different approach or declare done with failure reason.
4. When task requires reading info from screen (e.g. order status, balance), extract and include it in the summary.
5. Keep "reason" to one concise sentence.
"""

# ── Agent ─────────────────────────────────────────────────────────────────────

class StepAgent:
    def __init__(self):
        self.adb = ADBController()
        self.running = False
        self.screen_w = 1080
        self.screen_h = 2400

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

        # Screen size
        try:
            self.screen_w, self.screen_h = await asyncio.to_thread(self.adb.get_screen_size)
            await log(f"屏幕分辨率: {self.screen_w}×{self.screen_h}")
        except Exception as e:
            await log(f"获取屏幕尺寸失败，使用默认值 1080×2400: {e}", "warn")

        # Build system prompt with screen dimensions
        system_prompt = SYSTEM_PROMPT.format(
            screen_w=self.screen_w,
            screen_h=self.screen_h
        )

        # Conversation history (text-only for assistant turns to save tokens)
        history: list[dict] = []
        action_history: list[dict] = []
        consecutive_same = 0
        last_action = None

        for step in range(1, MAX_STEPS + 1):
            if not self.running:
                await log("任务被用户停止", "warn")
                break

            await log(f"── Step {step}/{MAX_STEPS} ──────────────────")

            # ── 1. Screenshot ──
            try:
                await log("截取屏幕...")
                screenshot_b64 = await asyncio.to_thread(self.adb.screenshot_b64)
                if screenshot_cb:
                    await screenshot_cb(screenshot_b64)
            except Exception as e:
                await log(f"截图失败: {e}", "error")
                break

            # ── 2. Single multimodal call: vision + planning + grounding ──
            # step-3.7-flash 直接看图，返回包含坐标的动作 JSON
            await log("step-3.7-flash 分析屏幕并规划动作...")

            user_content = [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}
                },
                {
                    "type": "text",
                    "text": (
                        f"用户任务: {task}\n"
                        f"已执行步骤({len(action_history)}步): "
                        f"{json.dumps(action_history, ensure_ascii=False) if action_history else '无'}\n\n"
                        "请看截图，决定下一步动作。"
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
                        response_format={"type": "json_object"},
                        max_tokens=300
                    )
                )
                action_text = resp.choices[0].message.content.strip()
                action = json.loads(action_text)

                # Append text summary to history (not the image, to control token usage)
                history.append({
                    "role": "user",
                    "content": f"[Step {step}] 截图已分析，任务: {task}"
                })
                history.append({"role": "assistant", "content": action_text})

                # Keep history manageable (last 10 turns)
                if len(history) > 20:
                    history = history[-20:]

            except Exception as e:
                await log(f"模型调用失败: {e}", "error")
                break

            action_name = action.get("action", "wait")
            reason = action.get("reason", "")
            await log(f"决策: [{action_name}] {reason}")

            # Notify frontend
            if action_cb:
                await action_cb(action)

            # Infinite loop guard
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

            # ── 3. Done? ──
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

            # ── 4. Execute ──
            await self._execute(action, log)

            action_history.append({
                "step": step,
                "action": action_name,
                "reason": reason[:80]
            })

            await asyncio.sleep(ACTION_DELAY_SEC)

        self.running = False
        await log("Agent 执行结束")

    async def _execute(self, action: dict, log):
        name = action.get("action", "")

        if name == "tap":
            x = int(action.get("x", 0))
            y = int(action.get("y", 0))
            # Clamp to screen bounds
            x = max(0, min(x, self.screen_w))
            y = max(0, min(y, self.screen_h))
            await log(f"点击 ({x}, {y})")
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
