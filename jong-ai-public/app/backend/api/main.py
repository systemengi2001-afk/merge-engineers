from __future__ import annotations

import json, os, tempfile, hashlib, time, secrets, shutil
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from jong_core import analyze_hand, analyze_hand_instant
from jong_core.ai_reference_registry import reference_catalog, reference_coverage
from jong_core.call_decision import evaluate_pon_decision, evaluate_call_decision
from jong_core.self_kan_decision import evaluate_self_kan_decision
from jong_core.defense_ev import evaluate_defense_ev, OpponentThreat
from jong_core.placement_utility import evaluate_placement_ev, PlacementState
from jong_core.round_outcome_sim import evaluate_round_outcomes
from jong_core.match_state_ev import evaluate_match_state_ev, MatchState
from jong_core.future_match_rollout import evaluate_future_match_rollout
from jong_core.jobs import PrecisionJobStore
from jong_core.calibration import CalibrationStore
from jong_core.rules import PROFILES, get_ruleset
from jong_core.call_legality import CallContext, check_call_legality
from jong_core.open_hand import OpenMeld, check_osaka_call_from_hand
from jong_core.open_scoring import score_open_hand
from jong_core.scoring import ScoreConfig
from jong_core.analyzer import _single_tile_index
from jong_core.reference_oracle import build_mahjong_cpp_request, call_mahjong_cpp, normalize_mahjong_cpp_response, compare_jong_to_oracle
from jong_core.oracle_validation import OracleValidationCase, validate_live_cases, probe_mahjong_cpp
from jong_core.diff_mining_pipeline import ComparisonInput, build_diff_mining_report
from jong_core.visible_state_audit import VisibleAuditCase, audit_visible_case, run_visible_state_audit
from jong_core.defense_learning import DefenseFeatureRow, DefenseTrainingSample, CalibrationBin, BinnedDefenseCalibrator, fit_binned_calibrator, evaluate_defense_calibration, fit_validate_defense_calibrator, extract_training_samples_from_snapshots, snapshots_from_event_log, tenhou_xml_to_event_log
from jong_core.oracle_first import analyze_oracle_first
from jong_core.benchmark import compare_case, summary_dict
from jong_core.error_mining import mine_report
from jong_core.case_generator import generate_cases
from jong_core.diagnostics import diagnose_report
from jong_core.improvement_planner import build_improvement_queue, compare_benchmark_summaries
from jong_core.improvement_gate import evaluate_improvement_gate, decision_dict
from jong_core.vision import (
    extract_seat_hand_roi,
    VisionPipeline, OnnxYoloDetector, correction_payload,
    load_labels_from_json, recognize_bottom_row,
)
from jong_core.vision.decoder import make_ultralytics_decoder

calibration_store = CalibrationStore(Path(os.getenv("JONG_CALIBRATION_DB", "/tmp/jong_ai_calibration.sqlite3")))
precision_jobs = PrecisionJobStore(calibration_store)

app = FastAPI(title="JONG AI Analysis API", version="6.41.0")

@app.get("/v1/reference/ai-catalog")
def ai_reference_catalog() -> dict:
    return {"references": reference_catalog(), "coverage": reference_coverage(), "commercial_note": "Engineering policy only; not legal advice."}


class VisibleZones(BaseModel):
    self_discards: list[str] = []
    # Legacy aggregate fields retained for backward compatibility.
    opponent_discards: list[str] = []
    open_melds: list[str] = []
    # v6.16: seat-resolved public zones. In sanma use opponent1/opponent2;
    # yonma callers may also populate opponent3. These stay separate so the
    # next defense layer can derive genbutsu/suji per opponent without losing
    # provenance while all tiles still reduce the live wall today.
    opponent1_discards: list[str] = []
    opponent2_discards: list[str] = []
    opponent3_discards: list[str] = []
    opponent1_melds: list[str] = []
    opponent2_melds: list[str] = []
    opponent3_melds: list[str] = []


class HandRequest(BaseModel):
    hand: str = Field(examples=["123456m123p45677s"])
    visible_tiles: list[str] = []
    visible_zones: VisibleZones | None = None
    draws: int | None = Field(default=None, ge=0, le=18)
    score_ev: bool = False
    dealer: bool = False
    round_wind: str = "1z"
    seat_wind: str = "2z"
    dora_indicators: list[str] = []
    red_dora_count: int = Field(default=0, ge=0, le=12)
    aka_profile: str = "one_each"
    red_supply: tuple[int,int,int] | None = None
    game_mode: str = "yonma"
    ruleset: str | None = None
    nuki_count: int = Field(default=0, ge=0, le=4)
    chip_count: int = Field(default=0, ge=0, le=20)
    chip_value_points: int = Field(default=0, ge=0, le=100000)
    auto_nuki: bool = True

class CorrectedPhotoRequest(HandRequest):
    original_detected_hand: str | None = None
    vision_training_id: str | None = None
    corrected_tiles: list[str] | None = None

class VisionCorrectionFeedback(BaseModel):
    original_detected_hand: str | None = None
    corrected_hand: str
    ruleset: str = "yonma_standard"
    source: str = "app"
    vision_training_id: str | None = None
    corrected_tiles: list[str] | None = None

def _stage_vision_training_crops(image_path: str, rec) -> str | None:
    """Persist the 14 recognized tile crops briefly so human corrections can label pixels.

    Disabled unless JONG_VISION_TRAINING_DIR is configured. The token is random and
    contains no user identity; the original full photo is never retained.
    """
    root_raw=os.getenv("JONG_VISION_TRAINING_DIR")
    if not root_raw or len(rec.tiles) != 14:
        return None
    from PIL import Image
    root=Path(root_raw); root.mkdir(parents=True,exist_ok=True)
    token=secrets.token_urlsafe(18)
    stage=root/"staging"/token; stage.mkdir(parents=True,exist_ok=False)
    im=Image.open(image_path).convert("RGB"); W,H=im.size
    detected=[]
    for i,t in enumerate(rec.tiles):
        x0,y0,x1,y1=t.bbox
        # Vision contract uses normalized coordinates. Fail closed on malformed boxes.
        vals=(float(x0),float(y0),float(x1),float(y1))
        if not (0 <= vals[0] < vals[2] <= 1 and 0 <= vals[1] < vals[3] <= 1):
            shutil.rmtree(stage,ignore_errors=True); return None
        box=(round(vals[0]*W),round(vals[1]*H),round(vals[2]*W),round(vals[3]*H))
        im.crop(box).save(stage/f"{i:02d}.jpg",quality=92)
        detected.append(t.tile)
    (stage/"manifest.json").write_text(json.dumps({"created_at":int(time.time()),"detected_tiles":detected},ensure_ascii=False),encoding="utf-8")
    return token

