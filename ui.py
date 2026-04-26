import os, json, time, math, random, threading, platform
import tkinter as tk
from collections import deque
from PIL import Image, ImageTk, ImageDraw
import sys
from pathlib import Path


def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


BASE_DIR   = get_base_dir()
CONFIG_DIR = BASE_DIR / "config"
API_FILE   = CONFIG_DIR / "api_keys.json"

SYSTEM_NAME = "J · A · R · V · I · S"
MODEL_BADGE = "MARK XXXVII"

C_BG      = "#070711"
C_PRI     = "#6366f1"
C_MID     = "#8b5cf6"
C_DIM     = "#3d3f7a"
C_DIMMER  = "#0d0d1a"
C_ACC     = "#a78bfa"
C_ACC2    = "#c4b5fd"
C_TEXT    = "#e2e8f0"
C_PANEL   = "#080816"
C_GREEN   = "#22d3ee"
C_RED     = "#ef4444"
C_MUTED_C = "#ef4444"
C_BORDER  = "#1a1a3a"
C_YOUBG   = "#1e1b4b"
C_YOUFG   = "#c7d2fe"
C_AIBG    = "#111125"
C_AIFG    = "#e2e8f0"
C_SYSFG   = "#a78bfa"
C_ERRFG   = "#fca5a5"
C_ERRBG   = "#1a0a0a"
C_LABEL   = "#4b5580"
C_HDR_BG  = "#08080f"


