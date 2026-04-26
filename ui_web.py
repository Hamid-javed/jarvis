import os
import sys
import json
import base64
import threading
from pathlib import Path

import webview


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


BASE_DIR   = _get_base_dir()
CONFIG_DIR = BASE_DIR / "config"
API_FILE   = CONFIG_DIR / "api_keys.json"
HTML_FILE  = BASE_DIR / "ui" / "index.html"


class JsApi:
    """Methods on this class are callable from JavaScript via window.pywebview.api.*"""

    def __init__(self, ui: "JarvisWebUI"):
        self._ui = ui

    def submit_text(self, text: str):
        text = text.strip()
        if not text:
            return
        self._ui.write_log(f"You: {text}")
        if self._ui.on_text_command:
            threading.Thread(
                target=self._ui.on_text_command,
                args=(text,),
                daemon=True,
            ).start()

    def toggle_mute(self):
        self._ui.muted = not self._ui.muted
        if self._ui.muted:
            self._ui.set_state("MUTED")
            self._ui.write_log("SYS: Microphone muted.")
        else:
            self._ui.set_state("LISTENING")
            self._ui.write_log("SYS: Microphone active.")

    def close(self):
        os._exit(0)

    def save_setup(self, api_key: str, os_system: str) -> dict:
        api_key = api_key.strip()
        if not api_key:
            return {"ok": False, "error": "API key required"}
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(API_FILE, "w", encoding="utf-8") as f:
            json.dump({"gemini_api_key": api_key, "os_system": os_system}, f, indent=4)
        self._ui._api_ready.set()
        self._ui._evaluate_js("hideSetup()")
        self._ui.set_state("LISTENING")
        self._ui.write_log("SYS: Systems initialised. JARVIS online.")
        return {"ok": True}


class JarvisWebUI:
    """
    Drop-in replacement for JarvisUI. Owns a pywebview window and bridges
    state/messages to the HTML frontend via evaluate_js().
    """

    def __init__(self, face_path: str | None = None):
        self.muted: bool = False
        self.on_text_command = None
        self._api_ready = threading.Event()
        self._window_loaded = threading.Event()
        self._window = None
        self._js_api = JsApi(self)
        self._js_lock = threading.Lock()
        self._js_queue: list[str] = []
        self._face_path = face_path

        if self._api_keys_exist():
            self._api_ready.set()

    # ── Interface contract (mirrors JarvisUI public API) ──────────────────────

    def wait_for_api_key(self):
        self._api_ready.wait()

    def set_state(self, state: str):
        self._evaluate_js(f"setState({json.dumps(state)})")

    def write_log(self, text: str):
        tl = text.lower()
        if tl.startswith("you:"):
            tag = "you"
            body = text[4:].strip()
        elif tl.startswith("jarvis:") or tl.startswith("ai:"):
            colon = text.index(":")
            tag = "ai"
            body = text[colon + 1:].strip()
        elif tl.startswith("err:") or "error" in tl or "failed" in tl:
            tag = "err"
            body = text
        else:
            tag = "sys"
            body = text

        if tag == "ai":
            self._evaluate_js(f"startTypewriter({json.dumps(body)})")
        else:
            self._evaluate_js(f"appendMessage({json.dumps(tag)}, {json.dumps(body)})")

    def start_speaking(self):
        self.set_state("SPEAKING")

    def stop_speaking(self):
        if not self.muted:
            self.set_state("LISTENING")

    # ── Window lifecycle ──────────────────────────────────────────────────────

    def start(self):
        """Create and show the pywebview window. Blocks until closed."""
        self._window = webview.create_window(
            "J.A.R.V.I.S",
            str(HTML_FILE),
            js_api=self._js_api,
            width=984,
            height=816,
            resizable=True,
            background_color="#05050a",
            min_size=(700, 550),
        )
        self._window.events.loaded += self._on_loaded
        webview.start(debug=False)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _on_loaded(self):
        self._window_loaded.set()
        face_b64 = self._load_face_b64()
        if face_b64:
            self._window.evaluate_js(f"setFaceImage({json.dumps(face_b64)})")
        if not self._api_keys_exist():
            self._window.evaluate_js("showSetup()")
        else:
            self._window.evaluate_js("hideSetup()")
        with self._js_lock:
            for js in self._js_queue:
                try:
                    self._window.evaluate_js(js)
                except Exception:
                    pass
            self._js_queue.clear()

    def _evaluate_js(self, js: str):
        if self._window and self._window_loaded.is_set():
            try:
                self._window.evaluate_js(js)
            except Exception:
                pass
        else:
            with self._js_lock:
                self._js_queue.append(js)

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