def _commit_crop_labels(training_id: str | None, corrected_tiles: list[str] | None) -> dict:
    """Bind staged ROI pixels to the user's ordered corrections without guessing alignment."""
    if not training_id or corrected_tiles is None:
        return {"recorded":False,"reason":"no_crop_labels"}
    if len(corrected_tiles) != 14:
        return {"recorded":False,"reason":"invalid_crop_labels","detail":"corrected_tiles must contain 14 ordered labels"}
    from jong_core.vision.labels import normalize_label
    labels=[normalize_label(x) for x in corrected_tiles]
    if any(x == "UNKNOWN" for x in labels):
        return {"recorded":False,"reason":"invalid_crop_labels","detail":"unknown tile label"}
    root_raw=os.getenv("JONG_VISION_TRAINING_DIR")
    if not root_raw:
        return {"recorded":False,"reason":"training_dir_not_configured"}
    root=Path(root_raw); stage=root/"staging"/training_id
    manifest=stage/"manifest.json"
    if not manifest.exists():
        return {"recorded":False,"reason":"training_session_missing"}
    meta=json.loads(manifest.read_text(encoding="utf-8"))
    if len(meta.get("detected_tiles",[])) != 14 or any(not (stage/f"{i:02d}.jpg").exists() for i in range(14)):
        return {"recorded":False,"reason":"training_session_incomplete"}
    digest=hashlib.sha256((training_id+"|"+"|".join(labels)).encode()).hexdigest()[:16]
    out=root/"labeled"/digest
    if out.exists():
        shutil.rmtree(stage,ignore_errors=True)
        return {"recorded":False,"reason":"duplicate_crop_labels","sample_id":digest}
    out.parent.mkdir(parents=True,exist_ok=True); stage.rename(out)
    meta.update({"corrected_tiles":labels,"labeled_at":int(time.time()),"sample_id":digest})
    (out/"manifest.json").write_text(json.dumps(meta,ensure_ascii=False),encoding="utf-8")
    return {"recorded":True,"sample_id":digest,"tiles":14}

def _record_vision_correction(req: VisionCorrectionFeedback) -> dict:
    """Store de-identified correction pairs only; never stores the uploaded photo."""
    if not req.original_detected_hand or req.original_detected_hand == req.corrected_hand:
        return {"recorded": False, "reason": "no_correction"}
    path=Path(os.getenv("JONG_VISION_CORRECTIONS", "/tmp/jong_ai_vision_corrections.jsonl"))
    path.parent.mkdir(parents=True, exist_ok=True)
    from jong_core.vision.correction import correction_tile_delta
    try:
        delta = correction_tile_delta(req.original_detected_hand, req.corrected_hand)
    except (ValueError, TypeError) as e:
        return {"recorded": False, "reason": "invalid_pair", "detail": str(e)}
    digest=hashlib.sha256(f"{req.original_detected_hand}>{req.corrected_hand}".encode()).hexdigest()[:16]
    # Idempotency matters on mobile: retries after a timeout must not overweight one
    # correction in the future training corpus. JSONL stays append-friendly while
    # this bounded scan keeps the endpoint dependency-free.
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    if json.loads(line).get("id") == digest:
                        return {"recorded": False, "reason": "duplicate", "correction_id": digest, "tile_delta": delta}
                except (json.JSONDecodeError, AttributeError):
                    continue
    row={"id":digest,"ts":int(time.time()),"original":req.original_detected_hand,"corrected":req.corrected_hand,"ruleset":req.ruleset,"source":req.source,"tile_delta":delta}
    with path.open("a",encoding="utf-8") as f:
        f.write(json.dumps(row,ensure_ascii=False)+"\n")
    return {"recorded": True, "correction_id": digest, "tile_delta": delta}

def _build_vision_pipeline() -> VisionPipeline:
    model_path=os.getenv("JONG_ONNX_MODEL")
    labels_path=os.getenv("JONG_ONNX_LABELS")
    if not model_path:
        raise HTTPException(status_code=503, detail="vision model not configured: set JONG_ONNX_MODEL")

    # First create a temporary detector/session shell to inspect model metadata.
    try:
        import onnxruntime as ort
    except ImportError as e:
        raise HTTPException(status_code=503, detail="onnxruntime is not installed") from e

    session=ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
    from jong_core.vision.model_config import labels_from_onnx_session
    labels=labels_from_onnx_session(session)

    if labels is None and labels_path:
        labels=load_labels_from_json(labels_path)
    if labels is None:
        raise HTTPException(
            status_code=503,
            detail="model class labels unavailable; provide JONG_ONNX_LABELS JSON",
        )

    decoder=make_ultralytics_decoder(labels)
    return VisionPipeline(OnnxYoloDetector(model_path, decoder))

def _parse_json_list(raw: str, field: str) -> list[str]:
    try:
        val=json.loads(raw)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"{field} must be JSON array") from e
    if not isinstance(val,list) or not all(isinstance(x,str) for x in val):
        raise HTTPException(status_code=400, detail=f"{field} must be JSON array of strings")
    return val

def _run_analysis(
    hand: str, visible_tiles: list[str], draws: int | None, score_ev: bool,
    dealer: bool, round_wind: str, seat_wind: str,
    dora_indicators: list[str], red_dora_count: int,
    game_mode: str = "yonma", ruleset: str | None = None,
    nuki_count: int = 0, chip_count: int = 0, chip_value_points: int = 0,
    auto_nuki: bool = True, aka_profile: str = "one_each", red_supply: tuple[int,int,int] | None = None,
    visible_zones: dict[str,list[str]] | None = None
):
    try:
        return analyze_hand(
            hand, visible_tiles, draws,
            score_ev=score_ev,
            dealer=dealer,
            round_wind=round_wind,
            seat_wind=seat_wind,
            dora_indicators=dora_indicators,
            red_dora_count=red_dora_count,
            aka_profile=aka_profile,
            red_supply=red_supply,
            game_mode=game_mode,
            ruleset=ruleset,
            nuki_count=nuki_count,
            chip_count=chip_count,
            chip_value_points=chip_value_points,
            auto_nuki=auto_nuki,
            visible_zones=visible_zones,
        )
    except (ValueError,TypeError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


class CallLegalityRequest(BaseModel):
    ruleset_id: str = "osaka_sanma_v1"
    call_type: str
    completes_yaku_route: bool = False
    has_guaranteed_yaku_after_call: bool = False
    claimed_tile: str | None = None


class OpenMeldRequest(BaseModel):
    kind: str
    tile: str

class CompleteFirstRequest(BaseModel):
    concealed_hand_after_call: str
    call_type: str
    called_tile: str
    melds_after_call: list[OpenMeldRequest] = []
    round_wind: str = "1z"
    seat_wind: str = "2z"


class OpenScoreRequest(BaseModel):
    concealed_complete_hand: str
    melds: list[OpenMeldRequest]
    winning_tile: str | None = None
    dealer: bool = False
    round_wind: str = "1z"
    seat_wind: str = "2z"
    dora_indicators: list[str] = []
    red_dora_count: int = 0
    nuki_count: int = 0
    chip_count: int = 0
    chip_value_points: int = 0
    ruleset: str = "osaka_sanma_v1"



class LiveOracleCaseRequest(BaseModel):
    case_id: str
    hand: str
    game_mode: str = "yonma"
    ruleset: str | None = None
    round_wind: str = "1z"
    seat_wind: str = "2z"
    dora_indicators: list[str] = []
    visible_tiles: list[str] = []
    nuki_count: int = 0
    turn: int = Field(default=1, ge=1, le=18)

class LiveOracleValidateRequest(BaseModel):
    oracle_url: str
    cases: list[LiveOracleCaseRequest]
    timeout: float = Field(default=20.0, gt=0, le=60)
    instant_draws: int = Field(default=2, ge=1, le=6)

@app.post("/v1/reference/live-validate")
def live_oracle_validate(req: LiveOracleValidateRequest) -> dict:
    try:
        return validate_live_cases(
            req.oracle_url,
            [
                OracleValidationCase(
                    case_id=c.case_id,
                    hand=c.hand,
                    game_mode=c.game_mode,
                    ruleset=c.ruleset,
                    round_wind=c.round_wind,
                    seat_wind=c.seat_wind,
                    dora_indicators=tuple(c.dora_indicators),
                    visible_tiles=tuple(c.visible_tiles),
                    nuki_count=c.nuki_count,
                    turn=c.turn,
                ) for c in req.cases
            ],
            timeout=req.timeout,
            instant_draws=req.instant_draws,
        )
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=502,detail=str(e)) from e

