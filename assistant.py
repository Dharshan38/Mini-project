from voice_engine import VoiceEngine
from nlu_engine import NLUEngine
from skills.registry import SkillRegistry
from skills.app_skill import AppSkill
from skills.web_skill import WebSkill
from skills.system_skill import SystemSkill

import tkinter as tk
import threading
import time

class Assistant:
    def __init__(self):
        # 1. Init NLP
        self.nlu = NLUEngine("en_core_web_sm")
        
        # 2. Init Skills
        self.registry = SkillRegistry()
        self.registry.register_skill(AppSkill())
        self.registry.register_skill(WebSkill())
        self.registry.register_skill(SystemSkill())
        
        # 3. Init Voice
        self.voice = VoiceEngine()
        
        # 4. State
        self.is_listening = True
        self.last_command = ""
        
        # 5. GUI Setup (must be in main thread usually)
        self.setup_gui()
        
        # 6. Start Listener Thread
        threading.Thread(target=self.voice.listen_continuous, args=(self.on_speech_detected,), daemon=True).start()

    def setup_gui(self):
        self.root = tk.Tk()
        self.root.title("AI Assistant")
        self.root.geometry("300x400")
        self.root.configure(bg="black")
        
        self.canvas = tk.Canvas(self.root, width=300, height=300, bg="black", highlightthickness=0)
        self.canvas.pack()
        
        self.status_label = tk.Label(self.root, text="Listening...", fg="white", bg="black", font=("Arial", 12))
        self.status_label.pack(pady=10)
        
        self.circle = self.canvas.create_oval(120, 120, 180, 180, fill="blue")
        self.pulse_size = 0
        self.pulse_dir = 1
        
        self.animate_gui()

    def animate_gui(self):
        if self.is_listening:
            self.pulse_size += self.pulse_dir * 2
            if self.pulse_size > 20 or self.pulse_size < 0:
                self.pulse_dir *= -1
            
            fill = "green" if self.last_command else "blue"
            if self.voice.is_speaking: fill = "purple"
            
            self.canvas.itemconfig(self.circle, fill=fill)
            self.canvas.coords(
                self.circle,
                120 - self.pulse_size,
                120 - self.pulse_size,
                180 + self.pulse_size,
                180 + self.pulse_size
            )
        
        self.root.after(50, self.animate_gui)

    def queue_process_command(self, text):
        self.status_label.config(text=f"Heard: {text}")
        self.last_command = text
        
        # Optional: Wake word check
        if "bell" in text or "hey bell" in text:
             # Just process command if wake word is part of it?
             # Or treat all speech as command if active?
             # Let's clean the wake word out
             text = text.replace("hey bell", "").replace("bell", "").strip()
             if not text:
                 self.voice.speak("Yes?")
                 return
        
        # Process command
        self.process_command(text)
        
        # Reset last command visual after a bit
        threading.Timer(2.0, lambda: setattr(self, 'last_command', "")).start()

    def on_speech_detected(self, text, is_partial):
        if is_partial: return
        print(f"Heard: {text}")
        
        # Schedule GUI update on main thread
        self.root.after(0, self.queue_process_command, text)

    def process_command(self, text):
        intent, entities, confidence = self.nlu.parse(text)
        print(f"Intent: {intent} ({confidence}), Entities: {entities}")
        
        if confidence < 0.6:
            self.voice.speak("I didn't quite catch that.")
            return

        skill = self.registry.get_skill_for_intent(intent)
        if skill:
            response = skill.handle_intent(intent, entities)
            if response:
                self.voice.speak(response)
        else:
            self.voice.speak("I'm not sure how to help with that yet.")

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = Assistant()
    app.run()
