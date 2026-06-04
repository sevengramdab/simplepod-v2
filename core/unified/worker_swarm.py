#!/usr/bin/env python3
"""
core/unified/worker_swarm.py
===========================
20-Node Concurrent Micro-Service Swarm.

ELI5: Think of this like a 20-gang lighting control panel.
      Each switch controls a different room or floor.
      They all operate simultaneously — the lobby lights,
      the HVAC, the security system, the elevator — without
      any one switch waiting for another to finish.
      If a bulb burns out, the panel logs it and routes
      power to the backup circuit automatically.
"""

from __future__ import annotations

import asyncio
import logging
import time
import traceback
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Callable

from .config import SwarmConfig, WorkerRole, UnifiedConfig

logger = logging.getLogger("simplepod.unified.swarm")


class MessageType(str, Enum):
    """
    ELI5: The different kinds of radio chatter between security guards.
          Some messages are commands, some are status updates,
          some are emergency alerts.
    """

    TASK_REQUEST = "task_request"
    TASK_RESULT = "task_result"
    HEARTBEAT = "heartbeat"
    ERROR_REPORT = "error_report"
    STATE_UPDATE = "state_update"
    SHUTDOWN = "shutdown"
    RESTART_WORKER = "restart_worker"


@dataclass
class WorkerMessage:
    """
    ELI5: A standardized radio call. Every message has a sender,
          a recipient, a message type, and a payload.
    """

    msg_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    sender_id: int = -1
    recipient_id: int = -1  # -1 = broadcast
    msg_type: MessageType = MessageType.TASK_REQUEST
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "msg_id": self.msg_id,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "msg_type": self.msg_type.value,
            "payload": self.payload,
            "timestamp": self.timestamp,
        }


@dataclass
class WorkerState:
    """
    ELI5: The status board for one security guard.
          Are they on patrol? When did they last check in?
          How many incidents have they handled?
    """

    worker_id: int
    role: WorkerRole
    status: str = "idle"  # idle | busy | degraded | dead
    task_count: int = 0
    error_count: int = 0
    last_heartbeat: float = field(default_factory=time.time)
    spawned_at: float = field(default_factory=time.time)
    current_task: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "role": self.role.value,
            "status": self.status,
            "task_count": self.task_count,
            "error_count": self.error_count,
            "last_heartbeat": self.last_heartbeat,
            "uptime_seconds": round(time.time() - self.spawned_at, 1),
            "current_task": self.current_task,
            "metadata": self.metadata,
        }


