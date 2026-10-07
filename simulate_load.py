import subprocess
import time
import argparse
import sys

def main(lb_ip, filepath, num_clients):
    print(f"Starting {num_clients} concurrent file transfers to Load Balancer at {lb_ip}...")
    
    processes = []
    for i in range(num_clients):
        # We start the sender script as a subprocess
        cmd = ["python", "sender.py", lb_ip, filepath]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        processes.append((i+1, p))
        time.sleep(0.1) # Stagger slightly
        
    print("All clients spawned. Waiting for them to finish (or press Ctrl+C to abort)...")
    
    try:
        while processes:
            for i, p in processes[:]:
                ret = p.poll()
                if ret is not None:
                    out = p.stdout.read()
                    print(f"--- Client {i} Finished (Code {ret}) ---")
                    # print(out) # Uncomment to see full logs from each client
                    processes.remove((i, p))
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\nAborting...")
        for i, p in processes:
            p.kill()
        sys.exit(0)
        
    print("Simulation complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate load on the P2P network")
    parser.add_argument("lb_ip", help="IP address of the Load Balancer")
    parser.add_argument("filepath", help="Path of the file to send")
    parser.add_argument("--clients", type=int, default=10, help="Number of concurrent clients")
    
    args = parser.parse_args()
    main(args.lb_ip, args.filepath, args.clients)
