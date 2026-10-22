import threading
import logging
import time

from load_balancer import start_load_balancer
from receiver import start_server

logging.basicConfig(level=logging.INFO, format='%(asctime)s - DAEMON - %(levelname)s - %(message)s')

class ServiceDaemon:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super(ServiceDaemon, cls).__new__(cls, *args, **kwargs)
                cls._instance._is_running = False
                cls._instance._stop_event = threading.Event()
                cls._instance._threads = []
        return cls._instance

    def is_running(self):
        return self._is_running

    def start(self, lb_port=5000, worker_ports=[5001, 5002, 5003], max_conns=25):
        with self._lock:
            if self._is_running:
                logging.info("Service daemon already running.")
                return True

            self._stop_event.clear()
            self._threads = []

            # 1. Start Worker Nodes
            for port in worker_ports:
                t = threading.Thread(
                    target=start_server,
                    args=(port, self._stop_event),
                    daemon=True,
                    name=f"WorkerThread-{port}"
                )
                t.start()
                self._threads.append(t)

            time.sleep(0.3) # Short buffer for workers to bind

            # 2. Start Load Balancer
            lb_thread = threading.Thread(
                target=start_load_balancer,
                args=(lb_port, max_conns, self._stop_event, worker_ports),
                daemon=True,
                name=f"LoadBalancerThread-{lb_port}"
            )
            lb_thread.start()
            self._threads.append(lb_thread)

            self._is_running = True
            logging.info(f"Background P2P Receiver Engine successfully started (LB Port: {lb_port}, Workers: {worker_ports}).")
            return True

    def stop(self):
        with self._lock:
            if not self._is_running:
                return True

            logging.info("Stopping background P2P Receiver Engine...")
            self._stop_event.set()
            self._is_running = False
            return True

# Convenience global instance
daemon_instance = ServiceDaemon()
