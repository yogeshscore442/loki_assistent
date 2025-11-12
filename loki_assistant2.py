# -*- coding: utf-8 -*-
"""
Loki Assistant — Single-file advanced version with YouTube ad-skip and next-track.
Save as: loki_assistant2.py
Run: python loki_assistant2.py

Requirements:
  pip install speechrecognition pyttsx3 pyautogui sounddevice numpy pillow colorama psutil pygetwindow opencv-python

Optional:
  - skip_ad.png (screenshot of YouTube Skip Ad button) placed in same folder for more reliable skipping.

Important:
  - On macOS: give Python/Terminal Accessibility & Screen Recording permissions.
  - Keep YouTube visible and not minimized for automation to work reliably.
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
import math

# UI imports (optional)
try:
    import tkinter as tk
    from tkinter import ttk
except Exception:
    tk = None

# Image handling
try:
    from PIL import Image, ImageTk, ImageOps, ImageDraw
except Exception:
    Image = None

# Assistant imports
try:
    import speech_recognition as sr
except Exception:
    sr = None
import pyttsx3
import webbrowser
import pyautogui
import sounddevice as sd
import numpy as np
import wave
from colorama import Fore, Style, init
import psutil

# optional window focus helper
try:
    import pygetwindow as gw
except Exception:
    gw = None

# optional OpenCV for better image matching (confidence)
try:
    import cv2
except Exception:
    cv2 = None

init(autoreset=True)

# ---------- Config ----------
USER_GIF = r"C:\Users\YOGESH\Downloads\tenor.gif"  # change if needed
FALLBACK_GIF = r"/mnt/data/5df7237e-e9cd-4523-8b94-1b1552c8b555.gif"
GIF_PATH = USER_GIF if os.path.exists(USER_GIF) else FALLBACK_GIF

# Optional image names to detect skip button
SKIP_IMAGE_NAMES = ["skip_ad.png", "skip_ad_button.png", "skipad.png", "skip-ads.png"]

# GUI availability check
ENABLE_GUI = (tk is not None and Image is not None and os.path.exists(GIF_PATH))

# pyautogui settings
pyautogui.PAUSE = 0.05

# ---------- Small helpers ----------
def find_process_by_name(name):
    found = []
    try:
        name = name.lower()
        for proc in psutil.process_iter(['name', 'pid']):
            pname = proc.info.get('name') or ''
            if name in str(pname).lower():
                found.append(proc)
    except Exception:
        pass
    return found

def make_circular_image(pil_img, size):
    try:
        img = pil_img.convert("RGBA").resize((size, size), Image.LANCZOS)
        mask = Image.new('L', (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size, size), fill=255)
        img.putalpha(mask)
        return img
    except Exception:
        return pil_img

# ---------- Overlay GUI ----------
class OverlayGUI(threading.Thread):
    def __init__(self, gif_path, queue_in=None, size=140):
        super().__init__(daemon=True)
        self.gif_path = gif_path
        self.queue_in = queue_in or queue.Queue()
        self._running = True
        self._listening = False
        self.last_user = ""
        self.last_assistant = ""
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
            width = 320
            height = 120
            x = max(0, screen_w - width - 20)
            y = max(0, screen_h - height - 60)
            self.root.geometry(f"{width}x{height}+{x}+{y}")

            frame = tk.Frame(self.root, bg=bg)
            frame.pack(fill="both", expand=True)

            self.canvas = tk.Canvas(frame, width=self._size, height=self._size,
                                    bg=bg, highlightthickness=0)
            self.canvas.grid(row=0, column=0, rowspan=3, padx=(10, 8), pady=10)

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
            print(f"{Fore.RED}Overlay GUI error: {e}{Style.RESET_ALL}")

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
                circ = make_circular_image(f, self._size)
                tkimg = ImageTk.PhotoImage(circ)
                self._frame_images.append(tkimg)
            try:
                self._delay = im.info.get('duration', 100)
            except Exception:
                self._delay = 100
        except Exception as e:
            print(f"{Fore.YELLOW}Failed to load GIF frames: {e}{Style.RESET_ALL}")
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
                self.root.after(self._delay if self._delay > 0 else 100, lambda: self._animate(index + 1))
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

# ---------- Loki Assistant ----------
class LokiAssistant:
    def __init__(self, overlay_queue=None):
        # TTS engine
        try:
            self.engine = pyttsx3.init()
            self.setup_voice()
        except Exception:
            self.engine = None
            print(f"{Fore.YELLOW}Warning: pyttsx3 init failed, PowerShell fallback may be used{Style.RESET_ALL}")

        # TTS queue & thread
        self.tts_queue = queue.Queue()
        self._tts_running = True
        self.tts_thread = threading.Thread(target=self._tts_worker, daemon=True)
        self.tts_thread.start()

        # recognizer
        self.recognizer = sr.Recognizer() if sr else None
        self.listen_duration = 7
        self._suppress_listen = False
        self._last_spoken_time = 0
        self.print_responses = True
        self._last_command = None
        self._last_command_time = 0
        self.duplicate_action_window = 5

        # math ops
        self.operators = {
            '+': lambda x, y: x + y,
            '-': lambda x, y: x - y,
            'x': lambda x, y: x * y,
            '*': lambda x, y: x * y,
            '/': lambda x, y: x / y if y != 0 else None
        }

        self.question_words = [
            "what", "who", "when", "where", "why", "how", "which",
            "could you", "can you", "would you", "will you",
            "tell me", "show me", "let me know"
        ]
        self.action_keywords = [
            'open', 'close', 'search', 'calculate', 'set', 'change', 'play', 'take', 'screenshot',
            'stop', 'quit', 'exit', 'launch', 'find', 'calculator'
        ]

        # voice choices
        self.current_voice_index = 0
        self.available_voices = []
        self.available_voice_names = []

        # overlay integration
        self.overlay_queue = overlay_queue

        # preferred browser tokens
        self.PREFERRED_BROWSER_TITLES = ['chrome', 'youtube', 'edge', 'firefox', 'brave']

    def setup_voice(self):
        if self.engine:
            try:
                voices = self.engine.getProperty('voices')
                self.available_voices = voices
                try:
                    self.available_voice_names = [getattr(v, 'name', v.id) for v in voices]
                except Exception:
                    self.available_voice_names = [v.id for v in voices]
                self.current_voice_index = 0
                self.engine.setProperty('voice', voices[self.current_voice_index].id)
                self.engine.setProperty('rate', 150)
            except Exception:
                self.engine = None

    def speak(self, text):
        if not text:
            return
        try:
            if self.overlay_queue:
                self.overlay_queue.put(('assistant', text))
        except Exception:
            pass

        if self.print_responses:
            try:
                print(f"{Fore.CYAN}Assistant: {text}{Style.RESET_ALL}")
            except Exception:
                print("Assistant:", text)

        try:
            self._last_spoken_time = time.time()
        except Exception:
            pass

        try:
            self.tts_queue.put_nowait(text)
            return
        except queue.Full:
            try:
                while not self.tts_queue.empty():
                    self.tts_queue.get_nowait()
            except Exception:
                pass
            try:
                self.tts_queue.put_nowait(text)
                return
            except Exception:
                pass

        try:
            self._powershell_speak(text)
        except Exception:
            if self.engine:
                try:
                    self.engine.say(text)
                    self.engine.runAndWait()
                except Exception:
                    print(f"{Fore.RED}TTS failed{Style.RESET_ALL}")

    def _tts_worker(self):
        while getattr(self, '_tts_running', True):
            try:
                text = self.tts_queue.get(timeout=0.2)
            except queue.Empty:
                continue
            if text is None:
                break
            try:
                try:
                    self._powershell_speak(text)
                except Exception:
                    if self.engine:
                        try:
                            self.engine.say(text)
                            self.engine.runAndWait()
                        except Exception:
                            pass
            except Exception:
                pass
            finally:
                try:
                    self.tts_queue.task_done()
                except Exception:
                    pass
            time.sleep(0.01)

    def _powershell_speak(self, text: str):
        if not text:
            return
        if platform.system().lower() != "windows":
            raise RuntimeError("PowerShell TTS only available on Windows")
        try:
            safe = str(text).replace("'", "''").replace('"', '""')
            select_voice_cmd = ''
            try:
                if self.available_voice_names and 0 <= self.current_voice_index < len(self.available_voice_names):
                    ps_name = str(self.available_voice_names[self.current_voice_index]).replace("'", "''")
                    select_voice_cmd = f"$synth.SelectVoice('{ps_name}');"
            except Exception:
                select_voice_cmd = ''
            ps_script = (
                "try {{\n"
                "    Add-Type -AssemblyName System.Speech;\n"
                "    $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer;\n"
                "    {SELECT_VOICE_CMD}\n"
                "    $synth.Rate = 0;\n"
                "    $synth.Volume = 100;\n"
                "    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8;\n"
                "    $synth.Speak([string]'{SAFE}');\n"
                "    $synth.Dispose();\n"
                "}} catch {{\n"
                "    [Console]::Error.WriteLine($_.Exception.Message);\n"
                "    exit 1;\n"
                "}}"
            )
            try:
                ps_filled = ps_script.format(SELECT_VOICE_CMD=select_voice_cmd, SAFE=safe)
            except Exception:
                ps_filled = ps_script.replace('{SELECT_VOICE_CMD}', select_voice_cmd).replace('{SAFE}', safe)
            cmd = ['powershell', '-NoProfile', '-NonInteractive', '-Command', ps_filled]
            creationflags = 0
            if hasattr(subprocess, "CREATE_NO_WINDOW"):
                creationflags = subprocess.CREATE_NO_WINDOW
            result = subprocess.run(cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    text=True, creationflags=creationflags)
            if result.returncode != 0:
                raise Exception(f"PowerShell TTS failed: {result.stderr}")
        except Exception as e:
            print(f"{Fore.YELLOW}PowerShell TTS error: {e}{Style.RESET_ALL}")
            raise

    # audio recording and saving
    def record_audio(self, duration=None, sample_rate=44100):
        duration = duration or self.listen_duration
        recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1)
        sd.wait()
        return recording.flatten()

    def save_audio(self, recording, filename="temp.wav", sample_rate=44100):
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes((recording * 32767).astype(np.int16).tobytes())

    # --------- FIXED listen() (no 'with sd.rec(...) as ...') ----------
    def listen(self):
        """Record and transcribe, with safeguards against hearing assistant."""
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

            if not self.recognizer:
                return ""

            # RECORD properly
            try:
                recording = self.record_audio()
            except Exception as e:
                print(f"{Fore.RED}Recording error: {e}{Style.RESET_ALL}")
                self.speak("Microphone error. Please ensure your microphone is connected.")
                return ""

            temp_file = "temp_recording.wav"
            try:
                self.save_audio(recording, temp_file)
            except Exception as e:
                print(f"{Fore.RED}Save audio error: {e}{Style.RESET_ALL}")
                self.speak("Microphone error while saving audio.")
                return ""

            # TRANSCRIBE
            try:
                with sr.AudioFile(temp_file) as source:
                    audio = self.recognizer.record(source)
                    try:
                        command = self.recognizer.recognize_google(audio).lower()
                    except sr.UnknownValueError:
                        self.speak("Sorry, I didn't catch that. Please say that again clearly.")
                        command = ""
                    except sr.RequestError as e:
                        print(f"{Fore.RED}Recognition request error: {e}{Style.RESET_ALL}")
                        self.speak("Sorry, there was an error with the speech recognition service.")
                        command = ""
                    except Exception as e:
                        print(f"{Fore.RED}Recognition error: {e}{Style.RESET_ALL}")
                        self.speak("Sorry, I couldn't reach the speech service.")
                        command = ""
            finally:
                try:
                    os.remove(temp_file)
                except Exception:
                    pass

            if self.print_responses and command:
                print(f"{Fore.YELLOW}🗣️ You said: {command}{Style.RESET_ALL}")
            try:
                if self.overlay_queue:
                    self.overlay_queue.put(('user', command))
            except Exception:
                pass
            return command

        except Exception as e:
            print(f"{Fore.RED}Microphone error: {e}{Style.RESET_ALL}")
            self.speak("Microphone error. Please ensure your microphone is connected.")
            return ""
        finally:
            try:
                if self.overlay_queue:
                    self.overlay_queue.put(('listening', False))
            except Exception:
                pass

    # screenshot
    def take_screenshot(self):
        try:
            screenshots_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Screenshots')
            if not os.path.exists(screenshots_dir):
                os.makedirs(screenshots_dir)
            self._suppress_listen = True
            for i in range(2, 0, -1):
                self.speak(str(i))
                time.sleep(1)
            screenshot = pyautogui.screenshot()
            filename = f'screenshot_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
            screenshot_path = os.path.join(screenshots_dir, filename)
            screenshot.save(screenshot_path)
            self._suppress_listen = False
            self._last_spoken_time = time.time()
            self.speak("Captured and saved in the Yogesh folder.")
            try:
                if platform.system().lower() == "windows":
                    os.startfile(screenshot_path)
                else:
                    subprocess.Popen(['xdg-open', screenshot_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
        except Exception as e:
            print(f"{Fore.RED}Screenshot error: {e}{Style.RESET_ALL}")
            self.speak("Sorry, I couldn't take a screenshot.")

    def get_weather(self):
        self.speak("I need a weather API key configured to fetch weather.")

    def open_app(self, key, url=None):
        system = platform.system().lower()
        try:
            if key == 'chrome':
                chrome = shutil.which('chrome') or shutil.which('chrome.exe')
                if chrome:
                    if url:
                        subprocess.Popen([chrome, url], shell=False)
                    else:
                        subprocess.Popen([chrome], shell=False)
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
                        return True
                if url:
                    webbrowser.open(url)
                    return True
                return False
            if key == 'vscode' or key == 'code':
                code = shutil.which('code')
                if code:
                    subprocess.Popen([code], shell=False)
                    return True
                local = os.environ.get('LOCALAPPDATA')
                if local:
                    path = os.path.join(local, 'Programs', 'Microsoft VS Code', 'Code.exe')
                    if os.path.exists(path):
                        subprocess.Popen([path], shell=False)
                        return True
                return False
        except Exception as e:
            print(f"{Fore.RED}open_app error: {e}{Style.RESET_ALL}")
            return False

    def close_app(self, app_name):
        try:
            procs = find_process_by_name(app_name)
            if not procs:
                self.speak(f"No running {app_name} applications found.")
                return False
            for proc in procs:
                try:
                    psutil.Process(proc.info['pid']).terminate()
                except Exception:
                    pass
            self.speak(f"Closed {app_name} successfully.")
            return True
        except Exception as e:
            print(f"{Fore.RED}Error closing app: {e}{Style.RESET_ALL}")
            self.speak(f"Sorry, I couldn't close {app_name}.")
            return False

    def solve_math(self, expression):
        try:
            expr = expression.lower()
            expr = expr.replace('what is', '').replace('calculate', '').replace('solve', '')
            expr = expr.replace("what's", '').replace('whats', '').replace('equals', '')
            expr = expr.replace('equal to', '').replace('answer', '').strip()
            expr = expr.replace('plus', '+').replace('minus', '-').replace('x', '*')
            expr = expr.replace('times', '*').replace('multiplied by', '*').replace('divided by', '/')
            number_pattern = r'-?\d+(?:\.\d+)?'
            numbers = list(map(float, re.findall(number_pattern, expr)))
            if len(numbers) != 2:
                return None
            op_match = re.search(r'[\+\-\*/x]', expr)
            if not op_match:
                return None
            op = op_match.group()
            num1, num2 = numbers
            if op in self.operators:
                result = self.operators[op](num1, num2)
                if result is not None:
                    if float(result).is_integer():
                        return int(result)
                    return result
            return None
        except Exception:
            return None

    # --------------- YouTube/Music controls ---------------
    def _focus_browser_window(self):
        try:
            if gw:
                all_titles = gw.getAllTitles()
                for tkn in self.PREFERRED_BROWSER_TITLES:
                    for title in all_titles:
                        try:
                            if title and tkn.lower() in title.lower():
                                wins = gw.getWindowsWithTitle(title)
                                if wins:
                                    win = wins[0]
                                    try:
                                        win.activate()
                                        time.sleep(0.2)
                                        return True
                                    except Exception:
                                        try:
                                            win.minimize()
                                            time.sleep(0.05)
                                            win.maximize()
                                            time.sleep(0.2)
                                            return True
                                        except Exception:
                                            continue
                        except Exception:
                            continue
            sw, sh = pyautogui.size()
            pyautogui.click(int(sw*0.5), int(sh*0.5))
            time.sleep(0.12)
            return True
        except Exception:
            return False

    def _locate_skip_button_regions(self):
        sw, sh = pyautogui.size()
        regions = []
        regions.append((int(sw*0.55), int(sh*0.6), int(sw*0.4), int(sh*0.35)))
        regions.append((int(sw*0.25), int(sh*0.6), int(sw*0.5), int(sh*0.35)))
        regions.append((int(sw*0.7), int(sh*0.7), int(sw*0.22), int(sh*0.22)))
        regions.append((int(sw*0.2), int(sh*0.2), int(sw*0.6), int(sh*0.6)))
        return regions

    def _try_click_skip_images(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        regions = self._locate_skip_button_regions()
        for name in SKIP_IMAGE_NAMES:
            path = os.path.join(script_dir, name)
            if not os.path.exists(path):
                continue
            for region in regions:
                try:
                    if cv2:
                        loc = pyautogui.locateCenterOnScreen(path, region=region, confidence=0.78)
                    else:
                        loc = pyautogui.locateCenterOnScreen(path, region=region)
                    if loc:
                        dx = int((math.sin(time.time())*3))
                        dy = int((math.cos(time.time())*3))
                        x_click = loc.x + dx
                        y_click = loc.y + dy
                        pyautogui.moveTo(x_click, y_click, duration=0.12)
                        pyautogui.click(x_click, y_click)
                        time.sleep(0.12)
                        return True
                except Exception:
                    continue
        return False

    def skip_youtube_ad(self):
        try:
            self.speak("Trying to skip the ad.")
            self._focus_browser_window()
            attempts = 6
            for attempt in range(attempts):
                try:
                    for k in ['k', 'l', 'right', 'space', 'm']:
                        try:
                            pyautogui.press(k)
                            time.sleep(0.1)
                        except Exception:
                            pass
                    try:
                        pyautogui.press('right', presses=2, interval=0.08)
                    except Exception:
                        pass
                except Exception:
                    pass

                clicked = self._try_click_skip_images()
                if clicked:
                    self.speak("Skipped the ad.")
                    return True

                try:
                    pyautogui.press('n')
                except Exception:
                    pass

                time.sleep(0.5)
            try:
                pyautogui.press('nexttrack')
                self.speak("Attempted next track as fallback.")
                return True
            except Exception:
                pass

            self.speak("I tried multiple methods but couldn't detect the skip button. Make sure the video is visible.")
            return False
        except Exception as e:
            print(f"{Fore.RED}skip_youtube_ad error: {e}{Style.RESET_ALL}")
            self.speak("Sorry, I couldn't skip the ad automatically.")
            return False

    def play_next_track(self):
        try:
            self._focus_browser_window()
            try:
                pyautogui.press('n', presses=2, interval=0.12)
            except Exception:
                pass
            time.sleep(0.15)
            try:
                pyautogui.press('nexttrack')
            except Exception:
                pass
            self.speak("Playing the next track.")
            return True
        except Exception as e:
            print(f"{Fore.RED}play_next_track error: {e}{Style.RESET_ALL}")
            self.speak("Sorry, I couldn't go to the next track.")
            return False

    def play_pause_player(self):
        try:
            self._focus_browser_window()
            pyautogui.press('k')
            return True
        except Exception:
            return False

    # Command processor
    def process_command(self, command):
        if not command:
            return True
        original = command
        command = command.lower().strip()
        for w in ['loki', 'lokesh', 'low key', 'hey']:
            if command.startswith(w):
                command = command.replace(w, '', 1).strip()
        command = re.sub(r'\s+', ' ', command)
        words = set(command.split())

        is_question = False
        if any(command.strip().startswith(q) for q in self.question_words):
            is_question = True
        if '?' in original:
            is_question = True

        math_patterns = [
            r"^what\s+is\s+\d+[\s+\+\-\*/x]\s*\d+",
            r"^calculate\s+\d+[\s+\+\-\*/x]\s*\d+",
            r"^solve\s+\d+[\s+\+\-\*/x]\s*\d+",
            r"^how\s+much\s+is\s+\d+[\s+\+\-\*/x]\s*\d+"
        ]
        if any(re.search(pattern, command) for pattern in math_patterns):
            is_question = True

        question_patterns = [
            r"^can you",
            r"^could you",
            r"^tell me",
            r"^do you",
            r"^how (do|can|would|could|should|is|are|to)",
            r"^what (is|are|should|can|do|does)",
            r"^when (is|are|should|will)",
            r"^where (is|are|can)",
            r"^why (is|are|do|does)",
            r"^which (is|are|one)",
            r"^would you",
            r"^will you",
            r"^show me",
            r"^let me know"
        ]
        if any(re.search(pattern, command) for pattern in question_patterns):
            is_question = True

        is_action = any(re.search(r'\b' + re.escape(k) + r'\b', command) for k in self.action_keywords)
        if not (is_question or is_action):
            return True

        # listening duration change
        if ("listening" in command or "listen" in command) and any(w in words for w in ["set", "change", "make"]):
            m = re.search(r"(\d+)", command)
            if m:
                secs = int(m.group(1))
                self.listen_duration = max(1, min(60, secs))
                self.speak(f"Okay, I will listen for {self.listen_duration} seconds.")
                return True
            else:
                self.speak("Please tell me how many seconds to listen.")
                return True

        # speech rate
        if any(w in command for w in ["speech rate", "speak faster", "speak slower", "change speech"]):
            m = re.search(r"(\d{2,3})", command)
            if m:
                rate = int(m.group(1))
                if self.engine:
                    try:
                        self.engine.setProperty('rate', rate)
                        self.speak(f"Speech rate set to {rate}.")
                        return True
                    except Exception:
                        pass
                self.speak(f"Okay, noted speech rate {rate}.")
                return True
            if 'faster' in command:
                if self.engine:
                    try:
                        current = self.engine.getProperty('rate')
                        new = min(300, current + 20)
                        self.engine.setProperty('rate', new)
                        self.speak('Okay, speaking a bit faster now.')
                    except Exception:
                        self.speak('Unable to change rate right now.')
                else:
                    self.speak('TTS engine not available.')
                return True
            if 'slower' in command:
                if self.engine:
                    try:
                        current = self.engine.getProperty('rate')
                        new = max(80, current - 20)
                        self.engine.setProperty('rate', new)
                        self.speak('Okay, speaking a bit slower now.')
                    except Exception:
                        self.speak('Unable to change rate right now.')
                else:
                    self.speak('TTS engine not available.')
                return True

        # again remove wake words
        for w in ['loki', 'lokesh', 'low key']:
            if command.startswith(w):
                command = command.replace(w, '', 1).strip()
        command = re.sub(r'\s+', ' ', command)
        if not command:
            return True

        # Basic commands
        if any(word in command for word in ["hello", "hi", "hey"]):
            self.speak("Hello! Yogesh, I'm Loki — your personal assistant. How can I help you today?")
            return True
        if "who are you" in command:
            self.speak("I am Loki, your personal AI assistant. I can open apps , and more.")
            return True
        if any(t in command for t in ["time", "clock"]):
            current_time = datetime.datetime.now().strftime("%I:%M %p")
            self.speak(f"The current time is {current_time}")
            return True
        if any(w in command for w in ["weather", "temperature", "forecast"]):
            self.get_weather()
            return True

        if "screenshot" in command or "capture" in command or "screen shot" in command:
            self.take_screenshot()
            return True

        # NEW controls: skip ad / next track / play / pause
        if "skip ad" in command or "skip ads" in command or "skip the ad" in command:
            self.skip_youtube_ad()
            return True

        if "play next song" in command or "play next songs" in command or "next song" in command or "play next" in command or "next track" in command:
            self.play_next_track()
            return True

        if "play music" in command or ("play" in command and "music" in command):
            played = self.play_pause_player()
            if played:
                self.speak("Playing the music.")
            else:
                self.speak("Tried to play the music.")
            return True

        if "pause" in command or ("stop" in command and "music" in command):
            paused = self.play_pause_player()
            if paused:
                self.speak("Paused.")
            else:
                self.speak("Tried to pause.")
            return True

        # closing, opening, etc (kept original)
        if "close" in command:
            if "chrome" in command:
                self.close_app("chrome.exe")
            elif "camera" in command:
                self.close_app("WindowsCamera.exe")
            elif "calculator" in command or "calc" in command:
                if not self.close_app("Calculator.exe"):
                    self.close_app("ApplicationFrameHost.exe")
            elif "vs code" in command or "visual studio code" in command:
                self.close_app("Code.exe")
            elif "spotify" in command:
                self.close_app("spotify.exe")
            else:
                self.speak("Sorry, I don't know how to close that application.")
            return True

        if any(browser in command for browser in ["chrome", "browser", "chorme", "crome"]):
            if "close" in command:
                self.close_app("chrome.exe")
            else:
                self.speak("Opening Google Chrome")
                self.open_app('chrome', url='http://google.com')
            return True

        if "camera" in command:
            if "close" in command:
                self.close_app("WindowsCamera.exe")
            else:
                self.speak("Opening camera")
                try:
                    os.system("start microsoft.windows.camera:")
                except Exception:
                    pass
            return True

        if "whatsapp" in command:
            if "close" in command:
                self.close_app("WhatsApp.exe")
            else:
                self.speak("Opening WhatsApp Web")
                webbrowser.open('https://web.whatsapp.com')
            return True

        if any(music in command for music in ["music", "songs", "song"]):
            if "close" in command:
                self.close_app("Music.UI.exe")
            else:
                self.speak("Opening YouTube Music")
                webbrowser.open('https://music.youtube.com')
            return True

        if "youtube" in command:
            if "close" in command:
                self.close_app("chrome.exe")
            else:
                self.speak("Opening YouTube")
                webbrowser.open('https://youtube.com')
            return True

        if "edge" in command or "microsoft edge" in command:
            if "close" in command:
                self.close_app("msedge.exe")
            else:
                self.speak("Opening Microsoft Edge")
                edge = shutil.which('msedge') or shutil.which('msedge.exe')
                if edge:
                    try:
                        subprocess.Popen([edge], shell=False)
                    except Exception:
                        try:
                            os.system('start microsoft-edge:')
                        except Exception:
                            pass
                else:
                    try:
                        os.system('start microsoft-edge:')
                    except Exception:
                        pass
            return True

        if "spotify" in command:
            self.speak("Opening Spotify Web")
            webbrowser.open('https://open.spotify.com')
            return True

        if "google" in command and ("open" in command or "search" in command):
            self.speak("Opening Google")
            webbrowser.open('http://google.com')
            return True

        if any(k in command for k in ["code", "vs code", "visual studio code"]):
            self.speak("Opening Visual Studio Code")
            self.open_app('vscode')
            return True

        if "thank you" in command:
            self.speak("You're welcome! Is there anything else I can help you with?")
            return True

        if any(word in command for word in ["goodbye", "bye", "quit", "exit"]):
            self.speak("Goodbye! Have a great day!")
            return False

        if "joke" in command:
            self.speak("Why don't scientists trust atoms? Because they make up everything!")
            return True

        if "calculator" in command:
            self.speak("Opening calculator")
            try:
                subprocess.Popen('calc.exe')
            except Exception:
                self.speak("Sorry, I couldn't open the calculator")
            return True

        if "search" in command:
            search_query = command.replace("search", "").strip()
            if search_query:
                self.speak(f"Searching for {search_query}")
                webbrowser.open(f'https://www.google.com/search?q={search_query}')
            else:
                self.speak("What would you like me to search for?")
            return True

        # math handling
        if any(op in command for op in ['plus', 'minus', 'times', 'multiplied by', 'divided by', '+', '-', '*', '/', 'x']) or \
           (any(w in command for w in ['what', 'calculate', 'solve']) and any(n.isdigit() for n in command.split())):
            expr = command.lower()
            expr = expr.replace('what is', '').replace('calculate', '').replace('equals', '').replace('equal to', '')
            expr = expr.replace("what's", '').replace('whats', '').replace('solve', '')
            expr = expr.strip()
            result = self.solve_math(expr)
            if result is not None:
                self.speak(f"The answer is {result}")
            else:
                self.speak("Sorry, I couldn't solve that math problem. Try simple arithmetic like 2 plus 2.")
            return True

        # fallback for questions
        if is_question:
            if re.search(r'how\s+(do|can)\s+you\s+(help|assist)', command):
                self.speak("I can help open apps, perform calculations, tell the time, search the web, and more.")
                return True
            self.speak("I can help with many tasks — please try rephrasing or ask me to open an app or operations.")
            return True

        return True

    def run(self):
        self.speak("Hello! Yogesh. I'm Loki, your personal assistant. How can I help you?")
        running = True
        while running:
            command = ""
            try:
                command = self.listen()
            except Exception:
                pass
            if command:
                running = self.process_command(command)
            time.sleep(0.1)

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

# ---------- Main ----------
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
        print("Interrupted by user.")
    finally:
        assistant.shutdown()
        if overlay:
            overlay.stop()
        print("Exiting Loki Assistant.")

if __name__ == "__main__":
    main()
