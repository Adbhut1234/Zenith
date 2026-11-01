"""
Set-of-Marks (SoM) Visual Grounding Engine for Zenith AI
Pioneered for frontier multimodal agents (GPT-6 Astra, OmniParser).
Overlays distinctive visual badges [1], [2], [3]... over clickable UI elements
and pairs them with exact pixel coordinates, eliminating coordinate hallucinations
and near-miss clicks across Windows applications.
"""

import io
import math
import logging
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Any
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import cv2

logger = logging.getLogger("zenith.som")

# High-contrast color palette for visual badges
PALETTE = [
    (0, 220, 255),    # Vibrant Cyan
    (255, 170, 0),    # Neon Amber
    (0, 255, 136),    # Emerald Neon
    (255, 77, 166),   # Bright Magenta
    (140, 102, 255),  # Violet
    (255, 221, 0)     # Canary Yellow
]


@dataclass
class MarkInfo:
    mark_id: int
    center_x: int
    center_y: int
    rect: Tuple[int, int, int, int]  # (left, top, right, bottom)
    label: str
    control_type: str

    @property
    def center(self) -> Tuple[int, int]:
        return (self.center_x, self.center_y)


def _compute_iou(boxA: Tuple[int, int, int, int], boxB: Tuple[int, int, int, int]) -> float:
    """Computes Intersection-over-Union (IoU) between two bounding boxes."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interArea = max(0, xB - xA) * max(0, yB - yA)
    boxAArea = max(1, (boxA[2] - boxA[0]) * (boxA[3] - boxA[1]))
    boxBArea = max(1, (boxB[2] - boxB[0]) * (boxB[3] - boxB[1]))

    return interArea / float(boxAArea + boxBArea - interArea)


def extract_uia_bounding_boxes(max_elements: int = 50) -> List[Dict[str, Any]]:
    """Extracts interactive bounding boxes directly from Windows UI Automation tree."""
    elements = []
    try:
        from pywinauto import Desktop
        desktop = Desktop(backend="uia")
        
        # Priority control types for interaction
        interactive_types = {
            "Button", "Edit", "MenuItem", "ListItem", "TabItem",
            "CheckBox", "RadioButton", "ComboBox", "Hyperlink", "TreeItem"
        }

        # Inspect top 6 visible active windows
        for w in desktop.windows()[:6]:
            try:
                if not w.is_visible() or not w.is_enabled():
                    continue
                w_rect = w.rectangle()
                if w_rect.width() < 100 or w_rect.height() < 100:
                    continue

                for ctrl in w.descendants():
                    try:
                        if not ctrl.is_visible() or not ctrl.is_enabled():
                            continue
                        ctype = ctrl.friendly_class_name()
                        if ctype in interactive_types:
                            r = ctrl.rectangle()
                            w_px = r.width()
                            h_px = r.height()
                            # Filter out microscopic controls or fullscreen wrappers
                            if 12 <= w_px <= 1600 and 10 <= h_px <= 600:
                                name = ctrl.window_text().strip()
                                elements.append({
                                    "rect": (r.left, r.top, r.right, r.bottom),
                                    "label": name or f"{ctype}",
                                    "type": ctype
                                })
                                if len(elements) >= max_elements * 2:
                                    break
                    except Exception:
                        continue
            except Exception:
                continue
    except Exception as e:
        logger.warning(f"UIA bounding box extraction error: {e}")

    return elements


def extract_visual_contour_boxes(screenshot_np: np.ndarray, max_boxes: int = 40) -> List[Dict[str, Any]]:
    """Fast computer vision detection of interactive buttons, icons, and text boxes using edge contours."""
    boxes = []
    try:
        gray = cv2.cvtColor(screenshot_np, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 30, 100)
        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        
        h_screen, w_screen = gray.shape
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            # Standard button / icon dimensions
            if 20 <= w <= 800 and 14 <= h <= 300:
                # Discard full-screen containers
                if w > w_screen * 0.9 or h > h_screen * 0.9:
                    continue
                boxes.append({
                    "rect": (x, y, x + w, y + h),
                    "label": f"Button/Element ({w}x{h})",
                    "type": "VisualElement"
                })
                if len(boxes) >= max_boxes * 4:
                    break
    except Exception as e:
        logger.warning(f"Visual contour detection error: {e}")

    return boxes


def generate_set_of_marks(screenshot: Image.Image, max_marks: int = 45) -> Tuple[Image.Image, Dict[int, MarkInfo]]:
    """
    Core Set-of-Marks (SoM) Generator.
    Extracts elements via hybrid UIA + CV, applies Non-Maximum Suppression,
    and returns (annotated_image, mark_map).
    """
    w_orig, h_orig = screenshot.size
    
    # 1. Gather candidates from UIA and Computer Vision
    raw_candidates = []
    
    # First: UIA accessibility elements (highest semantic quality)
    uia_elements = extract_uia_bounding_boxes(max_elements=max_marks)
    raw_candidates.extend(uia_elements)
    
    # Second: Computer vision contours (catches web/canvas/electron apps)
    if len(raw_candidates) < max_marks:
        np_img = np.array(screenshot.convert("RGB"))[:, :, ::-1] # RGB -> BGR
        cv_elements = extract_visual_contour_boxes(np_img, max_boxes=max_marks - len(raw_candidates))
        raw_candidates.extend(cv_elements)

    # 2. Non-Maximum Suppression (NMS) to eliminate duplicate/overlapping boxes
    filtered_boxes = []
    for cand in raw_candidates:
        r = cand["rect"]
        # Ensure within screen bounds
        rect_clean = (
            max(0, min(r[0], w_orig - 1)),
            max(0, min(r[1], h_orig - 1)),
            max(1, min(r[2], w_orig)),
            max(1, min(r[3], h_orig))
        )
        if (rect_clean[2] - rect_clean[0]) < 8 or (rect_clean[3] - rect_clean[1]) < 8:
            continue

        is_duplicate = False
        for existing in filtered_boxes:
            if _compute_iou(rect_clean, existing["rect"]) > 0.45:
                is_duplicate = True
                break
        if not is_duplicate:
            cand["rect"] = rect_clean
            filtered_boxes.append(cand)
            if len(filtered_boxes) >= max_marks:
                break

    # 3. Sort marks in natural reading order (top to bottom, left to right)
    filtered_boxes.sort(key=lambda b: (b["rect"][1] // 40, b["rect"][0]))

    # 4. Draw Set-of-Marks onto an image copy
    annotated = screenshot.copy().convert("RGBA")
    overlay = Image.new("RGBA", annotated.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    mark_map: Dict[int, MarkInfo] = {}

    for idx, cand in enumerate(filtered_boxes, start=1):
        color = PALETTE[(idx - 1) % len(PALETTE)]
        r = cand["rect"]
        l, t, r_x, b = r
        center_x = (l + r_x) // 2
        center_y = (t + b) // 2

        mark_info = MarkInfo(
            mark_id=idx,
            center_x=center_x,
            center_y=center_y,
            rect=r,
            label=cand["label"],
            control_type=cand["type"]
        )
        mark_map[idx] = mark_info

        # Draw semi-transparent bounding box outline
        draw.rectangle([l, t, r_x, b], outline=color + (220,), width=2)

        # Draw distinct badge pill for the number [idx]
        badge_text = f"[{idx}]"
        # Approximate font metrics
        badge_w = len(badge_text) * 8 + 8
        badge_h = 16
        
        badge_x0 = max(0, l)
        badge_y0 = max(0, t - badge_h)
        badge_x1 = badge_x0 + badge_w
        badge_y1 = badge_y0 + badge_h

        # Solid dark badge background with colored border
        draw.rounded_rectangle([badge_x0, badge_y0, badge_x1, badge_y1], radius=3, fill=(15, 15, 20, 240), outline=color, width=1)
        draw.text((badge_x0 + 4, badge_y0 + 1), badge_text, fill=color)

    # Composite overlay onto screenshot
    result_img = Image.alpha_composite(annotated, overlay).convert("RGB")
    return result_img, mark_map


def format_marks_for_prompt(mark_map: Dict[int, MarkInfo], max_items: int = 35) -> str:
    """Formats the detected marks as a structured dictionary for the AI prompt."""
    if not mark_map:
        return "No specific UI marks detected."

    lines = ["Available Set-of-Marks (SoM) on screen:"]
    for idx, m in list(mark_map.items())[:max_items]:
        clean_label = m.label[:30].strip() if m.label else m.control_type
        lines.append(f"  [{m.mark_id}] {m.control_type}: '{clean_label}' at ({m.center_x}, {m.center_y})")
    
    if len(mark_map) > max_items:
        lines.append(f"  ... and {len(mark_map) - max_items} more marks visible on screen.")
        
    return "\n".join(lines)


def resolve_action_target(action: Dict[str, Any], mark_map: Dict[int, MarkInfo], snap_distance: int = 35) -> Optional[Tuple[int, int]]:
    """
    Resolves the exact (x, y) pixel target from an AI action.
    Prioritizes explicit mark_id, then snaps close coordinates to marks, preventing near-misses.
    """
    # 1. Explicit mark_id takes absolute priority (100% precision)
    if "mark_id" in action and action["mark_id"] in mark_map:
        mark = mark_map[action["mark_id"]]
        logger.info(f"Target resolved by mark_id [{mark.mark_id}]: {mark.label} -> {mark.center}")
        return mark.center

    # 2. Coordinate snapping to closest mark within tolerance
    coord = action.get("coordinate")
    if coord and len(coord) == 2:
        cx, cy = int(coord[0]), int(coord[1])
        closest_mark = None
        closest_dist = float("inf")
        
        for mark in mark_map.values():
            dist = math.hypot(mark.center_x - cx, mark.center_y - cy)
            if dist < closest_dist:
                closest_dist = dist
                closest_mark = mark
                
        # Snap if within proximity tolerance
        if closest_mark and closest_dist <= snap_distance:
            logger.info(f"Coordinate ({cx}, {cy}) snapped to closest Mark [{closest_mark.mark_id}] ({closest_mark.center_x}, {closest_mark.center_y}) - distance {closest_dist:.1f}px")
            return closest_mark.center
            
        return (cx, cy)

    # 3. Label text match fallback
    elem_name = action.get("element_name", "").strip().lower()
    if elem_name:
        for mark in mark_map.values():
            if elem_name in mark.label.lower():
                logger.info(f"Target resolved by label text '{elem_name}' -> Mark [{mark.mark_id}] {mark.center}")
                return mark.center

    return None
