#!/usr/bin/env python3
"""
test_unified_pipeline.py
========================
Integration tests for the SimplePod Unified Orchestrator.

ELI5: Instead of testing one light switch at a time, we flip the
      main breaker ON, dispatch a work order to the full security
      team, and verify every guard checks in and the job gets done.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from core.unified.pipeline import (
    SimplePodUnifiedOrchestrator,
    PipelineState,
    GoalResult,
)
from core.unified.config import UnifiedConfig


class TestPipelineState:
    def test_state_values(self) -> None:
        """ELI5: Every building mode should have a clear label."""
        assert PipelineState.INIT == "init"
        assert PipelineState.RUNNING == "running"
        assert PipelineState.SHUTDOWN == "shutdown"


class TestSimplePodUnifiedOrchestrator:
    @pytest.mark.asyncio
    async def test_orchestrator_creation(self) -> None:
        """ELI5: Can we build the superintendent's desk?"""
        orch = SimplePodUnifiedOrchestrator(config=UnifiedConfig())
        assert orch.state == PipelineState.INIT
        assert orch.swarm is not None
        assert orch.vision is not None
        assert orch.os_interface is not None
        assert orch.healing is not None

    @pytest.mark.asyncio
    async def test_start_stop_lifecycle(self) -> None:
        """ELI5: Can we open and close the building without crashes?"""
        orch = SimplePodUnifiedOrchestrator(config=UnifiedConfig())
        await orch.start()
        assert orch.state == PipelineState.RUNNING
        status = orch.status()
        assert status["pipeline_state"] == "running"
        assert status["swarm"]["running"] is True
        await orch.stop()
        assert orch.state == PipelineState.SHUTDOWN

    @pytest.mark.asyncio
    async def test_pause_resume(self) -> None:
        """ELI5: Can we put the building in after-hours mode and wake it back up?"""
        orch = SimplePodUnifiedOrchestrator(config=UnifiedConfig())
        await orch.start()
        await orch.pause()
        assert orch.state == PipelineState.PAUSED
        await orch.resume()
        assert orch.state == PipelineState.RUNNING
        await orch.stop()

    @pytest.mark.asyncio
    async def test_submit_goal(self) -> None:
        """ELI5: Can we submit a work order and get a tracking number?"""
        orch = SimplePodUnifiedOrchestrator(config=UnifiedConfig())
        await orch.start()
        goal_id = await orch.submit_goal("Test goal")
        assert goal_id.startswith("goal_")
        result = orch.get_goal(goal_id)
        assert result is not None
        assert result.goal == "Test goal"
        await orch.stop()

    @pytest.mark.asyncio
    async def test_status_format(self) -> None:
        """ELI5: Does the building's status board show all required lights?"""
        orch = SimplePodUnifiedOrchestrator(config=UnifiedConfig())
        await orch.start()
        status = orch.status()
        required_keys = [
            "pipeline_state",
            "swarm",
            "vision_engine_ready",
            "os_interface_ready",
            "healing_engine_ready",
            "active_goals",
        ]
        for key in required_keys:
            assert key in status, f"Missing key: {key}"
        await orch.stop()

    @pytest.mark.asyncio
    async def test_idempotent_stop(self) -> None:
        """ELI5: Pressing the shutdown button twice shouldn't explode the building."""
        orch = SimplePodUnifiedOrchestrator(config=UnifiedConfig())
        await orch.start()
        await orch.stop()
        await orch.stop()  # Should not raise
        assert orch.state == PipelineState.SHUTDOWN
