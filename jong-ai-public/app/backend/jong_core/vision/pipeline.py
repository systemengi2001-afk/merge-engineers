from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from statistics import mean
from typing import Iterable

from .schema import Detection, RecognitionResult
from .labels import normalize_label
from .model_config import labels_from_onnx_session
from .diagnostics import diagnose_detections


def _center_x(bbox: tuple[float,float,float,float]) -> float:
    return (bbox[0] + bbox[2]) / 2.0

def _bbox_iou(a: tuple[float,float,float,float], b: tuple[float,float,float,float]) -> float:
    """Intersection-over-union for detector boxes in any common coordinate space."""
    ix1=max(a[0],b[0]); iy1=max(a[1],b[1]); ix2=min(a[2],b[2]); iy2=min(a[3],b[3])
    iw=max(0.0,ix2-ix1); ih=max(0.0,iy2-iy1)
    inter=iw*ih
    area_a=max(0.0,a[2]-a[0])*max(0.0,a[3]-a[1])
    area_b=max(0.0,b[2]-b[0])*max(0.0,b[3]-b[1])
    union=area_a+area_b-inter
    return inter/union if union > 0 else 0.0


def _compact_mpsz(labels: Iterable[str]) -> str | None:
    labels = list(labels)
    if any(x == "UNKNOWN" for x in labels):
        return None
    groups = {"m": [], "p": [], "s": [], "z": []}
    for token in labels:
        if len(token) != 2 or token[1] not in groups:
            return None
        groups[token[1]].append(token[0])
    parts=[]
    for suit in "mpsz":
        if groups[suit]:
            groups[suit].sort(key=lambda x: (x != "0", int(x)))
            parts.append("".join(groups[suit]) + suit)
    return "".join(parts)


class Detector(ABC):
    name = "detector"
    @abstractmethod
    def detect(self, image_path: str | Path) -> list[Detection]:
        raise NotImplementedError


class MockDetector(Detector):
    """Test-only detector. Never enabled automatically in production."""
    name = "mock_detector_v0.5"
    def __init__(self, detections: list[Detection]):
        self._detections = detections
    def detect(self, image_path: str | Path) -> list[Detection]:
        return list(self._detections)


