from __future__ import annotations
import ast
import json
from pathlib import Path

def load_labels_from_json(path: str | Path) -> list[str]:
    data=json.loads(Path(path).read_text())
    if isinstance(data, dict):
        # Accept {"0":"1m",...} or {0:"1m"...}
        pairs=sorted(((int(k),v) for k,v in data.items()), key=lambda x:x[0])
        return [str(v) for _,v in pairs]
    if isinstance(data, list):
        return [str(x) for x in data]
    raise ValueError("label JSON must be a list or index->label object")

def labels_from_onnx_session(session) -> list[str] | None:
    """Read Ultralytics-style class names from ONNX metadata when present."""
    meta=session.get_modelmeta()
    custom=getattr(meta,"custom_metadata_map",{}) or {}
    raw=custom.get("names") or custom.get("class_names") or custom.get("labels")
    if not raw:
        return None
    # Ultralytics commonly stores a Python-dict-like string.
    for parser in (json.loads, ast.literal_eval):
        try:
            obj=parser(raw)
            if isinstance(obj, dict):
                return [str(v) for _,v in sorted(((int(k),v) for k,v in obj.items()), key=lambda x:x[0])]
            if isinstance(obj, list):
                return [str(x) for x in obj]
        except Exception:
            pass
    return None
