#!/usr/bin/env python3
"""
test_unified_vision.py
======================
Unit tests for the Vision Engine.

ELI5: Before trusting the security cameras, we test them with
      a staged photo of the lobby where we already know where
      every chair and person should be.
"""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

import pytest

from core.unified.vision_engine import VisionEngine, VisionResult, UIElement, ElementType
from core.unified.config import VisionConfig


class TestUIElement:
    def test_element_creation(self) -> None:
        """ELI5: Can we log a single person spotted in the lobby?"""
        elem = UIElement(
            element_id="btn_01",
            element_type=ElementType.BUTTON,
            bbox=(100, 200, 50, 30),
            center=(125, 215),
            confidence=0.95,
            detected_text="OK",
        )
        assert elem.element_id == "btn_01"
        assert elem.center == (125, 215)
        assert elem.confidence == 0.95

    def test_element_to_dict(self) -> None:
        """ELI5: Can the sighting be serialized for evidence?"""
        elem = UIElement(
            element_id="inp_01",
            element_type=ElementType.TEXT_INPUT,
            bbox=(10, 10, 200, 40),
            center=(110, 30),
            confidence=0.88,
        )
        d = elem.to_dict()
        assert d["element_type"] == "text_input"
        assert d["confidence"] == 0.88


class TestVisionResult:
    def test_find_by_type(self) -> None:
        """ELI5: Filter the security report for only employees."""
        result = VisionResult(
            success=True,
            width=1920,
            height=1080,
            elements=[
                UIElement("b1", ElementType.BUTTON, (0, 0, 10, 10), (5, 5), 0.9),
                UIElement("i1", ElementType.ICON, (20, 20, 10, 10), (25, 25), 0.8),
                UIElement("b2", ElementType.BUTTON, (40, 40, 10, 10), (45, 45), 0.7),
            ],
        )
        buttons = result.find_by_type(ElementType.BUTTON)
        assert len(buttons) == 2

    def test_find_by_text(self) -> None:
        """ELI5: Search the guest list for 'Smith'."""
        result = VisionResult(
            success=True,
            width=1920,
            height=1080,
            elements=[
                UIElement("b1", ElementType.BUTTON, (0, 0, 10, 10), (5, 5), 0.9, "Submit"),
                UIElement("b2", ElementType.BUTTON, (20, 20, 10, 10), (25, 25), 0.8, "Cancel"),
            ],
        )
        matches = result.find_by_text("sub")
        assert len(matches) == 1
        assert matches[0].detected_text == "Submit"

    def test_find_at_position(self) -> None:
        """ELI5: Who is standing at coordinates (25, 25)?"""
        result = VisionResult(
            success=True,
            width=1920,
            height=1080,
            elements=[
                UIElement("b1", ElementType.BUTTON, (0, 0, 10, 10), (5, 5), 0.9),
                UIElement("i1", ElementType.ICON, (20, 20, 10, 10), (25, 25), 0.8),
            ],
        )
        found = result.find_at_position(25, 25)
        assert found is not None
        assert found.element_id == "i1"


class TestVisionEngine:
    def test_engine_creation(self) -> None:
        """ELI5: Can we power on the security camera system?"""
        engine = VisionEngine(config=VisionConfig())
        assert engine.config.template_match_threshold == 0.75

    def test_detect_contours_mock(self) -> None:
        """ELI5: Test the AI person-detector with a blank canvas."""
        pytest.importorskip("cv2")
        pytest.importorskip("numpy")
        import numpy as np
        import cv2

        engine = VisionEngine(config=VisionConfig(contour_min_area=50))
        # Create a synthetic image with one white rectangle on black background
        img = np.zeros((200, 200, 3), dtype=np.uint8)
        cv2.rectangle(img, (50, 50), (100, 100), (255, 255, 255), -1)
        elements = engine.detect_contours(img)
        # Should find at least one contour
        assert len(elements) >= 1

    def test_deduplicate_elements(self) -> None:
        """ELI5: Two guards report the same person — merge into one."""
        engine = VisionEngine()
        elements = [
            UIElement("a", ElementType.BUTTON, (0, 0, 10, 10), (5, 5), 0.9),
            UIElement("b", ElementType.BUTTON, (3, 3, 10, 10), (8, 8), 0.8),
            UIElement("c", ElementType.BUTTON, (100, 100, 10, 10), (105, 105), 0.7),
        ]
        deduped = engine._deduplicate_elements(elements, min_distance=20)
        # a and b are too close (distance ~4.2), so one should be removed
        assert len(deduped) == 2