class ReferenceCompareRequest(BaseModel):
    hand: str
    game_mode: str = "yonma"
    ruleset: str | None = None
    round_wind: str = "1z"
    seat_wind: str = "2z"
    dora_indicators: list[str] = []
    visible_tiles: list[str] = []
    nuki_count: int = 0
    turn: int = Field(default=1, ge=1, le=18)
    oracle_url: str | None = None


class OracleFirstRequest(BaseModel):
    hand: str
    game_mode: str = "yonma"
    ruleset: str | None = None
    round_wind: str = "1z"
    seat_wind: str = "2z"
    dora_indicators: list[str] = []
    visible_tiles: list[str] = []
    nuki_count: int = 0
    turn: int = Field(default=1, ge=1, le=18)
    strict_oracle: bool = False





class DefenseLearningSampleRequest(BaseModel):
    sample_id: str
    features: dict
    deal_in: int
    sample_weight: float = 1.0
    source: str = "unknown"
    verified: bool = False
    group_id: str | None = None

class DefenseCalibrationFitRequest(BaseModel):
    ruleset: str
    samples: list[DefenseLearningSampleRequest]
    verified_only: bool = True

class DefenseCalibrationValidateRequest(DefenseCalibrationFitRequest):
    validation_fraction: float = 0.2
    min_validation_samples: int = 20
    max_brier_regression: float = 0.0
    max_ece: float = 0.10


class DefenseSnapshotExtractRequest(BaseModel):
    snapshots: list[dict]

class DefenseEventLogRequest(BaseModel):
    payload: dict

class DefenseTenhouXmlRequest(BaseModel):
    xml: str
    hero_player: int = 0
    ruleset: str = "sanma_standard"
    game_mode: str = "sanma"

@app.post("/v1/defense/training/extract-tenhou-xml")
def defense_training_extract_tenhou_xml(req: DefenseTenhouXmlRequest) -> dict:
    try:
        payload=tenhou_xml_to_event_log(req.xml,hero_player=req.hero_player,ruleset=req.ruleset,game_mode=req.game_mode)
        snapshots=snapshots_from_event_log(payload)
        rows=extract_training_samples_from_snapshots(snapshots)
        from dataclasses import asdict
        return {"samples":[asdict(x) for x in rows],"count":len(rows),"snapshot_count":len(snapshots),"source":"tenhou-mjlog-xml-v1","label_policy":"explicit-ron-provenance-v1"}
    except (ValueError,TypeError,KeyError) as e:
        raise HTTPException(status_code=400,detail=str(e)) from e

@app.post("/v1/defense/training/extract-event-log")
def defense_training_extract_event_log(req: DefenseEventLogRequest) -> dict:
    try:
        snapshots=snapshots_from_event_log(req.payload)
        rows=extract_training_samples_from_snapshots(snapshots)
        from dataclasses import asdict
        return {"samples":[asdict(x) for x in rows],"count":len(rows),"snapshot_count":len(snapshots),"label_policy":"explicit-ron-provenance-v1"}
    except (ValueError,TypeError,KeyError) as e:
        raise HTTPException(status_code=400,detail=str(e)) from e

@app.post("/v1/defense/training/extract-snapshots")
def defense_training_extract_snapshots(req: DefenseSnapshotExtractRequest) -> dict:
    try:
        rows=extract_training_samples_from_snapshots(req.snapshots)
        from dataclasses import asdict
        return {"samples":[asdict(x) for x in rows],"count":len(rows),"label_policy":"observed-discard-only-v1"}
    except (ValueError,TypeError) as e:
        raise HTTPException(status_code=400,detail=str(e)) from e

@app.post("/v1/defense/calibration/fit-validate")
def defense_calibration_fit_validate(req: DefenseCalibrationValidateRequest) -> dict:
    try:
        samples=[DefenseTrainingSample(sample_id=x.sample_id,features=DefenseFeatureRow(**x.features),deal_in=x.deal_in,sample_weight=x.sample_weight,source=x.source,verified=x.verified,group_id=x.group_id) for x in req.samples]
        out=fit_validate_defense_calibrator(samples,ruleset=req.ruleset,validation_fraction=req.validation_fraction,verified_only=req.verified_only,min_validation_samples=req.min_validation_samples,max_brier_regression=req.max_brier_regression,max_ece=req.max_ece)
        m=out.pop("model")
        return {**out,"model":{"version":m.version,"ruleset":m.ruleset,"total_samples":m.total_samples,"verified_only":m.verified_only,"bins":[b.__dict__ for b in m.bins]}}
    except (ValueError,TypeError) as e:
        raise HTTPException(status_code=400,detail=str(e)) from e

@app.post("/v1/defense/calibration/fit-evaluate")
def defense_calibration_fit_evaluate(req: DefenseCalibrationFitRequest) -> dict:
    try:
        samples=[
            DefenseTrainingSample(
                sample_id=x.sample_id,
                features=DefenseFeatureRow(**x.features),
                deal_in=x.deal_in,
                sample_weight=x.sample_weight,
                source=x.source,
                verified=x.verified,
                group_id=x.group_id,
            )
            for x in req.samples
        ]
        model=fit_binned_calibrator(
            samples,
            ruleset=req.ruleset,
            verified_only=req.verified_only,
        )
        evaluation=evaluate_defense_calibration(
            samples,
            calibrator=model,
            ruleset=req.ruleset,
            verified_only=req.verified_only,
        )
        return {
            "model":{
                "version":model.version,
                "ruleset":model.ruleset,
                "total_samples":model.total_samples,
                "verified_only":model.verified_only,
                "bins":[b.__dict__ for b in model.bins],
            },
            "evaluation":evaluation,
        }
    except (ValueError,TypeError) as e:
        raise HTTPException(status_code=400,detail=str(e)) from e

