#!/usr/bin/env python3
"""
core/unified/os_interface.py
============================
Native OS-Level Integration — Synthetic keyboard and mouse inputs.

ELI5: Think of this like a programmable smart home remote.
      It can press light switches, turn dimmers, and open blinds
      exactly as if a person walked up and did it by hand.
      Every button press is logged and validated so we don't
      accidentally flip the wrong breaker.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

# ELI5: Check if the smart remote has batteries before we try to use it.
try:
    import pyautogui

    _PYAUTOGUI_OK = True
except Exception:
    pyautogui = None  # type: ignore
    _PYAUTOGUI_OK = False

try:
    from PIL import Image

    _PIL_OK = True
except Exception:
    Image = None  # type: ignore
    _PIL_OK = False

from .config import OSInterfaceConfig

logger = logging.getLogger("simplepod.unified.os")


@dataclass
class OSScreenInfo:
    """
    ELI5: Like the building's floor plan dimensions.
          We need to know the walls before we tell the robot
          where to walk, so it doesn't crash into anything.
    """

    width: int
    height: int


@dataclass
class OSActionResult:
    """
    ELI5: The work order receipt after the maintenance tech
          finishes a job. Did they succeed? What did they touch?
    """

    success: bool
    action: str
    message: str
    coordinates: Optional[Tuple[int, int]] = None
    metadata: Dict[str, Any] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "action": self.action,
            "message": self.message,
            "coordinates": self.coordinates,
            "metadata": self.metadata,
        }


class OSInterface:
    """
    ELI5: The central smart-home hub that translates software commands
          into physical switch flips. It knows every room's layout
          and refuses to send the robot into a wall.
    """

    def __init__(self, config: Optional[OSInterfaceConfig] = None) -> None:
        self.config = config or OSInterfaceConfig()
        self._screen: Optional[OSScreenInfo] = None

        if _PYAUTOGUI_OK:
            # ELI5: Set the emergency stop so if the robot goes crazy,
            #       moving the mouse to a corner shuts it down instantly.
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.05

    def _check_pyautogui(self) -> None:
        if not _PYAUTOGUI_OK:
            raise RuntimeError(
                "pyautogui is not installed or failed to load. "
                "OS-level input simulation is unavailable."
            )

    async def _run_in_executor(self, fn: Any, *args: Any) -> Any:
        """
        ELI5: The smart remote runs on a separate frequency so it
              doesn't jam the main walkie-talkie channel.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, fn, *args)

    async def get_screen_size(self) -> OSScreenInfo:
        """
        ELI5: Measure the lobby before sending in the cleaning crew.
        """
        if self._screen is not None:
            return self._screen

        self._check_pyautogui()
        size = await self._run_in_executor(pyautogui.size)
        self._screen = OSScreenInfo(width=size.width, height=size.height)
        return self._screen

    def _clamp_coords(self, x: int, y: int) -> Tuple[int, int]:
        """
        ELI5: If the robot's GPS says 'walk to coordinate 9999',
              we clamp it to the building's actual walls so it
              doesn't walk off the property.
        """
        if self._screen is None:
            # Fallback: assume standard 1080p if screen not probed yet
            max_x, max_y = 1920, 1080
        else:
            max_x, max_y = self._screen.width, self._screen.height

        pad = self.config.screen_boundary_padding
        clamped_x = max(pad, min(x, max_x - pad))
        clamped_y = max(pad, min(y, max_y - pad))
        return clamped_x, clamped_y

    async def move_to(self, x: int, y: int) -> OSActionResult:
        """
        ELI5: Tell the robot to walk to a specific spot in the lobby.
        """
        self._check_pyautogui()
        await self.get_screen_size()
        cx, cy = self._clamp_coords(x, y)

        try:
            await self._run_in_executor(
                pyautogui.moveTo, cx, cy, duration=self.config.movement_duration
            )
            return OSActionResult(
                success=True,
                action="move_to",
                message=f"Moved mouse to ({cx}, {cy})",
                coordinates=(cx, cy),
            )
        except Exception as exc:
            logger.exception("move_to failed")
            return OSActionResult(
                success=False,
                action="move_to",
                message=f"Failed: {exc}",
                coordinates=(cx, cy),
            )

    async def click(
        self,
        x: int,
        y: int,
        button: str = "left",
        clicks: int = 1,
    ) -> OSActionResult:
        """
        ELI5: The robot walks up to a light switch and flips it.
        """
        self._check_pyautogui()
        await self.get_screen_size()
        cx, cy = self._clamp_coords(x, y)

        try:
            await self._run_in_executor(
                pyautogui.click, cx, cy, clicks=clicks, button=button
            )
            return OSActionResult(
                success=True,
                action="click",
                message=f"Clicked ({cx}, {cy}) {clicks}x with {button} button",
                coordinates=(cx, cy),
                metadata={"button": button, "clicks": clicks},
            )
        except Exception as exc:
            logger.exception("click failed")
            return OSActionResult(
                success=False,
                action="click",
                message=f"Failed: {exc}",
                coordinates=(cx, cy),
            )

    async def double_click(self, x: int, y: int) -> OSActionResult:
        """
        ELI5: Double-tap the light switch — like a dimmer's double-tap
              to go to full brightness.
        """
        return await self.click(x, y, button="left", clicks=2)

    async def right_click(self, x: int, y: int) -> OSActionResult:
        """
        ELI5: Right-click is like opening the panel's hidden menu
              to see advanced settings.
        """
        return await self.click(x, y, button="right", clicks=1)

    async def drag(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        button: str = "left",
    ) -> OSActionResult:
        """
        ELI5: The robot grabs a sliding dimmer switch at position A
              and drags it smoothly to position B.
        """
        self._check_pyautogui()
        await self.get_screen_size()
        cx1, cy1 = self._clamp_coords(x1, y1)
        cx2, cy2 = self._clamp_coords(x2, y2)

        try:
            await self._run_in_executor(pyautogui.moveTo, cx1, cy1)
            await self._run_in_executor(
                pyautogui.dragTo, cx2, cy2, duration=self.config.drag_duration, button=button
            )
            return OSActionResult(
                success=True,
                action="drag",
                message=f"Dragged from ({cx1}, {cy1}) to ({cx2}, {cy2})",
                coordinates=(cx2, cy2),
                metadata={"start": (cx1, cy1), "button": button},
            )
        except Exception as exc:
            logger.exception("drag failed")
            return OSActionResult(
                success=False,
                action="drag",
                message=f"Failed: {exc}",
                coordinates=(cx2, cy2),
            )

    async def scroll(self, clicks: int, x: Optional[int] = None, y: Optional[int] = None) -> OSActionResult:
        """
        ELI5: Spin the scroll wheel on a smart thermostat
              to adjust the temperature up or down.
        """
        self._check_pyautogui()

        try:
            if x is not None and y is not None:
                await self.get_screen_size()
                cx, cy = self._clamp_coords(x, y)
                await self._run_in_executor(pyautogui.moveTo, cx, cy)

            await self._run_in_executor(pyautogui.scroll, clicks)
            return OSActionResult(
                success=True,
                action="scroll",
                message=f"Scrolled {clicks} clicks",
                coordinates=(x, y) if x is not None and y is not None else None,
                metadata={"clicks": clicks},
            )
        except Exception as exc:
            logger.exception("scroll failed")
            return OSActionResult(
                success=False,
                action="scroll",
                message=f"Failed: {exc}",
            )

    async def type_text(self, text: str, interval: Optional[float] = None) -> OSActionResult:
        """
        ELI5: The robot types a memo into the building's intercom
              system, one character at a time, so it doesn't jam.
        """
        self._check_pyautogui()
        iv = interval if interval is not None else self.config.typing_interval

        try:
            await self._run_in_executor(pyautogui.typewrite, text, interval=iv)
            return OSActionResult(
                success=True,
                action="type_text",
                message=f"Typed {len(text)} characters",
                metadata={"length": len(text), "interval": iv},
            )
        except Exception as exc:
            logger.exception("type_text failed")
            return OSActionResult(
                success=False,
                action="type_text",
                message=f"Failed: {exc}",
            )

    async def send_hotkey(self, *keys: str) -> OSActionResult:
        """
        ELI5: Press multiple buttons at once — like holding 'Ctrl' while
              pressing 'C' to copy a document on the copier machine.
        """
        self._check_pyautogui()

        try:
            await self._run_in_executor(pyautogui.hotkey, *keys)
            return OSActionResult(
                success=True,
                action="send_hotkey",
                message=f"Sent hotkey: {'+'.join(keys)}",
                metadata={"keys": list(keys)},
            )
        except Exception as exc:
            logger.exception("send_hotkey failed")
            return OSActionResult(
                success=False,
                action="send_hotkey",
                message=f"Failed: {exc}",
            )

    async def press_key(self, key: str) -> OSActionResult:
        """
        ELI5: Press a single button — like the 'Door Open' button
              on the elevator panel.
        """
        self._check_pyautogui()

        try:
            await self._run_in_executor(pyautogui.press, key)
            return OSActionResult(
                success=True,
                action="press_key",
                message=f"Pressed key: {key}",
                metadata={"key": key},
            )
        except Exception as exc:
            logger.exception("press_key failed")
            return OSActionResult(
                success=False,
                action="press_key",
                message=f"Failed: {exc}",
            )

    async def screenshot(self) -> OSActionResult:
        """
        ELI5: Take a photo of the entire lobby for the security log.
        """
        self._check_pyautogui()

        try:
            img = await self._run_in_executor(pyautogui.screenshot)
            return OSActionResult(
                success=True,
                action="screenshot",
                message=f"Screenshot captured: {img.size}",
                metadata={"size": img.size},
            )
        except Exception as exc:
            logger.exception("screenshot failed")
            return OSActionResult(
                success=False,
                action="screenshot",
                message=f"Failed: {exc}",
            )
