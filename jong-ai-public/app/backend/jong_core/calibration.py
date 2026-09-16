from __future__ import annotations
import sqlite3
from pathlib import Path
from statistics import mean

SCHEMA = """
CREATE TABLE IF NOT EXISTS ev_calibration (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at REAL NOT NULL,
    hand TEXT NOT NULL,
    discard TEXT NOT NULL,
    shanten INTEGER NOT NULL,
    ukeire_total INTEGER NOT NULL,
    instant_ev REAL NOT NULL,
    precision_ev REAL NOT NULL,
    instant_win REAL NOT NULL,
    precision_win REAL NOT NULL,
    instant_tenpai REAL NOT NULL,
    precision_tenpai REAL NOT NULL,
    ruleset TEXT NOT NULL DEFAULT 'legacy_unknown',
    instant_draws INTEGER NOT NULL DEFAULT -1,
    precision_draws INTEGER NOT NULL DEFAULT -1
);
CREATE INDEX IF NOT EXISTS idx_ev_calibration_features_v2
ON ev_calibration(ruleset, instant_draws, precision_draws, shanten, ukeire_total);
"""

class CalibrationStore:
    def __init__(self, path: str | Path):
        self.path=str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as con:
            # Create the base table first without assuming v2 columns already exist.
            con.execute("""
            CREATE TABLE IF NOT EXISTS ev_calibration (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at REAL NOT NULL,
                hand TEXT NOT NULL,
                discard TEXT NOT NULL,
                shanten INTEGER NOT NULL,
                ukeire_total INTEGER NOT NULL,
                instant_ev REAL NOT NULL,
                precision_ev REAL NOT NULL,
                instant_win REAL NOT NULL,
                precision_win REAL NOT NULL,
                instant_tenpai REAL NOT NULL,
                precision_tenpai REAL NOT NULL
            )
            """)
            cols={r[1] for r in con.execute("PRAGMA table_info(ev_calibration)")}
            migrations=[
                ("ruleset","TEXT NOT NULL DEFAULT 'legacy_unknown'"),
                ("instant_draws","INTEGER NOT NULL DEFAULT -1"),
                ("precision_draws","INTEGER NOT NULL DEFAULT -1"),
            ]
            for name,ddl in migrations:
                if name not in cols:
                    con.execute(f"ALTER TABLE ev_calibration ADD COLUMN {name} {ddl}")
            con.execute("""CREATE INDEX IF NOT EXISTS idx_ev_calibration_features_v2
                           ON ev_calibration(ruleset, instant_draws, precision_draws, shanten, ukeire_total)""")

    def record_pair(self, hand: str, instant: dict, precision: dict, created_at: float,
                    *, ruleset: str, instant_draws: int, precision_draws: int):
        imap={c["discard"]:c for c in instant.get("candidates",[])}
        pmap={c["discard"]:c for c in precision.get("candidates",[])}
        rows=[]
        for d in sorted(set(imap)&set(pmap)):
            i=imap[d]; p=pmap[d]
            rows.append((
                created_at, hand, d,
                int(i.get("shanten",99)), int(i.get("ukeire_total",0)),
                float(i.get("expected_points",0.0)), float(p.get("expected_points",0.0)),
                float(i.get("win_probability",0.0)), float(p.get("win_probability",0.0)),
                float(i.get("tenpai_probability",0.0)), float(p.get("tenpai_probability",0.0)),
                ruleset, int(instant_draws), int(precision_draws),
            ))
        if not rows:
            return 0
        with sqlite3.connect(self.path) as con:
            con.executemany("""
            INSERT INTO ev_calibration(
                created_at,hand,discard,shanten,ukeire_total,
                instant_ev,precision_ev,instant_win,precision_win,
                instant_tenpai,precision_tenpai,ruleset,instant_draws,precision_draws
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, rows)
        return len(rows)

    def stats(self, *, ruleset: str | None=None,
              instant_draws: int | None=None, precision_draws: int | None=None) -> dict:
        where=[]; args=[]
        for col,val in (("ruleset",ruleset),("instant_draws",instant_draws),("precision_draws",precision_draws)):
            if val is not None:
                where.append(f"{col}=?"); args.append(val)
        sql="""SELECT instant_ev,precision_ev,instant_win,precision_win,
                      instant_tenpai,precision_tenpai FROM ev_calibration"""
        if where: sql += " WHERE " + " AND ".join(where)
        with sqlite3.connect(self.path) as con:
            rows=con.execute(sql,args).fetchall()
        if not rows:
            return {"samples":0,"ruleset":ruleset,"instant_draws":instant_draws,"precision_draws":precision_draws}
        return {
            "samples":len(rows),
            "mae_ev":mean(abs(r[1]-r[0]) for r in rows),
            "mae_win_probability":mean(abs(r[3]-r[2]) for r in rows),
            "mae_tenpai_probability":mean(abs(r[5]-r[4]) for r in rows),
            "ruleset":ruleset,"instant_draws":instant_draws,"precision_draws":precision_draws,
        }

    def correction_for(self, shanten: int, ukeire_total: int, *,
                       ruleset: str, instant_draws: int, precision_draws: int) -> dict:
        with sqlite3.connect(self.path) as con:
            rows=con.execute("""
            SELECT instant_ev,precision_ev,instant_win,precision_win,
                   instant_tenpai,precision_tenpai
            FROM ev_calibration
            WHERE ruleset=? AND instant_draws=? AND precision_draws=?
              AND shanten=? AND ukeire_total BETWEEN ? AND ?
            ORDER BY id DESC LIMIT 200
            """,(ruleset,int(instant_draws),int(precision_draws),
                 shanten,max(0,ukeire_total-2),ukeire_total+2)).fetchall()
        if len(rows) < 8:
            return {"samples":len(rows),"ready":False}
        return {
            "samples":len(rows),"ready":True,
            "ev_delta":mean(r[1]-r[0] for r in rows),
            "win_delta":mean(r[3]-r[2] for r in rows),
            "tenpai_delta":mean(r[5]-r[4] for r in rows),
        }

    def apply(self, result: dict, *, ruleset: str, instant_draws: int, precision_draws: int) -> dict:
        for c in result.get("candidates",[]):
            corr=self.correction_for(
                int(c.get("shanten",99)),int(c.get("ukeire_total",0)),
                ruleset=ruleset,instant_draws=instant_draws,precision_draws=precision_draws,
            )
            c["calibration_samples"]=corr.get("samples",0)
            c["calibration_scope"]={
                "ruleset":ruleset,"instant_draws":instant_draws,"precision_draws":precision_draws
            }
            if not corr.get("ready"):
                c["calibrated"]=False
                continue
            c["expected_points"]=max(0.0,float(c.get("expected_points",0.0))+corr["ev_delta"])
            c["win_probability"]=min(1.0,max(0.0,float(c.get("win_probability",0.0))+corr["win_delta"]))
            c["tenpai_probability"]=min(1.0,max(0.0,float(c.get("tenpai_probability",0.0))+corr["tenpai_delta"]))
            c["calibrated"]=True
        result["candidates"].sort(
            key=lambda c:(-c.get("expected_points",0),-c.get("win_probability",0),
                          -c.get("tenpai_probability",0),c.get("shanten",99),
                          -c.get("ukeire_total",0),c.get("discard",""))
        )
        result["best_by_ev"]=result["candidates"][0]["discard"] if result.get("candidates") else None
        result["calibration_scope"]={
            "ruleset":ruleset,"instant_draws":instant_draws,"precision_draws":precision_draws
        }
        return result
