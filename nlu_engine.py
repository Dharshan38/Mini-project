import spacy
from spacy.matcher import Matcher, PhraseMatcher
import json
import os

class NLUEngine:
    def __init__(self, model_name="en_core_web_sm"):
        try:
            self.nlp = spacy.load(model_name)
        except OSError:
            print(f"Downloading {model_name}...")
            from spacy.cli import download
            download(model_name)
            self.nlp = spacy.load(model_name)
            
        self.matcher = Matcher(self.nlp.vocab)
        self.define_patterns()
        
    def define_patterns(self):
        # Open App: open/start/launch + [app_name]
        # Using dependency parsing logic + simple keyword lists as backup
        pass

    def parse(self, text):
        doc = self.nlp(text.lower())
        intent = "unknown"
        entities = {}
        confidence = 0.0

        print(f"DEBUG: Processing '{text}'")
        for token in doc:
            print(f"  {token.text} -> {token.lemma_} ({token.pos_}, {token.dep_})")
        
        # Rule-based Intent Classification using Dependency Parsing
        # 1. Open App
        # Looking for verbs: open, start, launch, run
        root = [token for token in doc if token.dep_ == "ROOT"]
        if root:
            root = root[0]
            lemma = root.lemma_
            
            # --- APP CONTROL ---
            if lemma in ["open", "start", "launch", "run"]:
                intent = "open_app"
                # Find direct object
                dobj = [child for child in root.children if child.dep_ in ("dobj", "attr", "acomp")]
                if dobj:
                    app_name = dobj[0].text
                    # Check for compound nouns e.g. "google chrome"
                    compounds = [c for c in dobj[0].children if c.dep_ == "compound"]
                    if compounds:
                        app_name = f"{compounds[0].text} {app_name}"
                    entities["app_name"] = app_name
                    confidence = 0.9
                else:
                    # Fallback: maybe just "notepad" if "open notepad" (sometimes parse tree differs)
                    # Use app config list check
                    pass

            elif lemma in ["close", "exit", "quit", "stop", "terminate", "kill"]:
                intent = "close_app"
                dobj = [child for child in root.children if child.dep_ in ("dobj", "attr")]
                if dobj:
                    app_name = dobj[0].text
                    compounds = [c for c in dobj[0].children if c.dep_ == "compound"]
                    if compounds:
                        app_name = f"{compounds[0].text} {app_name}"
                    entities["app_name"] = app_name
                    confidence = 0.9

            # --- WEB SEARCH ---
            elif lemma in ["search", "find", "google", "look"]:
                intent = "search_web"
                # "search for x" -> prep 'for' -> pobj 'x'
                # "google x" -> dobj 'x'
                
                query_parts = []
                for child in root.children:
                    if child.dep_ == "dobj":
                        query_parts.append(child.text)
                        # Add subtree
                        query_parts.extend([t.text for t in child.subtree if t != child])
                    elif child.dep_ == "prep" and child.text == "for":
                        for pobj in child.children:
                            if pobj.dep_ == "pobj":
                                query_parts.append(pobj.text)
                                query_parts.extend([t.text for t in pobj.subtree if t != pobj])
                                
                if query_parts:
                    entities["query"] = " ".join(query_parts)
                    confidence = 0.85
                elif "search" in text or "google" in text:
                     # Fallback regex-like
                     if "search for" in text:
                         entities["query"] = text.split("search for", 1)[1].strip()
                     elif "google" in text:
                         entities["query"] = text.split("google", 1)[1].strip()
                     intent = "search_web"
                     confidence = 0.7

            # --- MEDIA ---
            elif lemma in ["play"]:
                intent = "play_media"
                # play x on youtube
                query = ""
                platform = "youtube" # default
                
                dobj = [child for child in root.children if child.dep_ == "dobj"]
                if dobj:
                    query = " ".join([t.text for t in dobj[0].subtree])
                
                # Check for "on platform"
                prep = [child for child in root.children if child.dep_ == "prep" and child.text == "on"]
                if prep:
                    pobj = [child for child in prep[0].children if child.dep_ == "pobj"]
                    if pobj:
                        platform = pobj[0].text
                        # remove platform from query if present (unlikely with subtree logic but good to double check)
                
                entities["query"] = query
                entities["platform"] = platform
                confidence = 0.9

            # --- SYSTEM ---
            elif lemma in ["turn", "increase", "decrease", "set", "mute", "unmute"]:
                 if "volume" in text:
                     intent = "system_control"
                     if lemma in ["increase", "raise"] or "up" in text:
                         entities["action"] = "volume_up"
                     elif lemma in ["decrease", "lower"] or "down" in text:
                         entities["action"] = "volume_down"
                     elif lemma in ["mute", "silence"]:
                         entities["action"] = "mute"
                     confidence = 0.9
            
            elif lemma in ["shutdown", "restart", "reboot"]:
                 intent = "system_control"
                 entities["action"] = lemma
                 confidence = 0.95
                 
            # --- FILE OPS ---
            elif lemma in ["create", "make", "generate"]:
                # create a folder named x
                if "folder" in text or "directory" in text:
                    intent = "file_operation"
                    entities["action"] = "create_folder"
                elif "file" in text:
                    intent = "file_operation"
                    entities["action"] = "create_file"
                
                # Extract name? "named X", "called X"
                # This matches "named" as generic parsing
                # Actually let's look for "named" child
                # ... simplified for now
                if "named" in text:
                     entities["target"] = text.split("named", 1)[1].strip()
                confidence = 0.8
            
            elif lemma in ["delete", "remove", "erase"]:
                intent = "file_operation"
                if "folder" in text:
                    entities["action"] = "delete_folder"
                else:
                    entities["action"] = "delete_file"
                pass 
                
        # Secondary check: Phrase matching for greetings
        if intent == "unknown":
            if any(w in text for w in ["hello", "hi", "hey", "greetings"]):
                intent = "conversation"
                entities["type"] = "greeting"
                confidence = 0.9
            elif "time" in text:
                intent = "system_control"
                entities["action"] = "time"
                confidence = 0.9
            elif "date" in text:
                intent = "system_control"
                entities["action"] = "date"
                confidence = 0.9
            elif "joke" in text:
                intent = "conversation"
                entities["type"] = "joke"
                confidence = 0.9
            elif "who are you" in text:
                intent = "conversation"
                entities["type"] = "whoami"
                confidence = 0.95

        return intent, entities, confidence