class OnnxYoloDetector(Detector):
    """Model-agnostic ONNX adapter for Mahjong-YOLO-style exports.

    A decoder callable is required because exported YOLO tensor layouts differ by
    exporter/version. This avoids silently decoding a model with the wrong schema.
    """
    name = "onnx_yolo_adapter_v0.5"
    def __init__(self, model_path: str | Path, decoder, input_size: int = 640):
        self.model_path = str(model_path)
        self.decoder = decoder
        self.input_size = input_size
        try:
            import onnxruntime as ort
        except ImportError as e:
            raise RuntimeError("onnxruntime is required for ONNX inference") from e
        self.session = ort.InferenceSession(self.model_path, providers=["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name
        self.metadata_labels = labels_from_onnx_session(self.session)

    def _preprocess(self, image_path: str | Path):
        try:
            from PIL import Image
            import numpy as np
        except ImportError as e:
            raise RuntimeError("Pillow and numpy are required for image preprocessing") from e
        img = Image.open(image_path).convert("RGB")
        ow, oh = img.size
        scale = min(self.input_size / ow, self.input_size / oh)
        nw, nh = int(round(ow*scale)), int(round(oh*scale))
        resized = img.resize((nw,nh))
        canvas = Image.new("RGB", (self.input_size,self.input_size), (114,114,114))
        px, py = (self.input_size-nw)//2, (self.input_size-nh)//2
        canvas.paste(resized, (px,py))
        arr = np.asarray(canvas, dtype="float32") / 255.0
        arr = arr.transpose(2,0,1)[None,...]
        return arr, {"original_size": (ow,oh), "scale": scale, "pad": (px,py), "input_size": self.input_size}

    def detect(self, image_path: str | Path) -> list[Detection]:
        tensor, meta = self._preprocess(image_path)
        outputs = self.session.run(None, {self.input_name: tensor})
        raw = self.decoder(outputs, meta)
        return [Detection(
            tile=normalize_label(item["label"]),
            confidence=float(item["confidence"]),
            bbox=tuple(float(x) for x in item["bbox"]),
            class_id=item.get("class_id"),
        ) for item in raw]


class VisionPipeline:
    def __init__(self, detector: Detector, min_confidence: float = 0.80, expected_counts=(13,14)):
        self.detector = detector
        self.min_confidence = min_confidence
        self.expected_counts = tuple(expected_counts)

    def recognize_hand(self, image_path: str | Path) -> RecognitionResult:
        detections = sorted(self.detector.detect(image_path), key=lambda d: _center_x(d.bbox))
        warnings=[]
        if len(detections) not in self.expected_counts:
            warnings.append(f"expected 13 or 14 tiles, detected {len(detections)}")
        low=[d for d in detections if d.confidence < self.min_confidence]
        if low:
            warnings.append(f"{len(low)} detection(s) below confidence threshold {self.min_confidence:.2f}")

        # Duplicate detector boxes are a dangerous silent-error mode: the total
        # count can still be 13/14 and every class can look plausible, while one
        # real tile is effectively replaced by a duplicate.  Gate strongly
        # overlapping boxes before downstream EV analysis.  We intentionally do
        # not auto-delete either box because that could hide a genuine occlusion.
        overlap_pairs=[]
        for i in range(len(detections)):
            for j in range(i+1,len(detections)):
                iou=_bbox_iou(detections[i].bbox,detections[j].bbox)
                if iou >= 0.70:
                    overlap_pairs.append((i,j,iou))
        if overlap_pairs:
            worst=max(x[2] for x in overlap_pairs)
            warnings.append(
                f"{len(overlap_pairs)} suspicious overlapping detection pair(s); max IoU {worst:.2f}"
            )

        # Row-geometry diagnostics catch another silent failure mode: all boxes
        # can be individually confident and non-overlapping, yet one false box
        # may sit far above/below the actual hand or have a wildly different
        # size. Use robust medians so a single outlier cannot define the baseline.
        if len(detections) >= 5:
            import statistics
            widths=[max(0.0,d.bbox[2]-d.bbox[0]) for d in detections]
            heights=[max(0.0,d.bbox[3]-d.bbox[1]) for d in detections]
            centers_y=[(d.bbox[1]+d.bbox[3])/2.0 for d in detections]
            med_w=statistics.median(widths); med_h=statistics.median(heights)
            med_y=statistics.median(centers_y)
            size_outliers=[]; row_outliers=[]
            for i,(w,h,cy) in enumerate(zip(widths,heights,centers_y)):
                if med_w > 0 and med_h > 0 and (w < 0.55*med_w or w > 1.80*med_w or h < 0.55*med_h or h > 1.80*med_h):
                    size_outliers.append(i)
                if med_h > 0 and abs(cy-med_y) > 0.65*med_h:
                    row_outliers.append(i)
            if size_outliers:
                warnings.append(f"{len(size_outliers)} detection(s) have anomalous box size")
            if row_outliers:
                warnings.append(f"{len(row_outliers)} detection(s) are off the hand row")
        labels=[normalize_label(d.tile) for d in detections]
        unknown=[x for x in labels if x=="UNKNOWN"]
        if unknown:
            warnings.append(f"{len(unknown)} tile(s) are UNKNOWN")

        # A detector can produce individually plausible boxes that are physically
        # impossible as a Mahjong hand (for example five copies of 1m).  Never
        # let such a recognition flow into EV analysis without user review.
        physical_counts={}
        for label in labels:
            if label == "UNKNOWN":
                continue
            # Red fives (0m/0p/0s) are the same physical tile type as five.
            physical = ("5" + label[1]) if label[0] == "0" else label
            physical_counts[physical] = physical_counts.get(physical, 0) + 1
        impossible=[tile for tile,count in physical_counts.items() if count > 4]
        if impossible:
            warnings.append("physical copy limit exceeded: " + ", ".join(sorted(impossible)))

        mpsz=_compact_mpsz(labels)
        confidence=mean([d.confidence for d in detections]) if detections else 0.0
        diagnostics=tuple(x.to_dict() for x in diagnose_detections(detections, self.min_confidence))
        return RecognitionResult(
            tiles=tuple(detections),
            hand_mpsz=mpsz,
            confidence=confidence,
            needs_review=bool(warnings) or mpsz is None,
            warnings=tuple(warnings),
            model=self.detector.name,
            diagnostics=diagnostics,
        )
