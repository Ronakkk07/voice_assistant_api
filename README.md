# Public Voice Assistant API

A small, public, **no-auth** API that:

1. Accepts an audio file.
2. Transcribes speech on your backend using Whisper.
3. Sends transcript to Gemini.
4. Returns Gemini's response.
5. Requires wake word **Luna** before forwarding to Gemini.

> Each request must include the caller's own Gemini key (header or form field). The server does not store persistent Gemini keys.
> Wake word defaults to `luna` and can be changed with `WAKE_WORD` env var.

## API contract

### `POST /v1/voice/respond`

- **Auth:** none
- **Gemini key (required per request, any one of these):**
  - Header: `X-Gemini-Api-Key: <YOUR_GEMINI_API_KEY>`
  - Multipart field: `gemini_api_key=<YOUR_GEMINI_API_KEY>`
- **Body (multipart/form-data):**
  - `audio_file` (required): audio file (`.wav`, `.mp3`, `.m4a`, etc.)

#### Response

```json
{
  "activated": true,
  "transcript": "book a cab for tomorrow",
  "command": "book a cab for tomorrow",
  "response": "Sure — where should I arrange the pickup?"
}
```

If wake word is missing:

```json
{
  "activated": false,
  "transcript": "what is the weather",
  "command": null,
  "response": "Wake word 'luna' not detected. Say 'luna' first."
}
```

## Run locally

```bash
cd public_voice_assistant_api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Optional:
export WAKE_WORD=luna
uvicorn main:app --reload --port 8001
```

## cURL example

```bash
curl -X POST "http://127.0.0.1:8001/v1/voice/respond" \
  -H "X-Gemini-Api-Key: YOUR_GEMINI_API_KEY" \
  -F "audio_file=@./sample.wav"
```

## Notes

- This repository intentionally has no login/auth layer.
- Caller Gemini key is accepted per request only.
- Use HTTPS so request keys are encrypted in transit.
- Do **not** store caller Gemini keys in database/logs.
- You can place this folder in a separate public repository as-is.
