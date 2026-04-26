import io
import os
import sys
import time
import wave
import subprocess
import threading

import sounddevice as sd
import numpy as np
import speech_recognition as sr

SAMPLE_RATE = 16000
CHUNK_SECONDS = 3
WAKE_WORDS = ["wake up", "wake", "hey jarvis", "hello jarvis", "jarvis"]
JARVIS_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_SCRIPT = os.path.join(JARVIS_DIR, "main.py")

recognizer = sr.Recognizer()
_jarvis_process = None


def is_jarvis_running():
    global _jarvis_process
    return _jarvis_process is not None and _jarvis_process.poll() is None


def launch_jarvis():
    global _jarvis_process
    print("[Wakeup] Wake word detected! Launching Jarvis...")
    _jarvis_process = subprocess.Popen(
        [sys.executable, MAIN_SCRIPT],
        cwd=JARVIS_DIR,
    )


def record_chunk():
    frames = int(CHUNK_SECONDS * SAMPLE_RATE)
    audio = sd.rec(frames, samplerate=SAMPLE_RATE, channels=1, dtype="int16")
    sd.wait()
    return audio


def to_wav_bytes(audio_np):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio_np.tobytes())
    buf.seek(0)
    return buf.read()


def transcribe(wav_bytes):
    audio_data = sr.AudioData(wav_bytes, SAMPLE_RATE, 2)
    try:
        return recognizer.recognize_google(audio_data).lower()
    except sr.UnknownValueError:
        return ""
    except sr.RequestError:
        return ""


def listen_loop():
    print("[Wakeup] Listening for 'wake up'...")
    while True:
        try:
            audio = record_chunk()
            wav = to_wav_bytes(audio)
            text = transcribe(wav)
            if text:
                print(f"[Wakeup] Heard: {text}")
            if any(w in text for w in WAKE_WORDS):
                if not is_jarvis_running():
                    launch_jarvis()
                    time.sleep(15)  # cooldown before listening again
        except Exception as e:
            print(f"[Wakeup] Error: {e}")
            time.sleep(1)


if __name__ == "__main__":
    listen_loop()
