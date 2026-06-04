#!/usr/bin/env python3
"""
core/unified/vision_engine.py
=============================
Optical State Parsing — Computer Vision module for UI element detection.

ELI5: Think of this like a security camera with AI person-detection.
      It watches the screen (the building lobby), spots the buttons
      and text boxes (people and furniture), and tells the security
      guard exactly where each one is standing so he can walk up
      and interact with them.
"""

from __future__ import annotations

import asyncio
import base64
import io
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# ELI5: Like checking if the camera DVR is plugged in before you try
#       to record. If it's missing, we still patrol the lobby manually.
try:
    import cv2
    import numpy as np

    _CV2_OK = True
except Exception:
    cv2 = None  # type: ignore
    np = None  # type: ignore
    _CV2_OK = False

try:
    from PIL import Image

    _PIL_OK = True
except Exception:
    Image = None  # type: ignore
    _PIL_OK = False

try:
    import pyautogui

    _PYAUTOGUI_OK = True
except Exception:
    pyautogui = None  # type: ignore
    _PYAUTOGUI_OK = False

try:
    import onnxruntime as ort

    _ONNX_OK = True
except Exception:
    ort = None  # type: ignore
    _ONNX_OK = False

from .config import VisionConfig

logger = logging.getLogger("simplepod.unified.vision")


class ElementType(str, Enum):
    """
    ELI5: Like the legend on a floor plan.
          A circle might be a light fixture, a square an outlet.
    """

    BUTTON = "button"
    TEXT_INPUT = "text_input"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    DROPDOWN = "dropdown"
    LINK = "link"
    ICON = "icon"
    SCROLLBAR = "scrollbar"
    WINDOW = "window"
    UNKNOWN = "unknown"


@dataclass
class UIElement:
    """
    ELI5: A single person spotted by the security camera.
          We note their exact position, how confident we are it's them,
          and what they're wearing (so we know if they're staff or visitor).
    """

    element_id: str
    element_type: ElementType
    bbox: Tuple[int, int, int, int]  # x, y, w, h
    center: Tuple[int, int]
    confidence: float
    detected_text: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "element_id": self.element_id,
            "element_type": self.element_type.value,
            "bbox": self.bbox,
            "center": self.center,
            "confidence": round(self.confidence, 4),
            "detected_text": self.detected_text,
            "metadata": self.metadata,
        }


@dataclass
class VisionResult:
    """
    ELI5: The full security report after scanning the lobby.
          How many people, where they are, and a photo for evidence.
    """

    success: bool
    width: int
    height: int
    elements: List[UIElement]
    raw_image_base64: Optional[str] = None
    error: Optional[str] = None
    processing_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "width": self.width,
            "height": self.height,
            "elements": [e.to_dict() for e in self.elements],
            "raw_image_base64": self.raw_image_base64,
            "error": self.error,
            "processing_time_ms": round(self.processing_time_ms, 2),
        }

    def find_by_type(self, element_type: ElementType) -> List[UIElement]:
        """
        ELI5: Filter the security report to show only employees,
              or only visitors, depending on what you're looking for.
        """
        return [e for e in self.elements if e.element_type == element_type]

    def find_by_text(self, text: str) -> List[UIElement]:
        """
        ELI5: Search the guest list for a specific name.
        """
        return [
            e
            for e in self.elements
            if e.detected_text and text.lower() in e.detected_text.lower()
        ]

    def find_at_position(self, x: int, y: int, tolerance: int = 10) -> Optional[UIElement]:
        """
        ELI5: Given GPS coordinates, find who is standing there.
        """
        for e in self.elements:
            cx, cy = e.center
            if abs(cx - x) <= tolerance and abs(cy - y) <= tolerance:
                return e
        return None


