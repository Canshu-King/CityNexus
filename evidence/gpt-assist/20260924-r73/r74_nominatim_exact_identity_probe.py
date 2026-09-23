from __future__ import annotations

# Diagnostic only. Exact OSM-object name evidence via Nominatim lookup.
import argparse, json, time, unicodedata
from pathlib import Path
import httpx

ALLOWED={"name","official_name","short_name","alt_name","full_name","loc_name","reg_name","nat_name"}

def norm(v):
    s=unicodedata.normalize("NFKC",str(v or "")).strip()
    return "".join(ch for ch in s if not ch.isspace())

def names(row):
    nd=row.get("namedetails") if isinstance(row,dict) else {}
    nd=nd if isinstance(nd,dict) else {}
    out=[]
    for k,v in nd.items():
        k=str(k)
        if k not in ALLOWED and not k.startswith("name:"):
            continue
        values=v if isinstance(v,(list,tuple)) else [v]
        for item in values:
            if not isinstance(item,str): continue
            parts=item.split(";") if k=="alt_name" else [item]
            for part in parts:
                part=part.strip()
                if part: out.append({"field":k,"value":part})
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--osm-id",required=True)
    ap.add_argument("--query",required=True)
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--base-url",default="https://nominatim.openstreetmap.org")
    args=ap.parse_args()
    started=time.monotonic(); status=None; err=None; payload=None
    try:
        with httpx.Client(timeout=15.0,trust_env=True,headers={"User-Agent":"CityNexus-R7.4-Diagnostic/1.0 (+https://citynexus.local/)"}) as c:
            r=c.get(args.base_url.rstrip("/")+"/lookup",params={"osm_ids":args.osm_id,"format":"jsonv2","namedetails":1,"extratags":1,"addressdetails":1,"accept-language":"zh-CN,zh,en"})
            status=r.status_code; r.raise_for_status(); payload=r.json()
    except Exception as exc:
        err=f"{type(exc).__name__}: {exc}"
    rows=payload if isinstance(payload,list) else []
    exact=None
    for row in rows:
        typ=str(row.get("osm_type") or "")[:1].upper()
        rid=str(row.get("osm_id") or "")
        if f"{typ}{rid}"==args.osm_id.upper():
            exact=row; break
    vals=names(exact or {})
    wanted=norm(args.query)
    matches=[x for x in vals if norm(x["value"])==wanted]
    result={"classification":"R74_NOMINATIM_EXACT_OSM_IDENTITY_PROBE","query":args.query,"osm_id":args.osm_id,"http_status":status,"elapsed_ms":round((time.monotonic()-started)*1000,1),"error":err,"exact_entity_returned":exact is not None,"exact_name_matches":matches,"allowed_name_values":vals,"raw_exact_row":exact,"truth_boundary":{"diagnostic_only":True,"unique_candidate_is_not_identity_proof":True,"fuzzy_match_is_not_identity_proof":True,"different_entity_id_never_proves_identity":True}}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if err is None else 2

if __name__=="__main__":
    raise SystemExit(main())
