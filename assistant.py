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
import zipfile
import urllib.request
import re
from AppOpener import open as open_app, close as close_app

# ---------------- CONFIGURATION ----------------
WAKE_WORD = "hey bell"

def get_vosk_model():
    model_name = "vosk-model-small-en-us-0.15"
    # Check if model exists in current directory
    model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), model_name)
    
    if not os.path.exists(model_path):
        print(f"Model '{model_name}' not found. Downloading...")
        url = f"https://alphacephei.com/vosk/models/{model_name}.zip"
        zip_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{model_name}.zip")
        try:
            urllib.request.urlretrieve(url, zip_path)
            print("Download complete. Extracting...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(os.path.dirname(os.path.abspath(__file__)))
            print("Extraction complete.")
            os.remove(zip_path)
        except Exception as e:
            print(f"Failed to download/extract model: {e}")
            sys.exit(1)
            
    return model_path

VOSK_MODEL_PATH = get_vosk_model()

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
            print("Waiting for detail input (speak now)...")
            # Increased timeouts significantly so user doesn't get cut off
            audio = recognizer_obj.listen(source, timeout=10, phrase_time_limit=10)
        
        text = recognizer_obj.recognize_google(audio).lower()
        print(f"Captured: {text}")
        return text
    except sr.WaitTimeoutError:
        print("Input timeout - no speech detected.")
        return None
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

def play_on_youtube(query, browser_pref="default"):
    """Custom function to play video in specific browser"""
    try:
        # Search for video ID
        search_query = query.replace(' ', '+')
        html = urllib.request.urlopen("https://www.youtube.com/results?search_query=" + search_query)
        video_ids = re.findall(r"watch\?v=(\S{11})", html.read().decode())
        
        target_url = ""
        if video_ids:
            target_url = "https://www.youtube.com/watch?v=" + video_ids[0]
        else:
            target_url = f"https://www.youtube.com/results?search_query={query}"
            
        print(f"Target URL: {target_url} | Browser: {browser_pref}")
        
        # Browser selection
        if browser_pref and "brave" in browser_pref.lower():
            try:
                brave_path = r"C:\Users\savio\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe"
                if os.path.exists(brave_path):
                     subprocess.Popen([brave_path, target_url])
                else:
                     speak("Brave not found, using default.")
                     webbrowser.open(target_url)
            except Exception as e:
                print(f"Brave error: {e}")
                webbrowser.open(target_url)
                    
        elif browser_pref and ("chrome" in browser_pref.lower() or "google" in browser_pref.lower()):
            try:
                 # Try common chrome paths
                 paths = [
                    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
                 ]
                 found = False
                 for p in paths:
                     if os.path.exists(p):
                         subprocess.Popen([p, target_url])
                         found = True
                         break
                 if not found:
                     # Try blindly
                     subprocess.Popen(f'start chrome "{target_url}"', shell=True)
            except Exception as e:
                 print(f"Chrome error: {e}")
                 webbrowser.open(target_url)
                 
        else:
            # Default behavior
            webbrowser.open(target_url)
            
    except Exception as e:
        print(f"Play error: {e}")
        webbrowser.open(f"https://www.youtube.com/results?search_query={query}")

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

    elif "play" in command:
        query = command.replace("play", "").replace("on youtube", "").replace("youtube", "").strip()
        if query:
            speak(f"Which browser should I use? Chrome or Brave?")
            # Wait for user response
            browser_choice = wait_for_input()
            
            if browser_choice:
                speak(f"{get_random_reply('open')}Playing {query} on {browser_choice}")
                play_on_youtube(query, browser_choice)
            else:
                speak("I didn't hear a choice, using default browser.")
                play_on_youtube(query, "default")
        else:
            speak("What should I play?")

    elif "open chrome" in command or "open google" in command:
        speak(f"{get_random_reply('open')}Opening Chrome")
        try:
             os.startfile("chrome.exe")
        except:
             speak("Could not locate Chrome.")
             
    elif "open brave" in command:
         speak(f"{get_random_reply('open')}Opening Brave")
         try:
             path = r"C:\Users\savio\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe"
             os.startfile(path)
         except:
             speak("Could not find Brave browser.") 

    elif "open" in command:
        app_name = command.replace("open ", "").strip()
        speak(f"{get_random_reply('open')}Opening {app_name}")
        try:
            open_app(app_name, match_closest=True, output=False) # Requires AppOpener library
        except:
             speak(f"I couldn't find an app named {app_name}")

    elif "close" in command:
        app_name = command.replace("close ", "").strip()
        speak(f"{get_random_reply('done')}Closing {app_name}")
        try:
            close_app(app_name, match_closest=True, output=False)
        except:
             speak(f"Could not close {app_name}")

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
        # Fallback to general search (Alexa-like behavior)
        speak("I'm not sure about that command, let me look it up for you.")
        pywhatkit.search(command) # Uses Google Search
        speak("Here is what I found on the web.")

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
recognizer_obj.pause_threshold = 2.0 # Increased to allow for pauses in speech

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
        full_command = recognizer_obj.recognize_google(audio).lower()
        print(f"You said: {full_command}")
        
        # Split chained commands
        # extended keywords list for splitting
        splitters = [" and ", " then ", " also ", " after that "]
        commands = [full_command]
        
        for splitter in splitters:
            new_commands = []
            for cmd in commands:
                new_commands.extend(cmd.split(splitter))
            commands = new_commands
            
        # Execute each sub-command
        should_sleep = False
        for cmd in commands:
            cmd = cmd.strip()
            if cmd:
                print(f"Processing sub-command: {cmd}")
                if process_command(cmd):
                    should_sleep = True
                # Small delay between commands to let actions complete/animations finish
                time.sleep(1)
        
        return should_sleep

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
