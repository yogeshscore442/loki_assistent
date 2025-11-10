# loki_assistent

Loki Assistant is a local, voice-driven personal assistant written in Python.
It listens for spoken commands, performs common tasks (open apps, search web, take screenshots, simple math, timers, notes, conversions, etc.), and speaks every response out loud using the local TTS engine. The project includes a lightweight optional overlay UI and a large set of recognized phrases (150+ generated operations) so the assistant understands many natural phrasings.

🚀 Highlights
Voice-first: every assistant output is spoken (pyttsx3 with PowerShell fallback on Windows).

150+ programmatically generated command phrases (verbs × targets) to cover many natural variants.

Useful built-in operations: open/close apps, browser search, screenshots, timer/reminder, quick notes, conversions, simple math, system info.

Optional circular overlay showing listening / last messages (requires tkinter + Pillow).

Robust TTS handling with a synchronized engine lock to avoid missed speech.

Safe, offline-first design — no required cloud dependencies (speech recognition uses Google Web Speech by default; can be swapped).

✅ Features
Voice input (speech recognition) and voice output (TTS) for all responses.

Programmatic phrase generation producing 150+ distinct phrase variants.

Handlers for:

Opening/closing apps (Chrome, VSCode, etc.)

Taking single screenshots (suppresses listening while counting down)

Web search (opens browser)

Timers & reminders

Quick notes (local notes file)

Simple two-number arithmetic

Unit conversions (meters↔km, °C↔°F)

System info, shutdown/restart (with prompts)

Optional overlay GUI with circular avatar and listening indicator.

Lots of comments and clear code structure — easy to extend.
