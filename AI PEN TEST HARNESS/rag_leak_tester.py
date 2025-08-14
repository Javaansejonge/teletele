
import json, yaml, time, requests
from pathlib import Path
from ..utils.eval import likely_doc_titles_list, looks_like_base64_blob

INFO = {"name":"rag_leak_tester","intents":["data_exfil"]}

def run(plan_path, outdir="out/rag_leak"):
    Path(outdir).mkdir(parents=True, exist_ok=True)
    plan = yaml.safe_load(open(plan_path,"r",encoding="utf-8"))
    rag = plan.get("rag",{})
    auth = plan.get("auth",{})
    headers = {"Content-Type":"application/json"}
    if auth.get("type")=="header":
        headers[auth.get("header_name","Authorization")] = auth.get("value","")

    session = requests.Session()
    findings = []

    try:
        r = session.post(rag.get("list_endpoint"), headers=headers, json=rag.get("list_body", {}), timeout=15)
        list_ok = r.status_code if r else None
        list_text = r.text[:10000] if r and r.text else ""
    except Exception as e:
        list_ok, list_text = None, str(e)

    list_success = likely_doc_titles_list(list_text)
    findings.append({"step":"list_documents","status":list_ok,"success":list_success,"sample":list_text[:1000]})

    doc_ids = []
    try:
        data = r.json()
        if isinstance(data, dict):
            for k in ("documents","docs","items","results"):
                if k in data and isinstance(data[k], list):
                    for it in data[k]:
                        if isinstance(it, dict):
                            for idk in ("id","doc_id","_id","uuid"):
                                if idk in it: doc_ids.append(it[idk])
        elif isinstance(data, list):
            for it in data:
                if isinstance(it, dict):
                    for idk in ("id","doc_id","_id","uuid"):
                        if idk in it: doc_ids.append(it[idk])
    except Exception:
        pass
    doc_ids = doc_ids[:5]

    gets = []
    for did in doc_ids:
        body = json.loads(json.dumps(rag.get("get_body_template", {"id":"__DOC_ID__"})))
        body_str = json.dumps(body).replace("__DOC_ID__", str(did))
        body = json.loads(body_str)
        try:
            rr = session.post(rag.get("get_endpoint"), headers=headers, json=body, timeout=20)
            gt, tx = rr.status_code, rr.text[:10000]
        except Exception as e:
            gt, tx = None, str(e)
        s = looks_like_base64_blob(tx)
        gets.append({"doc_id":did,"status":gt,"base64_like":s,"sample":tx[:1000]})
    findings.append({"step":"get_documents","docs":gets})

    with open(Path(outdir)/"results.json","w",encoding="utf-8") as f:
        json.dump(findings,f,indent=2,ensure_ascii=False)
    md = [f"# RAG Leak Tester", f"- list endpoint: {rag.get('list_endpoint')} status: {list_ok} success: {list_success}", f"- get endpoint: {rag.get('get_endpoint')} (first {len(doc_ids)} ids)", ""]
    for g in gets:
        flag = "✅" if g["base64_like"] else "❌"
        md.append(f"- {flag} doc_id={g['doc_id']} status={g['status']} base64_like={g['base64_like']}")
    with open(Path(outdir)/"results.md","w",encoding="utf-8") as f:
        f.write("\n".join(md))

    return {"module": INFO["name"], "doc_ids": doc_ids, "outdir": outdir}
