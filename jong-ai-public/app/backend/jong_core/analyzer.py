from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable

from .tiles import parse_mpsz, format_tile, total_tiles
from .shanten import calculate_shanten
from .ev import estimate_probabilities
from .ev_score import estimate_score_ev
from .scoring import ScoreConfig
from .rules import get_ruleset, validate_counts_for_rules
from .sanma_transition import estimate_sanma_auto_nuki_ev
from .visible_state import build_visible_state
from .dora_rules import get_aka_profile, red_counts_from_mpsz, validate_red_hand, validate_visible_reds, red_normal_remaining_for_five, red_after_best_discard, FIVE_INDEXES


@dataclass
class UkeireTile:
    tile: str
    remaining: int
    next_shanten: int


@dataclass
class DiscardCandidate:
    discard: str
    shanten: int
    hand_type: str
    ukeire_total: int
    ukeire: list[UkeireTile]


def _visible_counts(hand: list[int], visible_tiles: Iterable[str]) -> list[int]:
    visible = hand.copy()
    for token in visible_tiles:
        c = parse_mpsz(token)
        for i in range(34):
            visible[i] += c[i]
            if visible[i] > 4:
                raise ValueError(f"visible count exceeds four for {format_tile(i)}")
    return visible


def ukeire_for_13(counts13: list[int], visible_counts: list[int], allowed_tiles: set[int] | frozenset[int] | None = None) -> tuple[int, str, list[UkeireTile]]:
    base = calculate_shanten(counts13)
    base_shanten = int(base["shanten"])
    result: list[UkeireTile] = []
    allowed = allowed_tiles if allowed_tiles is not None else range(34)
    for i in allowed:
        if visible_counts[i] >= 4:
            continue
        counts13[i] += 1
        nxt = calculate_shanten(counts13)
        counts13[i] -= 1
        if int(nxt["shanten"]) < base_shanten:
            result.append(UkeireTile(
                tile=format_tile(i),
                remaining=4 - visible_counts[i],
                next_shanten=int(nxt["shanten"]),
            ))
    return base_shanten, str(base["best_type"]), result


def analyze_counts(counts: list[int], visible_counts: list[int] | None = None, allowed_tiles: set[int] | frozenset[int] | None = None) -> dict:
    n = total_tiles(counts)
    if n not in (13, 14):
        raise ValueError(f"v0.1 supports 13 or 14 concealed tiles; got {n}")
    if visible_counts is None:
        visible_counts = counts.copy()

    current = calculate_shanten(counts)

    if n == 13:
        sh, hand_type, uke = ukeire_for_13(counts.copy(), visible_counts, allowed_tiles)
        return {
            "tile_count": n,
            "current": current,
            "ukeire_total": sum(x.remaining for x in uke),
            "ukeire": [asdict(x) for x in uke],
            "candidates": [],
        }

    candidates: list[DiscardCandidate] = []
    for i in range(34):
        if counts[i] == 0:
            continue
        reduced = counts.copy()
        reduced[i] -= 1
        sh, hand_type, uke = ukeire_for_13(reduced, visible_counts, allowed_tiles)
        candidates.append(DiscardCandidate(
            discard=format_tile(i),
            shanten=sh,
            hand_type=hand_type,
            ukeire_total=sum(x.remaining for x in uke),
            ukeire=uke,
        ))

    candidates.sort(key=lambda c: (c.shanten, -c.ukeire_total, c.discard))
    return {
        "tile_count": n,
        "current": current,
        "best_by_shanten_ukeire": candidates[0].discard if candidates else None,
        "candidates": [
            {
                "discard": c.discard,
                "shanten": c.shanten,
                "hand_type": c.hand_type,
                "ukeire_total": c.ukeire_total,
                "ukeire": [asdict(x) for x in c.ukeire],
            }
            for c in candidates
        ],
        "notice": "Ranking is shanten then ukeire only. EV is intentionally not implemented yet.",
    }


def _single_tile_index(token: str) -> int:
    c = parse_mpsz(token)
    if sum(c) != 1:
        raise ValueError(f"expected one tile, got: {token}")
    return next(i for i,n in enumerate(c) if n)


