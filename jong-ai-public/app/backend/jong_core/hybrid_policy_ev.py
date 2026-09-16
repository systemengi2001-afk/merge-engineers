"""JONG v6.5: fuse an AI discard policy with mathematical EV evidence.

The fusion is deliberately auditable: EV is converted to a within-position utility,
AI probabilities stay as probabilities, and disagreement is surfaced instead of hidden.
No third-party implementation is bundled here; the mathematical fields can be produced
by JONG or by a separately licensed/reference engine.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
from typing import Mapping, Sequence


@dataclass(frozen=True)
class HybridWeights:
    policy: float = 0.40
    points_ev: float = 0.40
    win: float = 0.10
    tenpai: float = 0.05
    ukeire: float = 0.05

    def normalized(self) -> "HybridWeights":
        vals=[self.policy,self.points_ev,self.win,self.tenpai,self.ukeire]
        if any((not math.isfinite(v)) or v < 0 for v in vals) or sum(vals) <= 0:
            raise ValueError("hybrid weights must be finite, non-negative, and have positive mass")
        s=sum(vals)
        return HybridWeights(*(v/s for v in vals))


def _minmax(values: Sequence[float]) -> list[float]:
    if not values: return []
    lo,hi=min(values),max(values)
    if math.isclose(lo,hi,rel_tol=0,abs_tol=1e-12): return [0.5]*len(values)
    return [(v-lo)/(hi-lo) for v in values]


def _normalize_policy(raw: Mapping[str,float], actions: Sequence[str]) -> dict[str,float]:
    extra=set(raw)-set(actions)
    if extra: raise ValueError(f"policy contains illegal/unavailable discards: {sorted(extra)}")
    vals={a:float(raw.get(a,0.0)) for a in actions}
    if any((not math.isfinite(v)) or v < 0 for v in vals.values()):
        raise ValueError("policy probabilities must be finite and non-negative")
    total=sum(vals.values())
    if total <= 0: raise ValueError("policy probabilities must have positive mass")
    return {a:v/total for a,v in vals.items()}


def fuse_policy_with_ev(candidates: Sequence[Mapping], policy_probabilities: Mapping[str,float], *,
                        weights: HybridWeights=HybridWeights()) -> dict:
    """Rank discard candidates using AI policy + mathematical evidence.

    Required candidate keys: discard. Optional evidence keys are expected_points,
    win_probability, tenpai_probability and ukeire_total. Missing evidence is neutral,
    allowing the same contract to work while precision EV is computed asynchronously.
    """
    if not candidates: raise ValueError("at least one candidate is required")
    actions=[str(c["discard"]) for c in candidates]
    if len(set(actions)) != len(actions): raise ValueError("candidate discards must be unique")
    p=_normalize_policy(policy_probabilities,actions)
    w=weights.normalized()
    ev=_minmax([float(c.get("expected_points",0.0)) for c in candidates])
    win=_minmax([float(c.get("win_probability",0.0)) for c in candidates])
    ten=_minmax([float(c.get("tenpai_probability",0.0)) for c in candidates])
    uke=_minmax([float(c.get("ukeire_total",0.0)) for c in candidates])
    rows=[]
    for i,c in enumerate(candidates):
        score=w.policy*p[actions[i]]+w.points_ev*ev[i]+w.win*win[i]+w.tenpai*ten[i]+w.ukeire*uke[i]
        rows.append({**dict(c),"ai_policy_probability":p[actions[i]],"ev_utility":ev[i],
                     "hybrid_score":score})
    rows.sort(key=lambda x:(-x["hybrid_score"],-x.get("expected_points",0),x["discard"]))
    policy_best=max(actions,key=p.get)
    ev_best=max(candidates,key=lambda c:(float(c.get("expected_points",0)),float(c.get("win_probability",0))))["discard"]
    return {"best_action":rows[0]["discard"],"policy_best":policy_best,"ev_best":ev_best,
            "policy_ev_disagree":policy_best != ev_best,"candidates":rows,
            "weights":w.__dict__,
            "model":"jong_hybrid_policy_math_ev_v6.5",
            "notice":"Hybrid rank is a JONG engineering score, not a calibrated point EV. expected_points remains the mathematical/reference EV field."}


def structural_policy_prior(candidates: Sequence[Mapping], *, temperature: float=.35) -> dict[str,float]:
    """Fallback JONG policy prior until a trained full-action policy is attached.

    It uses only structural hand evidence and is explicitly not labelled as Mortal/NAGA.
    """
    if temperature <= 0: raise ValueError("temperature must be > 0")
    if not candidates: raise ValueError("at least one candidate is required")
    logits=[]
    for c in candidates:
        sh=float(c.get("shanten",6)); uke=float(c.get("ukeire_total",0))
        win=float(c.get("win_probability",0)); ten=float(c.get("tenpai_probability",0))
        logits.append((-1.25*sh + .025*uke + 1.4*win + .7*ten)/temperature)
    m=max(logits); ex=[math.exp(x-m) for x in logits]; z=sum(ex)
    return {str(c["discard"]):e/z for c,e in zip(candidates,ex)}
