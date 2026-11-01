"""
Verification test for Phase 2: Set-of-Marks (SoM) Visual Grounding in Zenith
Validates visual element detection, badge generation, coordinate snapping,
and exact target resolution for 100% precision computer use.
"""

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

import time
from PIL import Image, ImageDraw
from agent_tools.som_grounding import (
    generate_set_of_marks,
    format_marks_for_prompt,
    resolve_action_target,
    MarkInfo
)


def run_som_verification():
    print("=" * 65)
    print("🎯 ZENITH PHASE 2 VERIFICATION: SET-OF-MARKS (SoM) GROUNDING")
    print("=" * 65)

    # 1. Create a simulated realistic desktop UI surface
    print("\n[*] Step 1: Synthesizing Realistic 1280x720 Application Canvas...")
    canvas = Image.new("RGB", (1280, 720), color=(28, 28, 30))
    draw = ImageDraw.Draw(canvas)

    # UI Components
    # 1. Search Bar at (100, 30) -> (600, 75)
    draw.rectangle([100, 30, 600, 75], fill=(44, 44, 46), outline=(99, 99, 102), width=2)
    # 2. Search Button at (610, 30) -> (710, 75)
    draw.rectangle([610, 30, 710, 75], fill=(0, 122, 255), outline=(255, 255, 255), width=2)
    # 3. Settings Button at (720, 30) -> (820, 75)
    draw.rectangle([720, 30, 820, 75], fill=(58, 58, 60), outline=(255, 255, 255), width=2)
    # 4. Action Card / Form Input at (150, 180) -> (450, 240)
    draw.rectangle([150, 180, 450, 240], fill=(44, 44, 46), outline=(99, 99, 102), width=2)
    # 5. Submit Button at (150, 260) -> (300, 310)
    draw.rectangle([150, 260, 300, 310], fill=(48, 209, 88), outline=(255, 255, 255), width=2)

    print("    ✅ Canvas created with 5 interactive UI components.")

    # 2. Execute Set-of-Marks Generation
    print("\n[*] Step 2: Running Set-of-Marks Detection & Overlay Pipeline...")
    t0 = time.time()
    annotated_img, mark_map = generate_set_of_marks(canvas, max_marks=20)
    proc_time_ms = (time.time() - t0) * 1000
    print(f"    ✅ Generated {len(mark_map)} Set-of-Marks badges in {proc_time_ms:.2f}ms.")
    assert len(mark_map) >= 4, f"Expected at least 4 marks, got {len(mark_map)}"

    # 3. Validate Mark Details
    print("\n[*] Step 3: Inspecting Detected Marks:")
    for mid, mark in mark_map.items():
        print(f"    - Mark [{mark.mark_id}] ({mark.control_type}): Center=({mark.center_x}, {mark.center_y}) Bounds={mark.rect}")
        assert mark.center_x > 0 and mark.center_y > 0

    # 4. Validate Prompt Generation
    print("\n[*] Step 4: Formatting Set-of-Marks Context for LLM:")
    prompt_snippet = format_marks_for_prompt(mark_map)
    print("    --------------------------------------------------")
    for line in prompt_snippet.split("\n")[:6]:
        print(f"    {line}")
    print("    --------------------------------------------------")
    assert "Set-of-Marks (SoM)" in prompt_snippet

    # 5. Validate Resolution by Mark ID (100% precision)
    print("\n[*] Step 5: Testing Exact Target Resolution by mark_id...")
    test_action = {"action": "left_click", "mark_id": 2, "reasoning": "Click search button"}
    resolved_target = resolve_action_target(test_action, mark_map)
    expected_target = mark_map[2].center
    print(f"    ✅ Action mark_id:2 -> Target: {resolved_target} (Expected: {expected_target})")
    assert resolved_target == expected_target

    # 6. Validate Proximity Snapping (Correcting coordinate drift)
    print("\n[*] Step 6: Testing Coordinate Snapping (Fixing DPI & Human Offset)...")
    # Mark 2 center is approximately (660, 52). Simulating a drifting coordinate at (675, 60):
    drifted_coord = (mark_map[2].center_x + 15, mark_map[2].center_y + 8)
    snap_action = {"action": "left_click", "coordinate": list(drifted_coord)}
    snapped_target = resolve_action_target(snap_action, mark_map, snap_distance=40)
    print(f"    ✅ Drifting Coordinate {drifted_coord} -> Snapped to: {snapped_target}")
    assert snapped_target == expected_target

    print("\n" + "=" * 65)
    print("🎉 PHASE 2 VERIFICATION COMPLETE: ALL CHECKS PASSED!")
    print("=" * 65)


if __name__ == "__main__":
    run_som_verification()
