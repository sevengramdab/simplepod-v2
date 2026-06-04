#!/usr/bin/env python3
"""
core/unified/self_healing.py
============================
Self-Healing CI/CD Loop — Automated test compilation, error catching,
and autonomous refactoring until tests pass.

ELI5: Think of this like a smart electrical panel with self-diagnostic
      breakers. If a circuit starts overheating (syntax error), the
      panel detects it, calls an electrician (the LLM), watches them
      repair the wiring, and then re-tests the circuit before flipping
      the breaker back on. If it still trips, the process repeats
      up to 5 times before paging the head engineer.
"""

from __future__ import annotations

import asyncio
import ast
import json
import logging
import os
import py_compile
import shutil
import subprocess
import tempfile
import time
import traceback
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .config import SelfHealingConfig

logger = logging.getLogger("simplepod.unified.healing")


@dataclass
class CheckResult:
    """
    ELI5: The meter reading after testing one outlet.
          Was there voltage? Was the ground fault light on?
    """

    check_name: str
    passed: bool
    stdout: str = ""
    stderr: str = ""
    errors: List[str] = field(default_factory=list)
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_name": self.check_name,
            "passed": self.passed,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "errors": self.errors,
            "duration_ms": round(self.duration_ms, 2),
        }


@dataclass
class HealingIteration:
    """
    ELI5: One full cycle of the smart breaker:
          test → detect fault → call electrician → re-test.
    """

    iteration: int
    check_results: List[CheckResult]
    fix_applied: bool
    fix_description: str
    backup_path: Optional[str]
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "iteration": self.iteration,
            "check_results": [c.to_dict() for c in self.check_results],
            "fix_applied": self.fix_applied,
            "fix_description": self.fix_description,
            "backup_path": self.backup_path,
            "error": self.error,
        }


@dataclass
class HealingSession:
    """
    ELI5: The complete maintenance log for one service call.
          Every test, every repair, every re-test is documented.
    """

    session_id: str
    target_path: str
    iterations: List[HealingIteration] = field(default_factory=list)
    final_status: str = "running"  # running | healed | failed | max_iterations
    started_at: str = field(default_factory=lambda: datetime.now(timezone(timedelta(hours=-7))).isoformat())
    finished_at: Optional[str] = None
    total_duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "target_path": self.target_path,
            "iterations": [i.to_dict() for i in self.iterations],
            "final_status": self.final_status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "total_duration_ms": round(self.total_duration_ms, 2),
        }


class SelfHealingEngine:
    """
    ELI5: The building's automated maintenance department.
          It patrols the hallways (watches files), tests every outlet
          (runs checks), and calls in repairs when something is broken.
    """

    def __init__(self, config: Optional[SelfHealingConfig] = None) -> None:
        self.config = config or SelfHealingConfig()
        self._sessions: Dict[str, HealingSession] = {}

    def _now_pst(self) -> str:
        """
        ELI5: Set our watch to Pacific Time so every log entry matches.
        """
        pst = timezone(timedelta(hours=-7))
        return datetime.now(pst).strftime("%Y-%m-%d_%H%M_PST")

    def _backup_file(self, path: Path) -> Path:
        """
        ELI5: Before the electrician touches any wiring, we photocopy
              the original blueprints and lock them in the filing cabinet.
              If the repair goes wrong, we can restore exactly what was there.
        """
        # Use ark_backup_dir if set, else local fallback
        backup_dir = Path(self.config.ark_backup_dir) if self.config.ark_backup_dir else Path("./ark_backups")
        if not backup_dir.exists() or not backup_dir.is_dir():
            backup_dir = Path("./ark_backups")
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = self._now_pst()
        backup_name = f"{path.stem}_{timestamp}{path.suffix}"
        backup_path = backup_dir / backup_name
        shutil.copy2(path, backup_path)
        logger.info("Backup created: %s -> %s", path, backup_path)
        return backup_path

    def _is_allowed_path(self, path: Path) -> bool:
        """
        ELI5: The maintenance robot is only allowed in certain rooms.
              It cannot wander into the CEO's office or the vault.
        """
        if self.config.sandbox_only:
            for watch in self.config.watch_paths:
                watch_path = Path(watch).resolve()
                try:
                    path.resolve().relative_to(watch_path)
                    return True
                except ValueError:
                    continue
            return False
        return True

    async def _run_subprocess(
        self,
        cmd: List[str],
        cwd: Optional[str] = None,
        timeout: int = 120,
    ) -> Tuple[int, str, str]:
        """
        ELI5: The walkie-talkie call to a subcontractor.
              We ask them to do a job and wait for their report back.
        """
        loop = asyncio.get_event_loop()
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
            stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            stdout = stdout_b.decode("utf-8", errors="replace")
            stderr = stderr_b.decode("utf-8", errors="replace")
            return proc.returncode or 0, stdout, stderr
        except asyncio.TimeoutError:
            if proc.returncode is None:
                proc.kill()
                await proc.wait()
            return 1, "", f"Command timed out after {timeout}s"
        except Exception as exc:
            return 1, "", str(exc)

    async def check_syntax(self, path: Path) -> CheckResult:
        """
        ELI5: The first test — does the wire even conduct electricity?
              If the insulation is cracked (syntax error), we catch it here.
        """
        t0 = time.time()
        try:
            py_compile.compile(str(path), doraise=True)
            return CheckResult(check_name="syntax", passed=True, duration_ms=(time.time() - t0) * 1000)
        except py_compile.PyCompileError as exc:
            return CheckResult(
                check_name="syntax",
                passed=False,
                errors=[str(exc)],
                duration_ms=(time.time() - t0) * 1000,
            )

    async def check_ast(self, path: Path) -> CheckResult:
        """
        ELI5: A more detailed inspection of the wire's internal structure.
              Even if it conducts, is the copper braided correctly?
        """
        t0 = time.time()
        try:
            source = path.read_text(encoding="utf-8", errors="ignore")
            ast.parse(source)
            return CheckResult(check_name="ast", passed=True, duration_ms=(time.time() - t0) * 1000)
        except SyntaxError as exc:
            return CheckResult(
                check_name="ast",
                passed=False,
                errors=[f"Line {exc.lineno}: {exc.msg}"],
                duration_ms=(time.time() - t0) * 1000,
            )

    async def check_mypy(self, path: Path) -> CheckResult:
        """
        ELI5: Check that every wire is labeled with the correct gauge.
              12 AWG where 12 AWG belongs, 14 AWG where 14 AWG belongs.
        """
        if not self.config.mypy_enabled:
            return CheckResult(check_name="mypy", passed=True)

        t0 = time.time()
        rc, stdout, stderr = await self._run_subprocess(
            ["python", "-m", "mypy", "--ignore-missing-imports", "--show-error-codes", str(path)]
        )
        passed = rc == 0
        errors = []
        if not passed:
            for line in (stdout + stderr).splitlines():
                if ": error:" in line or ": note:" in line:
                    errors.append(line.strip())
        return CheckResult(
            check_name="mypy",
            passed=passed,
            stdout=stdout,
            stderr=stderr,
            errors=errors,
            duration_ms=(time.time() - t0) * 1000,
        )

    async def check_ruff(self, path: Path) -> CheckResult:
        """
        ELI5: The code inspector checks for code violations —
              like exposed junction boxes or wires running without conduit.
        """
        if not self.config.ruff_enabled:
            return CheckResult(check_name="ruff", passed=True)

        t0 = time.time()
        rc, stdout, stderr = await self._run_subprocess(
            ["python", "-m", "ruff", "check", str(path)]
        )
        passed = rc == 0
        errors = []
        if not passed:
            for line in (stdout + stderr).splitlines():
                if line.strip() and not line.startswith("Found"):
                    errors.append(line.strip())
        return CheckResult(
            check_name="ruff",
            passed=passed,
            stdout=stdout,
            stderr=stderr,
            errors=errors,
            duration_ms=(time.time() - t0) * 1000,
        )

    async def check_pytest(self, path: Path) -> CheckResult:
        """
        ELI5: The full load test — turn on every appliance at once
              and make sure the main breaker doesn't trip.
        """
        if not self.config.pytest_enabled:
            return CheckResult(check_name="pytest", passed=True)

        t0 = time.time()
        # Look for tests in the same directory or a tests/ folder
        test_dirs: List[Path] = []
        if (path.parent / "tests").exists():
            test_dirs.append(path.parent / "tests")
        if (path.parent.parent / "tests").exists():
            test_dirs.append(path.parent.parent / "tests")

        if not test_dirs:
            return CheckResult(
                check_name="pytest",
                passed=True,
                stdout="No test directories found — skipping.",
                duration_ms=(time.time() - t0) * 1000,
            )

        errors = []
        all_passed = True
        combined_stdout = ""
        combined_stderr = ""

        for test_dir in test_dirs:
            rc, stdout, stderr = await self._run_subprocess(
                [
                    "python",
                    "-m",
                    "pytest",
                    str(test_dir),
                    "-v",
                    "--tb=short",
                    "--color=no",
                ],
                timeout=self.config.timeout_seconds,
            )
            combined_stdout += stdout + "\n"
            combined_stderr += stderr + "\n"
            if rc != 0:
                all_passed = False
                for line in (stdout + stderr).splitlines():
                    if "FAILED" in line or "ERROR" in line:
                        errors.append(line.strip())

        return CheckResult(
            check_name="pytest",
            passed=all_passed,
            stdout=combined_stdout,
            stderr=combined_stderr,
            errors=errors,
            duration_ms=(time.time() - t0) * 1000,
        )

    async def run_all_checks(self, path: Path) -> List[CheckResult]:
        """
        ELI5: Run the complete inspection checklist on one circuit.
        """
        checks = [
            self.check_syntax(path),
            self.check_ast(path),
            self.check_mypy(path),
            self.check_ruff(path),
            self.check_pytest(path),
        ]
        return await asyncio.gather(*checks)

    def _build_llm_prompt(
        self,
        path: Path,
        source: str,
        check_results: List[CheckResult],
    ) -> str:
        """
        ELI5: Write up the work order for the electrician.
              List every fault found, the exact location, and the
              original wiring diagram so they know what to fix.
        """
        error_lines = []
        for cr in check_results:
            if not cr.passed:
                error_lines.append(f"## {cr.check_name}")
                for err in cr.errors[:10]:
                    error_lines.append(f"- {err}")

        prompt = f"""You are an expert Python developer. Fix the following code so it passes all checks.

File: {path.name}

Errors detected:
{chr(10).join(error_lines)}

Current code:
```python
{source}
```

Return ONLY the corrected Python code inside a single ```python code block. Do not include explanations.
"""
        return prompt

    async def query_llm_for_fix(self, prompt: str) -> str:
        """
        ELI5: Call the master electrician on the radio. If the main
              channel is dead, the backup solar radio kicks in automatically.
        """
        from .llm_fallback import fix_code
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, fix_code, prompt)

        # Extract ```python block if present
        if "```python" in result:
            start = result.index("```python") + len("```python")
            end = result.find("```", start)
            if end == -1:
                end = len(result)
            return result[start:end].strip()
        return result.strip()

    async def heal_file(self, path: Path) -> HealingSession:
        """
        ELI5: The full maintenance protocol for one circuit.
              Inspect, diagnose, repair, re-inspect, repeat.
        """
        session_id = f"heal_{path.stem}_{int(time.time())}"
        session = HealingSession(session_id=session_id, target_path=str(path))
        self._sessions[session_id] = session

        if not self._is_allowed_path(path):
            session.final_status = "failed"
            session.error = "Path outside sandbox"
            session.finished_at = self._now_pst()
            return session

        t0_total = time.time()

        for iteration in range(1, self.config.max_iterations + 1):
            logger.info("Healing iteration %d for %s", iteration, path)
            check_results = await self.run_all_checks(path)
            all_passed = all(cr.passed for cr in check_results)

            if all_passed:
                session.iterations.append(
                    HealingIteration(
                        iteration=iteration,
                        check_results=check_results,
                        fix_applied=False,
                        fix_description="All checks passed — no fix needed.",
                        backup_path=None,
                    )
                )
                session.final_status = "healed"
                break

            # Build and apply fix
            source = path.read_text(encoding="utf-8", errors="ignore")
            prompt = self._build_llm_prompt(path, source, check_results)
            fixed_code = await self.query_llm_for_fix(prompt)

            if not fixed_code:
                session.iterations.append(
                    HealingIteration(
                        iteration=iteration,
                        check_results=check_results,
                        fix_applied=False,
                        fix_description="LLM returned empty fix.",
                        backup_path=None,
                        error="LLM produced no fix",
                    )
                )
                session.final_status = "failed"
                break

            backup_path = None
            if self.config.backup_before_fix:
                backup_path = self._backup_file(path)

            path.write_text(fixed_code, encoding="utf-8")

            session.iterations.append(
                HealingIteration(
                    iteration=iteration,
                    check_results=check_results,
                    fix_applied=True,
                    fix_description=f"Applied LLM fix (iteration {iteration})",
                    backup_path=str(backup_path) if backup_path else None,
                )
            )

            # Re-check immediately in next loop iteration
        else:
            session.final_status = "max_iterations"

        session.total_duration_ms = (time.time() - t0_total) * 1000
        session.finished_at = self._now_pst()
        return session

    async def heal_directory(self, directory: Path) -> List[HealingSession]:
        """
        ELI5: Patrol an entire floor and test every outlet.
        """
        sessions: List[HealingSession] = []
        for ext in self.config.allowed_extensions:
            for file_path in directory.rglob(f"*{ext}"):
                if ".venv" in str(file_path) or "node_modules" in str(file_path):
                    continue
                session = await self.heal_file(file_path)
                sessions.append(session)
        return sessions

    def get_session(self, session_id: str) -> Optional[HealingSession]:
        """
        ELI5: Pull the maintenance log from the filing cabinet.
        """
        return self._sessions.get(session_id)
