from __future__ import annotations

from collections import Counter
from pathlib import Path
import json

_VALID_SUITS = {"m", "p", "s", "z"}


def _valid_tile(tile: str) -> bool:
    if not isinstance(tile, str) or len(tile) != 2 or tile[1] not in _VALID_SUITS:
        return False
    rank, suit = tile[0], tile[1]
    if suit == "z":
        return rank in "1234567"
    return rank in "0123456789"


def _physical(tile: str) -> str:
    return ("5" + tile[1]) if tile[0] == "0" else tile


def audit_label(label_path: str | Path) -> dict:
    """Validate one manually labelled real-photo hand before benchmark use."""
    path = Path(label_path)
    errors: list[str] = []
    try:
        row = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"label": str(path), "valid": False, "errors": [f"invalid json: {exc}"]}

    tiles = row.get("expected_tiles")
    # v5.5 structured ground truth keeps the 13-tile standing hand and the
    # separated draw tile explicit.  This is important for real-table photos:
    # flattening them too early hides draw-tile/ROI segmentation failures.
    hand_tiles = row.get("hand_tiles")
    drawn_tile = row.get("drawn_tile")
    if hand_tiles is not None or drawn_tile is not None:
        if not isinstance(hand_tiles, list) or len(hand_tiles) != 13:
            errors.append("hand_tiles must contain exactly 13 tiles when structured ground truth is used")
        if not _valid_tile(drawn_tile):
            errors.append("drawn_tile must be one valid tile token when structured ground truth is used")
        if isinstance(hand_tiles, list) and len(hand_tiles) == 13 and _valid_tile(drawn_tile):
            structured = hand_tiles + [drawn_tile]
            if tiles is None:
                tiles = structured
            elif tiles != structured:
                errors.append("expected_tiles must equal hand_tiles + drawn_tile in order")

    if not isinstance(tiles, list):
        errors.append("expected_tiles must be a list")
        tiles = []
    elif len(tiles) not in (13, 14):
        errors.append(f"expected_tiles must contain 13 or 14 tiles, got {len(tiles)}")

    bad = [str(t) for t in tiles if not _valid_tile(t)]
    if bad:
        errors.append("invalid tile token(s): " + ", ".join(bad))

    counts = Counter(_physical(t) for t in tiles if _valid_tile(t))
    over = sorted(t for t, n in counts.items() if n > 4)
    if over:
        errors.append("physical copy limit exceeded: " + ", ".join(over))

    if row.get("manual_label_verified") is not True:
        errors.append("manual_label_verified must be true")

    image_value = row.get("roi_image") or row.get("image")
    image_path = None
    if not image_value:
        errors.append("roi_image or image is required")
    else:
        image_path = (path.parent / image_value).resolve()
        if not image_path.is_file():
            errors.append(f"image does not exist: {image_value}")

    return {
        "label": str(path), "valid": not errors, "errors": errors,
        "id": row.get("id"), "image": str(image_path) if image_path else None,
        "expected_tiles": tiles,
        "hand_tiles": hand_tiles if isinstance(hand_tiles, list) else None,
        "drawn_tile": drawn_tile if _valid_tile(drawn_tile) else None,
        "structured_ground_truth": isinstance(hand_tiles, list) and len(hand_tiles) == 13 and _valid_tile(drawn_tile),
    }


def build_verified_manifest(dataset_dir: str | Path, output: str | Path | None = None) -> dict:
    """Build an evaluation manifest using only audited, manually verified labels.

    Invalid/unverified rows are excluded rather than silently contaminating a
    commercial-readiness benchmark. The returned audit makes exclusions visible.
    """
    root = Path(dataset_dir)
    labels_dir = root / "labels"
    audits = [audit_label(p) for p in sorted(labels_dir.glob("*.json"))] if labels_dir.is_dir() else []
    accepted = [a for a in audits if a["valid"]]
    manifest = [{
        "image": a["image"], "expected_tiles": a["expected_tiles"],
        **({"hand_tiles": a["hand_tiles"], "drawn_tile": a["drawn_tile"]} if a.get("structured_ground_truth") else {}),
    } for a in accepted]
    report = {
        "dataset_dir": str(root.resolve()),
        "labels_found": len(audits),
        "verified_samples": len(accepted),
        "excluded_samples": len(audits) - len(accepted),
        "commercial_minimum_reached": len(accepted) >= 100,
        "manifest": manifest,
        "audit": audits,
    }
    if output is not None:
        Path(output).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
