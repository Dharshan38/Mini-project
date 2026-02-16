import importlib
import os
import inspect
from skills.base_skill import Skill

class SkillRegistry:
    def __init__(self):
        self.skills = []
        self.intent_map = {} # intent_name -> skill_instance

    def load_skills(self, skills_dir=None):
        if not skills_dir:
            skills_dir = os.path.dirname(__file__)
        
        print(f"Loading skills from {skills_dir}...")
        
        # Iterate over files in the directory
        for filename in os.listdir(skills_dir):
            if filename.endswith(".py") and filename != "base_skill.py" and filename != "registry.py":
                module_name = filename[:-3]
                try:
                    # Import module
                    module = importlib.import_module(f"skills.{module_name}")
                    
                    # Find Skill subclasses
                    for name, obj in inspect.getmembers(module):
                        if inspect.isclass(obj) and issubclass(obj, Skill) and obj is not Skill:
                            skill_instance = obj()
                            self.register_skill(skill_instance)
                            print(f"Registered skill: {skill_instance.name}")
                except Exception as e:
                    print(f"Error loading skill {filename}: {e}")

    def register_skill(self, skill: Skill):
        self.skills.append(skill)
        for intent in skill.intents:
            self.intent_map[intent] = skill

    def get_skill_for_intent(self, intent_name):
        return self.intent_map.get(intent_name)
