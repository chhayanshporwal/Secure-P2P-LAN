import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import os
import sys
import time
import json
import getpass
import subprocess
import socket

# Import our secure protocol, daemon, and audit manager
from sender import send_file_with_resume
from service_daemon import daemon_instance
from history_manager import HistoryManager
from receiver import add_receive_listener

# -------------------------------------------------------------
# Standard Desktop Typography & Sizing Constants
# -------------------------------------------------------------
# Platform-Specific Sleek Typography & Layout Metrics
# (Compact & sleek on Windows; standard & readable on macOS)
# -------------------------------------------------------------
IS_MAC = sys.platform == "darwin"

if IS_MAC:
    FONT_TITLE = ("Helvetica", 14, "bold")
    FONT_SUBTITLE = ("Helvetica", 10)
    FONT_CARD_TITLE = ("Helvetica", 11, "bold")
    FONT_HEADER = ("Helvetica", 11, "bold")
    FONT_LABEL_BOLD = ("Helvetica", 10, "bold")
    FONT_LABEL = ("Helvetica", 10)
    FONT_STAT = ("Helvetica", 13, "bold")
    FONT_BTN = ("Helvetica", 10, "bold")
    FONT_BTN_SM = ("Helvetica", 9, "bold")
    FONT_MONO = ("Menlo", 9)
    TREE_ROW_HEIGHT = 26
    WIN_GEOMETRY = "720x640"
    WIN_MINSIZE = (660, 520)
    BTN_PADX = 12
    BTN_PADY = 5
    BTN_BD = 2
else:
    FONT_TITLE = ("Segoe UI", 11, "bold")
    FONT_SUBTITLE = ("Segoe UI", 8)
    FONT_CARD_TITLE = ("Segoe UI", 9, "bold")
    FONT_HEADER = ("Segoe UI", 9, "bold")
    FONT_LABEL_BOLD = ("Segoe UI", 9, "bold")
    FONT_LABEL = ("Segoe UI", 9)
    FONT_STAT = ("Segoe UI", 11, "bold")
    FONT_BTN = ("Segoe UI", 9, "bold")
    FONT_BTN_SM = ("Segoe UI", 8, "bold")
    FONT_MONO = ("Consolas", 8)
    TREE_ROW_HEIGHT = 22
    WIN_GEOMETRY = "680x600"
    WIN_MINSIZE = (620, 480)
    BTN_PADX = 10
    BTN_PADY = 4
    BTN_BD = 2


def get_lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


def format_size(num_bytes):
    """Dynamically formats byte count to B, KB, MB, or GB."""
    if num_bytes is None or num_bytes <= 0:
        return "0 B"
    num_bytes = float(num_bytes)
    if num_bytes < 1024:
        return f"{int(num_bytes)} B"
    elif num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    elif num_bytes < 1024 * 1024 * 1024:
        return f"{num_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{num_bytes / (1024 ** 3):.2f} GB"


def format_speed(speed_mbps):
    """Always format transfer speed in MB/s (MBPS)."""
    if speed_mbps is None or speed_mbps <= 0:
        return "0.00 MB/s"
    return f"{speed_mbps:.2f} MB/s"


def format_duration(seconds):
    """
    Dynamically formats seconds into human-readable e.g.
    '3min 4sec', '18sec', '1hr 5min 12sec', or '0.5s'.
    """
    if seconds is None or seconds < 0:
        return "--"
    seconds = float(seconds)
    if seconds < 1.0:
        return f"{seconds:.2f}s" if seconds > 0 else "0s"

    total_sec = int(round(seconds))
    if total_sec < 60:
        return f"{total_sec}sec"

    minutes, sec = divmod(total_sec, 60)
    if minutes < 60:
        if sec > 0:
            return f"{minutes}min {sec}sec"
        return f"{minutes}min"

    hours, minutes = divmod(minutes, 60)
    parts = [f"{hours}hr"]
    if minutes > 0:
        parts.append(f"{minutes}min")
    if sec > 0:
        parts.append(f"{sec}sec")
    return " ".join(parts)


def format_eta(seconds):
    """Dynamically formats ETA seconds into e.g. '3min 4sec', '12sec', 'Done'."""
    if seconds is None or seconds <= 0:
        return "Done"
    return format_duration(seconds)


def get_project_root():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    base = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(base) == "src":
        return os.path.dirname(base)
    return base


def get_received_files_dir():
    save_dir = os.path.join(get_project_root(), "received_files")
    os.makedirs(save_dir, exist_ok=True)
    return save_dir


CONFIG_FILE = os.path.join(get_project_root(), "config.json")


def load_user_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    default_name = getpass.getuser().capitalize() if hasattr(getpass, 'getuser') else "User"
    return {"display_name": default_name, "last_receiver_ip": "192.168.x.x"}


def save_user_config(cfg):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass


