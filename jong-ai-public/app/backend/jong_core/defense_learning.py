from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable
import json
import math

from .tiles import parse_mpsz
from .rules import get_ruleset
from .defense_ev import (
    OpponentThreat,
    _single_index,
    _is_suji,
    _wall_factor,
    _matagi_factor,
    _riichi_timing_factor,
    _dora_targets,
    _dora_risk_factor,
    _risk_vs_one,
)


@dataclass(frozen=True)
class DefenseFeatureRow:
    ruleset: str
    candidate_tile: str
    opponent_player: int
    riichi: bool
    riichi_turn: int | None
    visible_count: int
    is_honor: bool
    is_terminal: bool
    is_suji: bool
    is_genbutsu: bool
    wall_factor: float
    matagi_factor: float
    timing_factor: float
    dora_factor: float
    is_dora: bool
    is_dora_neighbor: bool
    heuristic_probability: float


@dataclass(frozen=True)
class DefenseTrainingSample:
    sample_id: str
    features: DefenseFeatureRow
    deal_in: int
    sample_weight: float = 1.0
    source: str = 'unknown'
    verified: bool = False
    # Stable hand/round identity. Samples from one decision context must stay
    # in one split to prevent near-duplicate paifu states leaking into validation.
    group_id: str | None = None


@dataclass(frozen=True)
class CalibrationBin:
    lower: float
    upper: float
    samples: int
    weighted_samples: float
    raw_mean: float
    observed_rate: float
    calibrated_rate: float


@dataclass(frozen=True)
class BinnedDefenseCalibrator:
    version: str
    ruleset: str
    bins: tuple[CalibrationBin,...]
    total_samples: int
    verified_only: bool = True

    def predict(self, probability: float) -> float:
        p=max(0.0,min(1.0,float(probability)))
        for b in self.bins:
            if b.lower <= p < b.upper or (p == 1.0 and b.upper == 1.0):
                return max(0.0,min(1.0,b.calibrated_rate))
        return p


DEFAULT_EDGES=(0.0,0.01,0.02,0.035,0.05,0.075,0.10,0.15,0.20,0.35,1.0)


def _visible_counts(
    hand: str,
    visible_tiles: Iterable[str],
    dora_indicators: Iterable[str],
    threat: OpponentThreat,
) -> list[int]:
    counts=parse_mpsz(hand)
    for token in tuple(visible_tiles)+tuple(dora_indicators)+tuple(threat.discards):
        c=parse_mpsz(token)
        for i,n in enumerate(c):
            counts[i]+=n
            if counts[i] > 4:
                raise ValueError(f'visible count exceeds four for tile index {i}')
    return counts


def extract_defense_features(
    *,
    hand: str,
    candidate_tile: str,
    threat: OpponentThreat,
    visible_tiles: Iterable[str]=(),
    dora_indicators: Iterable[str]=(),
    ruleset: str='osaka_sanma_v1',
    game_mode: str='sanma',
) -> DefenseFeatureRow:
    profile=get_ruleset(ruleset,game_mode)
    tile=_single_index(candidate_tile)
    visible=_visible_counts(hand,visible_tiles,dora_indicators,threat)
    dora_targets=_dora_targets(dora_indicators,profile.allowed_tiles)
    discard_set={_single_index(x) for x in threat.discards}

    wall_factor,_=_wall_factor(tile,visible)
    matagi_factor,_=_matagi_factor(tile,threat)
    timing_factor,_=_riichi_timing_factor(threat)
    dora_factor,dora_reasons=_dora_risk_factor(tile,dora_targets)

    heuristic,_=_risk_vs_one(
        tile,threat,
        visible_counts=visible,
        dora_targets=dora_targets,
    )

    turn=None
    if threat.riichi:
        idx=threat.riichi_discard_index
        if idx is None:
            idx=max(0,len(threat.discards)-1)
        turn=idx+1

    rank=tile%9 if tile < 27 else None
    return DefenseFeatureRow(
        ruleset=profile.id,
        candidate_tile=candidate_tile,
        opponent_player=threat.player,
        riichi=bool(threat.riichi),
        riichi_turn=turn,
        visible_count=visible[tile],
        is_honor=tile>=27,
        is_terminal=(tile<27 and rank in (0,8)),
        is_suji=_is_suji(tile,discard_set),
        is_genbutsu=tile in discard_set,
        wall_factor=wall_factor,
        matagi_factor=matagi_factor,
        timing_factor=timing_factor,
        dora_factor=dora_factor,
        is_dora=('ドラ' in dora_reasons),
        is_dora_neighbor=('ドラそば' in dora_reasons),
        heuristic_probability=heuristic,
    )


