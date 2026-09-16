from __future__ import annotations
from .tiles import parse_mpsz, total_tiles, format_tile
from .analyzer import analyze_counts
from .ev_transition_instant import estimate_transition_aware
from .ev_instant import estimate_instant
from .rules import get_ruleset, validate_counts_for_rules
from .visible_state import build_visible_state
from .hybrid_policy_ev import structural_policy_prior, fuse_policy_with_ev


def analyze_hand_instant(hand: str, visible_tiles=(), draws: int=3, *, game_mode: str | None=None, ruleset: str | None=None, nuki_count: int=0, dora_indicators=()) -> dict:
    counts=parse_mpsz(hand)
    if total_tiles(counts)!=14:
        raise ValueError("instant EV currently expects 14 tiles")
    profile=get_ruleset(ruleset,game_mode)
    validate_counts_for_rules(counts,profile)
    state=build_visible_state(
        counts,profile,
        visible_tiles=visible_tiles,
        dora_indicators=dora_indicators,
        nuki_count=nuki_count,
    )
    visible=list(state.counts)
    result=analyze_counts(counts,visible,profile.allowed_tiles)
    result['ruleset']=profile.public_dict()
    result['sanma_state']={'nuki_count':nuki_count,'nuki_dora_han':nuki_count*profile.nuki_dora_han}
    result['visible_state']={'live_total':state.live_total,'source_counts':state.source_counts}
    # Fast UI estimate remains heuristic; nuki han is represented as a conservative point hint multiplier.
    nuki_hint_multiplier=min(4.0, 2.0 ** (nuki_count*profile.nuki_dora_han))
    total_live=state.live_total
    # Refine the competitive candidates with transition-aware enumeration.
    # At one draw the calculation is cheap enough for every candidate; for
    # longer horizons keep UI latency bounded by refining the top structural set.
    structural_order=sorted(
        result['candidates'],
        key=lambda x:(x['shanten'],-x['ukeire_total'],x['discard'])
    )
    # Multi-draw transition enumeration grows quickly. Keep the synchronous UI
    # path bounded: exact transition refinement is reserved for one draw; longer
    # horizons use the documented heuristic and are replaced by async precision EV.
    refine_count=len(structural_order) if draws <= 1 else 0
    refine_discards={x['discard'] for x in structural_order[:refine_count]}

    for c in result['candidates']:
        if c['discard'] in refine_discards:
            discard_idx=next(i for i in range(34) if counts[i] and format_tile(i)==c['discard'])
            hand13=counts.copy()
            hand13[discard_idx]-=1
            est=estimate_transition_aware(
                hand13,visible,draws,
                allowed_tiles=set(profile.allowed_tiles),
                average_win_points_hint=5200.0*nuki_hint_multiplier,
            )
            c['tenpai_probability']=est.tenpai_probability
            c['win_probability']=est.win_probability
            c['expected_points']=round(est.expected_points,1)
            c['average_win_points']=round(est.average_win_points,1)
            c['first_draw_states']=est.first_draw_states
            c['transition_refined']=True
            c['ev_model']=est.model
        else:
            est=estimate_instant(
                c['shanten'],c['ukeire_total'],draws,total_live,
                average_win_points_hint=5200.0*nuki_hint_multiplier,
            )
            c['tenpai_probability']=est.tenpai_probability
            c['win_probability']=est.win_probability
            c['expected_points']=round(est.expected_points,1)
            c['average_win_points']=round(est.average_win_points,1)
            c['transition_refined']=False
            c['ev_model']=est.model
    result['candidates'].sort(key=lambda c:(-c['expected_points'],-c['tenpai_probability'],c['shanten'],-c['ukeire_total'],c['discard']))
    result['best_by_ev']=result['candidates'][0]['discard'] if result['candidates'] else None
    # v6.5 hybrid layer: policy and mathematical EV remain separately inspectable.
    policy=structural_policy_prior(result['candidates'])
    result['hybrid']=fuse_policy_with_ev(result['candidates'],policy)
    result['best_by_hybrid']=result['hybrid']['best_action']
    result['policy_source']='jong_structural_prior_v6.5_untrained'
    result['notice']='Instant estimate for UI responsiveness; precision EV should replace it asynchronously. Hybrid score is not itself point EV.'
    return result
