"""
WebSocket API Server
前后端通信核心，管理 Agent 生命周期
"""

import asyncio
import base64
import json
import logging
import sys

import websockets

from config import WS_PORT
from step_agent import StepAgent
from adb_controller import ADBController
from audio_client import transcribe

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger("api_server")

# ── State ────────────────────────────────────────────────────────────────────

connected: set = set()
current_agent: StepAgent | None = None
agent_task: asyncio.Task | None = None

# ── Broadcast Helpers ─────────────────────────────────────────────────────────

async def broadcast(payload: dict):
    data = json.dumps(payload, ensure_ascii=False)
    if connected:
        await asyncio.gather(
            *(ws.send(data) for ws in connected.copy()),
            return_exceptions=True
        )

async def log_broadcast(msg: str, level: str = "info"):
    await broadcast({"type": "log", "level": level, "message": msg})

async def screenshot_broadcast(b64: str):
    await broadcast({"type": "screenshot", "data": b64})

async def action_broadcast(action: dict):
    await broadcast({"type": "action_event", "action": action})

async def tts_broadcast(audio_bytes: bytes):
    await broadcast({"type": "tts_audio", "data": base64.b64encode(audio_bytes).decode()})

# ── Handler ───────────────────────────────────────────────────────────────────

async def handler(ws):
    global current_agent, agent_task

    connected.add(ws)
    logger.info(f"Client connected ({len(connected)} total)")
    await ws.send(json.dumps({"type": "status", "status": "idle"}))

    audio_buf = bytearray()

    try:
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            t = msg.get("type", "")

            # ── ping ──
            if t == "ping":
                await ws.send(json.dumps({"type": "pong"}))

            # ── check ADB status ──
            elif t == "check_adb":
                devices = await asyncio.to_thread(ADBController.list_devices)
                await ws.send(json.dumps({
                    "type": "adb_status",
                    "connected": len(devices) > 0,
                    "devices": devices
                }))

            # ── start task ──
            elif t == "start_task":
                task = msg.get("task", "").strip()
                if not task:
                    await ws.send(json.dumps({"type": "error", "message": "任务内容不能为空"}))
                    continue

                if current_agent and current_agent.running:
                    await ws.send(json.dumps({"type": "error", "message": "已有任务正在运行"}))
                    continue

                await broadcast({"type": "status", "status": "running"})

                current_agent = StepAgent()

                async def run_agent_task():
                    try:
                        await current_agent.run(
                            task=task,
                            log_cb=log_broadcast,
                            screenshot_cb=screenshot_broadcast,
                            action_cb=action_broadcast,
                            tts_cb=tts_broadcast,
                        )
                    except Exception as e:
                        logger.exception("Agent crashed")
                        await log_broadcast(f"Agent 异常终止: {e}", "error")
                    finally:
                        await broadcast({"type": "status", "status": "idle"})

                agent_task = asyncio.create_task(run_agent_task())

            # ── stop task ──
            elif t == "stop_task":
                if current_agent:
                    current_agent.stop()
                if agent_task:
                    agent_task.cancel()
                await broadcast({"type": "status", "status": "idle"})
                await log_broadcast("任务已手动停止", "warn")

            # ── voice: audio chunks (streamed) ──
            elif t == "audio_chunk":
                chunk = base64.b64decode(msg.get("data", ""))
                audio_buf.extend(chunk)

            # ── voice: end of recording ──
            elif t == "audio_end":
                if audio_buf:
                    await log_broadcast("正在识别语音...", "info")
                    try:
                        text = await asyncio.to_thread(
                            transcribe, bytes(audio_buf), "audio.webm"
                        )
                        await broadcast({"type": "task_transcript", "text": text})
                        await log_broadcast(f"识别结果: {text}", "info")
                    except Exception as e:
                        await log_broadcast(f"语音识别失败: {e}", "error")
                    audio_buf.clear()

    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        logger.error(f"Handler error: {e}")
    finally:
        connected.discard(ws)
        logger.info(f"Client disconnected ({len(connected)} remaining)")


# ── Entry Point ───────────────────────────────────────────────────────────────

async def main():
    logger.info(f"Step Demo API Server — ws://localhost:{WS_PORT}")
    logger.info("Waiting for frontend connection...")
    async with websockets.serve(handler, "0.0.0.0", WS_PORT):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped.")
