import tkinter as tk
import threading
import time
import json
import datetime
import subprocess
import psutil
import pyttsx3
import pyaudio
from vosk import Model, KaldiRecognizer
import speech_recognition as sr

# ---------------- VOICE ENGINE ----------------
engine = pyttsx3.init("sapi5")
engine.setProperty("rate", 170)

def speak(text):
    engine.say(text)
    engine.runAndWait()

# ---------------- ASSISTANT STATE ----------------
STATE = "SLEEPING"  # SLEEPING | LISTENING

# ---------------- GUI ----------------
root = tk.Tk()
root.title("Desktop Assistant")
root.geometry("300x400")
root.resizable(False, False)
root.configure(bg="black")

canvas = tk.Canvas(root, width=300, height=300, bg="black", highlightthickness=0)
canvas.pack()

status_label = tk.Label(
    root, text="Sleeping... Say 'Hey Jarvis'",
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

# ---------------- OFFLINE WAKE WORD ----------------
model = Model("vosk-model-small-en-us-0.15/vosk-model-small-en-us-0.15")
rec = KaldiRecognizer(model, 16000)

def wake_word_listener():
    global STATE

    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=16000,
        input=True,
        frames_per_buffer=8000
    )
    stream.start_stream()

    while True:
        data = stream.read(4000, exception_on_overflow=False)
        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            text = result.get("text", "")
            if "hey jarvis" in text:
                STATE = "LISTENING"
                status_label.config(text="Listening...")
                speak("Yes, I am listening")
                listen_command()
                STATE = "SLEEPING"
                status_label.config(text="Sleeping... Say 'Hey Jarvis'")

# ---------------- COMMAND LISTENER ----------------
def listen_command():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        audio = r.listen(source, phrase_time_limit=5)
    try:
        command = r.recognize_google(audio).lower()

        if "time" in command:
            speak(datetime.datetime.now().strftime("Time is %H:%M"))

        elif "open notepad" in command:
            subprocess.Popen("notepad.exe")
            speak("Opening notepad")

        elif "battery" in command:
            battery = psutil.sensors_battery()
            speak(f"Battery is at {battery.percent} percent")

        elif "exit" in command:
            speak("Going back to sleep")

        else:
            speak("Command not recognized")

    except:
        speak("I didn't understand")

# ---------------- START THREADS ----------------
threading.Thread(target=wake_word_listener, daemon=True).start()
animate()
root.mainloop()



