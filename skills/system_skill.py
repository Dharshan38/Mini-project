from skills.base_skill import Skill
import os
import shutil
import pyautogui

class SystemSkill(Skill):
    def __init__(self):
        self._name = "System Skill"
        self._intents = ["system_control", "file_operation", "conversation"]

    @property
    def name(self):
        return self._name

    @property
    def intents(self):
        return self._intents
        
    def handle_intent(self, intent_name, entities, context=None):
        if intent_name == "system_control":
            action = entities.get("action", "")
            if action == "volume_up":
                pyautogui.press("volumeup")
                return "Turning volume up."
            elif action == "volume_down":
                pyautogui.press("volumedown")
                return "Turning volume down."
            elif action == "mute":
                pyautogui.press("volumemute")
                return "Muted."
            elif action == "shutdown":
                os.system("shutdown /s /t 60")
                return "Shutting down in 60 seconds."
            elif action == "restart":
                os.system("shutdown /r /t 60")
                return "Restarting in 60 seconds."
            elif action == "time":
                from datetime import datetime
                return f"It is currently {datetime.now().strftime('%I:%M %p')}."
            elif action == "date":
                from datetime import datetime
                return f"Today is {datetime.now().strftime('%A, %B %d')}."
            return "Unable to perform system action."
            
        elif intent_name == "file_operation":
            action = entities.get("action", "")
            target = entities.get("target", "New Folder") # default name
            # default location: desktop
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            
            if action == "create_folder":
                try:
                    path = os.path.join(desktop, target)
                    os.makedirs(path, exist_ok=True)
                    return f"Created folder {target} on Desktop."
                except Exception as e:
                    return f"Failed to create folder: {str(e)}"
            elif action == "delete_folder":
                # Safety check?
                # ...
                try:
                    path = os.path.join(desktop, target)
                    if os.path.exists(path):
                        # Move to trash ideally, but shutil.rmtree is permanent
                        # os.rmdir only works if empty
                        # Let's just say "I can't delete permanently for safety"
                        return f"I cannot delete folders for safety reasons yet."
                    else:
                        return f"Folder {target} not found."
                except Exception:
                    pass
            elif action == "create_file":
                # ...
                pass
            return "File operation not fully supported."

        elif intent_name == "conversation":
            ctype = entities.get("type", "")
            if ctype == "greeting":
                return "Hello! I am your AI assistant."
            elif ctype == "joke":
                import pyjokes
                return pyjokes.get_joke()
            elif ctype == "whoami":
                return "I am a Python-based AI assistant refactored for flexibility."
            return "I am listening."

        return "I didn't understand that command."
