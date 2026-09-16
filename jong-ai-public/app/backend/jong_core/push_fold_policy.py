from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class PushFoldState:
    game_mode: str
    is_dealer: bool
    shanten: int
    good_shape: bool
    dora_count: int
    danger: float
    turn: int
    opponent_is_dealer: bool = False
    placement_pressure: float = 0.0  # -1 protect rank, +1 must gain rank


def evaluate_push_fold(state: PushFoldState) -> dict:
    """Mode-aware, auditable push/fold prior.

    This is intentionally a policy prior rather than a claim of learned-pro strength.
    danger is a calibrated-input slot (0..1); current callers may feed defense estimates.
    """
    if state.game_mode not in {'sanma','yonma'}:
        raise ValueError('game_mode must be sanma or yonma')
    if state.shanten < 0:
        raise ValueError('shanten must be >= 0')
    danger=max(0.0,min(1.0,float(state.danger)))
    turn=max(1,min(18,int(state.turn)))

    # Sanma has fewer tiles/players and materially higher hand values/speeds, so the
    # attack prior is higher. Keep this separate from yonma rather than sharing one knob.
    attack = 0.58 if state.game_mode == 'sanma' else 0.46
    attack += 0.18 if state.shanten == 0 else (0.08 if state.shanten == 1 else -0.10)
    attack += 0.08 if state.good_shape else -0.04
    attack += min(0.24, 0.055 * state.dora_count)
    attack += 0.06 if state.is_dealer else 0.0
    attack += 0.10 * max(-1.0,min(1.0,state.placement_pressure))
    # Late unfinished hands lose value.
    if state.shanten >= 1:
        attack -= max(0,turn-9) * (0.012 if state.game_mode=='sanma' else 0.015)

    risk_weight = 0.78 if state.game_mode == 'sanma' else 0.92
    if state.opponent_is_dealer:
        risk_weight += 0.12
    if state.is_dealer:
        risk_weight -= 0.06
    # Protecting placement should magnify risk aversion.
    if state.placement_pressure < 0:
        risk_weight += 0.12 * abs(state.placement_pressure)

    score=attack-risk_weight*danger
    if score >= 0.34:
        action='push'
    elif score >= 0.18:
        action='borderline'
    else:
        action='fold'
    return {
        'state': asdict(state), 'attack_score': round(attack,6),
        'risk_weight': round(risk_weight,6), 'policy_score': round(score,6),
        'action': action,
        'notice': 'Deterministic mode-specific policy prior; not yet trained/pro-calibrated. Use EV simulation/oracle data to calibrate thresholds.'
    }
