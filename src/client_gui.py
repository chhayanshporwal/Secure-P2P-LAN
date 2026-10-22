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

def format_gb(num_bytes):
    gb = num_bytes / (1024 ** 3)
    if gb >= 0.01:
        return f"{gb:.3f} GB"
    elif gb > 0:
        return f"{gb:.4f} GB"
    return "0.000 GB"

def format_gbps(gbps):
    if gbps >= 0.01:
        return f"{gbps:.3f} GB/s"
    elif gbps > 0:
        return f"{gbps:.4f} GB/s"
    return "0.000 GB/s"

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

    def build_tab_ui(self):
        container = tk.Frame(self, bg="#f8fafc", padx=16, pady=12)
        container.pack(fill=tk.BOTH, expand=True)

        # 1. Receiver Configuration Card
        srv_card = tk.LabelFrame(
            container,
            text=" 🌐 Receiver Peer Configuration ",
            font=("Arial", 9, "bold"),
            fg="#334155",
            bg="#ffffff",
            bd=1,
            relief=tk.SOLID,
            padx=10,
            pady=6
        )
        srv_card.pack(fill=tk.X, pady=(0, 8))

        tk.Label(srv_card, text="Target Receiver IP:", font=("Arial", 9, "bold"), bg="#ffffff", fg="#475569").pack(side=tk.LEFT)
        self.ip_entry = tk.Entry(srv_card, font=("Arial", 9), bg="#f8fafc", relief=tk.SOLID, bd=1)
        self.ip_entry.insert(0, self.app.config.get("last_receiver_ip", "192.168.x.x"))
        self.ip_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0), ipady=2)

        # 2. File Selection Card
        file_card = tk.LabelFrame(
            container,
            text=f" 📁 File Payload (Transfer #{self.tab_id}) ",
            font=("Arial", 9, "bold"),
            fg="#334155",
            bg="#ffffff",
            bd=1,
            relief=tk.SOLID,
            padx=10,
            pady=8
        )
        file_card.pack(fill=tk.X, pady=(0, 8))

        file_top = tk.Frame(file_card, bg="#ffffff")
        file_top.pack(fill=tk.X)

        self.browse_btn = tk.Button(
            file_top,
            text="Browse File...",
            command=self.browse_file,
            font=("Arial", 9, "bold"),
            bg="#e2e8f0",
            fg="#1e293b",
            relief=tk.RAISED,
            padx=8,
            pady=2,
            cursor="hand2"
        )
        self.browse_btn.pack(side=tk.LEFT)

        self.file_label = tk.Label(
            file_top,
            text="No file selected",
            font=("Arial", 9, "italic"),
            fg="#64748b",
            bg="#ffffff",
            anchor="w"
        )
        self.file_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))

        # 3. Transfer Monitor Card
        self.mon_card = tk.LabelFrame(
            container,
            text=" 📊 Transfer Monitor ",
            font=("Arial", 9, "bold"),
            fg="#334155",
            bg="#ffffff",
            bd=1,
            relief=tk.SOLID,
            padx=10,
            pady=8
        )
        self.mon_card.pack(fill=tk.X, pady=(0, 8))

        stats_top = tk.Frame(self.mon_card, bg="#ffffff")
        stats_top.pack(fill=tk.X, pady=(0, 2))

        self.pct_label = tk.Label(stats_top, text="0%", font=("Arial", 11, "bold"), fg="#0f172a", bg="#ffffff")
        self.pct_label.pack(side=tk.LEFT)

        self.bytes_label = tk.Label(stats_top, text="0.000 GB / 0.000 GB", font=("Arial", 9), fg="#64748b", bg="#ffffff")
        self.bytes_label.pack(side=tk.RIGHT)

        # Progress Bar
        self.progress_bar = ttk.Progressbar(
            self.mon_card,
            orient="horizontal",
            mode="determinate",
            style="Custom.Horizontal.TProgressbar"
        )
        self.progress_bar.pack(fill=tk.X, pady=3)

        stats_bottom = tk.Frame(self.mon_card, bg="#ffffff")
        stats_bottom.pack(fill=tk.X, pady=(2, 0))

        self.speed_label = tk.Label(stats_bottom, text="⚡ Speed: 0.000 GB/s", font=("Arial", 9), fg="#475569", bg="#ffffff")
        self.speed_label.pack(side=tk.LEFT)

        self.eta_label = tk.Label(stats_bottom, text="⏱️ ETA: --", font=("Arial", 9), fg="#475569", bg="#ffffff")
        self.eta_label.pack(side=tk.RIGHT)

        # 4. Status Banner
        self.status_box = tk.Frame(container, bg="#e0f2fe", bd=1, relief=tk.SOLID, padx=8, pady=5)
        self.status_box.pack(fill=tk.X, pady=(0, 8))

        self.status_label = tk.Label(
            self.status_box,
            text="Ready: Enter the Receiver's IP and choose a file to begin.",
            font=("Arial", 9),
            fg="#0369a1",
            bg="#e0f2fe",
            wraplength=520,
            justify=tk.LEFT
        )
        self.status_label.pack(anchor="w")

        # 5. Interactive Control Action Buttons Row
        ctrl_frame = tk.Frame(container, bg="#f8fafc")
        ctrl_frame.pack(fill=tk.X, pady=(0, 4))

        # Send Button
        self.send_btn = tk.Button(
            ctrl_frame,
            text="🔒 Send Securely",
            command=self.start_transfer,
            font=("Arial", 10, "bold"),
            bg="#10b981",
            fg="black",
            relief=tk.RAISED,
            pady=6,
            cursor="hand2"
        )
        self.send_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        # Pause / Resume Button
        self.pause_btn = tk.Button(
            ctrl_frame,
            text="⏸️ Pause",
            command=self.toggle_pause,
            font=("Arial", 9, "bold"),
            bg="#f1f5f9",
            fg="#1e293b",
            relief=tk.RAISED,
            pady=6,
            width=10,
            state=tk.DISABLED,
            cursor="hand2"
        )
        self.pause_btn.pack(side=tk.LEFT, padx=4)

        # Cancel Button
        self.cancel_btn = tk.Button(
            ctrl_frame,
            text="🛑 Cancel",
            command=self.cancel_transfer,
            font=("Arial", 9, "bold"),
            bg="#fee2e2",
            fg="#991b1b",
            relief=tk.RAISED,
            pady=6,
            width=10,
            state=tk.DISABLED,
            cursor="hand2"
        )
        self.cancel_btn.pack(side=tk.LEFT, padx=(4, 4))

        # Close Tab Button
        self.close_btn = tk.Button(
            ctrl_frame,
            text="✖ Close Tab",
            command=self.close_tab,
            font=("Arial", 9),
            bg="#e2e8f0",
            fg="#475569",
            relief=tk.RAISED,
            pady=6,
            width=10,
            cursor="hand2"
        )
        self.close_btn.pack(side=tk.LEFT, padx=(4, 0))

    def browse_file(self):
        if self.is_transferring: return
        self.filepath = filedialog.askopenfilename()
        if self.filepath:
            size_bytes = os.path.getsize(self.filepath)
            name = os.path.basename(self.filepath)
            self.file_label.config(text=f"{name} ({format_gb(size_bytes)})", fg="#0f172a", font=("Arial", 9, "bold"))
            self.reset_progress(size_bytes)

    def reset_progress(self, size_bytes=0):
        self.progress_bar['value'] = 0
        self.pct_label.config(text="0%")
        self.bytes_label.config(text=f"0.000 GB / {format_gb(size_bytes)}")
        self.speed_label.config(text="⚡ Speed: 0.000 GB/s")
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

    def update_progress(self, sent, total):
        now = time.time()
        if sent < total and (now - self.last_update_time) < 0.06:
            return

        pct = int((sent / total) * 100) if total > 0 else 0
        sent_gb = sent / (1024 ** 3)
        total_gb = total / (1024 ** 3)

        elapsed = now - self.transfer_start_time if self.transfer_start_time else 0.001
        speed_gbps = sent_gb / elapsed if elapsed > 0 else 0
        remaining_gb = total_gb - sent_gb
        eta_seconds = (remaining_gb / speed_gbps) if speed_gbps > 0 else 0

        self.last_update_time = now
        self.last_sent_bytes = sent

        def _apply():
            self.progress_bar['value'] = pct
            self.pct_label.config(text=f"{pct}%")
            self.bytes_label.config(text=f"{format_gb(sent)} / {format_gb(total)}")
            self.speed_label.config(text=f"⚡ Speed: {format_gbps(speed_gbps)}")
            self.eta_label.config(text=f"⏱️ ETA: {eta_seconds:.1f}s" if eta_seconds > 0 else "⏱️ ETA: Done")

        self.after(0, _apply)

    def toggle_pause(self):
        if not self.is_transferring: return
        if not self.is_paused:
            self.pause_event.clear()
            self.is_paused = True
            self.pause_btn.config(text="▶️ Resume", bg="#dbeafe")
            self.update_status("Transfer Paused by user.")
        else:
            self.pause_event.set()
            self.is_paused = False
            self.pause_btn.config(text="⏸️ Pause", bg="#f1f5f9")
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
        self.pause_btn.config(state=tk.NORMAL, text="⏸️ Pause", bg="#f1f5f9")
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
        self.pause_btn.config(state=tk.DISABLED, text="⏸️ Pause", bg="#f1f5f9")
        self.cancel_btn.config(state=tk.DISABLED)
        self.close_btn.config(state=tk.NORMAL)


class SecureClientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Secure P2P Client (Hybrid AES-ECC + Audit Log)")
        self.root.geometry("680x620")
        self.root.minsize(640, 560)
        self.root.configure(bg="#f1f5f9")

        # Load configuration
        self.config = load_user_config()
        self.my_ip = get_lan_ip()
        
        self.display_name_var = tk.StringVar(value=self.config.get("display_name", "User"))
        self.service_status_var = tk.StringVar(value="Checking...")

        self.tab_counter = 0
        self.send_tabs = []

        # Real-time Receive Notification State
        self.pending_notifications = []
        self.active_popup = None
        self.popup_timer_id = None
        add_receive_listener(self.on_file_received_event)

        # Configure TTK Styles
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
            thickness=16
        )

        self.build_main_ui()

        # Auto-start the background receiver daemon (Zero Terminal Friction!)
        self.start_background_engine()

        # Handle clean window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def build_main_ui(self):
        # 1. Header Banner (Profile, IP, Service Status)
        header = tk.Frame(self.root, bg="#0f172a", height=82)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        top_row = tk.Frame(header, bg="#0f172a")
        top_row.pack(fill=tk.X, padx=16, pady=(8, 0))

        # Title & Security Badge
        title_frame = tk.Frame(top_row, bg="#0f172a")
        title_frame.pack(side=tk.LEFT)

        title_lbl = tk.Label(
            title_frame,
            text="🛡️ Secure P2P Client",
            font=("Arial", 13, "bold"),
            fg="#f8fafc",
            bg="#0f172a"
        )
        title_lbl.pack(anchor="w")

        sub_lbl = tk.Label(
            title_frame,
            text="Blackbox P2P Transfer (ECDH P-256 + AES-256-GCM + Atomicity)",
            font=("Arial", 8),
            fg="#94a3b8",
            bg="#0f172a"
        )
        sub_lbl.pack(anchor="w")

        # Service Online Badge & Toggle
        srv_status_frame = tk.Frame(top_row, bg="#0f172a")
        srv_status_frame.pack(side=tk.RIGHT)

        self.srv_lbl = tk.Label(
            srv_status_frame,
            textvariable=self.service_status_var,
            font=("Arial", 9, "bold"),
            fg="#4ade80",
            bg="#0f172a"
        )
        self.srv_lbl.pack(side=tk.LEFT, padx=(0, 8))

        self.srv_toggle_btn = tk.Button(
            srv_status_frame,
            text="Stop Service",
            command=self.toggle_service,
            font=("Arial", 8),
            bg="#334155",
            fg="black",
            relief=tk.RAISED,
            padx=6,
            pady=2,
            cursor="hand2"
        )
        self.srv_toggle_btn.pack(side=tk.LEFT)

        # Bottom Row of Header: Display Name & My IP
        info_row = tk.Frame(header, bg="#0f172a")
        info_row.pack(fill=tk.X, padx=16, pady=(4, 6))

        # Editable Display Name
        tk.Label(info_row, text="My Display Name:", font=("Arial", 9), fg="#cbd5e1", bg="#0f172a").pack(side=tk.LEFT)
        self.name_entry = tk.Entry(info_row, textvariable=self.display_name_var, font=("Arial", 9, "bold"), width=16, bg="#1e293b", fg="#ffffff", insertbackground="white", relief=tk.SOLID, bd=1)
        self.name_entry.pack(side=tk.LEFT, padx=(6, 15))
        self.name_entry.bind("<FocusOut>", self.save_name_change)
        self.name_entry.bind("<Return>", self.save_name_change)

        # My Local IP & Copy Button
        tk.Label(info_row, text=f"My LAN IP: {self.my_ip}", font=("Arial", 9, "bold"), fg="#38bdf8", bg="#0f172a").pack(side=tk.LEFT)
        copy_btn = tk.Button(
            info_row,
            text="📋 Copy IP",
            command=self.copy_ip,
            font=("Arial", 8),
            bg="#334155",
            fg="black",
            relief=tk.RAISED,
            padx=6,
            pady=1,
            cursor="hand2"
        )
        copy_btn.pack(side=tk.LEFT, padx=(6, 0))

        # 2. Main Tabbed Navigation
        self.main_notebook = ttk.Notebook(self.root)
        self.main_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(8, 10))

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
        top_bar.pack(fill=tk.X, padx=8, pady=(6, 4))

        tk.Label(
            top_bar,
            text="Active File Transfers:",
            font=("Arial", 10, "bold"),
            fg="#334155",
            bg="#f1f5f9"
        ).pack(side=tk.LEFT)

        add_tab_btn = tk.Button(
            top_bar,
            text="➕ New Transfer Tab",
            command=self.add_send_tab,
            font=("Arial", 9, "bold"),
            bg="#38bdf8",
            fg="black",
            relief=tk.RAISED,
            padx=10,
            pady=3,
            cursor="hand2"
        )
        add_tab_btn.pack(side=tk.RIGHT)

        # Sub-notebook for multiple concurrent sending tabs
        self.sub_notebook = ttk.Notebook(self.send_page)
        self.sub_notebook.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Initial Send Tab
        self.add_send_tab()

    def add_send_tab(self):
        self.tab_counter += 1
        tab_frame = TransferSubTab(self.sub_notebook, self.tab_counter, self)
        self.sub_notebook.add(tab_frame, text=f"  Transfer #{self.tab_counter}  ")
        self.sub_notebook.select(tab_frame)
        self.send_tabs.append(tab_frame)

    def remove_send_tab(self, tab_frame):
        if len(self.send_tabs) <= 1:
            messagebox.showinfo("Notice", "At least one transfer tab must remain open.")
            return
        self.sub_notebook.forget(tab_frame)
        self.send_tabs.remove(tab_frame)

    def build_history_page_ui(self):
        h_container = tk.Frame(self.history_page, bg="#f1f5f9", padx=12, pady=10)
        h_container.pack(fill=tk.BOTH, expand=True)

        # Top Bar with Title and Actions
        h_top = tk.Frame(h_container, bg="#f1f5f9")
        h_top.pack(fill=tk.X, pady=(0, 8))

        tk.Label(
            h_top,
            text="Audit Trail & Transfer Log:",
            font=("Arial", 11, "bold"),
            fg="#1e293b",
            bg="#f1f5f9"
        ).pack(side=tk.LEFT)

        btn_frame = tk.Frame(h_top, bg="#f1f5f9")
        btn_frame.pack(side=tk.RIGHT)

        open_folder_btn = tk.Button(
            btn_frame,
            text="📂 Open Received Folder",
            command=self.open_received_folder,
            font=("Arial", 9, "bold"),
            bg="#e2e8f0",
            fg="#1e293b",
            padx=8,
            pady=3,
            cursor="hand2"
        )
        open_folder_btn.pack(side=tk.LEFT, padx=4)

        refresh_btn = tk.Button(
            btn_frame,
            text="🔄 Refresh",
            command=self.refresh_history,
            font=("Arial", 9),
            bg="#e2e8f0",
            fg="#1e293b",
            padx=8,
            pady=3,
            cursor="hand2"
        )
        refresh_btn.pack(side=tk.LEFT, padx=4)

        clear_btn = tk.Button(
            btn_frame,
            text="🗑️ Clear",
            command=self.clear_history_log,
            font=("Arial", 9),
            bg="#fee2e2",
            fg="#991b1b",
            padx=8,
            pady=3,
            cursor="hand2"
        )
        clear_btn.pack(side=tk.LEFT, padx=(4, 0))

        # Treeview Table
        table_frame = tk.Frame(h_container, bg="#ffffff", bd=1, relief=tk.SOLID)
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("id", "direction", "peer", "file", "size", "timestamp", "duration", "speed", "status")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("id", text="#")
        self.tree.heading("direction", text="Direction")
        self.tree.heading("peer", text="Peer (Name / IP)")
        self.tree.heading("file", text="Filename")
        self.tree.heading("size", text="Size (GB)")
        self.tree.heading("timestamp", text="Date & Time")
        self.tree.heading("duration", text="Time Taken")
        self.tree.heading("speed", text="Throughput (GB/s)")
        self.tree.heading("status", text="Status")

        self.tree.column("id", width=35, anchor="center")
        self.tree.column("direction", width=85, anchor="center")
        self.tree.column("peer", width=140, anchor="w")
        self.tree.column("file", width=130, anchor="w")
        self.tree.column("size", width=85, anchor="e")
        self.tree.column("timestamp", width=130, anchor="center")
        self.tree.column("duration", width=75, anchor="center")
        self.tree.column("speed", width=110, anchor="e")
        self.tree.column("status", width=95, anchor="center")

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
            size_str = format_gb(r['filesize'])
            speed_gbps = (r['speed_mbps'] / 1024.0) if r['speed_mbps'] > 0 else 0.0
            speed_str = format_gbps(speed_gbps) if speed_gbps > 0 else "--"
            dur_str = f"{r['duration_sec']:.2f}s" if r['duration_sec'] > 0 else "--"

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
            body_headline = f"'{item['filename']}' ({format_gb(item['filesize'])})"
            sub_headline = f"From: {item['sender_name']} ({item['peer_ip']})"
        else:
            title_text = f"📥 {count} Files Received!"
            body_headline = f"{count} files received from {senders_str}"
            latest = self.pending_notifications[-1]
            sub_headline = f"Latest: '{latest['filename']}' ({format_gb(latest['filesize'])})"

        popup = tk.Toplevel(self.root)
        self.active_popup = popup
        popup.title("P2P File Transfer Notification")
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)

        popup_w, popup_h = 390, 140
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = max(10, screen_w - popup_w - 25)
        y = max(10, screen_h - popup_h - 45)
        popup.geometry(f"{popup_w}x{popup_h}+{x}+{y}")

        # Modern Card Container with Accent Border
        card = tk.Frame(popup, bg="#0f172a", bd=2, relief=tk.SOLID, highlightbackground="#10b981", highlightthickness=2)
        card.pack(fill=tk.BOTH, expand=True)

        # Header Row
        header_f = tk.Frame(card, bg="#0f172a")
        header_f.pack(fill=tk.X, padx=12, pady=(8, 2))

        title_lbl = tk.Label(header_f, text=title_text, font=("Arial", 10, "bold"), fg="#10b981", bg="#0f172a", cursor="hand2")
        title_lbl.pack(side=tk.LEFT)
        title_lbl.bind("<Button-1>", lambda e: self.navigate_to_history_from_popup())

        close_btn = tk.Button(
            header_f,
            text="✖",
            command=self.close_notification_popup,
            font=("Arial", 9, "bold"),
            bg="#0f172a",
            fg="#94a3b8",
            activeforeground="#f8fafc",
            activebackground="#0f172a",
            bd=0,
            cursor="hand2"
        )
        close_btn.pack(side=tk.RIGHT)

        # Middle Content Row (Clickable)
        content_f = tk.Frame(card, bg="#0f172a", cursor="hand2")
        content_f.pack(fill=tk.X, padx=12, pady=(2, 6))
        content_f.bind("<Button-1>", lambda e: self.navigate_to_history_from_popup())

        body_lbl = tk.Label(content_f, text=body_headline, font=("Arial", 9, "bold"), fg="#f8fafc", bg="#0f172a", anchor="w", wraplength=360, justify=tk.LEFT)
        body_lbl.pack(fill=tk.X)
        body_lbl.bind("<Button-1>", lambda e: self.navigate_to_history_from_popup())

        sub_lbl = tk.Label(content_f, text=sub_headline, font=("Arial", 8), fg="#94a3b8", bg="#0f172a", anchor="w", wraplength=360, justify=tk.LEFT)
        sub_lbl.pack(fill=tk.X, pady=(2, 0))
        sub_lbl.bind("<Button-1>", lambda e: self.navigate_to_history_from_popup())

        # Action Buttons Row
        actions_f = tk.Frame(card, bg="#0f172a")
        actions_f.pack(fill=tk.X, padx=12, pady=(4, 8))

        history_btn = tk.Button(
            actions_f,
            text="📜 View Full History",
            command=self.navigate_to_history_from_popup,
            font=("Arial", 9, "bold"),
            bg="#10b981",
            fg="black",
            relief=tk.RAISED,
            padx=10,
            pady=3,
            cursor="hand2"
        )
        history_btn.pack(side=tk.LEFT, padx=(0, 6))

        folder_btn = tk.Button(
            actions_f,
            text="📂 Open Folder",
            command=self.open_received_folder,
            font=("Arial", 9),
            bg="#334155",
            fg="black",
            relief=tk.RAISED,
            padx=8,
            pady=3,
            cursor="hand2"
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
