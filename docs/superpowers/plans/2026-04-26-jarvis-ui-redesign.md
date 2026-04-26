# JARVIS UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the tkinter canvas UI with a pywebview-powered HTML/CSS/JS frontend — sleek dark-glass design, 50/50 split layout, violet/indigo accent, reactive orbit-ring animations.

**Architecture:** `ui_web.py` hosts `JarvisWebUI` (drop-in replacement for `JarvisUI`) and a `JsApi` class exposed to the browser via pywebview's JS bridge. The HTML frontend in `ui/index.html` drives all visuals; Python calls `evaluate_js()` to push state/messages; JS calls `window.pywebview.api.*` to send user input back. `main.py` gets a two-line swap.

**Tech Stack:** Python 3.x, pywebview ≥ 4.4 (Edge WebView2 on Windows), HTML5/CSS3/Vanilla JS, pytest

---

## File Map

| File | Status | Responsibility |
|---|---|---|
| `ui_web.py` | **Create** | `JsApi` (JS→Python bridge) + `JarvisWebUI` (Python→JS bridge, state, interface contract) |
| `ui/index.html` | **Create** | Complete frontend: layout, CSS animations, JS state machine, chat log, setup overlay |
| `tests/test_ui_web.py` | **Create** | Unit tests for `JsApi` and `JarvisWebUI` (window mocked) |
| `main.py` | **Modify** | Import swap + replace `ui.root.mainloop()` with `ui.start()` |
| `requirements.txt` | **Modify** | Add `pywebview>=4.4` |
| `ui.py` | **Unchanged** | Kept as fallback reference |

---

## Task 1: Add pywebview dependency

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add pywebview to requirements.txt**

The existing `requirements.txt` is UTF-16 encoded. Rewrite it as UTF-8 with pywebview added:

```
sounddevice
google-genai
google-generativeai
pillow
requests
beautifulsoup4
duckduckgo-search
playwright
pyautogui
pypercli
pygetwindow
opencv-python
numpy
mss
Pillow
psutil
comtypes
pycaw
win10toast
send2trash
youtube-transcript-api
pywinauto
SpeechRecognition
pywebview>=4.4
```