def analyze_hand(
    hand: str,
    visible_tiles: Iterable[str] = (),
    draws: int | None = None,
    *,
    score_ev: bool = False,
    dealer: bool = False,
    round_wind: str = "1z",
    seat_wind: str = "2z",
    dora_indicators: Iterable[str] = (),
    red_dora_count: int = 0,
    aka_profile: str = "one_each",
    red_supply: tuple[int,int,int] | None = None,
    game_mode: str | None = None,
    ruleset: str | None = None,
    nuki_count: int = 0,
    chip_count: int = 0,
    chip_value_points: int = 0,
    auto_nuki: bool = True,
    visible_zones: dict[str, Iterable[str]] | None = None,
) -> dict:
    visible_tiles=tuple(visible_tiles)
    visible_zones={str(k): tuple(v) for k,v in (visible_zones or {}).items()}
    zone_tiles=tuple(tok for tokens in visible_zones.values() for tok in tokens)
    all_visible_tiles=visible_tiles + zone_tiles
    counts = parse_mpsz(hand)
    profile = get_ruleset(ruleset, game_mode)
    aka=get_aka_profile(aka_profile, profile.players, red_supply=red_supply)
    hand_reds=red_counts_from_mpsz(hand)
    validate_red_hand(counts,hand_reds,aka)
    # v6.14: physical aka visibility is sourced from every public zone that can
    # contain a red five. Dora indicators live in the dead wall but are visible
    # and therefore must reduce both live red supply and red-draw EV.
    red_visible_by_source = {
        "hand": hand_reds,
        "visible_tiles": (0, 0, 0),
        "dora_indicators": (0, 0, 0),
    }
    for zone in visible_zones:
        red_visible_by_source[f"zone:{zone}"]=(0,0,0)
    source_tokens=[("visible_tiles", visible_tiles), ("dora_indicators", tuple(dora_indicators))]
    source_tokens += [(f"zone:{zone}", tokens) for zone,tokens in visible_zones.items()]
    for source, tokens in source_tokens:
        acc=[0,0,0]
        for tok in tokens:
            rr=red_counts_from_mpsz(tok)
            acc=[a+b for a,b in zip(acc,rr)]
        red_visible_by_source[source]=tuple(acc)
    visible_reds=[sum(red_visible_by_source[src][i] for src in red_visible_by_source) for i in range(3)]
    validate_visible_reds(tuple(visible_reds), aka)
    validate_counts_for_rules(counts, profile)
    if nuki_count < 0 or nuki_count > 4:
        raise ValueError("nuki_count must be 0..4")
    state = build_visible_state(
        counts, profile,
        visible_tiles=all_visible_tiles,
        dora_indicators=dora_indicators,
        nuki_count=nuki_count,
    )
    visible = list(state.counts)
    result = analyze_counts(counts, visible, profile.allowed_tiles)
    zone_counts = {zone: sum(sum(parse_mpsz(tok)) for tok in tokens) for zone,tokens in visible_zones.items()}
    # Preserve seat provenance in the analysis response. This is intentionally
    # descriptive in v6.16: it does not yet claim calibrated deal-in EV.
    opponent_public = {}
    for n in (1, 2, 3):
        dkey=f"opponent{n}_discards"; mkey=f"opponent{n}_melds"
        if dkey in visible_zones or mkey in visible_zones:
            opponent_public[str(n)] = {
                "discards": list(visible_zones.get(dkey, ())),
                "melds": list(visible_zones.get(mkey, ())),
            }
    result["visible_state"] = {
        "live_total": state.live_total,
        "source_counts": state.source_counts,
        "zones": zone_counts,
        "opponents": opponent_public,
    }
    result["ruleset"] = profile.public_dict()
    result["sanma_state"] = {
        "nuki_count": nuki_count,
        "nuki_dora_han": nuki_count * profile.nuki_dora_han,
        "chip_count": chip_count,
        "chip_value_points": chip_value_points,
        "auto_nuki": auto_nuki,
    }
    if draws is not None and total_tiles(counts) == 14:
        if score_ev and draws > 6:
            raise ValueError("v0.3 alpha score EV currently limits draws to 6 for runtime safety")

        result["dora_rules"]={"aka_profile":aka.id,"red_supply":aka.red_supply,"red_in_hand":hand_reds,"red_visible":tuple(visible_reds),"red_visible_by_source":red_visible_by_source}
        # v6.13: expose physical aka/normal composition of every five in ukeire.
        # Structural ukeire remains 34-type compatible, while the API now tells the
        # product exactly how many of those live fives are red.
        for candidate in result["candidates"]:
            for u in candidate.get("ukeire", []):
                ui = _single_tile_index(u["tile"])
                if ui in FIVE_INDEXES:
                    si = FIVE_INDEXES.index(ui)
                    red_left, normal_left = red_normal_remaining_for_five(
                        ui, visible[ui], visible_reds[si], aka
                    )
                    u["red_remaining"] = red_left
                    u["normal_remaining"] = normal_left
        cfg = ScoreConfig(
            dealer=dealer,
            round_wind=_single_tile_index(round_wind),
            seat_wind=_single_tile_index(seat_wind),
            riichi=True,
            tsumo=True,
            dora_indicators=tuple(_single_tile_index(x) for x in dora_indicators),
            # Explicit reds in the hand are tracked per candidate below. The legacy
            # manual bonus remains only for backward API compatibility.
            red_dora_count=red_dora_count,
            players=profile.players,
            tsumo_loss=profile.tsumo_loss,
            nuki_dora_count=nuki_count * profile.nuki_dora_han,
            chip_count=chip_count,
            chip_value_points=chip_value_points,
        )

        # v6.12: expose physically distinct normal/red five discards when both are held.
        # Structural shanten still uses 34 tile types, but commercial EV must not hide
        # the point-value difference between discarding 5s and r5s.
        expanded_candidates = []
        for base_candidate in result["candidates"]:
            discard_idx = _single_tile_index(base_candidate["discard"])
            if discard_idx in FIVE_INDEXES:
                si = FIVE_INDEXES.index(discard_idx)
                reds_here = hand_reds[si]
                normals_here = counts[discard_idx] - reds_here
                if reds_here > 0 and normals_here > 0:
                    normal_c = dict(base_candidate)
                    normal_c["physical_discard"] = base_candidate["discard"]
                    normal_c["is_red_discard"] = False
                    red_c = dict(base_candidate)
                    red_c["physical_discard"] = "r5" + "mps"[si]
                    red_c["discard"] = red_c["physical_discard"]
                    red_c["is_red_discard"] = True
                    expanded_candidates.extend((normal_c, red_c))
                    continue
                base_candidate["physical_discard"] = ("r5" + "mps"[si]) if reds_here > 0 else base_candidate["discard"]
                base_candidate["is_red_discard"] = bool(reds_here > 0 and normals_here == 0)
            else:
                base_candidate["physical_discard"] = base_candidate["discard"]
                base_candidate["is_red_discard"] = False
            expanded_candidates.append(base_candidate)
        result["candidates"] = expanded_candidates

        for candidate in result["candidates"]:
            discard_idx = _single_tile_index(candidate["discard"])
            reduced = counts.copy()
            reduced[discard_idx] -= 1

            if score_ev:
                if profile.players == 3 and profile.north_nuki and auto_nuki and aka.id == "none":
                    evr = estimate_sanma_auto_nuki_ev(
                        reduced, visible, draws, cfg, set(profile.allowed_tiles), auto_nuki=True
                    )
                    candidate["expected_future_nuki"] = round(evr.expected_future_nuki, 4)
                    candidate["expected_future_north_kept"] = round(evr.expected_future_north_kept, 4)
                    candidate["north_policy"] = evr.north_policy
                else:
                    if candidate.get("is_red_discard") and discard_idx in FIVE_INDEXES:
                        candidate_reds=list(hand_reds)
                        candidate_reds[FIVE_INDEXES.index(discard_idx)] -= 1
                        candidate_reds=tuple(candidate_reds)
                    else:
                        candidate_reds=red_after_best_discard(discard_idx,counts,hand_reds)
                    evr = estimate_score_ev(reduced, visible, draws, cfg, allowed_tiles=set(profile.allowed_tiles),
                                            red_hand_counts=candidate_reds, red_visible_counts=tuple(visible_reds),
                                            aka_profile=aka)
                    candidate["aka_profile"]=aka.id
                    candidate["red_dora_after_discard"]=sum(candidate_reds)
                candidate["draws"] = evr.draws
                candidate["tenpai_probability"] = evr.tenpai_probability
                candidate["win_probability"] = evr.win_probability
                candidate["expected_points"] = round(evr.expected_points, 3)
                candidate["average_win_points"] = round(evr.average_win_points, 1)
                candidate["ev_model"] = evr.model
            else:
                probs = estimate_probabilities(reduced, visible, draws, allowed_tiles=set(profile.allowed_tiles))
                candidate["draws"] = probs.draws
                candidate["tenpai_probability"] = probs.tenpai_probability
                candidate["win_probability"] = probs.win_probability
                candidate["probability_model"] = probs.model

        if score_ev:
            result["candidates"].sort(
                key=lambda c: (-c.get("expected_points", -1), -c.get("win_probability", -1),
                               -c.get("tenpai_probability", -1), c["shanten"],
                               -c["ukeire_total"], c["discard"])
            )
            result["best_by_ev"] = result["candidates"][0]["discard"] if result["candidates"] else None
            result["best_by_win_probability"] = max(result["candidates"], key=lambda c: c.get("win_probability", -1))["discard"] if result["candidates"] else None
            result["ranking_objective"] = "expected_points_then_win_then_tenpai_v6.14"
            result["education_contract_version"] = "v6.10"
            result["notice"] = (
                "v6.14 ranks score-EV candidates by expected points first and distinguishes normal/red five physical discards when both are held (win probability × scored winning branches), then win/tenpai probability. "
                "It models a subset of yaku/fu and is NOT yet production-grade scoring. "
                "Opponents, ron, calls, defense, ippatsu/ura and placement value are not modeled."
            )
        else:
            result["candidates"].sort(
                key=lambda c: (-c.get("win_probability", -1), -c.get("tenpai_probability", -1),
                               c["shanten"], -c["ukeire_total"], c["discard"])
            )
            result["best_by_probability"] = result["candidates"][0]["discard"] if result["candidates"] else None
            result["notice"] = (
                "v0.2 probabilities use a self-draw finite-horizon DP. "
                "Opponents, calls, ron, scoring EV and defense are not modeled yet."
            )
    return result