class VisibleAuditRequest(BaseModel):
    count: int = Field(default=1000, ge=1, le=10000)
    rulesets: list[str] = ["yonma_standard","sanma_standard","osaka_sanma_v1"]
    seed: int = 20260915

@app.post("/v1/audit/visible-state")
def visible_state_audit(req: VisibleAuditRequest) -> dict:
    try:
        return run_visible_state_audit(
            req.count,
            rulesets=tuple(req.rulesets),
            seed=req.seed,
        )
    except ValueError as e:
        raise HTTPException(status_code=400,detail=str(e)) from e

class DiffMiningCaseRequest(BaseModel):
    case_id: str
    case: dict
    jong: dict
    oracle: dict
    reference_source: str
    reference_verified: bool = False

class DiffMiningRequest(BaseModel):
    cases: list[DiffMiningCaseRequest]
    max_cases: int = Field(default=1000, ge=1, le=10000)
    ev_threshold: float = 500.0
    win_threshold: float = 0.05
    tenpai_threshold: float = 0.05
    ukeire_threshold: float = 2.0
    fixture_limit: int = Field(default=100, ge=1, le=1000)
    min_fixture_severity: float = 4.0

@app.post("/v1/benchmark/diff-mine")
def benchmark_diff_mine(req: DiffMiningRequest) -> dict:
    return build_diff_mining_report(
        [
            ComparisonInput(
                case_id=x.case_id,
                case=x.case,
                jong=x.jong,
                oracle=x.oracle,
                reference_source=x.reference_source,
                reference_verified=x.reference_verified,
            )
            for x in req.cases
        ],
        max_cases=req.max_cases,
        ev_threshold=req.ev_threshold,
        win_threshold=req.win_threshold,
        tenpai_threshold=req.tenpai_threshold,
        ukeire_threshold=req.ukeire_threshold,
        fixture_limit=req.fixture_limit,
        min_fixture_severity=req.min_fixture_severity,
    )

class BenchmarkPair(BaseModel):
    case_id: str
    jong: dict
    oracle: dict

class BenchmarkEvaluateRequest(BaseModel):
    pairs: list[BenchmarkPair]


class BenchmarkTriageRequest(BaseModel):
    report: dict
    ev_threshold: float = 500.0
    win_threshold: float = 0.05
    tenpai_threshold: float = 0.05
    ukeire_threshold: float = 2.0


class BenchmarkDiagnoseRequest(BaseModel):
    report: dict
    ukeire_threshold: float = 2.0
    probability_threshold: float = 0.05
    ev_threshold: float = 500.0


class ImprovementQueueRequest(BaseModel):
    diagnostics: dict
    limit: int = Field(default=100, ge=1, le=1000)


class ImprovementGateRequest(BaseModel):
    before: dict
    after: dict
    max_accuracy_regression: float = 0.0
    max_probability_mae_regression: float = 0.0
    max_ukeire_mae_regression: float = 0.0
    max_ev_mae_regression: float = 0.0
    require_any_improvement: bool = True


class ExistingMeldRequest(BaseModel):
    kind: str
    tile: str

class CallDecisionRequest(BaseModel):
    concealed_hand: str
    offered_tile: str
    existing_melds: list[ExistingMeldRequest] = []
    ruleset: str = "osaka_sanma_v1"
    round_wind: str = "1z"
    seat_wind: str = "2z"
    visible_tiles: list[str] = []
    dora_indicators: list[str] = []
    nuki_count: int = 0
    draws: int = Field(default=3, ge=1, le=6)



class SelfKanDecisionRequest(BaseModel):
    concealed_hand: str
    existing_melds: list[ExistingMeldRequest] = []
    ruleset: str = "osaka_sanma_v1"
    round_wind: str = "1z"
    seat_wind: str = "2z"
    visible_tiles: list[str] = []
    dora_indicators: list[str] = []
    nuki_count: int = 0
    draws: int = Field(default=3, ge=1, le=6)


class ThreatRequest(BaseModel):
    player: int
    riichi: bool = False
    discards: list[str] = []
    estimated_hand_value: float = 8000.0
    riichi_discard_index: int | None = None
    tedashi_flags: list[bool | None] = []

class ThreatTimelineRequest(BaseModel):
    player: int
    riichi: bool = False
    riichi_discard_index: int | None = None
    tedashi_flags: list[bool | None] = []
    estimated_hand_value: float = 8000.0

class DefenseCalibrationModelRequest(BaseModel):
    version: str
    ruleset: str
    total_samples: int = Field(ge=1)
    verified_only: bool = True
    bins: list[dict]

class DefenseEVRequest(BaseModel):
    hand: str
    threats: list[ThreatRequest] = []
    threat_timeline: list[ThreatTimelineRequest] = []
    visible_zones: VisibleZones | None = None
    visible_tiles: list[str] = []
    dora_indicators: list[str] = []
    draws: int = Field(default=3, ge=1, le=6)
    game_mode: str = "sanma"
    ruleset: str = "osaka_sanma_v1"
    nuki_count: int = 0
    calibration_model: DefenseCalibrationModelRequest | None = None


class PlacementStateRequest(BaseModel):
    scores: list[int]
    self_index: int
    round_index: int = 0
    total_rounds: int = 8
    dealer_index: int | None = None

class PlacementEVRequest(BaseModel):
    hand: str
    threats: list[ThreatRequest]
    placement: PlacementStateRequest
    visible_tiles: list[str] = []
    dora_indicators: list[str] = []
    draws: int = Field(default=3, ge=1, le=6)
    game_mode: str = "sanma"
    ruleset: str = "osaka_sanma_v1"
    nuki_count: int = 0



class MatchStateRequest(BaseModel):
    scores: list[int]
    self_index: int
    dealer_index: int
    round_index: int
    total_rounds: int
    honba: int = 0
    riichi_sticks: int = 0
    agari_yame: bool = True
    target_return_points: int | None = None

class MatchEVRequest(BaseModel):
    hand: str
    threats: list[ThreatRequest]
    match: MatchStateRequest
    visible_tiles: list[str] = []
    dora_indicators: list[str] = []
    draws: int = Field(default=3, ge=1, le=6)
    game_mode: str = "sanma"
    ruleset: str = "osaka_sanma_v1"
    nuki_count: int = 0


class FutureMatchEVRequest(MatchEVRequest):
    future_rounds: int = Field(default=2, ge=0, le=4)

