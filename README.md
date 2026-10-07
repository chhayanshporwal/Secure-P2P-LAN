# Secure Load-Balanced P2P LAN File Transfer

A localized, fault-tolerant, secure Peer-to-Peer (P2P) file transfer application for Local Area Networks (LANs). It implements a **Load-Balanced Client-Server architecture** over TCP sockets with a **Hybrid Cryptography approach (AES + ECC)**.

This project builds upon the concepts in *"Hybrid AES-ECC Model for the Security of Data over Cloud Storage"*, adapting the cryptographic strength of the cloud model into a decentralized, resilient LAN environment.

## Features Added

1. **Round-Robin Load Balancer**: Prevents single-point bottlenecks by distributing incoming client transfers across multiple worker nodes.
2. **Fault Tolerance & Resumable Transfers**: If a worker node crashes mid-transfer, the client automatically detects the drop, reconnects to the Load Balancer to get a new node, and **resumes** the encrypted transfer from the exact byte it failed, preventing data loss.
3. **Multi-Threading**: Worker nodes can handle multiple incoming client connections simultaneously.

---

## Requirements

To install dependencies, run:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## How to Showcase the Implementation (Presentation Guide)

To effectively demonstrate this project, you need multiple terminal windows to simulate a real network of servers.

### Step 1: Start the Load Balancer
Open Terminal 1 and run:
```bash
source venv/bin/activate
python load_balancer.py
```
*It will run on port 5000 by default.*

### Step 2: Start the Worker Nodes (Receivers)
Open Terminal 2 and 3. Start two separate worker nodes on different ports (representing different VMs).
**Terminal 2:**
```bash
source venv/bin/activate
python receiver.py --port 5001
```
**Terminal 3:**
```bash
source venv/bin/activate
python receiver.py --port 5002
```


### Step 4: The "Kill Switch" Demo (Proving Fault Tolerance)
1. Send a very large file (e.g., a 1GB dummy file).
   ```bash
   python sender.py 127.0.0.1 large_file.bin
   ```
2. While the transfer is happening on `Worker 1` (Port 5001), go to that terminal and press **Ctrl+C** to kill the server!
3. Watch the `sender.py` terminal: It will detect the crash, output `Transfer interrupted... Retrying`, connect to the Load Balancer, get assigned to `Worker 2` (Port 5002), and immediately **RESUME** the transfer without starting from 0%.

---

## Research Paper Guidelines

When writing your research paper, make sure to:
1. **Cite the Base Paper heavily**: Mention how their Hybrid AES-ECC model proved ECC's superiority over RSA regarding key size and speed in cloud environments.
2. **State your Novelty**: Explain that while cloud storage is great, it requires internet bandwidth and external trust. Your model takes their exact cryptographic approach and applies it to a **zero-trust, decentralized LAN environment**.
3. **Highlight the Load Balancer**: Emphasize that traditional FTP/SMB fails or bottlenecks under heavy load. Your localized load balancer solves this.
4. **Showcase Resumability**: Discuss the algorithm you used for encrypted chunk-resuming (`RESUME N`), proving that fault tolerance doesn't compromise AES-GCM security.

---

## 🚀 Showcasing to Real Users on a LAN (Corporate Style)

To demonstrate this like a real corporate environment, you can run the **Server** and **Load Balancer** on your computer, and have your friends/colleagues act as **Clients** on their own laptops.

### Step 1: Package the Client into a Simple App
You can convert the new Graphical User Interface (`client_gui.py`) into a standalone `.exe` (Windows) or `.app` (Mac) so your friends don't need Python installed!

1. Open your terminal and install PyInstaller:
   ```bash
   pip install pyinstaller
   ```
2. Build the standalone client app:
   ```bash
   pyinstaller --onefile --windowed client_gui.py
   ```
3. Once complete, you will find a `client_gui` executable inside the newly created `dist/` folder.
4. **Share this executable file with your friends via a USB drive.**

### Step 2: Set up your Server (Your Computer)
1. Ensure your laptop is connected to the same Wi-Fi network (LAN) as your friends.
2. Find your laptop's Local IP Address (e.g., `192.168.1.5`).
3. Start the Load Balancer (it will automatically use your Local IP):
   ```bash
   python load_balancer.py
   ```
4. Start 3 Worker Nodes in 3 separate terminal tabs on your laptop:
   ```bash
   python receiver.py --port 5001
   python receiver.py --port 5002
   python receiver.py --port 5003
   ```
*Note: Because all 3 worker nodes are running on your computer, any file they receive will be saved into your `Project` folder perfectly synced!*

### Step 3: Let your friends send files!
1. Tell your friends to open the `client_gui` app on their laptops.
2. They will see a simple window asking for the **Corporate Load Balancer IP**.
3. Tell them to enter your laptop's Local IP address (the one from Step 2, e.g., `192.168.1.5`).
4. They can select any file and click **Send Securely**. 
5. The Load Balancer on your computer will intercept their request, assign them to Port 5001, 5002, or 5003 based on traffic, and seamlessly save the file into your folder! 
6. (Bonus): You can physically stop one of the `receiver.py` scripts while they are sending a large file, and their GUI will automatically resume it on another port!

---

## 📊 Detailed Guide for Testing and Analysis
To gather the exact metrics for your research paper, two automated testing scripts have been provided.

### 1. Cryptographic Benchmarking (`analysis_dashboard.py`)
This script isolates the cryptography (AES-GCM) from the network to measure raw CPU performance.
*   **How to run:** `python analysis_dashboard.py`
*   **What it does:** It generates perfectly sized random files (1MB to 50MB), encrypts/decrypts them, and calculates the exact execution time down to the microsecond.
*   **The Output:** It prints a markdown-ready table of speeds, calculates the exact **Avalanche Effect** percentage, and generates a `performance_graph.png` which you can embed in your paper.

### 2. Network & Fault Tolerance Analysis (`network_analysis.py`)
This script automates the entire localized LAN topology to measure real-world network performance and resiliency.
*   **How to run:** `python network_analysis.py`
*   **What it does:** 
    *   **Test 1 (Throughput):** Measures exactly how many MB/s the system can transfer over a secure socket.
    *   **Test 2 (Load Balancer Efficiency):** Fires 3 concurrent uploads at a single server vs. distributed across 3 servers. It calculates the exact **% Performance Improvement** provided by your Load Balancer architecture.
    *   **Test 3 (Fault Tolerance):** Starts a transfer and programmatically assassines the receiving server mid-way to prove that the system can automatically recover, resume, and prevent data loss.

*Copy the output of both of these scripts directly into the **Experimental Results** section of your research paper!*
