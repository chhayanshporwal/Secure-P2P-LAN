#!/usr/bin/env python3
"""
Secure P2P File Transfer Application Launcher
Starts the Blackbox P2P Client (Hybrid AES-256-GCM + ECDH P-256 + Service Daemon)
"""
import sys
import os

# Add src/ to module search path
SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from client_gui import SecureClientGUI, tk

def main():
    root = tk.Tk()
    app = SecureClientGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
