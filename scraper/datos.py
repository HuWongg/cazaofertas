"""Persistencia: catálogo con historial de precios + estado entre ejecuciones."""
from __future__ import annotations

import gzip
import json
import os
import time
from pathlib import Path

from . import config

DIR = Path(os.environ.get("CAZA_DATA", "data"))
CATALOGO = DIR / "catalogo.json.gz"
ESTADO = DIR / "estado.json"


def hoy() -> int:
    # Día local de Chile aproximado (UTC-3/-4): restamos 3 horas.
    return int((time.time() - 3 * 3600) // 86400)


def cargar_catalogo() -> dict:
    if CATALOGO.exists():
        with gzip.open(CATALOGO, "rt", encoding="utf-8") as f:
            return json.load(f)
    return {}


def guardar_catalogo(cat: dict) -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    tmp = CATALOGO.with_suffix(".tmp")
    with gzip.open(tmp, "wt", encoding="utf-8", compresslevel=9) as f:
        json.dump(cat, f, ensure_ascii=False, separators=(",", ":"))
    tmp.replace(CATALOGO)


def cargar_estado() -> dict:
    if ESTADO.exists():
        return json.loads(ESTADO.read_text(encoding="utf-8"))
    return {}


def guardar_estado(est: dict) -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    ESTADO.write_text(json.dumps(est, ensure_ascii=False, indent=1), encoding="utf-8")


def registrar(cat: dict, p: dict, ahora: float) -> None:
    """Agrega/actualiza un producto en el catálogo y su historial diario (mínimo del día)."""
    d = hoy()
    e = cat.get(p["id"])
    if e is None:
        e = cat[p["id"]] = {"h": []}
    e.update({
        "n": p["nombre"], "m": p.get("marca") or "", "t": p["tienda"], "u": p["url"],
        "i": p.get("img"), "c": p.get("categoria"), "v": p.get("vendedor"),
        "p": p["precio"], "pt": p.get("precio_tarjeta"), "pl": p.get("precio_lista"),
        "ts": int(ahora),
    })
    if p.get("agotado"):
        e["x"] = 1
    else:
        e.pop("x", None)
    h = e["h"]
    if h and h[-1][0] == d:
        h[-1][1] = min(h[-1][1], p["precio"])
    else:
        h.append([d, p["precio"]])
    if len(h) > config.DIAS_HISTORIAL:
        del h[: len(h) - config.DIAS_HISTORIAL]


def podar(cat: dict, ahora: float) -> int:
    """Borra productos que no se ven hace más de DIAS_HISTORIAL días."""
    limite = ahora - config.DIAS_HISTORIAL * 86400
    viejos = [k for k, v in cat.items() if v.get("ts", 0) < limite]
    for k in viejos:
        del cat[k]
    return len(viejos)


def a_producto(pid: str, e: dict) -> dict:
    return {
        "id": pid, "tienda": e["t"], "nombre": e["n"], "marca": e.get("m", ""), "url": e["u"],
        "img": e.get("i"), "categoria": e.get("c"), "vendedor": e.get("v"),
        "precio": e["p"], "precio_tarjeta": e.get("pt"), "precio_lista": e.get("pl"),
        "ts": e.get("ts", 0), "agotado": bool(e.get("x")),
    }
