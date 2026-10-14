"""Start both local services; Ctrl+C stops only the processes started here."""
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    node = shutil.which("node")
    vite = ROOT / "frontend" / "node_modules" / "vite" / "bin" / "vite.js"
    if not node or not vite.exists():
        print("Install Node.js and run npm ci in frontend first.", file=sys.stderr)
        return 1
    for port in (5000, 5173):
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                print(f"Port {port} is already in use. Stop the existing service first.", file=sys.stderr)
                return 1
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    processes = []
    try:
        processes.append(subprocess.Popen([sys.executable, "-m", "backend.app"], cwd=ROOT, creationflags=flags))
        processes.append(subprocess.Popen([node, str(vite), "--host", "127.0.0.1", "--strictPort"], cwd=ROOT / "frontend", creationflags=flags))
        print("Open http://127.0.0.1:5173/ — Ctrl+C stops both services.", flush=True)
        while all(process.poll() is None for process in processes):
            time.sleep(0.5)
        return 1
    except KeyboardInterrupt:
        return 0
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


if __name__ == "__main__":
    raise SystemExit(main())
