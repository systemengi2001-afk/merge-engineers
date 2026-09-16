from __future__ import annotations
import argparse, json
from pathlib import Path
from jong_core.vision.dataset import build_verified_manifest


def main():
    ap = argparse.ArgumentParser(description="Audit real-photo labels and build a verified JONG AI vision manifest")
    ap.add_argument("--dataset", default="../vision_dataset")
    ap.add_argument("--output", default="vision-eval-manifest.json")
    ap.add_argument("--audit-output", default="vision-dataset-audit.json")
    args = ap.parse_args()
    report = build_verified_manifest(args.dataset, args.output)
    Path(args.audit_output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("labels_found","verified_samples","excluded_samples","commercial_minimum_reached")}, indent=2))

if __name__ == "__main__":
    main()
