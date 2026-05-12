"""
vision_client.py — 辅助视觉工具（可选使用）
主 Agent Loop 已将视觉理解+规划+Grounding 合并为 step_agent.py 内的单次调用。
此文件保留独立的视觉工具函数，供调试或扩展使用。
"""

import json
import re
import logging
from openai import OpenAI
from config import STEP_API_KEY, STEP_BASE_URL, MODEL_AGENT

logger = logging.getLogger(__name__)
_client = OpenAI(api_key=STEP_API_KEY, base_url=STEP_BASE_URL)


def _image_message(b64: str) -> dict:
    return {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}


def ground_element(screenshot_b64: str, target_description: str,
                   screen_width: int, screen_height: int) -> dict:
    """
    Locate a UI element and return pixel coordinates.
    Uses step-3.7-flash (multimodal) for direct visual grounding.
    Returns {"x": int, "y": int, "found": bool}
    """
    prompt = (
        f"The image is an Android phone screenshot ({screen_width}x{screen_height} pixels).\n"
        f"Find the CENTER pixel coordinates of: {target_description}\n\n"
        "Reply ONLY with JSON. No explanation.\n"
        'If found:    {"x": <int>, "y": <int>, "found": true}\n'
        'If not found: {"x": 0, "y": 0, "found": false}'
    )
    try:
        response = _client.chat.completions.create(
            model=MODEL_AGENT,
            messages=[{"role": "user", "content": [
                _image_message(screenshot_b64),
                {"type": "text", "text": prompt}
            ]}],
            max_tokens=80
        )
        text = response.choices[0].message.content.strip()
        match = re.search(r'\{[^}]+\}', text)
        if match:
            result = json.loads(match.group())
            result["x"] = max(0, min(int(result.get("x", 0)), screen_width))
            result["y"] = max(0, min(int(result.get("y", 0)), screen_height))
            return result
    except Exception as e:
        logger.error(f"ground_element error: {e}")
    return {"x": 0, "y": 0, "found": False}


def describe_screen(screenshot_b64: str) -> str:
    """Return a concise Chinese description of the current screen."""
    prompt = (
        "请用中文简洁描述当前手机屏幕的内容。"
        "包括：当前处于哪个App/页面，可见的主要按钮、文字、状态信息。"
        "重点描述可交互的UI元素。不超过150字。"
    )
    try:
        response = _client.chat.completions.create(
            model=MODEL_AGENT,
            messages=[{"role": "user", "content": [
                _image_message(screenshot_b64),
                {"type": "text", "text": prompt}
            ]}],
            max_tokens=300
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"describe_screen error: {e}")
        return "屏幕内容解析失败"


def answer_about_screen(screenshot_b64: str, question: str) -> str:
    """Ask a specific question about the current screen."""
    try:
        response = _client.chat.completions.create(
            model=MODEL_AGENT,
            messages=[{"role": "user", "content": [
                _image_message(screenshot_b64),
                {"type": "text", "text": question}
            ]}],
            max_tokens=400
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"answer_about_screen error: {e}")
        return "无法获取屏幕信息"