def validate_training_sample(sample: DefenseTrainingSample) -> None:
    if sample.deal_in not in (0,1):
        raise ValueError('deal_in must be 0 or 1')
    if sample.sample_weight <= 0 or not math.isfinite(sample.sample_weight):
        raise ValueError('sample_weight must be finite and > 0')
    p=sample.features.heuristic_probability
    if not (0.0 <= p <= 1.0):
        raise ValueError('heuristic_probability must be 0..1')
    if sample.features.visible_count < 0 or sample.features.visible_count > 4:
        raise ValueError('visible_count must be 0..4')
    if not sample.sample_id:
        raise ValueError('sample_id is required')


def write_training_jsonl(path: str|Path, samples: Iterable[DefenseTrainingSample]) -> int:
    p=Path(path)
    p.parent.mkdir(parents=True,exist_ok=True)
    rows=list(samples)
    with p.open('w',encoding='utf-8') as f:
        for s in rows:
            validate_training_sample(s)
            f.write(json.dumps(asdict(s),ensure_ascii=False,separators=(',',':'))+'\n')
    return len(rows)


def read_training_jsonl(path: str|Path) -> list[DefenseTrainingSample]:
    out=[]
    with Path(path).open('r',encoding='utf-8') as f:
        for lineno,line in enumerate(f,1):
            line=line.strip()
            if not line:
                continue
            raw=json.loads(line)
            feat=DefenseFeatureRow(**raw['features'])
            s=DefenseTrainingSample(
                sample_id=str(raw['sample_id']),
                features=feat,
                deal_in=int(raw['deal_in']),
                sample_weight=float(raw.get('sample_weight',1.0)),
                source=str(raw.get('source','unknown')),
                verified=bool(raw.get('verified',False)),
                group_id=(str(raw['group_id']) if raw.get('group_id') is not None else None),
            )
            try:
                validate_training_sample(s)
            except ValueError as e:
                raise ValueError(f'line {lineno}: {e}') from e
            out.append(s)
    return out


def _pav_monotonic(values: list[float], weights: list[float]) -> list[float]:
    """Weighted pool-adjacent-violators for non-decreasing calibration rates."""
    blocks=[]
    for i,(v,w) in enumerate(zip(values,weights)):
        blocks.append([i,i,float(v),float(w)])
        while len(blocks)>=2 and blocks[-2][2] > blocks[-1][2]:
            b=blocks.pop()
            a=blocks.pop()
            total=a[3]+b[3]
            mean=(a[2]*a[3]+b[2]*b[3])/total if total else 0.0
            blocks.append([a[0],b[1],mean,total])
    out=[0.0]*len(values)
    for start,end,mean,_ in blocks:
        for i in range(start,end+1):
            out[i]=mean
    return out


def fit_binned_calibrator(
    samples: Iterable[DefenseTrainingSample],
    *,
    ruleset: str,
    edges: tuple[float,...]=DEFAULT_EDGES,
    verified_only: bool=True,
    laplace_alpha: float=1.0,
) -> BinnedDefenseCalibrator:
    if len(edges)<2 or edges[0]!=0.0 or edges[-1]!=1.0:
        raise ValueError('edges must start at 0.0 and end at 1.0')
    if any(a>=b for a,b in zip(edges,edges[1:])):
        raise ValueError('edges must be strictly increasing')

    rows=[]
    for s in samples:
        validate_training_sample(s)
        if s.features.ruleset != ruleset:
            continue
        if verified_only and not s.verified:
            continue
        rows.append(s)
    if not rows:
        raise ValueError('no matching training samples')

    raw_bins=[]
    rates=[]
    weights=[]
    for lo,hi in zip(edges,edges[1:]):
        bucket=[
            s for s in rows
            if lo <= s.features.heuristic_probability < hi
            or (hi==1.0 and s.features.heuristic_probability==1.0)
        ]
        w=sum(s.sample_weight for s in bucket)
        weighted_pos=sum(s.sample_weight*s.deal_in for s in bucket)
        weighted_raw=sum(s.sample_weight*s.features.heuristic_probability for s in bucket)
        if w:
            raw_mean=weighted_raw/w
            # light smoothing prevents 0/1 extremes on tiny buckets
            observed=(weighted_pos+laplace_alpha)/(w+2*laplace_alpha)
        else:
            raw_mean=(lo+hi)/2
            observed=raw_mean
        raw_bins.append((lo,hi,bucket,w,raw_mean,observed))
        rates.append(observed)
        weights.append(max(w,1e-9))

    calibrated=_pav_monotonic(rates,weights)

    bins=[]
    for (lo,hi,bucket,w,raw_mean,observed),cal in zip(raw_bins,calibrated):
        bins.append(CalibrationBin(
            lower=lo,upper=hi,
            samples=len(bucket),
            weighted_samples=w,
            raw_mean=raw_mean,
            observed_rate=observed,
            calibrated_rate=cal,
        ))

    return BinnedDefenseCalibrator(
        version='defense-calibrator-v4.4',
        ruleset=ruleset,
        bins=tuple(bins),
        total_samples=len(rows),
        verified_only=verified_only,
    )


