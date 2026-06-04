#!/usr/bin/env python3
"""
test_unified_self_healing.py
============================
Unit tests for the Self-Healing CI/CD engine.

ELI5: Before trusting the smart breaker to auto-repair circuits,
      we deliberately create a faulty outlet and watch the system
      detect, diagnose, and document the fault.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.unified.self_healing import (
    SelfHealingEngine,
    HealingSession,
    HealingIteration,
    CheckResult,
)
from core.unified.config import SelfHealingConfig


class TestCheckResult:
    def test_passed_result(self) -> None:
        """ELI5: A healthy outlet should show green on the tester."""
        result = CheckResult(check_name="syntax", passed=True, duration_ms=10.0)
        assert result.passed is True
        assert result.errors == []

    def test_failed_result(self) -> None:
        """ELI5: A faulty outlet should list exactly what's wrong."""
        result = CheckResult(
            check_name="mypy",
            passed=False,
            errors=["Line 5: Missing return type"],
            duration_ms=50.0,
        )
        assert result.passed is False
        assert len(result.errors) == 1


class TestHealingIteration:
    def test_iteration_to_dict(self) -> None:
        """ELI5: Can we log one full repair cycle?"""
        iteration = HealingIteration(
            iteration=1,
            check_results=[CheckResult("syntax", True)],
            fix_applied=True,
            fix_description="Added missing import",
            backup_path="/backups/test_2026-01-01_1200_PST.py",
        )
        d = iteration.to_dict()
        assert d["iteration"] == 1
        assert d["fix_applied"] is True


class TestHealingSession:
    def test_session_to_dict(self) -> None:
        """ELI5: Can we compile the complete maintenance report?"""
        session = HealingSession(
            session_id="test_001",
            target_path="./src/test.py",
            final_status="healed",
        )
        d = session.to_dict()
        assert d["session_id"] == "test_001"
        assert d["final_status"] == "healed"


class TestSelfHealingEngine:
    def test_engine_creation(self) -> None:
        """ELI5: Can we power on the automated maintenance department?"""
        engine = SelfHealingEngine(config=SelfHealingConfig())
        assert engine.config.max_iterations == 5

    @pytest.mark.asyncio
    async def test_check_syntax_valid_file(self, tmp_path: Path) -> None:
        """ELI5: A properly wired outlet should pass continuity."""
        engine = SelfHealingEngine()
        valid_file = tmp_path / "valid.py"
        valid_file.write_text("x = 1\n", encoding="utf-8")
        result = await engine.check_syntax(valid_file)
        assert result.passed is True
        assert result.check_name == "syntax"

    @pytest.mark.asyncio
    async def test_check_syntax_invalid_file(self, tmp_path: Path) -> None:
        """ELI5: A cracked wire should fail the continuity test."""
        engine = SelfHealingEngine()
        invalid_file = tmp_path / "invalid.py"
        invalid_file.write_text("x = \n", encoding="utf-8")
        result = await engine.check_syntax(invalid_file)
        assert result.passed is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_check_ast_valid(self, tmp_path: Path) -> None:
        """ELI5: A properly braided cable should pass structural inspection."""
        engine = SelfHealingEngine()
        valid_file = tmp_path / "valid_ast.py"
        valid_file.write_text("def hello():\n    return 42\n", encoding="utf-8")
        result = await engine.check_ast(valid_file)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_check_ast_invalid(self, tmp_path: Path) -> None:
        """ELI5: A frayed cable should fail structural inspection."""
        engine = SelfHealingEngine()
        invalid_file = tmp_path / "invalid_ast.py"
        invalid_file.write_text("def hello(\n", encoding="utf-8")
        result = await engine.check_ast(invalid_file)
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_heal_file_sandbox_restriction(self, tmp_path: Path) -> None:
        """ELI5: The maintenance robot should refuse to enter restricted areas."""
        engine = SelfHealingEngine(config=SelfHealingConfig(sandbox_only=True, watch_paths=["/tmp"]))
        file_outside = tmp_path / "outside.py"
        file_outside.write_text("x = 1\n", encoding="utf-8")
        session = await engine.heal_file(file_outside)
        assert session.final_status == "failed"
        assert "sandbox" in (session.error or "").lower()

    def test_get_session(self) -> None:
        """ELI5: Can we retrieve a maintenance log from the filing cabinet?"""
        engine = SelfHealingEngine()
        session = HealingSession(session_id="test_002", target_path="./test.py")
        engine._sessions["test_002"] = session
        found = engine.get_session("test_002")
        assert found is not None
        assert found.session_id == "test_002"
        not_found = engine.get_session("missing")
        assert not_found is None