Write this to `requirements.txt` using UTF-8 encoding (do NOT use the Write tool's default — open with `encoding="utf-8"` or just use the Write tool which writes UTF-8).

- [ ] **Step 2: Install pywebview**

```bash
pip install "pywebview>=4.4"
```

Expected output includes: `Successfully installed pywebview-4.x.x`

- [ ] **Step 3: Verify install**

```bash
python -c "import webview; print(webview.__version__)"
```

Expected: prints version like `4.4.1` with no errors.

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "feat: add pywebview dependency for UI redesign"
```

---

## Task 2: Create `ui_web.py` — `JsApi` + `JarvisWebUI`

**Files:**
- Create: `ui_web.py`
- Create: `tests/test_ui_web.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_ui_web.py`:

```python
import json
import threading
import pytest
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path


class FakeWindow:
    def __init__(self):
        self.js_calls = []
        self.events = MagicMock()

    def evaluate_js(self, js):
        self.js_calls.append(js)


# ── JsApi tests ───────────────────────────────────────────────────────────────

def make_ui_with_window():
    """Return a JarvisWebUI with a fake window already loaded."""
    from ui_web import JarvisWebUI
    ui = JarvisWebUI.__new__(JarvisWebUI)
    ui.muted = False
    ui.on_text_command = None
    ui._api_ready = threading.Event()
    ui._window_loaded = threading.Event()
    ui._window_loaded.set()
    ui._window = FakeWindow()
    ui._js_lock = threading.Lock()
    ui._js_queue = []
    ui._face_path = None
    from ui_web import JsApi
    ui._js_api = JsApi(ui)
    return ui


def test_jsapi_submit_text_fires_callback():
    ui = make_ui_with_window()
    received = []
    ui.on_text_command = lambda t: received.append(t)
    ui._js_api.submit_text("open spotify")
    import time; time.sleep(0.05)   # callback runs in thread
    assert received == ["open spotify"]


def test_jsapi_submit_text_empty_does_nothing():
    ui = make_ui_with_window()
    called = []
    ui.on_text_command = lambda t: called.append(t)
    ui._js_api.submit_text("   ")
    import time; time.sleep(0.05)
    assert called == []


def test_jsapi_toggle_mute_toggles_state():
    ui = make_ui_with_window()
    assert ui.muted is False
    ui._js_api.toggle_mute()
    assert ui.muted is True
    ui._js_api.toggle_mute()
    assert ui.muted is False


def test_jsapi_toggle_mute_calls_set_state():
    ui = make_ui_with_window()
    ui._js_api.toggle_mute()
    js_calls = ui._window.js_calls
    assert any('MUTED' in c for c in js_calls)


def test_jsapi_save_setup_writes_config(tmp_path):
    from ui_web import JarvisWebUI, JsApi
    ui = make_ui_with_window()
    # Redirect config dir to tmp
    import ui_web
    orig = ui_web.API_FILE
    ui_web.API_FILE = tmp_path / "api_keys.json"
    ui_web.CONFIG_DIR = tmp_path

    result = ui._js_api.save_setup("test-key-123", "windows")
    assert result["ok"] is True
    data = json.loads((tmp_path / "api_keys.json").read_text())
    assert data["gemini_api_key"] == "test-key-123"
    assert data["os_system"] == "windows"
    assert ui._api_ready.is_set()

    ui_web.API_FILE = orig


def test_jsapi_save_setup_rejects_empty_key():
    ui = make_ui_with_window()
    result = ui._js_api.save_setup("", "windows")
    assert result["ok"] is False


# ── JarvisWebUI tests ──────────────────────────────────────────────────────────

def test_set_state_evaluates_js():
    ui = make_ui_with_window()
    ui.set_state("SPEAKING")
    assert any('setState("SPEAKING")' in c for c in ui._window.js_calls)


def test_write_log_you_calls_append_message():
    ui = make_ui_with_window()
    ui.write_log("You: hello there")
    assert any('"you"' in c and 'hello there' in c for c in ui._window.js_calls)


def test_write_log_ai_calls_typewriter():
    ui = make_ui_with_window()
    ui.write_log("Jarvis: Good morning, sir.")
    assert any('startTypewriter' in c and 'Good morning' in c for c in ui._window.js_calls)


def test_write_log_sys_calls_append_message():
    ui = make_ui_with_window()
    ui.write_log("SYS: JARVIS online.")
    assert any('"sys"' in c for c in ui._window.js_calls)


def test_write_log_error_uses_err_tag():
    ui = make_ui_with_window()
    ui.write_log("ERR: open_app failed")
    assert any('"err"' in c for c in ui._window.js_calls)


def test_start_speaking_sets_state():
    ui = make_ui_with_window()
    ui.start_speaking()
    assert any('SPEAKING' in c for c in ui._window.js_calls)


def test_stop_speaking_sets_listening_when_not_muted():
    ui = make_ui_with_window()
    ui.muted = False
    ui.stop_speaking()
    assert any('LISTENING' in c for c in ui._window.js_calls)


def test_stop_speaking_does_not_change_state_when_muted():
    ui = make_ui_with_window()
    ui.muted = True
    ui.stop_speaking()
    # Should NOT call setState at all
    assert not any('setState' in c for c in ui._window.js_calls)


def test_evaluate_js_queues_when_window_not_loaded():
    from ui_web import JarvisWebUI
    ui = JarvisWebUI.__new__(JarvisWebUI)
    ui._window_loaded = threading.Event()   # NOT set
    ui._window = FakeWindow()
    ui._js_lock = threading.Lock()
    ui._js_queue = []
    ui._evaluate_js('someCall()')
    assert 'someCall()' in ui._js_queue
    assert ui._window.js_calls == []


def test_wait_for_api_key_returns_immediately_when_ready():
    ui = make_ui_with_window()
    ui._api_ready.set()
    # Should not block
    ui.wait_for_api_key()   # returns immediately
```

- [ ] **Step 2: Run tests to verify they all fail**

```bash
cd E:/projects/jarvis && python -m pytest tests/test_ui_web.py -v 2>&1 | head -30
```

Expected: `ModuleNotFoundError: No module named 'ui_web'`

- [ ] **Step 3: Create `ui_web.py`**

```python
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
        self._window: webview.Window | None = None
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
        # Inject face image as base64 data URL (avoids local file access issues)
        face_b64 = self._load_face_b64()
        if face_b64:
            self._window.evaluate_js(f"setFaceImage({json.dumps(face_b64)})")
        # Show or hide setup overlay
        if not self._api_keys_exist():
            self._window.evaluate_js("showSetup()")
        else:
            self._window.evaluate_js("hideSetup()")
        # Flush any JS that was queued before the window loaded
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
            # Try .jpg fallback
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
```

- [ ] **Step 4: Run tests**

```bash
cd E:/projects/jarvis && python -m pytest tests/test_ui_web.py -v
```

Expected: all tests pass. If `test_jsapi_submit_text_fires_callback` is flaky due to threading, increase sleep to `0.1`.

- [ ] **Step 5: Commit**

```bash
git add ui_web.py tests/test_ui_web.py
git commit -m "feat: add JarvisWebUI and JsApi with tests"
```

---

## Task 3: Create `ui/index.html` — complete frontend

**Files:**
- Create: `ui/index.html`

No unit tests for HTML. Visually verified in Task 5.

- [ ] **Step 1: Create `ui/index.html`**

```html
<!DOCTYPE html>
<html lang="en" data-state="INITIALISING">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>J.A.R.V.I.S</title>
<style>
/* ── Reset & base ─────────────────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --acc:     #6366f1;
  --acc2:    #8b5cf6;
  --acc3:    #a78bfa;
  --bg:      #05050a;
  --panel:   rgba(15, 15, 25, 0.92);
  --border:  rgba(255,255,255,0.07);
  --text:    #e2e8f0;
  --muted:   rgba(255,255,255,0.25);
}

html, body {
  height: 100%;
  background: var(--bg);
  color: var(--text);
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  overflow: hidden;
  user-select: none;
}

/* ── App shell ─────────────────────────────────────────────────────────────── */
#app {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--panel);
  border: 1px solid rgba(99,102,241,0.15);
}

