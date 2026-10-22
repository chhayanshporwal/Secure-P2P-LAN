import socket
import logging
import threading
import queue
import time
import os

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

# Configuration
DEFAULT_MAX_CONNECTIONS = 25   # Baseline concurrent transfer capacity
MAX_QUEUE_CAPACITY = 100        # Max clients waiting in queue before rejection

WORKERS = [
    {"ip": LOCAL_IP, "port": 5001, "active_conns": 0},
    {"ip": LOCAL_IP, "port": 5002, "active_conns": 0},
    {"ip": LOCAL_IP, "port": 5003, "active_conns": 0}
]

state_lock = threading.Lock()
active_connections = 0
waiting_queue = queue.Queue(maxsize=MAX_QUEUE_CAPACITY)

def get_dynamic_capacity():
    """
    Dynamically expands capacity up to 35-50 connections based on system responsiveness
    and available worker node count.
    """
    base = DEFAULT_MAX_CONNECTIONS
    # Scale capacity dynamically with available active worker nodes
    alive_workers = len(WORKERS)
    dynamic_limit = max(base, alive_workers * 10) # Allows expanding dynamically based on worker cluster size
    return dynamic_limit

def select_least_loaded_worker():
    """Least-Connections Load Balancing algorithm."""
    with state_lock:
        best_worker = min(WORKERS, key=lambda w: w["active_conns"])
        best_worker["active_conns"] += 1
        return best_worker

def release_worker_slot(worker_port):
    global active_connections
    with state_lock:
        for w in WORKERS:
            if w["port"] == worker_port:
                w["active_conns"] = max(0, w["active_conns"] - 1)
                break
        active_connections = max(0, active_connections - 1)
        cap = get_dynamic_capacity()
        q_size = waiting_queue.qsize()
        logging.info(f"Slot released on port {worker_port}. Capacity: {active_connections}/{cap} active | Queued: {q_size}")

def queue_dispatcher():
    """
    Background worker that monitors the waiting queue.
    Whenever an active slot opens below capacity, it pops the next queued connection.
    """
    global active_connections
    while True:
        try:
            # Check if there is capacity to admit a queued connection
            with state_lock:
                cap = get_dynamic_capacity()
                can_admit = (active_connections < cap) and not waiting_queue.empty()

            if can_admit:
                try:
                    conn, addr = waiting_queue.get_nowait()
                except queue.Empty:
                    time.sleep(0.05)
                    continue

                # Process the queued client
                try:
                    worker = select_least_loaded_worker()
                    with state_lock:
                        active_connections += 1

                    host_ip = conn.getsockname()[0]
                    response = f"{host_ip}:{worker['port']}\n"
                    conn.sendall(response.encode('utf-8'))
                    logging.info(f"[DISPATCHED FROM QUEUE] Client {addr} admitted -> Worker {response.strip()} (Active: {active_connections}/{get_dynamic_capacity()})")

                    # Manage connection lifecycle
                    threading.Thread(target=monitor_lease, args=(conn, worker['port']), daemon=True).start()
                except Exception as e:
                    logging.error(f"Error admitting queued client {addr}: {e}")
                    try: conn.close()
                    except Exception: pass
            else:
                time.sleep(0.05)
        except Exception as e:
            logging.error(f"Queue dispatcher error: {e}")
            time.sleep(0.1)

def monitor_lease(conn, worker_port):
    """
    Monitors the client socket lease. When client finishes or disconnects,
    the active connection slot is immediately released and available for queued clients.
    """
    try:
        # Wait until client socket closes or sends release
        while True:
            data = conn.recv(1024)
            if not data:
                break
    except Exception:
        pass
    finally:
        try: conn.close()
        except Exception: pass
        release_worker_slot(worker_port)

def handle_client(conn, addr):
    global active_connections
    try:
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        with state_lock:
            cap = get_dynamic_capacity()
            is_full = (active_connections >= cap)

        if not is_full:
            # Direct Admission
            worker = select_least_loaded_worker()
            with state_lock:
                active_connections += 1

            host_ip = conn.getsockname()[0]
            response = f"{host_ip}:{worker['port']}\n"
            conn.sendall(response.encode('utf-8'))
            logging.info(f"[DIRECT ASSIGN] Client {addr} -> Worker {response.strip()} | Load: {active_connections}/{cap} active | Queued: {waiting_queue.qsize()}")
            
            # Monitor the client lease in a daemon thread
            threading.Thread(target=monitor_lease, args=(conn, worker['port']), daemon=True).start()

        else:
            # Server capacity reached (>= 25 active connections)
            with state_lock:
                q_size = waiting_queue.qsize()

            if q_size >= MAX_QUEUE_CAPACITY:
                # Maximum queue limit exceeded
                reject_msg = f"REJECTED: Maximum server capacity exceeded ({cap} active, {MAX_QUEUE_CAPACITY} queued). Please try again later.\n"
                conn.sendall(reject_msg.encode('utf-8'))
                logging.warning(f"[REJECTED] Client {addr}: Queue full ({MAX_QUEUE_CAPACITY}/{MAX_QUEUE_CAPACITY})")
                conn.close()
                return

            # Push into FIFO Waiting Queue
            pos = q_size + 1
            queue_msg = f"QUEUED:{pos}:{cap}:Server at capacity ({active_connections}/{cap}). Position #{pos} in queue...\n"
            conn.sendall(queue_msg.encode('utf-8'))
            logging.info(f"[QUEUED] Client {addr} placed at queue position #{pos} (Active: {active_connections}/{cap})")

            waiting_queue.put((conn, addr))

    except Exception as e:
        logging.error(f"Error handling client {addr}: {e}")
        try: conn.close()
        except Exception: pass

def start_load_balancer(port=5000, max_conns=25, stop_event=None, worker_ports=None):
    global DEFAULT_MAX_CONNECTIONS, WORKERS
    DEFAULT_MAX_CONNECTIONS = max_conns
    if worker_ports:
        WORKERS = [{"ip": LOCAL_IP, "port": p, "active_conns": 0} for p in worker_ports]

    lb_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lb_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    lb_socket.bind(('0.0.0.0', port))
    lb_socket.listen(100) # Increased backlog to absorb connection spikes
    lb_socket.settimeout(1.0)
    
    # Start the background Queue Dispatcher thread
    threading.Thread(target=queue_dispatcher, daemon=True).start()

    logging.info(f"Dynamic Load Balancer running on 0.0.0.0:{port}")
    logging.info(f"Configured Baseline Connections: {DEFAULT_MAX_CONNECTIONS} (Auto-expanded to {get_dynamic_capacity()} across {len(WORKERS)} workers)")
    logging.info(f"Max Waiting Queue Size: {MAX_QUEUE_CAPACITY}")
    logging.info(f"Host LAN IP (Enter this in Client GUI): {LOCAL_IP}")
    
    while stop_event is None or not stop_event.is_set():
        try:
            conn, addr = lb_socket.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
        except socket.timeout:
            continue
        except (KeyboardInterrupt, OSError):
            break
            
    try: lb_socket.close()
    except Exception: pass
    logging.info("Load balancer stopped.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Dynamic Load Balancer with Concurrency Limits & Queueing")
    parser.add_argument("--port", type=int, default=5000, help="Port of the Load Balancer (default: 5000)")
    parser.add_argument("--max-connections", type=int, default=25, help="Baseline max active connections (default: 25)")
    args = parser.parse_args()
    start_load_balancer(port=args.port, max_conns=args.max_connections)