def save_calibrator(path: str|Path, model: BinnedDefenseCalibrator) -> None:
    Path(path).write_text(
        json.dumps(asdict(model),ensure_ascii=False,indent=2),
        encoding='utf-8'
    )


def load_calibrator(path: str|Path) -> BinnedDefenseCalibrator:
    raw=json.loads(Path(path).read_text(encoding='utf-8'))
    return BinnedDefenseCalibrator(
        version=raw['version'],
        ruleset=raw['ruleset'],
        bins=tuple(CalibrationBin(**x) for x in raw['bins']),
        total_samples=int(raw['total_samples']),
        verified_only=bool(raw.get('verified_only',True)),
    )


def _auc(y: list[int], p: list[float], w: list[float]) -> float|None:
    pos=sum(ww for yy,ww in zip(y,w) if yy==1)
    neg=sum(ww for yy,ww in zip(y,w) if yy==0)
    if pos<=0 or neg<=0:
        return None
    order=sorted(range(len(y)),key=lambda i:p[i])
    # pairwise weighted AUC with tie=0.5; O(n^2) but evaluation sets here are modest.
    good=0.0
    total=pos*neg
    for i in order:
        if y[i]!=1:
            continue
        for j in order:
            if y[j]!=0:
                continue
            if p[i]>p[j]:
                good += w[i]*w[j]
            elif p[i]==p[j]:
                good += 0.5*w[i]*w[j]
    return good/total


def evaluate_defense_calibration(
    samples: Iterable[DefenseTrainingSample],
    *,
    calibrator: BinnedDefenseCalibrator|None=None,
    ruleset: str|None=None,
    verified_only: bool=True,
) -> dict:
    rows=[]
    for s in samples:
        validate_training_sample(s)
        if ruleset is not None and s.features.ruleset != ruleset:
            continue
        if verified_only and not s.verified:
            continue
        rows.append(s)
    if not rows:
        return {'samples':0}

    y=[s.deal_in for s in rows]
    raw=[s.features.heuristic_probability for s in rows]
    pred=[calibrator.predict(x) if calibrator else x for x in raw]
    w=[s.sample_weight for s in rows]
    total=sum(w)

    def weighted_mean(vals):
        return sum(v*ww for v,ww in zip(vals,w))/total

    brier=weighted_mean([(pp-yy)**2 for pp,yy in zip(pred,y)])
    raw_brier=weighted_mean([(pp-yy)**2 for pp,yy in zip(raw,y)])
    eps=1e-9
    logloss=weighted_mean([
        -(yy*math.log(max(eps,min(1-eps,pp)))+(1-yy)*math.log(max(eps,min(1-eps,1-pp))))
        for pp,yy in zip(pred,y)
    ])

    # Expected calibration error over the same stable bins.
    ece=0.0
    bin_rows=[]
    for lo,hi in zip(DEFAULT_EDGES,DEFAULT_EDGES[1:]):
        idx=[
            i for i,pp in enumerate(pred)
            if lo <= pp < hi or (hi==1.0 and pp==1.0)
        ]
        if not idx:
            continue
        bw=sum(w[i] for i in idx)
        pmean=sum(pred[i]*w[i] for i in idx)/bw
        ymean=sum(y[i]*w[i] for i in idx)/bw
        ece += (bw/total)*abs(pmean-ymean)
        bin_rows.append({
            'lower':lo,'upper':hi,'samples':len(idx),
            'predicted_mean':pmean,'observed_rate':ymean,
        })

    return {
        'samples':len(rows),
        'weighted_samples':total,
        'ruleset':ruleset,
        'verified_only':verified_only,
        'raw_brier':raw_brier,
        'brier':brier,
        'brier_improvement':raw_brier-brier,
        'logloss':logloss,
        'ece':ece,
        'auc':_auc(y,pred,w),
        'bins':bin_rows,
        'model_version':calibrator.version if calibrator else 'raw-heuristic',
    }


