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

Handlers for
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



.

🧰 Requirements
Python 3.8+

Recommended packages:

bash
Copy code
pip install pyttsx3 SpeechRecognition sounddevice numpy pyautogui Pillow colorama psutil
Platform notes:

Windows: pyttsx3 typically uses sapi5; PowerShell fallback is available by default.

Linux: pyttsx3 may use espeak; ensure espeak installed.

macOS: pyttsx3 may use nsss.

⚙️ Installation
Clone this repo:

bash
Copy code
git clone <your-repo-url>
cd loki-assistant
Install requirements:

bash
Copy code
pip install -r requirements.txt
Or install individually if you prefer.

(Optional) If you want the overlay and circular avatar, ensure tkinter and Pillow are installed and a GIF path is configured.

▶️ Usage
Run the assistant:

bash
Copy code
python Loki_assistant2_voice_for_all.py
On start it will announce itself (voice) and then listen. Speak commands like:

"Open Chrome" → opens browser and says "Opening Google Chrome."

"What time is it?" → speaks current time.

"Take a screenshot" → countdown and saves screenshot, then speaks confirmation.

"Calculate 12 divided by 4" → speaks the answer.

"Set a timer for 30 seconds" → sets timer and announces when finished.

You can also type or extend command handlers in the code.



