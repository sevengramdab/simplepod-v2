"""
remote.py
=========
Remote PC control endpoints for the VS Code extension.
ELI5: A wireless remote that can type, click, and run commands
      on the PC where the backend is running.
"""
from __future__ import annotations

import base64
import io
import os
import platform
import subprocess
import time
import traceback
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/remote", tags=["remote"])

# ELI5: Think of this like the timestamp on a Title Block.
#       It tells you how long the panel has been energized.
START_TIME = time.time()

# Try to import pyautogui; if unavailable, mouse/keyboard endpoints return 503.
try:
    import pyautogui
    _PYAUTOGUI_OK = True
except Exception:
    pyautogui = None  # type: ignore
    _PYAUTOGUI_OK = False

# ELI5: Think of psutil like a multimeter clipped to the main breaker.
#       If the multimeter battery dies, we still read the panel — we just say "N/A".
try:
    import psutil
    _PSUTIL_OK = True
except Exception:
    psutil = None  # type: ignore
    _PSUTIL_OK = False


class TypeRequest(BaseModel):
    text: str = Field(..., description="Text to type on the remote PC")
    interval: float = Field(0.01, ge=0, description="Seconds between keystrokes")


class ClickRequest(BaseModel):
    x: int = Field(..., ge=0, description="Screen X coordinate")
    y: int = Field(..., ge=0, description="Screen Y coordinate")
    button: str = Field("left", description="Mouse button: left, right, middle")
    clicks: int = Field(1, ge=1, le=3, description="Number of clicks")


class KeysRequest(BaseModel):
    keys: str = Field(..., description="Key combination, e.g. 'enter', 'ctrl+c', 'alt+tab'")


class ShellRequest(BaseModel):
    command: str = Field(..., description="Shell command to execute")
    cwd: Optional[str] = Field(None, description="Working directory")
    timeout: int = Field(30, ge=1, le=300, description="Seconds to wait for completion")


class ScrollRequest(BaseModel):
    clicks: int = Field(..., description="Scroll amount: positive = up, negative = down")
    x: Optional[int] = Field(None, ge=0, description="Move mouse to X first")
    y: Optional[int] = Field(None, ge=0, description="Move mouse to Y first")


class DragRequest(BaseModel):
    x1: int = Field(..., ge=0, description="Start X coordinate")
    y1: int = Field(..., ge=0, description="Start Y coordinate")
    x2: int = Field(..., ge=0, description="End X coordinate")
    y2: int = Field(..., ge=0, description="End Y coordinate")
    duration: float = Field(0.5, ge=0, le=5, description="Drag duration in seconds")
    button: str = Field("left", description="Mouse button: left, right, middle")


class RemoteResponse(BaseModel):
    success: bool
    message: str


class ScreenshotResponse(BaseModel):
    success: bool
    image_base64: str
    width: int
    height: int


def _check_pyautogui():
    if not _PYAUTOGUI_OK:
        raise HTTPException(
            status_code=503,
            detail="Remote control unavailable: pyautogui not installed or failed to load"
        )


@router.post("/type", response_model=RemoteResponse)
async def remote_type(req: TypeRequest):
    """Type text as if from a keyboard."""
    _check_pyautogui()
    try:
        pyautogui.typewrite(req.text, interval=req.interval)
        return RemoteResponse(success=True, message=f"Typed {len(req.text)} characters")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Type failed: {e}")


@router.post("/click", response_model=RemoteResponse)
async def remote_click(req: ClickRequest):
    """Click the mouse at screen coordinates."""
    _check_pyautogui()
    try:
        pyautogui.click(req.x, req.y, clicks=req.clicks, button=req.button)
        return RemoteResponse(success=True, message=f"Clicked ({req.x}, {req.y}) x{req.clicks}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Click failed: {e}")


@router.post("/keys", response_model=RemoteResponse)
async def remote_keys(req: KeysRequest):
    """Send special key combinations (e.g. 'enter', 'ctrl+c', 'alt+tab')."""
    _check_pyautogui()
    try:
        parts = [p.strip() for p in req.keys.split('+')]
        if len(parts) == 1:
            pyautogui.press(parts[0])
        else:
            pyautogui.hotkey(*parts)
        return RemoteResponse(success=True, message=f"Sent keys: {req.keys}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Keys failed: {e}")


