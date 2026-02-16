import pyttsx3
import pyaudio
import json
import os
import sys
import threading
import queue
import time
import audioop
import numpy as np
from collections import deque
from vosk import Model, KaldiRecognizer

# ================= CONFIG =================
VOSK_MODEL_PATH = "vosk-model-small-en-us-0.15"
SAMPLE_RATE = 16000
BUFFER_SIZE = 4000
CALIBRATION_TIME = 10   # 10 seconds (3s noise, 7s voice)
NOISE_MARGIN = 200      # Margin above ambient
MIC_NAME_SUBSTRING = "Microphone Array"

def auto_detect_mic():
    p = pyaudio.PyAudio()
    best_index = None

    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        name = info.get("name", "").lower()

        if info.get("maxInputChannels", 0) > 0:
            # Priority order
            if "headphone" in name or "earphone" in name:
                return i
            if "microphone array" in name:
                best_index = i
            # If no better match, keep scanning.
            # If nothing found, return None (uses default)
            
    return best_index if best_index is not None else None

# =========================================

# =========================================


class VoiceEngine:
    def __init__(self, model_path=VOSK_MODEL_PATH):
        # -------- STATE --------
        self.is_speaking = False
        self.speech_queue = queue.Queue()
        
        # Audio Config (Set by Calibration)
        self.device_index = auto_detect_mic()
        self.noise_floor = 300
        self.gain = 1.0
        
        print(f"🎧 Using mic device index: {self.device_index}")

        # -------- TTS THREAD --------
        threading.Thread(target=self._speech_worker, daemon=True).start()

        # -------- STT --------
        self.model_path = model_path
        self._setup_vosk()

    # ================= VOSK SETUP =================
    def _setup_vosk(self):
        try:
            if os.path.exists(self.model_path):
                self.model = Model(self.model_path)
                print(f"✅ Loaded local Vosk model: {self.model_path}")
            else:
                print(f"⚠️ Model '{self.model_path}' not found. Downloading/Loading default 'en-us'...")
                self.model = Model(lang="en-us")

            self.recognizer = KaldiRecognizer(self.model, SAMPLE_RATE)
            self.recognizer.SetWords(True)

            print("✅ Vosk model loaded")

        except Exception as e:
            print(f"❌ Vosk init failed: {e}")
            sys.exit(1)

    # ================= TTS =================
    def speak(self, text):
        print(f"Assistant: {text}")
        self.speech_queue.put(text)

    def _speech_worker(self):
        try:
            tts = pyttsx3.init("sapi5")
            tts.setProperty("rate", 170)
        except Exception as e:
            print(f"❌ TTS init error: {e}")
            return

        while True:
            text = self.speech_queue.get()
            if text is None:
                break

            self.is_speaking = True
            try:
                tts.say(text)
                tts.runAndWait()
            except Exception as e:
                print(f"❌ TTS error: {e}")
            finally:
                self.is_speaking = False
                self.speech_queue.task_done()

    # ================= CALIBRATION =================
    def calibrate_microphone(self, stream):
        print("🎙️ 10-second microphone calibration started")
        print("👉 Stay silent for 3 seconds, then speak normally for 7 seconds.")
        
        noise_samples = []
        voice_samples = []

        start_time = time.time()

        while time.time() - start_time < CALIBRATION_TIME:
            data = stream.read(BUFFER_SIZE, exception_on_overflow=False)
            rms = audioop.rms(data, 2)

            elapsed = time.time() - start_time

            # First 3 sec → ambient noise
            if elapsed < 3:
                noise_samples.append(rms)
            # Next 7 sec → user voice
            else:
                voice_samples.append(rms)

        avg_noise = sum(noise_samples) / len(noise_samples) if noise_samples else 300
        avg_voice = sum(voice_samples) / len(voice_samples) if voice_samples else 1000

        # 🎯 Final calibrated values
        self.noise_floor = avg_noise + NOISE_MARGIN
        self.gain = min(max(avg_voice / 1200, 1.5), 3.0)

        print(f"✅ Noise floor set to: {int(self.noise_floor)}")
        print(f"✅ Mic gain set to: {round(self.gain, 2)}")
        print("🎉 Calibration complete")

    # ================= LISTENING =================
    def listen_continuous(self, callback):
        """
        Continuous offline listener with "Talk -> Stop -> Process -> Continue" flow.
        1. Listen for voice.
        2. Record until silence (Vosk's endpointing).
        3. Call callback(text) with the full utterance.
        4. Wait for callback to finish (and any TTS it triggers).
        5. Resume listening for the next command.
        """

        p = pyaudio.PyAudio()
        stream = None

        try:
            # 1. Setup Stream
            kwargs = {
                "format": pyaudio.paInt16,
                "channels": 1,
                "rate": SAMPLE_RATE,
                "input": True,
                "frames_per_buffer": BUFFER_SIZE
            }
            
            # Select Device
            mic_index = None
            if MIC_NAME_SUBSTRING:
                mic_index = self._find_device_index(MIC_NAME_SUBSTRING, "input")
            
            if mic_index is not None:
                stream = p.open(**kwargs, input_device_index=mic_index)
                print(f"🎤 Listening on Device Index {mic_index}...")
            else:
                 # Fallback to default device
                 stream = p.open(**kwargs)
                 print("🎤 Listening on Default Device...")

            stream.start_stream()
            
            # 🔥 10-second Calibration (Once on startup)
            self.calibrate_microphone(stream)

        except Exception as e:
            print(f"❌ Audio stream error: {e}")
            if stream:
                stream.stop_stream()
                stream.close()
            p.terminate()
            return

        print("🟢 Ready. Speak now.")
        
        while True:
            # A. WAIT LOOP: Don't record if Speaking
            # The loop will naturally wait here if self.is_speaking is True (e.g., during TTS).
            if self.is_speaking:
                time.sleep(0.1) # Small delay to prevent busy-waiting
                continue

            try:
                # B. READ AUDIO
                # read exception_on_overflow=False to prevent crashes if we processed for too long
                raw_data = stream.read(BUFFER_SIZE, exception_on_overflow=False)

                # C. SIGNAL PROCESSING (Gated)
                # 1. RMS Check
                rms = audioop.rms(raw_data, 2)
                
                # 2. Apply Calibrated Gain
                audio = np.frombuffer(raw_data, dtype=np.int16)
                audio = np.clip(audio * self.gain, -32768, 32767).astype(np.int16)
                data = audio.tobytes()

                # D. VOSK RECOGNITION
                # AcceptWaveform returns True when it detects end of utterance (Silence after speech)
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    text = result.get("text", "").strip()

                    if text:
                        print(f"🧠 Heard: {text} (RMS: {rms})")
                        
                        # ✋ PROCESS COMMAND
                        # The callback is synchronous, so this thread waits for it to complete.
                        callback(text, False)
                        
                        # 3. Post-Task Behavior
                        # If the callback triggered TTS, the `is_speaking` flag will be True,
                        # and the loop will pause at the top until TTS finishes.
                        
                        print("🟡 Ready for next command...")

            except Exception as e:
                print(f"❌ Listen error: {e}")
                time.sleep(0.1)

    def _find_device_index(self, name_substring, device_type="input"):
        """
        Scans devices and returns the index of the first match.
        device_type: 'input' or 'output'
        """
        p = pyaudio.PyAudio()
        info = p.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')
        
        print(f"🔍 Scanning {num_devices} audio devices for '{name_substring}'...")
        
        for i in range(num_devices):
            device_info = p.get_device_info_by_host_api_device_index(0, i)
            device_name = device_info.get('name')
            max_input = device_info.get('maxInputChannels')
            max_output = device_info.get('maxOutputChannels')
            
            # Filter by type
            if device_type == "input" and max_input <= 0: continue
            if device_type == "output" and max_output <= 0: continue
            
            # Check name match
            if name_substring.lower() in device_name.lower():
                print(f"✅ Found Device: {device_name} (Index {i})")
                return i
                
        print(f"⚠️ Device '{name_substring}' not found. Using Default.")
        return None
