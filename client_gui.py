import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import os
import sys

# Import our secure protocol logic
from sender import send_file_with_resume

class SecureClientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Secure P2P Client (Hybrid AES-ECC)")
        self.root.geometry("450x250")
        
        # UI Elements
        tk.Label(root, text="Corporate Load Balancer IP:", font=("Arial", 10, "bold")).pack(pady=5)
        self.ip_entry = tk.Entry(root, width=30)
        self.ip_entry.insert(0, "192.168.x.x")
        self.ip_entry.pack()
        
        tk.Label(root, text="Selected File:", font=("Arial", 10, "bold")).pack(pady=5)
        self.file_label = tk.Label(root, text="No file selected", fg="blue")
        self.file_label.pack()
        
        self.browse_btn = tk.Button(root, text="Browse File", command=self.browse_file)
        self.browse_btn.pack(pady=5)
        
        self.send_btn = tk.Button(root, text="Send Securely", command=self.start_transfer, bg="green", fg="black", font=("Arial", 10, "bold"))
        self.send_btn.pack(pady=15)
        
        self.status_label = tk.Label(root, text="Status: Ready", font=("Arial", 9, "italic"))
        self.status_label.pack()
        
        self.filepath = None

    def browse_file(self):
        self.filepath = filedialog.askopenfilename()
        if self.filepath:
            self.file_label.config(text=os.path.basename(self.filepath))

    def start_transfer(self):
        lb_ip = self.ip_entry.get().strip()
        if not lb_ip or lb_ip == "192.168.x.x":
            messagebox.showerror("Error", "Please enter the Server's (Load Balancer) LAN IP.")
            return
        if not self.filepath:
            messagebox.showerror("Error", "Please select a file to send.")
            return
            
        self.send_btn.config(state=tk.DISABLED)
        self.status_label.config(text="Status: Connecting & Encrypting... (Check console for progress)")
        
        # Run transfer in background thread to keep UI responsive
        threading.Thread(target=self.run_transfer, args=(lb_ip, self.filepath), daemon=True).start()

    def run_transfer(self, lb_ip, filepath):
        try:
            # Connect to LB on port 5000
            send_file_with_resume(lb_ip, 5000, filepath)
            self.root.after(0, lambda: self.status_label.config(text="Status: Transfer Complete!"))
            self.root.after(0, lambda: messagebox.showinfo("Success", "File successfully sent and securely encrypted using AES-GCM and ECC!"))
        except Exception as e:
            self.root.after(0, lambda: self.status_label.config(text="Status: Failed"))
            self.root.after(0, lambda: messagebox.showerror("Error", f"Connection failed: {e}"))
        finally:
            self.root.after(0, lambda: self.send_btn.config(state=tk.NORMAL))

if __name__ == "__main__":
    root = tk.Tk()
    app = SecureClientGUI(root)
    root.mainloop()
