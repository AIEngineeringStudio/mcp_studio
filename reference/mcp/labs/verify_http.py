"""Start only our test server, verify HTTP contracts, and always clean it up."""
from pathlib import Path
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent


def listening():
    try:
        with socket.create_connection(("127.0.0.1", 8765), timeout=0.2):
            return True
    except OSError:
        return False


if __name__ == "__main__":
    if listening():
        raise SystemExit("Port 8765 is already in use; stop your lab server first.")
    process = subprocess.Popen(
        [sys.executable, str(ROOT / "server.py"), "--http"], cwd=ROOT,
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
    )
    try:
        deadline = time.monotonic() + 20
        while not listening():
            if process.poll() is not None:
                raise RuntimeError(process.stderr.read())
            if time.monotonic() > deadline:
                raise TimeoutError("Test server did not become ready in 20 seconds")
            time.sleep(0.1)
        subprocess.run([sys.executable, str(ROOT / "client.py"), "http"],
                       cwd=ROOT, check=True, timeout=30)
    finally:
        if process.poll() is None:
            process.terminate()
        try:
            process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
