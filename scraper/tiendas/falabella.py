"""Falabella: los productos vienen en el JSON __NEXT_DATA__ de cada página de categoría."""
from __future__ import annotations

import json
import re

from ..http import Bloqueado, Cliente

BASE = "https://www.falabella.com/falabella-cl/category/{cat}/{slug}"
_NEXT = re.compile(r'<script id="__NEXT_DATA__" type="application/json"[^>]*>(.*?)</script>', re.S)


def _num(txt) -> int | None:
    if not txt:
        return None
    if isinstance(txt, list):
        txt = txt[0] if txt else None
        if txt is None:
            return None
    digitos = re.sub(r"[^\d]", "", str(txt))
    return int(digitos) if digitos else None


def _precios(lista: list[dict]) -> tuple[int | None, int | None, int | None]:
    """Devuelve (precio público, precio con tarjeta CMR, precio normal tachado)."""
    publico, tarjeta, normal = [], None, None
    for p in lista or []:
        valor = _num(p.get("price"))
        if not valor:
            continue
        tipo = p.get("type", "")
        if tipo == "cmrPrice":
            tarjeta = valor
        elif tipo == "normalPrice" or p.get("crossed"):
            normal = valor
        else:  # internetPrice, eventPrice, etc.
            publico.append(valor)
    precio = min(publico) if publico else normal
    if normal and precio and normal <= precio:
        normal = None
    return precio, tarjeta, normal


def parsear(html: str, categoria: str) -> tuple[list[dict], int]:
    m = _NEXT.search(html)
    if not m:
        raise Bloqueado("Falabella: página sin __NEXT_DATA__ (posible bloqueo)")
    pp = json.loads(m.group(1)).get("props", {}).get("pageProps", {})
    resultados = pp.get("results") or []
    pag = pp.get("pagination") or {}
    total_paginas = 1
    if pag.get("count") and pag.get("perPage"):
        total_paginas = -(-int(pag["count"]) // int(pag["perPage"]))
    productos = []
    for r in resultados:
        precio, tarjeta, normal = _precios(r.get("prices"))
        if not precio:
            continue
        sku = str(r.get("skuId") or r.get("productId"))
        imgs = r.get("mediaUrls") or []
        productos.append({
            "id": f"falabella:{sku}",
            "tienda": "falabella",
            "sku": sku,
            "nombre": (r.get("displayName") or "").strip(),
            "marca": (r.get("brand") or "").strip(),
            "url": r.get("url") or f"https://www.falabella.com/falabella-cl/product/{r.get('productId')}",
            "img": imgs[0] if imgs else None,
            "precio": precio,
            "precio_tarjeta": tarjeta,
            "precio_lista": normal,
            "vendedor": r.get("sellerName"),
            "categoria": categoria,
        })
    return productos, total_paginas


def pagina(cli: Cliente, cat: str, slug: str, n: int) -> tuple[list[dict], int]:
    url = BASE.format(cat=cat, slug=slug) + (f"?page={n}" if n > 1 else "")
    return parsear(cli.get(url), slug.replace("-", " "))
