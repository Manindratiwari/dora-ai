# Dora (standalone version with real backend)

Why this exists: inside the claude.ai artifact view the browser blocks the microphone (NotAllowedError).
Running Dora as its own page fixes that, because the page is then served from `http://localhost`, where Chrome and Edge allow mic access.

## Run locally
1. `cd dora/backend`
2. `python -m venv .venv` then activate it (Windows: `.venv\Scripts\activate`)
3. `pip install -r requirements.txt`
4. Copy `../.env.example` to `backend/.env` and set `LLM_API_KEY` (server side only, never in frontend code)
5. `uvicorn main:app --port 8010 --reload`
6. Open http://localhost:8010 in **Chrome or Edge** and allow the microphone when asked.

Check http://localhost:8010/api/health: `key_set` should be `true`.

## Notes
- Voice uses the browser Web Speech API. Chrome sends audio to Google for recognition, so it needs internet.
- The wake word works only while the tab is open (browsers block background listening).
- Backend has input validation and a simple per-IP rate limit. It has no auth, database, reminders, notes or web search yet.
- For production, host the backend on any HTTPS host (Render, Railway, Fly.io) and keep `.env` values as host environment variables.

## Use it as a mobile app (PWA, Android)
Dora is an installable web app. Once opened over HTTPS in Chrome on Android, it can be added to the home screen and runs fullscreen like a native app.

1. **Get an HTTPS URL** (a phone cannot use `localhost`, and plain `http://192.168.x.x` blocks the mic and installing):
   - Quick test: with the backend running, run `cloudflared tunnel --url http://localhost:8010` (or `ngrok http 8010`) and open the https URL it prints.
   - Permanent: deploy this repo to Render (`render.yaml` included). Set `LLM_API_KEY` in the Render dashboard. Any host that runs `uvicorn --app-dir backend main:app --host 0.0.0.0 --port $PORT` works (Railway, Fly.io).
2. Open the URL in **Chrome on Android**, tap **Install app** (top right) or the menu, then **Add to Home screen**.
3. Open Dora from the home screen and allow the microphone.

## Limits
- Chrome on Android supports voice recognition; iPhone Safari support is limited.
- No push notifications, so no real reminders yet. Wake word works only while the app is open on screen.
- A native APK (for example with Capacitor) is possible later, but Android WebView lacks the browser speech API, so it would need a native speech-recognition plugin.
- Status: all code here was written but not run or tested (no network or Android device available).
