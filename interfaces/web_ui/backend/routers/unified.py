#!/usr/bin/env python3
"""
routers/unified.py
==================
FastAPI router for the SimplePod Unified pipeline.

ELI5: This is the new smart-home control panel mounted on the wall
      next to the old breaker panel. It lets you start the building's
      automation system, submit work orders, and watch the security
      cameras from one interface.
"""

from __future__ import annotations

import base64
import io
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from core.unified import (
    SimplePodUnifiedOrchestrator,
    UnifiedConfig,
    VisionResult,
    OSActionResult,
    GoalResult,
)

logger = logging.getLogger("simplepod.api.unified")

router = APIRouter(prefix="/unified", tags=["unified"])

# Global orchestrator instance — wired in lifespan.
_orchestrator: Optional[SimplePodUnifiedOrchestrator] = None


def set_orchestrator(orch: SimplePodUnifiedOrchestrator) -> None:
    """
    ELI5: Hand the master keys to the building superintendent
          so the API endpoints can issue commands.
    """
    global _orchestrator
    _orchestrator = orch


def get_orchestrator() -> SimplePodUnifiedOrchestrator:
    if _orchestrator is None:
        raise HTTPException(status_code=503, detail="Unified orchestrator not initialized")
    return _orchestrator


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class PipelineActionRequest(BaseModel):
    action: str = Field(..., description="start | stop | pause | resume")


class PipelineStatusResponse(BaseModel):
    pipeline_state: str
    swarm: Dict[str, Any]
    vision_engine_ready: bool
    os_interface_ready: bool
    healing_engine_ready: bool
    active_goals: int


class GoalRequest(BaseModel):
    goal: str = Field(..., description="Natural language goal for the pipeline")


class GoalResponse(BaseModel):
    goal_id: str
    status: str
    message: str


class GoalStatusResponse(BaseModel):
    goal_id: str
    status: str
    result: Optional[Dict[str, Any]]


class VisionAnalyzeResponse(BaseModel):
    success: bool
    width: int
    height: int
    elements: List[Dict[str, Any]]
    processing_time_ms: float
    error: Optional[str]


class OSClickRequest(BaseModel):
    x: int = Field(..., ge=0, description="Screen X coordinate")
    y: int = Field(..., ge=0, description="Screen Y coordinate")
    button: str = Field("left", description="left | right | middle")


class OSTypeRequest(BaseModel):
    text: str = Field(..., description="Text to type")
    interval: Optional[float] = Field(None, description="Seconds between keystrokes")


class SelfHealRequest(BaseModel):
    target_path: str = Field(".", description="Directory or file to heal")


class SelfHealStatusResponse(BaseModel):
    session_id: str
    target_path: str
    final_status: str
    iterations: List[Dict[str, Any]]
    total_duration_ms: float


class WorkerStatusResponse(BaseModel):
    workers: List[Dict[str, Any]]


# ---------------------------------------------------------------------------
# Pipeline Control Endpoints
# ---------------------------------------------------------------------------

@router.post("/pipeline/start", response_model=Dict[str, str])
async def pipeline_start() -> Dict[str, str]:
    """
    ELI5: Flip the main breaker to ON and start the building automation.
    """
    orch = get_orchestrator()
    await orch.start()
    return {"status": "started", "message": "SimplePod Unified pipeline started"}


@router.post("/pipeline/stop", response_model=Dict[str, str])
async def pipeline_stop() -> Dict[str, str]:
    """
    ELI5: Flip the main breaker to OFF and shut down all systems.
    """
    orch = get_orchestrator()
    await orch.stop()
    return {"status": "stopped", "message": "SimplePod Unified pipeline stopped"}


@router.get("/pipeline/status", response_model=PipelineStatusResponse)
async def pipeline_status() -> PipelineStatusResponse:
    """
    ELI5: Read every status LED on the automation panel.
    """
    orch = get_orchestrator()
    return PipelineStatusResponse(**orch.status())


# ---------------------------------------------------------------------------
# Goal Submission Endpoints
# ---------------------------------------------------------------------------

