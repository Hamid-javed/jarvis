# JARVIS UI Redesign — Design Spec
**Date:** 2026-04-26

## Summary

Replace the current tkinter canvas-based UI with a pywebview-powered HTML/CSS interface. The new design is a sleek, modern dark-glass app with a 50/50 split layout, violet/indigo accent, and reactive animations that activate on AI state changes.

---

## Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Rendering | pywebview (local HTML) | True backdrop-filter blur, CSS animations, real glassmorphism — not achievable in tkinter |
| Direction | Sleek Modern | Dark glass panels, rounded corners, sans-serif — premium AI product feel |
| Layout | 50/50 split | Avatar panel (left) + chat panel (right) — avatar gets equal weight |
| Accent color | Violet / Indigo | `#6366f1` → `#8b5cf6` — sophisticated, modern AI aesthetic |
| Animation | Reactive | Subtle ambient idle; rich animations (orbit rings, scan arcs) only during LISTENING / THINKING / SPEAKING states |

---

## Architecture

The current `ui.py` (tkinter `JarvisUI` class) is replaced with two new files:

- **`ui_web.py`** — `JarvisWebUI` class: owns the pywebview window, exposes a Python API (`js_api`) to the HTML frontend, manages state transitions, bridges the existing `on_text_command` callback
- **`ui/index.html`** — the full HTML/CSS/JS frontend served as a local file
- **`main.py`** — swap `JarvisUI` → `JarvisWebUI`, no other changes

All existing action modules (`actions/`), agent modules (`agent/`), memory, and config are untouched.

---

## Left Panel — Avatar

**Idle state:**
- Avatar circle: 120px, `linear-gradient(135deg, #6366f1, #8b5cf6)`, `border-radius: 50%`
- Ambient glow: `radial-gradient` behind avatar, opacity ~0.18
- Breathing animation: subtle `scale(1.0) → scale(1.03)` + glow pulse, 3s cycle
- Waveform: 16 bars, very low amplitude, slow idle wave
- Status badge: pill with blinking dot + "LISTENING" / current state label
- Orbit rings: **hidden** at idle
- Model badge: "MARK XXXVII" at bottom, muted color

**Active states (LISTENING / THINKING / SPEAKING / PROCESSING):**
- 3 orbit rings appear with CSS `animation: spin-cw / spin-ccw` at varying speeds
- Ring opacity and speed scale with state intensity (SPEAKING = fastest)
- Waveform amplitude increases during SPEAKING
- Avatar glow intensity increases
- MUTED state: rings hidden, glow shifts to red-tinted, status badge red

**User photo:** if `face.png` / `face.jpg` exists in project root, render it inside the avatar circle clipped to `border-radius: 50%`. Otherwise show gradient orb.

---

## Right Panel — Chat

**Chat log:**
- Bubble layout: user messages right-aligned (`background: rgba(99,102,241,0.18)`), AI messages left-aligned (`background: rgba(255,255,255,0.05)`)
- Sender label above each bubble (small, uppercase, muted)
- System messages centered, no bubble, muted text
- Typewriter effect: JS `setInterval` character-by-character append on AI messages
- Typing indicator: 3 animated dots shown while AI is processing
- Auto-scroll to bottom on new message

**Input bar:**
- `<input>` field: `border-radius: 12px`, `border: 1px solid rgba(255,255,255,0.08)`, focus ring `rgba(99,102,241,0.5)`
- Send button: 36×36px, `border-radius: 10px`, gradient fill, arrow SVG icon
- `Enter` submits; `F4` toggles mute (via `window.addEventListener('keydown')`)
- Hint line below: "ENTER to send · F4 to mute" in muted text

---

## Title Bar

- macOS-style traffic lights (cosmetic, non-functional — close wired to `window.pywebview.api.close()`)
- Centered: "J · A · R · V · I · S" in spaced lettering
- Right: live clock updated every second via `setInterval`

---

## Python ↔ JS Bridge (`js_api`)

`JarvisWebUI` exposes these methods callable from JS:

| Method | Direction | Purpose |
|---|---|---|
| `submit_text(text)` | JS → Python | User sends a message |
| `toggle_mute()` | JS → Python | F4 / mute button |
| `close()` | JS → Python | Window close button |

Python calls JS via `window.evaluate_js(...)`:

| Call | Purpose |
|---|---|
| `appendMessage(sender, text, tag)` | Add message to chat log |
| `setState(state)` | Update avatar animations + status badge |
| `startTypewriter(text)` | Trigger typewriter on AI response |

---

## State Machine

States match current `set_state()` contract: `INITIALISING`, `LISTENING`, `THINKING`, `PROCESSING`, `SPEAKING`, `MUTED`, `ONLINE`.

JS `setState(state)` applies CSS classes to `<body data-state="...">`, driving all animation changes via CSS attribute selectors — no JS animation logic.

---

## Dependencies

Add to `requirements.txt`:
```
pywebview>=4.4
```

No other new dependencies. pywebview bundles a platform WebView (Edge WebView2 on Windows, WKWebView on macOS, WebKitGTK on Linux).

---

## Files Changed

| File | Change |
|---|---|
| `ui_web.py` | New — `JarvisWebUI` class |
| `ui/index.html` | New — full HTML/CSS/JS frontend |
| `main.py` | Import `JarvisWebUI`; replace `ui.root.mainloop()` with `webview.start(runner, daemon=True)` |
| `requirements.txt` | Add `pywebview>=4.4` |
| `ui.py` | Keep unchanged (fallback reference) |

## Interface Contract

`JarvisWebUI` must satisfy the same interface `JarvisLive` expects from the current `JarvisUI`:

| Attribute / Method | Type | Notes |
|---|---|---|
| `muted` | `bool` property | Read directly by `JarvisLive` audio callback |
| `on_text_command` | callable | Set by `JarvisLive.__init__` |
| `set_state(state)` | method | States: `INITIALISING LISTENING THINKING PROCESSING SPEAKING MUTED ONLINE` |
| `write_log(text)` | method | Triggers typewriter in frontend via `evaluate_js` |
| `wait_for_api_key()` | method | Blocks until config saved; setup screen still uses tkinter overlay or blocks in Python |
| `start_speaking()` / `stop_speaking()` | methods | Called by audio playback loop |

---

## Out of Scope

- Setup UI (API key entry) — keep existing tkinter setup screen for now, or port separately
- Voice wakeword / speech recognition changes
- Any action or agent logic
- Mobile / web deployment