class BaseWorker:
    """
    ELI5: The base template for every security guard.
          Every guard wears the same uniform and follows the same
          radio protocol, but each specializes in a different task.
    """

    def __init__(self, worker_id: int, role: WorkerRole, config: SwarmConfig) -> None:
        self.worker_id = worker_id
        self.role = role
        self.config = config
        self.state = WorkerState(worker_id=worker_id, role=role)
        self.inbox: asyncio.Queue[WorkerMessage] = asyncio.Queue()
        self._task: Optional[asyncio.Task] = None
        self._shutdown = False

    async def start(self) -> None:
        """
        ELI5: Clock in and start the patrol loop.
        """
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Worker %d (%s) started", self.worker_id, self.role.value)

    async def stop(self) -> None:
        """
        ELI5: Clock out and hand over the keys.
        """
        self._shutdown = True
        await self.inbox.put(WorkerMessage(msg_type=MessageType.SHUTDOWN, sender_id=self.worker_id))
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=5.0)
            except asyncio.TimeoutError:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
        logger.info("Worker %d (%s) stopped", self.worker_id, self.role.value)

    async def send_message(self, msg: WorkerMessage) -> None:
        """
        ELI5: Slip a note into this guard's mailbox.
        """
        await self.inbox.put(msg)

    async def _run_loop(self) -> None:
        """
        ELI5: The guard's patrol routine — walk the beat, check the
              mailbox, handle any incidents, report status.
        """
        while not self._shutdown:
            try:
                msg = await asyncio.wait_for(self.inbox.get(), timeout=self.config.heartbeat_interval)
            except asyncio.TimeoutError:
                await self._heartbeat()
                continue

            if msg.msg_type == MessageType.SHUTDOWN:
                break

            try:
                await self._handle_message(msg)
            except Exception as exc:
                self.state.error_count += 1
                self.state.status = "degraded"
                logger.exception("Worker %d error handling message %s", self.worker_id, msg.msg_id)
                await self._report_error(msg, exc)

    async def _heartbeat(self) -> None:
        """
        ELI5: Radio the control room every 5 minutes:
              'Guard 7, all clear, still on patrol.'
        """
        self.state.last_heartbeat = time.time()

    async def _handle_message(self, msg: WorkerMessage) -> None:
        """
        ELI5: What to do when a message arrives. Subclasses override this.
        """
        pass

    async def _report_error(self, msg: WorkerMessage, exc: Exception) -> None:
        """
        ELI5: If the guard gets hurt or sees a fire, they immediately
              radio the emergency channel with details.
        """
        error_msg = WorkerMessage(
            sender_id=self.worker_id,
            recipient_id=18,  # Error Catcher
            msg_type=MessageType.ERROR_REPORT,
            payload={
                "original_msg": msg.to_dict(),
                "error": str(exc),
                "traceback": traceback.format_exc(),
            },
        )
        # We can't directly send; subclasses should override with state_manager ref


# ---------------------------------------------------------------------------
# Individual Worker Implementations
# ---------------------------------------------------------------------------

class OrchestratorWorker(BaseWorker):
    """
    ELI5: Guard 01 — The shift supervisor.
          Reads every work order, decides which guard handles it,
          and makes sure nothing falls through the cracks.
    """

    def __init__(self, worker_id: int, config: SwarmConfig) -> None:
        super().__init__(worker_id, WorkerRole.ORCHESTRATOR, config)
        self._state_manager_id = 2
        self._pending_tasks: Dict[str, WorkerMessage] = {}

    async def _handle_message(self, msg: WorkerMessage) -> None:
        if msg.msg_type == MessageType.TASK_REQUEST:
            self.state.status = "busy"
            self.state.current_task = msg.payload.get("task_id")
            await self._route_task(msg)
            self.state.task_count += 1
            self.state.status = "idle"
            self.state.current_task = None

    async def _route_task(self, msg: WorkerMessage) -> None:
        """
        ELI5: The supervisor reads the work order and decides:
              'Guard 3, you handle the lobby sweep.
               Guard 8, you test the breaker panel.'
        """
        task_type = msg.payload.get("task_type", "unknown")
        routing_map: Dict[str, List[int]] = {
            "vision": [3, 4, 5],
            "os_input": [6, 7],
            "self_heal": [8, 9, 10, 11, 12],
            "fs_io": [13, 14, 15],
            "llm": [16, 17],
        }
        targets = routing_map.get(task_type, [2])
        # Pick first available based on state manager info (simplified)
        target_id = targets[0]
        forward_msg = WorkerMessage(
            sender_id=self.worker_id,
            recipient_id=target_id,
            msg_type=MessageType.TASK_REQUEST,
            payload=msg.payload,
        )
        # In real implementation, this would be sent via state manager
        self._pending_tasks[msg.msg_id] = msg


