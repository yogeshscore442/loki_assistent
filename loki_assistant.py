# -*- coding: utf-8 -*-
"""
Loki Assistant — Speak-for-all fix
Save as: Loki_assistant2_voice_for_all.py
Run: python Loki_assistant2_voice_for_all.py

This version forces every assistant output to be spoken synchronously via speak_sync(),
and also prints text to console. It still preserves fallback to PowerShell on Windows.
"""

import os
import sys
import threading
import time
import queue
import subprocess
import re
import datetime
import shutil
import platform

# optional GUI libs
try:
    import tkinter as tk
    from tkinter import ttk
except Exception:
    tk = None

# optional PIL for GUI
try:
    from PIL import Image, ImageTk, ImageOps, ImageDraw
except Exception:
    Image = None

# core voice & audio libs
try:
    import speech_recognition as sr
except Exception:
    raise RuntimeError("Please install SpeechRecognition: pip install SpeechRecognition")

try:
    import pyttsx3
except Exception:
    pyttsx3 = None  # fallback will be PowerShell on Windows

# other helpful libs
try:
    import webbrowser
    import pyautogui
    import sounddevice as sd
    import numpy as np
    import wave
    from colorama import Fore, Style, init
    import psutil
except Exception:
    # proceed, but some features will be limited if missing
    pass

try:
    init(autoreset=True)
except Exception:
    pass

# ---------- Config ----------
NOTES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "loki_notes.txt")
USER_GIF = r"C:\Users\YOGESH\Downloads\tenor.gif"
FALLBACK_GIF = r"/mnt/data/5df7237e-e9cd-4523-8b94-1b1552c8b555.gif"
GIF_PATH = USER_GIF if os.path.exists(USER_GIF) else FALLBACK_GIF
ENABLE_GUI = (tk is not None and Image is not None and os.path.exists(GIF_PATH))

def safe_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
    except Exception:
        sys.stdout.write(" ".join(map(str, args)) + "\n")

def find_process_by_name(name):
    found = []
    try:
        name_l = name.lower()
        for proc in psutil.process_iter(['name', 'pid']):
            pname = proc.info.get('name') or ''
            if name_l in str(pname).lower():
                found.append(proc)
    except Exception:
        pass
    return found

