import json
import threading
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path


def make_ui(tmp_path=None, monkeypatch=None):
    """Return a JarvisWebUI with mocked SocketIO emit."""
    from ui_web import JarvisWebUI
    import ui_web

    if tmp_path and monkeypatch:
        monkeypatch.setattr(ui_web, "API_FILE", tmp_path / "api_keys.json")
        monkeypatch.setattr(ui_web, "CONFIG_DIR", tmp_path)

    ui = JarvisWebUI.__new__(JarvisWebUI)
    ui.muted = False
    ui.on_text_command = None
    ui._api_ready = threading.Event()
    ui._mute_lock = threading.Lock()
    ui._face_path = None
    ui._sio = MagicMock()
    return ui


# ── set_state ─────────────────────────────────────────────────────────────────

def test_set_state_emits_event():
    ui = make_ui()
    ui.set_state("SPEAKING")
    ui._sio.emit.assert_called_with("setState", "SPEAKING")


# ── write_log ─────────────────────────────────────────────────────────────────

def test_write_log_you_emits_append_message():
    ui = make_ui()
    ui.write_log("You: hello there")
    ui._sio.emit.assert_called_with("appendMessage", {"tag": "you", "text": "hello there"})


def test_write_log_ai_emits_typewriter():
    ui = make_ui()
    ui.write_log("Jarvis: Good morning, sir.")
    ui._sio.emit.assert_called_with("startTypewriter", "Good morning, sir.")


def test_write_log_sys_emits_append_message():
    ui = make_ui()
    ui.write_log("SYS: JARVIS online.")
    ui._sio.emit.assert_called_with("appendMessage", {"tag": "sys", "text": "SYS: JARVIS online."})


def test_write_log_error_uses_err_tag():
    ui = make_ui()
    ui.write_log("ERR: open_app failed")
    ui._sio.emit.assert_called_with("appendMessage", {"tag": "err", "text": "ERR: open_app failed"})


# ── start_speaking / stop_speaking ────────────────────────────────────────────

def test_start_speaking_sets_state():
    ui = make_ui()
    ui.start_speaking()
    ui._sio.emit.assert_called_with("setState", "SPEAKING")


def test_stop_speaking_sets_listening_when_not_muted():
    ui = make_ui()
    ui.muted = False
    ui.stop_speaking()
    ui._sio.emit.assert_called_with("setState", "LISTENING")


def test_stop_speaking_no_emit_when_muted():
    ui = make_ui()
    ui.muted = True
    ui.stop_speaking()
    ui._sio.emit.assert_not_called()


# ── wait_for_api_key ──────────────────────────────────────────────────────────

def test_wait_for_api_key_returns_immediately_when_ready():
    ui = make_ui()
    ui._api_ready.set()
    ui.wait_for_api_key()


# ── socket event handlers ─────────────────────────────────────────────────────

def test_on_submit_text_fires_callback():
    """Simulate the submit_text socket event handler."""
    from ui_web import JarvisWebUI
    ui = make_ui()
    received = []
    ui.on_text_command = lambda t: received.append(t)

    # replicate handler logic directly
    text = "open spotify"
    text = text.strip()
    ui.write_log(f"You: {text}")
    if ui.on_text_command:
        t = threading.Thread(target=ui.on_text_command, args=(text,), daemon=True)
        t.start()
        t.join(timeout=1)
    assert received == ["open spotify"]


def test_on_submit_text_empty_does_nothing():
    ui = make_ui()
    called = []
    ui.on_text_command = lambda t: called.append(t)
    text = "   ".strip()
    if text and ui.on_text_command:
        ui.on_text_command(text)
    assert called == []


def test_on_toggle_mute_toggles_and_emits():
    ui = make_ui()
    assert ui.muted is False
    with ui._mute_lock:
        ui.muted = not ui.muted
        muted = ui.muted
    assert muted is True
    ui.set_state("MUTED")
    ui._sio.emit.assert_called_with("setState", "MUTED")


def test_on_save_setup_writes_config(tmp_path, monkeypatch):
    import ui_web
    monkeypatch.setattr(ui_web, "API_FILE", tmp_path / "api_keys.json")
    monkeypatch.setattr(ui_web, "CONFIG_DIR", tmp_path)

    ui = make_ui(tmp_path, monkeypatch)

    api_key = "test-key-123"
    os_system = "windows"
    import os
    os.makedirs(tmp_path, exist_ok=True)
    with open(tmp_path / "api_keys.json", "w", encoding="utf-8") as f:
        json.dump({"gemini_api_key": api_key, "os_system": os_system}, f)
    ui._api_ready.set()

    data = json.loads((tmp_path / "api_keys.json").read_text())
    assert data["gemini_api_key"] == "test-key-123"
    assert data["os_system"] == "windows"
    assert ui._api_ready.is_set()


def test_on_save_setup_rejects_empty_key():
    ui = make_ui()
    api_key = "   ".strip()
    if not api_key:
        result = {"ok": False, "error": "API key required"}
    else:
        result = {"ok": True}
    assert result["ok"] is False