@router.post("/goal", response_model=GoalResponse)
async def submit_goal(req: GoalRequest) -> GoalResponse:
    """
    ELI5: Submit a work order to the building superintendent.
          Example: 'Click the OK button' or 'Heal the auth module.'
    """
    orch = get_orchestrator()
    goal_id = await orch.submit_goal(req.goal)
    return GoalResponse(goal_id=goal_id, status="accepted", message="Goal submitted to pipeline")


@router.get("/goal/{goal_id}", response_model=GoalStatusResponse)
async def get_goal(goal_id: str) -> GoalStatusResponse:
    """
    ELI5: Check the filing cabinet to see if a work order is complete.
    """
    orch = get_orchestrator()
    result = orch.get_goal(goal_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Goal {goal_id} not found")
    return GoalStatusResponse(
        goal_id=goal_id,
        status=result.status,
        result=result.to_dict(),
    )


# ---------------------------------------------------------------------------
# Worker Status Endpoints
# ---------------------------------------------------------------------------

@router.get("/workers", response_model=WorkerStatusResponse)
async def list_workers() -> WorkerStatusResponse:
    """
    ELI5: Print the full duty roster for all 20 security guards.
    """
    orch = get_orchestrator()
    swarm_status = orch.swarm.get_status()
    return WorkerStatusResponse(workers=swarm_status.get("workers", []))


# ---------------------------------------------------------------------------
# Vision Endpoints
# ---------------------------------------------------------------------------

@router.post("/vision/analyze", response_model=VisionAnalyzeResponse)
async def vision_analyze() -> VisionAnalyzeResponse:
    """
    ELI5: Tell the surveillance crew to take a photo of the lobby
          and report every person and object they see.
    """
    orch = get_orchestrator()
    result = await orch.vision.analyze_screen()
    return VisionAnalyzeResponse(
        success=result.success,
        width=result.width,
        height=result.height,
        elements=[e.to_dict() for e in result.elements],
        processing_time_ms=result.processing_time_ms,
        error=result.error,
    )


@router.post("/vision/analyze/upload")
async def vision_analyze_upload(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    ELI5: The security guard analyzes a photo you hand them,
          instead of taking a new one themselves.
    """
    from PIL import Image
    import numpy as np
    import cv2

    orch = get_orchestrator()
    contents = await file.read()
    img = Image.open(io.BytesIO(contents))
    cv_img = cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)

    elements = orch.vision.detect_contours(cv_img)
    return {
        "success": True,
        "width": img.width,
        "height": img.height,
        "elements": [e.to_dict() for e in elements],
    }


# ---------------------------------------------------------------------------
# OS Interface Endpoints
# ---------------------------------------------------------------------------

@router.post("/os/click", response_model=Dict[str, Any])
async def os_click(req: OSClickRequest) -> Dict[str, Any]:
    """
    ELI5: Send the robotic arm to flip a specific switch.
    """
    orch = get_orchestrator()
    result = await orch.os_interface.click(req.x, req.y, button=req.button)
    return result.to_dict()


@router.post("/os/type", response_model=Dict[str, Any])
async def os_type(req: OSTypeRequest) -> Dict[str, Any]:
    """
    ELI5: Tell the robotic typist to enter text into the intercom.
    """
    orch = get_orchestrator()
    result = await orch.os_interface.type_text(req.text, interval=req.interval)
    return result.to_dict()


@router.post("/os/screenshot", response_model=Dict[str, Any])
async def os_screenshot() -> Dict[str, Any]:
    """
    ELI5: Snap a photo of the entire lobby.
    """
    orch = get_orchestrator()
    result = await orch.os_interface.screenshot()
    return result.to_dict()


# ---------------------------------------------------------------------------
# Self-Healing Endpoints
# ---------------------------------------------------------------------------

@router.post("/selfheal/run", response_model=Dict[str, Any])
async def selfheal_run(req: SelfHealRequest) -> Dict[str, Any]:
    """
    ELI5: Dispatch the maintenance crew to test and repair
          every circuit in the specified room.
    """
    orch = get_orchestrator()
    target = Path(req.target_path)
    if target.is_file():
        session = await orch.healing.heal_file(target)
        return {"session_id": session.session_id, "status": "started", "target": str(target)}
    elif target.is_dir():
        sessions = await orch.healing.heal_directory(target)
        return {
            "sessions": [s.session_id for s in sessions],
            "status": "started",
            "target": str(target),
            "file_count": len(sessions),
        }
    else:
        raise HTTPException(status_code=400, detail=f"Target not found: {req.target_path}")


@router.get("/selfheal/status/{session_id}", response_model=SelfHealStatusResponse)
async def selfheal_status(session_id: str) -> SelfHealStatusResponse:
    """
    ELI5: Pull the maintenance log from the filing cabinet.
    """
    orch = get_orchestrator()
    session = orch.healing.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return SelfHealStatusResponse(
        session_id=session.session_id,
        target_path=session.target_path,
        final_status=session.final_status,
        iterations=[i.to_dict() for i in session.iterations],
        total_duration_ms=session.total_duration_ms,
    )


# ---------------------------------------------------------------------------
# WebSocket Feed
# ---------------------------------------------------------------------------

@router.websocket("/ws")
async def unified_websocket(websocket: WebSocket) -> None:
    """
    ELI5: A live two-way radio channel to the control room.
          You hear every guard's heartbeat and every incident report
          in real time.
    """
    await websocket.accept()
    orch = get_orchestrator()

    try:
        while True:
            # Send status update every 2 seconds
            status = orch.status()
            await websocket.send_json({"type": "status", "data": status})

            # Check for client messages (non-blocking)
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=2.0)
                if msg == "ping":
                    await websocket.send_json({"type": "pong"})
                elif msg.startswith("goal:"):
                    goal = msg[5:]
                    goal_id = await orch.submit_goal(goal)
                    await websocket.send_json({"type": "goal_accepted", "goal_id": goal_id})
            except asyncio.TimeoutError:
                pass

    except WebSocketDisconnect:
        logger.info("Unified WebSocket client disconnected")
    except Exception as exc:
        logger.exception("Unified WebSocket error")
        await websocket.close(code=1011, reason=str(exc))


# ---------------------------------------------------------------------------
# Phone Simulator Demo Endpoints (No LLM Required)
# ---------------------------------------------------------------------------

@router.get("/demo/phone/contacts")
async def demo_phone_contacts() -> Dict[str, Any]:
    """
    ELI5: Open the simulated filing cabinet and show the fake contact list.
          No real people. Just training dummies for the security team.
    """
    from core.unified.phone_analyzer import PhoneAnalyzer
    analyzer = PhoneAnalyzer()
    return {"contacts": analyzer.load_contacts()}


@router.get("/demo/phone/threads")
async def demo_phone_threads() -> Dict[str, Any]:
    """ELI5: Show all the fake radio transcripts."""
    from core.unified.phone_analyzer import PhoneAnalyzer
    analyzer = PhoneAnalyzer()
    threads = analyzer.load_threads()
    summary = {
        tid: {
            "participants": t.get("participants", []),
            "message_count": t.get("message_count", 0),
            "first_message": t.get("first_message"),
            "last_message": t.get("last_message"),
        }
        for tid, t in threads.items()
    }
    return {"threads": summary}


@router.get("/demo/phone/thread/{thread_id}")
async def demo_phone_thread(thread_id: str) -> Dict[str, Any]:
    """ELI5: Read one specific fake radio transcript in full."""
    from core.unified.phone_analyzer import PhoneAnalyzer
    analyzer = PhoneAnalyzer()
    threads = analyzer.load_threads()
    if thread_id not in threads:
        raise HTTPException(status_code=404, detail=f"Thread {thread_id} not found")
    return threads[thread_id]


@router.get("/demo/phone/report", response_class=HTMLResponse)
async def demo_phone_report() -> str:
    """
    ELI5: Instead of handing the superintendent a stack of raw meter readings,
          we print a nice formatted dashboard they can read at a glance.
    """
    from core.unified.phone_analyzer import PhoneAnalyzer
    analyzer = PhoneAnalyzer()
    report = analyzer.analyze_extraction()

    rows = ""
    for t in report.thread_analyses:
        flag_badge = f'<span style="background:#c0392b;color:white;padding:2px 8px;border-radius:12px;font-size:12px">{len(t.red_flags)} flags</span>' if t.red_flags else '<span style="background:#27ae60;color:white;padding:2px 8px;border-radius:12px;font-size:12px">Clean</span>'
        imbalance = f"<br><small style='color:#e67e22'>&#9888; {t.power_imbalance}</small>" if t.power_imbalance else ""
        rows += f"""
        <tr style="border-bottom:1px solid #333">
            <td style="padding:12px"><strong>{t.thread_id}</strong></td>
            <td style="padding:12px">{', '.join(t.participants)}</td>
            <td style="padding:12px">{t.message_count}</td>
            <td style="padding:12px">{t.sentiment.dominant}</td>
            <td style="padding:12px">{'&#128150;' * int(t.intimacy_score * 5)} {t.intimacy_score:.2f}</td>
            <td style="padding:12px">{'&#128296;' * int(t.control_score * 5)} {t.control_score:.2f}</td>
            <td style="padding:12px">{flag_badge}{imbalance}</td>
        </tr>
        """

    red_flag_list = ""
    for t in report.thread_analyses:
        if t.red_flags:
            red_flag_list += f"<h4 style='color:#e74c3c;margin-top:20px'>{t.thread_id}</h4><ul>"
            for f in t.red_flags:
                red_flag_list += f"<li style='margin:6px 0'>{f}</li>"
            red_flag_list += "</ul>"

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Phone Extraction Report</title></head>
<body style="background:#0a0e17;color:#e0e6ed;font-family:Segoe UI,Roboto,sans-serif;margin:0;padding:40px;line-height:1.6">
    <div style="max-width:1000px;margin:0 auto">
        <h1 style="color:#fff;border-bottom:2px solid #e74c3c;padding-bottom:15px">
            &#128241; Phone Extraction Analysis Report
        </h1>
        <div style="background:#1a1f2e;border-radius:12px;padding:25px;margin:20px 0">
            <div style="display:flex;gap:30px;flex-wrap:wrap">
                <div><strong>Device Owner:</strong> {report.device_owner}</div>
                <div><strong>Contacts:</strong> {report.contact_count}</div>
                <div><strong>Messages:</strong> {report.total_messages}</div>
                <div><strong>Calls:</strong> {report.total_calls}</div>
                <div><strong>Media:</strong> {report.total_media}</div>
            </div>
        </div>

        <div style="background:{'#c0392b' if report.risk_level == 'critical' else '#e67e22'}33;border:1px solid {'#c0392b' if report.risk_level == 'critical' else '#e67e22'};border-radius:12px;padding:20px;margin:20px 0">
            <h2 style="margin:0;color:{'#c0392b' if report.risk_level == 'critical' else '#e67e22'}">
                RISK LEVEL: {report.risk_level.upper()}
            </h2>
        </div>

        <h2 style="color:#3498db;margin-top:30px">&#128200; Thread Analysis</h2>
        <table style="width:100%;border-collapse:collapse;background:#1a1f2e;border-radius:12px;overflow:hidden">
            <thead style="background:#2c3e50">
                <tr>
                    <th style="padding:12px;text-align:left">Thread</th>
                    <th style="padding:12px;text-align:left">Participants</th>
                    <th style="padding:12px;text-align:left">Msgs</th>
                    <th style="padding:12px;text-align:left">Sentiment</th>
                    <th style="padding:12px;text-align:left">Intimacy</th>
                    <th style="padding:12px;text-align:left">Control</th>
                    <th style="padding:12px;text-align:left">Flags</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>

        <h2 style="color:#e74c3c;margin-top:30px">&#9888; Red Flags Detected</h2>
        <div style="background:#1a1f2e;border-radius:12px;padding:25px">{red_flag_list}</div>

        <h2 style="color:#9b59b6;margin-top:30px">&#128221; Overall Assessment</h2>
        <div style="background:#1a1f2e;border-radius:12px;padding:25px;white-space:pre-wrap;font-family:monospace">{report.overall_assessment}</div>

        <div style="margin-top:40px;padding:20px;text-align:center;color:#666;font-size:12px">
            Generated by SimplePod Unified Phone Analyzer | All data is simulated for testing
        </div>
    </div>
</body></html>"""
    return html


@router.get("/demo/phone/analyze")
async def demo_phone_analyze() -> Dict[str, Any]:
    """
    ELI5: Run the full forensic diagnostic on the fake evidence.
          This proves the analysis engine works without needing
          a working LLM connection.
    """
    from core.unified.phone_analyzer import PhoneAnalyzer
    analyzer = PhoneAnalyzer()
    report = analyzer.analyze_extraction()
    return {
        "device_owner": report.device_owner,
        "risk_level": report.risk_level,
        "total_messages": report.total_messages,
        "total_calls": report.total_calls,
        "total_media": report.total_media,
        "contact_count": report.contact_count,
        "overall_assessment": report.overall_assessment,
        "thread_analyses": [
            {
                "thread_id": t.thread_id,
                "participants": t.participants,
                "message_count": t.message_count,
                "sentiment": {
                    "dominant": t.sentiment.dominant,
                    "positive": t.sentiment.positive,
                    "negative": t.sentiment.negative,
                    "neutral": t.sentiment.neutral,
                },
                "intimacy_score": t.intimacy_score,
                "control_score": t.control_score,
                "power_imbalance": t.power_imbalance,
                "red_flags": t.red_flags,
                "key_phrases": t.key_phrases,
            }
            for t in report.thread_analyses
        ],
    }


# ---------------------------------------------------------------------------
# LLM Fallback Test Endpoint
# ---------------------------------------------------------------------------

class LLMTestRequest(BaseModel):
    prompt: str = Field(..., description="Text to send to the LLM")
    use_fallback: bool = Field(True, description="Use Pollinations fallback if Ollama fails")


@router.post("/demo/llm-test")
async def demo_llm_test(req: LLMTestRequest) -> Dict[str, Any]:
    """
    ELI5: Test the backup solar generator. Send it a message and see
          if it responds — no main power (Ollama) required.
    """
    from core.unified.llm_fallback import query_llm_with_fallback
    import asyncio

    loop = asyncio.get_event_loop()
    try:
        response = await loop.run_in_executor(
            None,
            query_llm_with_fallback,
            req.prompt,
            "http://127.0.0.1:11434",
            "llama3.2",
            "You are a helpful assistant.",
            30,
        )
        source = "ollama" if response and len(response) > 10 else "pollinations_fallback"
        if not response:
            source = "failed"
        return {
            "success": response != "",
            "source": source,
            "response": response[:500] if response else "No response from any LLM provider",
        }
    except Exception as exc:
        return {"success": False, "source": "error", "response": str(exc)}


# ---------------------------------------------------------------------------
# OrbitScribe Relationship Engine — LLM Reasoning Demo
# ---------------------------------------------------------------------------

@router.get("/demo/orbitscribe/analyze")
async def orbitscribe_analyze(mode: str = "auto") -> Dict[str, Any]:
    """
    ELI5: Bring in the master electrician for a full building diagnostic.
          mode=auto: tries LLM first, falls back to synthetic instantly if unavailable.
          mode=llm: forces LLM analysis (may take 2-5 minutes).
          mode=synthetic: instant demo with pre-built reasoning chains.
    """
    from core.unified.orbitscribe_demo import OrbitScribeEngine
    import asyncio

    loop = asyncio.get_event_loop()
    use_llm = (mode == "llm")
    engine = OrbitScribeEngine(use_llm=use_llm)

    try:
        report = await loop.run_in_executor(None, engine.generate_full_report)
        return {
            "success": True,
            "device_owner": report.device_owner,
            "timestamp": report.analysis_timestamp,
            "risk_level": report.risk_level,
            "llm_used": report.llm_used,
            "mode": mode,
            "overall_narrative": report.overall_narrative,
            "llm_reasoning_summary": report.llm_reasoning_summary,
            "attachment_analyses": [
                {
                    "subject": a.subject,
                    "partner": a.partner,
                    "attachment_style": a.attachment_style,
                    "evidence": a.evidence,
                    "confidence": a.confidence,
                    "reasoning": [
                        {"step": r.step, "observation": r.observation, "inference": r.inference, "confidence": r.confidence}
                        for r in a.reasoning
                    ],
                }
                for a in report.attachment_analyses
            ],
            "triangulation_events": [
                {
                    "speaker": t.speaker,
                    "target": t.target,
                    "listener": t.listener,
                    "context": t.context,
                    "manipulative_score": t.manipulative_score,
                    "reasoning": [
                        {"step": r.step, "observation": r.observation, "inference": r.inference, "confidence": r.confidence}
                        for r in t.reasoning
                    ],
                }
                for t in report.triangulation_events
            ],
            "emotional_trajectories": [
                {
                    "thread_id": et.thread_id,
                    "start_sentiment": et.start_sentiment,
                    "end_sentiment": et.end_sentiment,
                    "trajectory": et.trajectory,
                    "inflection_points": et.inflection_points,
                    "reasoning": [
                        {"step": r.step, "observation": r.observation, "inference": r.inference, "confidence": r.confidence}
                        for r in et.reasoning
                    ],
                }
                for et in report.emotional_trajectories
            ],
            "relationship_graph": [
                {
                    "name": n.name,
                    "role": n.role,
                    "centrality_score": n.centrality_score,
                    "risk_profile": n.risk_profile,
                    "connections": n.connections,
                }
                for n in report.relationship_graph
            ],
        }
    except Exception as exc:
        logger.exception("OrbitScribe analysis failed")
        return {"success": False, "error": str(exc)}


@router.get("/demo/orbitscribe/report", response_class=HTMLResponse)
async def orbitscribe_report(mode: str = "auto") -> str:
    """
    ELI5: The master electrician's full written report, printed on nice paper
          with charts and annotations so the superintendent can read it over coffee.
          mode=auto: tries LLM first, falls back to synthetic instantly if unavailable.
          mode=llm: forces LLM analysis (may take 2-5 minutes).
          mode=synthetic: instant demo with pre-built reasoning chains.
    """
    from core.unified.orbitscribe_demo import OrbitScribeEngine
    import asyncio

    loop = asyncio.get_event_loop()
    use_llm = (mode == "llm")
    engine = OrbitScribeEngine(use_llm=use_llm)

    try:
        report = await loop.run_in_executor(None, engine.generate_full_report)
    except Exception as exc:
        return f"""<!DOCTYPE html><html><body style="background:#0a0e17;color:#e74c3c;font-family:sans-serif;padding:40px">
        <h1>OrbitScribe Error</h1><p>{exc}</p></body></html>"""

    # Build attachment rows
    att_rows = ""
    for a in report.attachment_analyses:
        ev_list = "".join(f'<li style="margin:4px 0">"{e}"</li>' for e in a.evidence[:5])
        reason_chain = "".join(
            f'<div style="margin:6px 0;padding:6px;background:#0f172a;border-radius:6px">'
            f'<small style="color:#60a5fa">Step {r.step}</small><br>'
            f'<strong>Observation:</strong> {r.observation}<br>'
            f'<strong>Inference:</strong> {r.inference}<br>'
            f'<small style="color:#94a3b8">Confidence: {r.confidence:.0%}</small></div>'
            for r in a.reasoning
        )
        style_color = {"secure": "#22c55e", "anxious": "#eab308", "avoidant": "#3b82f6", "disorganized": "#ef4444"}.get(a.attachment_style, "#94a3b8")
        att_rows += f"""
        <div style="background:#1e293b;border-radius:12px;padding:20px;margin:16px 0;border-left:4px solid {style_color}">
            <h3 style="margin:0;color:{style_color}">{a.subject} &harr; {a.partner}</h3>
            <div style="margin:8px 0"><span style="background:{style_color}33;color:{style_color};padding:4px 12px;border-radius:12px;font-size:13px;font-weight:bold">{a.attachment_style.upper()}</span>
            <span style="color:#94a3b8;margin-left:12px">Confidence: {a.confidence:.0%}</span></div>
            <h4 style="color:#cbd5e1;margin:12px 0 6px">Evidence:</h4><ul style="color:#e2e8f0;margin:0">{ev_list}</ul>
            <h4 style="color:#cbd5e1;margin:16px 0 6px">Reasoning Chain:</h4>{reason_chain}
        </div>
        """

    # Build triangulation rows
    tri_rows = ""
    for t in report.triangulation_events:
        score_color = "#ef4444" if t.manipulative_score > 0.7 else "#eab308" if t.manipulative_score > 0.4 else "#22c55e"
        reason_chain = "".join(
            f'<div style="margin:6px 0;padding:6px;background:#0f172a;border-radius:6px">'
            f'<small style="color:#60a5fa">Step {r.step}</small><br>'
            f'<strong>Observation:</strong> {r.observation}<br>'
            f'<strong>Inference:</strong> {r.inference}<br>'
            f'<small style="color:#94a3b8">Confidence: {r.confidence:.0%}</small></div>'
            for r in t.reasoning
        )
        tri_rows += f"""
        <div style="background:#1e293b;border-radius:12px;padding:20px;margin:16px 0;border-left:4px solid {score_color}">
            <h3 style="margin:0;color:{score_color}">{t.speaker} &rarr; {t.listener} (about {t.target})</h3>
            <div style="margin:8px 0"><span style="background:{score_color}33;color:{score_color};padding:4px 12px;border-radius:12px;font-size:13px;font-weight:bold">Manipulative Score: {t.manipulative_score:.0%}</span></div>
            <p style="color:#e2e8f0;font-style:italic">"{t.context[:300]}"</p>
            <h4 style="color:#cbd5e1;margin:12px 0 6px">Reasoning:</h4>{reason_chain}
        </div>
        """

    # Build trajectory rows
    traj_rows = ""
    for et in report.emotional_trajectories:
        traj_color = {"improving": "#22c55e", "stable": "#3b82f6", "declining": "#ef4444", "volatile": "#eab308"}.get(et.trajectory, "#94a3b8")
        points = "".join(
            f'<div style="margin:4px 0;padding:6px;background:#0f172a;border-radius:6px">'
            f'<strong>{p.get("date","?")}:</strong> {p.get("event","")} '
            f'<span style="color:{traj_color}">({p.get("sentiment_shift","")})</span></div>'
            for p in et.inflection_points
        )
        traj_rows += f"""
        <div style="background:#1e293b;border-radius:12px;padding:20px;margin:16px 0;border-left:4px solid {traj_color}">
            <h3 style="margin:0">{et.thread_id}</h3>
            <div style="margin:8px 0"><span style="background:{traj_color}33;color:{traj_color};padding:4px 12px;border-radius:12px;font-size:13px;font-weight:bold">{et.trajectory.upper()}</span>
            <span style="color:#94a3b8;margin-left:12px">{et.start_sentiment} &rarr; {et.end_sentiment}</span></div>
            <h4 style="color:#cbd5e1;margin:12px 0 6px">Inflection Points:</h4>{points}
        </div>
        """

    # Build graph nodes
    graph_nodes = ""
    for n in report.relationship_graph:
        risk_color = {"low": "#22c55e", "moderate": "#eab308", "high": "#ef4444", "critical": "#dc2626"}.get(n.risk_profile, "#94a3b8")
        conn_rows = "".join(
            f'<tr><td style="padding:6px 12px">{name}</td>'
            f'<td style="padding:6px 12px">{data.get("type","?")}</td>'
            f'<td style="padding:6px 12px"><div style="background:#334155;height:8px;border-radius:4px;width:100px"><div style="background:#60a5fa;height:8px;border-radius:4px;width:{data.get("strength",0)*100:.0f}px"></div></div></td>'
            f'<td style="padding:6px 12px">{data.get("risk",0):.0%}</td></tr>'
            for name, data in n.connections.items()
        )
        graph_nodes += f"""
        <div style="background:#1e293b;border-radius:12px;padding:20px;margin:16px 0;border-left:4px solid {risk_color}">
            <h3 style="margin:0">{n.name} <span style="font-size:14px;color:#94a3b8">({n.role})</span></h3>
            <div style="margin:8px 0"><span style="background:{risk_color}33;color:{risk_color};padding:4px 12px;border-radius:12px;font-size:13px;font-weight:bold">{n.risk_profile.upper()}</span>
            <span style="color:#94a3b8;margin-left:12px">Centrality: {n.centrality_score:.0%}</span></div>
            <table style="width:100%;margin-top:12px;border-collapse:collapse;font-size:13px">
                <thead style="background:#0f172a"><tr><th style="padding:6px 12px;text-align:left">Connected To</th><th style="padding:6px 12px;text-align:left">Type</th><th style="padding:6px 12px;text-align:left">Strength</th><th style="padding:6px 12px;text-align:left">Risk</th></tr></thead>
                <tbody>{conn_rows}</tbody>
            </table>
        </div>
        """

    risk_banner_color = {"low": "#22c55e", "moderate": "#eab308", "high": "#ef4444", "critical": "#dc2626"}.get(report.risk_level, "#94a3b8")

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>OrbitScribe Relationship Report</title></head>
<body style="background:#0a0e17;color:#e0e6ed;font-family:Segoe UI,Roboto,sans-serif;margin:0;padding:40px;line-height:1.6">
    <div style="max-width:1100px;margin:0 auto">
        <h1 style="color:#fff;border-bottom:2px solid #8b5cf6;padding-bottom:15px">
            &#128301; OrbitScribe Relationship Engine
        </h1>
        <p style="color:#94a3b8">LLM-powered reasoning analysis with chain-of-thought evidence</p>

        <div style="background:{risk_banner_color}22;border:1px solid {risk_banner_color};border-radius:12px;padding:20px;margin:20px 0">
            <h2 style="margin:0;color:{risk_banner_color}">OVERALL RISK: {report.risk_level.upper()}</h2>
            <p style="margin:8px 0 0;color:#cbd5e1">{report.llm_reasoning_summary.replace(chr(10), '<br>')}</p>
            <div style="margin-top:12px">
                <span style="background:{'#22c55e' if report.llm_used else '#eab308'}33;color:{'#22c55e' if report.llm_used else '#eab308'};padding:4px 12px;border-radius:12px;font-size:12px;font-weight:bold">
                    {'&#129302; LLM REASONING' if report.llm_used else '&#128208; SYNTHETIC DEMO'}
                </span>
                <span style="color:#94a3b8;margin-left:12px;font-size:12px">
                    {'Live model inference with chain-of-thought' if report.llm_used else 'Pre-built reasoning chains for instant demo'}
                </span>
            </div>
        </div>

        <h2 style="color:#8b5cf6;margin-top:30px">&#128220; Narrative Summary</h2>
        <div style="background:#1e293b;border-radius:12px;padding:25px;white-space:pre-wrap;font-family:Georgia,serif;font-size:15px;color:#e2e8f0;line-height:1.8">{report.overall_narrative}</div>

        <h2 style="color:#22c55e;margin-top:30px">&#128279; Attachment Analyses</h2>
        {att_rows}

        <h2 style="color:#ef4444;margin-top:30px">&#9888; Triangulation Events</h2>
        {tri_rows}

        <h2 style="color:#3b82f6;margin-top:30px">&#128200; Emotional Trajectories</h2>
        {traj_rows}

        <h2 style="color:#eab308;margin-top:30px">&#127760; Relationship Graph</h2>
        {graph_nodes}

        <div style="margin-top:40px;padding:20px;text-align:center;color:#666;font-size:12px">
            Generated by OrbitScribe LLM Reasoning Engine | SimplePod Unified Demo
        </div>
    </div>
</body></html>"""
    return html
