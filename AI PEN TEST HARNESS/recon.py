
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import re
from .shared import KEYWORDS, JS_ROUTE_PATTERNS
from ..utils.http import safe_get, detect_encoding, probe_head_or_get

INFO = {"name":"recon_mapper","utilities":["recon_mapper"]}

COMMON_PATHS = [
    "/robots.txt","/sitemap.xml","/.well-known/ai-plugin.json",
    "/openapi.json","/swagger","/swagger.json","/docs","/redoc",
    "/graphql","/api","/api/v1","/ws","/socket.io","/mcp","/rag","/embeddings"
]

def same_origin(base_url, other_url):
    bp, op = urlparse(base_url), urlparse(other_url)
    return (bp.scheme, bp.netloc) == (op.scheme, op.netloc)

def run(session, base_url, timeout=10, max_pages=40):
    pages, scripts, ws_urls, endpoints = [], [], set(), []
    to_visit, visited = [base_url], set()

    for p in COMMON_PATHS:
        url, r = probe_head_or_get(session, base_url, p, timeout)
        endpoints.append({"url":url,"path":p,"status":(r.status_code if r else None),"ctype":(r.headers.get("Content-Type","") if r else "")})

    while to_visit and len(visited) < max_pages:
        url = to_visit.pop(0)
        if url in visited: continue
        visited.add(url)
        r = safe_get(session, url, timeout)
        if not r or "text/html" not in r.headers.get("Content-Type",""): continue
        html = r.content.decode(detect_encoding(r.content), errors="ignore")
        soup = BeautifulSoup(html, "html.parser")

        for a in soup.find_all("a", href=True):
            href = urljoin(url, a["href"])
            if same_origin(base_url, href) and href not in visited and len(visited)+len(to_visit) < max_pages:
                to_visit.append(href)

        forms = [{"action": urljoin(url, f.get("action") or ""), "method": (f.get("method") or "GET").upper()} for f in soup.find_all("form")]
        kws = [k for k in KEYWORDS if k.lower() in html.lower()]
        pages.append({"url": url, "forms": forms, "keywords": kws})

        for s in soup.find_all("script", src=True):
            s_url = urljoin(url, s["src"])
            sr = safe_get(session, s_url, timeout)
            if sr and sr.status_code < 400 and "javascript" in sr.headers.get("Content-Type",""):
                text = sr.text
                routes = set()
                for pat in JS_ROUTE_PATTERNS:
                    for m in re.findall(pat, text, flags=re.IGNORECASE):
                        routes.add(m)
                for m in re.findall(r'ws[s]?:\/\/[^\s\'"]+', text, flags=re.IGNORECASE):
                    ws_urls.add(m)
                scripts.append({"url": s_url, "routes": sorted(routes), "keywords": [k for k in KEYWORDS if k.lower() in text.lower()]})

    return {"module": INFO["name"], "pages": pages, "scripts": scripts, "ws_urls": sorted(ws_urls), "endpoints": endpoints}
