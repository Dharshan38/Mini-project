import tkinter as tk
import threading
import time
import json
import datetime
import subprocess
import psutil
import pyttsx3
import pyaudio
import webbrowser
import os
import sys
import queue
import wikipedia
import pyautogui
import pyjokes
import pywhatkit
from vosk import Model, KaldiRecognizer
import speech_recognition as sr

# ---------------- CONFIGURATION ----------------
WAKE_WORD = "hey jarvis"
VOSK_MODEL_PATH = r"d:/mini project/vosk-model-small-en-us-0.15/vosk-model-small-en-us-0.15"

# ---------------- NON-BLOCKING SPEECH ENGINE ----------------
class SpeechEngine(threading.Thread):
    def __init__(self):
        super().__init__()
        self.engine = pyttsx3.init("sapi5")
        self.engine.setProperty("rate", 170)
        self.queue = queue.Queue()
        self.daemon = True
        self.start()

    def run(self):
        while True:
            text = self.queue.get()
            if text is None:
                break
            try:
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception as e:
                print(f"Speech error: {e}")
            self.queue.task_done()

    def say(self, text):
        self.queue.put(text)

voice = SpeechEngine()

def speak(text):
    print(f"Assistant: {text}")
    voice.say(text)

# ---------------- ASSISTANT STATE ----------------
STATE = "LISTENING"  # SLEEPING | LISTENING

# ---------------- GUI ----------------
root = tk.Tk()
root.title("Desktop Assistant")
root.geometry("300x400")
root.resizable(False, False)
root.configure(bg="black")

canvas = tk.Canvas(root, width=300, height=300, bg="black", highlightthickness=0)
canvas.pack()

status_label = tk.Label(
    root, text="Listening...",
    fg="white", bg="black", font=("Arial", 12)
)
status_label.pack(pady=10)

circle = canvas.create_oval(120, 120, 180, 180, fill="blue")

pulse_size = 0
pulse_dir = 1

def animate():
    global pulse_size, pulse_dir

    if STATE == "SLEEPING":
        canvas.itemconfig(circle, fill="blue")
        canvas.coords(circle, 120, 120, 180, 180)

    elif STATE == "LISTENING":
        pulse_size += pulse_dir * 2
        if pulse_size > 20 or pulse_size < 0:
            pulse_dir *= -1

        canvas.itemconfig(circle, fill="green")
        canvas.coords(
            circle,
            120 - pulse_size,
            120 - pulse_size,
            180 + pulse_size,
            180 + pulse_size
        )

    root.after(50, animate)

# ---------------- DEVICE SELECTION ----------------
def get_input_device_index():
    p = pyaudio.PyAudio()
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    # Prefer Microphone Array
    for i in range(0, numdevices):
        name = p.get_device_info_by_host_api_device_index(0, i).get('name')
        if "Microphone Array" in name and "Intel" in name:
            print(f"Selected Device: {name} (Index {i})")
            return i
    # Fallback to any Microphone
    for i in range(0, numdevices):
        name = p.get_device_info_by_host_api_device_index(0, i).get('name')
        if "Microphone" in name:
             print(f"Selected Device: {name} (Index {i})")
             return i
    print("Using Default Device")
    return None

DEVICE_INDEX = get_input_device_index()

# ---------------- COMMAND PROCESSOR ----------------
def process_command(command):
    # --- WEB ---
    if "open youtube" in command:
        speak("Opening YouTube")
        webbrowser.open("https://www.youtube.com")
        
    elif "open google" in command:
        speak("Opening Google")
        webbrowser.open("https://www.google.com")
        
    elif "open facebook" in command:
        speak("Opening Facebook")
        webbrowser.open("https://www.facebook.com")
        
    elif "open instagram" in command:
        speak("Opening Instagram")
        webbrowser.open("https://www.instagram.com")
        
    elif "open stackoverflow" in command:
        speak("Opening Stack Overflow")
        webbrowser.open("https://stackoverflow.com")

    elif "search for" in command:
        query = command.replace("search for", "").strip()
        speak(f"Searching for {query}")
        webbrowser.open(f"https://www.google.com/search?q={query}")

    elif "play" in command and "youtube" in command:
        query = command.replace("play", "").replace("on youtube", "").replace("youtube", "").strip()
        speak(f"Playing {query} on YouTube")
        pywhatkit.playonyt(query)

    elif "wikipedia" in command:
        try:
            speak("Searching Wikipedia...")
            query = command.replace("wikipedia", "").strip()
            results = wikipedia.summary(query, sentences=2)
            speak("According to Wikipedia")
            speak(results)
        except:
            speak("I couldn't find anything on Wikipedia")

    # --- APPS ---
    elif "open notepad" in command:
        speak("Opening Notepad")
        # subprocess.Popen("notepad.exe") # Creating issue with focus potentially?
        try:
            os.startfile("notepad.exe")
        except:
             subprocess.Popen("notepad.exe")
             
    elif "open calculator" in command:
        speak("Opening Calculator")
        try:
            os.startfile("calc.exe")
        except:
             subprocess.Popen("calc.exe")

    elif "open paint" in command:
        speak("Opening Paint")
        try:
            os.startfile("mspaint.exe")
        except:
             subprocess.Popen("mspaint.exe")

    # --- SYSTEM ---
    elif "time" in command:
        strTime = datetime.datetime.now().strftime("%H:%M")
        speak(f"The time is {strTime}")

    elif "date" in command:
        today = datetime.date.today().strftime("%B %d, %Y")
        speak(f"Today is {today}")
        
    elif "battery" in command:
        battery = psutil.sensors_battery()
        speak(f"Battery is at {battery.percent} percent")

    elif "shutdown" in command:
        speak("Shutting down the system")
        os.system("shutdown /s /t 1")

    elif "restart" in command:
        speak("Restarting the system")
        os.system("shutdown /r /t 1")
        
    elif "log off" in command or "sign out" in command:
        speak("Logging off")
        os.system("shutdown /l")
        
    elif "screenshot" in command:
        speak("Taking screenshot")
        file_name = f"screenshot_{int(time.time())}.png"
        pyautogui.screenshot(file_name)
        speak("Screenshot saved")

    elif "volume up" in command:
        pyautogui.press("volumeup")
        
    elif "volume down" in command:
        pyautogui.press("volumedown")
        
    elif "mute" in command:
        pyautogui.press("volumemute")

    elif "joke" in command:
        joke = pyjokes.get_joke()
        speak(joke)

    # --- EXIT ---
    elif "exit" in command or "go to sleep" in command:
        speak("Going back to sleep")
        return True # Signal to sleep

    return False

