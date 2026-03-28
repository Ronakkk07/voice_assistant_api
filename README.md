# Public Voice Assistant API

A small, public, **no-auth** API that:
Endpoint to test: http://44.195.84.200/docs
1. Accepts an audio file / Speak through microphone.
2. Transcribes speech on your backend using Whisper.
3. Sends transcript to Gemini.
4. Returns Gemini's response.
5. Requires wake word **Luna** before forwarding to Gemini.
6. Can add this if you want gemini to talk back 
   ``` const utterance = new SpeechSynthesisUtterance(data.response);```
   ```speechSynthesis.speak(utterance); ```

> Each request must include the caller's own Gemini key (header or form field). The server does not store persistent Gemini keys.
> Wake word defaults to `luna` and can be changed through `WAKE_WORD` 

## API contract

### `POST /v1/voice/respond`

- **Auth:** none
- **Gemini key (required per request, any one of these):**
  - Header: `X-Gemini-Api-Key: <YOUR_GEMINI_API_KEY>`
  - Multipart field: `gemini_api_key=<YOUR_GEMINI_API_KEY>`
- **Body (multipart/form-data):**
  - `audio_file` (required): audio file (`.wav`, `.mp3`, `.m4a`, etc.)

### `POST /v1/voice/respond/raw`
Speak through microphone
- **Auth:** none
- **Gemini key:** `X-Gemini-Api-Key` header (required)
- **Body:** raw audio bytes (`audio/webm`, `audio/wav`, etc.)
- Good for browser microphone flows where you send a recorded blob directly.

#### Response

```json
{
  "activated": true,
  "transcript": "book a cab for tomorrow",
  "command": "luna book a cab for tomorrow",
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

Raw bytes mode:

```bash
curl -X POST "http://127.0.0.1:8001/v1/voice/respond/raw" \
  -H "X-Gemini-Api-Key: YOUR_GEMINI_API_KEY" \
  -H "Content-Type: audio/webm" \
  --data-binary "@./mic_recording.webm"
```

## Browser microphone example (no file picker)
Add this html file to implement the microphone feature and to store your gemini key here
```html
<button id="speak">Speak</button>
<script>
  const API = "http://127.0.0.1:8001/v1/voice/respond/raw";
  const GEMINI_KEY = "YOUR_GEMINI_API_KEY"; // use your own key

  document.getElementById("speak").onclick = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
    const chunks = [];

    recorder.ondataavailable = (e) => chunks.push(e.data);
    recorder.onstop = async () => {
      const blob = new Blob(chunks, { type: "audio/webm" });
      const res = await fetch(API, {
        method: "POST",
        headers: {
          "X-Gemini-Api-Key": GEMINI_KEY,
          "Content-Type": "audio/webm",
        },
        body: blob,
      });
      console.log(await res.json());
      stream.getTracks().forEach((t) => t.stop());
    };

    recorder.start();
    setTimeout(() => recorder.stop(), 4000); // record 4s
  };
</script>
```

## Notes

- This repository intentionally has no login/auth layer.
- Gemini key is accepted per request only.
- Use HTTPS so request keys are encrypted in transit.
- Do **not** store caller Gemini keys in database/logs.
- You can place this folder in a separate public repository as-is.