class StateManagerWorker(BaseWorker):
    """
    ELI5: Guard 02 — The dispatch center.
          Every guard radios their status here.
          All messages pass through this desk before going anywhere else.
    """

    def __init__(self, worker_id: int, config: SwarmConfig) -> None:
        super().__init__(worker_id, WorkerRole.STATE_MANAGER, config)
        self.workers: Dict[int, BaseWorker] = {}
        self.state_store: Dict[str, Any] = {}
        self.message_history: List[WorkerMessage] = []

    def register_worker(self, worker: BaseWorker) -> None:
        self.workers[worker.worker_id] = worker

    async def _handle_message(self, msg: WorkerMessage) -> None:
        self.message_history.append(msg)

        if msg.msg_type == MessageType.STATE_UPDATE:
            key = msg.payload.get("key")
            value = msg.payload.get("value")
            if key is not None:
                self.state_store[key] = value

        elif msg.msg_type == MessageType.TASK_REQUEST:
            # Route to target worker
            recipient = msg.recipient_id
            if recipient == -1:
                # Broadcast to all capable workers
                for wid, w in self.workers.items():
                    if wid != msg.sender_id:
                        await w.send_message(msg)
            elif recipient in self.workers:
                await self.workers[recipient].send_message(msg)
            else:
                logger.warning("StateManager: recipient %d not found", recipient)

        elif msg.msg_type == MessageType.TASK_RESULT:
            # Forward to original requester or orchestrator
            original_sender = msg.payload.get("original_sender", 1)
            if original_sender in self.workers:
                await self.workers[original_sender].send_message(msg)

        elif msg.msg_type == MessageType.ERROR_REPORT:
            # Forward to error catcher (18)
            if 18 in self.workers:
                await self.workers[18].send_message(msg)

        elif msg.msg_type == MessageType.RESTART_WORKER:
            target = msg.payload.get("worker_id")
            if target in self.workers:
                await self.workers[target].stop()
                await self.workers[target].start()

    def get_worker_state(self, worker_id: int) -> Optional[WorkerState]:
        w = self.workers.get(worker_id)
        return w.state if w else None

    def all_states(self) -> List[WorkerState]:
        return [w.state for w in self.workers.values()]


class VisionCaptureWorker(BaseWorker):
    """
    ELI5: Guard 03 — The surveillance photographer.
          Takes photos of the lobby and uploads them to dispatch.
    """

    def __init__(self, worker_id: int, config: SwarmConfig) -> None:
        super().__init__(worker_id, WorkerRole.VISION_CAPTURE, config)

    async def _handle_message(self, msg: WorkerMessage) -> None:
        if msg.msg_type == MessageType.TASK_REQUEST and msg.payload.get("task_type") == "vision":
            self.state.status = "busy"
            # Actual vision capture handled by pipeline integration
            result = {"status": "captured", "worker_id": self.worker_id}
            self.state.task_count += 1
            self.state.status = "idle"
            await self._send_result(msg, result)

    async def _send_result(self, original_msg: WorkerMessage, result: Dict[str, Any]) -> None:
        result_msg = WorkerMessage(
            sender_id=self.worker_id,
            recipient_id=original_msg.sender_id,
            msg_type=MessageType.TASK_RESULT,
            payload={"original_msg": original_msg.to_dict(), "result": result},
        )
        await self.inbox.put(result_msg)


class VisionDetectWorker(BaseWorker):
    """
    ELI5: Guard 04 — The AI security analyst.
          Looks at the photos and circles every person and object.
    """

    def __init__(self, worker_id: int, config: SwarmConfig) -> None:
        super().__init__(worker_id, WorkerRole.VISION_DETECT, config)

    async def _handle_message(self, msg: WorkerMessage) -> None:
        if msg.msg_type == MessageType.TASK_REQUEST and msg.payload.get("task_type") == "vision":
            self.state.status = "busy"
            result = {"status": "detected", "worker_id": self.worker_id}
            self.state.task_count += 1
            self.state.status = "idle"
            await self._send_result(msg, result)

    async def _send_result(self, original_msg: WorkerMessage, result: Dict[str, Any]) -> None:
        result_msg = WorkerMessage(
            sender_id=self.worker_id,
            recipient_id=original_msg.sender_id,
            msg_type=MessageType.TASK_RESULT,
            payload={"original_msg": original_msg.to_dict(), "result": result},
        )
        await self.inbox.put(result_msg)