@app.post("/v1/match/future-rollout")
def future_match_rollout(req: FutureMatchEVRequest) -> dict:
    try:
        return evaluate_future_match_rollout(
            req.hand,
            threats=[
                OpponentThreat(
                    player=x.player,
                    riichi=x.riichi,
                    discards=tuple(x.discards),
                    estimated_hand_value=x.estimated_hand_value,
                    riichi_discard_index=x.riichi_discard_index,
                    tedashi_flags=tuple(x.tedashi_flags),
                ) for x in req.threats
            ],
            match=MatchState(
                scores=tuple(req.match.scores),
                self_index=req.match.self_index,
                dealer_index=req.match.dealer_index,
                round_index=req.match.round_index,
                total_rounds=req.match.total_rounds,
                honba=req.match.honba,
                riichi_sticks=req.match.riichi_sticks,
                agari_yame=req.match.agari_yame,
                target_return_points=req.match.target_return_points,
            ),
            visible_tiles=req.visible_tiles,
            dora_indicators=req.dora_indicators,
            draws=req.draws,
            game_mode=req.game_mode,
            ruleset=req.ruleset,
            nuki_count=req.nuki_count,
            future_rounds=req.future_rounds,
        )
    except ValueError as e:
        raise HTTPException(status_code=400,detail=str(e)) from e

@app.post("/v1/match/evaluate")
def match_evaluate(req: MatchEVRequest) -> dict:
    try:
        return evaluate_match_state_ev(
            req.hand,
            threats=[
                OpponentThreat(
                    player=x.player,
                    riichi=x.riichi,
                    discards=tuple(x.discards),
                    estimated_hand_value=x.estimated_hand_value,
                    riichi_discard_index=x.riichi_discard_index,
                    tedashi_flags=tuple(x.tedashi_flags),
                ) for x in req.threats
            ],
            match=MatchState(
                scores=tuple(req.match.scores),
                self_index=req.match.self_index,
                dealer_index=req.match.dealer_index,
                round_index=req.match.round_index,
                total_rounds=req.match.total_rounds,
                honba=req.match.honba,
                riichi_sticks=req.match.riichi_sticks,
                agari_yame=req.match.agari_yame,
                target_return_points=req.match.target_return_points,
            ),
            visible_tiles=req.visible_tiles,
            dora_indicators=req.dora_indicators,
            draws=req.draws,
            game_mode=req.game_mode,
            ruleset=req.ruleset,
            nuki_count=req.nuki_count,
        )
    except ValueError as e:
        raise HTTPException(status_code=400,detail=str(e)) from e

@app.post("/v1/placement/round-outcomes")
def placement_round_outcomes(req: PlacementEVRequest) -> dict:
    try:
        return evaluate_round_outcomes(
            req.hand,
            threats=[
                OpponentThreat(
                    player=x.player,
                    riichi=x.riichi,
                    discards=tuple(x.discards),
                    estimated_hand_value=x.estimated_hand_value,
                    riichi_discard_index=x.riichi_discard_index,
                    tedashi_flags=tuple(x.tedashi_flags),
                ) for x in req.threats
            ],
            placement=PlacementState(
                scores=tuple(req.placement.scores),
                self_index=req.placement.self_index,
                round_index=req.placement.round_index,
                total_rounds=req.placement.total_rounds,
                dealer_index=req.placement.dealer_index,
            ),
            visible_tiles=req.visible_tiles,
            dora_indicators=req.dora_indicators,
            draws=req.draws,
            game_mode=req.game_mode,
            ruleset=req.ruleset,
            nuki_count=req.nuki_count,
        )
    except ValueError as e:
        raise HTTPException(status_code=400,detail=str(e)) from e

@app.post("/v1/placement/evaluate")
def placement_evaluate(req: PlacementEVRequest) -> dict:
    try:
        return evaluate_placement_ev(
            req.hand,
            threats=[
                OpponentThreat(
                    player=x.player,
                    riichi=x.riichi,
                    discards=tuple(x.discards),
                    estimated_hand_value=x.estimated_hand_value,
                    riichi_discard_index=x.riichi_discard_index,
                    tedashi_flags=tuple(x.tedashi_flags),
                ) for x in req.threats
            ],
            placement=PlacementState(
                scores=tuple(req.placement.scores),
                self_index=req.placement.self_index,
                round_index=req.placement.round_index,
                total_rounds=req.placement.total_rounds,
                dealer_index=req.placement.dealer_index,
            ),
            visible_tiles=req.visible_tiles,
            dora_indicators=req.dora_indicators,
            draws=req.draws,
            game_mode=req.game_mode,
            ruleset=req.ruleset,
            nuki_count=req.nuki_count,
        )
    except ValueError as e:
        raise HTTPException(status_code=400,detail=str(e)) from e

@app.post("/v1/defense/evaluate")
def defense_evaluate(req: DefenseEVRequest) -> dict:
    try:
        # v6.17: bridge the seat-resolved public-state contract directly into
        # defense. Explicit threat metadata wins; otherwise opponentN_discards
        # become conservative non-riichi threats. Melds/self discards are still
        # public information and therefore contribute to wall/one-chance counts.
        zones=req.visible_zones.model_dump() if req.visible_zones else {}
        threat_by_player={x.player:x for x in req.threats}
        resolved=[]
        for player in (1,2,3):
            x=threat_by_player.get(player)
            discards=list(x.discards) if x else list(zones.get(f"opponent{player}_discards",[]))
            if not discards and x is None:
                continue
            timeline_by_player={t.player:t for t in req.threat_timeline}
            tl=timeline_by_player.get(player)
            zone_riichi=tl.riichi if tl else False
            zone_riichi_idx=tl.riichi_discard_index if tl else None
            zone_flags=tuple(tl.tedashi_flags) if tl else ()
            if zone_riichi_idx is not None and not (0 <= zone_riichi_idx < len(discards)):
                raise ValueError(f"opponent{player}_riichi_discard_index is outside that player's river")
            if zone_flags and len(zone_flags) != len(discards):
                raise ValueError(f"opponent{player}_tedashi_flags must match that player's river length")
            resolved.append(OpponentThreat(
                player=player, riichi=x.riichi if x else zone_riichi, discards=tuple(discards),
                estimated_hand_value=x.estimated_hand_value if x else (tl.estimated_hand_value if tl else 8000.0),
                riichi_discard_index=x.riichi_discard_index if x else zone_riichi_idx,
                tedashi_flags=tuple(x.tedashi_flags) if x else zone_flags,
            ))
        # Preserve unusual/non-seat threat ids supplied by legacy callers.
        resolved.extend(OpponentThreat(
            player=x.player, riichi=x.riichi, discards=tuple(x.discards),
            estimated_hand_value=x.estimated_hand_value, riichi_discard_index=x.riichi_discard_index,
            tedashi_flags=tuple(x.tedashi_flags),
        ) for x in req.threats if x.player not in (1,2,3))
        extra_visible=list(req.visible_tiles)+list(zones.get("self_discards",[]))+list(zones.get("open_melds",[]))
        for player in (1,2,3):
            extra_visible += list(zones.get(f"opponent{player}_melds",[]))
        calibrator=None
        if req.calibration_model is not None:
            cm=req.calibration_model
            if cm.ruleset != req.ruleset:
                raise ValueError("calibration_model.ruleset must match request ruleset")
            bins=tuple(CalibrationBin(**b) for b in cm.bins)
            if not bins:
                raise ValueError("calibration_model.bins must not be empty")
            calibrator=BinnedDefenseCalibrator(
                version=cm.version,ruleset=cm.ruleset,bins=bins,
                total_samples=cm.total_samples,verified_only=cm.verified_only,
            )
        out=evaluate_defense_ev(
            req.hand,
            threats=resolved,
            visible_tiles=extra_visible,
            dora_indicators=req.dora_indicators,
            draws=req.draws,
            game_mode=req.game_mode,
            ruleset=req.ruleset,
            nuki_count=req.nuki_count,
            risk_calibrator=calibrator,
        )
        out["public_state_bridge"]={"version":"v6.18","seat_resolved":bool(req.visible_zones),"timeline_metadata":bool(req.threat_timeline),"resolved_threat_players":[x.player for x in resolved]}
        return out
    except ValueError as e:
        raise HTTPException(status_code=400,detail=str(e)) from e

