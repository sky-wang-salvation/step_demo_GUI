import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

STEP_API_KEY = os.getenv("STEP_API_KEY", "")
STEP_BASE_URL = os.getenv("STEP_BASE_URL", "https://api.stepfun.com/v1")

# Models
# step-3.7-flash is a multimodal model: handles vision understanding,
# GUI grounding (coordinate prediction) and task planning in ONE call.
MODEL_AGENT  = "step-3.7-flash"   # screenshot → action JSON (vision + planning + grounding)
MODEL_ASR    = "stepaudio-2.5-asr"   # speech → text
MODEL_TTS    = "stepaudio-2.5-tts"   # text → speech

# Server
WS_PORT = int(os.getenv("WS_PORT", "8766"))

# Agent
MAX_STEPS = 25
ACTION_DELAY_SEC = 1.5   # pause between actions (seconds)
TTS_VOICE = "灿灿"        # change to any supported Step TTS voice
