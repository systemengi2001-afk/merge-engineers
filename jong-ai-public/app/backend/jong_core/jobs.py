from __future__ import annotations
from dataclasses import dataclass, asdict
from threading import Lock, Thread
from time import time
from uuid import uuid4

from .analyzer import analyze_hand
from .calibration import CalibrationStore

@dataclass
class Job:
    id: str
    status: str
    created_at: float
    updated_at: float
    request: dict
    result: dict | None = None
    error: str | None = None

class PrecisionJobStore:
    def __init__(self, calibration: CalibrationStore | None = None):
        self._jobs: dict[str, Job] = {}
        self._lock = Lock()
        self.calibration = calibration

    def create(self, request: dict) -> Job:
        now=time()
        job=Job(str(uuid4()), 'queued', now, now, request)
        with self._lock:
            self._jobs[job.id]=job
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def snapshot(self, job_id: str) -> dict | None:
        job=self.get(job_id)
        if not job: return None
        data=asdict(job)
        # avoid echoing large private request data in polling payload
        data.pop('request',None)
        return data

    def start(self, job_id: str):
        job=self.get(job_id)
        if not job: raise KeyError(job_id)
        t=Thread(target=self._run,args=(job_id,),daemon=True)
        t.start()

    def _run(self, job_id: str):
        with self._lock:
            job=self._jobs[job_id]
            job.status='running'; job.updated_at=time()
            req=dict(job.request)
        try:
            # Precision v1.3 is intentionally bounded. Deeper exact analysis remains a later engine task.
            draws=min(int(req.get('draws') or 3), 2)
            result=analyze_hand(
                req['hand'], req.get('visible_tiles',()), draws,
                score_ev=True,
                dealer=bool(req.get('dealer',False)),
                round_wind=req.get('round_wind','1z'),
                seat_wind=req.get('seat_wind','2z'),
                dora_indicators=req.get('dora_indicators',()),
                red_dora_count=int(req.get('red_dora_count',0)),
                game_mode=req.get('game_mode'),
                ruleset=req.get('ruleset'),
                nuki_count=int(req.get('nuki_count',0)),
                chip_count=int(req.get('chip_count',0)),
                chip_value_points=int(req.get('chip_value_points',0)),
                auto_nuki=bool(req.get('auto_nuki',True)),
            )
            result['precision_meta']={
                'requested_draws': int(req.get('draws') or 3),
                'computed_draws': draws,
                'model': 'bounded_exact_score_dp_v1.4',
                'is_final_commercial_ev': False,
            }
            if self.calibration and req.get('instant_result'):
                self.calibration.record_pair(
                    req['hand'], req['instant_result'], result, time(),
                    ruleset=req.get('resolved_ruleset','legacy_unknown'),
                    instant_draws=int(req.get('calibration_instant_draws',draws)),
                    precision_draws=draws,
                )
            with self._lock:
                job=self._jobs[job_id]
                job.result=result; job.status='completed'; job.updated_at=time()
        except Exception as e:
            with self._lock:
                job=self._jobs[job_id]
                job.error=str(e); job.status='failed'; job.updated_at=time()