# -------------------------------------------------------------
# Cross-Platform High-Contrast Button with Defined Boundaries
# -------------------------------------------------------------
class ModernButton(tk.Label):
    """
    A custom label-based button that renders vibrant colors, crisp fonts,
    clearly visible 3D boundaries, and responsive tactile press states.
    """
    def __init__(self, parent, text="", command=None, bg="#059669", fg="#ffffff",
                 hover_bg=None, font=None, padx=None, pady=None, state=tk.NORMAL,
                 relief=tk.RAISED, bd=None, **kwargs):
        self.command = command
        self.normal_bg = bg
        self.hover_bg = hover_bg or self._calc_hover(bg)
        self.active_bg = self._calc_active(bg)
        self.normal_fg = fg
        self._state = state
        self.normal_relief = relief
        self.normal_bd = bd if bd is not None else BTN_BD
        self.disabled_bg = "#e2e8f0"
        self.disabled_fg = "#94a3b8"

        current_bg = self.disabled_bg if state == tk.DISABLED else self.normal_bg
        current_fg = self.disabled_fg if state == tk.DISABLED else self.normal_fg
        current_relief = tk.GROOVE if state == tk.DISABLED else self.normal_relief
        cursor = "hand2" if state == tk.NORMAL else "arrow"

        btn_font = font if font is not None else FONT_BTN
        btn_padx = padx if padx is not None else BTN_PADX
        btn_pady = pady if pady is not None else BTN_PADY

        super().__init__(
            parent, text=text, bg=current_bg, fg=current_fg,
            font=btn_font, padx=btn_padx, pady=btn_pady, cursor=cursor,
            relief=current_relief, bd=self.normal_bd, **kwargs
        )
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _calc_hover(self, hex_color):
        try:
            h = hex_color.lstrip('#')
            rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
            darker = tuple(max(0, int(c * 0.90)) for c in rgb)
            return f"#{darker[0]:02x}{darker[1]:02x}{darker[2]:02x}"
        except Exception:
            return hex_color

    def _calc_active(self, hex_color):
        try:
            h = hex_color.lstrip('#')
            rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
            darker = tuple(max(0, int(c * 0.72)) for c in rgb)
            return f"#{darker[0]:02x}{darker[1]:02x}{darker[2]:02x}"
        except Exception:
            return hex_color

    def _on_enter(self, event=None):
        if self._state == tk.NORMAL:
            self.configure(bg=self.hover_bg, relief=self.normal_relief)

    def _on_leave(self, event=None):
        if self._state == tk.NORMAL:
            self.configure(bg=self.normal_bg, relief=self.normal_relief)

    def _on_press(self, event=None):
        if self._state == tk.NORMAL:
            self.configure(bg=self.active_bg, relief=tk.SUNKEN)

    def _on_release(self, event=None):
        if self._state == tk.NORMAL:
            self.configure(bg=self.hover_bg, relief=self.normal_relief)
            if self.command:
                self.command()

    def cget(self, key):
        if key == "state":
            return self._state
        return super().cget(key)

    def __getitem__(self, key):
        if key == "state":
            return self._state
        return super().__getitem__(key)

    def config(self, **kwargs):
        if "state" in kwargs:
            self._state = kwargs.pop("state")
            if self._state == tk.DISABLED:
                super().config(bg=self.disabled_bg, fg=self.disabled_fg, cursor="arrow", relief=tk.GROOVE)
            else:
                super().config(bg=self.normal_bg, fg=self.normal_fg, cursor="hand2", relief=self.normal_relief)
        if "text" in kwargs:
            super().config(text=kwargs.pop("text"))
        if "bg" in kwargs:
            self.normal_bg = kwargs.pop("bg")
            self.hover_bg = self._calc_hover(self.normal_bg)
            self.active_bg = self._calc_active(self.normal_bg)
            if self._state == tk.NORMAL:
                super().config(bg=self.normal_bg)
        if "fg" in kwargs:
            self.normal_fg = kwargs.pop("fg")
            if self._state == tk.NORMAL:
                super().config(fg=self.normal_fg)
        if "command" in kwargs:
            self.command = kwargs.pop("command")
        if kwargs:
            super().config(**kwargs)

    configure = config


