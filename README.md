🧠 Loki Assistant

Loki Assistant is a local, voice-driven personal assistant written in Python.
It listens for spoken commands, performs useful daily tasks (like opening apps, taking screenshots, searching the web, solving math problems, setting reminders, and more), and speaks every response out loud using your local Text-to-Speech (TTS) engine.

The project includes a lightweight optional overlay UI, and features 150+ natural command phrases — so Loki understands a wide range of user inputs.

🚀 Highlights

🎙️ Voice-first: All responses are spoken aloud (via pyttsx3, with PowerShell fallback on Windows).

🧩 150+ command phrases: Programmatically generated from verbs × targets for natural speech coverage.

⚙️ Offline-first: Works without internet (uses Google Web Speech by default but can be swapped).

💻 Cross-platform support: Works on Windows, Linux, and macOS.

🖼️ Optional overlay UI: Circular avatar and listening indicator using tkinter + Pillow.

🔒 Synchronized TTS engine lock to avoid missed or overlapping speech.

🧠 Simple, well-structured code with comments for easy extension and customization.

✅ Features
🎤 Voice Input & Output

Recognizes your speech and speaks all responses out loud.

Works completely offline once dependencies are installed.

🛠️ Built-in Command Handlers

Open/Close Apps (e.g., Chrome, VSCode, etc.)

Web Search (opens default browser)

Take Screenshots (with countdown and listening suppression)

Set Timers / Reminders (announces when finished)

Quick Notes (stores notes locally)

Simple Arithmetic (e.g., “calculate 12 divided by 4”)

Unit Conversions (e.g., meters ↔ kilometers, °C ↔ °F)

System Information (CPU usage, battery, etc.)

Shutdown / Restart (with confirmation prompts)

🖥️ Optional Overlay GUI

Displays a circular avatar indicating listening, speaking, and idle states.

Shows the last message and response dynamically.


# 🧠 Loki Assistant

Loki Assistant is a local, voice-driven personal assistant written in Python.
It listens for spoken commands, performs useful daily tasks, and speaks every response aloud.

---

## ⚙️ Installation

Clone the repository:
Install dependencies:
```bash
git clone <your-repo-url>
cd loki-assistant

bash

pip install -r requirements.txt

Run the assistant using:

bash
python Loki_assistant2.py

"If you get any errors in python Loki_assistant2.py , use this file. Additional functions have been added in , try it 🔥

bash
python Loki_assistant.py



