import socket
import logging
import struct
import os
import hashlib
import threading
import argparse
from crypto_utils import (
    generate_ecc_key_pair,
    serialize_public_key,
    decrypt_aes_key_with_ecc,
    decrypt_chunk
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - WORKER - %(levelname)s - %(message)s')

def receive_all(sock, num_bytes):
    data = b''
    while len(data) < num_bytes:
        packet = sock.recv(num_bytes - len(data))
        if not packet:
            return None
        data += packet
    return data

def handle_client(conn, addr, port):
    try:
        logging.info(f"[{port}] Connection accepted from {addr}")
        
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
        filename = parts[0].strip()
        filesize = int(parts[1].strip())
        expected_hash = parts[2].strip()
        
        save_path = f"received_{os.path.basename(filename)}"
        
        # Check if file exists for resuming
        received_bytes = 0
        if os.path.exists(save_path):
            received_bytes = os.path.getsize(save_path)
            
        if received_bytes > 0 and received_bytes < filesize:
            logging.info(f"[{port}] Resuming {filename} from byte {received_bytes}")
            conn.sendall(f"RESUME {received_bytes}".encode('utf-8'))
        elif received_bytes == filesize:
            logging.info(f"[{port}] File {filename} already fully received.")
            conn.sendall(b"DONE")
            return
        else:
            logging.info(f"[{port}] Incoming new file: {filename} ({filesize} bytes)")
            conn.sendall(b"ACK")
        
        # Step 6: Decryption & Reassembly
        mode = "ab" if received_bytes > 0 else "wb"
        hasher = hashlib.sha256()
        
        # Re-hash existing file if resuming to maintain integrity check
        if received_bytes > 0:
            with open(save_path, "rb") as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk: break
                    hasher.update(chunk)
                    
        with open(save_path, mode) as f:
            while received_bytes < filesize:
                chunk_len_data = receive_all(conn, 4)
                if not chunk_len_data:
                    break # Connection dropped (simulating network failure)
                
                chunk_len = struct.unpack("!I", chunk_len_data)[0]
                encrypted_chunk = receive_all(conn, chunk_len)
                
                decrypted_chunk = decrypt_chunk(encrypted_chunk, aes_key)
                f.write(decrypted_chunk)
                hasher.update(decrypted_chunk)
                
                received_bytes += len(decrypted_chunk)
        
        if received_bytes == filesize:
            actual_hash = hasher.hexdigest()
            if actual_hash == expected_hash:
                logging.info(f"[{port}] Integrity check passed! File {filename} complete.")
            else:
                logging.error(f"[{port}] Integrity check failed! Expected {expected_hash}, got {actual_hash}")
        else:
            logging.warning(f"[{port}] Transfer interrupted at {received_bytes}/{filesize} bytes.")
            
    except Exception as e:
        logging.error(f"[{port}] Error: {e}")
    finally:
        conn.close()

def start_server(port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('0.0.0.0', port))
    server_socket.listen(5) # Allow queueing up to 5 concurrent client backlogs
    
    logging.info(f"Worker Node listening on 0.0.0.0:{port}")
    
    while True:
        try:
            conn, addr = server_socket.accept()
            # Multi-threading for concurrent clients
            threading.Thread(target=handle_client, args=(conn, addr, port), daemon=True).start()
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5001, help="Port of the worker node")
    args = parser.parse_args()
    start_server(args.port)