# -------------------------------------------------------------
# Individual Transfer Sub-Tab
# -------------------------------------------------------------
class TransferSubTab(tk.Frame):
    def __init__(self, parent, tab_id, app):
        super().__init__(parent, bg="#f8fafc")
        self.tab_id = tab_id
        self.app = app

        self.filepath = None
        self.transfer_start_time = None
        self.last_update_time = 0
        self.last_sent_bytes = 0

        self.pause_event = threading.Event()
        self.pause_event.set()
        self.cancel_event = threading.Event()
        self.is_transferring = False
        self.is_paused = False

        self.build_tab_ui()

    def update_tab_id(self, new_id):
        self.tab_id = new_id
        if hasattr(self, 'file_card'):
            self.file_card.config(text=f" 📁 File Payload (Transfer #{self.tab_id}) ")

    def build_tab_ui(self):
        # 1. Responsive Scrollable Canvas Container
        self.canvas = tk.Canvas(self, bg="#f8fafc", highlightthickness=0, bd=0)
        self.v_scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.v_scrollbar.set)

        self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Inner container frame mounted on Canvas
        self.container = tk.Frame(self.canvas, bg="#f8fafc", padx=14, pady=10)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.container, anchor="nw")

        # Dynamic resizing & scrolling bindings
        self.container.bind("<Configure>", self._on_container_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self._bind_mousewheel_recursive(self.canvas)
        self._bind_mousewheel_recursive(self)

        # 2. Receiver Peer Configuration Card
        srv_card = tk.LabelFrame(
            self.container,
            text=" 🌐 Receiver Peer Configuration ",
            font=FONT_CARD_TITLE,
            fg="#0f172a",
            bg="#ffffff",
            bd=1,
            relief=tk.GROOVE,
            padx=12,
            pady=8
        )
        srv_card.pack(fill=tk.X, pady=(0, 10))

        tk.Label(srv_card, text="Target Receiver IP:", font=FONT_LABEL_BOLD, bg="#ffffff", fg="#0f172a").pack(side=tk.LEFT)
        self.ip_entry = tk.Entry(
            srv_card,
            font=FONT_LABEL,
            bg="#ffffff",
            fg="#0f172a",
            insertbackground="#0f172a",
            selectbackground="#0284c7",
            selectforeground="#ffffff",
            disabledbackground="#f1f5f9",
            disabledforeground="#94a3b8",
            relief=tk.SOLID,
            bd=1
        )
        self.ip_entry.insert(0, self.app.config.get("last_receiver_ip", "192.168.x.x"))
        self.ip_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0), ipady=3)

        # 3. File Selection Card
        self.file_card = tk.LabelFrame(
            self.container,
            text=f" 📁 File Payload (Transfer #{self.tab_id}) ",
            font=FONT_CARD_TITLE,
            fg="#0f172a",
            bg="#ffffff",
            bd=1,
            relief=tk.GROOVE,
            padx=12,
            pady=8
        )
        self.file_card.pack(fill=tk.X, pady=(0, 10))

        file_top = tk.Frame(self.file_card, bg="#ffffff")
        file_top.pack(fill=tk.X)

        self.browse_btn = ModernButton(
            file_top,
            text="Browse File...",
            command=self.browse_file,
            font=FONT_BTN_SM,
            bg="#2563eb",
            fg="#ffffff",
            hover_bg="#1d4ed8",
            padx=BTN_PADX,
            pady=BTN_PADY
        )
        self.browse_btn.pack(side=tk.LEFT)

        self.file_label = tk.Label(
            file_top,
            text="No file selected",
            font=FONT_LABEL_BOLD,
            fg="#0f172a",
            bg="#ffffff",
            anchor="w"
        )
        self.file_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))

        # 4. Transfer Monitor Card
        self.mon_card = tk.LabelFrame(
            self.container,
            text=" 📊 Transfer Monitor ",
            font=FONT_CARD_TITLE,
            fg="#0f172a",
            bg="#ffffff",
            bd=1,
            relief=tk.GROOVE,
            padx=12,
            pady=8
        )
        self.mon_card.pack(fill=tk.X, pady=(0, 10))

        stats_top = tk.Frame(self.mon_card, bg="#ffffff")
        stats_top.pack(fill=tk.X, pady=(0, 2))

        self.pct_label = tk.Label(stats_top, text="0%", font=FONT_STAT, fg="#0f172a", bg="#ffffff")
        self.pct_label.pack(side=tk.LEFT)

        self.bytes_label = tk.Label(stats_top, text="0 B / 0 B", font=FONT_LABEL_BOLD, fg="#0f172a", bg="#ffffff")
        self.bytes_label.pack(side=tk.RIGHT)

        # Progress Bar
        self.progress_bar = ttk.Progressbar(
            self.mon_card,
            orient="horizontal",
            mode="determinate",
            style="Custom.Horizontal.TProgressbar"
        )
        self.progress_bar.pack(fill=tk.X, pady=5)

        stats_bottom = tk.Frame(self.mon_card, bg="#ffffff")
        stats_bottom.pack(fill=tk.X, pady=(2, 0))

        self.speed_label = tk.Label(stats_bottom, text="⚡ Speed: 0.00 MB/s", font=FONT_LABEL_BOLD, fg="#0284c7", bg="#ffffff")
        self.speed_label.pack(side=tk.LEFT)

        self.eta_label = tk.Label(stats_bottom, text="⏱️ ETA: --", font=FONT_LABEL_BOLD, fg="#0f172a", bg="#ffffff")
        self.eta_label.pack(side=tk.RIGHT)

        # 5. Status Banner
        self.status_box = tk.Frame(self.container, bg="#e0f2fe", bd=1, relief=tk.SOLID, padx=10, pady=6)
        self.status_box.pack(fill=tk.X, pady=(0, 10))

        self.status_label = tk.Label(
            self.status_box,
            text="Ready: Enter the Receiver's IP and choose a file to begin.",
            font=FONT_LABEL_BOLD,
            fg="#0369a1",
            bg="#e0f2fe",
            justify=tk.LEFT,
            anchor="w"
        )
        self.status_label.pack(anchor="w", fill=tk.X, expand=True)
        self.status_box.bind("<Configure>", lambda e: self.status_label.config(wraplength=max(200, e.width - 20)))

        # 6. Interactive Control Action Buttons Row
        ctrl_frame = tk.Frame(self.container, bg="#f8fafc")
        ctrl_frame.pack(fill=tk.X, pady=(0, 10))

        # Send Button
        self.send_btn = ModernButton(
            ctrl_frame,
            text="🔒 Send Securely",
            command=self.start_transfer,
            font=FONT_BTN,
            bg="#059669",
            fg="#ffffff",
            hover_bg="#047857",
            padx=BTN_PADX + 4,
            pady=BTN_PADY + 2
        )
        self.send_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        # Pause / Resume Button
        self.pause_btn = ModernButton(
            ctrl_frame,
            text="⏸️ Pause",
            command=self.toggle_pause,
            font=FONT_BTN,
            bg="#0284c7",
            fg="#ffffff",
            hover_bg="#0369a1",
            padx=BTN_PADX,
            pady=BTN_PADY + 2,
            state=tk.DISABLED
        )
        self.pause_btn.pack(side=tk.LEFT, padx=3)

        # Cancel Button
        self.cancel_btn = ModernButton(
            ctrl_frame,
            text="🛑 Cancel",
            command=self.cancel_transfer,
            font=FONT_BTN,
            bg="#dc2626",
            fg="#ffffff",
            hover_bg="#b91c1c",
            padx=BTN_PADX,
            pady=BTN_PADY + 2,
            state=tk.DISABLED
        )
        self.cancel_btn.pack(side=tk.LEFT, padx=3)

        # Close Tab Button
        self.close_btn = ModernButton(
            ctrl_frame,
            text="✖ Close Tab",
            command=self.close_tab,
            font=FONT_BTN,
            bg="#64748b",
            fg="#ffffff",
            hover_bg="#475569",
            padx=BTN_PADX,
            pady=BTN_PADY + 2
        )
        self.close_btn.pack(side=tk.LEFT, padx=(3, 0))

        # 7. Live Transfer Activity & Security Log (Expands to fill extra vertical height)
        self.log_card = tk.LabelFrame(
            self.container,
            text=" 🛡️ Live Transfer Activity & Security Log ",
            font=FONT_CARD_TITLE,
            fg="#0f172a",
            bg="#ffffff",
            bd=1,
            relief=tk.GROOVE,
            padx=10,
            pady=6
        )
        self.log_card.pack(fill=tk.BOTH, expand=True, pady=(0, 2))

        self.log_text = tk.Text(
            self.log_card,
            height=5,
            font=FONT_MONO,
            bg="#0f172a",
            fg="#38bdf8",
            insertbackground="#38bdf8",
            relief=tk.FLAT,
            padx=8,
            pady=6,
            wrap=tk.WORD
        )
        log_scroll = ttk.Scrollbar(self.log_card, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.log_text.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] P2P Client initialized. Hybrid Cryptography Engine ready.\n")
        self.log_text.config(state=tk.DISABLED)

        # Recursively bind mousewheel to all nested widgets so scrolling works anywhere
        self._bind_mousewheel_recursive(self.container)
        self.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", self._on_mousewheel))
        self.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))

    def _on_container_configure(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        min_h = self.container.winfo_reqheight()
        new_h = max(event.height, min_h)
        self.canvas.itemconfig(self.canvas_window, width=event.width, height=new_h)

    def _bind_mousewheel_recursive(self, widget):
        widget.bind("<MouseWheel>", self._on_mousewheel, add="+")
        widget.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"), add="+")
        widget.bind("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"), add="+")
        for child in widget.winfo_children():
            if not isinstance(child, (tk.Text, ttk.Treeview)):
                self._bind_mousewheel_recursive(child)

    def _on_mousewheel(self, event):
        try:
            if sys.platform == "darwin":
                self.canvas.yview_scroll(int(-1 * event.delta), "units")
            else:
                units = int(-1 * (event.delta / 120))
                if units == 0:
                    units = -1 if event.delta > 0 else 1
                self.canvas.yview_scroll(units, "units")
        except Exception:
            pass

    def append_log(self, message):
        def _apply():
            if hasattr(self, 'log_text'):
                try:
                    self.log_text.config(state=tk.NORMAL)
                    ts = time.strftime("%H:%M:%S")
                    self.log_text.insert(tk.END, f"[{ts}] {message}\n")
                    self.log_text.see(tk.END)
                    self.log_text.config(state=tk.DISABLED)
                except Exception:
                    pass
        self.after(0, _apply)

    def browse_file(self):
        if self.is_transferring: return
        self.filepath = filedialog.askopenfilename()
        if self.filepath:
            size_bytes = os.path.getsize(self.filepath)
            name = os.path.basename(self.filepath)
            self.file_label.config(text=f"{name} ({format_size(size_bytes)})", fg="#0f172a", font=FONT_LABEL_BOLD)
            self.reset_progress(size_bytes)
            self.append_log(f"Selected payload: '{name}' ({format_size(size_bytes)})")

    def reset_progress(self, size_bytes=0):
        self.progress_bar['value'] = 0
        self.pct_label.config(text="0%")
        self.bytes_label.config(text=f"0 B / {format_size(size_bytes)}")
        self.speed_label.config(text="⚡ Speed: 0.00 MB/s")
        self.eta_label.config(text="⏱️ ETA: --")

    def update_status(self, text):
        def _apply():
            if "Interrupted" in text or "Retrying" in text:
                self.status_box.config(bg="#fef3c7")
                self.status_label.config(text=f"⚠️ {text}", fg="#92400e", bg="#fef3c7")
            elif "Complete" in text or "Verified" in text:
                self.status_box.config(bg="#dcfce7")
                self.status_label.config(text=f"✅ {text}", fg="#166534", bg="#dcfce7")
            elif "Cancelled" in text:
                self.status_box.config(bg="#fee2e2")
                self.status_label.config(text=f"🛑 {text}", fg="#991b1b", bg="#fee2e2")
            elif "Paused" in text:
                self.status_box.config(bg="#fef3c7")
                self.status_label.config(text=f"⏸️ {text}", fg="#b45309", bg="#fef3c7")
            elif "Error" in text or "Failed" in text:
                self.status_box.config(bg="#fee2e2")
                self.status_label.config(text=f"❌ {text}", fg="#991b1b", bg="#fee2e2")
            elif "queue" in text.lower() or "capacity" in text.lower():
                self.status_box.config(bg="#ede9fe")
                self.status_label.config(text=f"{text}", fg="#5b21b6", bg="#ede9fe")
            else:
                self.status_box.config(bg="#e0f2fe")
                self.status_label.config(text=f"🔄 {text}", fg="#0369a1", bg="#e0f2fe")
        self.after(0, _apply)
        self.append_log(text)

    def update_progress(self, sent, total):
        now = time.time()
        if sent < total and (now - self.last_update_time) < 0.06:
            return

        pct = int((sent / total) * 100) if total > 0 else 0
        elapsed = now - self.transfer_start_time if self.transfer_start_time else 0.001
        speed_mbps = (sent / (1024 * 1024)) / elapsed if elapsed > 0 else 0
        remaining_bytes = total - sent
        eta_seconds = (remaining_bytes / (speed_mbps * 1024 * 1024)) if speed_mbps > 0 else 0

        self.last_update_time = now
        self.last_sent_bytes = sent

        def _apply():
            self.progress_bar['value'] = pct
            self.pct_label.config(text=f"{pct}%")
            self.bytes_label.config(text=f"{format_size(sent)} / {format_size(total)}")
            self.speed_label.config(text=f"⚡ Speed: {format_speed(speed_mbps)}")
            self.eta_label.config(text=f"⏱️ ETA: {format_eta(eta_seconds)}")

        self.after(0, _apply)

    def toggle_pause(self):
        if not self.is_transferring: return
        if not self.is_paused:
            self.pause_event.clear()
            self.is_paused = True
            self.pause_btn.config(text="▶️ Resume", bg="#0284c7")
            self.update_status("Transfer Paused by user.")
        else:
            self.pause_event.set()
            self.is_paused = False
            self.pause_btn.config(text="⏸️ Pause", bg="#0284c7")
            self.update_status("Transfer Resumed.")

    def cancel_transfer(self):
        if not self.is_transferring: return
        confirm = messagebox.askyesno("Cancel Transfer", f"Cancel Transfer #{self.tab_id}?\nStaged data on receiver will be purged immediately for atomicity.")
        if confirm:
            self.cancel_event.set()
            self.pause_event.set()
            self.update_status("Cancelling transfer and purging staged data...")

    def close_tab(self):
        if self.is_transferring:
            messagebox.showwarning("Active Transfer", "Please pause or cancel the active transfer before closing this tab.")
            return
        self.app.remove_send_tab(self)

    def start_transfer(self):
        dest_ip = self.ip_entry.get().strip()
        if not dest_ip or dest_ip == "192.168.x.x":
            messagebox.showerror("IP Missing", "Please enter the Target Receiver's IP address.")
            return
        if not self.filepath:
            messagebox.showerror("No File Selected", "Please select a file to transfer.")
            return

        self.app.config["last_receiver_ip"] = dest_ip
        save_user_config(self.app.config)

        self.is_transferring = True
        self.is_paused = False
        self.pause_event.set()
        self.cancel_event.clear()

        self.send_btn.config(state=tk.DISABLED, text="Encrypting & Sending...")
        self.browse_btn.config(state=tk.DISABLED)
        self.pause_btn.config(state=tk.NORMAL, text="⏸️ Pause", bg="#0284c7")
        self.cancel_btn.config(state=tk.NORMAL)
        self.close_btn.config(state=tk.DISABLED)

        self.transfer_start_time = time.time()
        self.last_update_time = time.time()
        self.update_status("Connecting to Receiver Peer...")

        sender_name = self.app.display_name_var.get().strip() or "User"
        threading.Thread(target=self.run_transfer, args=(dest_ip, self.filepath, sender_name), daemon=True).start()

    def run_transfer(self, dest_ip, filepath, sender_name):
        try:
            send_file_with_resume(
                dest_ip,
                5000,
                filepath,
                status_cb=self.update_status,
                progress_cb=self.update_progress,
                pause_event=self.pause_event,
                cancel_event=self.cancel_event,
                sender_name=sender_name
            )
            self.update_status("Transfer Complete! Atomic Commit Verified.")
            self.after(0, lambda: messagebox.showinfo(
                "Transfer Successful",
                f"File '{os.path.basename(filepath)}' in Transfer #{self.tab_id} was successfully encrypted with AES-256-GCM and transferred!"
            ))
            self.after(0, self.app.refresh_history)
        except Exception as e:
            if self.cancel_event.is_set():
                self.update_status("Transfer Cancelled. Staged data purged (Atomicity).")
            else:
                self.update_status(f"Failed: {e}")
                self.after(0, lambda: messagebox.showerror("Transfer Error", f"Transfer #{self.tab_id} halted: {e}"))
            self.after(0, self.app.refresh_history)
        finally:
            self.is_transferring = False
            self.is_paused = False
            self.after(0, self.reset_controls)

    def reset_controls(self):
        self.send_btn.config(state=tk.NORMAL, text="🔒 Send Securely")
        self.browse_btn.config(state=tk.NORMAL)
        self.pause_btn.config(state=tk.DISABLED, text="⏸️ Pause", bg="#0284c7")
        self.cancel_btn.config(state=tk.DISABLED)
        self.close_btn.config(state=tk.NORMAL)


