import socket
import logging
import struct
import os
import sys
import hashlib
import threading
import argparse
import time
from crypto_utils import (
    generate_ecc_key_pair,
    serialize_public_key,
    decrypt_aes_key_with_ecc,
    decrypt_chunk
)
from history_manager import HistoryManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - WORKER - %(levelname)s - %(message)s')

def get_received_files_dir():
    if getattr(sys, 'frozen', False):
        save_dir = os.path.join(os.path.dirname(sys.executable), "received_files")
    else:
        base = os.path.dirname(os.path.abspath(__file__))
        if os.path.basename(base) == "src":
            save_dir = os.path.join(os.path.dirname(base), "received_files")
        else:
            save_dir = os.path.join(base, "received_files")
    os.makedirs(save_dir, exist_ok=True)
    return save_dir

_receive_listeners = []

def add_receive_listener(callback):
    if callback not in _receive_listeners:
        _receive_listeners.append(callback)

def remove_receive_listener(callback):
    if callback in _receive_listeners:
        _receive_listeners.remove(callback)

def notify_receive_listeners(sender_name, peer_ip, filename, filesize):
    for cb in list(_receive_listeners):
        try:
            cb(sender_name, peer_ip, filename, filesize)
        except Exception as e:
            logging.error(f"Error in receive listener callback: {e}")

def receive_all(sock, num_bytes):
    data = b''
    while len(data) < num_bytes:
        packet = sock.recv(num_bytes - len(data))
        if not packet:
            return None
        data += packet
    return data

