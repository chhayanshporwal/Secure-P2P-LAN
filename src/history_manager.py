import sqlite3
import os
import sys
import time
from datetime import datetime

def _get_db_path():
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), "transfer_history.db")
    base = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(base) == "src":
        return os.path.join(os.path.dirname(base), "transfer_history.db")
    return os.path.join(base, "transfer_history.db")

DB_PATH = _get_db_path()

class HistoryManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(HistoryManager, cls).__new__(cls, *args, **kwargs)
            cls._instance._init_db()
        return cls._instance

    def _init_db(self):
        try:
            with sqlite3.connect(DB_PATH, timeout=10) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS transfers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        direction TEXT NOT NULL,
                        peer_name TEXT NOT NULL,
                        peer_ip TEXT NOT NULL,
                        filename TEXT NOT NULL,
                        filesize INTEGER NOT NULL,
                        timestamp TEXT NOT NULL,
                        duration_sec REAL DEFAULT 0.0,
                        speed_mbps REAL DEFAULT 0.0,
                        status TEXT NOT NULL,
                        file_path TEXT DEFAULT ''
                    )
                """)
                conn.commit()
        except Exception as e:
            print(f"[HistoryManager] DB Init Error: {e}")

    def add_record(self, direction, peer_name, peer_ip, filename, filesize, duration_sec, speed_mbps, status, file_path=""):
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with sqlite3.connect(DB_PATH, timeout=10) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO transfers (
                        direction, peer_name, peer_ip, filename, filesize,
                        timestamp, duration_sec, speed_mbps, status, file_path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    direction,
                    peer_name or "Unknown",
                    peer_ip or "0.0.0.0",
                    filename or "Unknown",
                    int(filesize or 0),
                    timestamp,
                    round(float(duration_sec or 0.0), 2),
                    round(float(speed_mbps or 0.0), 2),
                    status or "Unknown",
                    file_path or ""
                ))
                conn.commit()
        except Exception as e:
            print(f"[HistoryManager] Add Record Error: {e}")

    def get_all_records(self, limit=200):
        try:
            with sqlite3.connect(DB_PATH, timeout=10) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM transfers ORDER BY id DESC LIMIT ?", (limit,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"[HistoryManager] Get Records Error: {e}")
            return []

    def clear_history(self):
        try:
            with sqlite3.connect(DB_PATH, timeout=10) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM transfers")
                conn.commit()
            return True
        except Exception as e:
            print(f"[HistoryManager] Clear History Error: {e}")
            return False

if __name__ == "__main__":
    hm = HistoryManager()
    hm.add_record(
        direction="SENT",
        peer_name="Alice",
        peer_ip="192.168.1.50",
        filename="research_paper.pdf",
        filesize=15420000,
        duration_sec=3.4,
        speed_mbps=4.5,
        status="Completed",
        file_path="/path/to/research_paper.pdf"
    )
    print("History record sample:", hm.get_all_records())