@app.post("/v1/call/self-kan-decision")
def self_kan_decision(req: SelfKanDecisionRequest) -> dict:
    from jong_core.open_hand import OpenMeld
    try:
        return evaluate_self_kan_decision(
            req.concealed_hand,
            existing_melds=[OpenMeld(x.kind,x.tile) for x in req.existing_melds],
            ruleset=req.ruleset,
            round_wind=req.round_wind,
            seat_wind=req.seat_wind,
            visible_tiles=req.visible_tiles,
            dora_indicators=req.dora_indicators,
            nuki_count=req.nuki_count,
            draws=req.draws,
        )
    except ValueError as e:
        raise HTTPException(status_code=400,detail=str(e)) from e

@app.post("/v1/call/decision")
def call_decision(req: CallDecisionRequest) -> dict:
    from jong_core.open_hand import OpenMeld
    try:
        return evaluate_call_decision(
            req.concealed_hand,
            req.offered_tile,
            existing_melds=[OpenMeld(x.kind,x.tile) for x in req.existing_melds],
            ruleset=req.ruleset,
            round_wind=req.round_wind,
            seat_wind=req.seat_wind,
            visible_tiles=req.visible_tiles,
            dora_indicators=req.dora_indicators,
            nuki_count=req.nuki_count,
            draws=req.draws,
        )
    except ValueError as e:
        raise HTTPException(status_code=400,detail=str(e)) from e

@app.post("/v1/call/pon-decision")
def call_pon_decision(req: CallDecisionRequest) -> dict:
    from jong_core.open_hand import OpenMeld
    try:
        return evaluate_pon_decision(
            req.concealed_hand,
            req.offered_tile,
            existing_melds=[OpenMeld(x.kind,x.tile) for x in req.existing_melds],
            ruleset=req.ruleset,
            round_wind=req.round_wind,
            seat_wind=req.seat_wind,
            visible_tiles=req.visible_tiles,
            dora_indicators=req.dora_indicators,
            nuki_count=req.nuki_count,
            draws=req.draws,
        )
    except ValueError as e:
        raise HTTPException(status_code=400,detail=str(e)) from e

@app.post("/v1/benchmark/improvement-gate")
def improvement_gate(req: ImprovementGateRequest) -> dict:
    d=evaluate_improvement_gate(
        req.before,req.after,
        max_accuracy_regression=req.max_accuracy_regression,
        max_probability_mae_regression=req.max_probability_mae_regression,
        max_ukeire_mae_regression=req.max_ukeire_mae_regression,
        max_ev_mae_regression=req.max_ev_mae_regression,
        require_any_improvement=req.require_any_improvement,
    )
    return decision_dict(d)

@app.post("/v1/benchmark/improvement-queue")
def improvement_queue(req: ImprovementQueueRequest) -> dict:
    return build_improvement_queue(req.diagnostics,limit=req.limit)

class BenchmarkCompareRequest(BaseModel):
    before: dict
    after: dict

@app.post("/v1/benchmark/compare-runs")
def compare_runs(req: BenchmarkCompareRequest) -> dict:
    return compare_benchmark_summaries(req.before,req.after)

@app.post("/v1/benchmark/diagnose")
def benchmark_diagnose(req: BenchmarkDiagnoseRequest) -> dict:
    return diagnose_report(
        req.report,
        ukeire_threshold=req.ukeire_threshold,
        probability_threshold=req.probability_threshold,
        ev_threshold=req.ev_threshold,
    )

@app.post("/v1/benchmark/triage")
def benchmark_triage(req: BenchmarkTriageRequest) -> dict:
    return mine_report(
        req.report,
        ev_threshold=req.ev_threshold,
        win_threshold=req.win_threshold,
        tenpai_threshold=req.tenpai_threshold,
        ukeire_threshold=req.ukeire_threshold,
    )

class BenchmarkGenerateRequest(BaseModel):
    count: int = Field(default=100, ge=1, le=10000)
    ruleset: str = "yonma_standard"
    seed: int = 20260914

@app.post("/v1/benchmark/generate-cases")
def benchmark_generate(req: BenchmarkGenerateRequest) -> dict:
    try:
        cases=generate_cases(req.count,ruleset=req.ruleset,seed=req.seed)
        return {"count":len(cases),"cases":cases}
    except ValueError as e:
        raise HTTPException(status_code=400,detail=str(e)) from e

@app.post("/v1/benchmark/evaluate")
def benchmark_evaluate(req: BenchmarkEvaluateRequest) -> dict:
    rows=[compare_case(p.case_id,p.jong,p.oracle) for p in req.pairs]
    return summary_dict(rows)

@app.post("/v1/analyze/oracle-first")
def oracle_first(req: OracleFirstRequest) -> dict:
    try:
        return analyze_oracle_first(
            hand=req.hand,
            game_mode=req.game_mode,
            ruleset=req.ruleset,
            round_wind=req.round_wind,
            seat_wind=req.seat_wind,
            dora_indicators=req.dora_indicators,
            visible_tiles=req.visible_tiles,
            nuki_count=req.nuki_count,
            turn=req.turn,
            strict_oracle=req.strict_oracle,
        )
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=502 if req.strict_oracle else 400, detail=str(e)) from e

@app.post("/v1/reference/compare")
def reference_compare(req: ReferenceCompareRequest) -> dict:
    """Compare JONG AI with an external mahjong-cpp reference service.

    The service is intentionally external to keep GPL code out of the proprietary core.
    Configure JONG_MAHJONG_CPP_URL or pass oracle_url in development.
    """
    url=req.oracle_url or os.getenv("JONG_MAHJONG_CPP_URL")
    if not url:
        raise HTTPException(status_code=503,detail="reference oracle not configured: set JONG_MAHJONG_CPP_URL")
    try:
        jong=analyze_hand_instant(
            req.hand,req.visible_tiles,draws=max(1,min(6,req.turn)),
            game_mode=req.game_mode,ruleset=req.ruleset,nuki_count=req.nuki_count,
        )
        payload=build_mahjong_cpp_request(
            hand=req.hand,game_mode=req.game_mode,round_wind=req.round_wind,
            seat_wind=req.seat_wind,dora_indicators=req.dora_indicators,
            nuki_count=req.nuki_count,visible_tiles=req.visible_tiles,
        )
        raw=call_mahjong_cpp(url,payload)
        oracle=normalize_mahjong_cpp_response(raw,turn=req.turn)
        return {
            "source":"mahjong-cpp / pystyle reference",
            "comparison":compare_jong_to_oracle(jong,oracle),
            "oracle_meta":{"searched":oracle.searched,"time_us":oracle.time_us},
        }
    except (ValueError,RuntimeError) as e:
        raise HTTPException(status_code=502,detail=str(e)) from e