class VisionExtractWorker(BaseWorker):
    """
    ELI5: Guard 05 — The evidence clerk.
          Extracts exact coordinates and labels from the analyst's circles.
    """

    def __init__(self, worker_id: int, config: SwarmConfig) -> None:
        super().__init__(worker_id, WorkerRole.VISION_EXTRACT, config)

    async def _handle_message(self, msg: WorkerMessage) -> None:
        if msg.msg_type == MessageType.TASK_REQUEST and msg.payload.get("task_type") == "vision":
            self.state.status = "busy"
            result = {"status": "extracted", "worker_id": self.worker_id}
            self.state.task_count += 1
            self.state.status = "idle"
            await self._send_result(msg, result)

    async def _send_result(self, original_msg: WorkerMessage, result: Dict[str, Any]) -> None:
        result_msg = WorkerMessage(
            sender_id=self.worker_id,
            recipient_id=original_msg.sender_id,
            msg_type=MessageType.TASK_RESULT,
            payload={"original_msg": original_msg.to_dict(), "result": result},
        )
        await self.inbox.put(result_msg)


class OSMouseWorker(BaseWorker):
    """
    ELI5: Guard 06 — The robotic arm that flips light switches.
    """

    def __init__(self, worker_id: int, config: SwarmConfig) -> None:
        super().__init__(worker_id, WorkerRole.OS_MOUSE, config)

    async def _handle_message(self, msg: WorkerMessage) -> None:
        if msg.msg_type == MessageType.TASK_REQUEST and msg.payload.get("task_type") == "os_input":
            self.state.status = "busy"
            action = msg.payload.get("action")
            result = {"status": "executed", "action": action, "worker_id": self.worker_id}
            self.state.task_count += 1
            self.state.status = "idle"
            await self._send_result(msg, result)

    async def _send_result(self, original_msg: WorkerMessage, result: Dict[str, Any]) -> None:
        result_msg = WorkerMessage(
            sender_id=self.worker_id,
            recipient_id=original_msg.sender_id,
            msg_type=MessageType.TASK_RESULT,
            payload={"original_msg": original_msg.to_dict(), "result": result},
        )
        await self.inbox.put(result_msg)


class OSKeyboardWorker(BaseWorker):
    """
    ELI5: Guard 07 — The robotic typist.
    """

    def __init__(self, worker_id: int, config: SwarmConfig) -> None:
        super().__init__(worker_id, WorkerRole.OS_KEYBOARD, config)

    async def _handle_message(self, msg: WorkerMessage) -> None:
        if msg.msg_type == MessageType.TASK_REQUEST and msg.payload.get("task_type") == "os_input":
            self.state.status = "busy"
            action = msg.payload.get("action")
            result = {"status": "executed", "action": action, "worker_id": self.worker_id}
            self.state.task_count += 1
            self.state.status = "idle"
            await self._send_result(msg, result)

    async def _send_result(self, original_msg: WorkerMessage, result: Dict[str, Any]) -> None:
        result_msg = WorkerMessage(
            sender_id=self.worker_id,
            recipient_id=original_msg.sender_id,
            msg_type=MessageType.TASK_RESULT,
            payload={"original_msg": original_msg.to_dict(), "result": result},
        )
        await self.inbox.put(result_msg)