/* ── Title bar ─────────────────────────────────────────────────────────────── */
#titlebar {
  height: 44px;
  background: rgba(8, 8, 18, 0.95);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  padding: 0 18px;
  gap: 8px;
  flex-shrink: 0;
  -webkit-app-region: drag;
}

.tb-dot {
  width: 11px; height: 11px;
  border-radius: 50%;
  cursor: pointer;
  -webkit-app-region: no-drag;
}
.dot-red    { background: #ff5f56; }
.dot-yellow { background: #ffbd2e; }
.dot-green  { background: #27c93f; }

#tb-title {
  flex: 1;
  text-align: center;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 4px;
  color: rgba(255,255,255,0.4);
}

#tb-clock {
  font-size: 13px;
  font-variant-numeric: tabular-nums;
  font-weight: 700;
  color: var(--acc);
  -webkit-app-region: no-drag;
}

/* ── Main split ─────────────────────────────────────────────────────────────── */
#main {
  flex: 1;
  display: flex;
  overflow: hidden;
}

/* ── LEFT PANEL ─────────────────────────────────────────────────────────────── */
#left {
  width: 50%;
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 18px;
  padding: 28px 20px;
  position: relative;
  background: linear-gradient(160deg, rgba(99,102,241,0.05) 0%, transparent 55%);
}

/* Ambient glow */
#avatar-glow {
  position: absolute;
  width: 280px; height: 280px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(99,102,241,0.16) 0%, transparent 70%);
  pointer-events: none;
  transition: opacity 0.6s;
}

/* Orbit rings */
.orbit-ring {
  position: absolute;
  border-radius: 50%;
  border: 1px solid transparent;
  opacity: 0;
  transition: opacity 0.5s;
}
.ring-1 {
  width: 230px; height: 230px;
  border-top-color:   rgba(99,102,241,0.55);
  border-right-color: rgba(99,102,241,0.12);
  animation: spin-cw 4s linear infinite;
}
.ring-2 {
  width: 196px; height: 196px;
  border-bottom-color: rgba(139,92,246,0.45);
  border-left-color:   rgba(139,92,246,0.1);
  animation: spin-ccw 7s linear infinite;
}
.ring-3 {
  width: 162px; height: 162px;
  border-top-color:   rgba(167,139,250,0.3);
  border-right-color: rgba(167,139,250,0.07);
  animation: spin-cw 10s linear infinite;
}

@keyframes spin-cw  { to { transform: rotate(360deg);  } }
@keyframes spin-ccw { to { transform: rotate(-360deg); } }

/* State-driven ring visibility and speed */
html[data-state="LISTENING"]    .orbit-ring { opacity: 1; }
html[data-state="LISTENING"]    .ring-1 { animation-duration: 4s; }
html[data-state="LISTENING"]    .ring-2 { animation-duration: 7s; }
html[data-state="LISTENING"]    .ring-3 { animation-duration: 10s; }

html[data-state="SPEAKING"]     .orbit-ring { opacity: 1; }
html[data-state="SPEAKING"]     .ring-1 { animation-duration: 1.2s; }
html[data-state="SPEAKING"]     .ring-2 { animation-duration: 2.2s; }
html[data-state="SPEAKING"]     .ring-3 { animation-duration: 3.4s; }

html[data-state="THINKING"]     .orbit-ring { opacity: 0.75; }
html[data-state="THINKING"]     .ring-1 { animation-duration: 2.5s; }
html[data-state="THINKING"]     .ring-2 { animation-duration: 4.5s; }
html[data-state="THINKING"]     .ring-3 { animation-duration: 7s; }

html[data-state="PROCESSING"]   .orbit-ring { opacity: 0.75; }
html[data-state="PROCESSING"]   .ring-1 { animation-duration: 2s; }
html[data-state="PROCESSING"]   .ring-2 { animation-duration: 3.5s; }
html[data-state="PROCESSING"]   .ring-3 { animation-duration: 5.5s; }

html[data-state="INITIALISING"] .orbit-ring { opacity: 0.35; }
html[data-state="ONLINE"]       .orbit-ring { opacity: 1; }
html[data-state="MUTED"]        .orbit-ring { opacity: 0; }

/* Avatar */
#avatar-wrap {
  position: relative;
  width: 130px; height: 130px;
  display: flex; align-items: center; justify-content: center;
  z-index: 2;
}

#avatar-circle {
  width: 122px; height: 122px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--acc) 0%, var(--acc2) 60%, var(--acc3) 100%);
  box-shadow: 0 0 28px rgba(99,102,241,0.5), 0 0 56px rgba(99,102,241,0.18),
              inset 0 1px 0 rgba(255,255,255,0.18);
  display: flex; align-items: center; justify-content: center;
  overflow: hidden;
  animation: breathe 3.2s ease-in-out infinite;
  transition: background 0.5s, box-shadow 0.5s;
}

