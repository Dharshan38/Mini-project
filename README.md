# Offline Intent-Based AI Assistant

A Python-based AI voice assistant refactored for flexibility, offline capabilities, and intent-driven architecture.

## 🚀 Key Features

*   **Offline-First**: Uses **Vosk** for Speech-to-Text and **pyttsx3** for Text-to-Speech. No internet required for core operation.
*   **Intent-Based NLU**: Uses **spaCy** for dependency parsing and entity extraction. Understands natural language phrasing (e.g., "Launch Chrome please" vs "Open Chrome").
*   **Skill-Based Architecture**: Modular design where new capabilities can be added as simple Python files in the `skills/` directory.
*   **Dynamic App Resolution**: Recognizes apps via a configuration file (`config/apps.json`), allowing new apps to be added without code changes.
*   **Zero-Shot Friendly**: Capable of parsing unseen commands by leveraging linguistic structure (Verb-Object relationships) rather than strict keyword matching.

## 📂 Architecture

*   **`assistant.py`**: The entry point. Manages the GUI, threads, and orchestrates NLU, Voice, and Skills.
*   **`nlu_engine.py`**: The "brain". Uses spaCy to convert raw text into Intents (what user wants) and Entities (parameters).
*   **`voice_engine.py`**: Handles audio input/output. Runs VOSK and TTS in separate threads to keep the UI responsive.
*   **`skills/`**:
    *   `base_skill.py`: Abstract base class for all skills.
    *   `registry.py`: Dynamically loads skills at runtime.
    *   `app_skill.py`: Handles opening/closing applications.
    *   `web_skill.py`: Search and media playback.
    *   `system_skill.py`: Volume, shutdown, file operations.
*   **`config/`**:
    *   `apps.json`: Maps app names (and aliases like "browser") to executable files.

## 🛠️ Setup & Usage

1.  **Install Expectations**:
    ```bash
    pip install -r requirements.txt
    python -m spacy download en_core_web_sm
    ```
2.  **Run**:
    ```bash
    python assistant.py
    ```
    *Note: The first run may download the Vosk model automatically.*

## 🧩 Adding New Skills

To add a new capability (e.g., specific home automation):

1.  Create a file `skills/home_skill.py`.
2.  Inherit from `Skill` and define valid intents.
3.  Implement `handle_intent`.
4.  The `registry` will automatically pick it up on next restart!

## 🤖 Why This Scales

Unlike simple `if "text" in command:` scripts, this architecture decouples **Understanding** (NLU) from **Action** (Skills). Adding a new way to phrase a command ("Start up the browser") works instantly because the NLU engine understands "Start up" is a verb similar to "Open".