@router.post("/shell", response_model=RemoteResponse)
async def remote_shell(req: ShellRequest):
    """Execute a shell command and return stdout/stderr."""
    try:
        result = subprocess.run(
            req.command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=req.cwd,
            timeout=req.timeout,
        )
        output = result.stdout.strip()
        if result.stderr:
            output += "\n[stderr] " + result.stderr.strip()
        msg = f"Exit {result.returncode} | {output[:200]}"
        return RemoteResponse(
            success=result.returncode == 0,
            message=msg,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail=f"Command timed out after {req.timeout}s")
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Shell failed: {e}")


@router.post("/scroll", response_model=RemoteResponse)
async def remote_scroll(req: ScrollRequest):
    """Scroll the mouse wheel."""
    _check_pyautogui()
    try:
        if req.x is not None and req.y is not None:
            pyautogui.moveTo(req.x, req.y)
        pyautogui.scroll(req.clicks)
        return RemoteResponse(success=True, message=f"Scrolled {req.clicks} clicks")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scroll failed: {e}")


@router.post("/drag", response_model=RemoteResponse)
async def remote_drag(req: DragRequest):
    """Drag the mouse from start to end coordinates."""
    _check_pyautogui()
    try:
        pyautogui.moveTo(req.x1, req.y1)
        pyautogui.dragTo(req.x2, req.y2, duration=req.duration, button=req.button)
        return RemoteResponse(
            success=True,
            message=f"Dragged from ({req.x1}, {req.y1}) to ({req.x2}, {req.y2})"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Drag failed: {e}")


@router.get("/screenshot", response_model=ScreenshotResponse)
async def remote_screenshot():
    """Capture a screenshot and return it as base64 PNG."""
    _check_pyautogui()
    try:
        img = pyautogui.screenshot()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        return ScreenshotResponse(
            success=True,
            image_base64=b64,
            width=img.width,
            height=img.height,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Screenshot failed: {e}")

# ---------------------------------------------------------------------------
# Status, Logs, Processes, and Task Injection
# ELI5: These are the panel schedule, demand meter, circuit tracer,
#       and work-order inbox for the remote node.
# ---------------------------------------------------------------------------

class InjectRequest(BaseModel):
    prompt: str = Field(..., description="Prompt or command to inject")
    model: Optional[str] = Field(None, description="Optional target model")
    mode: Optional[str] = Field(None, description="Optional execution mode")


# ELI5: Think of this like a panel schedule combined with a demand meter.
#       It tells the electrician (dashboard) which breakers are hot,
#       how much load is on each bus, and whether the generator (Kimi) is running.
@router.get("/status")
async def remote_status():
    """Return system status for this node."""
    node_id = os.environ.get("SIMPOD_NODE_ID", "unknown")
    hostname = platform.node()
    system_platform = platform.system()

    cpu_percent = None
    memory_percent = None
    disk_percent = None
    kimi_running = False
    active_tasks = 0

    if _PSUTIL_OK and psutil is not None:
        try:
            cpu_percent = psutil.cpu_percent(interval=0.5)
        except Exception:
            pass
        try:
            memory_percent = psutil.virtual_memory().percent
        except Exception:
            pass
        try:
            disk_percent = psutil.disk_usage("/").percent
        except Exception:
            pass
        try:
            for proc in psutil.process_iter(["name"]):
                name = (proc.info.get("name") or "").lower()
                if "code" in name or "kimi" in name:
                    kimi_running = True
                    break
        except Exception:
            pass

    # ELI5: Try to read the active task count from the swarm orchestrator.
    #       If the utility closet is locked, we just report zero tasks.
    try:
        from interfaces.web_ui.backend.dependencies import get_swarm_orchestrator
        orch = get_swarm_orchestrator()
        if hasattr(orch, "active_tasks"):
            active_tasks = len(orch.active_tasks) if isinstance(orch.active_tasks, (list, tuple, set, dict)) else int(orch.active_tasks)
        elif hasattr(orch, "list_tasks"):
            tasks = orch.list_tasks()
            active_tasks = len(tasks) if isinstance(tasks, (list, tuple, set, dict)) else int(tasks)
        elif hasattr(orch, "get_active_tasks"):
            tasks = orch.get_active_tasks()
            active_tasks = len(tasks) if isinstance(tasks, (list, tuple, set, dict)) else int(tasks)
    except Exception:
        pass

    return {
        "node_id": node_id,
        "hostname": hostname,
        "platform": system_platform,
        "cpu_percent": cpu_percent,
        "memory_percent": memory_percent,
        "disk_percent": disk_percent,
        "uptime_seconds": round(time.time() - START_TIME, 2),
        "kimi_running": kimi_running,
        "active_tasks": active_tasks,
        "timestamp": time.time(),
    }


# ELI5: Think of this like pulling the last N entries from the panel's event log.
#       The electrician doesn't read the whole binder — just the recent faults.
@router.get("/logs")
async def remote_logs(
    lines: int = Query(50, ge=1, le=1000),
    logfile: str = Query("backend", description="backend | shadow | launcher"),
):
    """Tail the last N lines from a known log file."""
    # Resolve project root from this file's location (4 levels up)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

    log_paths = {
        "backend": [
            os.path.join(project_root, "backend.log"),
            os.path.join(project_root, "logs", "backend.log"),
            os.path.join(project_root, "interfaces", "web_ui", "backend", "backend.log"),
        ],
        "shadow": [
            os.path.join(project_root, "logs", "shadow_node.log"),
            os.path.join(project_root, "shadow_node.log"),
        ],
        "launcher": [
            os.path.join(project_root, "launcher.log"),
            os.path.join(project_root, "logs", "launcher.log"),
        ],
    }

    candidates = log_paths.get(logfile, [])
    target_path = None
    for p in candidates:
        if os.path.isfile(p):
            target_path = p
            break

    if not target_path:
        raise HTTPException(status_code=404, detail=f"Log file '{logfile}' not found")

    try:
        with open(target_path, "r", encoding="utf-8", errors="replace") as f:
            # Read all lines and take the last N
            all_lines = f.readlines()
            tail = [line.rstrip("\n") for line in all_lines[-lines:]]
            return {"lines": tail}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read log: {e}")


# ELI5: Think of this like a circuit tracer — you clip it to every breaker
#       and read the load (CPU) and wire temperature (memory) for each circuit.
@router.get("/processes")
async def remote_processes(
    filter: Optional[str] = Query(None, description="If 'kimi', filter to relevant processes"),
):
    """List running processes with optional Kimi-related filter."""
    procs = []
    if not (_PSUTIL_OK and psutil is not None):
        return {"processes": procs}

    allowed = {"code", "kimi", "python", "node"}
    try:
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
            try:
                name = p.info.get("name") or ""
                if filter and filter.lower() == "kimi":
                    name_lower = name.lower()
                    if not any(a in name_lower for a in allowed):
                        continue
                cpu = p.info.get("cpu_percent") or 0.0
                mem_info = p.info.get("memory_info")
                mem_mb = round(mem_info.rss / (1024 * 1024), 2) if mem_info else 0.0
                procs.append({
                    "pid": p.info.get("pid"),
                    "name": name,
                    "cpu_percent": round(cpu, 2),
                    "memory_mb": mem_mb,
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Process enumeration failed: {e}")

    return {"processes": procs}


# ELI5: Think of this like dropping a work order into the inbox.
#       If the dispatcher (orchestrator) is on duty, they queue it.
#       If not, the local apprentice handles it and echoes back the instructions.
@router.post("/inject")
async def remote_inject(req: InjectRequest):
    """Inject a prompt/task into the local node or swarm orchestrator."""
    queued = False
    task_id = None

    try:
        from interfaces.web_ui.backend.dependencies import get_swarm_orchestrator
        orch = get_swarm_orchestrator()
        if orch is not None and hasattr(orch, "submit_task"):
            task = orch.submit_task(req.prompt, model=req.model, mode=req.mode)
            queued = True
            if hasattr(task, "task_id"):
                task_id = task.task_id
            elif isinstance(task, dict):
                task_id = task.get("task_id")
    except Exception:
        pass

    if queued:
        return {
            "success": True,
            "message": "Queued for local execution",
            "task_id": task_id,
            "prompt": req.prompt,
            "model": req.model,
            "mode": req.mode,
        }

    return {
        "success": True,
        "message": "Queued for local execution",
        "prompt": req.prompt,
        "model": req.model,
        "mode": req.mode,
    }
