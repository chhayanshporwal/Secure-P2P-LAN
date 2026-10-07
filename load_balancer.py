import socket
import logging
import threading
import itertools

logging.basicConfig(level=logging.INFO, format='%(asctime)s - LB - %(levelname)s - %(message)s')

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

LOCAL_IP = get_local_ip()

# In a real-world scenario, workers would dynamically register themselves.
# For this PoC, we assume 3 worker nodes are running on the local machine on different ports.
WORKERS = [
    {"ip": LOCAL_IP, "port": 5001},
    {"ip": LOCAL_IP, "port": 5002},
    {"ip": LOCAL_IP, "port": 5003}
]

# Round-robin cycle for simple and effective load balancing
worker_cycle = itertools.cycle(WORKERS)

def handle_client(conn, addr):
    try:
        worker = next(worker_cycle)
        response = f"{worker['ip']}:{worker['port']}"
        conn.sendall(response.encode('utf-8'))
        logging.info(f"Assigned client {addr} to worker {response}")
    except Exception as e:
        logging.error(f"Error handling client {addr}: {e}")
    finally:
        conn.close()

def start_load_balancer(port=5000):
    lb_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lb_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    lb_socket.bind(('0.0.0.0', port))
    lb_socket.listen(10)
    
    logging.info(f"Load Balancer running on 0.0.0.0:{port}")
    
    while True:
        try:
            conn, addr = lb_socket.accept()
            logging.info(f"Connection request from {addr}")
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
        except KeyboardInterrupt:
            logging.info("Load balancer shutting down.")
            break

if __name__ == "__main__":
    start_load_balancer()
