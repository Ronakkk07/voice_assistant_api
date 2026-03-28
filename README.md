# Public Voice Assistant API

A small, public, **no-auth** API that:

1. Accepts an audio file.
2. Transcribes speech on your backend using Whisper.
3. Sends transcript to Gemini.
4. Returns Gemini's response.

> Configure Gemini API key on the server in `env/.env` (or via `GEMINI_API_KEY_FILE`). The API no longer accepts key in headers/forms.

## API contract

### `POST /v1/voice/respond`

- **Auth:** none
- **Gemini key (server-side only, any one of these):**
  - `env/.env` with `GEMINI_API_KEY=<YOUR_GEMINI_API_KEY>`
  - `env/.env` with `GEMINI_API_KEY_FILE=/path/to/gemini_key.txt`
- **Body (multipart/form-data):**
  - `audio_file` (required): audio file (`.wav`, `.mp3`, `.m4a`, etc.)

#### Response

```json
{
  "transcript": "book a cab for tomorrow",
  "response": "Sure — where should I arrange the pickup?"
}
```

## Run locally

```bash
cd public_voice_assistant_api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp env/.env.example env/.env
# edit env/.env and place your key
uvicorn main:app --reload --port 8001
```

### Keep key in file (recommended)

```bash
echo "YOUR_GEMINI_API_KEY" > /secure/path/gemini_key.txt
cp env/.env.example env/.env
# edit env/.env and set:
# GEMINI_API_KEY_FILE=/secure/path/gemini_key.txt
uvicorn main:app --reload --port 8001
```

## cURL example

```bash
curl -X POST "http://127.0.0.1:8001/v1/voice/respond" \
  -F "audio_file=@./sample.wav"
```

## Notes

- This repository intentionally has no login/auth layer.
- Gemini key is loaded only from server env (`env/.env`) or key file path.
- Do **not** store caller Gemini keys in database/logs.
- You can place this folder in a separate public repository as-is.