html[data-state="SPEAKING"] #avatar-circle {
  animation: breathe-speak 0.9s ease-in-out infinite;
}
html[data-state="MUTED"] #avatar-circle {
  background: linear-gradient(135deg, #7f1d1d, #991b1b);
  box-shadow: 0 0 28px rgba(239,68,68,0.4), 0 0 56px rgba(239,68,68,0.12);
  animation: breathe 3.2s ease-in-out infinite;
}

@keyframes breathe {
  0%,100% { transform: scale(1);    box-shadow: 0 0 28px rgba(99,102,241,0.5),  0 0 56px rgba(99,102,241,0.18); }
  50%     { transform: scale(1.03); box-shadow: 0 0 38px rgba(99,102,241,0.65), 0 0 72px rgba(99,102,241,0.28); }
}
@keyframes breathe-speak {
  0%,100% { transform: scale(1);    }
  50%     { transform: scale(1.06); }
}

#avatar-face {
  width: 100%; height: 100%;
  display: flex; align-items: center; justify-content: center;
  border-radius: 50%;
  overflow: hidden;
}
#avatar-face img {
  width: 100%; height: 100%;
  object-fit: cover;
  border-radius: 50%;
}
#avatar-orb-text {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1px;
  color: rgba(255,255,255,0.8);
}

/* Status badge */
#status-badge {
  display: flex;
  align-items: center;
  gap: 7px;
  background: rgba(99,102,241,0.1);
  border: 1px solid rgba(99,102,241,0.22);
  border-radius: 20px;
  padding: 5px 15px;
  z-index: 2;
  transition: background 0.3s, border-color 0.3s;
}
html[data-state="MUTED"] #status-badge {
  background: rgba(239,68,68,0.1);
  border-color: rgba(239,68,68,0.3);
}
html[data-state="MUTED"] #status-badge #status-dot { background: #ef4444; }
html[data-state="MUTED"] #status-badge #status-text { color: #fca5a5; }

#status-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--acc3);
  animation: blink 1.5s ease-in-out infinite;
  flex-shrink: 0;
}
html[data-state="SPEAKING"] #status-dot { background: #f97316; animation: blink 0.6s ease-in-out infinite; }
html[data-state="THINKING"]  #status-dot { background: #eab308; }
html[data-state="PROCESSING"] #status-dot { background: #eab308; }

@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.25} }

#status-text {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 2px;
  color: var(--acc3);
  text-transform: uppercase;
  transition: color 0.3s;
}

/* Waveform */
#waveform {
  display: flex;
  align-items: center;
  gap: 3px;
  height: 28px;
  z-index: 2;
}
.wave-bar {
  width: 3px;
  border-radius: 3px;
  background: linear-gradient(to top, var(--acc), var(--acc3));
}
html[data-state="LISTENING"]   .wave-bar { animation: wave-idle  1.4s ease-in-out infinite; }
html[data-state="SPEAKING"]    .wave-bar { animation: wave-speak 0.5s ease-in-out infinite; }
html[data-state="THINKING"]    .wave-bar { animation: wave-idle  2s ease-in-out infinite; }
html[data-state="PROCESSING"]  .wave-bar { animation: wave-idle  1.8s ease-in-out infinite; }
html[data-state="INITIALISING"].wave-bar { animation: wave-idle  3s ease-in-out infinite; }
html[data-state="MUTED"]       .wave-bar { animation: none; height: 3px !important; opacity: 0.3; }

@keyframes wave-idle  { 0%,100%{transform:scaleY(1)}    50%{transform:scaleY(0.3)} }
@keyframes wave-speak { 0%,100%{transform:scaleY(1)}    50%{transform:scaleY(0.15)} }

/* Mute button */
#mute-btn {
  display: flex;
  align-items: center;
  gap: 7px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 10px;
  padding: 6px 14px;
  cursor: pointer;
  z-index: 2;
  transition: background 0.2s, border-color 0.2s;
  color: rgba(255,255,255,0.4);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 1px;
}
#mute-btn:hover { background: rgba(99,102,241,0.12); border-color: rgba(99,102,241,0.3); }
html[data-state="MUTED"] #mute-btn {
  background: rgba(239,68,68,0.1);
  border-color: rgba(239,68,68,0.35);
  color: #fca5a5;
}
#mute-icon { font-size: 13px; }

/* Model badge */
#model-badge {
  font-size: 9px;
  letter-spacing: 3px;
  color: rgba(255,255,255,0.15);
  text-transform: uppercase;
  z-index: 2;
}

/* ── RIGHT PANEL ─────────────────────────────────────────────────────────────── */
#right {
  width: 50%;
  display: flex;
  flex-direction: column;
  padding: 16px 16px 14px;
  gap: 10px;
}

#chat-label {
  font-size: 9px;
  letter-spacing: 2px;
  color: rgba(255,255,255,0.18);
  text-transform: uppercase;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

