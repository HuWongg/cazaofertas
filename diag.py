"""Diagnóstico de conectividad desde GitHub Actions (resultado en data/diag.json)."""
import json
import time
from pathlib import Path

from curl_cffi import requests as creq

R = "https://api.ripley.com/experience/retail/web/api-findability-orchestrator/v1"
PK = "key_8pjkPsSkEsJHKgxR"
out = {"ts": int(time.time())}
s = creq.Session(impersonate="chrome", timeout=30,
                 headers={"Accept": "application/json", "Origin": "https://simple.ripley.cl",
                          "Referer": "https://simple.ripley.cl/"})


def probar(nombre, url, **kw):
    try:
        r = s.get(url, **kw)
        txt = r.text
        try:
            j = r.json()
            resumen = {"keys": list(j.keys())[:20] if isinstance(j, dict) else type(j).__name__}
            if isinstance(j, dict) and isinstance(j.get("data"), dict):
                resumen["data_keys"] = list(j["data"].keys())[:20]
                prods = j["data"].get("products")
                if isinstance(prods, list):
                    resumen["n"] = len(prods)
                    resumen["total"] = j["data"].get("total")
                    resumen["offset"] = j["data"].get("offset")
                    resumen["limit"] = j["data"].get("limit")
                    if prods:
                        resumen["p0"] = {k: prods[0].get(k) for k in ("sku", "priceNumber")}
                        resumen["skus"] = [x.get("sku") for x in prods[:4]]
            if isinstance(j, dict) and j.get("error"):
                resumen["error"] = str(j.get("error"))[:200]
            if isinstance(j, dict) and isinstance(j.get("products"), list):
                resumen["n"] = len(j["products"])
                resumen["total"] = j.get("total")
                if j["products"]:
                    resumen["p0"] = {k: j["products"][0].get(k) for k in ("sku", "name", "priceNumber", "masterPriceNumber")}
        except Exception:  # noqa: BLE001
            resumen = {"snippet": txt[:300]}
        out[nombre] = {"status": r.status_code, "server": r.headers.get("server"), **resumen}
        return r
    except Exception as e:  # noqa: BLE001
        out[nombre] = {"error": f"{type(e).__name__}: {e}"}


r = probar("ripley_auth", R + "/auth")
tok = None
try:
    tok = r.json()["data"]["access_token"]
except Exception:  # noqa: BLE001
    try:
        tok = r.json().get("access_token")
    except Exception:  # noqa: BLE001
        pass
out["ripley_token"] = bool(tok)
if tok:
    h = {"x-access-token": tok}
    c = {"catalog": "note_books"}
    variantes = {
        "base": c,
        "offset": {**c, "offset": 48},
        "limit": {**c, "limit": 48},
        "limit_offset": {**c, "limit": 48, "offset": 48},
        "from_size": {**c, "from": 48, "size": 48},
        "pageNumber": {**c, "pageNumber": 2},
        "p": {**c, "p": 2},
        "orderBy": {**c, "orderBy": "price_asc"},
        "sort": {**c, "sort": "price_asc"},
        "limit100": {**c, "limit": 100},
        "depto": {"catalog": "tecno"},
    }
    for k, p in variantes.items():
        probar("ripley_cat_" + k, R + "/findability/catalog", params=p, headers=h)

probar("ripley_web", "https://simple.ripley.cl/tecno/computacion/notebooks")
probar("paris_cnstrc", f"https://ac.cnstrc.com/browse/group_id/tecnologia?key={PK}&c=ciojs-client-2&i=gh&s=1"
       "&page=1&num_results_per_page=5&sort_by=best-discount&sort_order=descending")
probar("paris_web", "https://www.paris.cl/tecnologia/computadores/notebooks/")

Path("data").mkdir(exist_ok=True)
Path("data/diag.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps(out, ensure_ascii=False, indent=1))
