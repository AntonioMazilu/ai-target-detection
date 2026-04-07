import csv
import socket
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional


class UdpLabelListener:
    def __init__(
        self,
        bind_ip: str = "0.0.0.0",
        bind_port: int = 20000,
        buffer_size: int = 4096,
        csv_path: str = "/app/udp_listener_log.csv",
        max_recent: int = 120,
    ) -> None:
        self.bind_ip = bind_ip
        self.bind_port = bind_port
        self.buffer_size = buffer_size
        self.csv_path = Path(csv_path)
        self.max_recent = max_recent

        self._lock = threading.Lock()
        self._recent: Deque[Dict[str, Any]] = deque(maxlen=max_recent)
        self._received_count = 0
        self._listening = False
        self._last_error: Optional[str] = None
        self._last_message: Optional[Dict[str, Any]] = None

        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()

    @staticmethod
    def _normalize_csv_row(row: Dict[str, str]) -> Dict[str, Any]:
        sender_port_raw = row.get("sender_port", "")
        try:
            sender_port = int(sender_port_raw)
        except (TypeError, ValueError):
            sender_port = sender_port_raw

        return {
            "timestamp": row.get("timestamp", ""),
            "sender_ip": row.get("sender_ip", ""),
            "sender_port": sender_port,
            "label": row.get("label", ""),
        }

    def _read_recent_from_csv(self, limit: int) -> List[Dict[str, Any]]:
        if not self.csv_path.exists():
            return []

        rows: Deque[Dict[str, Any]] = deque(maxlen=limit)
        with self.csv_path.open("r", newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                rows.append(self._normalize_csv_row(row))

        return list(reversed(rows))

    def _csv_stats(self) -> Dict[str, Any]:
        if not self.csv_path.exists():
            return {"count": 0, "last_message": None}

        count = 0
        last_row: Optional[Dict[str, Any]] = None
        with self.csv_path.open("r", newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                count += 1
                last_row = self._normalize_csv_row(row)

        return {"count": count, "last_message": last_row}

    def _append_csv_row(self, timestamp: str, sender_ip: str, sender_port: int, label: str) -> None:
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        file_exists = self.csv_path.exists()
        with self.csv_path.open("a", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            if not file_exists:
                writer.writerow(["timestamp", "sender_ip", "sender_port", "label"])
            writer.writerow([timestamp, sender_ip, sender_port, label])

    def _listen_loop(self) -> None:
        while True:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(1.0)

            try:
                sock.bind((self.bind_ip, self.bind_port))
                with self._lock:
                    self._listening = True
                    self._last_error = None
            except Exception as exc:
                with self._lock:
                    self._listening = False
                    self._last_error = f"UDP listener bind failed: {exc}"
                sock.close()
                time.sleep(2)
                continue

            try:
                while True:
                    try:
                        data, addr = sock.recvfrom(self.buffer_size)
                    except socket.timeout:
                        continue

                    label = data.decode("utf-8", errors="replace").strip()
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                    message = {
                        "timestamp": timestamp,
                        "sender_ip": addr[0],
                        "sender_port": addr[1],
                        "label": label,
                    }

                    try:
                        self._append_csv_row(
                            timestamp=timestamp,
                            sender_ip=addr[0],
                            sender_port=addr[1],
                            label=label,
                        )
                    except Exception as exc:
                        with self._lock:
                            self._last_error = f"CSV write failed: {exc}"

                    with self._lock:
                        self._recent.append(message)
                        self._last_message = message
                        self._received_count += 1
            except Exception as exc:
                with self._lock:
                    self._last_error = f"UDP listener error: {exc}"
            finally:
                with self._lock:
                    self._listening = False
                sock.close()
                time.sleep(1)

    def get_recent(self, limit: int = 25) -> List[Dict[str, Any]]:
        limit = max(1, min(limit, self.max_recent))
        try:
            return self._read_recent_from_csv(limit=limit)
        except Exception as exc:
            with self._lock:
                self._last_error = f"CSV read failed: {exc}"
                messages = list(self._recent)
            return list(reversed(messages[-limit:]))

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            listening = self._listening
            last_error = self._last_error
            memory_count = self._received_count
            memory_last = self._last_message

        csv_count = 0
        csv_last = None
        try:
            stats = self._csv_stats()
            csv_count = int(stats["count"])
            csv_last = stats["last_message"]
        except Exception as exc:
            last_error = f"CSV stats failed: {exc}"

        return {
            "bind_ip": self.bind_ip,
            "bind_port": self.bind_port,
            "buffer_size": self.buffer_size,
            "csv_path": str(self.csv_path),
            "listening": listening,
            "received_count": max(memory_count, csv_count),
            "last_error": last_error,
            "last_message": csv_last or memory_last,
        }