class JarvisUI:
    def __init__(self, face_path, size=None):
        self.root = tk.Tk()
        self.root.title("J.A.R.V.I.S — MARK XXXVII")
        self.root.resizable(True, True)

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        W  = min(sw, 1100)
        H  = min(sh, 720)
        self.root.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")
        self.root.configure(bg=C_BG)

        self.W = W
        self.H = H
        HDR    = 36
        self.HDR = HDR
        LW     = W // 2
        self.LW = LW

        self.FACE_SZ = min(int((H - HDR) * 0.44), 260)
        self.FCX     = LW // 2
        self.FCY     = HDR + int((H - HDR) * 0.35)

        self.speaking     = False
        self.muted        = False
        self.scale        = 1.0
        self.target_scale = 1.0
        self.halo_a       = 60.0
        self.target_halo  = 60.0
        self.last_t       = time.time()
        self.tick         = 0
        self.scan_angle   = 0.0
        self.scan2_angle  = 180.0
        self.rings_spin   = [0.0, 120.0, 240.0]
        self.pulse_r      = [0.0, self.FACE_SZ * 0.26, self.FACE_SZ * 0.52]
        self.status_text  = "INITIALISING"
        self.status_blink = True
        self._jarvis_state = "INITIALISING"

        self.typing_queue = deque()
        self.is_typing    = False

        self.on_text_command = None

        self._face_pil         = None
        self._has_face         = False
        self._face_scale_cache = None
        self._load_face(face_path)

        self._build_header()
        self._build_left_canvas()
        self._build_divider()
        self._build_right_panel()
        self._build_mute_button()

        self.root.bind("<F4>", lambda e: self._toggle_mute())
        self.root.bind("<Configure>", self._on_resize)

        self._api_key_ready = self._api_keys_exist()
        if not self._api_key_ready:
            self._show_setup_ui()

        self._animate()
        self.root.protocol("WM_DELETE_WINDOW", lambda: os._exit(0))

    # ── Resize ────────────────────────────────────────────────────────────────

    def _on_resize(self, event):
        if event.widget is not self.root:
            return
        W, H = event.width, event.height
        if W == self.W and H == self.H:
            return
        self.W = W; self.H = H
        LW = W // 2; self.LW = LW
        self.FACE_SZ = min(int((H - self.HDR) * 0.44), 260)
        self.FCX     = LW // 2
        self.FCY     = self.HDR + int((H - self.HDR) * 0.35)
        self.hdr.config(width=W)
        self.bg.config(width=LW, height=H - self.HDR)
        self.div.place(x=LW, y=self.HDR, height=H - self.HDR)
        self.right_outer.place(x=LW + 1, y=self.HDR,
                               width=W - LW - 1, height=H - self.HDR)
        BTN_Y = H - 28 - 12
        self._mute_canvas.place(x=12, y=BTN_Y)
        self._update_chat_wrap()

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self):
        W, HDR = self.W, self.HDR
        self.hdr = tk.Canvas(self.root, width=W, height=HDR,
                              bg=C_HDR_BG, highlightthickness=0)
        self.hdr.place(x=0, y=0)
        self.hdr.create_line(0, HDR - 1, W, HDR - 1, fill=C_BORDER, width=1)
        self.hdr.create_text(W // 2, HDR // 2, text=SYSTEM_NAME,
                              fill=C_ACC2, font=("Segoe UI", 11, "bold"),
                              anchor="center")
        self.hdr.create_text(W - 14, HDR // 2, text=MODEL_BADGE,
                              fill=C_DIM, font=("Segoe UI", 8), anchor="e")
        self._clock_id = self.hdr.create_text(14, HDR // 2,
                                               text="00:00:00",
                                               fill=C_ACC, font=("Segoe UI", 9),
                                               anchor="w")
        self._tick_clock()

    def _tick_clock(self):
        self.hdr.itemconfigure(self._clock_id, text=time.strftime("%H:%M:%S"))
        self.root.after(1000, self._tick_clock)

    # ── Left canvas ───────────────────────────────────────────────────────────

    def _build_left_canvas(self):
        W, H, HDR, LW = self.W, self.H, self.HDR, self.LW
        self.bg = tk.Canvas(self.root, width=LW, height=H - HDR,
                             bg=C_BG, highlightthickness=0)
        self.bg.place(x=0, y=HDR)

    # ── Divider ───────────────────────────────────────────────────────────────

    def _build_divider(self):
        H, HDR, LW = self.H, self.HDR, self.LW
        self.div = tk.Frame(self.root, bg=C_BORDER, width=1)
        self.div.place(x=LW, y=HDR, height=H - HDR)

    # ── Right panel ───────────────────────────────────────────────────────────

    def _build_right_panel(self):
        W, H, HDR, LW = self.W, self.H, self.HDR, self.LW
        RW = W - LW - 1

        self.right_outer = tk.Frame(self.root, bg=C_PANEL)
        self.right_outer.place(x=LW + 1, y=HDR, width=RW, height=H - HDR)

        # ── Conversation header ──────────────────────────────────────────────
        hdr_frame = tk.Frame(self.right_outer, bg=C_PANEL)
        hdr_frame.pack(fill="x", padx=18, pady=(12, 0))
        tk.Label(hdr_frame, text="CONVERSATION",
                 fg=C_LABEL, bg=C_PANEL,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        tk.Frame(hdr_frame, bg=C_BORDER, height=1).pack(fill="x", pady=(6, 0))

        # ── Scrollable chat area ─────────────────────────────────────────────
        chat_container = tk.Frame(self.right_outer, bg=C_PANEL)
        chat_container.pack(fill="both", expand=True, pady=(6, 0))

        self._chat_canvas = tk.Canvas(chat_container, bg=C_PANEL,
                                      highlightthickness=0,
                                      bd=0)
        self._chat_canvas.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(chat_container, orient="vertical",
                                  command=self._chat_canvas.yview,
                                  bg=C_PANEL, troughcolor=C_PANEL,
                                  highlightthickness=0, borderwidth=0,
                                  width=6)
        scrollbar.pack(side="right", fill="y")
        self._chat_canvas.configure(yscrollcommand=scrollbar.set)

        self._msg_frame = tk.Frame(self._chat_canvas, bg=C_PANEL)
        self._chat_window = self._chat_canvas.create_window(
            (0, 0), window=self._msg_frame, anchor="nw"
        )

        self._msg_frame.bind("<Configure>", self._on_msg_frame_configure)
        self._chat_canvas.bind("<Configure>", self._on_chat_canvas_configure)

        # Mouse-wheel scroll
        self._chat_canvas.bind("<MouseWheel>",
            lambda e: self._chat_canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        # ── Input divider + area ─────────────────────────────────────────────
        tk.Frame(self.right_outer, bg=C_BORDER, height=1).pack(fill="x")

        input_outer = tk.Frame(self.right_outer, bg=C_PANEL, padx=14, pady=10)
        input_outer.pack(fill="x")

        input_row = tk.Frame(input_outer, bg=C_DIMMER,
                             highlightbackground=C_BORDER,
                             highlightthickness=1)
        input_row.pack(fill="x")

        self._input_var = tk.StringVar()
        self._input_entry = tk.Entry(
            input_row,
            textvariable=self._input_var,
            fg=C_TEXT, bg=C_DIMMER,
            insertbackground=C_ACC,
            borderwidth=0, relief="flat",
            font=("Segoe UI", 12),
            highlightthickness=0,
        )
        self._input_entry.pack(side="left", fill="x", expand=True,
                                ipady=8, padx=(12, 4))
        self._input_entry.bind("<Return>",   self._on_input_submit)
        self._input_entry.bind("<KP_Enter>", self._on_input_submit)
        self._input_entry.bind("<FocusIn>",
            lambda e: input_row.config(highlightbackground=C_MID))
        self._input_entry.bind("<FocusOut>",
            lambda e: input_row.config(highlightbackground=C_BORDER))

        self._send_btn = tk.Button(
            input_row,
            text="▶",
            command=self._on_input_submit,
            fg="#ffffff", bg=C_PRI,
            activeforeground="#ffffff", activebackground=C_MID,
            font=("Segoe UI", 11, "bold"),
            borderwidth=0, relief="flat", cursor="hand2",
            padx=14, pady=8,
        )
        self._send_btn.pack(side="right")

        tk.Label(input_outer, text="ENTER to send  ·  F4 to mute",
                 fg=C_LABEL, bg=C_PANEL,
                 font=("Segoe UI", 8)).pack(anchor="e", pady=(4, 0))

    def _on_msg_frame_configure(self, event):
        self._chat_canvas.configure(scrollregion=self._chat_canvas.bbox("all"))
        self._chat_canvas.yview_moveto(1.0)

    def _on_chat_canvas_configure(self, event):
        self._chat_canvas.itemconfig(self._chat_window, width=event.width)

    def _update_chat_wrap(self):
        RW = self.W - self.LW - 1
        wrap = max(200, int(RW * 0.70))
        for widget in self._msg_frame.winfo_children():
            for child in widget.winfo_children():
                if isinstance(child, tk.Label) and child.cget("wraplength") > 0:
                    child.configure(wraplength=wrap)

    # ── Mute button ───────────────────────────────────────────────────────────

    def _build_mute_button(self):
        BTN_W, BTN_H = 100, 28
        BTN_X = 12
        BTN_Y = self.H - BTN_H - 12

        self._mute_canvas = tk.Canvas(
            self.root, width=BTN_W, height=BTN_H,
            bg=C_BG, highlightthickness=0, cursor="hand2"
        )
        self._mute_canvas.place(x=BTN_X, y=BTN_Y)
        self._mute_canvas.bind("<Button-1>", lambda e: self._toggle_mute())
        self._draw_mute_button()

    def _draw_mute_button(self):
        c = self._mute_canvas
        c.delete("all")
        if self.muted:
            border, fill = C_MUTED_C, "#1a0010"
            icon, label, fg = "⊘", " MUTED", C_MUTED_C
        else:
            border, fill = C_DIM, C_DIMMER
            icon, label, fg = "●", " LIVE", C_GREEN

        c.create_rectangle(0, 0, 100, 28, outline=border, fill=fill, width=1)
        c.create_text(50, 14, text=f"{icon}{label}",
                      fill=fg, font=("Segoe UI", 9, "bold"))

    def _toggle_mute(self):
        self.muted = not self.muted
        self._draw_mute_button()
        if self.muted:
            self.set_state("MUTED")
            self.write_log("SYS: Microphone muted.")
        else:
            self.set_state("LISTENING")
            self.write_log("SYS: Microphone active.")

    # ── Input submit ──────────────────────────────────────────────────────────

    def _on_input_submit(self, event=None):
        text = self._input_var.get().strip()
        if not text:
            return
        self._input_var.set("")
        self.write_log(f"You: {text}")
        if self.on_text_command:
            threading.Thread(
                target=self.on_text_command,
                args=(text,),
                daemon=True
            ).start()

    # ── State machine ─────────────────────────────────────────────────────────

    def set_state(self, state: str):
        self._jarvis_state = state
        if state == "MUTED":
            self.status_text = "MUTED";    self.speaking = False
        elif state == "SPEAKING":
            self.status_text = "SPEAKING"; self.speaking = True
        elif state == "THINKING":
            self.status_text = "THINKING"; self.speaking = False
        elif state == "LISTENING":
            self.status_text = "LISTENING"; self.speaking = False
        elif state == "PROCESSING":
            self.status_text = "PROCESSING"; self.speaking = False
        else:
            self.status_text = "ONLINE";  self.speaking = False

    # ── Face loading ──────────────────────────────────────────────────────────

    def _load_face(self, path):
        FW = self.FACE_SZ
        try:
            img  = Image.open(path).convert("RGBA").resize((FW, FW), Image.LANCZOS)
            mask = Image.new("L", (FW, FW), 0)
            ImageDraw.Draw(mask).ellipse((2, 2, FW - 2, FW - 2), fill=255)
            img.putalpha(mask)
            self._face_pil = img
            self._has_face = True
        except Exception:
            self._has_face = False

    @staticmethod
    def _ac(r, g, b, a):
        f = a / 255.0
        return f"#{int(r*f):02x}{int(g*f):02x}{int(b*f):02x}"

    # ── Animation loop ────────────────────────────────────────────────────────

    def _animate(self):
        self.tick += 1
        t   = self.tick
        now = time.time()

        if now - self.last_t > (0.14 if self.speaking else 0.55):
            if self.speaking:
                self.target_scale = random.uniform(1.05, 1.11)
                self.target_halo  = random.uniform(138, 182)
            elif self.muted:
                self.target_scale = random.uniform(0.998, 1.001)
                self.target_halo  = random.uniform(20, 32)
            else:
                self.target_scale = random.uniform(1.001, 1.007)
                self.target_halo  = random.uniform(50, 68)
            self.last_t = now

        sp = 0.35 if self.speaking else 0.16
        self.scale  += (self.target_scale - self.scale) * sp
        self.halo_a += (self.target_halo  - self.halo_a) * sp

        for i, spd in enumerate([1.2, -0.8, 1.9] if self.speaking else [0.5, -0.3, 0.82]):
            self.rings_spin[i] = (self.rings_spin[i] + spd) % 360

        self.scan_angle  = (self.scan_angle  + (2.8 if self.speaking else 1.2)) % 360
        self.scan2_angle = (self.scan2_angle + (-1.7 if self.speaking else -0.68)) % 360

        pspd  = 3.8 if self.speaking else 1.8
        limit = self.FACE_SZ * 0.72
        new_p = [r + pspd for r in self.pulse_r if r + pspd < limit]
        if len(new_p) < 3 and random.random() < (0.06 if self.speaking else 0.022):
            new_p.append(0.0)
        self.pulse_r = new_p

        if t % 40 == 0:
            self.status_blink = not self.status_blink

        self._draw()
        self.root.after(16, self._animate)

    def _draw(self):
        c   = self.bg
        LW  = self.LW
        H   = self.H - self.HDR
        t   = self.tick
        FCX = self.FCX
        FCY = self.FCY - self.HDR
        FW  = self.FACE_SZ
        c.delete("all")

        # Background dot grid
        for x in range(0, LW, 44):
            for y in range(0, H, 44):
                c.create_rectangle(x, y, x + 1, y + 1, fill=C_DIMMER, outline="")

        # Ambient halo rings
        for r in range(int(FW * 0.54), int(FW * 0.28), -22):
            frac = 1.0 - (r - FW * 0.28) / (FW * 0.26)
            ga   = max(0, min(255, int(self.halo_a * 0.09 * frac)))
            gh   = f"{ga:02x}"
            if self.muted:
                c.create_oval(FCX - r, FCY - r, FCX + r, FCY + r,
                              outline=f"#{gh}0030", width=2)
            else:
                c.create_oval(FCX - r, FCY - r, FCX + r, FCY + r,
                              outline=f"#{gh}{gh}ff", width=2)

        # Pulse rings
        for pr in self.pulse_r:
            pa = max(0, int(220 * (1.0 - pr / (FW * 0.72))))
            r  = int(pr)
            if self.muted:
                c.create_oval(FCX - r, FCY - r, FCX + r, FCY + r,
                              outline=self._ac(239, 68, 68, pa // 3), width=2)
            else:
                c.create_oval(FCX - r, FCY - r, FCX + r, FCY + r,
                              outline=self._ac(99, 102, 241, pa), width=2)

        # Orbit arc rings
        for idx, (r_frac, w_ring, arc_l, gap) in enumerate([
                (0.47, 3, 110, 75), (0.39, 2, 75, 55), (0.31, 1, 55, 38)]):
            ring_r = int(FW * r_frac)
            base_a = self.rings_spin[idx]
            a_val  = max(0, min(255, int(self.halo_a * (1.0 - idx * 0.18))))
            if self.muted:
                col = self._ac(239, 68, 68, a_val)
            elif idx == 0:
                col = self._ac(99, 102, 241, a_val)
            elif idx == 1:
                col = self._ac(139, 92, 246, a_val)
            else:
                col = self._ac(167, 139, 250, a_val)
            for s in range(360 // (arc_l + gap)):
                start = (base_a + s * (arc_l + gap)) % 360
                c.create_arc(FCX - ring_r, FCY - ring_r, FCX + ring_r, FCY + ring_r,
                             start=start, extent=arc_l,
                             outline=col, width=w_ring, style="arc")

        # Scan arc
        sr      = int(FW * 0.49)
        scan_a  = min(255, int(self.halo_a * 1.4))
        arc_ext = 70 if self.speaking else 42
        scan_col = self._ac(239, 68, 68, scan_a) if self.muted else self._ac(99, 102, 241, scan_a)
        c.create_arc(FCX - sr, FCY - sr, FCX + sr, FCY + sr,
                     start=self.scan_angle, extent=arc_ext,
                     outline=scan_col, width=3, style="arc")
        c.create_arc(FCX - sr, FCY - sr, FCX + sr, FCY + sr,
                     start=self.scan2_angle, extent=arc_ext,
                     outline=self._ac(167, 139, 250, scan_a // 2), width=2, style="arc")

        # Tick marks
        t_out = int(FW * 0.495)
        t_in  = int(FW * 0.472)
        a_mk  = self._ac(99, 102, 241, 120)
        for deg in range(0, 360, 10):
            rad = math.radians(deg)
            inn = t_in if deg % 30 == 0 else t_in + 5
            c.create_line(FCX + t_out * math.cos(rad), FCY - t_out * math.sin(rad),
                          FCX + inn  * math.cos(rad), FCY - inn  * math.sin(rad),
                          fill=a_mk, width=1)

        # Crosshair
        ch_r = int(FW * 0.50)
        gap  = int(FW * 0.15)
        ch_a = self._ac(99, 102, 241, int(self.halo_a * 0.55))
        for x1, y1, x2, y2 in [
                (FCX - ch_r, FCY, FCX - gap, FCY), (FCX + gap, FCY, FCX + ch_r, FCY),
                (FCX, FCY - ch_r, FCX, FCY - gap), (FCX, FCY + gap, FCX, FCY + ch_r)]:
            c.create_line(x1, y1, x2, y2, fill=ch_a, width=1)

        # Corner brackets
        blen = 18
        bc   = self._ac(99, 102, 241, 180)
        hl = FCX - FW // 2; hr = FCX + FW // 2
        ht = FCY - FW // 2; hb = FCY + FW // 2
        for bx, by, sdx, sdy in [(hl, ht, 1, 1), (hr, ht, -1, 1),
                                   (hl, hb, 1, -1), (hr, hb, -1, -1)]:
            c.create_line(bx, by, bx + sdx * blen, by,              fill=bc, width=2)
            c.create_line(bx, by, bx,               by + sdy * blen, fill=bc, width=2)

        # Face or orb
        if self._has_face:
            fw = int(FW * self.scale)
            if (self._face_scale_cache is None or
                    abs(self._face_scale_cache[0] - self.scale) > 0.004):
                scaled = self._face_pil.resize((fw, fw), Image.BILINEAR)
                tk_img = ImageTk.PhotoImage(scaled)
                self._face_scale_cache = (self.scale, tk_img)
            c.create_image(FCX, FCY, image=self._face_scale_cache[1])
        else:
            orb_r = int(FW * 0.27 * self.scale)
            orb_color = (239, 68, 68) if self.muted else (61, 63, 122)
            for i in range(7, 0, -1):
                r2   = int(orb_r * i / 7)
                frac = i / 7
                ga   = max(0, min(255, int(self.halo_a * 1.1 * frac)))
                c.create_oval(FCX - r2, FCY - r2, FCX + r2, FCY + r2,
                              fill=self._ac(int(orb_color[0] * frac),
                                            int(orb_color[1] * frac),
                                            int(orb_color[2] * frac), ga),
                              outline="")
            c.create_text(FCX, FCY, text="J.A.R.V.I.S",
                          fill=self._ac(99, 102, 241, min(255, int(self.halo_a * 2))),
                          font=("Segoe UI", 12, "bold"))

        # Status badge
        sy = FCY + FW // 2 + 36
        if self.muted:
            stat, sc = "⊘  MUTED", C_MUTED_C
        elif self.speaking:
            stat, sc = "●  SPEAKING", C_PRI
        elif self._jarvis_state == "THINKING":
            sym  = "◈" if self.status_blink else "◇"
            stat, sc = f"{sym}  THINKING", C_ACC2
        elif self._jarvis_state == "PROCESSING":
            sym  = "▷" if self.status_blink else "▶"
            stat, sc = f"{sym}  PROCESSING", C_ACC2
        elif self._jarvis_state == "LISTENING":
            sym  = "●" if self.status_blink else "○"
            stat, sc = f"{sym}  LISTENING", C_GREEN
        else:
            sym  = "●" if self.status_blink else "○"
            stat, sc = f"{sym}  {self.status_text}", C_ACC

        c.create_text(LW // 2, sy, text=stat,
                      fill=sc, font=("Segoe UI", 10, "bold"))

        # Waveform bars
        wy = sy + 22
        N  = 28
        BH = 16
        bw = 6
        total_w = N * bw
        wx0 = (LW - total_w) // 2
        for i in range(N):
            if self.muted:
                hb  = 2
                col = self._ac(239, 68, 68, 80)
            elif self.speaking:
                hb  = random.randint(3, BH)
                col = self._ac(99, 102, 241, 200) if hb > BH * 0.6 else self._ac(139, 92, 246, 160)
            else:
                hb  = int(3 + 2 * math.sin(t * 0.08 + i * 0.55))
                col = self._ac(61, 63, 122, 140)
            bx = wx0 + i * bw
            c.create_rectangle(bx, wy + BH - hb, bx + bw - 1, wy + BH,
                                fill=col, outline="")

    # ── Chat / bubble messages ────────────────────────────────────────────────

    def _add_bubble(self, tag: str, text: str):
        """Add a message bubble to the scrollable chat area (must run on main thread)."""
        RW   = self.W - self.LW - 1
        wrap = max(200, int(RW * 0.68))

        outer = tk.Frame(self._msg_frame, bg=C_PANEL)
        outer.pack(fill="x", padx=14, pady=(4, 0))

        if tag == "sys":
            tk.Label(outer, text=text, fg=C_SYSFG, bg=C_PANEL,
                     font=("Segoe UI", 9, "italic"),
                     wraplength=wrap, justify="center").pack(anchor="center")
            return

        if tag == "you":
            sender_text = "YOU"
            sender_fg   = C_LABEL
            bubble_bg   = C_YOUBG
            bubble_fg   = C_YOUFG
            side        = "right"
            anchor      = "e"
        elif tag == "err":
            sender_text = "ERROR"
            sender_fg   = C_ERRFG
            bubble_bg   = C_ERRBG
            bubble_fg   = C_ERRFG
            side        = "left"
            anchor      = "w"
        else:  # ai
            sender_text = "JARVIS"
            sender_fg   = C_LABEL
            bubble_bg   = C_AIBG
            bubble_fg   = C_AIFG
            side        = "left"
            anchor      = "w"

        # Sender label
        tk.Label(outer, text=sender_text,
                 fg=sender_fg, bg=C_PANEL,
                 font=("Segoe UI", 8, "bold")).pack(anchor=anchor, padx=2)

        # Bubble frame (border simulation via inner frame)
        if tag == "ai":
            border_frame = tk.Frame(outer, bg=C_PRI)
            border_frame.pack(anchor=anchor)
            bubble = tk.Frame(border_frame, bg=bubble_bg)
            bubble.pack(padx=(2, 0), pady=0)
        else:
            bubble = tk.Frame(outer, bg=bubble_bg)
            bubble.pack(anchor=anchor)

        tk.Label(bubble, text=text,
                 fg=bubble_fg, bg=bubble_bg,
                 font=("Segoe UI", 11),
                 wraplength=wrap, justify="left" if tag != "you" else "right",
                 padx=12, pady=7).pack()

    def _scroll_to_bottom(self):
        self._chat_canvas.update_idletasks()
        self._chat_canvas.yview_moveto(1.0)

    # ── Public write_log ──────────────────────────────────────────────────────

    def write_log(self, text: str):
        self.typing_queue.append(text)
        tl = text.lower()
        if tl.startswith("you:"):
            self.set_state("PROCESSING")
        elif tl.startswith("jarvis:") or tl.startswith("ai:"):
            self.set_state("SPEAKING")
        if not self.is_typing:
            self._start_typing()

    def _start_typing(self):
        if not self.typing_queue:
            self.is_typing = False
            if not self.speaking and not self.muted:
                self.set_state("LISTENING")
            return
        self.is_typing = True
        text = self.typing_queue.popleft()
        tl   = text.lower()

        if tl.startswith("you:"):
            tag, body = "you", text[4:].strip()
        elif tl.startswith("jarvis:") or tl.startswith("ai:"):
            colon = text.index(":")
            tag, body = "ai", text[colon + 1:].strip()
        elif tl.startswith("err:") or "error" in tl or "failed" in tl:
            tag, body = "err", text
        else:
            tag, body = "sys", text

        if tag in ("you", "err", "sys"):
            self._add_bubble(tag, body)
            self._scroll_to_bottom()
            self.root.after(25, self._start_typing)
        else:
            # Typewriter effect for AI
            self._start_typewriter(body)

    def _start_typewriter(self, text: str):
        RW   = self.W - self.LW - 1
        wrap = max(200, int(RW * 0.68))

        outer = tk.Frame(self._msg_frame, bg=C_PANEL)
        outer.pack(fill="x", padx=14, pady=(4, 0))

        tk.Label(outer, text="JARVIS",
                 fg=C_LABEL, bg=C_PANEL,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=2)

        border_frame = tk.Frame(outer, bg=C_PRI)
        border_frame.pack(anchor="w")
        bubble = tk.Frame(border_frame, bg=C_AIBG)
        bubble.pack(padx=(2, 0), pady=0)

        lbl = tk.Label(bubble, text="",
                       fg=C_AIFG, bg=C_AIBG,
                       font=("Segoe UI", 11),
                       wraplength=wrap, justify="left",
                       padx=12, pady=7)
        lbl.pack()

        self._scroll_to_bottom()
        self._type_into_label(lbl, text, 0)

    def _type_into_label(self, lbl, text, i):
        if i < len(text):
            lbl.configure(text=text[:i + 1])
            self._scroll_to_bottom()
            self.root.after(10, self._type_into_label, lbl, text, i + 1)
        else:
            self.root.after(25, self._start_typing)

    def start_speaking(self):
        self.set_state("SPEAKING")

    def stop_speaking(self):
        if not self.muted:
            self.set_state("LISTENING")

    # ── API key helpers ───────────────────────────────────────────────────────

    def _api_keys_exist(self) -> bool:
        if not API_FILE.exists():
            return False
        try:
            data = json.loads(API_FILE.read_text(encoding="utf-8"))
            return bool(data.get("gemini_api_key")) and bool(data.get("os_system"))
        except Exception:
            return False

    def start(self):
        self.root.mainloop()

    def wait_for_api_key(self):
        while not self._api_key_ready:
            time.sleep(0.1)

    @staticmethod
    def _detect_os() -> str:
        s = platform.system().lower()
        if s == "darwin": return "mac"
        if s == "windows": return "windows"
        return "linux"

    # ── Setup overlay ─────────────────────────────────────────────────────────

    def _show_setup_ui(self):
        detected = self._detect_os()
        self._selected_os = tk.StringVar(value=detected)

        self.setup_frame = tk.Frame(
            self.root, bg="#0d0d18",
            highlightbackground=C_PRI, highlightthickness=1
        )
        self.setup_frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(self.setup_frame, text="◈  INITIALISATION REQUIRED",
                 fg=C_ACC, bg="#0d0d18",
                 font=("Segoe UI", 13, "bold")).pack(pady=(22, 2))
        tk.Label(self.setup_frame, text="Configure J.A.R.V.I.S. before first boot.",
                 fg=C_DIM, bg="#0d0d18",
                 font=("Segoe UI", 9)).pack(pady=(0, 16))
        tk.Label(self.setup_frame, text="GEMINI API KEY",
                 fg=C_DIM, bg="#0d0d18",
                 font=("Segoe UI", 9, "bold")).pack(pady=(0, 3))

        self.gemini_entry = tk.Entry(
            self.setup_frame, width=48,
            fg=C_TEXT, bg=C_DIMMER,
            insertbackground=C_ACC,
            borderwidth=0, font=("Segoe UI", 10), show="*",
            highlightthickness=1,
            highlightbackground=C_BORDER,
            highlightcolor=C_MID,
        )
        self.gemini_entry.pack(pady=(0, 20), ipady=5)

        tk.Frame(self.setup_frame, bg=C_BORDER, height=1).pack(fill="x", padx=24, pady=(0, 14))
        tk.Label(self.setup_frame, text="SELECT OPERATING SYSTEM",
                 fg=C_DIM, bg="#0d0d18",
                 font=("Segoe UI", 9, "bold")).pack(pady=(0, 4))

        detect_label = {"windows": "Windows", "mac": "macOS", "linux": "Linux"}.get(detected, detected.capitalize())
        tk.Label(self.setup_frame, text=f"Auto-detected: {detect_label}",
                 fg=C_ACC2, bg="#0d0d18",
                 font=("Segoe UI", 8)).pack(pady=(0, 10))

        os_btn_frame = tk.Frame(self.setup_frame, bg="#0d0d18")
        os_btn_frame.pack(pady=(0, 20))

        self._os_buttons = {}
        for os_key, os_label in [("windows", "⊞ Windows"), ("mac", " macOS"), ("linux", "🐧 Linux")]:
            btn = tk.Button(os_btn_frame, text=os_label, width=12,
                            font=("Segoe UI", 10), borderwidth=0, cursor="hand2", pady=7,
                            command=lambda k=os_key: self._select_os(k))
            btn.pack(side="left", padx=6)
            self._os_buttons[os_key] = btn

        self._select_os(detected)

        tk.Frame(self.setup_frame, bg=C_BORDER, height=1).pack(fill="x", padx=24, pady=(0, 16))
        tk.Button(self.setup_frame, text="▶  INITIALISE SYSTEMS",
                  command=self._save_api_keys,
                  bg=C_PRI, fg="#ffffff",
                  activebackground=C_MID, activeforeground="#ffffff",
                  font=("Segoe UI", 10, "bold"),
                  borderwidth=0, pady=10, padx=20, cursor="hand2").pack(pady=(0, 22))

    def _select_os(self, os_key: str):
        self._selected_os.set(os_key)
        styles = {"windows": (C_PRI, C_DIMMER), "mac": (C_ACC2, "#1a1500"), "linux": (C_GREEN, "#001a10")}
        for key, btn in self._os_buttons.items():
            if key == os_key:
                fg, _ = styles[key]
                btn.configure(fg="#ffffff" if key != "mac" else "#000000",
                              bg=fg, activeforeground="#ffffff",
                              activebackground=fg, relief="flat")
            else:
                btn.configure(fg=C_DIM, bg=C_DIMMER,
                              activeforeground=C_TEXT,
                              activebackground=C_BORDER, relief="flat")

    def _save_api_keys(self):
        gemini = self.gemini_entry.get().strip()
        if not gemini:
            self.gemini_entry.configure(highlightbackground=C_RED, highlightcolor=C_RED)
            return
        os_system = self._selected_os.get()
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(API_FILE, "w", encoding="utf-8") as f:
            json.dump({"gemini_api_key": gemini, "os_system": os_system}, f, indent=4)
        self.setup_frame.destroy()
        self._api_key_ready = True
        self.set_state("LISTENING")
        self.write_log(f"SYS: Systems initialised. OS → {os_system.upper()}. JARVIS online.")
