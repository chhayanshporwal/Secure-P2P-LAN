import socket
import logging
import struct
import os
import hashlib
import argparse
import time
from crypto_utils import (
    generate_aes_key,
    encrypt_aes_key_with_ecc,
    deserialize_public_key,
    encrypt_chunk
)

from history_manager import HistoryManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - SENDER - %(levelname)s - %(message)s')

def receive_all(sock, num_bytes):
    data = b''
    while len(data) < num_bytes:
        packet = sock.recv(num_bytes - len(data))
        if not packet:
            return None
        data += packet
    return data

def format_size(num_bytes):
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

def calculate_file_hash(filepath):
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(65536)
            if not chunk: break
            hasher.update(chunk)
    return hasher.hexdigest()

def get_worker_from_lb(lb_ip, lb_port, status_cb=None, cancel_event=None):
    """
    Connects to the Load Balancer, handles queueing notifications,
    and returns (lb_sock, worker_ip, worker_port).
    The lb_sock is kept open as a lease while the transfer is active.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    sock.connect((lb_ip, lb_port))
    sock.settimeout(2.0)
    
    buffer = ""
    while True:
        if cancel_event and cancel_event.is_set():
            sock.close()
            raise Exception("Transfer cancelled while waiting in queue.")
        
        try:
            chunk = sock.recv(1024).decode('utf-8')
            if not chunk:
                break
            buffer += chunk
            while '\n' in buffer or (':' in buffer and not buffer.startswith('QUEUED') and not buffer.startswith('REJECTED')):
                if '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                else:
                    line = buffer
                    buffer = ""
                line = line.strip()
                if not line:
                    continue
                if line.startswith("QUEUED:"):
                    parts = line.split(":")
                    pos = parts[1] if len(parts) > 1 else "?"
                    cap = parts[2] if len(parts) > 2 else "25"
                    if status_cb:
                        status_cb(f"⏳ Server at capacity ({cap} active). In waiting queue: Position #{pos}...")
                elif line.startswith("REJECTED:"):
                    sock.close()
                    raise Exception(line)
                elif ":" in line:
                    raw = line.replace("ASSIGNED:", "").strip()
                    ip, port = raw.split(":")
                    return sock, ip, int(port)
        except socket.timeout:
            continue
            
    sock.close()
    raise Exception("Disconnected from Load Balancer without worker assignment.")

def send_file_with_resume(lb_ip, lb_port, filepath, status_cb=None, progress_cb=None, pause_event=None, cancel_event=None, sender_name="User"):
    if not os.path.exists(filepath):
        logging.error(f"File not found: {filepath}")
        if status_cb: status_cb(f"Error: File not found: {filepath}")
        return

    filesize = os.path.getsize(filepath)
    filename = os.path.basename(filepath)
    logging.info("Calculating SHA-256 hash of the file...")
    if status_cb: status_cb("Calculating SHA-256 hash...")
    file_hash = calculate_file_hash(filepath)
    
    sent_bytes = 0
    chunk_size = 65536 # 64 KB for high-throughput LAN transfer
    t0 = time.time()
    
    while sent_bytes < filesize:
        if cancel_event and cancel_event.is_set():
            if status_cb: status_cb("🛑 Transfer Cancelled.")
            HistoryManager().add_record(
                direction="SENT",
                peer_name=lb_ip,
                peer_ip=lb_ip,
                filename=filename,
                filesize=filesize,
                duration_sec=time.time() - t0,
                speed_mbps=0.0,
                status="Cancelled",
                file_path=os.path.abspath(filepath)
            )
            raise Exception("Transfer cancelled by user.")

        client_socket = None
        lb_sock = None
        try:
            # 1. Connect to Load Balancer to get assigned a worker
            if status_cb: status_cb(f"Contacting Load Balancer ({lb_ip}:{lb_port})...")
            lb_sock, worker_ip, worker_port = get_worker_from_lb(lb_ip, lb_port, status_cb=status_cb, cancel_event=cancel_event)
            logging.info(f"Assigned to Worker Node: {worker_ip}:{worker_port}")
            if status_cb: status_cb(f"Connected to Worker {worker_ip}:{worker_port}")
            
            # 2. Connect to the assigned worker
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 262144)
            client_socket.settimeout(10) # 10s timeout to detect drops quickly
            client_socket.connect((worker_ip, worker_port))
            
            # 3. ECC Handshake
            if status_cb: status_cb("Performing ECC Key Handshake...")
            pub_len_data = receive_all(client_socket, 4)
            if not pub_len_data: raise Exception("Failed to receive public key")
            pub_len = struct.unpack("!I", pub_len_data)[0]
            pub_bytes = receive_all(client_socket, pub_len)
            receiver_public_key = deserialize_public_key(pub_bytes)
            
            aes_key = generate_aes_key()
            encrypted_aes_key = encrypt_aes_key_with_ecc(aes_key, receiver_public_key)
            client_socket.sendall(struct.pack("!I", len(encrypted_aes_key)) + encrypted_aes_key)
            
            # 4. Metadata (Include sender_name and current sent_bytes offset)
            metadata = f"{sender_name} | {filename} | {filesize} | {file_hash} | {sent_bytes} | <END_OF_HEADER>"
            metadata_bytes = metadata.encode('utf-8')
            client_socket.sendall(struct.pack("!I", len(metadata_bytes)) + metadata_bytes)
            
            # 5. Wait for ACK or RESUME
            resp = client_socket.recv(1024).decode('utf-8')
            if resp.startswith("RESUME"):
                sent_bytes = int(resp.split(" ")[1])
                logging.info(f"Resuming transfer from byte {sent_bytes}")
                if status_cb: status_cb(f"Resuming transfer from byte {sent_bytes}...")
            elif resp == "DONE":
                logging.info("File already fully uploaded!")
                if status_cb: status_cb("File already fully uploaded.")
                if progress_cb: progress_cb(filesize, filesize)
                return
            elif resp == "ACK":
                logging.info("Starting transfer...")
                if status_cb: status_cb("Encrypting & transferring chunks...")
                
            # 6. Send Data Chunks with Pause & Cancel support
            with open(filepath, 'rb') as f:
                f.seek(sent_bytes)
                while sent_bytes < filesize:
                    # Check for cancellation
                    if cancel_event and cancel_event.is_set():
                        logging.info("Cancel signal detected. Sending CANC to worker...")
                        try: client_socket.sendall(b"CANC")
                        except Exception: pass
                        if status_cb: status_cb("🛑 Transfer Cancelled.")
                        HistoryManager().add_record(
                            direction="SENT",
                            peer_name=lb_ip,
                            peer_ip=lb_ip,
                            filename=filename,
                            filesize=filesize,
                            duration_sec=time.time() - t0,
                            speed_mbps=0.0,
                            status="Cancelled",
                            file_path=os.path.abspath(filepath)
                        )
                        raise Exception("Transfer cancelled by user.")
                    
                    # Check for pause
                    if pause_event and not pause_event.is_set():
                        if status_cb: status_cb("⏸️ Transfer Paused")
                        while not pause_event.is_set():
                            if cancel_event and cancel_event.is_set():
                                try: client_socket.sendall(b"CANC")
                                except Exception: pass
                                if status_cb: status_cb("🛑 Transfer Cancelled.")
                                HistoryManager().add_record(
                                    direction="SENT",
                                    peer_name=lb_ip,
                                    peer_ip=lb_ip,
                                    filename=filename,
                                    filesize=filesize,
                                    duration_sec=time.time() - t0,
                                    speed_mbps=0.0,
                                    status="Cancelled",
                                    file_path=os.path.abspath(filepath)
                                )
                                raise Exception("Transfer cancelled by user.")
                            time.sleep(0.1)
                        if status_cb: status_cb("⚡ Transfer Resumed...")

                    chunk = f.read(chunk_size)
                    if not chunk: break
                    
                    encrypted_chunk = encrypt_chunk(chunk, aes_key)
                    client_socket.sendall(struct.pack("!I", len(encrypted_chunk)) + encrypted_chunk)
                    
                    sent_bytes += len(chunk)
                    if progress_cb:
                        progress_cb(sent_bytes, filesize)
                    now_t = time.time()
                    cur_speed = (sent_bytes / (1024 * 1024)) / max(0.001, now_t - t0)
                    print(f"\rProgress: {format_size(sent_bytes)} / {format_size(filesize)} | Speed: {cur_speed:.2f} MB/s", end="")
                    
            print()
            logging.info("Transfer complete!")
            if status_cb: status_cb("Transfer complete!")
            
            elapsed = max(0.01, time.time() - t0)
            speed_mbps = (filesize / (1024 * 1024)) / elapsed if filesize > 0 else 0.0
            HistoryManager().add_record(
                direction="SENT",
                peer_name=lb_ip,
                peer_ip=lb_ip,
                filename=filename,
                filesize=filesize,
                duration_sec=elapsed,
                speed_mbps=speed_mbps,
                status="Completed",
                file_path=os.path.abspath(filepath)
            )
            break # Success, break out of retry loop
            
        except Exception as e:
            if cancel_event and cancel_event.is_set():
                logging.info("Transfer cleanly cancelled.")
                raise e
            logging.error(f"Transfer interrupted: {e}. Retrying in 2 seconds...")
            if status_cb: status_cb(f"Interrupted ({e})! Re-routing via Load Balancer...")
            time.sleep(2)
        finally:
            if client_socket:
                try: client_socket.close()
                except Exception: pass
            if lb_sock:
                try: lb_sock.close()
                except Exception: pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="P2P File Transfer Sender (Load Balanced)")
    parser.add_argument("lb_ip", help="IP address of the Load Balancer")
    parser.add_argument("filepath", help="Path of the file to send")
    parser.add_argument("--lb_port", type=int, default=5000, help="Port of the Load Balancer")
    
    args = parser.parse_args()
    send_file_with_resume(args.lb_ip, args.lb_port, args.filepath)