def fit_validate_defense_calibrator(
    samples: Iterable[DefenseTrainingSample], *, ruleset: str,
    validation_fraction: float = 0.2, verified_only: bool = True,
    min_validation_samples: int = 20, max_brier_regression: float = 0.0,
    max_ece: float = 0.10,
) -> dict:
    """Deterministic leakage-resistant fit/validation gate keyed by sample_id.

    The model is fitted only on the train partition. Promotion is allowed only when
    held-out validation does not regress Brier score and ECE is below the requested cap.
    This is infrastructure validation, not evidence that production deal-in risk is calibrated.
    """
    if not (0.05 <= validation_fraction <= 0.5):
        raise ValueError('validation_fraction must be 0.05..0.5')
    rows=[]; seen=set()
    for s in samples:
        validate_training_sample(s)
        if s.features.ruleset != ruleset or (verified_only and not s.verified):
            continue
        if s.sample_id in seen:
            raise ValueError(f'duplicate sample_id: {s.sample_id}')
        seen.add(s.sample_id); rows.append(s)
    if len(rows) < max(2, min_validation_samples + 1):
        raise ValueError('insufficient matching samples for held-out validation')
    # Group-aware stable split: paifu extraction commonly emits many candidate
    # tiles from the same decision state. Splitting those rows independently leaks
    # near-identical board information into validation and overstates quality.
    import hashlib
    groups={}
    for s in rows:
        key=s.group_id or s.sample_id
        groups.setdefault(key,[]).append(s)
    ranked_groups=sorted(groups.items(),key=lambda kv: hashlib.sha256(kv[0].encode('utf-8')).digest())
    target=max(min_validation_samples, int(round(len(rows)*validation_fraction)))
    validation=[]; train=[]
    for _,grp in ranked_groups:
        if len(validation) < target:
            validation.extend(grp)
        else:
            train.extend(grp)
    if not train or len(validation) < min_validation_samples:
        raise ValueError('insufficient independent groups for held-out validation')
    model=fit_binned_calibrator(train,ruleset=ruleset,verified_only=False)
    ev=evaluate_defense_calibration(validation,calibrator=model,ruleset=ruleset,verified_only=False)
    passed=(ev['brier'] <= ev['raw_brier'] + max_brier_regression and ev['ece'] <= max_ece)
    return {
        'model': model, 'evaluation': ev, 'promotion_passed': passed,
        'split': {'strategy':'sha256-group-id-v2','train_samples':len(train),'validation_samples':len(validation),'train_groups':len({x.group_id or x.sample_id for x in train}),'validation_groups':len({x.group_id or x.sample_id for x in validation})},
        'gate': {'max_brier_regression':max_brier_regression,'max_ece':max_ece},
    }


def extract_training_samples_from_snapshots(snapshots: Iterable[dict]) -> list[DefenseTrainingSample]:
    """Convert verified normalized paifu decision snapshots into defense samples.

    This intentionally does not guess hidden counterfactuals: a row is emitted only
    for the tile actually discarded, with deal_in taken from the recorded outcome.
    Raw Tenhou/Majsoul parsing belongs in an adapter; this normalized boundary keeps
    provenance explicit and prevents invented labels.
    """
    out=[]
    seen=set()
    for n,raw in enumerate(snapshots,1):
        required=('snapshot_id','round_id','hand','discard','opponent','deal_in')
        missing=[k for k in required if k not in raw]
        if missing:
            raise ValueError(f'snapshot {n}: missing {missing[0]}')
        sid=str(raw['snapshot_id']); gid=str(raw['round_id'])
        if sid in seen:
            raise ValueError(f'duplicate snapshot_id: {sid}')
        seen.add(sid)
        opp=raw['opponent']
        try:
            threat=OpponentThreat(
                player=int(opp['player']), riichi=bool(opp.get('riichi',False)),
                discards=tuple(opp.get('discards',())),
                estimated_hand_value=float(opp.get('estimated_hand_value',8000)),
                riichi_discard_index=opp.get('riichi_discard_index'),
                tedashi_flags=tuple(opp.get('tedashi_flags',())),
            )
            feat=extract_defense_features(
                hand=str(raw['hand']), candidate_tile=str(raw['discard']), threat=threat,
                visible_tiles=tuple(raw.get('visible_tiles',())),
                dora_indicators=tuple(raw.get('dora_indicators',())),
                ruleset=str(raw.get('ruleset','osaka_sanma_v1')),
                game_mode=str(raw.get('game_mode','sanma')),
            )
            sample=DefenseTrainingSample(
                sample_id=sid, features=feat, deal_in=int(raw['deal_in']),
                sample_weight=float(raw.get('sample_weight',1.0)),
                source=str(raw.get('source','normalized-paifu-snapshot')),
                verified=bool(raw.get('verified',False)), group_id=gid,
            )
            validate_training_sample(sample)
        except (KeyError,TypeError,ValueError) as e:
            raise ValueError(f'snapshot {n}: {e}') from e
        if not sample.verified:
            raise ValueError(f'snapshot {n}: verified=true required for outcome labels')
        out.append(sample)
    return out


