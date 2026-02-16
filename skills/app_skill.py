from skills.base_skill import Skill
import webbrowser
import os
import subprocess
import json

class AppSkill(Skill):
    def __init__(self):
        self._name = "App Skill"
        self._intents = ["open_app", "close_app"]
        self.config_path = os.path.join(os.path.dirname(__file__), "..", "config", "apps.json")
        self.app_map = self._load_map()

    def _load_map(self):
        # Default map
        default = {
            "chrome": ["chrome", "browser", "google chrome"],
            "notepad": ["notepad", "text editor"],
            "calculator": ["calculator", "calc"],
            "paint": ["paint", "mspaint"]
        }
        try:
            with open(self.config_path, "r") as f:
                return json.load(f)
        except Exception:
            return default

    @property
    def name(self):
        return self._name

    @property
    def intents(self):
        return self._intents
        
    def _find_executable(self, requested_app):
        # Try exact match in map first
        requested_app = requested_app.lower()
        
        target_exec = None
        
        for exec_name, aliases in self.app_map.items():
            if requested_app in aliases or requested_app == exec_name:
                target_exec = exec_name
                break
        
        # If not in map, just try launching the name directly
        if not target_exec:
             target_exec = requested_app
             
        # Normalize executable name for Windows
        if not target_exec.endswith(".exe"):
             # Many common apps are just name.exe
             pass 
             
        return target_exec

    def handle_intent(self, intent_name, entities, context=None):
        app_name = entities.get("app_name", "").lower()
        if not app_name:
             # Look for direct match in text
             # ... simplified, assume entity extraction worked
             return "I didn't catch which app to open."

        target = self._find_executable(app_name)
        
        if intent_name == "open_app":
            if target == "chrome":
                 webbrowser.open("http://google.com")
                 return f"Opening {target}."
            
            # Generic launch
            try:
                # Try simple command first
                # Check different common paths?
                # Actually os.startfile is best on Windows for recognized apps
                try:
                    os.startfile(target)
                except OSError:
                    # try adding .exe
                    os.startfile(target + ".exe")
                    
                return f"Opening {app_name}."
            except Exception as e:
                return f"I couldn't find {app_name} on your system."
                
        elif intent_name == "close_app":
            # taskkill
            try:
                # If target is generic name, try to kill process
                # create image name
                image = target if target.endswith(".exe") else target + ".exe"
                os.system(f"taskkill /f /im {image}")
                return f"Closing {app_name}."
            except Exception:
                return f"I couldn't close {app_name}."

        return "I'm not sure how to handle that app command."
