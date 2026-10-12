"""Verificación externa con SoloTodo (solotodo.cl).

SoloTodo registra precios de ~370 tiendas chilenas (sobre todo tecnología y electro)
y guarda su historial. Para cada posible error de precio preguntamos:
  - ¿A cuánto lo venden AHORA las otras tiendas?
  - ¿Cuál ha sido su precio habitual en los últimos 45 días?
API pública: https://publicapi.solotodo.com
"""
from __future__ import annotations

import json
import statistics
import time
import urllib.parse
from datetime import datetime, timedelta, timezone

from .http import Bloqueado, Cliente
from .matching import codigos, conflicto

API = "https://publicapi.solotodo.com"
WEB = "https://www.solotodo.cl/products/{id}"
TIENDAS = {"falabella": {9, 8147}, "ripley": {18, 8510}, "paris": {11, 8148}}
TTL_OK = 4 * 3600
TTL_NADA = 24 * 3600

_nombres_tiendas: dict[int, str] = {}


def _json(cli: Cliente, ruta: str):
    return json.loads(cli.get(API + ruta, headers={"Accept": "application/json"}))


def _tiendas(cli: Cliente) -> dict[int, str]:
    if not _nombres_tiendas:
        for s in _json(cli, "/stores/?country=1"):
            _nombres_tiendas[s["id"]] = s["name"]
    return _nombres_tiendas


def _variantes_sku(p: dict) -> list[str]:
    sku = str(p.get("sku") or p["id"].split(":", 1)[1])
    if p["tienda"] == "ripley":
        return [sku + "P", sku]
    if p["tienda"] == "paris":
        return [sku, sku + "-1"]
    return [sku]


def _buscar_producto(cli: Cliente, p: dict) -> tuple[int | None, str]:
    """Devuelve (id de producto SoloTodo, cómo se encontró)."""
    tiendas = "&".join(f"stores={s}" for s in TIENDAS.get(p["tienda"], ()))
    # 1) La misma publicación (entidad) por SKU.
    for v in _variantes_sku(p):
        j = _json(cli, f"/entities/?{tiendas}&search={urllib.parse.quote(v)}")
        for e in j.get("results", []):
            if str(e.get("sku")) == v and e.get("product"):
                return e["product"]["id"], "publicacion"
    # 2) Por código de modelo (número de parte) — solo si el resultado es único y coherente.
    cods = sorted(codigos(p["nombre"]), key=len, reverse=True)
    for c in cods[:2]:
        if len(c) < 6:
            continue
        j = _json(cli, f"/products/?search={urllib.parse.quote(c)}&page_size=5")
        res = j.get("results", [])
        if len(res) == 1 and not conflicto(p["nombre"], res[0]["name"]):
            return res[0]["id"], "modelo"
    return None, ""


def _historial(cli: Cliente, pid: int, tienda_propia: str) -> dict:
    desde = (datetime.now(timezone.utc) - timedelta(days=45)).strftime("%Y-%m-%dT%H:%M:%SZ")
    data = _json(cli, f"/products/{pid}/pricing_history/?timestamp_after={desde}")
    nombres = _tiendas(cli)
    propias = TIENDAS.get(tienda_propia, set())
    ahora = datetime.now(timezone.utc)
    otras, habituales = [], []
    for item in data:
        e = item.get("entity") or {}
        if e.get("condition") and "NewCondition" not in e["condition"]:
            continue  # reacondicionados / usados no sirven de referencia
        st = e.get("store")
        hist = item.get("pricing_history") or []
        for h in hist:
            ts = datetime.fromisoformat(h["timestamp"].replace("Z", "+00:00"))
            if h.get("is_available") and ahora - ts > timedelta(hours=24):
                habituales.append(float(h["offer_price"]))
        if st in propias or not hist:
            continue
        u = hist[-1]
        ts = datetime.fromisoformat(u["timestamp"].replace("Z", "+00:00"))
        if u.get("is_available") and ahora - ts < timedelta(days=3):
            otras.append({"tienda": nombres.get(st, str(st)), "precio": int(float(u["offer_price"])),
                          "url": e.get("external_url")})
    otras.sort(key=lambda x: x["precio"])
    # Una entrada por tienda (la más barata).
    vistas, unicas = set(), []
    for o in otras:
        if o["tienda"] not in vistas:
            vistas.add(o["tienda"])
            unicas.append(o)
    return {
        "otras": unicas[:6],
        "ref_tiendas": unicas[0]["precio"] if unicas else None,
        "ref_historial": int(statistics.median(habituales)) if len(habituales) >= 5 else None,
        "min_historial": int(min(habituales)) if habituales else None,
    }


def verificar(cli: Cliente, p: dict, cache: dict, ahora: float) -> dict | None:
    """Consulta SoloTodo para el producto p (con caché). None si no se encontró."""
    c = cache.get(p["id"])
    if c and ahora - c["ts"] < (TTL_OK if c.get("r") else TTL_NADA):
        return c.get("r")
    try:
        pid, como = _buscar_producto(cli, p)
        r = None
        if pid:
            r = {"pid": pid, "como": como, "url": WEB.format(id=pid), **_historial(cli, pid, p["tienda"])}
            if not (r["ref_tiendas"] or r["ref_historial"]):
                r = None
    except (Bloqueado, json.JSONDecodeError, KeyError, ValueError) as e:
        print("   SoloTodo:", type(e).__name__, str(e)[:100])
        return c.get("r") if c else None
    cache[p["id"]] = {"ts": int(ahora), "r": r}
    return r


def podar_cache(cache: dict, ahora: float) -> None:
    for k in [k for k, v in cache.items() if ahora - v["ts"] > 2 * TTL_NADA]:
        del cache[k]
