
#!/usr/bin/env python3
import argparse, json, time, requests
from rich.console import Console
from pathlib import Path

from modules import recon as mod_recon
from modules import manifest_ws as mod_mw
from modules import checklist as mod_check
from modules import active_prompt_injection as mod_ap
from modules import rag_leak_tester as mod_rag
from modules import mcp_scanner as mod_mcp
from modules import output_safety_analyzer as mod_out
from utils.report import write_reports

console = Console()

def run_harness(target, timeout=10, max_pages=40, ws_probe=True, ws_insecure=False, outdir="out", plan=None, run_active=False, samples=None):
    session = requests.Session()
    agg = {"target": target, "timestamp": int(time.time())}

    console.rule("[bold cyan]1) Recon")
    recon_res = mod_recon.run(session, target, timeout=timeout, max_pages=max_pages)
    agg["recon"] = recon_res
    console.print(f"[green]Crawled pages:[/green] {len(recon_res['pages'])}  | JS files: {len(recon_res['scripts'])}  | WS URLs: {len(recon_res['ws_urls'])}")
    console.print(f"[green]Probed endpoints:[/green] {len(recon_res['endpoints'])}")

    console.rule("[bold cyan]2) Manifest & WebSockets")
    mw_res = mod_mw.run(session, target, ws_urls=recon_res["ws_urls"], timeout=timeout, ws_probe=ws_probe, ws_insecure=ws_insecure)
    agg["manifest_ws"] = mw_res
    mani = mw_res.get("manifest",{})
    console.print(f"[green]Manifest status:[/green] {mani.get('manifest_status')}  | OpenAPI: {mani.get('openapi_url')} ({mani.get('openapi_status')})")
    if mw_res.get("websockets"):
        ok = sum(1 for w in mw_res["websockets"] if w["probe"]=="handshake_ok")
        console.print(f"[green]WS endpoints probed:[/green] {len(mw_res['websockets'])} (OK: {ok})")

    md = [f"# AI Pentest Harness Summary for {target}\n",
          "## Recon",
          f"- Pages crawled: {len(recon_res['pages'])}",
          f"- JS files scanned: {len(recon_res['scripts'])}",
          f"- WebSocket URLs found: {len(recon_res['ws_urls'])}",
          f"- Probed endpoints: {len(recon_res['endpoints'])}",
          "\n## Manifest/OpenAPI",
          f"- Manifest status: {mani.get('manifest_status')}",
          f"- OpenAPI: {mani.get('openapi_url')} ({mani.get('openapi_status')})",
          f"- OpenAPI paths (preview): {', '.join(mani.get('openapi_paths_preview', [])) or 'n/a'}",
          "\n## WebSocket Probes"]
    for w in mw_res.get("websockets",[]):
        md.append(f"- {w['url']} — {w['probe']}")
    md.append("")

    Path(outdir).mkdir(parents=True, exist_ok=True)
    write_reports(outdir, "\n".join(md), agg)

    # Active modules
    if run_active and plan:
        console.rule("[bold magenta]3) Active: Prompt Injection")
        ap_res = mod_ap.run(plan, 'payloads/prompt_payloads.yaml', outdir=str(Path(outdir)/'active_prompt'))
        agg["active_prompt"] = ap_res

        console.rule("[bold magenta]4) Active: RAG Leak Tester")
        rag_res = mod_rag.run(plan, outdir=str(Path(outdir)/'rag_leak'))
        agg["rag_leak"] = rag_res

        console.rule("[bold magenta]5) Active: MCP Scanner")
        mcp_res = mod_mcp.run(plan, outdir=str(Path(outdir)/'mcp_scan'))
        agg["mcp_scan"] = mcp_res

    # Output safety analyzer (offline)
    if samples:
        console.rule("[bold magenta]Output Safety Analyzer")
        out_res = mod_out.run(samples, outdir=str(Path(outdir)/'output_safety'))
        agg["output_safety"] = out_res

    # Checklist
    checklist_path = str(Path(outdir) / "targets-checklist.md")
    mod_check.run(agg, checklist_path)

    write_reports(outdir, "\n".join(md), agg)
    return agg

def main():
    ap = argparse.ArgumentParser(description="AI Pentest Harness (passive-first with optional active plan)")
    ap.add_argument("url", help="Root URL to assess")
    ap.add_argument("--timeout", type=int, default=10)
    ap.add_argument("--max-pages", type=int, default=40)
    ap.add_argument("--no-ws-probe", action="store_true")
    ap.add_argument("--ws-insecure", action="store_true")
    ap.add_argument("--outdir", default="out")
    ap.add_argument("--plan", help="YAML plan for active modules", default=None)
    ap.add_argument("--run-active", action="store_true", help="Run active modules defined by the plan")
    ap.add_argument("--samples", help="Path to JSON/NDJSON with model outputs to analyze", default=None)
    args = ap.parse_args()

    agg = run_harness(args.url, timeout=args.timeout, max_pages=args.max_pages,
                      ws_probe=not args.no-ws-probe, ws_insecure=args.ws_insecure,
                      outdir=args.outdir, plan=args.plan, run_active=args.run_active,
                      samples=args.samples)

    console.rule("[bold green]Done")
    console.print(f"[bold]Report:[/bold] {args.outdir}/report.md  |  JSON: {args.outdir}/report.json")
    console.print(f"[bold]Checklist:[/bold] {args.outdir}/targets-checklist.md")

if __name__ == "__main__":
    main()
