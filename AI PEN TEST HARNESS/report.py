import json
from pathlib import Path

def write_reports(outdir, summary_md, report_obj):
    Path(outdir).mkdir(parents=True, exist_ok=True)
    with open(Path(outdir) / "report.json", "w", encoding="utf-8") as f:
        json.dump(report_obj, f, indent=2, ensure_ascii=False)
    with open(Path(outdir) / "report.md", "w", encoding="utf-8") as f:
        f.write(summary_md)
