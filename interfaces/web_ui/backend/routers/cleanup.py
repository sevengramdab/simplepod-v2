#!/usr/bin/env python3
"""
cleanup.py
==========
FastAPI router for disk cleanup tools.

ELI5: This is the cleanup crew's dispatch office. The foreman (engine)
      does the actual panel audit, but this office takes the work orders
      from the building manager (VS Code: extension) and returns the reports.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.cleanup.cleanup_engine import CleanupEngine, analyze_disk_safety

router = APIRouter(prefix="/tools/cleanup", tags=["cleanup"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------
class AnalyzeRequest(BaseModel):
    drive: str = Field("C:/", description="Drive or root path to analyze")


class LargeFilesRequest(BaseModel):
    drive: str = Field("C:/", description="Drive or root path to scan")
    min_size_mb: float = Field(100.0, ge=1, description="Minimum file size in MB")
    max_files: int = Field(200, ge=1, le=1000, description="Max files to return")


class CleanupTarget(BaseModel):
    path: str = Field(..., description="Absolute path to file or folder")
    force: bool = Field(False, description="Bypass safety score check")


class ExecuteRequest(BaseModel):
    targets: List[CleanupTarget] = Field(..., description="Items to delete")


class SafetyResponse(BaseModel):
    path: str
    size_mb: float
    safety_score: int
    safety_reason: str
    category: str
    last_modified_days: int
    is_directory: bool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post("/analyze")
async def cleanup_analyze(req: AnalyzeRequest):
    """
    ELI5: Full panel audit — read the demand meter, list every appliance,
          and flag anything drawing too much current.
    """
    try:
        engine = CleanupEngine(req.drive)
        return engine.analyze()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup analysis failed: {e}")


@router.post("/games")
async def cleanup_games(req: AnalyzeRequest):
    """
    ELI5: Walk the basement and attic specifically looking for gaming rigs
          and music production gear (the big amp draws).
    """
    try:
        from core.cleanup.cleanup_engine import find_games
        games = find_games(req.drive)
        return {
            "games": [
                {"name": g.name, "platform": g.platform, "size_gb": g.size_gb, "path": g.path}
                for g in games
            ],
            "total_gb": round(sum(g.size_gb for g in games), 2),
            "count": len(games),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Game scan failed: {e}")


@router.post("/large-files")
async def cleanup_large_files(req: LargeFilesRequest):
    """
    ELI5: Thermal-camera scan of the whole panel. Finds the hottest spots
          (biggest files) and colors them green/yellow/red based on whether
          it's safe to touch them.
    """
    try:
        engine = CleanupEngine(req.drive)
        return engine.scan_large_files(req.min_size_mb, req.max_files)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Large-file scan failed: {e}")


@router.post("/safety")
async def cleanup_safety(req: AnalyzeRequest):
    """
    ELI5: The full safety audit report — demand meter, thermal scan,
          and a written list of recommendations for the site supervisor.
    """
    try:
        return analyze_disk_safety(req.drive)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Safety audit failed: {e}")


@router.post("/execute")
async def cleanup_execute(req: ExecuteRequest):
    """
    ELI5: The actual lockout-tagout and breaker trip.
          ONLY items with green tags (safety_score >= 50) get touched
          unless you override with 'force' (requires master electrician sign-off).
    """
    try:
        targets = [{"path": t.path, "force": t.force} for t in req.targets]
        engine = CleanupEngine()
        result = engine.run(targets)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup execution failed: {e}")