def snapshots_from_event_log(payload: dict) -> list[dict]:
    """Build verified defense snapshots from a normalized chronological event log.

    Input is intentionally provider-neutral. Each round contains an initial hand for
    the hero and chronological events (discard/riichi/ron). Only the hero's observed
    discards are emitted. A discard is labelled deal_in=1 only when the immediately
    following terminal ron event explicitly names that discard event as `from_event`.
    This avoids inferring counterfactual outcomes from hidden hands.
    """
    if not isinstance(payload,dict) or not isinstance(payload.get('rounds'),list):
        raise ValueError('event log requires rounds[]')
    source=str(payload.get('source','normalized-event-log'))
    out=[]; snapshot_ids=set()
    for rn,rnd in enumerate(payload['rounds'],1):
        if not isinstance(rnd,dict): raise ValueError(f'round {rn}: object required')
        for k in ('round_id','hero_player','initial_hand','events'):
            if k not in rnd: raise ValueError(f'round {rn}: missing {k}')
        rid=str(rnd['round_id']); hero=int(rnd['hero_player']); events=rnd['events']
        if not isinstance(events,list): raise ValueError(f'round {rn}: events must be list')
        discards={}; riichi_idx={}; tedashi={}; event_ids=set()
        # Pre-index explicit ron provenance so labels do not depend on lookahead guesses.
        ron_from={}
        for ei,e in enumerate(events):
            if not isinstance(e,dict): raise ValueError(f'round {rn} event {ei}: object required')
            eid=str(e.get('event_id',''))
            if not eid: raise ValueError(f'round {rn} event {ei}: event_id required')
            if eid in event_ids: raise ValueError(f'round {rn}: duplicate event_id: {eid}')
            event_ids.add(eid)
            if e.get('type')=='ron':
                frm=e.get('from_event')
                if not frm: raise ValueError(f'round {rn} event {eid}: ron requires from_event')
                ron_from.setdefault(str(frm),[]).append(e)
        # Keep the hero's concealed hand synchronized with observed draw/discard events.
        # Training on the round's initial hand for later decisions silently corrupts
        # shanten/shape-derived defense features, so malformed chronology fails closed.
        from .tiles import parse_mpsz, counts_to_tiles, tile_index
        hero_counts=parse_mpsz(str(rnd['initial_hand']))
        def _tile_idx(tile):
            c=parse_mpsz(str(tile))
            if sum(c)!=1: raise ValueError(f'round {rn}: event tile must contain exactly one tile: {tile}')
            return next(i for i,n in enumerate(c) if n)
        def _hero_hand():
            return ''.join(counts_to_tiles(hero_counts))
        visible=list(rnd.get('visible_tiles',()))
        dora=list(rnd.get('dora_indicators',()))
        for ei,e in enumerate(events):
            typ=e.get('type'); eid=str(e['event_id'])
            if typ=='dora':
                if 'tile' not in e: raise ValueError(f'round {rn} event {eid}: dora tile required')
                dora.append(str(e['tile'])); continue
            if typ=='riichi':
                p=int(e['player']); riichi_idx[p]=len(discards.get(p,[])); continue
            if typ=='discard':
                p=int(e['player']); tile=str(e['tile'])
                # Snapshot state is before this discard and contains only information
                # publicly available at that decision.
                if p==hero:
                    opponents=[]
                    for op in sorted((set(discards)|set(riichi_idx))- {hero}):
                        opponents.append({'player':op,'riichi':op in riichi_idx,
                            'discards':list(discards.get(op,[])),
                            'riichi_discard_index':riichi_idx.get(op),
                            'tedashi_flags':list(tedashi.get(op,[]))})
                    # One sample per threatening opponent, because runtime calibration
                    # predicts deal-in probability versus one opponent at a time.
                    rons=ron_from.get(eid,[])
                    ron_winners={int(x['winner']) for x in rons if 'winner' in x}
                    for opp in opponents:
                        sid=f'{rid}:hero{hero}:{eid}:vs{opp["player"]}'
                        if sid in snapshot_ids: raise ValueError(f'duplicate snapshot_id: {sid}')
                        snapshot_ids.add(sid)
                        out.append({'snapshot_id':sid,'round_id':rid,'hand':_hero_hand(),'discard':tile,
                            'opponent':opp,'deal_in':int(opp['player'] in ron_winners),
                            'visible_tiles':list(visible),'dora_indicators':list(dora),
                            'ruleset':str(rnd.get('ruleset',payload.get('ruleset','osaka_sanma_v1'))),
                            'game_mode':str(rnd.get('game_mode',payload.get('game_mode','sanma'))),
                            'verified':True,'source':source})
                if p==hero:
                    ti=_tile_idx(tile)
                    if hero_counts[ti] <= 0:
                        raise ValueError(f'round {rn} event {eid}: hero discard {tile} not present in hand')
                    hero_counts[ti]-=1
                discards.setdefault(p,[]).append(tile); tedashi.setdefault(p,[]).append(bool(e.get('tedashi',True)))
                visible.append(tile)
            elif typ=='draw':
                p=int(e['player'])
                if p==hero:
                    if 'tile' not in e: raise ValueError(f'round {rn} event {eid}: hero draw tile required')
                    ti=_tile_idx(e['tile'])
                    if hero_counts[ti] >= 4: raise ValueError(f'round {rn} event {eid}: impossible fifth copy of {e["tile"]}')
                    hero_counts[ti]+=1
            elif typ=='call':
                # Provider adapters normalize calls by explicitly listing the tiles
                # removed from the caller's concealed hand.  This works uniformly for
                # chi/pon/daiminkan (called tile is external), ankan (four consumed),
                # and kakan (one consumed).  We deliberately do not guess consumed
                # tiles from call_type because red fives make that lossy.
                if 'player' not in e: raise ValueError(f'round {rn} event {eid}: call player required')
                p=int(e['player'])
                call_type=str(e.get('call_type','')).lower()
                if call_type not in ('chi','pon','daiminkan','ankan','kakan'):
                    raise ValueError(f'round {rn} event {eid}: unsupported call_type {call_type}')
                consumed=e.get('consumed_tiles')
                if not isinstance(consumed,list) or not consumed:
                    raise ValueError(f'round {rn} event {eid}: call consumed_tiles[] required')
                consumed_idx=[]
                for ct in consumed:
                    consumed_idx.append((_tile_idx(ct),str(ct)))
                if p==hero:
                    need={}
                    for ti,_ in consumed_idx: need[ti]=need.get(ti,0)+1
                    for ti,n in need.items():
                        if hero_counts[ti] < n:
                            raise ValueError(f'round {rn} event {eid}: hero call consumes tile not present in hand')
                    for ti,_ in consumed_idx: hero_counts[ti]-=1
                # Tiles exposed from the concealed hand become public information.
                # The called discard itself is already present in `visible` from its
                # discard event, so only consumed tiles are added here.
                visible.extend(ct for _,ct in consumed_idx)
            elif typ not in ('ron','round_end'):
                raise ValueError(f'round {rn} event {eid}: unsupported type {typ}')
        unknown=set(ron_from)-event_ids
        if unknown: raise ValueError(f'round {rn}: ron from_event not found: {sorted(unknown)[0]}')
    return out