# -------------------------------------------------------------
# Main Application GUI
# -------------------------------------------------------------
class SecureClientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Secure P2P Client (Hybrid AES-ECC + Audit Log)")
        self.root.geometry(WIN_GEOMETRY)
        self.root.minsize(WIN_MINSIZE[0], WIN_MINSIZE[1])
        self.root.configure(bg="#f1f5f9")

        # Load configuration
        self.config = load_user_config()
        self.my_ip = get_lan_ip()

        self.display_name_var = tk.StringVar(value=self.config.get("display_name", "User"))
        self.service_status_var = tk.StringVar(value="Checking...")

        self.send_tabs = []

        # Real-time Receive Notification State
        self.pending_notifications = []
        self.active_popup = None
        self.popup_timer_id = None
        add_receive_listener(self.on_file_received_event)

        # Configure TTK Styles for Modern Desktop
        self.style = ttk.Style()
        if "clam" in self.style.theme_names():
            self.style.theme_use("clam")

        self.style.configure(
            "Custom.Horizontal.TProgressbar",
            troughcolor="#e2e8f0",
            background="#10b981",
            darkcolor="#059669",
            lightcolor="#34d399",
            bordercolor="#cbd5e1",
            thickness=18
        )

        self.style.configure(
            "TNotebook",
            background="#f1f5f9",
            borderwidth=0
        )
        self.style.configure(
            "TNotebook.Tab",
            font=FONT_LABEL_BOLD,
            padding=(16, 8),
            background="#e2e8f0",
            foreground="#0f172a"
        )
        self.style.map(
            "TNotebook.Tab",
            background=[("selected", "#ffffff")],
            foreground=[("selected", "#0f172a")]
        )

        self.style.configure(
            "Treeview",
            font=FONT_LABEL,
            rowheight=TREE_ROW_HEIGHT,
            background="#ffffff",
            fieldbackground="#ffffff",
            foreground="#0f172a"
        )
        self.style.configure(
            "Treeview.Heading",
            font=FONT_LABEL_BOLD,
            foreground="#0f172a",
            background="#e2e8f0",
            padding=(6, 6)
        )

        self.build_main_ui()

        # Auto-start the background receiver daemon (Zero Terminal Friction!)
        self.start_background_engine()

        # Handle clean window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def build_main_ui(self):
        # 1. Header Banner (Profile, IP, Service Status)
        header = tk.Frame(self.root, bg="#0f172a", height=88)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        top_row = tk.Frame(header, bg="#0f172a")
        top_row.pack(fill=tk.X, padx=18, pady=(8, 0))

        # Title & Security Badge
        title_frame = tk.Frame(top_row, bg="#0f172a")
        title_frame.pack(side=tk.LEFT)

        title_lbl = tk.Label(
            title_frame,
            text="🛡️ Secure P2P Client",
            font=FONT_TITLE,
            fg="#f8fafc",
            bg="#0f172a"
        )
        title_lbl.pack(anchor="w")

        sub_lbl = tk.Label(
            title_frame,
            text="Blackbox P2P Transfer (ECDH P-256 + AES-256-GCM + Atomicity)",
            font=FONT_SUBTITLE,
            fg="#cbd5e1",
            bg="#0f172a"
        )
        sub_lbl.pack(anchor="w")

        # Service Online Badge & Toggle
        srv_status_frame = tk.Frame(top_row, bg="#0f172a")
        srv_status_frame.pack(side=tk.RIGHT)

        self.srv_lbl = tk.Label(
            srv_status_frame,
            textvariable=self.service_status_var,
            font=FONT_LABEL_BOLD,
            fg="#4ade80",
            bg="#0f172a"
        )
        self.srv_lbl.pack(side=tk.LEFT, padx=(0, 10))

        self.srv_toggle_btn = ModernButton(
            srv_status_frame,
            text="Stop Service",
            command=self.toggle_service,
            font=FONT_BTN_SM,
            bg="#334155",
            fg="#ffffff",
            hover_bg="#1e293b",
            padx=10,
            pady=4
        )
        self.srv_toggle_btn.pack(side=tk.LEFT)

        # Bottom Row of Header: Display Name & My IP
        info_row = tk.Frame(header, bg="#0f172a")
        info_row.pack(fill=tk.X, padx=18, pady=(4, 6))

        # Editable Display Name
        tk.Label(info_row, text="My Display Name:", font=FONT_LABEL, fg="#cbd5e1", bg="#0f172a").pack(side=tk.LEFT)
        self.name_entry = tk.Entry(
            info_row,
            textvariable=self.display_name_var,
            font=FONT_LABEL_BOLD,
            width=18,
            bg="#1e293b",
            fg="#ffffff",
            insertbackground="#ffffff",
            selectbackground="#0284c7",
            selectforeground="#ffffff",
            relief=tk.SOLID,
            bd=1
        )
        self.name_entry.pack(side=tk.LEFT, padx=(8, 18), ipady=2)
        self.name_entry.bind("<FocusOut>", self.save_name_change)
        self.name_entry.bind("<Return>", self.save_name_change)

        # My Local IP & Copy Button
        tk.Label(info_row, text=f"My LAN IP: {self.my_ip}", font=FONT_LABEL_BOLD, fg="#38bdf8", bg="#0f172a").pack(side=tk.LEFT)
        copy_btn = ModernButton(
            info_row,
            text="📋 Copy IP",
            command=self.copy_ip,
            font=FONT_BTN_SM,
            bg="#38bdf8",
            fg="#0f172a",
            hover_bg="#7dd3fc",
            padx=10,
            pady=3
        )
        copy_btn.pack(side=tk.LEFT, padx=(10, 0))

        # 2. Main Tabbed Navigation
        self.main_notebook = ttk.Notebook(self.root)
        self.main_notebook.pack(fill=tk.BOTH, expand=True, padx=14, pady=(10, 14))

        # Main Page 1: Send Files Tab (Contains multi-tab senders)
        self.send_page = tk.Frame(self.main_notebook, bg="#f1f5f9")
        self.main_notebook.add(self.send_page, text="   📤 Send Files (P2P Queue)   ")

        # Main Page 2: History & Audit Log Tab
        self.history_page = tk.Frame(self.main_notebook, bg="#f1f5f9")
        self.main_notebook.add(self.history_page, text="   📜 History & Audit Logs   ")

        # Build Send Page UI
        self.build_send_page_ui()

        # Build History Page UI
        self.build_history_page_ui()

        # Bind tab change to refresh history automatically
        self.main_notebook.bind("<<NotebookTabChanged>>", self.on_main_tab_changed)

    def build_send_page_ui(self):
        # Top toolbar for Send Page
        top_bar = tk.Frame(self.send_page, bg="#f1f5f9")
        top_bar.pack(fill=tk.X, padx=12, pady=(10, 6))

        tk.Label(
            top_bar,
            text="Active File Transfers:",
            font=FONT_HEADER,
            fg="#0f172a",
            bg="#f1f5f9"
        ).pack(side=tk.LEFT)

        add_tab_btn = ModernButton(
            top_bar,
            text="➕ New Transfer Tab",
            command=self.add_send_tab,
            font=FONT_BTN,
            bg="#0284c7",
            fg="#ffffff",
            hover_bg="#0369a1",
            padx=14,
            pady=6
        )
        add_tab_btn.pack(side=tk.RIGHT)

        # Sub-notebook for multiple concurrent sending tabs
        self.sub_notebook = ttk.Notebook(self.send_page)
        self.sub_notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        # Initial Send Tab
        self.add_send_tab()

    def reindex_tabs(self):
        """Ensures tab labels and card titles are strictly sequential and relative (1..N)."""
        for index, tab in enumerate(self.send_tabs, start=1):
            tab.update_tab_id(index)
            self.sub_notebook.tab(tab, text=f"  Transfer #{index}  ")

    def add_send_tab(self):
        next_id = len(self.send_tabs) + 1
        tab_frame = TransferSubTab(self.sub_notebook, next_id, self)
        self.sub_notebook.add(tab_frame, text=f"  Transfer #{next_id}  ")
        self.send_tabs.append(tab_frame)
        self.reindex_tabs()
        self.sub_notebook.select(tab_frame)

    def remove_send_tab(self, tab_frame):
        if len(self.send_tabs) <= 1:
            messagebox.showinfo("Notice", "At least one transfer tab must remain open.")
            return
        self.sub_notebook.forget(tab_frame)
        self.send_tabs.remove(tab_frame)
        self.reindex_tabs()

    def build_history_page_ui(self):
        h_container = tk.Frame(self.history_page, bg="#f1f5f9", padx=16, pady=14)
        h_container.pack(fill=tk.BOTH, expand=True)

        # Top Bar with Title and Actions
        h_top = tk.Frame(h_container, bg="#f1f5f9")
        h_top.pack(fill=tk.X, pady=(0, 10))

        tk.Label(
            h_top,
            text="Audit Trail & Transfer Log:",
            font=FONT_HEADER,
            fg="#0f172a",
            bg="#f1f5f9"
        ).pack(side=tk.LEFT)

        btn_frame = tk.Frame(h_top, bg="#f1f5f9")
        btn_frame.pack(side=tk.RIGHT)

        open_folder_btn = ModernButton(
            btn_frame,
            text="📂 Open Received Folder",
            command=self.open_received_folder,
            font=FONT_BTN_SM,
            bg="#0284c7",
            fg="#ffffff",
            hover_bg="#0369a1",
            padx=12,
            pady=5
        )
        open_folder_btn.pack(side=tk.LEFT, padx=4)

        refresh_btn = ModernButton(
            btn_frame,
            text="🔄 Refresh",
            command=self.refresh_history,
            font=FONT_BTN_SM,
            bg="#334155",
            fg="#ffffff",
            hover_bg="#1e293b",
            padx=10,
            pady=5
        )
        refresh_btn.pack(side=tk.LEFT, padx=4)

        clear_btn = ModernButton(
            btn_frame,
            text="🗑️ Clear",
            command=self.clear_history_log,
            font=FONT_BTN_SM,
            bg="#dc2626",
            fg="#ffffff",
            hover_bg="#b91c1c",
            padx=10,
            pady=5
        )
        clear_btn.pack(side=tk.LEFT, padx=(4, 0))

        # Responsive Treeview Table
        table_frame = tk.Frame(h_container, bg="#ffffff", bd=1, relief=tk.SOLID)
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("id", "direction", "peer", "file", "size", "timestamp", "duration", "speed", "status")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("id", text="#")
        self.tree.heading("direction", text="Direction")
        self.tree.heading("peer", text="Peer (Name / IP)")
        self.tree.heading("file", text="Filename")
        self.tree.heading("size", text="Size")
        self.tree.heading("timestamp", text="Date & Time")
        self.tree.heading("duration", text="Time Taken")
        self.tree.heading("speed", text="Throughput (MB/s)")
        self.tree.heading("status", text="Status")

        # Responsive column widths with stretch=True on main text columns
        self.tree.column("id", width=40, minwidth=35, anchor="center", stretch=False)
        self.tree.column("direction", width=95, minwidth=80, anchor="center", stretch=False)
        self.tree.column("peer", width=160, minwidth=120, anchor="w", stretch=True)
        self.tree.column("file", width=200, minwidth=140, anchor="w", stretch=True)
        self.tree.column("size", width=100, minwidth=80, anchor="e", stretch=False)
        self.tree.column("timestamp", width=155, minwidth=130, anchor="center", stretch=False)
        self.tree.column("duration", width=110, minwidth=85, anchor="center", stretch=False)
        self.tree.column("speed", width=120, minwidth=95, anchor="e", stretch=False)
        self.tree.column("status", width=110, minwidth=90, anchor="center", stretch=False)

        # Scrollbars
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.refresh_history()

    def on_main_tab_changed(self, event):
        selected_tab = self.main_notebook.tab(self.main_notebook.select(), "text")
        if "History" in selected_tab:
            self.refresh_history()

    def refresh_history(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        records = HistoryManager().get_all_records(limit=200)
        for r in records:
            dir_badge = "📤 SENT" if r["direction"] == "SENT" else "📥 RECV"
            peer_str = f"{r['peer_name']} ({r['peer_ip']})"
            size_str = format_size(r['filesize'])
            speed_str = format_speed(r['speed_mbps']) if r['speed_mbps'] > 0 else "--"
            dur_str = format_duration(r['duration_sec']) if r['duration_sec'] > 0 else "--"

            self.tree.insert("", "end", values=(
                r["id"],
                dir_badge,
                peer_str,
                r["filename"],
                size_str,
                r["timestamp"],
                dur_str,
                speed_str,
                r["status"]
            ))

    def clear_history_log(self):
        confirm = messagebox.askyesno("Clear History", "Are you sure you want to clear all transfer audit records?")
        if confirm:
            HistoryManager().clear_history()
            self.refresh_history()

    def open_received_folder(self):
        save_dir = get_received_files_dir()
        if sys.platform == "darwin":
            subprocess.Popen(["open", save_dir])
        elif sys.platform == "win32":
            os.startfile(save_dir)
        else:
            subprocess.Popen(["xdg-open", save_dir])

    def save_name_change(self, event=None):
        name = self.display_name_var.get().strip() or "User"
        self.config["display_name"] = name
        save_user_config(self.config)

    def copy_ip(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.my_ip)
        messagebox.showinfo("IP Copied", f"Your IP address '{self.my_ip}' was copied to clipboard!\nShare this with your friend so they can transfer files to you.")

    def start_background_engine(self):
        try:
            daemon_instance.start(lb_port=5000, worker_ports=[5001, 5002, 5003])
            self.service_status_var.set("🟢 Receiver Service: Online (Port 5000)")
            self.srv_lbl.config(fg="#4ade80")
            self.srv_toggle_btn.config(text="Stop Service")
        except Exception as e:
            self.service_status_var.set("🔴 Receiver Service: Offline")
            self.srv_lbl.config(fg="#f87171")
            self.srv_toggle_btn.config(text="Start Service")

    def toggle_service(self):
        if daemon_instance.is_running():
            daemon_instance.stop()
            self.service_status_var.set("🔴 Receiver Service: Offline")
            self.srv_lbl.config(fg="#f87171")
            self.srv_toggle_btn.config(text="Start Service")
        else:
            self.start_background_engine()

    def on_file_received_event(self, sender_name, peer_ip, filename, filesize):
        self.root.after(0, self.handle_file_received_notification, sender_name, peer_ip, filename, filesize)

    def handle_file_received_notification(self, sender_name, peer_ip, filename, filesize):
        self.refresh_history()
        self.pending_notifications.append({
            "sender_name": sender_name,
            "peer_ip": peer_ip,
            "filename": filename,
            "filesize": filesize,
            "time": time.time()
        })
        self.show_receive_popup()

    def show_receive_popup(self):
        if self.popup_timer_id:
            try:
                self.root.after_cancel(self.popup_timer_id)
            except Exception:
                pass
            self.popup_timer_id = None

        if self.active_popup:
            try:
                self.active_popup.destroy()
            except Exception:
                pass
            self.active_popup = None

        count = len(self.pending_notifications)
        if count == 0:
            return

        senders = sorted(list(set(item["sender_name"] for item in self.pending_notifications)))
        senders_str = ", ".join(senders)

        if count == 1:
            item = self.pending_notifications[0]
            title_text = "📥 New File Received!"
            body_headline = f"'{item['filename']}' ({format_size(item['filesize'])})"
            sub_headline = f"From: {item['sender_name']} ({item['peer_ip']})"
        else:
            title_text = f"📥 {count} Files Received!"
            body_headline = f"{count} files received from {senders_str}"
            latest = self.pending_notifications[-1]
            sub_headline = f"Latest: '{latest['filename']}' ({format_size(latest['filesize'])})"

        popup = tk.Toplevel(self.root)
        self.active_popup = popup
        popup.title("P2P File Transfer Notification")
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)

        popup_w, popup_h = 420, 150
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = max(10, screen_w - popup_w - 30)
        y = max(10, screen_h - popup_h - 50)
        popup.geometry(f"{popup_w}x{popup_h}+{x}+{y}")

        # Modern Card Container with Accent Border
        card = tk.Frame(popup, bg="#0f172a", bd=2, relief=tk.SOLID, highlightbackground="#10b981", highlightthickness=2)
        card.pack(fill=tk.BOTH, expand=True)

        # Header Row
        header_f = tk.Frame(card, bg="#0f172a")
        header_f.pack(fill=tk.X, padx=14, pady=(10, 4))

        title_lbl = tk.Label(header_f, text=title_text, font=FONT_LABEL_BOLD, fg="#10b981", bg="#0f172a", cursor="hand2")
        title_lbl.pack(side=tk.LEFT)
        title_lbl.bind("<Button-1>", lambda e: self.navigate_to_history_from_popup())

        close_btn = ModernButton(
            header_f,
            text="✖",
            command=self.close_notification_popup,
            font=FONT_BTN_SM,
            bg="#0f172a",
            fg="#94a3b8",
            hover_bg="#1e293b",
            padx=8,
            pady=2
        )
        close_btn.pack(side=tk.RIGHT)

        # Middle Content Row (Clickable)
        content_f = tk.Frame(card, bg="#0f172a", cursor="hand2")
        content_f.pack(fill=tk.X, padx=14, pady=(2, 8))
        content_f.bind("<Button-1>", lambda e: self.navigate_to_history_from_popup())

        body_lbl = tk.Label(content_f, text=body_headline, font=FONT_LABEL_BOLD, fg="#f8fafc", bg="#0f172a", anchor="w", wraplength=380, justify=tk.LEFT)
        body_lbl.pack(fill=tk.X)
        body_lbl.bind("<Button-1>", lambda e: self.navigate_to_history_from_popup())

        sub_lbl = tk.Label(content_f, text=sub_headline, font=FONT_SUBTITLE, fg="#94a3b8", bg="#0f172a", anchor="w", wraplength=380, justify=tk.LEFT)
        sub_lbl.pack(fill=tk.X, pady=(2, 0))
        sub_lbl.bind("<Button-1>", lambda e: self.navigate_to_history_from_popup())

        # Action Buttons Row
        actions_f = tk.Frame(card, bg="#0f172a")
        actions_f.pack(fill=tk.X, padx=14, pady=(4, 10))

        history_btn = ModernButton(
            actions_f,
            text="📜 View Full History",
            command=self.navigate_to_history_from_popup,
            font=FONT_BTN_SM,
            bg="#10b981",
            fg="#ffffff",
            hover_bg="#059669",
            padx=12,
            pady=5
        )
        history_btn.pack(side=tk.LEFT, padx=(0, 8))

        folder_btn = ModernButton(
            actions_f,
            text="📂 Open Folder",
            command=self.open_received_folder,
            font=FONT_BTN_SM,
            bg="#334155",
            fg="#ffffff",
            hover_bg="#1e293b",
            padx=10,
            pady=5
        )
        folder_btn.pack(side=tk.LEFT)

        # Auto-dismiss after 20 seconds
        self.popup_timer_id = self.root.after(20000, self.close_notification_popup)

    def navigate_to_history_from_popup(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.main_notebook.select(self.history_page)
        self.refresh_history()
        self.close_notification_popup()

    def close_notification_popup(self):
        if self.popup_timer_id:
            try:
                self.root.after_cancel(self.popup_timer_id)
            except Exception:
                pass
            self.popup_timer_id = None

        if self.active_popup:
            try:
                self.active_popup.destroy()
            except Exception:
                pass
            self.active_popup = None
        self.pending_notifications.clear()

    def on_close(self):
        self.close_notification_popup()
        daemon_instance.stop()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = SecureClientGUI(root)
    root.mainloop()