def handle_client(conn, addr, port):
    temp_save_path = None
    final_save_path = None
    t0 = time.time()
    sender_name = "Unknown"
    filename = "unknown"
    filesize = 0
    client_ip = addr[0]
    
    try:
        logging.info(f"[{port}] Connection accepted from {addr}")
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        conn.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 262144)
        
        # 3.1 Receiver generates ECC key pair
        private_key, public_key = generate_ecc_key_pair()
        
        # 3.2 Receiver sends its Public Key
        pub_bytes = serialize_public_key(public_key)
        conn.sendall(struct.pack("!I", len(pub_bytes)) + pub_bytes)
        
        # 3.5 Receiver receives encrypted AES key
        aes_payload_len_data = receive_all(conn, 4)
        if not aes_payload_len_data: return
        aes_payload_len = struct.unpack("!I", aes_payload_len_data)[0]
        aes_payload = receive_all(conn, aes_payload_len)
        
        # 3.6 Receiver decrypts AES session key
        aes_key = decrypt_aes_key_with_ecc(aes_payload, private_key)
        
        # Step 5: Receive Protocol Formatting (Metadata)
        metadata_len_data = receive_all(conn, 4)
        if not metadata_len_data: return
        metadata_len = struct.unpack("!I", metadata_len_data)[0]
        metadata = receive_all(conn, metadata_len).decode('utf-8')
        
        parts = metadata.replace("<END_OF_HEADER>", "").split(" | ")
        if len(parts) >= 5:
            sender_name = parts[0].strip()
            filename = parts[1].strip()
            filesize = int(parts[2].strip())
            expected_hash = parts[3].strip()
            client_offset = int(parts[4].strip())
        elif len(parts) == 4:
            sender_name = addr[0]
            filename = parts[0].strip()
            filesize = int(parts[1].strip())
            expected_hash = parts[2].strip()
            client_offset = int(parts[3].strip())
        else:
            sender_name = addr[0]
            filename = parts[0].strip()
            filesize = int(parts[1].strip())
            expected_hash = parts[2].strip()
            client_offset = 0
        
        save_dir = get_received_files_dir()
        final_save_path = os.path.join(save_dir, f"{client_ip}_{os.path.basename(filename)}")
            
        # Staged temporary file for ATOMICITY
        temp_save_path = final_save_path + ".part"
        
        # Multi-user & resume handling:
        if client_offset == 0:
            # Client is starting a fresh transfer -> purge any stale .part or previous file
            if os.path.exists(temp_save_path):
                try: os.remove(temp_save_path)
                except Exception: pass
            logging.info(f"[{port}] Incoming new file from '{sender_name}' ({client_ip}): {filename} ({filesize} bytes)")
            conn.sendall(b"ACK")
            received_bytes = 0
            mode = "wb"
        else:
            # Client is resuming after a network interruption
            received_bytes = os.path.getsize(temp_save_path) if os.path.exists(temp_save_path) else 0
            if received_bytes > 0 and received_bytes < filesize:
                logging.info(f"[{port}] Resuming {filename} for {client_ip} from staged byte {received_bytes}")
                conn.sendall(f"RESUME {received_bytes}".encode('utf-8'))
                mode = "ab"
            else:
                logging.info(f"[{port}] Stale offset. Restarting {filename} from byte 0")
                conn.sendall(b"ACK")
                received_bytes = 0
                mode = "wb"
        
        # Step 6: Decryption & Reassembly
        hasher = hashlib.sha256()
        
        # Re-hash existing staged file if resuming to maintain integrity check
        if received_bytes > 0 and os.path.exists(temp_save_path):
            with open(temp_save_path, "rb") as f:
                while True:
                    chunk = f.read(65536)
                    if not chunk: break
                    hasher.update(chunk)
                    
        cancelled = False
        with open(temp_save_path, mode) as f:
            while received_bytes < filesize:
                chunk_len_data = receive_all(conn, 4)
                if not chunk_len_data:
                    break # Connection dropped
                
                # Check for explicit Client Cancellation Signal
                if chunk_len_data == b"CANC":
                    logging.warning(f"[{port}] [ATOMIC CANCEL] Cancellation received from '{sender_name}' ({client_ip}). Aborting...")
                    cancelled = True
                    break
                
                chunk_len = struct.unpack("!I", chunk_len_data)[0]
                encrypted_chunk = receive_all(conn, chunk_len)
                if not encrypted_chunk:
                    break
                
                decrypted_chunk = decrypt_chunk(encrypted_chunk, aes_key)
                f.write(decrypted_chunk)
                hasher.update(decrypted_chunk)
                
                received_bytes += len(decrypted_chunk)
        
        # ATOMICITY ENFORCEMENT & AUDIT LOGGING
        elapsed = max(0.01, time.time() - t0)
        speed_mbps = (filesize / (1024 * 1024)) / elapsed if filesize > 0 else 0.0

        if cancelled:
            # Purge staged file immediately to ensure NOTHING is saved
            if temp_save_path and os.path.exists(temp_save_path):
                os.remove(temp_save_path)
            logging.info(f"[{port}] [ATOMIC PURGE] Staged file {temp_save_path} purged. Zero corrupted data retained.")
            HistoryManager().add_record(
                direction="RECEIVED",
                peer_name=sender_name,
                peer_ip=client_ip,
                filename=filename,
                filesize=filesize,
                duration_sec=elapsed,
                speed_mbps=0.0,
                status="Cancelled",
                file_path=""
            )
        elif received_bytes == filesize:
            actual_hash = hasher.hexdigest()
            if actual_hash == expected_hash:
                # ATOMIC COMMIT: Only commit staged file when 100% complete and cryptographic hash passes
                os.replace(temp_save_path, final_save_path)
                logging.info(f"[{port}] [ATOMIC COMMIT] Integrity verified! File {filename} committed to: {final_save_path}")
                HistoryManager().add_record(
                    direction="RECEIVED",
                    peer_name=sender_name,
                    peer_ip=client_ip,
                    filename=filename,
                    filesize=filesize,
                    duration_sec=elapsed,
                    speed_mbps=speed_mbps,
                    status="Completed",
                    file_path=os.path.abspath(final_save_path)
                )
                notify_receive_listeners(sender_name, client_ip, filename, filesize)
            else:
                # Integrity check failed -> Purge staged file to ensure atomicity
                if temp_save_path and os.path.exists(temp_save_path):
                    os.remove(temp_save_path)
                logging.error(f"[{port}] [ATOMIC PURGE] Hash mismatch! Expected {expected_hash}, got {actual_hash}. Staged file deleted.")
                HistoryManager().add_record(
                    direction="RECEIVED",
                    peer_name=sender_name,
                    peer_ip=client_ip,
                    filename=filename,
                    filesize=filesize,
                    duration_sec=elapsed,
                    speed_mbps=0.0,
                    status="Failed (Hash Mismatch)",
                    file_path=""
                )
        else:
            logging.warning(f"[{port}] Transfer paused/interrupted at {received_bytes}/{filesize} bytes. Preserving staged file for resumability.")
            
    except Exception as e:
        logging.error(f"[{port}] Error: {e}")
    finally:
        conn.close()

def start_server(port, stop_event=None):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('0.0.0.0', port))
    server_socket.listen(50) # Queue up to 50 concurrent handshakes
    server_socket.settimeout(1.0)
    
    logging.info(f"Worker Node listening on 0.0.0.0:{port}")
    
    while stop_event is None or not stop_event.is_set():
        try:
            conn, addr = server_socket.accept()
            # Multi-threading for concurrent clients
            threading.Thread(target=handle_client, args=(conn, addr, port), daemon=True).start()
        except socket.timeout:
            continue
        except (KeyboardInterrupt, OSError):
            break
            
    try: server_socket.close()
    except Exception: pass
    logging.info(f"Worker Node on port {port} stopped.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5001, help="Port of the worker node")
    args = parser.parse_args()
    start_server(args.port)