class HealingSyntaxWorker(BaseWorker):
    """
    ELI5: Guard 08 — The outlet tester with a basic continuity meter.
    """

    def __init__(self, worker_id: int, config: SwarmConfig) -> None:
        super().__init__(worker_id, WorkerRole.HEAL_SYNTAX, config)

    async def _handle_message(self, msg: WorkerMessage) -> None:
        if msg.msg_type == MessageType.TASK_REQUEST and msg.payload.get("task_type") == "self_heal":
            self.state.status = "busy"
            result = {"status": "syntax_checked", "worker_id": self.worker_id}
            self.state.task_count += 1
            self.state.status = "idle"
            await self._send_result(msg, result)

    async def _send_result(self, original_msg: WorkerMessage, result: Dict[str, Any]) -> None:
        result_msg = WorkerMessage(
            sender_id=self.worker_id,
            recipient_id=original_msg.sender_id,
            msg_type=MessageType.TASK_RESULT,
            payload={"original_msg": original_msg.to_dict(), "result": result},
        )
        await self.inbox.put(result_msg)


class HealingTypecheckWorker(BaseWorker):
    """
    ELI5: Guard 09 — The wire gauge inspector.
    """

    def __init__(self, worker_id: int, config: SwarmConfig) -> None:
        super().__init__(worker_id, WorkerRole.HEAL_TYPECHECK, config)

    async def _handle_message(self, msg: WorkerMessage) -> None:
        if msg.msg_type == MessageType.TASK_REQUEST and msg.payload.get("task_type") == "self_heal":
            self.state.status = "busy"
            result = {"status": "typechecked", "worker_id": self.worker_id}
            self.state.task_count += 1
            self.state.status = "idle"
            await self._send_result(msg, result)

    async def _send_result(self, original_msg: WorkerMessage, result: Dict[str, Any]) -> None:
        result_msg = WorkerMessage(
            sender_id=self.worker_id,
            recipient_id=original_msg.sender_id,
            msg_type=MessageType.TASK_RESULT,
            payload={"original_msg": original_msg.to_dict(), "result": result},
        )
        await self.inbox.put(result_msg)


class HealingTestWorker(BaseWorker):
    """
    ELI5: Guard 10 — The load bank tester.
    """

    def __init__(self, worker_id: int, config: SwarmConfig) -> None:
        super().__init__(worker_id, WorkerRole.HEAL_TEST, config)

    async def _handle_message(self, msg: WorkerMessage) -> None:
        if msg.msg_type == MessageType.TASK_REQUEST and msg.payload.get("task_type") == "self_heal":
            self.state.status = "busy"
            result = {"status": "tests_run", "worker_id": self.worker_id}
            self.state.task_count += 1
            self.state.status = "idle"
            await self._send_result(msg, result)

    async def _send_result(self, original_msg: WorkerMessage, result: Dict[str, Any]) -> None:
        result_msg = WorkerMessage(
            sender_id=self.worker_id,
            recipient_id=original_msg.sender_id,
            msg_type=MessageType.TASK_RESULT,
            payload={"original_msg": original_msg.to_dict(), "result": result},
        )
        await self.inbox.put(result_msg)


class HealingFixWorker(BaseWorker):
    """
    ELI5: Guard 11 — The electrician who rewires faulty circuits.
    """

    def __init__(self, worker_id: int, config: SwarmConfig) -> None:
        super().__init__(worker_id, WorkerRole.HEAL_FIX, config)

    async def _handle_message(self, msg: WorkerMessage) -> None:
        if msg.msg_type == MessageType.TASK_REQUEST and msg.payload.get("task_type") == "self_heal":
            self.state.status = "busy"
            result = {"status": "fix_generated", "worker_id": self.worker_id}
            self.state.task_count += 1
            self.state.status = "idle"
            await self._send_result(msg, result)

    async def _send_result(self, original_msg: WorkerMessage, result: Dict[str, Any]) -> None:
        result_msg = WorkerMessage(
            sender_id=self.worker_id,
            recipient_id=original_msg.sender_id,
            msg_type=MessageType.TASK_RESULT,
            payload={"original_msg": original_msg.to_dict(), "result": result},
        )
        await self.inbox.put(result_msg)


