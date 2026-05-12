import io
import logging
from openai import OpenAI
from config import STEP_API_KEY, STEP_BASE_URL, MODEL_ASR, MODEL_TTS, TTS_VOICE

logger = logging.getLogger(__name__)
_client = OpenAI(api_key=STEP_API_KEY, base_url=STEP_BASE_URL)


def transcribe(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    """
    Convert speech audio to text using stepaudio-2.5-asr.
    Accepts common formats: webm, wav, mp3, m4a, ogg.
    Returns the transcribed text string.
    """
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = filename

    try:
        response = _client.audio.transcriptions.create(
            model=MODEL_ASR,
            file=audio_file,
            response_format="text"
        )
        text = response.strip() if isinstance(response, str) else response
        logger.info(f"ASR result: {text}")
        return str(text)
    except Exception as e:
        logger.error(f"transcribe error: {e}")
        raise


def speak(text: str, voice: str = TTS_VOICE) -> bytes:
    """
    Convert text to speech using stepaudio-2.5-tts.
    Returns mp3 audio bytes.
    """
    try:
        response = _client.audio.speech.create(
            model=MODEL_TTS,
            input=text,
            voice=voice,
            response_format="mp3"
        )
        return response.content
    except Exception as e:
        logger.error(f"speak error: {e}")
        raise