# ---------- Optional overlay GUI ----------
class OverlayGUI(threading.Thread):
    def __init__(self, gif_path, queue_in=None, size=120):
        super().__init__(daemon=True)
        self.gif_path = gif_path
        self.queue_in = queue_in or queue.Queue()
        self._running = True
        self._listening = False
        self._frame_images = []
        self._delay = 100
        self._size = size
        self.root = None

    def run(self):
        if not ENABLE_GUI:
            return
        try:
            self.root = tk.Tk()
            self.root.title("Loki Overlay")
            self.root.attributes("-topmost", True)
            self.root.overrideredirect(True)
            bg = "#111111"
            self.root.configure(bg=bg)
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            width = 300
            height = 120
            x = max(0, screen_w - width - 20)
            y = max(0, screen_h - height - 60)
            self.root.geometry(f"{width}x{height}+{x}+{y}")
            frame = tk.Frame(self.root, bg=bg)
            frame.pack(fill="both", expand=True)
            self.canvas = tk.Canvas(frame, width=self._size, height=self._size, bg=bg, highlightthickness=0)
            self.canvas.grid(row=0, column=0, rowspan=3, padx=(10,8), pady=10)
            self.listen_label = tk.Label(frame, text='', fg='white', bg=bg, font=('Segoe UI', 10, 'bold'))
            self.listen_label.grid(row=0, column=1, sticky='w')
            self.user_label = tk.Label(frame, text='You: ', fg='#dddddd', bg=bg, font=('Segoe UI', 9))
            self.user_label.grid(row=1, column=1, sticky='w')
            self.assistant_label = tk.Label(frame, text='Loki: ', fg='#bbbbbb', bg=bg, font=('Segoe UI', 9))
            self.assistant_label.grid(row=2, column=1, sticky='w')
            self._load_gif_frames()
            self._animate(0)
            self._poll()
            self.root.mainloop()
        except Exception as e:
            safe_print("Overlay GUI error:", e)

    def _load_gif_frames(self):
        try:
            im = Image.open(self.gif_path)
            frames = []
            i = 0
            while True:
                try:
                    im.seek(i)
                    frames.append(im.copy())
                    i += 1
                except EOFError:
                    break
            self._frame_images = []
            for f in frames:
                circ = f.convert("RGBA").resize((self._size,self._size), Image.LANCZOS)
                mask = Image.new('L', (self._size,self._size), 0)
                d = ImageDraw.Draw(mask)
                d.ellipse((0,0,self._size,self._size), fill=255)
                circ.putalpha(mask)
                tkimg = ImageTk.PhotoImage(circ)
                self._frame_images.append(tkimg)
            try:
                self._delay = im.info.get('duration', 100)
            except Exception:
                self._delay = 100
        except Exception as e:
            safe_print("Failed to load GIF frames:", e)
            self._frame_images = []

    def _animate(self, index):
        if not self._running or not ENABLE_GUI:
            return
        if self._listening and self._frame_images:
            frame = self._frame_images[index % len(self._frame_images)]
            self.canvas.delete("all")
            self.canvas.create_image(self._size//2, self._size//2, image=frame)
            self.canvas.image = frame
            self.listen_label.config(text=' 🎙️Listening...')
        else:
            self.canvas.delete("all")
            if self._frame_images:
                frame = self._frame_images[0]
                self.canvas.create_image(self._size//2, self._size//2, image=frame)
                self.canvas.image = frame
            self.listen_label.config(text='')
        if self.root:
            try:
                self.root.after(self._delay if self._delay>0 else 100, lambda: self._animate(index+1))
            except Exception:
                pass

    def _poll(self):
        try:
            while not self.queue_in.empty():
                msg = self.queue_in.get_nowait()
                if not isinstance(msg, tuple) or len(msg) < 2:
                    continue
                key, val = msg[0], msg[1]
                if key == 'listening':
                    self._listening = bool(val)
                elif key == 'user':
                    self.user_label.config(text=f'You: {val[:30]}')
                elif key == 'assistant':
                    self.assistant_label.config(text=f'Loki: {val[:30]}')
        except Exception:
            pass
        if self._running and self.root:
            try:
                self.root.after(200, self._poll)
            except Exception:
                pass

    def stop(self):
        self._running = False
        try:
            if self.root:
                self.root.quit()
        except Exception:
            pass

# ---------- LokiAssistant (synchronous TTS for every output) ----------
class LokiAssistant:
    def __init__(self, overlay_queue=None):
        # engine + lock
        self.engine = None
        self.engine_lock = threading.Lock()
        self.available_voice_names = []
        self.current_voice_index = 0

        # try to init pyttsx3 robustly
        if pyttsx3 is not None:
            drivers = []
            sysname = platform.system().lower()
            if sysname == 'windows':
                drivers = ['sapi5', None]
            elif sysname == 'darwin':
                drivers = ['nsss', None]
            else:
                drivers = [None, 'espeak']
            for d in drivers:
                try:
                    if d:
                        self.engine = pyttsx3.init(driverName=d)
                    else:
                        self.engine = pyttsx3.init()
                    if self.engine:
                        break
                except Exception:
                    self.engine = None
            if self.engine:
                try:
                    voices = self.engine.getProperty('voices')
                    try:
                        self.available_voice_names = [getattr(v,'name',v.id) for v in voices]
                    except Exception:
                        self.available_voice_names = [v.id for v in voices]
                    self.current_voice_index = 0
                    try:
                        self.engine.setProperty('voice', voices[self.current_voice_index].id)
                    except Exception:
                        pass
                    try:
                        self.engine.setProperty('rate', 150)
                    except Exception:
                        pass
                    try:
                        self.engine.setProperty('volume', 1.0)
                    except Exception:
                        pass
                    safe_print("TTS engine initialized:", type(self.engine))
                except Exception as e:
                    safe_print("TTS setup error:", e)
                    self.engine = None
            else:
                safe_print("pyttsx3 init failed; will fallback to PowerShell on Windows.")
        else:
            safe_print("pyttsx3 not installed; will fallback to PowerShell on Windows.")

        # small queue retained (not required now but useful)
        self.tts_queue = queue.Queue(maxsize=256)
        self._tts_running = True
        self.tts_thread = threading.Thread(target=self._tts_worker, daemon=True)
        self.tts_thread.start()

        # speech recognizer
        self.recognizer = sr.Recognizer()
        self.listen_duration = 6
        self._suppress_listen = False
        self._last_spoken_time = 0
        self.print_responses = True

        self.overlay_queue = overlay_queue

        self.operators = {'+':lambda x,y: x+y, '-':lambda x,y:x-y, '*':lambda x,y:x*y, '/':lambda x,y: x/y if y!=0 else None}

    # this always attempts to speak synchronously (so voice occurs now)
    def speak_sync(self, text):
        if not text:
            return
        # suppress listening while speaking to avoid self-trigger
        try:
            self._suppress_listen = True
        except Exception:
            pass
        # try engine (thread-safe)
        if self.engine:
            try:
                with self.engine_lock:
                    self.engine.say(text)
                    self.engine.runAndWait()
                # successful speak
                try:
                    self._last_spoken_time = time.time()
                except Exception:
                    pass
                try:
                    self._suppress_listen = False
                except Exception:
                    pass
                return
            except Exception as e:
                safe_print("Engine speak failed:", e)
        # PowerShell fallback on Windows
        if platform.system().lower() == 'windows':
            try:
                self._powershell_speak(text)
                try:
                    self._last_spoken_time = time.time()
                except Exception:
                    pass
                try:
                    self._suppress_listen = False
                except Exception:
                    pass
                return
            except Exception as e:
                safe_print("PowerShell speak failed:", e)
        # final fallback: print only
        safe_print("TTS unavailable; would have spoken:", text)
        try:
            self._suppress_listen = False
        except Exception:
            pass

    # public speak: print + immediate speak_sync (ensures voice)
    def speak(self, text):
        if not text:
            return
        # overlay update
        try:
            if self.overlay_queue:
                self.overlay_queue.put(('assistant', text))
        except Exception:
            pass
        # print
        if self.print_responses:
            try:
                print(f"Assistant: {text}")
            except Exception:
                safe_print("Assistant:", text)
        # attempt to enqueue for worker (kept) but will always call sync to guarantee voice
        try:
            self.tts_queue.put_nowait(text)
        except Exception:
            pass
        # synchronous speak to ensure voice now
        self.speak_sync(text)

    def _tts_worker(self):
        # background worker: still consumes queue and tries to speak (if for some reason speak_sync failed earlier)
        while getattr(self, '_tts_running', True):
            try:
                text = self.tts_queue.get(timeout=0.2)
            except queue.Empty:
                continue
            if text is None:
                break
            # try speak_sync (will short-circuit to engine/powershell)
            try:
                self.speak_sync(text)
            except Exception as e:
                safe_print("Worker speak_sync failed:", e)
            try:
                self.tts_queue.task_done()
            except Exception:
                pass
            time.sleep(0.01)

    def _powershell_speak(self, text: str):
        if not text:
            return
        if platform.system().lower() != 'windows':
            raise RuntimeError("PowerShell TTS only on Windows")
        try:
            safe = str(text).replace("'", "''").replace('"', '""')
            ps_script = (
                "Add-Type -AssemblyName System.Speech; "
                "$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                "$synth.Volume = 100; $synth.Rate = 0; $synth.Speak([string]'{SAFE}'); "
                "$synth.Dispose();"
            ).replace('{SAFE}', safe)
            cmd = ['powershell', '-NoProfile', '-NonInteractive', '-Command', ps_script]
            creationflags = 0
            if hasattr(subprocess, "CREATE_NO_WINDOW"):
                creationflags = subprocess.CREATE_NO_WINDOW
            result = subprocess.run(cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=creationflags)
            if result.returncode != 0:
                raise Exception(result.stderr.strip())
        except Exception as e:
            raise

    # audio recording helpers
    def record_audio(self, duration=None, sample_rate=44100):
        duration = duration or self.listen_duration
        try:
            rec = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1)
            sd.wait()
            return rec.flatten()
        except Exception as e:
            safe_print("record_audio error:", e)
            return np.zeros(1)

    def save_audio(self, recording, filename="temp.wav", sample_rate=44100):
        try:
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes((recording * 32767).astype(np.int16).tobytes())
        except Exception as e:
            safe_print("save_audio error:", e)

    def listen(self):
        try:
            if self.overlay_queue:
                self.overlay_queue.put(('listening', True))
        except Exception:
            pass
        try:
            if getattr(self, '_suppress_listen', False):
                return ""
            last = getattr(self, '_last_spoken_time', 0)
            if time.time() - last < 0.6:
                return ""
            recording = self.record_audio()
            temp_file = "temp_recording.wav"
            self.save_audio(recording, temp_file)
            with sr.AudioFile(temp_file) as source:
                audio = self.recognizer.record(source)
                try:
                    command = self.recognizer.recognize_google(audio).lower()
                except sr.UnknownValueError:
                    self.speak("Sorry, I didn't catch that. Please say that again clearly.")
                    command = ""
                except sr.RequestError as e:
                    safe_print("recognize_google error:", e)
                    self.speak("Sorry, speech service error.")
                    command = ""
                except Exception as e:
                    safe_print("recognize error:", e)
                    self.speak("Sorry, I couldn't reach the speech service.")
                    command = ""
            try:
                os.remove(temp_file)
            except Exception:
                pass
            if command:
                safe_print("You said:", command)
            return command
        except Exception as e:
            safe_print("listen error:", e)
            self.speak("Microphone error. Please ensure microphone is connected.")
            return ""
        finally:
            try:
                if self.overlay_queue:
                    self.overlay_queue.put(('listening', False))
            except Exception:
                pass

    # simple open_app example ensures speak() used
    def open_app(self, key, url=None):
        try:
            if key == 'chrome':
                chrome = shutil.which('chrome') or shutil.which('chrome.exe')
                if chrome:
                    if url:
                        subprocess.Popen([chrome, url], shell=False)
                    else:
                        subprocess.Popen([chrome], shell=False)
                    self.speak("Opening Google Chrome.")
                    return True
                pf = os.environ.get('PROGRAMFILES', r'C:\Program Files')
                pf86 = os.environ.get('PROGRAMFILES(X86)', r'C:\Program Files (x86)')
                candidates = [
                    os.path.join(pf, 'Google', 'Chrome', 'Application', 'chrome.exe'),
                    os.path.join(pf86, 'Google', 'Chrome', 'Application', 'chrome.exe'),
                ]
                for c in candidates:
                    if os.path.exists(c):
                        if url:
                            subprocess.Popen([c, url], shell=False)
                        else:
                            subprocess.Popen([c], shell=False)
                        self.speak("Opening Google Chrome.")
                        return True
                if url:
                    webbrowser.open(url)
                    self.speak("Opening your browser.")
                    return True
                self.speak("Couldn't find Chrome, opening default browser.")
                webbrowser.open("http://google.com")
                return True
            if key in ('vscode','code'):
                code = shutil.which('code')
                if code:
                    subprocess.Popen([code], shell=False)
                    self.speak("Opening Visual Studio Code.")
                    return True
                local = os.environ.get('LOCALAPPDATA')
                if local:
                    path = os.path.join(local, 'Programs', 'Microsoft VS Code', 'Code.exe')
                    if os.path.exists(path):
                        subprocess.Popen([path], shell=False)
                        self.speak("Opening Visual Studio Code.")
                        return True
                self.speak("Could not open VS Code.")
                return False
        except Exception as e:
            safe_print("open_app error:", e)
            self.speak("Error while opening the application.")
            return False

    def close_app(self, app_name):
        try:
            procs = find_process_by_name(app_name.replace('.exe',''))
            if not procs:
                self.speak(f"No running {app_name} found.")
                return False
            for p in procs:
                try:
                    psutil.Process(p.info['pid']).terminate()
                except Exception:
                    pass
            self.speak(f"Closed {app_name} successfully.")
            return True
        except Exception as e:
            safe_print("close_app error:", e)
            self.speak("I couldn't close the application.")
            return False

    def solve_math(self, text):
        try:
            expr = text.lower().replace('what is','').replace("what's","").replace('calculate','').strip()
            expr = expr.replace('plus','+').replace('minus','-').replace('times','*').replace('x','*').replace('divided by','/')
            nums = re.findall(r'-?\d+(?:\.\d+)?', expr)
            if len(nums) < 2:
                return None
            op = re.search(r'[\+\-\*/]', expr)
            if not op:
                return None
            a = float(nums[0]); b = float(nums[1])
            operation = op.group()
            if operation in self.operators:
                res = self.operators[operation](a,b)
                if res is None:
                    return None
                if float(res).is_integer():
                    return int(res)
                return round(res,6)
            return None
        except Exception:
            return None

    def process_command(self, command):
        if not command:
            return True
        cmd = command.lower().strip()
        for w in ['loki','lokesh','hey loki','hey']:
            if cmd.startswith(w):
                cmd = cmd.replace(w,'',1).strip()
        if not cmd:
            return True

        # must speak examples
        if any(x in cmd for x in ["open chrome","open google chrome","launch chrome","open browser","open google"]):
            self.open_app('chrome', url='http://google.com')
            return True

        if any(x in cmd for x in ["open vscode","open visual studio code","open code"]):
            self.open_app('vscode')
            return True

        if "screenshot" in cmd or "capture" in cmd:
            self.speak("Taking screenshot in 2 seconds.")
            self.take_screenshot()
            return True

        if any(k in cmd for k in ["what time","time now","what's the time","what time is it"]):
            t = datetime.datetime.now().strftime("%I:%M %p")
            self.speak(f"The current time is {t}")
            return True

        if any(op in cmd for op in ['plus','minus','times','divided by','+','-','*','/']) and any(ch.isdigit() for ch in cmd):
            res = self.solve_math(cmd)
            if res is not None:
                self.speak(f"The answer is {res}")
            else:
                self.speak("I couldn't solve that. Try simple arithmetic.")
            return True

        if "who are you" in cmd:
            self.speak("I am Loki, your assistant. I will speak all outputs.")
            return True

        if "quit" in cmd or "exit" in cmd or "stop" in cmd:
            self.speak("Goodbye. Exiting now.")
            return False

        if cmd.startswith("search") or cmd.startswith("google") or "search for" in cmd:
            q = re.sub(r'^(search|google)\s*', '', cmd).strip()
            if not q:
                self.speak("What would you like me to search for?")
                return True
            self.speak(f"Searching for {q}")
            webbrowser.open(f'https://www.google.com/search?q={q}')
            return True

        # default: always speak the response
        self.speak("I heard: " + cmd)
        return True

    def take_screenshot(self):
        try:
            screenshots_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Screenshots')
            if not os.path.exists(screenshots_dir):
                os.makedirs(screenshots_dir)
            self._suppress_listen = True
            for i in range(2,0,-1):
                self.speak(str(i))
                time.sleep(1)
            img = pyautogui.screenshot()
            fn = f'screenshot_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
            path = os.path.join(screenshots_dir, fn)
            img.save(path)
            self._suppress_listen = False
            self._last_spoken_time = time.time()
            self.speak("Screenshot saved.")
            try:
                if platform.system().lower()=='windows':
                    os.startfile(path)
                else:
                    subprocess.Popen(['xdg-open', path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
        except Exception as e:
            safe_print("take_screenshot error:", e)
            self.speak("Could not take screenshot.")

    def run(self):
        self.speak("Voice initialized. Hello Yogesh. I will speak all responses.")
        running = True
        while running:
            cmd = self.listen()
            if cmd:
                running = self.process_command(cmd)
            time.sleep(0.05)

    def shutdown(self):
        try:
            self._tts_running = False
            try:
                self.tts_queue.put_nowait(None)
            except Exception:
                pass
            if self.tts_thread.is_alive():
                self.tts_thread.join(timeout=1)
        except Exception:
            pass

# ---------- main ----------
def main():
    overlay_queue = queue.Queue() if ENABLE_GUI else None
    overlay = None
    if ENABLE_GUI:
        overlay = OverlayGUI(GIF_PATH, queue_in=overlay_queue, size=120)
        overlay.start()
    assistant = LokiAssistant(overlay_queue=overlay_queue)
    try:
        assistant.run()
    except KeyboardInterrupt:
        safe_print("Interrupted by user.")
    finally:
        assistant.shutdown()
        if overlay:
            overlay.stop()
        safe_print("Exiting Loki Assistant.")

if __name__ == "__main__":
    main()