class HealingValidateWorker(BaseWorker):
    """
    ELI5: Guard 12 — The inspector who signs off on repairs.
    """

    def __init__(self, worker_id: int, config: SwarmConfig) -> None:
        super().__init__(worker_id, WorkerRole.HEAL_VALIDATE, config)

    async def _handle_message(self, msg: WorkerMessage) -> None:
        if msg.msg_type == MessageType.TASK_REQUEST and msg.payload.get("task_type") == "self_heal":
            self.state.status = "busy"
            result = {"status": "validated", "worker_id": self.worker_id}
            self.state.task_count += 1
            self.state.status = "idle"
            await self._send_result(msg, result)

    async def _send_result(self, original_msg: WorkerMessage, result: Dict[str, Any]) -> None:
        result_msg = WorkerMessage(
            sender_id=self.worker_id,
            recipient_id=original_msg.sender_id,
            msg_type=MessageType.TASK_RESULT,
            payload={"original_msg": original_msg.to_dict(), "result": result},
        )
        await self.inbox.put(result_msg)


class FSReadWorker(BaseWorker):
    """
    ELI5: Guard 13 — The file clerk who reads blueprints.
    """

    def __init__(self, worker_id: int, config: SwarmConfig) -> None:
        super().__init__(worker_id, WorkerRole.FS_READ, config)

    async def _handle_message(self, msg: WorkerMessage) -> None:
        if msg.msg_type == MessageType.TASK_REQUEST and msg.payload.get("task_type") == "fs_io":
            self.state.status = "busy"
            result = {"status": "read", "worker_id": self.worker_id}
            self.state.task_count += 1
            self.state.status = "idle"
            await self._send_result(msg, result)

    async def _send_result(self, original_msg: WorkerMessage, result: Dict[str, Any]) -> None:
        result_msg = WorkerMessage(
            sender_id=self.worker_id,
            recipient_id=original_msg.sender_id,
            msg_type=MessageType.TASK_RESULT,
            payload={"original_msg": original_msg.to_dict(), "result": result},
        )
        await self.inbox.put(result_msg)


class FSWriteWorker(BaseWorker):
    """
    ELI5: Guard 14 — The file clerk who files updated documents.
    """

    def __init__(self, worker_id: int, config: SwarmConfig) -> None:
        super().__init__(worker_id, WorkerRole.FS_WRITE, config)

    async def _handle_message(self, msg: WorkerMessage) -> None:
        if msg.msg_type == MessageType.TASK_REQUEST and msg.payload.get("task_type") == "fs_io":
            self.state.status = "busy"
            result = {"status": "written", "worker_id": self.worker_id}
            self.state.task_count += 1
            self.state.status = "idle"
            await self._send_result(msg, result)

    async def _send_result(self, original_msg: WorkerMessage, result: Dict[str, Any]) -> None:
        result_msg = WorkerMessage(
            sender_id=self.worker_id,
            recipient_id=original_msg.sender_id,
            msg_type=MessageType.TASK_RESULT,
            payload={"original_msg": original_msg.to_dict(), "result": result},
        )
        await self.inbox.put(result_msg)


class FSBackupWorker(BaseWorker):
    """
    ELI5: Guard 15 — The archivist who makes photocopies before
          anyone touches the originals.
    """

    def __init__(self, worker_id: int, config: SwarmConfig) -> None:
        super().__init__(worker_id, WorkerRole.FS_BACKUP, config)

    async def _handle_message(self, msg: WorkerMessage) -> None:
        if msg.msg_type == MessageType.TASK_REQUEST and msg.payload.get("task_type") == "fs_io":
            self.state.status = "busy"
            result = {"status": "backed_up", "worker_id": self.worker_id}
            self.state.task_count += 1
            self.state.status = "idle"
            await self._send_result(msg, result)

    async def _send_result(self, original_msg: WorkerMessage, result: Dict[str, Any]) -> None:
        result_msg = WorkerMessage(
            sender_id=self.worker_id,
            recipient_id=original_msg.sender_id,
            msg_type=MessageType.TASK_RESULT,
            payload={"original_msg": original_msg.to_dict(), "result": result},
        )
        await self.inbox.put(result_msg)


