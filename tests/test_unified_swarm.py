#!/usr/bin/env python3
"""
test_unified_swarm.py
=====================
Unit tests for the 20-node Worker Swarm.

ELI5: Before the building opens, we test every security guard's
      radio, make sure they can receive orders, and verify the
      dispatch center can route messages between them.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict

import pytest

from core.unified.worker_swarm import (
    WorkerSwarm,
    WorkerMessage,
    MessageType,
    WorkerState,
    BaseWorker,
    WORKER_ROLE_MAP,
)
from core.unified.config import SwarmConfig, WorkerRole


class TestWorkerMessage:
    def test_message_creation(self) -> None:
        """ELI5: Can we write a radio call and read it back?"""
        msg = WorkerMessage(
            sender_id=1,
            recipient_id=2,
            msg_type=MessageType.TASK_REQUEST,
            payload={"task": "test"},
        )
        assert msg.sender_id == 1
        assert msg.recipient_id == 2
        assert msg.msg_type == MessageType.TASK_REQUEST
        assert msg.payload["task"] == "test"

    def test_message_to_dict(self) -> None:
        """ELI5: Can the radio call be serialized for the logbook?"""
        msg = WorkerMessage(sender_id=3, msg_type=MessageType.HEARTBEAT)
        d = msg.to_dict()
        assert d["sender_id"] == 3
        assert d["msg_type"] == "heartbeat"


class TestWorkerState:
    def test_state_defaults(self) -> None:
        """ELI5: Does every new guard start with a clean slate?"""
        state = WorkerState(worker_id=5, role=WorkerRole.VISION_DETECT)
        assert state.status == "idle"
        assert state.task_count == 0
        assert state.error_count == 0

    def test_state_to_dict(self) -> None:
        """ELI5: Can we print the guard's status for the duty roster?"""
        state = WorkerState(worker_id=7, role=WorkerRole.OS_MOUSE)
        d = state.to_dict()
        assert d["worker_id"] == 7
        assert d["role"] == "os_mouse"
        assert d["status"] == "idle"


class TestBaseWorker:
    @pytest.mark.asyncio
    async def test_worker_lifecycle(self) -> None:
        """ELI5: Can we hire a guard, start their shift, and fire them?"""
        worker = BaseWorker(worker_id=99, role=WorkerRole.TELEMETRY, config=SwarmConfig())
        await worker.start()
        assert worker._task is not None
        await worker.stop()
        assert worker._shutdown is True

    @pytest.mark.asyncio
    async def test_worker_message_passing(self) -> None:
        """ELI5: Can we slip a note into the guard's mailbox?"""
        worker = BaseWorker(worker_id=98, role=WorkerRole.TELEMETRY, config=SwarmConfig())
        await worker.start()
        msg = WorkerMessage(sender_id=1, msg_type=MessageType.HEARTBEAT)
        await worker.send_message(msg)
        # Wait for the worker loop to process the message
        await asyncio.sleep(0.15)
        # The heartbeat message should have been consumed (queue empty or processed)
        assert worker.inbox.qsize() == 0
        await worker.stop()


class TestWorkerRoleMap:
    def test_all_workers_mapped(self) -> None:
        """ELI5: Do all 20 guard positions have job descriptions?"""
        for i in range(1, 21):
            assert i in WORKER_ROLE_MAP, f"Worker {i} not in role map"


class TestWorkerSwarm:
    @pytest.mark.asyncio
    async def test_swarm_start_stop(self) -> None:
        """ELI5: Can we open the building and close it without crashes?"""
        swarm = WorkerSwarm(config=SwarmConfig())
        await swarm.start()
        assert swarm._running is True
        assert len(swarm.workers) == 20
        await swarm.stop()
        assert swarm._running is False

    @pytest.mark.asyncio
    async def test_swarm_status(self) -> None:
        """ELI5: Can we read the full duty roster?"""
        swarm = WorkerSwarm(config=SwarmConfig())
        await swarm.start()
        status = swarm.get_status()
        assert status["running"] is True
        assert status["total_workers"] == 20
        assert len(status["workers"]) == 20
        await swarm.stop()

    @pytest.mark.asyncio
    async def test_submit_task(self) -> None:
        """ELI5: Can we submit a work order to the supervisor?"""
        swarm = WorkerSwarm(config=SwarmConfig())
        await swarm.start()
        task_id = await swarm.submit_task("generic", {"test": True})
        assert task_id.startswith("task_")
        await swarm.stop()

    @pytest.mark.asyncio
    async def test_state_manager_registered(self) -> None:
        """ELI5: Is the dispatch center connected to all guards?"""
        swarm = WorkerSwarm(config=SwarmConfig())
        await swarm.start()
        assert swarm._state_manager is not None
        assert len(swarm._state_manager.workers) == 20
        await swarm.stop()
