import requests, chardet
from urllib.parse import urljoin

HEADERS = {"User-Agent":"ai-pt-harness/1.0 (+passive-recon)"}

def detect_encoding(content):
    try:
        res = chardet.detect(content)
        return res.get("encoding") or "utf-8"
    except Exception:
        return "utf-8"

def safe_get(session, url, timeout=10, allow_redirects=True):
    try:
        r = session.get(url, headers=HEADERS, timeout=timeout, allow_redirects=allow_redirects)
        return r
    except requests.RequestException:
        return None

def probe_head_or_get(session, base_url, path, timeout=10):
    url = urljoin(base_url, path)
    try:
        r = session.head(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        if r.status_code >= 400 or r.status_code == 405:
            r = session.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        return url, r
    except requests.RequestException:
        return url, None
