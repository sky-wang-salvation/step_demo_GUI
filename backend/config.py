import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

STEP_API_KEY = os.getenv("STEP_API_KEY", "")
STEP_BASE_URL = os.getenv("STEP_BASE_URL", "https://api.stepfun.com/v1")

# Models
MODEL_AGENT  = "step-3.7-flash"      # screenshot → action JSON (vision + planning + grounding)
MODEL_ASR    = "stepaudio-2.5-asr"   # speech → text
MODEL_TTS    = "stepaudio-2.5-tts"   # text → speech

# Server
WS_PORT = int(os.getenv("WS_PORT", "8766"))

# Agent loop
MAX_STEPS        = 25
ACTION_DELAY_SEC = 3.0   # 等待操作生效（App 跳转/页面加载）

# API call parameters — follow GELab-Zero recommendations
AGENT_TEMPERATURE  = 1      # 必须为 1，保持采样多样性
AGENT_TOP_P        = 0.95
AGENT_FREQ_PENALTY = 0.05
AGENT_MAX_TOKENS   = 32768  # 给思维链 + JSON 输出留足空间

# Screenshot compression: scale down before sending to model to reduce tokens
SCREENSHOT_SCALE = 0.5      # 1080×2400 → 540×1200

# State compression: summarize old history to keep context manageable
STATE_COMPRESS_INTERVAL = 10   # compress every N steps
STATE_COMPRESS_KEEP     = 10   # keep last N steps in full detail

TTS_VOICE = "灿灿"              # Step TTS voice name
