#!/usr/bin/env python3
"""
core/unified/config.py
======================
Configuration dataclasses for the SimplePod Unified pipeline.

ELI5: Think of this like the directory sticker inside the main electrical
      panel door. Every circuit breaker size, wire gauge, and room
      assignment is listed here before any electrician flips a switch.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class DeploymentMode(str, Enum):
    """
    ELI5: Like choosing between a single-family home, a duplex,
          or a full apartment building. Each needs different wiring.
    """

    SINGLE = "single"
    MULTI_GPU = "multi_gpu"
    CLUSTER = "cluster"


class WorkerRole(str, Enum):
    """
    ELI5: Every room in the building has a purpose.
          You don't put a water heater in the bedroom.
    """

    ORCHESTRATOR = "orchestrator"
    STATE_MANAGER = "state_manager"
    VISION_CAPTURE = "vision_capture"
    VISION_DETECT = "vision_detect"
    VISION_EXTRACT = "vision_extract"
    OS_MOUSE = "os_mouse"
    OS_KEYBOARD = "os_keyboard"
    HEAL_SYNTAX = "heal_syntax"
    HEAL_TYPECHECK = "heal_typecheck"
    HEAL_TEST = "heal_test"
    HEAL_FIX = "heal_fix"
    HEAL_VALIDATE = "heal_validate"
    FS_READ = "fs_read"
    FS_WRITE = "fs_write"
    FS_BACKUP = "fs_backup"
    LLM_INFERENCE_A = "llm_inference_a"
    LLM_INFERENCE_B = "llm_inference_b"
    ERROR_CATCHER = "error_catcher"
    TELEMETRY = "telemetry"
    HEALTH_MONITOR = "health_monitor"


@dataclass
class WorkerPlacementConfig:
    """
    ELI5: Like a panel schedule that says which breaker panel
          serves which floor. You need to know before you run conduit.
    """

    deployment_mode: DeploymentMode = DeploymentMode.SINGLE
    local_workers: List[int] = field(default_factory=lambda: [1, 2, 6, 7, 13, 14, 15, 18, 19, 20])
    gpu_workers: Dict[str, List[int]] = field(
        default_factory=lambda: {"vision": [3, 4, 5], "llm": [16, 17]}
    )
    node_affinity: Dict[str, List[str]] = field(
        default_factory=lambda: {
            "vision": ["poland-01", "poland-02"],
            "llm": ["shadow-pc", "poland-01", "poland-02"],
            "os_input": ["local-only"],
        }
    )
    gpu_assignment: Dict[str, List[str]] = field(
        default_factory=lambda: {
            "poland-01": ["cuda:0", "cuda:1"],
            "poland-02": ["cuda:0", "cuda:1"],
        }
    )


@dataclass
class VisionConfig:
    """
    ELI5: Like the spec sheet for the security camera system.
          Resolution, frame rate, and detection sensitivity.
    """

    template_match_threshold: float = 0.75
    contour_min_area: int = 100
    contour_max_area: int = 500_000
    use_onnx: bool = False
    onnx_model_path: Optional[str] = None
    use_ocr: bool = False
    ocr_languages: List[str] = field(default_factory=lambda: ["en"])
    screenshot_format: str = "PNG"
    screenshot_quality: int = 85


@dataclass
class OSInterfaceConfig:
    """
    ELI5: Like the settings on a smart home automation hub.
          How fast the shades close, how dim the lights go.
    """

    typing_interval: float = 0.01
    click_duration: float = 0.1
    drag_duration: float = 0.5
    scroll_clicks: int = 3
    movement_duration: float = 0.25
    screen_boundary_padding: int = 5
    headless_fallback: bool = True


@dataclass
class SelfHealingConfig:
    """
    ELI5: Like the settings on a smart circuit breaker.
          How many times it tries to reset before calling the electrician.
    """

    enabled: bool = True
    watch_paths: List[str] = field(default_factory=lambda: ["."])
    max_iterations: int = 5
    backup_before_fix: bool = True
    ark_backup_dir: str = "./ark_backups"
    sandbox_only: bool = True
    allowed_extensions: List[str] = field(default_factory=lambda: [".py"])
    mypy_enabled: bool = True
    ruff_enabled: bool = True
    pytest_enabled: bool = True
    llm_model: str = "llama3.2"
    llm_host: str = "http://127.0.0.1:11434"
    timeout_seconds: int = 120


@dataclass
class SwarmConfig:
    """
    ELI5: Like the master specification for a 20-gang electrical box.
          Every switch has a label and a purpose.
    """

    max_workers: int = 20
    task_timeout: float = 30.0
    heartbeat_interval: float = 5.0
    dead_letter_ttl: float = 300.0
    enable_auto_restart: bool = True
    enable_gpu_routing: bool = False


@dataclass
class UnifiedConfig:
    """
    ELI5: The complete electrical permit package.
          Every drawing, every spec, every load calculation in one binder.
    """

    project_dir: str = "."
    ark_backup_dir: str = r"E:\ark_backups"
    fallback_backup_dir: str = "./ark_backups"
    worker_placement: WorkerPlacementConfig = field(default_factory=WorkerPlacementConfig)
    vision: VisionConfig = field(default_factory=VisionConfig)
    os_interface: OSInterfaceConfig = field(default_factory=OSInterfaceConfig)
    self_healing: SelfHealingConfig = field(default_factory=SelfHealingConfig)
    swarm: SwarmConfig = field(default_factory=SwarmConfig)
    log_level: str = "INFO"
    trace_id: Optional[str] = None

    @property
    def active_backup_dir(self) -> Path:
        """
        ELI5: Check if the off-site panel exists. If not, use the sub-panel
              in the basement. Either way, power stays on.
        """
        primary = Path(self.ark_backup_dir)
        if primary.exists() and primary.is_dir():
            return primary
        fallback = Path(self.fallback_backup_dir)
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback
