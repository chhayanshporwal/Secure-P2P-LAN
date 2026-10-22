# Secure P2P LAN File Transfer (Blackbox Application)

A localized, fault-tolerant, secure Peer-to-Peer (P2P) file transfer application for Local Area Networks (LANs). It implements a **Load-Balanced Client-Server architecture** over TCP sockets with a **Hybrid Cryptography approach (AES-256-GCM + ECDH P-256)** and atomic staged commits.

---

## 📁 Modular Directory Structure

The project is organized into two distinct directories:
```
Project/
├── main.py                    # Root one-click application launcher
├── requirements.txt           # Python dependencies
├── transfer_history.db        # SQLite audit log of transfers
├── received_files/            # Directory where transferred files are safely stored
├── dist/                      # Standalone packaged executables (SecureClient)
│
├── src/                       # 🟢 Working Application Code
│   ├── client_gui.py          # Blackbox Desktop GUI (Tabs, Monitor, Audit Log, Popups)
│   ├── service_daemon.py      # Background receiver & load balancer daemon
│   ├── receiver.py            # Worker node server (ECDH handshake, AES-GCM, Atomicity)
│   ├── sender.py              # Sender engine (Chunking, Pause/Resume/Cancel, Retry)
│   ├── load_balancer.py       # Least-connections load balancer (FIFO queue & limits)
│   ├── crypto_utils.py        # Cryptographic primitives (ECDH, AES-256-GCM, SHA-256)
│   └── history_manager.py     # SQLite audit logger for all transfer events
│
└── paper_and_research/        # 📄 Research & Academic Materials
    ├── Paper 2.pdf                                    # Base IEEE reference paper
    ├── Project_ Cyber Security Lab - Google Docs.pdf  # Project guidelines
    ├── research_paper_draft.md                        # Complete research paper manuscript
    ├── ecc_vs_dh_comparison.md                       # Cryptographic comparative analysis
    ├── analysis_dashboard.py                          # Cryptographic benchmarking & charts
    ├── network_analysis.py                            # Concurrency & fault-tolerance tests
    ├── performance_comparison.png                    # Benchmark graphs
    ├── performance_graph.png                         # Throughput graphs
    └── key_size_comparison.png                       # Key size comparison charts
```

---

## 🚀 How to Run the Blackbox Application

### Option 1: Run with Python
```bash
source venv/bin/activate
python main.py
```

### Option 2: Run Standalone Executable (Zero Terminal Friction)
- **On macOS**:
  Run the pre-compiled binary in `dist/SecureClient` or `dist/SecureClient.app`.
  To re-compile anytime, run:
  ```bash
  ./build_mac.sh
  ```
- **On Windows**:
  Copy the project folder to the Windows laptop and double-click:
  ```
  build_windows.bat
  ```
  *(Or run `pyinstaller --onefile --windowed --paths src --name "SecureClient" main.py`)*.
  This produces a single self-contained `dist\SecureClient.exe`.
- **Automated Cloud Build (No Windows PC Required)**:
  Push this repo to GitHub. The included `.github/workflows/build_executables.yml` automatically compiles both `SecureClient.exe` (Windows) and `SecureClient.zip` (Mac) in the cloud and provides direct download links!

---

## 🛡️ Key Features

1. **GB / GB/s Native Units**:
   - File payload sizes and transfer throughput are formatted with respect to **Gigabytes** (`X.XXX GB`) and **Gigabytes per second** (`X.XXX GB/s`).
2. **Instant Receive Pop-Up Notification**:
   - Whenever an incoming transfer finishes, an on-screen pop-up alert appears:
     - Shows file name or count of files received from peer(s).
     - Single-click on the notification card or **"📜 View Full History"** immediately raises the app and switches to the Audit History tab.
3. **Blackbox Zero-Terminal Experience**:
   - The application automatically launches its local Load Balancer and Worker Nodes in the background upon opening.
   - Shows local LAN IP in the header with a **Copy IP** button to share with peers.
4. **Atomicity (All-or-Nothing)**:
   - Incomplete or cancelled transfers are purged automatically; only verified files (matching SHA-256) are committed.
5. **Multi-Tab Transfer Queue**:
   - Queue and send multiple payloads concurrently across independent tabs.
6. **Dynamic Load Balancing**:
   - Supports up to 25+ concurrent transfers with least-connections routing and a 100-client FIFO queue.
