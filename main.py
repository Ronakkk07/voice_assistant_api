import os
import tempfile
from pathlib import Path
from threading import Lock

from fastapi import FastAPI, File, HTTPException, UploadFile
from google.generativeai import GenerativeModel, configure
from pydantic import BaseModel
from faster_whisper import WhisperModel
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / "env" / ".env")


app = FastAPI(
    title="Public Voice Assistant API",
    version="1.0.0",
    description=(
        "Unauthenticated API that transcribes speech and gets a Gemini response. "
        "Clients must supply their own Gemini API key on every request."
    ),
)


class VoiceResponse(BaseModel):
    transcript: str
    response: str


class WhisperService:
    """Lazy singleton loader so model is initialized only once."""

    _model = None
    _lock = Lock()

    @classmethod
    def get_model(cls) -> WhisperModel:
        if cls._model is None:
            with cls._lock:
                if cls._model is None:
                    cls._model = WhisperModel("base", device="cpu", compute_type="int8")
        return cls._model

@app.get("/")
def root():
    return {"message": "Voice Assistant API is running"}

def transcribe_audio(upload: UploadFile) -> str:
    suffix = os.path.splitext(upload.filename or "audio.wav")[1] or ".wav"
    fd, tmp_path = tempfile.mkstemp(suffix=suffix)

    try:
        with os.fdopen(fd, "wb") as temp_file:
            temp_file.write(upload.file.read())

        model = WhisperService.get_model()
        segments, _ = model.transcribe(tmp_path)
        return " ".join(segment.text for segment in segments).strip()
    finally:
        upload.file.close()
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def generate_response(transcript: str, api_key: str) -> str:
    configure(api_key=api_key)
    model = GenerativeModel("models/gemini-2.5-flash")

    prompt = (
        "You are a helpful AI voice assistant. "
        "Reply naturally, clearly, and briefly to the following transcript:\n\n"
        f"{transcript}"
    )

    result = model.generate_content(prompt)
    if not result.text:
        raise HTTPException(status_code=502, detail="Gemini returned an empty response")
    return result.text.strip()


def resolve_api_key(
) -> str:
    """
    Resolve Gemini key from server-side configuration only:
    1) File path from GEMINI_API_KEY_FILE env var
    2) GEMINI_API_KEY env var (loaded from env/.env when present)
    """
    key_file_path = os.getenv("GEMINI_API_KEY_FILE")
    if key_file_path:
        file_path = Path(key_file_path)
        if file_path.exists():
            return file_path.read_text(encoding="utf-8").strip()

    env_key = os.getenv("GEMINI_API_KEY")
    if env_key:
        return env_key.strip()

    raise HTTPException(
        status_code=400,
        detail=(
            "Missing Gemini API key. Configure GEMINI_API_KEY_FILE or GEMINI_API_KEY "
            "in env/.env."
        ),
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/v1/voice/respond", response_model=VoiceResponse)
def voice_respond(
    audio_file: UploadFile = File(...),
) -> VoiceResponse:
    resolved_key = resolve_api_key()

    transcript = transcribe_audio(audio_file)
    if not transcript:
        raise HTTPException(status_code=400, detail="Unable to transcribe audio")

    response_text = generate_response(transcript, resolved_key)
    return VoiceResponse(transcript=transcript, response=response_text)
