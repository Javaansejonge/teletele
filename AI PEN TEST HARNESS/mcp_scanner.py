
import json, yaml, requests
from pathlib import Path

INFO = {"name":"mcp_scanner","intents":["tool_abuse","data_exfil"]}

COMMON_ENDPOINTS = ["/mcp","/.well-known/mcp.json","/mcp/server","/mcp/tools","/mcp/resources","/mcp/prompts"]

def run(plan_path, outdir="out/mcp_scan"):
    Path(outdir).mkdir(parents=True, exist_ok=True)
    plan = yaml.safe_load(open(plan_path,"r",encoding="utf-8"))
    target = plan.get("target","")
    auth = plan.get("auth",{})
    headers = {}
    if auth.get("type")=="header":
        headers[auth.get("header_name","Authorization")] = auth.get("value","")

    session = requests.Session()
    results = []

    for url in plan.get("mcp",{}).get("http_endpoints",[]):
        try:
            r = session.get(url, headers=headers, timeout=12)
            ct = r.headers.get("Content-Type","") if r else ""
            data = None
            try: data = r.json()
            except Exception: data = None
            hit = {"url":url,"status":(r.status_code if r else None),"ctype":ct}
            if isinstance(data, dict):
                for key in ("tools","resources","prompts"):
                    if key in data:
                        hit[key] = list(data[key])[:10] if isinstance(data[key], (list, dict)) else "present"
            results.append(hit)
        except Exception as e:
            results.append({"url":url,"status":None,"error":str(e)[:200]})

    for p in COMMON_ENDPOINTS:
        url = target.rstrip("/") + p
        try:
            r = session.get(url, headers=headers, timeout=12)
            if r.status_code < 400:
                hit = {"url":url,"status":r.status_code,"ctype":r.headers.get("Content-Type","")}
                try:
                    data = r.json()
                    if isinstance(data, dict):
                        for key in ("tools","resources","prompts"):
                            if key in data:
                                hit[key] = list(data[key])[:10] if isinstance(data[key], (list, dict)) else "present"
                except Exception:
                    pass
                results.append(hit)
        except Exception:
            pass

    with open(Path(outdir)/"results.json","w",encoding="utf-8") as f:
        json.dump(results,f,indent=2,ensure_ascii=False)
    md = ["# MCP Scanner"]
    for r in results:
        md.append(f"- {r.get('url')} — status {r.get('status')} — {r.get('ctype','')}")
        for k in ("tools","resources","prompts"):
            if k in r:
                md.append(f"  - {k}: {r[k] if isinstance(r[k], list) else 'present'}")
    with open(Path(outdir)/"results.md","w",encoding="utf-8") as f:
        f.write("\n".join(md))

    return {"module": INFO["name"], "count": len(results), "outdir": outdir}