/* Chat log */
#chat-log {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-right: 4px;
  scroll-behavior: smooth;
}
#chat-log::-webkit-scrollbar { width: 3px; }
#chat-log::-webkit-scrollbar-track { background: transparent; }
#chat-log::-webkit-scrollbar-thumb { background: rgba(99,102,241,0.3); border-radius: 3px; }

/* Message groups */
.msg { display: flex; flex-direction: column; gap: 3px; max-width: 88%; }
.msg-sender { font-size: 9px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; }
.msg-bubble { padding: 8px 12px; border-radius: 12px; font-size: 12px; line-height: 1.55; word-break: break-word; }

.msg-you { align-self: flex-end; align-items: flex-end; }
.msg-you .msg-sender { color: rgba(255,255,255,0.28); }
.msg-you .msg-bubble {
  background: rgba(99,102,241,0.18);
  border: 1px solid rgba(99,102,241,0.28);
  color: var(--text);
  border-bottom-right-radius: 4px;
}

.msg-ai { align-self: flex-start; align-items: flex-start; }
.msg-ai .msg-sender { color: var(--acc3); }
.msg-ai .msg-bubble {
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.08);
  color: var(--text);
  border-bottom-left-radius: 4px;
}

.msg-sys { align-self: center; align-items: center; }
.msg-sys .msg-bubble { background: transparent; border: none; color: rgba(255,255,255,0.22); font-size: 10px; padding: 2px 6px; }

.msg-err { align-self: flex-start; align-items: flex-start; }
.msg-err .msg-sender { color: #f87171; }
.msg-err .msg-bubble {
  background: rgba(239,68,68,0.08);
  border: 1px solid rgba(239,68,68,0.2);
  color: #fca5a5;
  border-bottom-left-radius: 4px;
}

/* Typing indicator */
#typing-indicator {
  display: none;
  align-self: flex-start;
  padding: 8px 14px;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  border-bottom-left-radius: 4px;
  gap: 5px;
  align-items: center;
}
#typing-indicator.visible { display: flex; }
.t-dot {
  width: 5px; height: 5px;
  border-radius: 50%;
  background: var(--acc3);
  animation: tdot 1.2s ease-in-out infinite;
}
.t-dot:nth-child(2) { animation-delay: 0.2s; }
.t-dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes tdot { 0%,100%{transform:translateY(0);opacity:0.35} 50%{transform:translateY(-5px);opacity:1} }

/* Input area */
#input-area {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-shrink: 0;
}

#chat-input {
  flex: 1;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.09);
  border-radius: 12px;
  padding: 9px 14px;
  color: var(--text);
  font-size: 12px;
  font-family: inherit;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}
#chat-input:focus {
  border-color: rgba(99,102,241,0.5);
  box-shadow: 0 0 0 3px rgba(99,102,241,0.1);
}
#chat-input::placeholder { color: rgba(255,255,255,0.18); }

#send-btn {
  width: 36px; height: 36px;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--acc), var(--acc2));
  border: none;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: transform 0.15s, box-shadow 0.15s;
  box-shadow: 0 4px 12px rgba(99,102,241,0.4);
  flex-shrink: 0;
}
#send-btn:hover { transform: scale(1.08); box-shadow: 0 6px 18px rgba(99,102,241,0.55); }
#send-btn:active { transform: scale(0.96); }
#send-btn svg { width: 14px; height: 14px; fill: white; pointer-events: none; }

#input-hint {
  text-align: right;
  font-size: 9px;
  color: rgba(255,255,255,0.12);
  letter-spacing: 0.5px;
  flex-shrink: 0;
}

/* ── Setup overlay ──────────────────────────────────────────────────────────── */
#setup-overlay {
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(5,5,10,0.88);
  z-index: 100;
  align-items: center;
  justify-content: center;
}
#setup-overlay.visible { display: flex; }

#setup-box {
  background: rgba(12,12,24,0.97);
  border: 1px solid rgba(99,102,241,0.35);
  border-radius: 16px;
  padding: 32px 36px;
  width: 400px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-shadow: 0 24px 60px rgba(0,0,0,0.6), 0 0 40px rgba(99,102,241,0.1);
}

#setup-box h2 {
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 2px;
  color: var(--acc3);
  text-transform: uppercase;
}
#setup-box p {
  font-size: 11px;
  color: rgba(255,255,255,0.35);
  line-height: 1.5;
}
#setup-box label {
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 2px;
  color: rgba(255,255,255,0.3);
  text-transform: uppercase;
  display: block;
  margin-bottom: 5px;
}
#setup-api-input {
  width: 100%;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  padding: 9px 12px;
  color: var(--text);
  font-size: 12px;
  font-family: monospace;
  outline: none;
}
#setup-api-input:focus { border-color: rgba(99,102,241,0.5); }

#setup-os-btns { display: flex; gap: 8px; }
.os-btn {
  flex: 1;
  padding: 7px 0;
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.1);
  background: rgba(255,255,255,0.04);
  color: rgba(255,255,255,0.4);
  font-size: 10px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.15s;
  letter-spacing: 1px;
}
.os-btn.selected {
  background: var(--acc);
  border-color: var(--acc);
  color: white;
}
.os-btn:hover:not(.selected) { border-color: rgba(99,102,241,0.4); }

