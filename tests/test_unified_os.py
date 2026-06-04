#!/usr/bin/env python3
"""
test_unified_os.py
==================
Unit tests for the OS Interface module.

ELI5: Before trusting the robotic arms to flip switches, we verify
      they understand room boundaries and won't punch through walls.
"""

from __future__ import annotations

import pytest

from core.unified.os_interface import OSInterface, OSActionResult, OSScreenInfo
from core.unified.config import OSInterfaceConfig


class TestOSActionResult:
    def test_result_creation(self) -> None:
        """ELI5: Can we write a proper work order receipt?"""
        result = OSActionResult(
            success=True,
            action="click",
            message="Clicked (100, 200)",
            coordinates=(100, 200),
        )
        assert result.success is True
        assert result.action == "click"
        assert result.coordinates == (100, 200)
        assert result.metadata == {}

    def test_result_to_dict(self) -> None:
        """ELI5: Can the receipt be copied into the logbook?"""
        result = OSActionResult(
            success=False,
            action="type",
            message="Failed",
            metadata={"length": 5},
        )
        d = result.to_dict()
        assert d["success"] is False
        assert d["metadata"]["length"] == 5


class TestOSInterface:
    def test_interface_creation(self) -> None:
        """ELI5: Can we power on the smart home hub?"""
        iface = OSInterface(config=OSInterfaceConfig())
        assert iface.config.typing_interval == 0.01

    def test_clamp_coords_with_known_screen(self) -> None:
        """ELI5: If the robot is told to walk to (9999, 9999),
              does it stop at the building's walls?"""
        iface = OSInterface()
        iface._screen = OSScreenInfo(width=1920, height=1080)
        x, y = iface._clamp_coords(5000, 5000)
        assert x < 5000
        assert y < 5000
        assert x <= 1920 - iface.config.screen_boundary_padding
        assert y <= 1080 - iface.config.screen_boundary_padding

    def test_clamp_coords_negative(self) -> None:
        """ELI5: Negative coordinates should snap to the nearest wall."""
        iface = OSInterface()
        iface._screen = OSScreenInfo(width=1920, height=1080)
        x, y = iface._clamp_coords(-100, -50)
        assert x >= iface.config.screen_boundary_padding
        assert y >= iface.config.screen_boundary_padding

    @pytest.mark.asyncio
    async def test_get_screen_size_cached(self) -> None:
        """ELI5: After measuring the lobby once, we shouldn't need a tape measure again."""
        pytest.importorskip("pyautogui")
        iface = OSInterface()
        iface._screen = OSScreenInfo(width=1920, height=1080)
        size = await iface.get_screen_size()
        assert size.width == 1920
        assert size.height == 1080
