#!/usr/bin/env python
"""
UrbanPulse visual boot console.

Starts the FastAPI backend and Vite frontend together, streams both logs into a
single terminal dashboard, and keeps the processes alive until Ctrl+C.

Usage from repo root:
    python scripts/boot_urbanpulse.py

Optional:
    python scripts/boot_urbanpulse.py --no-open
    python scripts/boot_urbanpulse.py --backend-port 8001 --frontend-port 5173
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import queue
import shutil
import signal
import socket
import subprocess
import sys
import textwrap
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from collections import deque
from pathlib import Path

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"
CLEAR = "\033[2J\033[H"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"


class Service:
    def __init__(self, name: str, label: str, command: list[str], cwd: Path, color: str, log_path: Path):
        self.name = name
        self.label = label
        self.command = command
        self.cwd = cwd
        self.color = color
        self.log_path = log_path
        self.process: subprocess.Popen[str] | None = None
        self.lines: deque[str] = deque(maxlen=180)
        self.status = "WAITING"
        self.ready = False
        self.started_at: float | None = None
        self.exit_code: int | None = None
        self._reader_thread: threading.Thread | None = None
        self._log_file = None

    def start(self) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._log_file = self.log_path.open("w", encoding="utf-8", errors="replace")
        self._write_internal(f"$ {' '.join(self.command)}")
        self.process = subprocess.Popen(
            self.command,
            cwd=str(self.cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        self.started_at = time.time()
        self.status = "BOOTING"
        self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._reader_thread.start()

    def _write_internal(self, line: str) -> None:
        stamped = f"[{now_clock()}] {line}"
        self.lines.append(stamped)
        if self._log_file:
            self._log_file.write(stamped + "\n")
            self._log_file.flush()

    def _read_loop(self) -> None:
        assert self.process is not None
        assert self.process.stdout is not None
        for raw in self.process.stdout:
            line = raw.rstrip("\n\r")
            self._write_internal(line)
        self.exit_code = self.process.poll()
        if self.exit_code is None:
            self.exit_code = self.process.wait()
        if self.exit_code == 0:
            self.status = "STOPPED"
        else:
            self.status = "FAILED"
        self._write_internal(f"process exited with code {self.exit_code}")

    def poll(self) -> int | None:
        if not self.process:
            return None
        code = self.process.poll()
        if code is not None:
            self.exit_code = code
        return code

    def terminate(self) -> None:
        if not self.process or self.process.poll() is not None:
            self._close_log()
            return
        self._write_internal("stopping process...")
        try:
            if os.name == "nt":
                # npm on Windows spawns a child node/vite process. Kill the whole tree
                # so Ctrl+C from the boot console does not leave port 5173 occupied.
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(self.process.pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
                self.process.wait(timeout=8)
            else:
                self.process.send_signal(signal.SIGTERM)
                self.process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            self._write_internal("process did not stop; killing...")
            self.process.kill()
            self.process.wait(timeout=5)
        except Exception as exc:  # pragma: no cover - defensive shutdown
            self._write_internal(f"shutdown warning: {exc!r}")
        self._close_log()

    def _close_log(self) -> None:
        if self._log_file:
            self._log_file.flush()
            self._log_file.close()
            self._log_file = None

    def recent(self, n: int) -> list[str]:
        return list(self.lines)[-n:]


def now_clock() -> str:
    return dt.datetime.now().strftime("%H:%M:%S")


def strip_ansi_len(s: str) -> int:
    # This dashboard only injects ANSI around whole fields, not into log content.
    return len(s)


def fit(text: str, width: int) -> str:
    if width <= 1:
        return ""
    if strip_ansi_len(text) <= width:
        return text + " " * (width - strip_ansi_len(text))
    return text[: max(0, width - 1)] + "…"


def box_line(left: str, right: str = "", width: int = 100) -> str:
    if right:
        middle = f" {left} "
        tail = f" {right} "
        fill = max(0, width - len(middle) - len(tail) - 2)
        return "│" + middle + "─" * fill + tail + "│"
    return "│" + fit(" " + left, width - 2) + "│"


def port_is_open(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.35)
        return sock.connect_ex((host, port)) == 0


def http_json(url: str, timeout: float = 0.6) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def http_ok(url: str, timeout: float = 0.6) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def check_prereqs() -> list[str]:
    missing = []
    if not BACKEND_DIR.exists():
        missing.append(f"missing backend directory: {BACKEND_DIR}")
    if not FRONTEND_DIR.exists():
        missing.append(f"missing frontend directory: {FRONTEND_DIR}")
    if not command_exists("npm"):
        missing.append("npm is not on PATH")
    if not (BACKEND_DIR / "main.py").exists():
        missing.append("backend/main.py not found")
    if not (FRONTEND_DIR / "package.json").exists():
        missing.append("frontend/package.json not found")
    if not (FRONTEND_DIR / "node_modules").exists():
        missing.append("frontend/node_modules not found; run: cd frontend && npm install")
    return missing


def status_pill(service: Service) -> str:
    if service.status == "ONLINE":
        return f"{GREEN}ONLINE{RESET}"
    if service.status == "BOOTING":
        return f"{YELLOW}BOOTING{RESET}"
    if service.status == "FAILED":
        return f"{RED}FAILED{RESET}"
    if service.status == "STOPPED":
        return f"{DIM}STOPPED{RESET}"
    return f"{DIM}{service.status}{RESET}"


def render(args, backend: Service, frontend: Service, started: float, log_dir: Path, message: str, node_summary: str) -> str:
    width = min(max(shutil.get_terminal_size((116, 32)).columns, 88), 132)
    log_rows_each = 8 if shutil.get_terminal_size((116, 32)).lines >= 34 else 5
    uptime = int(time.time() - started)
    backend_pid = backend.process.pid if backend.process else "-"
    frontend_pid = frontend.process.pid if frontend.process else "-"
    backend_label = f"Backend  {status_pill(backend)}  http://localhost:{args.backend_port}"
    frontend_label = f"Frontend {status_pill(frontend)}  http://localhost:{args.frontend_port}"
    banner = [
        CLEAR + HIDE_CURSOR,
        f"{CYAN}╔{'═' * (width - 2)}╗{RESET}",
        f"{CYAN}║{RESET}{BOLD}{fit('  URBANPULSE LIVE BOOT CONSOLE  ', width - 2)}{RESET}{CYAN}║{RESET}",
        f"{CYAN}╠{'═' * (width - 2)}╣{RESET}",
        f"{CYAN}{box_line(backend_label, f'pid {backend_pid}', width)}{RESET}",
        f"{CYAN}{box_line(frontend_label, f'pid {frontend_pid}', width)}{RESET}",
        f"{CYAN}{box_line(f'Uptime {uptime}s', node_summary or 'waiting for health data', width)}{RESET}",
        f"{CYAN}╠{'═' * (width - 2)}╣{RESET}",
        f"{CYAN}{box_line('Logs: ' + str(log_dir), message, width)}{RESET}",
        f"{CYAN}╠{'═' * (width - 2)}╣{RESET}",
        f"{CYAN}{box_line('BACKEND STREAM', width=width)}{RESET}",
    ]
    for line in backend.recent(log_rows_each):
        banner.append(f"{CYAN}║{RESET} {GREEN}{fit(line, width - 4)}{RESET} {CYAN}║{RESET}")
    while len([x for x in banner if x]) < 11 + log_rows_each:
        banner.append(f"{CYAN}║{RESET}{' ' * (width - 2)}{CYAN}║{RESET}")
    banner += [
        f"{CYAN}╠{'═' * (width - 2)}╣{RESET}",
        f"{CYAN}{box_line('FRONTEND STREAM', width=width)}{RESET}",
    ]
    for line in frontend.recent(log_rows_each):
        banner.append(f"{CYAN}║{RESET} {MAGENTA}{fit(line, width - 4)}{RESET} {CYAN}║{RESET}")
    banner += [
        f"{CYAN}╠{'═' * (width - 2)}╣{RESET}",
        f"{CYAN}{box_line('Ctrl+C stops backend + frontend cleanly. Browser URL: http://localhost:' + str(args.frontend_port), width=width)}{RESET}",
        f"{CYAN}╚{'═' * (width - 2)}╝{RESET}",
    ]
    return "\n".join(banner)


def clear_vite_cache() -> None:
    cache = FRONTEND_DIR / "node_modules" / ".vite"
    if cache.exists():
        shutil.rmtree(cache, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Start UrbanPulse backend + frontend in one visual boot console.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--backend-port", type=int, default=8001)
    parser.add_argument("--frontend-port", type=int, default=5173)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--no-open", action="store_true", help="do not open the browser automatically")
    parser.add_argument("--keep-vite-cache", action="store_true", help="do not clear frontend/node_modules/.vite before start")
    parser.add_argument("--ready-timeout", type=int, default=90, help="seconds to wait before marking boot as slow")
    args = parser.parse_args()

    os.chdir(ROOT)
    prereq_errors = check_prereqs()
    if prereq_errors:
        print(f"{RED}UrbanPulse boot cannot start:{RESET}")
        for err in prereq_errors:
            print(f"  - {err}")
        print("\nInstall the normal project dependencies first:")
        print("  cd backend && python -m pip install -r requirements.txt")
        print("  cd frontend && npm install")
        return 2

    conflicts = []
    if port_is_open(args.backend_port):
        conflicts.append(f"backend port {args.backend_port} is already in use")
    if port_is_open(args.frontend_port):
        conflicts.append(f"frontend port {args.frontend_port} is already in use")
    if conflicts:
        print(f"{RED}UrbanPulse boot found busy ports:{RESET}")
        for item in conflicts:
            print(f"  - {item}")
        print("\nStop the old dev servers first, then run this script again.")
        return 3

    if not args.keep_vite_cache:
        clear_vite_cache()

    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = ROOT / "logs" / f"boot_{stamp}"
    npm_cmd = shutil.which("npm") or shutil.which("npm.cmd")
    if not npm_cmd:
        print(f"{RED}UrbanPulse boot cannot start: npm is not on PATH{RESET}")
        return 2

    backend = Service(
        "backend",
        "FastAPI backend",
        [sys.executable, "-m", "uvicorn", "main:app", "--host", args.host, "--port", str(args.backend_port)],
        BACKEND_DIR,
        GREEN,
        log_dir / "backend.log",
    )
    frontend = Service(
        "frontend",
        "Vite frontend",
        [npm_cmd, "run", "dev", "--", "--host", args.host, "--port", str(args.frontend_port)],
        FRONTEND_DIR,
        MAGENTA,
        log_dir / "frontend.log",
    )

    started = time.time()
    message = "starting services"
    browser_opened = False
    node_summary = "waiting for /api/health"

    try:
        backend.start()
        time.sleep(0.7)
        frontend.start()

        while True:
            backend.poll()
            frontend.poll()

            health = http_json(f"http://127.0.0.1:{args.backend_port}/api/health")
            nodes = http_json(f"http://127.0.0.1:{args.backend_port}/api/nodes")
            frontend_ok = http_ok(f"http://127.0.0.1:{args.frontend_port}/")
            proxy_health = http_json(f"http://127.0.0.1:{args.frontend_port}/api/health") if frontend_ok else None

            if health and backend.status != "FAILED":
                backend.status = "ONLINE"
                backend.ready = True
                packets = health.get("total_packets", "?")
                age = health.get("last_packet_age_ms", "?")
                node_summary = f"backend healthy | packets {packets} | last age {age}ms"
            elif backend.poll() is None and backend.status != "FAILED":
                backend.status = "BOOTING"

            if frontend_ok and proxy_health and frontend.status != "FAILED":
                frontend.status = "ONLINE"
                frontend.ready = True
            elif frontend.poll() is None and frontend.status != "FAILED":
                frontend.status = "BOOTING"

            if isinstance(nodes, list) and nodes:
                online = [str(n.get("node_id")) for n in nodes if n.get("state") == "ONLINE"]
                if online:
                    node_summary = f"nodes online: {', '.join(online)} | " + node_summary

            if backend.ready and frontend.ready:
                message = "ready"
                if not browser_opened and not args.no_open:
                    webbrowser.open(f"http://localhost:{args.frontend_port}")
                    browser_opened = True
            elif time.time() - started > args.ready_timeout:
                message = "boot is taking longer than expected; inspect logs below"

            print(render(args, backend, frontend, started, log_dir, message, node_summary), flush=True)
            time.sleep(1.0)

            if backend.exit_code not in (None, 0) or frontend.exit_code not in (None, 0):
                message = "a service exited; stopping boot console"
                print(render(args, backend, frontend, started, log_dir, message, node_summary), end="", flush=True)
                return 1

    except KeyboardInterrupt:
        print(SHOW_CURSOR)
        print(f"\n{YELLOW}Stopping UrbanPulse services...{RESET}")
        return 0
    finally:
        frontend.terminate()
        backend.terminate()
        print(SHOW_CURSOR, end="")
        print(f"\nLogs saved under: {log_dir}")


if __name__ == "__main__":
    raise SystemExit(main())