@app.post("/v1/score/open-hand")
def score_open(req: OpenScoreRequest) -> dict:
    try:
        profile=PROFILES[req.ruleset]
    except KeyError as e:
        raise HTTPException(status_code=400,detail=f"unknown ruleset: {req.ruleset}") from e
    try:
        melds=[OpenMeld(m.kind,m.tile) for m in req.melds]
        cfg=ScoreConfig(
            dealer=req.dealer,
            round_wind=_single_tile_index(req.round_wind),
            seat_wind=_single_tile_index(req.seat_wind),
            riichi=False,
            tsumo=True,
            dora_indicators=tuple(_single_tile_index(x) for x in req.dora_indicators),
            red_dora_count=req.red_dora_count,
            players=profile.players,
            tsumo_loss=profile.tsumo_loss,
            nuki_dora_count=req.nuki_count*profile.nuki_dora_han,
            chip_count=req.chip_count,
            chip_value_points=req.chip_value_points,
        )
        r=score_open_hand(
            req.concealed_complete_hand, melds, cfg,
            winning_tile=req.winning_tile,
            open_tanyao=profile.open_tanyao,
        )
        return {
            "points":r.points,"base_points":r.base_points,"bonus_points":r.bonus_points,
            "han":r.han,"fu":r.fu,"yaku":list(r.yaku),"dora":r.dora,
            "model":r.model,"ruleset":profile.id,
        }
    except ValueError as e:
        raise HTTPException(status_code=400,detail=str(e)) from e