# ---------------- OFFLINE WAKE WORD ----------------
model = Model(VOSK_MODEL_PATH)
rec = KaldiRecognizer(model, 16000)

def wake_word_listener():
    global STATE

    p = pyaudio.PyAudio()
    kwargs = {
        "format": pyaudio.paInt16,
        "channels": 1,
        "rate": 16000,
        "input": True,
        "frames_per_buffer": 8000
    }
    if DEVICE_INDEX is not None:
        kwargs["input_device_index"] = DEVICE_INDEX
        
    try:
        stream = p.open(**kwargs)
        stream.start_stream()
    except Exception as e:
        print(f"Error opening audio stream: {e}")
        return

    while True:
        try:
            # Wake word is only relevant in SLEEPING mode usually, but here we scan always?
            # Actually, standard flow: Scan for "Jarvis" -> wake up -> Listen for Google command -> Sleep
            
            if STATE == "SLEEPING":
                data = stream.read(4000, exception_on_overflow=False)
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = result.get("text", "")
                    if WAKE_WORD in text:
                        STATE = "LISTENING"
                        status_label.config(text="Listening...")
                        speak("Yes?")
            
            elif STATE == "LISTENING":
                should_sleep = listen_command()
                if should_sleep:
                    STATE = "SLEEPING"
                    status_label.config(text="Sleeping... Say 'Hey Jarvis'")
                    
        except Exception as e:
            print(f"Error in wake loop: {e}")
            # If stream breaks, try to recover?
            break

# ---------------- RECOGNIZER SETUP ----------------
# Initialize recognizer globally to persist settings/calibration
recognizer_obj = sr.Recognizer()
recognizer_obj.dynamic_energy_threshold = True
recognizer_obj.energy_threshold = 400
recognizer_obj.pause_threshold = 0.8 # Seconds of silence to consider command complete

def calibrate_mic():
    """Calibrate microphone for ambient noise once at startup"""
    try:
        if DEVICE_INDEX is not None:
            source = sr.Microphone(device_index=DEVICE_INDEX)
        else:
            source = sr.Microphone()
            
        with source:
            print("Calibrating microphone for 1 second... Please be silent.")
            recognizer_obj.adjust_for_ambient_noise(source, duration=1.0)
            print("Calibration complete. Threshold:", recognizer_obj.energy_threshold)
    except Exception as e:
        print(f"Calibration error: {e}")

# Call calibration immediately
calibrate_mic()

# ---------------- COMMAND LISTENER ----------------
def listen_command():
    try:
        # Use the pre-calibrated recognizer
        if DEVICE_INDEX is not None:
             source = sr.Microphone(device_index=DEVICE_INDEX)
        else:
             source = sr.Microphone()
             
        with source:
            print("Listening for command...")
            # increased phrase_time_limit to allow longer sentences
            # timeout ensures we don't hang if no one speaks
            audio = recognizer_obj.listen(source, timeout=5, phrase_time_limit=10)
            
    except sr.WaitTimeoutError:
        return False # Just no speech heard, keep listening
    except Exception as e:
        print(f"Mic error: {e}")
        return False

    try:
        print("Recognizing...")
        command = recognizer_obj.recognize_google(audio).lower()
        print(f"You said: {command}")
        
        return process_command(command)

    except sr.UnknownValueError:
        pass # Google didn't understand
    except sr.RequestError:
        speak("Network error")
    except Exception as e:
        print(f"Recognition error: {e}")
        pass
    
    return False # Default: stay listening

# ---------------- START THREADS ----------------
if __name__ == "__main__":
    threading.Thread(target=wake_word_listener, daemon=True).start()
    animate()
    root.mainloop()