#setup-error {
  font-size: 10px;
  color: #f87171;
  display: none;
  letter-spacing: 0.5px;
}
#setup-error.visible { display: block; }

#setup-submit {
  width: 100%;
  padding: 10px;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--acc), var(--acc2));
  border: none;
  color: white;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 2px;
  text-transform: uppercase;
  cursor: pointer;
  transition: opacity 0.15s, transform 0.15s;
}
#setup-submit:hover { opacity: 0.88; transform: translateY(-1px); }
</style>
</head>
<body>

<div id="app">

  <!-- Title bar -->
  <div id="titlebar">
    <div class="tb-dot dot-red"    onclick="window.pywebview && window.pywebview.api.close()"></div>
    <div class="tb-dot dot-yellow"></div>
    <div class="tb-dot dot-green"></div>
    <div id="tb-title">J · A · R · V · I · S</div>
    <div id="tb-clock">00:00:00</div>
  </div>

  <!-- Main split -->
  <div id="main">

    <!-- LEFT: Avatar panel -->
    <div id="left">
      <div id="avatar-glow"></div>
      <div class="orbit-ring ring-1"></div>
      <div class="orbit-ring ring-2"></div>
      <div class="orbit-ring ring-3"></div>

      <div id="avatar-wrap">
        <div id="avatar-circle">
          <div id="avatar-face">
            <span id="avatar-orb-text">JARVIS</span>
          </div>
        </div>
      </div>

      <div id="status-badge">
        <div id="status-dot"></div>
        <div id="status-text">INITIALISING</div>
      </div>

      <div id="waveform">
        <!-- 16 bars, heights set inline for natural variety -->
        <div class="wave-bar" style="height:8px"></div>
        <div class="wave-bar" style="height:16px"></div>
        <div class="wave-bar" style="height:10px"></div>
        <div class="wave-bar" style="height:20px"></div>
        <div class="wave-bar" style="height:6px"></div>
        <div class="wave-bar" style="height:14px"></div>
        <div class="wave-bar" style="height:22px"></div>
        <div class="wave-bar" style="height:8px"></div>
        <div class="wave-bar" style="height:12px"></div>
        <div class="wave-bar" style="height:18px"></div>
        <div class="wave-bar" style="height:7px"></div>
        <div class="wave-bar" style="height:15px"></div>
        <div class="wave-bar" style="height:11px"></div>
        <div class="wave-bar" style="height:19px"></div>
        <div class="wave-bar" style="height:9px"></div>
        <div class="wave-bar" style="height:13px"></div>
      </div>

      <button id="mute-btn" onclick="onMuteClick()">
        <span id="mute-icon">🎙</span>
        <span id="mute-label">LIVE · F4</span>
      </button>

      <div id="model-badge">Mark XXXVII</div>
    </div>

    <!-- RIGHT: Chat panel -->
    <div id="right">
      <div id="chat-label">Conversation</div>

      <div id="chat-log">
        <div id="typing-indicator">
          <div class="t-dot"></div>
          <div class="t-dot"></div>
          <div class="t-dot"></div>
        </div>
      </div>

      <div id="input-area">
        <input id="chat-input" type="text" placeholder="Ask JARVIS anything…"
               autocomplete="off" spellcheck="false" />
        <button id="send-btn" onclick="onSendClick()">
          <svg viewBox="0 0 24 24"><path d="M2 21l21-9L2 3v7l15 2-15 2v7z"/></svg>
        </button>
      </div>
      <div id="input-hint">ENTER to send &middot; F4 to mute</div>
    </div>

  </div>
</div>

<!-- Setup overlay -->
<div id="setup-overlay">
  <div id="setup-box">
    <h2>◈ Initialisation Required</h2>
    <p>Configure J.A.R.V.I.S. before first boot.</p>

    <div>
      <label>Gemini API Key</label>
      <input id="setup-api-input" type="password" placeholder="AIza..." autocomplete="off" />
    </div>

    <div>
      <label>Operating System</label>
      <div id="setup-os-btns">
        <button class="os-btn" data-os="windows" onclick="selectOs('windows')">⊞ Windows</button>
        <button class="os-btn" data-os="mac"     onclick="selectOs('mac')">  macOS</button>
        <button class="os-btn" data-os="linux"   onclick="selectOs('linux')">🐧 Linux</button>
      </div>
    </div>

    <div id="setup-error">API key cannot be empty.</div>

    <button id="setup-submit" onclick="onSetupSubmit()">▸ Initialise Systems</button>
  </div>
</div>

<script>
// ── State labels ───────────────────────────────────────────────────────────────
const STATE_LABELS = {
  LISTENING:    'LISTENING',
  SPEAKING:     'SPEAKING',
  THINKING:     'THINKING',
  PROCESSING:   'PROCESSING',
  MUTED:        'MUTED',
  INITIALISING: 'INITIALISING',
  ONLINE:       'ONLINE',
};

