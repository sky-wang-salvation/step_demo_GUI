import subprocess
import base64
import io
import logging
from typing import Optional

from PIL import Image

logger = logging.getLogger(__name__)


class ADBController:
    def __init__(self, device_id: Optional[str] = None):
        self.device_id = device_id
        self._base = ["adb"]
        if device_id:
            self._base += ["-s", device_id]

    def _run(self, *args, timeout: int = 10, binary: bool = False):
        cmd = self._base + list(args)
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=timeout
            )
            return result
        except subprocess.TimeoutExpired:
            logger.error(f"ADB command timed out: {' '.join(cmd)}")
            raise
        except FileNotFoundError:
            raise RuntimeError("ADB not found. Run: brew install android-platform-tools")

    # ── Connection ─────────────────────────────────────────────────────────────

    @staticmethod
    def list_devices() -> list[str]:
        try:
            result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)
            lines = result.stdout.strip().split("\n")[1:]
            return [l.split("\t")[0] for l in lines if l.strip() and "device" in l]
        except Exception:
            return []

    def is_connected(self) -> bool:
        return len(self.list_devices()) > 0

    def get_screen_size(self) -> tuple[int, int]:
        result = self._run("shell", "wm", "size")
        output = result.stdout.decode().strip()
        # "Physical size: 1080x2400"  or  "Override size: ..."
        for line in output.split("\n"):
            if "size:" in line.lower():
                size_part = line.split(":")[-1].strip()
                w, h = size_part.split("x")
                return int(w), int(h)
        return 1080, 2400  # fallback for vivo S19

    # ── Screenshot ──────────────────────────────────────────────────────────────

    def screenshot(self) -> bytes:
        result = self._run("exec-out", "screencap", "-p", timeout=15)
        return result.stdout

    def screenshot_b64(self, scale: float = 1.0) -> str:
        """截图并可选压缩。scale=0.5 将 1080×2400 压缩为 540×1200，减少 token 消耗。"""
        raw = self.screenshot()
        if scale < 1.0:
            img = Image.open(io.BytesIO(raw))
            new_w = int(img.width * scale)
            new_h = int(img.height * scale)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            if img.mode != "RGB":
                img = img.convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            raw = buf.getvalue()
        return base64.b64encode(raw).decode()

    # ── Input ────────────────────────────────────────────────────────────────────

    def tap(self, x: int, y: int):
        self._run("shell", "input", "tap", str(x), str(y))
        logger.debug(f"tap({x}, {y})")

    def long_press(self, x: int, y: int, ms: int = 1000):
        self._run("shell", "input", "swipe", str(x), str(y), str(x), str(y), str(ms))

    def swipe(self, x1: int, y1: int, x2: int, y2: int, ms: int = 400):
        self._run("shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(ms))

    def keyevent(self, code: int):
        self._run("shell", "input", "keyevent", str(code))

    def back(self):
        self.keyevent(4)

    def home(self):
        self.keyevent(3)

    def recent_apps(self):
        self.keyevent(187)

    def enter(self):
        self.keyevent(66)

    # ── Text Input ───────────────────────────────────────────────────────────────
    # vivo + Android 15: ADB Keyboard handles Chinese

    def switch_to_adb_keyboard(self):
        self._run("shell", "ime", "set", "com.android.adbkeyboard/.AdbIME")

    def type_text_adb_keyboard(self, text: str):
        """Input text via ADB Keyboard broadcast (supports Chinese)."""
        self.switch_to_adb_keyboard()
        self._run("shell", "am", "broadcast", "-a", "ADB_INPUT_TEXT", "--es", "msg", text)

    def type_text_ascii(self, text: str):
        """Input ASCII text directly (no Chinese support)."""
        escaped = text.replace("\\", "\\\\").replace(" ", "%s").replace("'", "\\'")
        self._run("shell", "input", "text", escaped)

    def type_text(self, text: str):
        """Auto-detect Chinese and use appropriate input method."""
        if any('\u4e00' <= c <= '\u9fff' for c in text):
            self.type_text_adb_keyboard(text)
        else:
            self.type_text_ascii(text)

    def clear_text(self, chars: int = 50):
        """Clear input field by selecting all and deleting."""
        self._run("shell", "input", "keyevent", "--longpress", "112")  # Ctrl+A equivalent
        self.keyevent(67)  # KEYCODE_DEL

    # ── App Launch ───────────────────────────────────────────────────────────────

    def launch_app(self, package_name: str):
        self._run("shell", "monkey", "-p", package_name,
                  "-c", "android.intent.category.LAUNCHER", "1")

    def force_stop_app(self, package_name: str):
        self._run("shell", "am", "force-stop", package_name)

    # ── Convenience Scrolls ──────────────────────────────────────────────────────

    def scroll_down(self, screen_w: int, screen_h: int):
        cx = screen_w // 2
        self.swipe(cx, int(screen_h * 0.70), cx, int(screen_h * 0.30))

    def scroll_up(self, screen_w: int, screen_h: int):
        cx = screen_w // 2
        self.swipe(cx, int(screen_h * 0.30), cx, int(screen_h * 0.70))

    def scroll_left(self, screen_w: int, screen_h: int):
        cy = screen_h // 2
        self.swipe(int(screen_w * 0.80), cy, int(screen_w * 0.20), cy)

    def scroll_right(self, screen_w: int, screen_h: int):
        cy = screen_h // 2
        self.swipe(int(screen_w * 0.20), cy, int(screen_w * 0.80), cy)