def tenhou_xml_to_event_log(xml_text: str, *, hero_player: int = 0,
                            ruleset: str = 'sanma_standard', game_mode: str = 'sanma') -> dict:
    """Strict Tenhou mjlog XML -> normalized event log adapter (v6.27).

    Supports INIT, draw/discard, REACH, AGARI and verified N meld decoding for chi,
    pon, daiminkan, ankan and kakan. Open calls are cross-checked against the exact
    physical source discard id; inconsistent logs fail closed instead of corrupting state.
    Physical Tenhou tile ids are normalized to 34-type JONG notation. Aka identity is
    not retained by this adapter yet, matching the structural defense feature boundary.
    """
    import xml.etree.ElementTree as ET
    if not isinstance(xml_text, str) or not xml_text.strip():
        raise ValueError('Tenhou XML text required')
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise ValueError(f'invalid Tenhou XML: {e}') from e
    if root.tag not in ('mjloggm', 'mjlog'):
        raise ValueError(f'unsupported Tenhou root: {root.tag}')
    if hero_player not in (0,1,2,3):
        raise ValueError('hero_player must be 0..3')
    from .tiles import format_tile
    def tile_from_id(raw):
        try: tid=int(raw)
        except (TypeError,ValueError): raise ValueError(f'invalid Tenhou tile id: {raw}')
        if not 0 <= tid < 136: raise ValueError(f'Tenhou tile id out of range: {tid}')
        return format_tile(tid//4)
    def decode_meld(m_raw, who, last_discard_ids):
        try: m=int(m_raw)
        except (TypeError,ValueError): raise ValueError(f'invalid Tenhou meld bitfield: {m_raw}')
        rel=m & 0x3
        source=(who + rel) % 4
        if m & 0x4:  # chi
            t=(m >> 10) & 0x3f; called_pos=t % 3; base=t // 3
            base=(base // 7) * 9 + (base % 7)
            ids=[(base+i)*4 + ((m >> (3+2*i)) & 0x3) for i in range(3)]
            called=ids[called_pos]
            typ='chi'; consumed=[x for i,x in enumerate(ids) if i != called_pos]
        elif m & 0x18:  # pon / kakan
            t=(m >> 9) & 0x7f; called_pos=t % 3; tile_type=t // 3
            unused=(m >> 5) & 0x3; all_ids=[tile_type*4+i for i in range(4)]
            if m & 0x8:
                ids=[x for i,x in enumerate(all_ids) if i != unused]
                called=ids[called_pos]; typ='pon'; consumed=[x for i,x in enumerate(ids) if i != called_pos]
            else:
                typ='kakan'; called=None; consumed=[all_ids[unused]]
        else:  # kan: rel=0 ankan, otherwise daiminkan
            hai=(m >> 8) & 0xff; tile_type=hai // 4; all_ids=[tile_type*4+i for i in range(4)]
            if rel == 0:
                typ='ankan'; called=None; consumed=all_ids
            else:
                typ='daiminkan'; called=hai; consumed=[x for x in all_ids if x != called]
        if typ in ('chi','pon','daiminkan'):
            if source == who: raise ValueError('Tenhou open meld has invalid self source')
            prior=last_discard_ids.get(source)
            if prior is None: raise ValueError('Tenhou open meld has no source discard')
            if prior != called: raise ValueError('Tenhou meld called tile does not match source discard')
        return {'type':'call','player':who,'call_type':typ,
                'consumed_tiles':[tile_from_id(x) for x in consumed],
                **({'called_tile':tile_from_id(called)} if called is not None else {})}

    rounds=[]; cur=None; seq=0; last_discard_by_player={}; last_discard_ids={}
    draw_prefix={'T':0,'U':1,'V':2,'W':3}; discard_prefix={'D':0,'E':1,'F':2,'G':3}
    for node in root:
        tag=node.tag
        if tag=='INIT':
            if cur is not None: rounds.append(cur)
            hai_key=f'hai{hero_player}'
            if hai_key not in node.attrib: raise ValueError(f'Tenhou INIT missing {hai_key}')
            ids=[x for x in node.attrib[hai_key].split(',') if x!='']
            if not ids: raise ValueError(f'Tenhou INIT empty {hai_key}')
            seq=0; last_discard_by_player={}; last_discard_ids={}
            seed=node.attrib.get('seed','')
            cur={'round_id':f'tenhou:{len(rounds)}:{seed}','hero_player':hero_player,
                 'initial_hand':''.join(tile_from_id(x) for x in ids),'ruleset':ruleset,
                 'game_mode':game_mode,'events':[]}
            continue
        if cur is None:
            # GO/UN/TAIKYOKU metadata before the first hand is intentionally ignored.
            continue
        seq+=1
        def emit(obj):
            obj={'event_id':f'e{seq}',**obj}; cur['events'].append(obj); return obj['event_id']
        if len(tag)>=2 and tag[0] in draw_prefix and tag[1:].isdigit():
            emit({'type':'draw','player':draw_prefix[tag[0]],'tile':tile_from_id(tag[1:])})
        elif len(tag)>=2 and tag[0] in discard_prefix and tag[1:].isdigit():
            p=discard_prefix[tag[0]]; eid=emit({'type':'discard','player':p,'tile':tile_from_id(tag[1:])})
            last_discard_by_player[p]=eid; last_discard_ids[p]=int(tag[1:])
        elif tag=='REACH':
            if node.attrib.get('step')=='1':
                if 'who' not in node.attrib: raise ValueError('Tenhou REACH missing who')
                emit({'type':'riichi','player':int(node.attrib['who'])})
            else:
                seq-=1  # step=2 is payment metadata, not a normalized event.
        elif tag=='DORA':
            if 'hai' not in node.attrib: raise ValueError('Tenhou DORA missing hai')
            emit({'type':'dora','tile':tile_from_id(node.attrib['hai'])})
        elif tag=='N':
            if 'who' not in node.attrib or 'm' not in node.attrib: raise ValueError('Tenhou N missing who/m')
            who=int(node.attrib['who'])
            if who not in (0,1,2,3): raise ValueError('Tenhou N who out of range')
            emit(decode_meld(node.attrib['m'], who, last_discard_ids))
        elif tag=='AGARI':
            if 'who' not in node.attrib or 'fromWho' not in node.attrib:
                raise ValueError('Tenhou AGARI missing who/fromWho')
            who=int(node.attrib['who']); frm=int(node.attrib['fromWho'])
            if who != frm:
                from_event=last_discard_by_player.get(frm)
                if not from_event: raise ValueError('Tenhou ron has no preceding source discard')
                emit({'type':'ron','winner':who,'from_player':frm,'from_event':from_event})
            else:
                emit({'type':'round_end','reason':'tsumo','winner':who})
        elif tag in ('RYUUKYOKU','BYE'):
            emit({'type':'round_end','reason':'ryuukyoku' if tag=='RYUUKYOKU' else 'bye'})
        elif tag in ('GO','UN','TAIKYOKU','SHUFFLE'):
            seq-=1
        else:
            raise ValueError(f'unsupported Tenhou tag in round: {tag}')
    if cur is not None: rounds.append(cur)
    if not rounds: raise ValueError('Tenhou XML contains no INIT rounds')
    return {'source':'tenhou-mjlog-xml-v1','ruleset':ruleset,'game_mode':game_mode,'rounds':rounds}


def tenhou_xml_corpus_to_training_samples(xml_documents: Iterable[str], *, ruleset: str = 'sanma_standard', game_mode: str = 'sanma', players: tuple[int, ...] = (0,1,2), allow_partial: bool = False) -> dict:
    """Convert a Tenhou XML corpus into leakage-safe verified training rows.

    Every selected seat is replayed independently, but all seats from the same physical
    hand retain one shared round/group id so held-out splitting cannot leak the same
    board across train and validation. Invalid documents fail the whole batch by default;
    allow_partial=True is explicit and returns rejection provenance.
    """
    docs=list(xml_documents)
    if not docs: raise ValueError('Tenhou corpus requires at least one XML document')
    if not players or any(p not in (0,1,2,3) for p in players) or len(set(players)) != len(players):
        raise ValueError('players must be unique Tenhou seats 0..3')
    rows=[]; rejected=[]
    import hashlib
    for di,xml in enumerate(docs):
        doc_key=hashlib.sha256(xml.encode('utf-8')).hexdigest()[:16] if isinstance(xml,str) else f'index-{di}'
        try:
            doc_rows=[]
            for hero in players:
                payload=tenhou_xml_to_event_log(xml,hero_player=hero,ruleset=ruleset,game_mode=game_mode)
                # Namespace physical hands by document while deliberately NOT by hero:
                # all seat views of one hand must remain in the same validation group.
                for rnd in payload['rounds']:
                    rnd['round_id']=f'tenhou-doc:{doc_key}:{rnd["round_id"].split(":",2)[-1]}'
                doc_rows.extend(extract_training_samples_from_snapshots(snapshots_from_event_log(payload)))
            rows.extend(doc_rows)
        except (ValueError,TypeError,KeyError) as e:
            rejected.append({'document_index':di,'document_key':doc_key,'error':str(e)})
            if not allow_partial:
                raise ValueError(f'Tenhou corpus document {di} rejected: {e}') from e
    # sample ids must be globally unique even when a caller accidentally repeats a log.
    seen=set()
    for r in rows:
        if r.sample_id in seen: raise ValueError(f'duplicate corpus sample_id: {r.sample_id}')
        seen.add(r.sample_id)
    return {'samples':rows,'documents':len(docs),'accepted_documents':len(docs)-len(rejected),'rejected':rejected,'players':list(players),'group_policy':'physical-hand-across-seats-v1'}
