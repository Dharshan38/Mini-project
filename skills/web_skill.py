from skills.base_skill import Skill
import webbrowser
import os

class WebSkill(Skill):
    def __init__(self):
        self._name = "Web Skill"
        self._intents = ["search_web", "play_media"]

    @property
    def name(self):
        return self._name

    @property
    def intents(self):
        return self._intents

    def handle_intent(self, intent_name, entities, context=None):
        if intent_name == "search_web":
            query = entities.get("query", "")
            if not query:
                return "What should I search for?"
            
            # Simple google search
            url = f"https://www.google.com/search?q={query}"
            webbrowser.open(url)
            return f"Opening search results for {query}."
        
        elif intent_name == "play_media":
            query = entities.get("query", "")
            platform = entities.get("platform", "youtube")
            
            if platform == "spotify":
                # Implement Spotify search
                pass
            
            # Default to Youtube
            if not query:
                 return "What should I play?"
                 
            try:
                import pywhatkit
                pywhatkit.playonyt(query)
                return f"Playing {query} on YouTube."
            except ImportError:
                # Fallback to web search
                url = f"https://www.youtube.com/results?search_query={query}"
                webbrowser.open(url)
                return f"Opening YouTube for {query}."

        return "I can't do that web action yet."
