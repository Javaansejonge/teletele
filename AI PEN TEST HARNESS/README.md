# AI Pentest Harness (Taxonomy-Driven)

A modular, **passive-first** but **active-capable** harness for AI infra assessments (chatbot, RAG, MCP, agents).

## Quickstart
```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

# Passive healthcheck
python harness.py https://target.tld --max-pages 80 --timeout 12

# Active light (requires plan & permission)
cp plans/active_plan.example.yaml plans/active_plan.yaml  # edit endpoints/tokens
python harness.py https://target.tld --plan plans/active_plan.yaml --run-active --outdir out_client

# Output safety analysis (offline samples)
python harness.py https://target.tld --samples samples.json --outdir out_client
```

### Outputs
- `out/report.json` — full structured data
- `out/report.md` — readable summary
- `out/targets-checklist.md` — actionable endpoints & payload starters
- Active (if enabled): `out/active_prompt`, `out/rag_leak`, `out/mcp_scan`, `out/output_safety`

## Modules
- `recon` — crawl, JS scan, endpoint probe
- `manifest_ws` — `.well-known/ai-plugin.json` + OpenAPI + WS handshake
- `active_prompt_injection` — send curated payloads to chat endpoint
- `rag_leak_tester` — list/get docs; base64-leak heuristic
- `mcp_scanner` — probe MCP metadata endpoints
- `output_safety_analyzer` — flag XSS-like patterns in outputs
- `checklist` — export targets & payload starters

## Plan file (active)
Edit `plans/active_plan.yaml` to set endpoints, auth headers, and RAG/MCP options.

---

## Business framing (turn this into a productized service)
**Vision:** Make AI features safer & trustworthy by default for EU companies.  
**Mission:** Deliver fast, reproducible AI security assessments that translate into fixes within days.  
**Strategy:** Land with a passive healthcheck → expand into full pentest & retainer; partner with AI dev agencies.

**Product tiers**
1) **AI Chatbot Healthcheck (Passive)** — €2.5k–€5k, 3–5 days  
2) **AI Pentest (Active)** — €12k–€25k per app  
3) **RAG/KAG Data Leak Audit** — €6k–€12k  
4) **MCP/Agent Security Audit** — €8k–€15k  
5) **AI Security Program (Retainer)** — €3k–€8k/month  
6) **Training & Playbooks** — €1.5k–€5k/workshop

**Sales motions**
- Send a one-page sample report from this harness.
- Offer the fixed-price healthcheck as the entry point.
- Map findings to a prioritized backlog with time-to-fix estimates.

> Always operate with **explicit written authorization** and a clear scope (SOW).
