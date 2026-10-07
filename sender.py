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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - SENDER - %(levelname)s - %(message)s')

def receive_all(sock, num_bytes):
    data = b''
    while len(data) < num_bytes:
        packet = sock.recv(num_bytes - len(data))
        if not packet:
            return None
        data += packet
    return data

def calculate_file_hash(filepath):
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(8192)
            if not chunk: break
            hasher.update(chunk)
    return hasher.hexdigest()

def get_worker_from_lb(lb_ip, lb_port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((lb_ip, lb_port))
    data = sock.recv(1024).decode('utf-8')
    sock.close()
    ip, port = data.split(':')
    return ip, int(port)

def send_file_with_resume(lb_ip, lb_port, filepath):
    if not os.path.exists(filepath):
        logging.error(f"File not found: {filepath}")
        return

    filesize = os.path.getsize(filepath)
    filename = os.path.basename(filepath)
    logging.info("Calculating SHA-256 hash of the file...")
    file_hash = calculate_file_hash(filepath)
    
    sent_bytes = 0
    chunk_size = 8192
    
    while sent_bytes < filesize:
        client_socket = None
        try:
            # 1. Connect to Load Balancer to get assigned a worker
            worker_ip, worker_port = get_worker_from_lb(lb_ip, lb_port)
            logging.info(f"Assigned to Worker Node: {worker_ip}:{worker_port}")
            
            # 2. Connect to the assigned worker
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(10) # 10s timeout to detect drops quickly
            client_socket.connect((worker_ip, worker_port))
            
            # 3. ECC Handshake
            pub_len_data = receive_all(client_socket, 4)
            if not pub_len_data: raise Exception("Failed to receive public key")
            pub_len = struct.unpack("!I", pub_len_data)[0]
            pub_bytes = receive_all(client_socket, pub_len)
            receiver_public_key = deserialize_public_key(pub_bytes)
            
            aes_key = generate_aes_key()
            encrypted_aes_key = encrypt_aes_key_with_ecc(aes_key, receiver_public_key)
            client_socket.sendall(struct.pack("!I", len(encrypted_aes_key)) + encrypted_aes_key)
            
            # 4. Metadata
            metadata = f"{filename} | {filesize} | {file_hash} | <END_OF_HEADER>"
            metadata_bytes = metadata.encode('utf-8')
            client_socket.sendall(struct.pack("!I", len(metadata_bytes)) + metadata_bytes)
            
            # 5. Wait for ACK or RESUME
            resp = client_socket.recv(1024).decode('utf-8')
            if resp.startswith("RESUME"):
                sent_bytes = int(resp.split(" ")[1])
                logging.info(f"Resuming transfer from byte {sent_bytes}")
            elif resp == "DONE":
                logging.info("File already fully uploaded!")
                return
            elif resp == "ACK":
                logging.info("Starting new transfer...")
                
            # 6. Send Data Chunks
            with open(filepath, 'rb') as f:
                f.seek(sent_bytes)
                while sent_bytes < filesize:
                    chunk = f.read(chunk_size)
                    if not chunk: break
                    
                    encrypted_chunk = encrypt_chunk(chunk, aes_key)
                    client_socket.sendall(struct.pack("!I", len(encrypted_chunk)) + encrypted_chunk)
                    
                    sent_bytes += len(chunk)
                    print(f"\rProgress: {sent_bytes}/{filesize} bytes", end="")
                    
            print()
            logging.info("Transfer complete!")
            break # Success, break out of retry loop
            
        except Exception as e:
            logging.error(f"Transfer interrupted: {e}. Retrying in 2 seconds...")
            time.sleep(2)
            # The loop will continue, contacting the LB again for a new worker and resuming
        finally:
            if client_socket:
                client_socket.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="P2P File Transfer Sender (Load Balanced)")
    parser.add_argument("lb_ip", help="IP address of the Load Balancer")
    parser.add_argument("filepath", help="Path of the file to send")
    parser.add_argument("--lb_port", type=int, default=5000, help="Port of the Load Balancer")
    
    args = parser.parse_args()
    send_file_with_resume(args.lb_ip, args.lb_port, args.filepath)
