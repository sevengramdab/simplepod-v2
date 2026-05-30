#!/usr/bin/env python3
"""
Shadow PC Watcher
=================
Continuously polls the Shadow PC node and captures forensic state
 the millisecond it comes back online.

ELI5: Think of this like a motion-activated security camera DVR.
       It sits quietly in the dark, but the instant the breaker panel
       lights come back on, it starts recording every meter reading.

Usage:
    python scripts/shadow_watcher.py

It will run forever until you Ctrl+C it.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SHADOW_IP = os.environ.get("SHADOW_IP", "100.64.0.2")
SHADOW_PORT = int(os.environ.get("SHADOW_PORT", "8002"))
LOCAL_BACKEND = os.environ.get("LOCAL_BACKEND", "http://localhost:8000")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "5"))  # seconds when offline
CAPTURE_DIR = Path("shadow_captures")
LOG_DIR = Path("logs")
WATCHER_LOG = LOG_DIR / "shadow_watcher.log"
RECOVERY_JSON = CAPTURE_DIR / "last_recovery.json"
STATE_JSON = CAPTURE_DIR / "watcher_state.json"

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
def setup_logging() -> None:
    LOG_DIR.mkdir(exist_ok=True)
    CAPTURE_DIR.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(WATCHER_LOG, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ts() -> str:
    return _now().strftime("%Y%m%d_%H%M%S")


def _fmt_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    if seconds < 3600:
        return f"{seconds / 60:.1f}m"
    return f"{seconds / 3600:.1f}h"


# ---------------------------------------------------------------------------
# Network probes
# ---------------------------------------------------------------------------
def probe_shadow_health(timeout: float = 3.0) -> dict[str, Any] | None:
    """Hit /health on Shadow PC. Returns JSON or None if unreachable."""
    try:
        url = f"http://{SHADOW_IP}:{SHADOW_PORT}/health"
        resp = requests.get(url, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def probe_local_backend(timeout: float = 3.0) -> dict[str, Any] | None:
    """Hit /health on local backend."""
    try:
        resp = requests.get(f"{LOCAL_BACKEND}/health", timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Capture routines
# ---------------------------------------------------------------------------
def capture_screenshot() -> Path | None:
    """Fetch /remote/screenshot from Shadow PC and save to disk."""
    try:
        url = f"http://{SHADOW_IP}:{SHADOW_PORT}/remote/screenshot"
        resp = requests.get(url, timeout=15)
        data = resp.json()
        if not data.get("success"):
            logging.warning("Screenshot endpoint returned success=False")
            return None

        img_data = base64.b64decode(data["image_base64"])
        filename = CAPTURE_DIR / f"shadow_{_ts()}.png"
        filename.write_bytes(img_data)
        logging.info(
            "📸 Screenshot saved: %s (%dx%d, %d bytes)",
            filename,
            data.get("width", 0),
            data.get("height", 0),
            len(img_data),
        )
        return filename
    except Exception as exc:
        logging.error("Screenshot capture failed: %s", exc)
    return None


def capture_status() -> dict[str, Any] | None:
    """Fetch /remote/status from Shadow PC."""
    try:
        url = f"http://{SHADOW_IP}:{SHADOW_PORT}/remote/status"
        resp = requests.get(url, timeout=5)
        data = resp.json()
        logging.info(
            "📊 Status — CPU %s%% | Memory %s%% | Disk %s%% | Kimi %s | Tasks %s",
            data.get("cpu_percent", "?"),
            data.get("memory_percent", "?"),
            data.get("disk_percent", "?"),
            "✅" if data.get("kimi_running") else "❌",
            data.get("active_tasks", "?"),
        )
        return data
    except Exception as exc:
        logging.error("Status capture failed: %s", exc)
    return None


def capture_processes(filter_kimi: bool = True) -> list[dict] | None:
    """Fetch /remote/processes from Shadow PC."""
    try:
        url = f"http://{SHADOW_IP}:{SHADOW_PORT}/remote/processes"
        if filter_kimi:
            url += "?filter=kimi"
        resp = requests.get(url, timeout=5)
        data = resp.json()
        procs = data.get("processes", [])
        logging.info("🔍 Processes captured: %d entries", len(procs))
        return procs
    except Exception as exc:
        logging.error("Process capture failed: %s", exc)
    return None


def capture_logs(lines: int = 100, logfile: str = "shadow") -> list[str] | None:
    """Fetch /remote/logs from Shadow PC."""
    try:
        url = f"http://{SHADOW_IP}:{SHADOW_PORT}/remote/logs?lines={lines}&logfile={logfile}"
        resp = requests.get(url, timeout=5)
        data = resp.json()
        log_lines = data.get("lines", [])
        logging.info("📝 Log tail captured: %d lines (%s)", len(log_lines), logfile)
        return log_lines
    except Exception as exc:
        logging.error("Log capture failed: %s", exc)
    return None


def inject_wake_task() -> dict[str, Any] | None:
    """Send a wake-up task to Shadow PC via /remote/inject."""
    try:
        url = f"http://{SHADOW_IP}:{SHADOW_PORT}/remote/inject"
        payload = {
            "prompt": (
                "Shadow PC watcher detected node recovery. "
                "Report current system status, check for any crashed services, "
                "and restart the SimplePod shadow node if it is not running."
            ),
            "model": None,
            "mode": "agent",
        }
        resp = requests.post(url, json=payload, timeout=10)
        data = resp.json()
        logging.info("💉 Wake task injected: %s", data.get("message", data))
        return data
    except Exception as exc:
        logging.error("Wake task injection failed: %s", exc)
    return None


# ---------------------------------------------------------------------------
# Recovery persistence
# ---------------------------------------------------------------------------
def write_recovery_report(
    status: dict | None,
    screenshot: Path | None,
    processes: list | None,
    logs: list | None,
    downtime_seconds: float | None,
) -> None:
    """Write recovery data so the VS Code: extension can pick it up."""
    report = {
        "recovered_at": _now().isoformat(),
        "shadow_ip": f"{SHADOW_IP}:{SHADOW_PORT}",
        "downtime_seconds": downtime_seconds,
        "downtime_formatted": _fmt_duration(downtime_seconds) if downtime_seconds else None,
        "status": status,
        "screenshot": str(screenshot) if screenshot else None,
        "process_count": len(processes) if processes else 0,
        "log_lines_captured": len(logs) if logs else 0,
    }
    RECOVERY_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    # Also append to a history file
    with open(CAPTURE_DIR / "recovery_history.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(report, default=str) + "\n")


def write_watcher_state(online: bool, offline_since: datetime | None) -> None:
    """Write current watcher state for external consumers."""
    state = {
        "timestamp": _now().isoformat(),
        "shadow_online": online,
        "shadow_ip": f"{SHADOW_IP}:{SHADOW_PORT}",
        "local_backend_ok": probe_local_backend() is not None,
        "offline_since": offline_since.isoformat() if offline_since else None,
    }
    STATE_JSON.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Windows toast notification (optional)
# ---------------------------------------------------------------------------
def toast_notify(title: str, message: str) -> None:
    """Fire a Windows toast notification if win10toast is available."""
    try:
        from win10toast import ToastNotifier
        ToastNotifier().show_toast(title, message, duration=10)
    except Exception:
        # Fallback: PowerShell notification
        try:
            cmd = [
                "powershell",
                "-Command",
                f"Add-Type -AssemblyName System.Windows.Forms; "
                f"[System.Windows.Forms.MessageBox]::Show('{message}', '{title}')",
            ]
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
def main() -> None:
    setup_logging()
    logging.info("=" * 60)
    logging.info("🔦 Shadow PC Watcher started")
    logging.info("   Target : %s:%d", SHADOW_IP, SHADOW_PORT)
    logging.info("   Local  : %s", LOCAL_BACKEND)
    logging.info("   Poll   : %ds", POLL_INTERVAL)
    logging.info("   Logs   : %s", WATCHER_LOG)
    logging.info("=" * 60)

    was_online = False
    offline_since: datetime | None = None
    probe_count = 0

    try:
        while True:
            probe_count += 1
            health = probe_shadow_health()
            online = health is not None

            # Write state every cycle so external tools can observe
            write_watcher_state(online, offline_since)

            if online and not was_online:
                # -----------------------------------------------------------
                # SHADOW PC JUST CAME BACK ONLINE
                # -----------------------------------------------------------
                now = _now()
                downtime = (now - offline_since).total_seconds() if offline_since else None
                logging.info("🔔🔔🔔 SHADOW PC IS BACK ONLINE! 🔔🔔🔔")
                if downtime:
                    logging.info("   Downtime: %s", _fmt_duration(downtime))

                # 1. Capture status
                status = capture_status()

                # 2. Capture screenshot
                screenshot = capture_screenshot()

                # 3. Capture processes
                processes = capture_processes(filter_kimi=True)

                # 4. Capture logs
                logs = capture_logs(lines=100, logfile="shadow")

                # 5. Inject wake task
                inject_wake_task()

                # 6. Persist everything
                write_recovery_report(status, screenshot, processes, logs, downtime)

                # 7. Notify user
                toast_notify(
                    "Shadow PC Recovered",
                    f"Shadow PC back online after {_fmt_duration(downtime) if downtime else 'unknown'} downtime. "
                    f"Screenshot and status captured.",
                )

                was_online = True
                offline_since = None

            elif not online and was_online:
                # -----------------------------------------------------------
                # SHADOW PC JUST WENT OFFLINE
                # -----------------------------------------------------------
                logging.warning("⚠️  SHADOW PC WENT OFFLINE")
                was_online = False
                offline_since = _now()
                toast_notify("Shadow PC Offline", "Lost connection to Shadow PC node.")

            elif not online and not was_online:
                # Still offline — heartbeat every ~60s to avoid log spam
                if probe_count % (60 // max(POLL_INTERVAL, 1)) == 0:
                    logging.info("   ...still waiting for %s:%d", SHADOW_IP, SHADOW_PORT)

            else:
                # Still online — light heartbeat every ~5 min
                if probe_count % (300 // max(POLL_INTERVAL, 1)) == 0:
                    logging.info("   Shadow PC still online (%s)", _now().strftime("%H:%M:%S"))

            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        logging.info("Watcher stopped by user.")
        write_watcher_state(False, offline_since)
        sys.exit(0)


if __name__ == "__main__":
    main()