class VisionEngine:
    """
    ELI5: The security camera control room.
          It can take photos of the screen, analyze them for people
          and objects, and hand the report to the guard desk.
    """

    def __init__(self, config: Optional[VisionConfig] = None) -> None:
        self.config = config or VisionConfig()
        self._onnx_session: Optional[Any] = None
        self._ocr_reader: Optional[Any] = None

        if _ONNX_OK and self.config.use_onnx and self.config.onnx_model_path:
            try:
                self._onnx_session = ort.InferenceSession(self.config.onnx_model_path)
                logger.info("ONNX Runtime loaded: %s", self.config.onnx_model_path)
            except Exception as exc:
                logger.warning("Failed to load ONNX model: %s", exc)

        if self.config.use_ocr:
            try:
                import easyocr

                self._ocr_reader = easyocr.Reader(self.config.ocr_languages)
                logger.info("OCR reader loaded for languages: %s", self.config.ocr_languages)
            except Exception as exc:
                logger.warning("Failed to load OCR: %s", exc)

    def _check_cv2(self) -> None:
        if not _CV2_OK:
            raise RuntimeError(
                "OpenCV (cv2) is required for vision operations. "
                "Install with: pip install opencv-python-headless"
            )

    async def capture_screen(
        self,
        region: Optional[Tuple[int, int, int, int]] = None,
    ) -> Image.Image:
        """
        ELI5: Snap a photo of the entire lobby, or just one corner
              if you specify the region.
        """
        if not _PYAUTOGUI_OK:
            raise RuntimeError("pyautogui not available for screenshot capture")

        loop = asyncio.get_event_loop()
        img = await loop.run_in_executor(None, pyautogui.screenshot, region)
        return img

    async def capture_screen_base64(
        self,
        region: Optional[Tuple[int, int, int, int]] = None,
    ) -> str:
        """
        ELI5: Same photo, but we encode it as a data string so it can
              travel over the radio to the main office.
        """
        img = await self.capture_screen(region)
        buffer = io.BytesIO()
        img.save(buffer, format=self.config.screenshot_format, quality=self.config.screenshot_quality)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    def _pil_to_cv2(self, img: Image.Image) -> Any:
        """
        ELI5: Convert the photo from the security camera's format
              to the format the AI analysis software expects.
        """
        self._check_cv2()
        rgb = img.convert("RGB")
        arr = np.array(rgb)
        return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

    def _cv2_to_pil(self, arr: Any) -> Image.Image:
        """
        ELI5: Convert back from AI analysis format to a normal photo.
        """
        rgb = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb)

    def detect_contours(self, cv_img: Any) -> List[UIElement]:
        """
        ELI5: Look at the photo and draw boxes around every distinct
              object — chairs, desks, monitors — so we know where they are.
        """
        self._check_cv2()
        elements: List[UIElement] = []
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for idx, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            if area < self.config.contour_min_area or area > self.config.contour_max_area:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            aspect = w / h if h > 0 else 1.0

            # Heuristic classification based on aspect ratio and size
            element_type = ElementType.UNKNOWN
            if 0.9 <= aspect <= 1.1 and area < 5000:
                element_type = ElementType.ICON
            elif aspect > 2.5 and h < 50:
                element_type = ElementType.TEXT_INPUT
            elif 0.8 <= aspect <= 3.0 and area > 2000:
                element_type = ElementType.BUTTON
            elif aspect > 3.0 and h < 40:
                element_type = ElementType.LINK

            elem = UIElement(
                element_id=f"contour_{idx}",
                element_type=element_type,
                bbox=(x, y, w, h),
                center=(x + w // 2, y + h // 2),
                confidence=min(1.0, area / 10000),
                metadata={"area": area, "aspect_ratio": round(aspect, 2)},
            )
            elements.append(elem)

        return elements

    def template_match(
        self,
        cv_img: Any,
        template_path: Union[str, Path],
        threshold: Optional[float] = None,
    ) -> List[UIElement]:
        """
        ELI5: We have a photo of a specific person (the template).
              Scan the entire lobby to find every place that person
              is standing. Return their coordinates.
        """
        self._check_cv2()
        tpl_path = Path(template_path)
        if not tpl_path.exists():
            logger.warning("Template not found: %s", tpl_path)
            return []

        template = cv2.imread(str(tpl_path), cv2.IMREAD_COLOR)
        if template is None:
            logger.warning("Failed to load template: %s", tpl_path)
            return []

        h, w = template.shape[:2]
        result = cv2.matchTemplate(cv_img, template, cv2.TM_CCOEFF_NORMED)
        thresh = threshold if threshold is not None else self.config.template_match_threshold
        loc = np.where(result >= thresh)

        elements: List[UIElement] = []
        for idx, (y, x) in enumerate(zip(*loc)):
            conf = float(result[y, x])
            elem = UIElement(
                element_id=f"template_{idx}",
                element_type=ElementType.UNKNOWN,
                bbox=(x, y, w, h),
                center=(x + w // 2, y + h // 2),
                confidence=conf,
                metadata={"template": str(tpl_path), "match_method": "TM_CCOEFF_NORMED"},
            )
            elements.append(elem)

        return elements

    def run_ocr(self, cv_img: Any) -> List[UIElement]:
        """
        ELI5: Read every name tag in the lobby photo.
              Return who is standing where and what their name is.
        """
        if self._ocr_reader is None:
            return []

        rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        results = self._ocr_reader.readtext(rgb)
        elements: List[UIElement] = []
        for idx, (bbox, text, conf) in enumerate(results):
            pts = [(int(p[0]), int(p[1])) for p in bbox]
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            x, y, w, h = min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)
            elem = UIElement(
                element_id=f"ocr_{idx}",
                element_type=ElementType.TEXT_INPUT,
                bbox=(x, y, w, h),
                center=(x + w // 2, y + h // 2),
                confidence=conf,
                detected_text=text,
                metadata={"ocr_confidence": round(conf, 4)},
            )
            elements.append(elem)
        return elements

    async def analyze_screen(
        self,
        region: Optional[Tuple[int, int, int, int]] = None,
        templates: Optional[List[Union[str, Path]]] = None,
    ) -> VisionResult:
        """
        ELI5: The full security sweep of the lobby.
              Take a photo, find all objects, read all name tags,
              and compile the complete incident report.
        """
        import time as time_mod

        t0 = time_mod.time()

        if not _CV2_OK:
            return VisionResult(
                success=False,
                width=0,
                height=0,
                elements=[],
                error="OpenCV not available. Install opencv-python-headless.",
            )

        try:
            pil_img = await self.capture_screen(region)
            cv_img = self._pil_to_cv2(pil_img)
            h, w = cv_img.shape[:2]

            all_elements: List[UIElement] = []

            # Contour detection
            all_elements.extend(self.detect_contours(cv_img))

            # Template matching
            if templates:
                for tpl in templates:
                    all_elements.extend(self.template_match(cv_img, tpl))

            # OCR
            if self.config.use_ocr:
                all_elements.extend(self.run_ocr(cv_img))

            # Deduplicate by center proximity
            deduped = self._deduplicate_elements(all_elements)

            # Encode raw image
            buffer = io.BytesIO()
            pil_img.save(buffer, format=self.config.screenshot_format)
            b64_img = base64.b64encode(buffer.getvalue()).decode("utf-8")

            elapsed = (time_mod.time() - t0) * 1000
            return VisionResult(
                success=True,
                width=w,
                height=h,
                elements=deduped,
                raw_image_base64=b64_img,
                processing_time_ms=elapsed,
            )

        except Exception as exc:
            logger.exception("Vision analysis failed")
            return VisionResult(
                success=False,
                width=0,
                height=0,
                elements=[],
                error=str(exc),
            )

    def _deduplicate_elements(
        self,
        elements: List[UIElement],
        min_distance: int = 15,
    ) -> List[UIElement]:
        """
        ELI5: If two security guards report the same person standing
              in almost the same spot, it's probably one person, not two.
              We merge the duplicate reports.
        """
        if not elements:
            return []

        sorted_elems = sorted(elements, key=lambda e: e.confidence, reverse=True)
        kept: List[UIElement] = []
        for elem in sorted_elems:
            too_close = False
            for existing in kept:
                dx = elem.center[0] - existing.center[0]
                dy = elem.center[1] - existing.center[1]
                dist = (dx * dx + dy * dy) ** 0.5
                if dist < min_distance:
                    too_close = True
                    break
            if not too_close:
                kept.append(elem)
        return kept
