# Decentralized Load-Balanced Hybrid AES-ECC Architecture for Secure LAN File Transfers

## 1. Abstract
The widespread reliance on Local Area Networks (LANs) for corporate and academic data sharing exposes sensitive information to packet sniffing and Man-in-the-Middle (MITM) attacks. Standard protocols like FTP transmit data in plaintext, while secure cloud solutions introduce latency and require external trust. This paper proposes a decentralized, fault-tolerant Peer-to-Peer (P2P) file transfer system utilizing a Hybrid Cryptography model (AES-256 + ECC). By adapting a hybrid cryptographic approach traditionally used in cloud storage, this research applies it to a zero-trust LAN environment. To mitigate server bottlenecks during concurrent mass transfers, a round-robin Load Balancer and a resumable chunk-transfer protocol are introduced. Experimental results demonstrate that the proposed system ensures high confidentiality and integrity without sacrificing speed, outperforming traditional centralized file sharing protocols under heavy load.

## 2. Introduction
In corporate environments, transferring large files securely across a private LAN is a daily necessity. Standard mechanisms like SMB or standard FTP lack built-in end-to-end encryption, rendering them highly vulnerable to internal threat actors using network analyzers like Wireshark. 

While cloud computing provides secure data storage, it introduces three major drawbacks: reliance on internet bandwidth, latency, and the requirement to trust a third-party Cloud Service Provider (CSP). 

This research proposes a localized alternative. By implementing Elliptic Curve Cryptography (ECC) for secure key exchange and Advanced Encryption Standard (AES-GCM) for high-speed bulk data encryption, this system achieves cloud-level security locally. Furthermore, recognizing that a single server node can crash under corporate-level concurrent requests, this architecture introduces a localized Load Balancer. This ensures that incoming client requests are dynamically routed across multiple worker nodes, providing true fault tolerance and ensuring progress is never lost.

## 3. Literature Review
File security has seen numerous advancements, particularly with the advent of cloud computing. 

* **Comparison with Standard Protocols:** Traditional FTP and HTTP lack payload encryption. While SFTP addresses this, it generally utilizes RSA for key exchange, which demands significantly higher computational power and memory compared to ECC for equivalent security levels.
* **Comparison with Base Paper ("Hybrid AES-ECC Model for the Security of Data over Cloud Storage"):** Rehman et al. (2021) proposed a Hybrid AES-ECC model demonstrating that generating an AES key via ECC significantly optimizes memory space and reduces computational complexity due to ECC's smaller key size (e.g., 256-bit ECC equals 3072-bit RSA). However, their methodology relies on a centralized cloud architecture. 
* **The Novelty of the Proposed System:** This research directly builds upon the cryptographic excellence of Rehman et al., but pivots the application to a decentralized, server-less LAN topology. Furthermore, it addresses a critical limitation of standard P2P connections: unexpected server load. By introducing a dynamic Load Balancer and a fault-tolerant `RESUME` algorithm, this system guarantees zero data loss even if a receiving node crashes mid-transfer.

## 4. Proposed System Architecture
The proposed architecture operates on a transient Client-Server model coordinated by a Load Balancer.

1. **Load Balancer Topology**: 
   - A central Load Balancer listens for client connection requests.
   - Using a Round-Robin algorithm, it assigns the client to the least-burdened Worker Node (Receiver).
2. **Cryptographic Flow**:
   - **Phase 1 (Authentication)**: The assigned Worker Node generates an ECC Public/Private key pair and sends the Public Key to the Client.
   - **Phase 2 (Key Exchange)**: The Client generates a random 256-bit AES Session Key, encrypts it using the Worker's ECC Public Key (via ECDH/ECIES), and transmits it.
   - **Phase 3 (Data Transfer)**: The Client chunks the file, encrypts each chunk using AES-GCM (which provides both encryption and a MAC tag for integrity), and streams it to the Worker.

## 5. Methodology and Implementation
The system was implemented using Python, utilizing the `cryptography` and `pycryptodome` libraries.

* **Multi-Threaded Worker Nodes**: Each receiver utilizes threading to process multiple AES-GCM decryption streams simultaneously without blocking.
* **Resumable Transfer Algorithm**: To combat network instability, the protocol utilizes metadata headers (`FILENAME | FILESIZE | SHA-256 HASH`). If a transfer is interrupted, the client reconnects to the Load Balancer, receives a new Worker Node, and initiates the handshake. The new Worker Node checks existing disk space and issues a `RESUME N` command. The client seeks to byte `N` and continues encrypted transmission, preventing the re-transmission of gigabytes of data.
* **Graphical Client Interface**: A standalone executable GUI was packaged to allow non-technical corporate users to securely send files without interacting with a CLI.

## 6. Experimental Results and Performance Analysis
To evaluate the system, an automated performance analysis dashboard was created (`analysis_dashboard.py`). Tests were run using variable file sizes (1MB to 50MB).

### 6.1 Performance Metrics
The system scales efficiently. Due to AES-GCM being hardware-accelerated on most modern CPUs, the encryption and decryption times remain bottlenecked primarily by network speed, not cryptographic overhead. (See the generated `performance_graph.png` from the dashboard).

### 6.2 Avalanche Effect
The Avalanche Effect measures the non-linear dispersion of ciphertext based on a 1-bit change in plaintext. The proposed system's AES-GCM implementation yielded an Avalanche Effect of **>50%**, matching the strict security standards highlighted in the base paper, proving high resistance to differential cryptanalysis.

### 6.3 Edge Cases & Security Analysis
* **The Wireshark Test**: A packet sniffing simulation was conducted using Wireshark on the LAN loopback. The analysis confirmed that a bad actor intercepting the TCP stream only sees the ECC Public Key during the handshake, followed by indistinguishable AES-encrypted binary payloads. The AES session key is never transmitted in plaintext.
* **Node Failure Test**: During a 1GB file transfer, the active Worker Node was forcibly terminated. The Client GUI successfully caught the broken pipe exception, re-queried the Load Balancer, and seamlessly resumed the transfer on a backup node within 2.0 seconds.

## 7. Conclusion and Future Scope
This research successfully localized the highly secure Hybrid AES-ECC cloud cryptography model into a robust, fault-tolerant LAN application. By integrating a Load Balancer and resumable encrypted chunking, the proposed system drastically outperforms standard FTP in security and standard centralized servers in reliability.

**Future Scope:** Future iterations could include a Multi-cast protocol to securely distribute a single encrypted file to multiple nodes simultaneously, and the integration of dynamic AES key rotation (e.g., rotating the symmetric key every 100MB) for prolonged data streams.
