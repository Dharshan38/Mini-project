from abc import ABC, abstractmethod

class Skill(ABC):
    @property
    @abstractmethod
    def name(self):
        """Unique name for the skill"""
        pass
        
    @property
    @abstractmethod
    def intents(self):
        """List of intents this skill handles"""
        pass
        
    @abstractmethod
    def handle_intent(self, intent_name, entities, context=None):
        """Execute logic based on intent"""
        pass
