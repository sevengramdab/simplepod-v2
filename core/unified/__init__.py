#!/usr/bin/env python3
"""
core/unified/__init__.py
=======================
SimplePod Unified — Local closed-loop Developer Environment & CI/CD suite.

ELI5: This is the master directory for the building's new smart
      automation wing. Every module in this package is a specialized
      crew that works together to keep the building running without
      calling outside contractors.
"""

from __future__ import annotations

from .config import UnifiedConfig, VisionConfig, OSInterfaceConfig, SelfHealingConfig, SwarmConfig
from .vision_engine import VisionEngine, VisionResult, UIElement, ElementType
from .os_interface import OSInterface, OSActionResult, OSScreenInfo
from .self_healing import SelfHealingEngine, HealingSession, HealingIteration, CheckResult
from .worker_swarm import WorkerSwarm, WorkerMessage, MessageType, WorkerState, BaseWorker
from .pipeline import SimplePodUnifiedOrchestrator, PipelineState, GoalResult

__all__ = [
    "UnifiedConfig",
    "VisionConfig",
    "OSInterfaceConfig",
    "SelfHealingConfig",
    "SwarmConfig",
    "VisionEngine",
    "VisionResult",
    "UIElement",
    "ElementType",
    "OSInterface",
    "OSActionResult",
    "OSScreenInfo",
    "SelfHealingEngine",
    "HealingSession",
    "HealingIteration",
    "CheckResult",
    "WorkerSwarm",
    "WorkerMessage",
    "MessageType",
    "WorkerState",
    "BaseWorker",
    "SimplePodUnifiedOrchestrator",
    "PipelineState",
    "GoalResult",
]
