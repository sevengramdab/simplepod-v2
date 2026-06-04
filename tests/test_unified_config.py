#!/usr/bin/env python3
"""
test_unified_config.py
======================
Unit tests for the Unified configuration module.

ELI5: Before we wire up the whole building, we test every breaker
      label to make sure the amperage ratings are correct.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.unified.config import (
    UnifiedConfig,
    VisionConfig,
    OSInterfaceConfig,
    SelfHealingConfig,
    SwarmConfig,
    DeploymentMode,
    WorkerRole,
)


class TestUnifiedConfig:
    def test_default_config_creation(self) -> None:
        """ELI5: Make sure the main electrical permit has all required fields."""
        cfg = UnifiedConfig()
        assert cfg.project_dir == "."
        assert cfg.log_level == "INFO"
        assert cfg.trace_id is None

    def test_active_backup_dir_fallback(self, tmp_path: Path) -> None:
        """
        ELI5: If the off-site archive is locked, we should fall back
              to the local filing cabinet.
        """
        cfg = UnifiedConfig(ark_backup_dir=str(tmp_path / "nonexistent"))
        active = cfg.active_backup_dir
        assert active.exists()
        assert active.name == "ark_backups"


class TestVisionConfig:
    def test_defaults(self) -> None:
        """ELI5: Check the security camera spec sheet defaults."""
        cfg = VisionConfig()
        assert cfg.template_match_threshold == 0.75
        assert cfg.contour_min_area == 100
        assert cfg.use_onnx is False
        assert cfg.use_ocr is False


class TestOSInterfaceConfig:
    def test_defaults(self) -> None:
        """ELI5: Check the smart home hub default settings."""
        cfg = OSInterfaceConfig()
        assert cfg.typing_interval == 0.01
        assert cfg.click_duration == 0.1
        assert cfg.screen_boundary_padding == 5


class TestSelfHealingConfig:
    def test_defaults(self) -> None:
        """ELI5: Check the smart breaker reset settings."""
        cfg = SelfHealingConfig()
        assert cfg.max_iterations == 5
        assert cfg.backup_before_fix is True
        assert cfg.sandbox_only is True
        assert ".py" in cfg.allowed_extensions


class TestSwarmConfig:
    def test_defaults(self) -> None:
        """ELI5: Check the 20-gang box specifications."""
        cfg = SwarmConfig()
        assert cfg.max_workers == 20
        assert cfg.task_timeout == 30.0
        assert cfg.heartbeat_interval == 5.0
        assert cfg.enable_auto_restart is True


class TestEnums:
    def test_deployment_mode_values(self) -> None:
        """ELI5: Make sure we have all three building types on the permit."""
        assert DeploymentMode.SINGLE == "single"
        assert DeploymentMode.MULTI_GPU == "multi_gpu"
        assert DeploymentMode.CLUSTER == "cluster"

    def test_worker_role_coverage(self) -> None:
        """ELI5: Count the number of job descriptions in the guard manual."""
        roles = list(WorkerRole)
        assert len(roles) == 20
