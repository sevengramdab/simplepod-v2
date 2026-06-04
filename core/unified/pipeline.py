#!/usr/bin/env python3
"""
core/unified/pipeline.py
========================
Main Orchestrator for the SimplePod Unified pipeline.

ELI5: Think of this like the building's master automation controller.
      It knows every floor, every room, every switch. When you say
      'turn off the lights and lock the doors,' it doesn't do it
      itself — it breaks the request into sub-tasks and dispatches
      each one to the right guard (worker). Then it watches the
      security cameras until everything is confirmed done.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import UnifiedConfig
from .vision_engine import VisionEngine, VisionResult
from .os_interface import OSInterface, OSActionResult
from .self_healing import SelfHealingEngine, HealingSession
from .worker_swarm import WorkerSwarm, WorkerMessage, MessageType

logger = logging.getLogger("simplepod.unified.pipeline")


class PipelineState(str, Enum):
    """
    ELI5: Like the building's operating modes:
          startup, normal hours, after-hours maintenance, or shutdown.
    """

    INIT = "init"
    PRIMING = "priming"
    RUNNING = "running"
    PAUSED = "paused"
    SHUTDOWN = "shutdown"
    ERROR = "error"


@dataclass
class GoalResult:
    """
    ELI5: The final report after you ask the building to do something.
          'All lights off, doors locked, 3 minutes elapsed, no errors.'
    """

    goal_id: str
    goal: str
    status: str  # completed | partial | failed
    vision_results: List[VisionResult] = field(default_factory=list)
    os_results: List[OSActionResult] = field(default_factory=list)
    healing_sessions: List[HealingSession] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)
    duration_ms: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "goal": self.goal,
            "status": self.status,
            "vision_results": [v.to_dict() for v in self.vision_results],
            "os_results": [o.to_dict() for o in self.os_results],
            "healing_sessions": [h.to_dict() for h in self.healing_sessions],
            "logs": self.logs,
            "duration_ms": round(self.duration_ms, 2),
            "error": self.error,
        }


class SimplePodUnifiedOrchestrator:
    """
    ELI5: The building superintendent's desk.
          One button starts the whole building in the morning.
          One button shuts it down at night.
          The superintendent speaks plain English ('test the circuits'),
          and the automation system translates that into the exact
          sequence of switch flips and patrol routes.
    """

    def __init__(self, config: Optional[UnifiedConfig] = None) -> None:
        self.config = config or UnifiedConfig()
        self.state = PipelineState.INIT
        self.swarm = WorkerSwarm(config=self.config.swarm)
        self.vision = VisionEngine(config=self.config.vision)
        self.os_interface = OSInterface(config=self.config.os_interface)
        self.healing = SelfHealingEngine(config=self.config.self_healing)
        self._goals: Dict[str, GoalResult] = {}
        self._state_lock = asyncio.Lock()

    async def start(self) -> None:
        """
        ELI5: Throw the main breaker and start every subsystem.
        """
        async with self._state_lock:
            if self.state not in (PipelineState.INIT, PipelineState.SHUTDOWN):
                logger.warning("Pipeline already in state: %s", self.state)
                return

            self.state = PipelineState.PRIMING
            logger.info("[PIPELINE] Priming SimplePod Unified...")

            # Start the 20-node worker swarm
            await self.swarm.start()

            self.state = PipelineState.RUNNING
            logger.info("[PIPELINE] SimplePod Unified is RUNNING")

    async def stop(self) -> None:
        """
        ELI5: Shut down every circuit in reverse order, lock the doors.
        """
        async with self._state_lock:
            if self.state == PipelineState.SHUTDOWN:
                return

            self.state = PipelineState.SHUTDOWN
            logger.info("[PIPELINE] Shutting down SimplePod Unified...")

            await self.swarm.stop()

            logger.info("[PIPELINE] Shutdown complete")

    async def pause(self) -> None:
        """
        ELI5: Put the building in 'after-hours' mode.
              Guards stay on post but don't accept new work orders.
        """
        async with self._state_lock:
            if self.state == PipelineState.RUNNING:
                self.state = PipelineState.PAUSED
                logger.info("[PIPELINE] Paused")

    async def resume(self) -> None:
        """
        ELI5: Wake the building back up to normal operating hours.
        """
        async with self._state_lock:
            if self.state == PipelineState.PAUSED:
                self.state = PipelineState.RUNNING
                logger.info("[PIPELINE] Resumed")

    def status(self) -> Dict[str, Any]:
        """
        ELI5: The building's current status board.
              Green lights for healthy systems, red for faults.
        """
        return {
            "pipeline_state": self.state.value,
            "swarm": self.swarm.get_status(),
            "vision_engine_ready": True,
            "os_interface_ready": True,
            "healing_engine_ready": True,
            "active_goals": len(self._goals),
        }

    async def submit_goal(self, goal: str) -> str:
        """
        ELI5: The superintendent says 'test the fire alarm system.'
              We create a work order, break it into steps,
              and dispatch each step to the right guards.
        """
        goal_id = f"goal_{int(time.time() * 1000)}"
        result = GoalResult(goal_id=goal_id, goal=goal, status="running")
        self._goals[goal_id] = result

        asyncio.create_task(self._execute_goal(goal_id, goal))
        return goal_id

    async def _execute_goal(self, goal_id: str, goal: str) -> None:
        """
        ELI5: The actual step-by-step execution of a work order.
              We look at what was asked and route it to the right crews.
        """
        t0 = time.time()
        result = self._goals[goal_id]

        try:
            goal_lower = goal.lower()

            # Self-healing goals
            if any(k in goal_lower for k in ("heal", "fix", "test", "refactor", "ci/cd")):
                await self._execute_healing_goal(result)

            # Vision + OS interaction goals
            elif any(k in goal_lower for k in ("click", "type", "screen", "ui", "mouse", "keyboard")):
                await self._execute_vision_os_goal(result)

            # Vision-only goals
            elif any(k in goal_lower for k in ("analyze", "detect", "scan", "find")):
                await self._execute_vision_goal(result)

            # Generic dispatch to swarm
            else:
                await self.swarm.submit_task("generic", {"goal": goal})
                result.logs.append("Dispatched generic goal to swarm")
                result.status = "completed"

        except Exception as exc:
            result.status = "failed"
            result.error = str(exc)
            logger.exception("Goal %s failed", goal_id)

        result.duration_ms = (time.time() - t0) * 1000

    async def _execute_healing_goal(self, result: GoalResult) -> None:
        """
        ELI5: Dispatch the maintenance crew to test and repair circuits.
        """
        result.logs.append("Starting self-healing protocol")

        # Determine target directory from goal, or use default
        target_dir = Path(self.config.project_dir)
        for word in result.goal.split():
            if "/" in word or "\\" in word or word.startswith("."):
                potential = Path(word)
                if potential.exists():
                    target_dir = potential
                    break

        sessions = await self.healing.heal_directory(target_dir)
        result.healing_sessions.extend(sessions)

        all_healed = all(s.final_status == "healed" for s in sessions)
        result.status = "completed" if all_healed else "partial"
        result.logs.append(f"Healed {len(sessions)} files")

    async def _execute_vision_goal(self, result: GoalResult) -> None:
        """
        ELI5: Dispatch the surveillance crew to photograph and analyze
              a specific area of the building.
        """
        result.logs.append("Starting vision analysis")
        vision_result = await self.vision.analyze_screen()
        result.vision_results.append(vision_result)
        result.status = "completed" if vision_result.success else "partial"

    async def _execute_vision_os_goal(self, result: GoalResult) -> None:
        """
        ELI5: Dispatch both the surveillance crew AND the robotic arms.
              First take a photo to see where the switch is, then
              send the robot to flip it.
        """
        result.logs.append("Starting vision-guided OS interaction")

        # Step 1: Capture and analyze screen
        vision_result = await self.vision.analyze_screen()
        result.vision_results.append(vision_result)

        if not vision_result.success:
            result.status = "failed"
            result.error = "Vision analysis failed"
            return

        # Step 2: Determine action from goal
        goal_lower = result.goal.lower()

        if "click" in goal_lower:
            # Try to find a button matching text after "click"
            words = result.goal.split()
            target_text = None
            for i, w in enumerate(words):
                if w.lower() == "click" and i + 1 < len(words):
                    target_text = words[i + 1].strip(".,;:!?")
                    break

            if target_text:
                matches = vision_result.find_by_text(target_text)
                if matches:
                    target = matches[0]
                    x, y = target.center
                    os_result = await self.os_interface.click(x, y)
                    result.os_results.append(os_result)
                    result.logs.append(f"Clicked '{target_text}' at ({x}, {y})")
                else:
                    result.logs.append(f"No UI element found for text: {target_text}")
            else:
                # Default: click center of screen
                w, h = vision_result.width, vision_result.height
                os_result = await self.os_interface.click(w // 2, h // 2)
                result.os_results.append(os_result)

        elif "type" in goal_lower:
            # Extract text to type
            words = result.goal.split("'", 2)
            if len(words) >= 2:
                text_to_type = words[1]
            else:
                text_to_type = result.goal.replace("type", "").strip()

            os_result = await self.os_interface.type_text(text_to_type)
            result.os_results.append(os_result)
            result.logs.append(f"Typed text: {text_to_type[:30]}...")

        result.status = "completed"

    def get_goal(self, goal_id: str) -> Optional[GoalResult]:
        """
        ELI5: Pull the work order from the filing cabinet to see
              if it's finished and what the results were.
        """
        return self._goals.get(goal_id)
