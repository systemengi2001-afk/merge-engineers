"""Commercial-safe teacher distillation utilities inspired by Mortal's workflow.

This module deliberately does NOT import or copy Mortal/AGPL code.  It consumes
teacher outputs exported by a separately operated reviewer and learns a small,
auditable policy from JONG-owned features.  That boundary matters for commercial
licensing and makes teacher provenance explicit in every artifact.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
import json, math
from pathlib import Path
from typing import Iterable
import hashlib
import random

from .push_fold_policy import PushFoldState, evaluate_push_fold

ACTIONS=("fold","borderline","push")
FEATURES=("bias","sanma","dealer","tenpai","ishanten","good_shape","dora","danger","late_turn","opp_dealer","placement")


def encode_state(s: PushFoldState) -> list[float]:
    return [1.0, 1.0 if s.game_mode=="sanma" else 0.0, float(s.is_dealer),
            float(s.shanten==0), float(s.shanten==1), float(s.good_shape),
            min(6,max(0,s.dora_count))/6.0, min(1,max(0,float(s.danger))),
            max(0,min(18,s.turn)-9)/9.0, float(s.opponent_is_dealer),
            max(-1.0,min(1.0,float(s.placement_pressure)))]


def _softmax(z):
    m=max(z); e=[math.exp(v-m) for v in z]; d=sum(e)
    return [v/d for v in e]

@dataclass
class DistilledPushFoldModel:
    weights: list[list[float]]
    samples: int
    teacher: str="mortal-external"
    schema_version: int=1

    def predict_proba(self, s: PushFoldState) -> dict[str,float]:
        x=encode_state(s)
        p=_softmax([sum(wi*xi for wi,xi in zip(w,x)) for w in self.weights])
        return dict(zip(ACTIONS,p))

    def evaluate(self,s:PushFoldState)->dict:
        probs=self.predict_proba(s); action=max(ACTIONS,key=probs.get)
        return {"action":action,"probabilities":probs,"samples":self.samples,
                "teacher":self.teacher,"notice":"Distilled from external teacher outputs; not Mortal code/weights."}

    def save(self,path:str|Path):
        Path(path).write_text(json.dumps({"schema_version":self.schema_version,"teacher":self.teacher,
            "samples":self.samples,"actions":ACTIONS,"features":FEATURES,"weights":self.weights},indent=2),encoding="utf-8")

    @classmethod
    def load(cls,path:str|Path):
        d=json.loads(Path(path).read_text(encoding="utf-8"))
        if tuple(d["actions"])!=ACTIONS or tuple(d["features"])!=FEATURES: raise ValueError("incompatible distillation schema")
        return cls(d["weights"],int(d["samples"]),d.get("teacher","mortal-external"),int(d.get("schema_version",1)))


def train_push_fold_distillation(samples: Iterable[dict], *, epochs:int=300, lr:float=.12, l2:float=.002) -> DistilledPushFoldModel:
    rows=[]
    for row in samples:
        s=PushFoldState(**row["state"]); x=encode_state(s)
        if "teacher_probabilities" in row:
            target=[float(row["teacher_probabilities"].get(a,0.0)) for a in ACTIONS]
            total=sum(target)
            if total<=0: raise ValueError("teacher probabilities must have positive mass")
            target=[v/total for v in target]
        else:
            a=row["teacher_action"]
            if a not in ACTIONS: raise ValueError(f"unsupported teacher action: {a}")
            target=[1.0 if z==a else 0.0 for z in ACTIONS]
        rows.append((x,target))
    if len(rows)<6: raise ValueError("at least 6 teacher samples are required")
    w=[[0.0]*len(FEATURES) for _ in ACTIONS]
    for _ in range(max(1,epochs)):
        grad=[[0.0]*len(FEATURES) for _ in ACTIONS]
        for x,t in rows:
            p=_softmax([sum(a*b for a,b in zip(wk,x)) for wk in w])
            for k in range(len(ACTIONS)):
                for j,xj in enumerate(x): grad[k][j]+=(p[k]-t[k])*xj
        n=len(rows)
        for k in range(len(ACTIONS)):
            for j in range(len(FEATURES)):
                reg=0.0 if j==0 else l2*w[k][j]
                w[k][j]-=lr*(grad[k][j]/n+reg)
    return DistilledPushFoldModel(w,len(rows))


def load_teacher_jsonl(path:str|Path)->list[dict]:
    rows=[]
    for no,line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(),1):
        if not line.strip(): continue
        try: rows.append(json.loads(line))
        except json.JSONDecodeError as e: raise ValueError(f"invalid JSONL line {no}: {e}") from e
    return rows


def baseline_agreement(samples:Iterable[dict])->dict:
    total=agree=0
    for row in samples:
        if "teacher_action" not in row: continue
        pred=evaluate_push_fold(PushFoldState(**row["state"]))["action"]
        total+=1; agree+=pred==row["teacher_action"]
    return {"samples":total,"agreement":(agree/total if total else None)}


# v6.3: production gate.  Distillation is only useful commercially if unseen
# teacher positions improve over the deterministic JONG baseline.  Keep the
# validation split deterministic so CI/regression numbers are reproducible.
def split_teacher_samples(samples: Iterable[dict], *, validation_ratio: float=.2, seed: int=63):
    rows=list(samples)
    if not 0 < validation_ratio < .5: raise ValueError("validation_ratio must be between 0 and .5")
    if len(rows)<10: raise ValueError("at least 10 samples are required for a train/validation split")
    rng=random.Random(seed); rng.shuffle(rows)
    n=max(2,round(len(rows)*validation_ratio))
    return rows[n:], rows[:n]


def _teacher_action(row:dict)->str:
    if "teacher_action" in row: return row["teacher_action"]
    probs=row.get("teacher_probabilities") or {}
    if not probs: raise ValueError("teacher label is missing")
    return max(ACTIONS,key=lambda a:float(probs.get(a,0)))


def evaluate_distillation(model:DistilledPushFoldModel, samples:Iterable[dict])->dict:
    total=student_ok=baseline_ok=0; nll=0.0
    for row in samples:
        s=PushFoldState(**row["state"]); truth=_teacher_action(row)
        probs=model.predict_proba(s); pred=max(ACTIONS,key=probs.get)
        base=evaluate_push_fold(s)["action"]
        total+=1; student_ok+=pred==truth; baseline_ok+=base==truth
        nll-=math.log(max(1e-12,probs[truth]))
    if not total: raise ValueError("evaluation set is empty")
    sa=student_ok/total; ba=baseline_ok/total
    return {"samples":total,"student_agreement":sa,"baseline_agreement":ba,
            "agreement_lift":sa-ba,"teacher_nll":nll/total}


def train_validated_distillation(samples:Iterable[dict], *, validation_ratio:float=.2,
                                 seed:int=63, min_lift:float=0.0, **train_kwargs)->dict:
    train,valid=split_teacher_samples(samples,validation_ratio=validation_ratio,seed=seed)
    model=train_push_fold_distillation(train,**train_kwargs)
    metrics=evaluate_distillation(model,valid)
    # Gate prevents a weak distilled model from silently replacing a stronger baseline.
    passed=metrics["agreement_lift"] >= min_lift
    return {"model":model,"metrics":metrics,"gate_passed":passed,
            "train_samples":len(train),"validation_samples":len(valid),
            "gate":{"metric":"agreement_lift","minimum":min_lift}}


def safe_evaluate(model:DistilledPushFoldModel, s:PushFoldState, *, confidence_threshold:float=.55)->dict:
    """Use distilled action only when confidence clears the production threshold."""
    if not 0 <= confidence_threshold <= 1: raise ValueError("confidence_threshold must be in [0,1]")
    learned=model.evaluate(s); confidence=max(learned["probabilities"].values())
    if confidence >= confidence_threshold:
        return {**learned,"confidence":confidence,"source":"distilled"}
    baseline=evaluate_push_fold(s)
    return {**baseline,"confidence":confidence,"source":"baseline-fallback",
            "distilled_action":learned["action"],"distilled_probabilities":learned["probabilities"]}