const MUTE_LABELS = {
  muted: { icon: '🔇', label: 'MUTED · F4' },
  live:  { icon: '🎙', label: 'LIVE · F4'  },
};

// ── Clock ──────────────────────────────────────────────────────────────────────
function updateClock() {
  const now = new Date();
  const h = String(now.getHours()).padStart(2, '0');
  const m = String(now.getMinutes()).padStart(2, '0');
  const s = String(now.getSeconds()).padStart(2, '0');
  document.getElementById('tb-clock').textContent = `${h}:${m}:${s}`;
}
setInterval(updateClock, 1000);
updateClock();

// ── setState — called from Python via evaluate_js ──────────────────────────────
function setState(state) {
  document.documentElement.dataset.state = state;
  const label = STATE_LABELS[state] || state;
  document.getElementById('status-text').textContent = label;

  // Mute button appearance
  if (state === 'MUTED') {
    document.getElementById('mute-icon').textContent  = MUTE_LABELS.muted.icon;
    document.getElementById('mute-label').textContent = MUTE_LABELS.muted.label;
  } else {
    document.getElementById('mute-icon').textContent  = MUTE_LABELS.live.icon;
    document.getElementById('mute-label').textContent = MUTE_LABELS.live.label;
  }
}

// ── appendMessage — called from Python via evaluate_js ─────────────────────────
function appendMessage(tag, text) {
  const log = document.getElementById('chat-log');
  const ti  = document.getElementById('typing-indicator');

  const wrap   = document.createElement('div');
  const sender = document.createElement('div');
  const bubble = document.createElement('div');

  wrap.classList.add('msg', `msg-${tag}`);
  sender.classList.add('msg-sender');
  bubble.classList.add('msg-bubble');
  bubble.textContent = text;

  const senderNames = { you: 'You', sys: '', err: 'Error', ai: 'Jarvis' };
  if (senderNames[tag]) {
    sender.textContent = senderNames[tag];
    wrap.appendChild(sender);
  }
  wrap.appendChild(bubble);

  // Insert before typing indicator
  log.insertBefore(wrap, ti);
  log.scrollTop = log.scrollHeight;
}

// ── startTypewriter — called from Python for AI responses ─────────────────────
function startTypewriter(text) {
  const log = document.getElementById('chat-log');
  const ti  = document.getElementById('typing-indicator');

  // Show typing indicator briefly, then replace with typewriter bubble
  ti.classList.add('visible');
  log.scrollTop = log.scrollHeight;

  setTimeout(function() {
    ti.classList.remove('visible');

    const wrap   = document.createElement('div');
    const sender = document.createElement('div');
    const bubble = document.createElement('div');

    wrap.classList.add('msg', 'msg-ai');
    sender.classList.add('msg-sender');
    sender.textContent = 'Jarvis';
    bubble.classList.add('msg-bubble');

    wrap.appendChild(sender);
    wrap.appendChild(bubble);
    log.insertBefore(wrap, ti);

    let i = 0;
    function typeChar() {
      if (i < text.length) {
        bubble.textContent += text[i];
        i++;
        log.scrollTop = log.scrollHeight;
        setTimeout(typeChar, 18);
      }
    }
    typeChar();
  }, 420);
}

// ── setFaceImage — called from Python after window loads ───────────────────────
function setFaceImage(dataUrl) {
  const face = document.getElementById('avatar-face');
  face.innerHTML = '';
  const img = document.createElement('img');
  img.src = dataUrl;
  face.appendChild(img);
}

// ── showSetup / hideSetup ─────────────────────────────────────────────────────
let _selectedOs = (navigator.platform.toLowerCase().includes('win')) ? 'windows' :
                  (navigator.platform.toLowerCase().includes('mac')) ? 'mac' : 'linux';

function showSetup() {
  document.getElementById('setup-overlay').classList.add('visible');
  selectOs(_selectedOs);
}

function hideSetup() {
  document.getElementById('setup-overlay').classList.remove('visible');
}

function selectOs(os) {
  _selectedOs = os;
  document.querySelectorAll('.os-btn').forEach(function(btn) {
    btn.classList.toggle('selected', btn.dataset.os === os);
  });
}

function onSetupSubmit() {
  const key = document.getElementById('setup-api-input').value.trim();
  const err = document.getElementById('setup-error');
  if (!key) {
    err.classList.add('visible');
    return;
  }
  err.classList.remove('visible');
  if (window.pywebview) {
    window.pywebview.api.save_setup(key, _selectedOs);
  }
}

// ── Input events ──────────────────────────────────────────────────────────────
function onSendClick() {
  const inp  = document.getElementById('chat-input');
  const text = inp.value.trim();
  if (!text) return;
  inp.value = '';
  if (window.pywebview) {
    window.pywebview.api.submit_text(text);
  }
}

function onMuteClick() {
  if (window.pywebview) {
    window.pywebview.api.toggle_mute();
  }
}

document.getElementById('chat-input').addEventListener('keydown', function(e) {
  if (e.key === 'Enter') { e.preventDefault(); onSendClick(); }
});

