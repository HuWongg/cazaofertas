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
                    if prods:
                        resumen["p0"] = {k: prods[0].get(k) for k in ("sku", "name", "priceNumber", "masterPriceNumber")}
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
    variantes = {
        "catalog": {"catalog": "note_books"},
        "catalog_page2": {"catalog": "note_books", "page": 2},
        "catalogId": {"catalogId": "note_books"},
        "slug": {"slug": "tecno/computacion/notebooks"},
        "path": {"path": "/tecno/computacion/notebooks"},
        "url": {"url": "/tecno/computacion/notebooks"},
        "categoryPath": {"categoryPath": "tecno/computacion/notebooks"},
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
