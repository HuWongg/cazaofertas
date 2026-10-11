"""Ripley: los productos vienen en __NEXT_DATA__ -> findabilityProps.data.products."""
from __future__ import annotations

import json
import re
import unicodedata

from ..http import Bloqueado, Cliente

BASE = "https://simple.ripley.cl"
_NEXT = re.compile(r'<script id="__NEXT_DATA__" type="application/json"[^>]*>(.*?)</script>', re.S)


def _slug(txt: str) -> str:
    t = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def parsear(html: str, categoria: str) -> tuple[list[dict], int]:
    m = _NEXT.search(html)
    if not m:
        raise Bloqueado("Ripley: página sin __NEXT_DATA__ (posible bloqueo)")
    pp = json.loads(m.group(1)).get("props", {}).get("pageProps", {})
    data = (pp.get("findabilityProps") or {}).get("data") or {}
    prods = data.get("products") or []
    total = int(data.get("total") or 0)
    limite = int(data.get("limit") or 48) or 48
    total_paginas = max(1, -(-total // limite))

    # Las URLs "bonitas" vienen en el JSON-LD; las asociamos por imagen.
    urls_por_img = {}
    try:
        for g in (data.get("structuredData") or {}).get("@graph", []):
            for it in (g.get("mainEntity") or {}).get("itemListElement", []) or []:
                item = it.get("item") or {}
                if item.get("image") and item.get("url"):
                    urls_por_img[item["image"]] = item["url"]
    except AttributeError:
        pass

    productos = []
    for p in prods:
        precio = p.get("priceNumber") or p.get("masterPriceNumber")
        if not precio:
            continue
        lista = p.get("masterPriceNumber")
        if lista and lista <= precio:
            lista = None
        tarjeta = p.get("ripleyPriceNumber")
        if tarjeta and tarjeta >= precio:
            tarjeta = None
        img = p.get("primaryImage")
        if img and img.startswith("//"):
            img = "https:" + img
        url = urls_por_img.get(p.get("primaryImage"))
        if not url:
            pid = str(p.get("parentProductID") or p.get("sku") or "").lower()
            url = f"{BASE}/{_slug(p.get('name') or '')}-{pid}"
        vendedor = (p.get("shop") or {}).get("shopName") if p.get("seller") == "MARKETPLACE" else "Ripley"
        sku = str(p.get("sku") or p.get("parentProductID"))
        productos.append({
            "id": f"ripley:{sku}",
            "tienda": "ripley",
            "sku": sku,
            "nombre": (p.get("name") or "").strip(),
            "marca": (p.get("brand") or "").strip(),
            "url": url,
            "img": img,
            "precio": int(precio),
            "precio_tarjeta": int(tarjeta) if tarjeta else None,
            "precio_lista": int(lista) if lista else None,
            "vendedor": vendedor,
            "categoria": categoria,
            "agotado": p.get("inStock") is False,
        })
    return productos, total_paginas


def pagina(cli: Cliente, ruta: str, n: int) -> tuple[list[dict], int]:
    url = BASE + ruta + (f"?page={n}" if n > 1 else "")
    cat = ruta.rstrip("/").split("/")[-1].replace("-", " ")
    return parsear(cli.get(url), cat)
