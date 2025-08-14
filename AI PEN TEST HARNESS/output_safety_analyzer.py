
import json
from pathlib import Path
from ..utils.eval import xss_like

INFO = {"name":"output_safety_analyzer","intents":["app_compromise"]}

def run(samples_path, outdir="out/output_safety"):
    Path(outdir).mkdir(parents=True, exist_ok=True)
    texts = []
    try:
        data = json.load(open(samples_path,"r",encoding="utf-8"))
        if isinstance(data, list):
            texts = [str(t) for t in data]
    except Exception:
        for line in open(samples_path,"r",encoding="utf-8"):
            line=line.strip()
            if not line: continue
            texts.append(line)

    findings = []
    for i, t in enumerate(texts[:500]):
        flag = xss_like(t)
        findings.append({"idx":i,"xss_like":flag,"sample":t[:200]})

    with open(Path(outdir)/"results.json","w",encoding="utf-8") as f:
        json.dump(findings,f,indent=2,ensure_ascii=False)

    md = [f"# Output Safety Analyzer", f"- Samples analyzed: {len(texts)}", f"- XSS-like flagged: {sum(1 for f in findings if f['xss_like'])}", ""]
    for f in findings[:20]:
        if f["xss_like"]:
            md.append(f"- idx={f['idx']} XSS-like: {f['sample']}")
    with open(Path(outdir)/"results.md","w",encoding="utf-8") as f:
        f.write("\n".join(md))

    return {"module": INFO["name"], "samples": len(texts), "outdir": outdir}
