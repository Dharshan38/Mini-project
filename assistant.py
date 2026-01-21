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
import shutil
import sys
import queue
import wikipedia
import pyautogui
import pyjokes
import pywhatkit
from vosk import Model, KaldiRecognizer
import speech_recognition as sr
import random

# ---------------- CONFIGURATION ----------------
WAKE_WORD = "hey bell"
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

# ---------------- HELPER FOR SUB-DIALOGUES ----------------
def wait_for_input():
    """Captures a single phrase for sub-dialogues (filename, confirmation, etc.)"""
    try:
        if DEVICE_INDEX is not None:
             source = sr.Microphone(device_index=DEVICE_INDEX)
        else:
             source = sr.Microphone()
             
        with source:
            print("Waiting for detail input...")
            # Short timeout ensuring quick interactions
            audio = recognizer_obj.listen(source, timeout=5, phrase_time_limit=5)
        
        text = recognizer_obj.recognize_google(audio).lower()
        print(f"Captured: {text}")
        return text
    except Exception as e:
        print(f"Input wait error: {e}")
        return None

def get_random_reply(category):
    """Returns a random friendly reply based on category."""
    replies = {
        "open": [
            "Sure! ",
            "Coming right up. ",
            "Got it. ",
            "Okay, ",
            "Just a second, "
        ],
        "check": [
             "Let me check. ",
             "One moment. ",
             "Checking that for you. ",
             "Here matches I found. "
        ],
        "done": [
             "Done! ",
             "All set. ",
             "Finished. ",
             "Completed. "
        ],
        "general": [
             "Okay. ",
             "Sure. ",
             "No problem. "
        ]
    }
    return random.choice(replies.get(category, replies["general"]))

def search_worker(query, search_type):
    """
    Recursive search in background.
    search_type: 'file' or 'dir'
    """
    speak(f"Searching for {search_type} {query}...")
    
    # Define search roots
    user_home = os.path.expanduser("~")
    search_paths = [
        os.path.join(user_home, "Desktop"),
        os.path.join(user_home, "Documents"),
        os.path.join(user_home, "Downloads"),
        os.path.join(user_home, "OneDrive", "Desktop"),
        os.path.join(user_home, "OneDrive", "Documents"),
    ]
    
    # Remove duplicates and non-existing paths
    search_paths = list(set([p for p in search_paths if os.path.exists(p)]))
    
    found_count = 0
    first_match = None
    
    print(f"Starting legacy search for {query} in {search_paths}")
    
    for root_path in search_paths:
        for root, dirs, files in os.walk(root_path):
            # Skip hidden folders
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            items = files if search_type == "file" else dirs
            
            for item in items:
                if query.lower() in item.lower():
                    found_count += 1
                    full_path = os.path.join(root, item)
                    if first_match is None:
                        first_match = full_path
                    
                    # Optimization: Stop after finding a few to save time? 
                    # For now scan all to count, or stop at 1? 
                    # User asked for "speak whether results are found".
                    # Let's stop at 1 for speed if we just want to open it.
                    # But counting is nice. Let's limit scan?
                    pass
    
    if first_match:
        if found_count == 1:
            speak(f"Found it.")
        else:
            speak(f"Found {found_count} matches. Opening the first one.")
            
        try:
            # Highlight in explorer
            subprocess.Popen(f'explorer /select,"{first_match}"')
        except Exception as e:
            print(f"Open error: {e}")
            speak("I found it, but couldn't open the folder.")
    else:
        speak(f"Sorry, I couldn't find any {search_type} named {query}.")