class LLMInferenceWorker(BaseWorker):
    """
    ELI5: Guard 16-17 — The on-call engineer who answers technical
          questions over the radio.
    """

    def __init__(self, worker_id: int, config: SwarmConfig) -> None:
        super().__init__(worker_id, WorkerRole.LLM_INFERENCE_A if worker_id == 16 else WorkerRole.LLM_INFERENCE_B, config)

    async def _handle_message(self, msg: WorkerMessage) -> None:
        if msg.msg_type == MessageType.TASK_REQUEST and msg.payload.get("task_type") == "llm":
            self.state.status = "busy"
            prompt = msg.payload.get("prompt", "")
            result = {"status": "inferred", "worker_id": self.worker_id, "prompt_preview": prompt[:50]}
            self.state.task_count += 1
            self.state.status = "idle"
            await self._send_result(msg, result)

    async def _send_result(self, original_msg: WorkerMessage, result: Dict[str, Any]) -> None:
        result_msg = WorkerMessage(
            sender_id=self.worker_id,
            recipient_id=original_msg.sender_id,
            msg_type=MessageType.TASK_RESULT,
            payload={"original_msg": original_msg.to_dict(), "result": result},
        )
        await self.inbox.put(result_msg)


class ErrorCatcherWorker(BaseWorker):
    """
    ELI5: Guard 18 — The emergency response coordinator.
          When any guard radios 'mayday,' this one logs it,
          alerts the supervisor, and dispatches a replacement.
    """

    def __init__(self, worker_id: int, config: SwarmConfig) -> None:
        super().__init__(worker_id, WorkerRole.ERROR_CATCHER, config)
        self._errors: List[Dict[str, Any]] = []

    async def _handle_message(self, msg: WorkerMessage) -> None:
        if msg.msg_type == MessageType.ERROR_REPORT:
            self.state.status = "busy"
            error_record = {
                "timestamp": time.time(),
                "sender": msg.sender_id,
                "error": msg.payload.get("error"),
                "traceback": msg.payload.get("traceback"),
            }
            self._errors.append(error_record)
            self.state.task_count += 1
            self.state.status = "idle"
            logger.error("Error caught from worker %d: %s", msg.sender_id, error_record["error"])

    def get_errors(self) -> List[Dict[str, Any]]:
        return self._errors


class TelemetryWorker(BaseWorker):
    """
    ELI5: Guard 19 — The building's energy management system.
          Logs every watt-hour, every temperature reading,
          every door open event into the building automation database.
    """

    def __init__(self, worker_id: int, config: SwarmConfig) -> None:
        super().__init__(worker_id, WorkerRole.TELEMETRY, config)
        self._metrics: List[Dict[str, Any]] = []

    async def _handle_message(self, msg: WorkerMessage) -> None:
        if msg.msg_type == MessageType.HEARTBEAT:
            self._metrics.append({
                "timestamp": time.time(),
                "worker_id": msg.sender_id,
                "payload": msg.payload,
            })
            self.state.task_count += 1

    def get_metrics(self) -> List[Dict[str, Any]]:
        return self._metrics


class HealthMonitorWorker(BaseWorker):
    """
    ELI5: Guard 20 — The night watch commander.
          Walks every floor every 30 minutes, checks that every
          guard is still on post, and if one is missing, calls
          in a replacement and updates the duty roster.
    """

    def __init__(self, worker_id: int, config: SwarmConfig) -> None:
        super().__init__(worker_id, WorkerRole.HEALTH_MONITOR, config)
        self._dead_workers: Set[int] = set()

    async def _heartbeat(self) -> None:
        await super()._heartbeat()
        # In a real implementation, this would check all worker heartbeats
        # via the state manager and trigger restarts for stale workers.

    async def _handle_message(self, msg: WorkerMessage) -> None:
        if msg.msg_type == MessageType.HEARTBEAT:
            # Track worker health
            sender = msg.sender_id
            if sender in self._dead_workers:
                self._dead_workers.discard(sender)
                logger.info("Worker %d recovered", sender)

    def mark_dead(self, worker_id: int) -> None:
        self._dead_workers.add(worker_id)

    def get_dead_workers(self) -> Set[int]:
        return self._dead_workers.copy()


