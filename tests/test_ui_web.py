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
    import ui_web
    ui = make_ui_with_window()
    orig_api_file = ui_web.API_FILE
    orig_config_dir = ui_web.CONFIG_DIR
    ui_web.API_FILE = tmp_path / "api_keys.json"
    ui_web.CONFIG_DIR = tmp_path

    result = ui._js_api.save_setup("test-key-123", "windows")
    assert result["ok"] is True
    data = json.loads((tmp_path / "api_keys.json").read_text())
    assert data["gemini_api_key"] == "test-key-123"
    assert data["os_system"] == "windows"
    assert ui._api_ready.is_set()

    ui_web.API_FILE = orig_api_file
    ui_web.CONFIG_DIR = orig_config_dir


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
    ui.wait_for_api_key()   # returns immediately
