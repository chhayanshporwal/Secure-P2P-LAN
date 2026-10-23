import sys
import os
import time

SRC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from service_daemon import daemon_instance
from sender import send_file_with_resume
from receiver import add_receive_listener
from history_manager import HistoryManager
from client_gui import format_size, format_speed

received_events = []

def test_listener(sender_name, peer_ip, filename, filesize):
    received_events.append({
        "sender": sender_name,
        "ip": peer_ip,
        "filename": filename,
        "size": filesize,
        "size_formatted": format_size(filesize)
    })
    print(f"[TEST LISTENER] Captured: {sender_name} sent {filename} ({format_size(filesize)})")

add_receive_listener(test_listener)

print("1. Starting background engine...")
daemon_instance.start(lb_port=5200, worker_ports=[5201, 5202])
time.sleep(1)

test_file = "test_payload.bin"
with open(test_file, "wb") as f:
    f.write(os.urandom(2 * 1024 * 1024)) # 2 MB test file

try:
    print("2. Sending file via sender...")
    send_file_with_resume("127.0.0.1", 5200, test_file, sender_name="TesterBob")
    time.sleep(1)

    print("3. Validating listener event...")
    assert len(received_events) >= 1, "Failed: listener was not called!"
    ev = received_events[0]
    assert ev["sender"] == "TesterBob"
    print(f"Listener verified: {ev}")

    print("4. Validating format_size and format_speed...")
    assert "GB" in format_size(1024 * 1024 * 1024)
    assert format_size(1024 * 1024 * 1024) == "1.00 GB"
    assert "MB/s" in format_speed(25.5)
    print("Format tests passed!")

    print("5. Validating History records...")
    records = HistoryManager().get_all_records(limit=5)
    assert len(records) > 0
    print(f"Latest history record: {records[0]['filename']} ({records[0]['direction']})")

    print("\nALL MODULAR AND NOTIFICATION TESTS PASSED SUCCESSFULLY!")

finally:
    daemon_instance.stop()
    if os.path.exists(test_file):
        os.remove(test_file)
