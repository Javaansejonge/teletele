
import json, yaml, ssl, re
from urllib.parse import urljoin
from ..utils.http import safe_get
try:
    import websocket
except Exception:
    websocket = None

INFO = {"name":"manifest_and_ws","utilities":["recon_mapper"]}

def fetch_manifest_and_openapi(session, base_url, timeout=10):
    out = {"manifest_url": urljoin(base_url,"/.well-known/ai-plugin.json"),
           "manifest_status": None, "openapi_url": None, "openapi_status": None,
           "openapi_kind": None, "openapi_paths_preview": []}
    r = safe_get(session, out["manifest_url"], timeout)
    if not r:
        return out
    out["manifest_status"] = r.status_code
    if r.status_code >= 400:
        return out
    try:
        manifest = r.json()
    except Exception:
        try:
            manifest = json.loads(r.text)
        except Exception:
            manifest = None
    if isinstance(manifest, dict):
        api = manifest.get("api") or {}
        cand = api.get("url") if isinstance(api, dict) else None
        cand = cand or manifest.get("openapi_url") or manifest.get("spec_url")
        if cand:
            out["openapi_url"] = urljoin(base_url, cand)
            rr = safe_get(session, out["openapi_url"], timeout)
            if rr:
                out["openapi_status"] = rr.status_code
                if rr.status_code < 400:
                    try:
                        data = rr.json(); kind = "json"
                    except Exception:
                        try:
                            import yaml
                            data = yaml.safe_load(rr.text); kind = "yaml"
                        except Exception:
                            data, kind = None, None
                    out["openapi_kind"] = kind
                    if isinstance(data, dict) and "paths" in data:
                        out["openapi_paths_preview"] = list(data["paths"].keys())[:15]
    return out

def probe_ws(urls, timeout=8, insecure=False):
    results = []
    if not websocket: return results
    for u in urls:
        status, detail = "skipped", ""
        try:
            ws = websocket.create_connection(u, timeout=timeout, sslopt={"cert_reqs": ssl.CERT_NONE} if insecure else None)
            status = "handshake_ok"; ws.close()
        except Exception as e:
            emsg = str(e).lower()
            if "401" in emsg: status = "unauthorized"
            elif "403" in emsg: status = "forbidden"
            elif "ssl" in emsg or "certificate" in emsg: status = "tls_error"
            elif "timed out" in emsg: status = "timeout"
            else: status = "error"
            detail = str(e)[:120]
        results.append({"url": u, "probe": status, "detail": detail})
    return results

def run(session, base_url, ws_urls=None, timeout=10, ws_probe=True, ws_insecure=False):
    manifest = fetch_manifest_and_openapi(session, base_url, timeout)
    ws_results = []
    if ws_probe and ws_urls:
        ws_results = probe_ws(ws_urls, timeout=timeout, insecure=ws_insecure)
    return {"module": INFO["name"], "manifest": manifest, "websockets": ws_results}
