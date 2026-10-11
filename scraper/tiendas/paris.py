"""Paris: usa el mismo buscador que la web de Paris (Constructor.io).

paris.cl bloquea servidores fuera de Chile, pero su catálogo se sirve desde
el buscador Constructor.io con una clave pública que la propia web incluye.
Ventajas: 100 productos por página y orden por "mejor descuento".
"""
from __future__ import annotations

import json
import urllib.parse

from ..http import Bloqueado, Cliente

CLAVE = "key_8pjkPsSkEsJHKgxR"  # clave pública del buscador de paris.cl
API = "https://ac.cnstrc.com/browse/group_id/{grupo}"
POR_PAGINA = 100


def _lista(precio: int, desc_pct) -> int | None:
    try:
        d = float(desc_pct or 0)
    except (TypeError, ValueError):
        return None
    if d <= 0 or d >= 100:
        return None
    return int(round(precio / (1 - d / 100) / 10.0) * 10)


def parsear(txt: str, categoria_defecto: str) -> tuple[list[dict], int]:
    try:
        j = json.loads(txt)
    except json.JSONDecodeError as e:
        raise Bloqueado(f"Paris: respuesta no es JSON ({txt[:80]!r})") from e
    res = j.get("response") or {}
    total = int(res.get("total_num_results") or 0)
    total_paginas = max(1, -(-min(total, 10000) // POR_PAGINA))
    productos = []
    for it in res.get("results") or []:
        d = it.get("data") or {}
        precio = d.get("displayedPrice")
        if not precio:
            continue
        precio = int(precio)
        pid = str(d.get("id") or "")
        if not pid:
            continue
        url = d.get("url") or f"https://www.paris.cl/{d.get('slug')}.html"
        url = url.replace("https://paris.cl/", "https://www.paris.cl/")
        grupos = [g.get("display_name") for g in d.get("groups") or [] if g.get("display_name")]
        vendedores = d.get("sellers") or []
        productos.append({
            "id": f"paris:{pid}",
            "tienda": "paris",
            "sku": pid,
            "nombre": (it.get("value") or "").strip(),
            "marca": (d.get("brand") or "").strip(),
            "url": url,
            "img": (d.get("image_url") or "").replace("792x1068", "384x0") or None,
            "precio": precio,
            "precio_tarjeta": None,
            "precio_lista": _lista(precio, d.get("discountPercentage")),
            "vendedor": vendedores[0] if vendedores and vendedores[0].lower() != "paris" else None,
            "categoria": (grupos[0] if grupos else categoria_defecto).lower(),
        })
    return productos, total_paginas


def pagina(cli: Cliente, grupo: str, n: int, orden: str | None = None) -> tuple[list[dict], int]:
    q = {
        "key": CLAVE, "c": "ciojs-client-2.66.0", "i": "cazaofertas", "s": "1",
        "page": n, "num_results_per_page": POR_PAGINA,
    }
    if orden == "descuento":
        q.update(sort_by="best-discount", sort_order="descending")
    url = API.format(grupo=urllib.parse.quote(grupo)) + "?" + urllib.parse.urlencode(q)
    return parsear(cli.get(url), grupo)