@app.post("/v1/rules/complete-first")
def complete_first(req: CompleteFirstRequest) -> dict:
    melds=[OpenMeld(m.kind,m.tile) for m in req.melds_after_call]
    try:
        return check_osaka_call_from_hand(
            req.concealed_hand_after_call,
            call_type=req.call_type,
            called_tile=req.called_tile,
            melds_after_call=melds,
            round_wind=req.round_wind,
            seat_wind=req.seat_wind,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

@app.post("/v1/rules/call-legality")
def call_legality(req: CallLegalityRequest) -> dict:
    r=check_call_legality(CallContext(
        req.ruleset_id, req.call_type, req.completes_yaku_route,
        req.has_guaranteed_yaku_after_call, req.claimed_tile
    ))
    return {"legal":r.legal,"reason":r.reason}

@app.get("/v1/rulesets")
def rulesets() -> dict:
    return {k:v.public_dict() for k,v in PROFILES.items()}

@app.get("/health")
def health() -> dict:
    return {
        "status":"ok",
        "version":"6.10-app0.2",
        "release":"6.34",
        "vision_configured":bool(os.getenv("JONG_ONNX_MODEL") or os.getenv("JONG_ROW_MODEL")),
        "vision_backend":"onnx" if os.getenv("JONG_ONNX_MODEL") else ("row-review" if os.getenv("JONG_ROW_MODEL") else None),
    }

@app.post("/v1/vision/hand")
async def vision_hand(image: UploadFile = File(...)) -> dict:
    suffix=Path(image.filename or "upload.jpg").suffix or ".jpg"
    data=await image.read()
    if len(data)>12*1024*1024:
        raise HTTPException(status_code=413,detail="image exceeds 12 MB")
    tmp=None
    try:
        with tempfile.NamedTemporaryFile(delete=False,suffix=suffix) as f:
            f.write(data); tmp=f.name
        result=_build_vision_pipeline().recognize_hand(tmp)
        payload=result.to_dict()
        payload["correction"]=correction_payload(result)
        return payload
    finally:
        if tmp and os.path.exists(tmp): os.unlink(tmp)
        roi_path = (tmp + ".roi.jpg") if tmp else None
        if roi_path and os.path.exists(roi_path): os.unlink(roi_path)

@app.post("/v1/photo/analyze")
async def photo_analyze(
    image: UploadFile = File(...),
    draws: int = Form(default=3, ge=0, le=18),
    score_ev: bool = Form(default=True),
    dealer: bool = Form(default=False),
    round_wind: str = Form(default="1z"),
    seat_wind: str = Form(default="2z"),
    dora_indicators_json: str = Form(default="[]"),
    visible_tiles_json: str = Form(default="[]"),
    red_dora_count: int = Form(default=0, ge=0, le=3),
    seat: str = Form(default="bottom"),
    game_mode: str = Form(default="yonma"),
    ruleset: str = Form(default="yonma_standard"),
    nuki_count: int = Form(default=0, ge=0, le=4),
    chip_count: int = Form(default=0, ge=0, le=20),
    chip_value_points: int = Form(default=0, ge=0, le=100000),
    auto_nuki: bool = Form(default=True),
) -> dict:
    """End-to-end photo -> recognition -> analysis.

    If recognition needs correction, analysis is intentionally withheld to prevent
    presenting EV for a possibly-wrong hand.
    """
    suffix=Path(image.filename or "upload.jpg").suffix or ".jpg"
    data=await image.read()
    if len(data)>12*1024*1024:
        raise HTTPException(status_code=413,detail="image exceeds 12 MB")

    dora=_parse_json_list(dora_indicators_json,"dora_indicators_json")
    visible=_parse_json_list(visible_tiles_json,"visible_tiles_json")

    tmp=None
    try:
        with tempfile.NamedTemporaryFile(delete=False,suffix=suffix) as f:
            f.write(data); tmp=f.name
        roi_path = tmp + ".roi.jpg"
        _, roi_box = extract_seat_hand_roi(tmp, seat=seat, output_path=roi_path)
        row_model=os.getenv("JONG_ROW_MODEL")
        if row_model and seat == "bottom":
            # v6.30 review-first real-table path works without pretending the legacy
            # classifier is accurate enough for automatic EV analysis.
            rec=recognize_bottom_row(tmp, row_model, float(os.getenv("JONG_VISION_AUTO_ACCEPT", "0.90")))
        else:
            rec=_build_vision_pipeline().recognize_hand(roi_path)
        rec_dict=rec.to_dict()
        rec_dict["roi"] = {"seat": seat, "box_pixels": list(roi_box)}
        rec_dict["correction"]=correction_payload(rec)
        try:
            rec_dict["vision_training_id"]=_stage_vision_training_crops(tmp, rec)
        except (OSError, ValueError):
            rec_dict["vision_training_id"]=None

        if rec.needs_review or rec.hand_mpsz is None:
            return {
                "status":"needs_review",
                "recognition":rec_dict,
                "analysis":None,
            }

        analysis=_run_analysis(
            rec.hand_mpsz, visible, draws, score_ev, dealer,
            round_wind, seat_wind, dora, red_dora_count,
            game_mode, ruleset, nuki_count, chip_count, chip_value_points, auto_nuki,
        )
        return {
            "status":"analyzed",
            "recognition":rec_dict,
            "analysis":analysis,
        }
    finally:
        if tmp and os.path.exists(tmp): os.unlink(tmp)
        roi_path = (tmp + ".roi.jpg") if tmp else None
        if roi_path and os.path.exists(roi_path): os.unlink(roi_path)

@app.post("/v1/vision/correction")
def vision_correction(req: VisionCorrectionFeedback) -> dict:
    hand_feedback=_record_vision_correction(req)
    try:
        crop_feedback=_commit_crop_labels(req.vision_training_id, req.corrected_tiles)
    except (OSError, ValueError, json.JSONDecodeError) as e:
        crop_feedback={"recorded":False,"reason":"crop_storage_error","detail":str(e)}
    if req.vision_training_id is None and req.corrected_tiles is None:
        return hand_feedback
    return {**hand_feedback,"crop_feedback":crop_feedback}

@app.post("/v1/photo/analyze-corrected")
def photo_analyze_corrected(req: CorrectedPhotoRequest) -> dict:
    """Analyze a user-corrected hand after photo recognition review."""
    from jong_core.vision.correction import validate_corrected_hand_mpsz
    try:
        validate_corrected_hand_mpsz(req.hand)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    analysis=_run_analysis(
        req.hand, req.visible_tiles, req.draws, req.score_ev, req.dealer,
        req.round_wind, req.seat_wind, req.dora_indicators, req.red_dora_count,
        req.game_mode, req.ruleset, req.nuki_count, req.chip_count, req.chip_value_points, req.auto_nuki,
        req.aka_profile, req.red_supply,
        req.visible_zones.model_dump() if req.visible_zones else None,
    )
    # A successful human correction is high-value supervised vision data. Record the
    # de-identified hand pair in the same request so clients cannot accidentally
    # skip the separate feedback endpoint. Analysis remains authoritative even if
    # telemetry storage is unavailable.
    correction_feedback = {"recorded": False, "reason": "not_attempted"}
    try:
        correction_feedback = _record_vision_correction(VisionCorrectionFeedback(
            original_detected_hand=req.original_detected_hand,
            corrected_hand=req.hand,
            ruleset=req.ruleset,
            source="photo_analyze_corrected",
            vision_training_id=req.vision_training_id,
            corrected_tiles=req.corrected_tiles,
        ))
    except (OSError, ValueError) as e:
        correction_feedback = {"recorded": False, "reason": "storage_error", "detail": str(e)}
    try:
        crop_feedback=_commit_crop_labels(req.vision_training_id, req.corrected_tiles)
    except (OSError, ValueError, json.JSONDecodeError) as e:
        crop_feedback={"recorded":False,"reason":"crop_storage_error","detail":str(e)}
    return {
        "status":"analyzed_after_correction",
        "original_detected_hand":req.original_detected_hand,
        "corrected_hand":req.hand,
        "correction_feedback":correction_feedback,
        "crop_feedback":crop_feedback,
        "analysis":analysis,
    }


@app.post("/v1/analyze/instant")
def analyze_instant(req: HandRequest) -> dict:
    try:
        return analyze_hand_instant(req.hand, req.visible_tiles, req.draws or 3,
                                    game_mode=req.game_mode, ruleset=req.ruleset, nuki_count=req.nuki_count)
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

@app.post("/v1/analyze/hand")
def analyze(req: HandRequest) -> dict:
    return _run_analysis(
        req.hand, req.visible_tiles, req.draws, req.score_ev, req.dealer,
        req.round_wind, req.seat_wind, req.dora_indicators, req.red_dora_count,
        req.game_mode, req.ruleset, req.nuki_count, req.chip_count, req.chip_value_points, req.auto_nuki,
        req.aka_profile, req.red_supply,
        req.visible_zones.model_dump() if req.visible_zones else None,
    )



@app.post("/v1/analyze/two-stage")
def analyze_two_stage(req: HandRequest) -> dict:
    """Return instant estimate immediately and launch a bounded precision job."""
    try:
        requested_draws = int(req.draws or 3)
        precision_draws = min(requested_draws, 2)
        resolved_ruleset = get_ruleset(req.ruleset, req.game_mode).id

        instant = analyze_hand_instant(
            req.hand, req.visible_tiles, requested_draws,
            game_mode=req.game_mode, ruleset=req.ruleset, nuki_count=req.nuki_count,
            dora_indicators=req.dora_indicators,
        )

        # Calibration must compare the same horizon. For UI latency we still return
        # requested-horizon instant analysis, but derive corrections from a hidden
        # instant result at the precision worker's bounded horizon.
        calibration_instant = instant
        if requested_draws != precision_draws:
            calibration_instant = analyze_hand_instant(
                req.hand, req.visible_tiles, precision_draws,
                game_mode=req.game_mode, ruleset=req.ruleset, nuki_count=req.nuki_count,
                dora_indicators=req.dora_indicators,
            )

        instant = calibration_store.apply(
            instant,
            ruleset=resolved_ruleset,
            instant_draws=precision_draws,
            precision_draws=precision_draws,
        )
        job = precision_jobs.create({
            "hand": req.hand,
            "visible_tiles": req.visible_tiles,
            "draws": req.draws or 3,
            "dealer": req.dealer,
            "round_wind": req.round_wind,
            "seat_wind": req.seat_wind,
            "dora_indicators": req.dora_indicators,
            "red_dora_count": req.red_dora_count,
            "game_mode": req.game_mode,
            "ruleset": req.ruleset,
            "nuki_count": req.nuki_count,
            "chip_count": req.chip_count,
            "chip_value_points": req.chip_value_points,
            "auto_nuki": req.auto_nuki,
            "instant_result": calibration_instant,
            "resolved_ruleset": resolved_ruleset,
            "calibration_instant_draws": precision_draws,
        })
        precision_jobs.start(job.id)
        return {
            "stage": "instant",
            "instant": instant,
            "precision_job_id": job.id,
            "precision_status": job.status,
        }
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

@app.get("/v1/analyze/precision/{job_id}")
def precision_status(job_id: str) -> dict:
    data = precision_jobs.snapshot(job_id)
    if data is None:
        raise HTTPException(status_code=404, detail="precision job not found")
    return data


@app.get("/v1/calibration/status")
def calibration_status() -> dict:
    return calibration_store.stats()

@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True, "service": "jong-ai", "version": app.version}

# Frontend MVP
_frontend = Path(__file__).resolve().parents[2] / "frontend"
if _frontend.exists():
    app.mount("/", StaticFiles(directory=str(_frontend), html=True), name="frontend")
