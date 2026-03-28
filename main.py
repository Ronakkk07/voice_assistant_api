import os
import tempfile
from threading import Lock

from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from google.generativeai import GenerativeModel, configure
from pydantic import BaseModel
from faster_whisper import WhisperModel


app = FastAPI(
    title="Public Voice Assistant API",
    version="1.0.0",
    description=(
        "Unauthenticated API that transcribes speech and gets a Gemini response. "
        "Clients must supply their own Gemini API key on every request."
    ),
)

WAKE_WORD = os.getenv("WAKE_WORD", "luna")


class VoiceResponse(BaseModel):
    activated: bool
    transcript: str
    command: str | None = None
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


def transcribe_audio_bytes(audio_bytes: bytes, suffix: str = ".wav") -> str:
    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as temp_file:
            temp_file.write(audio_bytes)

        model = WhisperService.get_model()
        segments, _ = model.transcribe(tmp_path)
        return " ".join(segment.text for segment in segments).strip()
    finally:
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


def extract_command_from_wake_word(transcript: str) -> tuple[bool, str]:
    """
    Require wake word before routing to Gemini.
    Returns:
      (True, cleaned_command) if wake word is found
      (False, original_transcript) if not found
    """
    lowered = transcript.lower()
    wake_word_lower = WAKE_WORD.lower()

    if wake_word_lower not in lowered:
        return False, transcript

    idx = lowered.find(wake_word_lower)
    cleaned = transcript[idx + len(WAKE_WORD) :].strip(" ,:.-")
    if not cleaned:
        cleaned = "Hello"
    return True, cleaned


def resolve_api_key(
    header_api_key: str | None,
    body_api_key: str | None,
) -> str:
    """
    Resolve Gemini key from request only:
    1) X-Gemini-Api-Key header
    2) gemini_api_key form field
    """
    if header_api_key:
        return header_api_key.strip()

    if body_api_key:
        return body_api_key.strip()

    raise HTTPException(
        status_code=400,
        detail=(
            "Missing Gemini API key. Provide X-Gemini-Api-Key header or "
            "gemini_api_key form field."
        ),
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/v1/voice/respond", response_model=VoiceResponse)
def voice_respond(
    audio_file: UploadFile = File(...),
    gemini_api_key: str | None = Form(default=None),
    x_gemini_api_key: str | None = Header(default=None),
) -> VoiceResponse:
    resolved_key = resolve_api_key(
        header_api_key=x_gemini_api_key,
        body_api_key=gemini_api_key,
    )

    transcript = transcribe_audio(audio_file)
    if not transcript:
        raise HTTPException(status_code=400, detail="Unable to transcribe audio")

    activated, command = extract_command_from_wake_word(transcript)
    if not activated:
        return VoiceResponse(
            activated=False,
            transcript=transcript,
            command=None,
            response=f"Wake word '{WAKE_WORD}' not detected. Say '{WAKE_WORD}' first.",
        )

    response_text = generate_response(command, resolved_key)
    return VoiceResponse(
        activated=True,
        transcript=transcript,
        command=command,
        response=response_text,
    )


@app.post("/v1/voice/respond/raw", response_model=VoiceResponse)
async def voice_respond_raw(
    request: Request,
    x_gemini_api_key: str | None = Header(default=None),
) -> VoiceResponse:
    resolved_key = resolve_api_key(
        header_api_key=x_gemini_api_key,
        body_api_key=None,
    )

    audio_bytes = await request.body()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty request body")

    content_type = (request.headers.get("content-type") or "").lower()
    suffix = ".webm" if "webm" in content_type else ".wav"

    transcript = transcribe_audio_bytes(audio_bytes, suffix=suffix)
    if not transcript:
        raise HTTPException(status_code=400, detail="Unable to transcribe audio")

    activated, command = extract_command_from_wake_word(transcript)
    if not activated:
        return VoiceResponse(
            activated=False,
            transcript=transcript,
            command=None,
            response=f"Wake word '{WAKE_WORD}' not detected. Say '{WAKE_WORD}' first.",
        )

    response_text = generate_response(command, resolved_key)
    return VoiceResponse(
        activated=True,
        transcript=transcript,
        command=command,
        response=response_text,
    )
