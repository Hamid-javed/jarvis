import os
import sys
import json
import base64
import threading
import webbrowser
from pathlib import Path

from flask import Flask, render_template_string, send_from_directory
from flask_socketio import SocketIO, emit


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


BASE_DIR   = _get_base_dir()
CONFIG_DIR = BASE_DIR / "config"
API_FILE   = CONFIG_DIR / "api_keys.json"
HTML_FILE  = BASE_DIR / "ui" / "index.html"

_PORT = 5173


class JarvisWebUI:
    """
    Drop-in replacement for JarvisUI. Serves the HTML frontend via Flask+SocketIO
    and bridges state/messages to the browser via socket events.
    """

    def __init__(self, face_path: str | None = None):
        self.muted: bool = False
        self.on_text_command = None
        self._api_ready = threading.Event()
        self._mute_lock = threading.Lock()
        self._face_path = face_path

        self._app = Flask(__name__, static_folder=str(BASE_DIR / "ui"), static_url_path="/ui")
        self._app.config["SECRET_KEY"] = "jarvis-secret"
        self._sio = SocketIO(self._app, cors_allowed_origins="*", async_mode="threading")

        self._register_routes()
        self._register_events()

        if self._api_keys_exist():
            self._api_ready.set()

    # ── Interface contract (mirrors JarvisUI public API) ──────────────────────

    def wait_for_api_key(self):
        self._api_ready.wait()

    def set_state(self, state: str):
        self._sio.emit("setState", state)

    def write_log(self, text: str):
        tl = text.lower()
        if tl.startswith("you:"):
            tag = "you"
            body = text[4:].strip()
        elif tl.startswith("jarvis:") or tl.startswith("ai:"):
            colon = text.index(":")
            tag = "ai"
            body = text[colon + 1:].strip()
        else:
            if tl.startswith("err:") or "error" in tl or "failed" in tl:
                tag = "err"
            else:
                tag = "sys"
            body = text

        if tag == "ai":
            self._sio.emit("startTypewriter", body)
        else:
            self._sio.emit("appendMessage", {"tag": tag, "text": body})

    def start_speaking(self):
        self.set_state("SPEAKING")

    def stop_speaking(self):
        with self._mute_lock:
            muted = self.muted
        if not muted:
            self.set_state("LISTENING")

    # ── Window lifecycle ──────────────────────────────────────────────────────

    def start(self):
        """Serve the UI and open a browser window. Blocks until Ctrl-C or close."""
        url = f"http://127.0.0.1:{_PORT}"
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
        self._sio.run(self._app, host="127.0.0.1", port=_PORT, use_reloader=False, log_output=False)

    # ── Flask routes ──────────────────────────────────────────────────────────

    def _register_routes(self):
        app = self._app

        @app.route("/")
        def index():
            return HTML_FILE.read_text(encoding="utf-8")

    # ── SocketIO events (JS → Python) ─────────────────────────────────────────

    def _register_events(self):
        sio = self._sio

        @sio.on("connect")
        def on_connect():
            face_b64 = self._load_face_b64()
            if face_b64:
                emit("setFaceImage", face_b64)
            if not self._api_keys_exist():
                emit("showSetup")
            else:
                emit("hideSetup")

        @sio.on("submit_text")
        def on_submit_text(text):
            text = text.strip()
            if not text:
                return
            self.write_log(f"You: {text}")
            if self.on_text_command:
                threading.Thread(
                    target=self.on_text_command,
                    args=(text,),
                    daemon=True,
                ).start()

        @sio.on("toggle_mute")
        def on_toggle_mute():
            with self._mute_lock:
                self.muted = not self.muted
                muted = self.muted
            if muted:
                self.set_state("MUTED")
                self.write_log("SYS: Microphone muted.")
            else:
                self.set_state("LISTENING")
                self.write_log("SYS: Microphone active.")

        @sio.on("close")
        def on_close():
            os._exit(0)

        @sio.on("save_setup")
        def on_save_setup(data):
            api_key = data.get("api_key", "").strip()
            os_system = data.get("os_system", "")
            if not api_key:
                emit("setup_result", {"ok": False, "error": "API key required"})
                return
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(API_FILE, "w", encoding="utf-8") as f:
                json.dump({"gemini_api_key": api_key, "os_system": os_system}, f, indent=4)
            self._api_ready.set()
            emit("hideSetup")
            self.set_state("LISTENING")
            self.write_log("SYS: Systems initialised. JARVIS online.")
            emit("setup_result", {"ok": True})

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _api_keys_exist(self) -> bool:
        if not API_FILE.exists():
            return False
        try:
            data = json.loads(API_FILE.read_text(encoding="utf-8"))
            return bool(data.get("gemini_api_key")) and bool(data.get("os_system"))
        except Exception:
            return False

    def _load_face_b64(self) -> str | None:
        if not self._face_path:
            return None
        path = Path(self._face_path)
        if not path.is_absolute():
            path = BASE_DIR / path
        if not path.exists():
            jpg = path.with_suffix(".jpg")
            if jpg.exists():
                path = jpg
            else:
                return None
        try:
            data = base64.b64encode(path.read_bytes()).decode()
            ext = path.suffix.lower().lstrip(".")
            mime = "jpeg" if ext in ("jpg", "jpeg") else "png"
            return f"data:image/{mime};base64,{data}"
        except Exception:
            return None
