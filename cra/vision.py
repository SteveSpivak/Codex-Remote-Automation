from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Dict, Iterable, Sequence


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def ocr_helper_source_path() -> Path:
    return _repo_root() / "scripts" / "capture_codex_window_ocr.m"


def ocr_helper_binary_path() -> Path:
    return _repo_root() / "var" / "bin" / "capture_codex_window_ocr"


def click_helper_source_path() -> Path:
    return _repo_root() / "scripts" / "click_screen_point.m"


def click_helper_binary_path() -> Path:
    return _repo_root() / "var" / "bin" / "click_screen_point"


def _build_objc_helper(source_path: Path, binary_path: Path) -> Path:
    binary_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "/usr/bin/clang",
            "-fobjc-arc",
            str(source_path),
            "-framework",
            "AppKit",
            "-framework",
            "CoreGraphics",
            "-framework",
            "Foundation",
            "-framework",
            "ImageIO",
            "-framework",
            "Vision",
            "-o",
            str(binary_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return binary_path


def build_ocr_helper() -> Path:
    return _build_objc_helper(ocr_helper_source_path(), ocr_helper_binary_path())


def build_click_helper() -> Path:
    return _build_objc_helper(click_helper_source_path(), click_helper_binary_path())


def capture_codex_window_ocr(
    *,
    app_name: str = "Codex",
    pid: int | None = None,
    image_output: Path | None = None,
) -> Dict[str, object]:
    helper_path = build_ocr_helper()
    command = [str(helper_path), "--app-name", app_name]
    if pid is not None:
        command.extend(["--pid", str(pid)])
    if image_output is not None:
        image_output.parent.mkdir(parents=True, exist_ok=True)
        command.extend(["--image-output", str(image_output)])

    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    payload = json.loads(stdout) if stdout else {"status": "error", "note": "No output from OCR helper."}
    payload["returncode"] = completed.returncode
    if stderr:
        payload["stderr"] = stderr
    return payload


def click_screen_point(x: float, y: float) -> Dict[str, object]:
    helper_path = build_click_helper()
    completed = subprocess.run(
        [str(helper_path), "--x", f"{x:.2f}", "--y", f"{y:.2f}"],
        check=False,
        capture_output=True,
        text=True,
    )
    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    payload = json.loads(stdout) if stdout else {"status": "error", "note": "No output from click helper."}
    payload["returncode"] = completed.returncode
    if stderr:
        payload["stderr"] = stderr
    return payload


def normalize_ocr_text(value: str) -> str:
    return " ".join(value.lower().split())


def _normalized_phrases(values: Iterable[str]) -> list[str]:
    return [normalize_ocr_text(value) for value in values if value and normalize_ocr_text(value)]


def _full_text(payload: Dict[str, object]) -> str:
    items = payload.get("text_items", [])
    texts = [str(item.get("text", "")) for item in items if isinstance(item, dict)]
    return normalize_ocr_text(" ".join(texts))


def find_text_target(
    payload: Dict[str, object],
    *,
    text_candidates: Sequence[str],
    required_context_phrases: Sequence[str] = (),
) -> Dict[str, object] | None:
    normalized_candidates = _normalized_phrases(text_candidates)
    if not normalized_candidates:
        raise ValueError("At least one OCR text candidate is required.")

    full_text = _full_text(payload)
    normalized_context = _normalized_phrases(required_context_phrases)
    if normalized_context and not all(phrase in full_text for phrase in normalized_context):
        return None

    best_match: Dict[str, object] | None = None
    best_score: tuple[int, float] | None = None

    for item in payload.get("text_items", []):
        if not isinstance(item, dict):
            continue
        item_text = normalize_ocr_text(str(item.get("text", "")))
        if not item_text:
            continue

        candidate_score = None
        for candidate in normalized_candidates:
            if item_text == candidate:
                candidate_score = (2, float(item.get("confidence", 0.0)))
                break
            if candidate in item_text:
                candidate_score = (1, float(item.get("confidence", 0.0)))
        if candidate_score is None:
            continue

        if best_score is None or candidate_score > best_score:
            best_score = candidate_score
            best_match = item

    return best_match


def run_visual_actuation(
    decision: str,
    selector_entry: Dict[str, object],
    *,
    app_name: str = "Codex",
    image_output: Path | None = None,
) -> Dict[str, object]:
    text_candidates = selector_entry.get("ocr_text_candidates", [])
    required_context = selector_entry.get("required_context_phrases", [])
    if not text_candidates:
        return {
            "status": "error",
            "method": "vision_ocr",
            "decision": decision,
            "note": "No ocr_text_candidates were configured for the requested decision.",
        }

    payload = capture_codex_window_ocr(app_name=app_name, image_output=image_output)
    if payload.get("status") != "ok":
        return {
            "status": "error",
            "method": "vision_ocr",
            "decision": decision,
            "details": payload,
        }

    target = find_text_target(
        payload,
        text_candidates=text_candidates,
        required_context_phrases=required_context,
    )
    if target is None:
        return {
            "status": "error",
            "method": "vision_ocr",
            "decision": decision,
            "details": payload,
            "note": "No OCR target matched the required context and candidate text.",
        }

    center = target.get("screen_center", {})
    if "x" not in center or "y" not in center:
        return {
            "status": "error",
            "method": "vision_ocr",
            "decision": decision,
            "target": target,
            "ocr": payload,
            "note": "The OCR match did not include a screen center coordinate.",
        }

    x = float(center.get("x"))
    y = float(center.get("y"))
    click_result = click_screen_point(x=x, y=y)
    return {
        "status": click_result.get("status", "error"),
        "method": "vision_ocr",
        "decision": decision,
        "target": target,
        "ocr": payload,
        "click": click_result,
    }