document.addEventListener('keydown', function(e) {
  if (e.key === 'F4') { e.preventDefault(); onMuteClick(); }
});
</script>

</body>
</html>
```

- [ ] **Step 2: Open in browser to verify layout**

```bash
start "" "E:/projects/jarvis/ui/index.html"
```

Verify: 50/50 split visible, orbit rings animate, status badge shows "INITIALISING", clock ticks, input and send button render correctly. Setup overlay not visible (no pywebview object in browser, but layout should be correct).

- [ ] **Step 3: Commit**

```bash
git add ui/index.html
git commit -m "feat: add JARVIS HTML/CSS/JS frontend"
```

---

## Task 4: Update `main.py`

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Swap import at top of `main.py`**

Replace line 12:
```python
from ui import JarvisUI
```
With:
```python
from ui_web import JarvisWebUI
```

- [ ] **Step 2: Update `main()` function**

Replace the `main()` function (currently lines 804–816):

```python
def main():
    ui = JarvisWebUI("face.png")

    def runner():
        ui.wait_for_api_key()
        jarvis = JarvisLive(ui)
        try:
            asyncio.run(jarvis.run())
        except KeyboardInterrupt:
            print("\n🔴 Shutting down...")

    threading.Thread(target=runner, daemon=True).start()
    ui.start()   # blocks main thread (replaces ui.root.mainloop())
```

- [ ] **Step 3: Update `JarvisLive.__init__` type hint (optional but clean)**

Line 425 currently reads `def __init__(self, ui: JarvisUI):` — change to:
```python
def __init__(self, ui: JarvisWebUI):
```

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "feat: wire main.py to JarvisWebUI, replace tkinter mainloop"
```

---

## Task 5: Smoke test — full end-to-end run

**Files:** none changed

- [ ] **Step 1: Run the app**

```bash
cd E:/projects/jarvis && python main.py
```

Expected:
- pywebview window opens (Edge WebView2 on Windows)
- If `config/api_keys.json` does NOT exist: setup overlay appears, gradient avatar shown
- If `config/api_keys.json` exists: setup overlay hidden, window shows "INITIALISING" state
- Clock ticks in title bar
- Orbit rings visible and spinning
- Typing in input field and pressing Enter logs "You: <text>" in chat

- [ ] **Step 2: Verify setup flow (if no API keys yet)**

1. Setup overlay is visible on launch
2. Enter a Gemini API key in the field
3. Select your OS
4. Click "Initialise Systems"
5. Overlay disappears
6. Chat log shows "Systems initialised. JARVIS online."
7. Status badge switches to "LISTENING"

- [ ] **Step 3: Verify state transitions**

With JARVIS connected to Gemini:
- Speak a command → status badge switches to PROCESSING → THINKING → SPEAKING
- Orbit rings speed up during SPEAKING
- Avatar breathe animation intensifies
- AI response appears with typewriter effect
- F4 key → status shows MUTED, rings hide, avatar circle turns red

- [ ] **Step 4: Verify face image (if `face.png` exists)**

- Restart app with `face.png` in project root
- Avatar circle should show the photo clipped to circle

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat: JARVIS UI redesign — pywebview sleek modern interface complete"
```

---

## Self-Review Checklist

- [x] **Spec § Left Panel — Avatar idle:** ambient glow, breathing, waveform idle, orbit rings hidden → covered by CSS `data-state="INITIALISING"` rings `opacity: 0.35`, idle wave animation, breathe keyframe
- [x] **Spec § Left Panel — Active states:** orbit rings appear, speed up on SPEAKING → CSS attribute selectors in Task 3
- [x] **Spec § Left Panel — User photo:** base64 injection via `setFaceImage()` → Task 2 `_load_face_b64()`
- [x] **Spec § Right Panel — Bubble chat:** you/ai/sys/err bubbles → Task 3 `appendMessage()`
- [x] **Spec § Right Panel — Typewriter:** `startTypewriter()` with 18ms delay → Task 3
- [x] **Spec § Right Panel — Typing indicator:** 3 animated dots, shown briefly before typewriter → Task 3
- [x] **Spec § Right Panel — Auto-scroll:** `log.scrollTop = log.scrollHeight` after every insert → Task 3
- [x] **Spec § Title bar:** traffic lights, centered name, live clock → Task 3
- [x] **Spec § Bridge JS→Python:** `submit_text`, `toggle_mute`, `close`, `save_setup` → Task 2 `JsApi`
- [x] **Spec § Bridge Python→JS:** `setState`, `appendMessage`, `startTypewriter` → Task 2 + Task 3
- [x] **Spec § Interface contract:** `muted`, `on_text_command`, `set_state`, `write_log`, `wait_for_api_key`, `start_speaking`, `stop_speaking` → Task 2 `JarvisWebUI`
- [x] **Spec § main.py:** import swap + `webview.start()` instead of `mainloop()` → Task 4
- [x] **Spec § requirements.txt:** `pywebview>=4.4` → Task 1
- [x] **Setup UI:** ported inline as HTML overlay (cleaner than keeping tkinter) — covered in Task 3 + `JsApi.save_setup()`
