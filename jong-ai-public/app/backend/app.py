from functools import lru_cache
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

app=FastAPI(title="JONG AI Public",version="4.5-public")

SANMA=set([0,8,*range(9,34)])
RULES={
 "yonma_standard":(set(range(34)),4),
 "sanma_standard":(SANMA,3),
 "osaka_sanma_v1":(SANMA,3),
}

def parse(s):
    c=[0]*34; ds=""
    bases={"m":0,"p":9,"s":18,"z":27}
    for ch in s:
        if ch.isdigit(): ds+=ch; continue
        if ch not in bases or not ds: raise ValueError("MPSZ形式が不正です")
        for d in ds:
            n=int(d)
            if ch=="z" and not 1<=n<=7: raise ValueError("字牌は1z〜7z")
            if ch!="z" and not 1<=n<=9: raise ValueError("数牌は1〜9")
            i=bases[ch]+n-1
            c[i]+=1
            if c[i]>4: raise ValueError("同じ牌は4枚までです")
        ds=""
    if ds: raise ValueError("MPSZ形式が不正です")
    return c

def fmt(i):
    if i<9:return f"{i+1}m"
    if i<18:return f"{i-8}p"
    if i<27:return f"{i-17}s"
    return f"{i-26}z"

@lru_cache(None)
def std_dfs(state,idx=0,m=0,t=0,p=0):
    a=list(state)
    while idx<34 and a[idx]==0: idx+=1
    if idx>=34:
        t=min(t,4-m)
        return 8-m*2-t-p
    best=8
    best=min(best,std_dfs(tuple(a),idx+1,m,t,p))
    if a[idx]>=3 and m<4:
        a[idx]-=3; best=min(best,std_dfs(tuple(a),idx,m+1,t,p)); a[idx]+=3
    if idx<27 and idx%9<=6 and a[idx+1] and a[idx+2] and m<4:
        a[idx]-=1;a[idx+1]-=1;a[idx+2]-=1
        best=min(best,std_dfs(tuple(a),idx,m+1,t,p))
        a[idx]+=1;a[idx+1]+=1;a[idx+2]+=1
    if a[idx]>=2 and p==0:
        a[idx]-=2;best=min(best,std_dfs(tuple(a),idx,m,t,1));a[idx]+=2
    if t<4-m:
        if a[idx]>=2:
            a[idx]-=2;best=min(best,std_dfs(tuple(a),idx,m,t+1,p));a[idx]+=2
        if idx<27 and idx%9<=7 and a[idx+1]:
            a[idx]-=1;a[idx+1]-=1
            best=min(best,std_dfs(tuple(a),idx,m,t+1,p))
            a[idx]+=1;a[idx+1]+=1
        if idx<27 and idx%9<=6 and a[idx+2]:
            a[idx]-=1;a[idx+2]-=1
            best=min(best,std_dfs(tuple(a),idx,m,t+1,p))
            a[idx]+=1;a[idx+2]+=1
    return best

def shanten(c):
    regular=std_dfs(tuple(c),0,0,0,0)
    pairs=sum(x>=2 for x in c); kinds=sum(x>0 for x in c)
    chiitoi=6-pairs+max(0,7-kinds)
    terminals=[0,8,9,17,18,26,*range(27,34)]
    unique=sum(c[i]>0 for i in terminals); pair=any(c[i]>=2 for i in terminals)
    kokushi=13-unique-(1 if pair else 0)
    return min(regular,chiitoi,kokushi)

def ukeire(c13,visible,allowed):
    base=shanten(c13); out=[]
    for i in sorted(allowed):
        if visible[i]>=4: continue
        c13[i]+=1; ns=shanten(c13); c13[i]-=1
        if ns<base: out.append((i,4-visible[i],ns))
    return base,out

def analyze(hand,ruleset,draws,visible_tokens,dora,nuki):
    c=parse(hand)
    if sum(c)!=14: raise ValueError("公開版は14枚の手牌を入力してください")
    if ruleset not in RULES: raise ValueError("不明なルール")
    allowed,players=RULES[ruleset]
    illegal=[fmt(i) for i,x in enumerate(c) if x and i not in allowed]
    if illegal: raise ValueError("この三麻では使用しない牌: "+",".join(illegal))
    visible=c.copy()
    for tok in [*visible_tokens,*dora]:
        q=parse(tok)
        for i,x in enumerate(q):
            visible[i]+=x
            if visible[i]>4: raise ValueError("可視牌が4枚を超えています")
    visible[30]+=nuki
    if visible[30]>4: raise ValueError("北が4枚を超えています")
    live=sum(4-visible[i] for i in allowed)
    rows=[]
    seen=set()
    for d in range(34):
        if c[d]==0 or d in seen: continue
        seen.add(d); h=c.copy();h[d]-=1
        s,u=ukeire(h,visible,allowed)
        ut=sum(x[1] for x in u)
        p1=0 if live<=0 else min(1,ut/live)
        ten=1-(1-p1)**max(1,draws)
        win=max(0.0,min(1.0,ten*(0.42 if s<=0 else 0.18/(s+1))))
        avg=5200*(2**min(nuki,2))
        ev=win*avg
        rows.append({"discard":fmt(d),"shanten":s,"ukeire_total":ut,
                     "ukeire":[{"tile":fmt(i),"remaining":r,"next_shanten":ns} for i,r,ns in u],
                     "tenpai_probability":ten,"win_probability":win,
                     "expected_points":round(ev,1),"average_win_points":avg})
    rows.sort(key=lambda x:(-x["expected_points"],x["shanten"],-x["ukeire_total"],x["discard"]))
    return {"best_by_ev":rows[0]["discard"] if rows else None,"candidates":rows,
            "ruleset":{"id":ruleset,"players":players},"notice":"JONG AI public beta: 高速近似EV"}

class Req(BaseModel):
    hand:str
    draws:int=Field(default=3,ge=1,le=6)
    game_mode:str="sanma"
    ruleset:str="sanma_standard"
    visible_tiles:list[str]=[]
    dora_indicators:list[str]=[]
    nuki_count:int=Field(default=0,ge=0,le=4)

@app.get("/healthz")
def healthz(): return {"ok":True,"version":app.version}

@app.post("/v1/analyze")
def api_analyze(r:Req):
    try:return analyze(r.hand,r.ruleset,r.draws,r.visible_tiles,r.dora_indicators,r.nuki_count)
    except ValueError as e: raise HTTPException(400,str(e))

front=Path(__file__).resolve().parents[1]/"frontend"
app.mount("/",StaticFiles(directory=str(front),html=True),name="frontend")
