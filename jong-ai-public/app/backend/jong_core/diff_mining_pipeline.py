from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable
import json

from .benchmark import compare_case, summary_dict
from .error_mining import mine_report
from .diagnostics import diagnose_report
from .regression_factory import select_priority_fixtures, write_fixture_json


TRUSTED_REFERENCE_SOURCES = {
    'mahjong-cpp-live',
    'mahjong-cpp-snapshot',
    'verified-human-fixture',
}


@dataclass(frozen=True)
class ComparisonInput:
    case_id: str
    case: dict
    jong: dict
    oracle: dict
    reference_source: str
    reference_verified: bool


@dataclass(frozen=True)
class MiningDecision:
    case_id: str
    severity: float
    primary_layer: str
    regression_eligible: bool
    reason: str
    reference_source: str


def _case_map(inputs: Iterable[ComparisonInput]) -> dict[str,dict]:
    return {x.case_id: dict(x.case) for x in inputs}


def _oracle_map(inputs: Iterable[ComparisonInput]) -> dict[str,dict]:
    return {x.case_id: dict(x.oracle) for x in inputs}


def _is_trusted(x: ComparisonInput) -> bool:
    return bool(x.reference_verified and x.reference_source in TRUSTED_REFERENCE_SOURCES)


def build_diff_mining_report(
    inputs: Iterable[ComparisonInput],
    *,
    max_cases: int=1000,
    ev_threshold: float=500.0,
    win_threshold: float=0.05,
    tenpai_threshold: float=0.05,
    ukeire_threshold: float=2.0,
    fixture_limit: int=100,
    min_fixture_severity: float=4.0,
) -> dict:
    all_rows=tuple(inputs)
    if max_cases < 1 or max_cases > 10000:
        raise ValueError('max_cases must be 1..10000')
    rows=all_rows[:max_cases]

    benchmark_rows=[
        compare_case(x.case_id,x.jong,x.oracle)
        for x in rows
    ]
    bench=summary_dict(benchmark_rows)

    triage=mine_report(
        bench,
        ev_threshold=ev_threshold,
        win_threshold=win_threshold,
        tenpai_threshold=tenpai_threshold,
        ukeire_threshold=ukeire_threshold,
    )
    diag=diagnose_report(
        bench,
        ukeire_threshold=ukeire_threshold,
        probability_threshold=max(win_threshold,tenpai_threshold),
        ev_threshold=ev_threshold,
    )

    triage_by_id={
        str(x['case_id']):x for x in triage.get('priority_cases',[])
    }
    diag_by_id={
        str(x['case_id']):x for x in diag.get('diagnostics',[])
    }
    input_by_id={x.case_id:x for x in rows}

    decisions=[]
    for x in rows:
        tr=triage_by_id.get(x.case_id,{})
        dg=diag_by_id.get(x.case_id,{})
        trusted=_is_trusted(x)
        sev=float(tr.get('severity',0.0))
        eligible=bool(
            trusted
            and sev >= min_fixture_severity
            and tr.get('reasons')
        )
        if not x.reference_verified:
            reason='reference_not_verified'
        elif x.reference_source not in TRUSTED_REFERENCE_SOURCES:
            reason='reference_source_not_trusted'
        elif sev < min_fixture_severity:
            reason='below_fixture_severity'
        elif not tr.get('reasons'):
            reason='within_thresholds'
        else:
            reason='eligible'
        decisions.append(MiningDecision(
            case_id=x.case_id,
            severity=sev,
            primary_layer=str(dg.get('primary_layer','none')),
            regression_eligible=eligible,
            reason=reason,
            reference_source=x.reference_source,
        ))

    eligible_ids={d.case_id for d in decisions if d.regression_eligible}
    eligible_triage={
        **triage,
        'priority_cases':[
            x for x in triage.get('priority_cases',[])
            if str(x.get('case_id')) in eligible_ids
        ],
    }

    fixtures=select_priority_fixtures(
        cases_by_id=_case_map(rows),
        triage=eligible_triage,
        oracle_results_by_id=_oracle_map(rows),
        limit=fixture_limit,
        min_severity=min_fixture_severity,
    )

    layer_counts={}
    for d in decisions:
        layer_counts[d.primary_layer]=layer_counts.get(d.primary_layer,0)+1

    return {
        'schema_version':'diff-mining-v4.2',
        'cases_received':len(all_rows),
        'cases_processed':len(rows),
        'benchmark':bench,
        'triage':triage,
        'diagnostics':diag,
        'primary_layer_counts':layer_counts,
        'reference_policy':{
            'trusted_sources':sorted(TRUSTED_REFERENCE_SOURCES),
            'fixtures_require_verified_reference':True,
        },
        'decisions':[asdict(x) for x in decisions],
        'regression_fixtures':[asdict(x) for x in fixtures],
        'regression_fixture_count':len(fixtures),
    }


def write_diff_bundle(
    output_dir: str|Path,
    report: dict,
) -> dict:
    out=Path(output_dir)
    out.mkdir(parents=True,exist_ok=True)

    report_path=out/'diff-mining-report.json'
    report_path.write_text(
        json.dumps(report,ensure_ascii=False,indent=2),
        encoding='utf-8'
    )

    fixture_path=out/'regression-fixtures.json'
    fixture_payload={'fixtures':report.get('regression_fixtures',[])}
    fixture_path.write_text(
        json.dumps(fixture_payload,ensure_ascii=False,indent=2),
        encoding='utf-8'
    )

    queue=[]
    for d in report.get('decisions',[]):
        if d.get('severity',0)<=0:
            continue
        queue.append({
            'case_id':d['case_id'],
            'priority':d['severity'],
            'primary_layer':d['primary_layer'],
            'regression_eligible':d['regression_eligible'],
            'reference_source':d['reference_source'],
        })
    queue.sort(key=lambda x:(-float(x['priority']),x['primary_layer'],x['case_id']))

    queue_path=out/'improvement-queue.json'
    queue_path.write_text(
        json.dumps({'queue':queue},ensure_ascii=False,indent=2),
        encoding='utf-8'
    )

    return {
        'report_path':str(report_path),
        'fixture_path':str(fixture_path),
        'queue_path':str(queue_path),
        'queue_size':len(queue),
    }