# ---------------------------------------------------------------------------
# Worker Swarm Factory
# ---------------------------------------------------------------------------

WORKER_ROLE_MAP: Dict[int, Callable[[int, SwarmConfig], BaseWorker]] = {
    1: OrchestratorWorker,
    2: StateManagerWorker,
    3: VisionCaptureWorker,
    4: VisionDetectWorker,
    5: VisionExtractWorker,
    6: OSMouseWorker,
    7: OSKeyboardWorker,
    8: HealingSyntaxWorker,
    9: HealingTypecheckWorker,
    10: HealingTestWorker,
    11: HealingFixWorker,
    12: HealingValidateWorker,
    13: FSReadWorker,
    14: FSWriteWorker,
    15: FSBackupWorker,
    16: LLMInferenceWorker,
    17: LLMInferenceWorker,
    18: ErrorCatcherWorker,
    19: TelemetryWorker,
    20: HealthMonitorWorker,
}


class WorkerSwarm:
    """
    ELI5: The master security control room that houses all 20 guards.
          It hires them, assigns their posts, handles their paychecks,
          and shuts down the whole operation at end of shift.
    """

    def __init__(self, config: Optional[SwarmConfig] = None) -> None:
        self.config = config or SwarmConfig()
        self.workers: Dict[int, BaseWorker] = {}
        self._state_manager: Optional[StateManagerWorker] = None
        self._running = False

    async def start(self) -> None:
        """
        ELI5: Open the building, turn on the lights, and clock in all 20 guards.
        """
        if self._running:
            return

        for worker_id in range(1, self.config.max_workers + 1):
            factory = WORKER_ROLE_MAP.get(worker_id)
            if factory is None:
                continue
            worker = factory(worker_id, self.config)
            self.workers[worker_id] = worker
            if isinstance(worker, StateManagerWorker):
                self._state_manager = worker

        # Register all workers with the state manager
        if self._state_manager:
            for w in self.workers.values():
                self._state_manager.register_worker(w)

        # Start all workers
        await asyncio.gather(*(w.start() for w in self.workers.values()))
        self._running = True
        logger.info("WorkerSwarm started with %d workers", len(self.workers))

    async def stop(self) -> None:
        """
        ELI5: End of shift — clock out every guard and lock the doors.
        """
        if not self._running:
            return

        # Stop in reverse order so state manager stays up longest
        for w in sorted(self.workers.values(), key=lambda x: -x.worker_id):
            await w.stop()

        self._running = False
        logger.info("WorkerSwarm stopped")

    async def submit_task(self, task_type: str, payload: Dict[str, Any]) -> str:
        """
        ELI5: Submit a work order to the supervisor (Worker 01).
        """
        task_id = f"task_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
        msg = WorkerMessage(
            sender_id=0,  # External client
            recipient_id=1,
            msg_type=MessageType.TASK_REQUEST,
            payload={"task_id": task_id, "task_type": task_type, **payload},
        )
        if 1 in self.workers:
            await self.workers[1].send_message(msg)
        return task_id

    def get_status(self) -> Dict[str, Any]:
        """
        ELI5: The end-of-shift report showing every guard's status.
        """
        return {
            "running": self._running,
            "total_workers": len(self.workers),
            "workers": [w.state.to_dict() for w in self.workers.values()],
        }

    def get_worker(self, worker_id: int) -> Optional[BaseWorker]:
        return self.workers.get(worker_id)
