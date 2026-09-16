from __future__ import annotations
import argparse, json, os
from pathlib import Path

from jong_core.vision import VisionPipeline, OnnxYoloDetector, load_labels_from_json
from jong_core.vision.decoder import make_ultralytics_decoder
from jong_core.vision.model_config import labels_from_onnx_session
from jong_core.vision.evaluation import load_manifest, evaluate_samples, select_review_threshold, commercial_readiness

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--labels")
    ap.add_argument("--output", default="vision-eval.json")
    ap.add_argument("--min-confidence", type=float, default=0.80)
    args=ap.parse_args()

    import onnxruntime as ort
    session=ort.InferenceSession(args.model,providers=["CPUExecutionProvider"])
    labels=labels_from_onnx_session(session)
    if labels is None and args.labels:
        labels=load_labels_from_json(args.labels)
    if labels is None:
        raise SystemExit("No class labels in model metadata. Pass --labels.")

    detector=OnnxYoloDetector(args.model, make_ultralytics_decoder(labels))
    pipeline=VisionPipeline(detector,min_confidence=args.min_confidence)
    report=evaluate_samples(pipeline, load_manifest(args.manifest))
    report["review_threshold_selection"] = select_review_threshold(report)
    report["commercial_readiness"] = commercial_readiness(report)
    Path(args.output).write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({k:report[k] for k in ("hands","exact_hand_rate","review_rate","mean_corrections","tile_accuracy","false_accept_rate","error_review_recall")},indent=2))

if __name__=="__main__":
    main()