# ---------------- COMMAND PROCESSOR ----------------
def process_command(command):
    # --- CONVERSATION & GREETINGS ---
    if command in ["hello", "hi", "hey", "hello bell", "hi bell"]:
        speak("Hello! How can I help you today?")
        return False

    elif "how are you" in command:
        speak("I am functioning within normal parameters, thank you for asking.")
        return False

    elif "who are you" in command or "what can you do" in command:
        speak("I am your personal desktop assistant. I can open apps, search the web, and answer basic questions.")
        return False
    
    elif "thank you" in command:
        speak("You are welcome.")
        return False

    # --- WEB ---
    if "open youtube" in command:
        speak(f"{get_random_reply('open')}Opening YouTube")
        webbrowser.open("https://www.youtube.com")
        
    elif "open google" in command:
        speak(f"{get_random_reply('open')}Opening Google")
        webbrowser.open("https://www.google.com")
        
    elif "open facebook" in command:
        speak(f"{get_random_reply('open')}Opening Facebook")
        webbrowser.open("https://www.facebook.com")
        
    elif "open instagram" in command:
        speak(f"{get_random_reply('open')}Opening Instagram")
        webbrowser.open("https://www.instagram.com")
        
    elif "open stackoverflow" in command:
        speak(f"{get_random_reply('open')}Opening Stack Overflow")
        webbrowser.open("https://stackoverflow.com")

    elif "search for" in command:
        query = command.replace("search for", "").strip()
        speak(f"{get_random_reply('check')}Searching for {query}")
        webbrowser.open(f"https://www.google.com/search?q={query}")

    elif "play" in command and "youtube" in command:
        query = command.replace("play", "").replace("on youtube", "").replace("youtube", "").strip()
        speak(f"{get_random_reply('open')}Playing {query} on YouTube")
        pywhatkit.playonyt(query)

    # --- KNOWLEDGE (WIKIPEDIA) ---
    elif "wikipedia" in command or command.startswith("who is") or command.startswith("what is") or "tell me about" in command:
        speak(f"{get_random_reply('check')}Searching...")
        try:
            # Clean command for query
            query = command.replace("wikipedia", "").replace("who is", "").replace("what is", "").replace("tell me about", "").strip()
            if not query:
                speak("What should I search for?")
            else:
                results = wikipedia.summary(query, sentences=2)
                speak("According to Wikipedia")
                speak(results)
        except wikipedia.exceptions.DisambiguationError:
             speak("There are multiple results for that. Please be more specific.")
        except wikipedia.exceptions.PageError:
             speak("I couldn't find any information on that.")
        except Exception as e:
            speak("I encountered an error searching.")
            print(f"Wiki error: {e}")

    # --- APPS ---
    elif "open notepad" in command:
        speak(f"{get_random_reply('open')}Opening Notepad for you")
        try:
            os.startfile("notepad.exe")
        except:
             subprocess.Popen("notepad.exe")
    
    elif "close notepad" in command:
        speak(f"{get_random_reply('done')}Closing Notepad")
        os.system("taskkill /f /im notepad.exe")
             
    elif "open calculator" in command:
        speak(f"{get_random_reply('open')}Opening the calculator for you")
        try:
            os.startfile("calc.exe")
        except:
             subprocess.Popen("calc.exe")

    elif "open paint" in command:
        speak(f"{get_random_reply('open')}Opening Paint for you")
        try:
            os.startfile("mspaint.exe")
        except:
             subprocess.Popen("mspaint.exe")
             
    elif "close chrome" in command or "close google" in command or "close youtube" in command:
        speak(f"{get_random_reply('done')}Closing Chrome")
        os.system("taskkill /f /im chrome.exe")

    # --- SYSTEM ---
    elif "time" in command:
        strTime = datetime.datetime.now().strftime("%H:%M")
        speak(f"{get_random_reply('check')}The time is {strTime}")

    elif "date" in command:
        today = datetime.date.today().strftime("%B %d, %Y")
        speak(f"{get_random_reply('check')}Today is {today}")
        
    elif "battery" in command:
        battery = psutil.sensors_battery()
        speak(f"{get_random_reply('check')}Battery is at {battery.percent} percent")

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

    # --- VOLUME ---
    elif "volume up" in command or "increase volume" in command:
        speak("Increasing volume")
        pyautogui.press("volumeup")
        
    elif "volume down" in command or "decrease volume" in command:
        speak("Decreasing volume")
        pyautogui.press("volumedown")
        
    elif "mute" in command:
        speak("Muting volume")
        pyautogui.press("volumemute")

    elif "joke" in command:
        joke = pyjokes.get_joke()
        speak(joke)

    # --- FILE EXPLORER & SYSTEM PATHS ---
    elif "open file explorer" in command:
        speak("Opening File Explorer")
        subprocess.Popen("explorer")

    elif "open this pc" in command:
        speak("Opening This PC")
        subprocess.Popen("explorer shell:MyComputerFolder")

    elif "open documents folder" in command:
        speak("Opening Documents")
        subprocess.Popen("explorer shell:Personal")

    elif "open desktop folder" in command:
        speak("Opening Desktop")
        subprocess.Popen("explorer shell:Desktop")

    elif "search file" in command:
        query = command.replace("search file", "").strip()
        if query:
            threading.Thread(target=search_worker, args=(query, "file")).start()
        else:
            speak("What file should I search for?")

    elif "search folder" in command:
        query = command.replace("search folder", "").strip()
        if query:
            threading.Thread(target=search_worker, args=(query, "dir")).start()
        else:
             speak("What folder should I search for?")

    elif "open whatsapp" in command:
        speak("Opening WhatsApp")
        try:
            # Try opening via protocol (Windows Store App)
            os.startfile("whatsapp:")
        except Exception:
            speak("Could not open WhatsApp. Is it installed?")

    # --- FILE & FOLDER MANAGEMENT ---
    # --- FILE & FOLDER MANAGEMENT ---
    elif "create new folder" in command or "create a folder" in command or "create folder" in command:
        speak("What should I name the folder?")
        name = wait_for_input()
        if name:
            desktop = os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop")
            if not os.path.exists(desktop):
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                
            path = os.path.join(desktop, name)
            try:
                os.makedirs(path, exist_ok=False)
                speak(f"Folder {name} created on Desktop")
                subprocess.Popen(f'explorer "{path}"')
            except FileExistsError:
                speak(f"A folder named {name} already exists.")
            except Exception as e:
                speak("Failed to create folder.")
                print(e)
        else:
            speak("I didn't hear a name.")

    elif "delete folder" in command:
        speak("Which folder should I delete?")
        name = wait_for_input()
        if name:
            desktop = os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop")
            if not os.path.exists(desktop):
                 desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            
            path = os.path.join(desktop, name)
            if os.path.exists(path) and os.path.isdir(path):
                speak(f"Are you sure you want to permanently delete {name}? Say yes to confirm.")
                confirm = wait_for_input()
                if confirm and "yes" in confirm:
                    try:
                        shutil.rmtree(path)
                        speak(f"Folder {name} deleted.")
                    except Exception as e:
                        speak("Could not delete the folder.")
                        print(e)
                else:
                    speak("Deletion cancelled.")
            else:
                speak(f"I cannot find a folder named {name} on the Desktop.")
        else:
             speak("I didn't hear a folder name.")

    elif "create text file" in command or "create a file" in command or "create file" in command:
        speak("What should I name the file?")
        name = wait_for_input()
        if name:
            # Automatic .txt extension if not provided
            if not name.endswith(".txt"):
                name += ".txt"
            
            speak("What should I write in it?")
            content = wait_for_input() 
            
            desktop = os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop")
            if not os.path.exists(desktop):
                 desktop = os.path.join(os.path.expanduser("~"), "Desktop")

            path = os.path.join(desktop, name)
            try:
                with open(path, "w") as f:
                    if content:
                        f.write(content)
                speak(f"File {name} created.")
                os.startfile(path)
            except Exception as e:
                speak("Failed to create file.")
                print(e)
        else:
            speak("I didn't hear a filename.")

    elif "delete file" in command:
        speak("Which file should I delete?")
        name = wait_for_input()
        if name:
            desktop = os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop")
            if not os.path.exists(desktop):
                 desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                 
            # Try exact name, then with .txt
            path = os.path.join(desktop, name)
            if not os.path.exists(path):
                path = os.path.join(desktop, name + ".txt")
            
            if os.path.exists(path) and os.path.isfile(path):
                speak(f"Are you sure you want to delete {os.path.basename(path)}?")
                confirm = wait_for_input()
                if confirm and "yes" in confirm:
                    try:
                        os.remove(path)
                        speak("File deleted.")
                    except Exception as e:
                        speak("Could not delete the file.")
                        print(e)
                else:
                    speak("Deletion cancelled.")
            else:
                speak(f"I cannot find a file named {name} on the Desktop.")
        else:
             speak("I didn't hear a filename.")

    # --- VOICE NOTES ---
    elif "take a note" in command or "write a note" in command:
        speak("What should I write?")
        note = wait_for_input()
        if note:
            desktop = os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop")
            if not os.path.exists(desktop):
                 desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                 
            file_path = os.path.join(desktop, "notes.txt")
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            
            try:
                with open(file_path, "a") as f:
                    f.write(f"[{timestamp}] {note}\n")
                speak("Note saved.")
                subprocess.Popen(f'notepad "{file_path}"')
            except Exception as e:
                print(f"Note error: {e}")
                speak("I couldn't save the note.")
        else:
             speak("I didn't hear anything.")

    elif "read my last note" in command or "read note" in command:
        desktop = os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop")
        if not os.path.exists(desktop):
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                
        file_path = os.path.join(desktop, "notes.txt")
        if os.path.exists(file_path):
            try:
                with open(file_path, "r") as f:
                    lines = f.readlines()
                    if lines:
                        last_note = lines[-1]
                        # Try to strip timestamp for reading
                        # Format is [timestamp] content
                        if "]" in last_note:
                            content = last_note.split("]", 1)[1].strip()
                            speak(f"Your last note was: {content}")
                        else:
                            speak(f"Your last note was: {last_note}")
                    else:
                        speak("You don't have any notes yet.")
            except Exception as e:
                print(f"Read error: {e}")
                speak("I couldn't read the notes file.")
        else:
             speak("You don't have any notes yet.")

    # --- EXIT ---
    elif "exit" in command or "go to sleep" in command or "quit voice assistance" in command:
        speak("Going back to sleep")
        return True # Signal to sleep

    # --- FALLBACK ---
    else:
        speak("I didn't understand that command")

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
