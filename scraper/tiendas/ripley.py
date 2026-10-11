"""Ripley: usa la API de catálogo que alimenta la web (api.ripley.com).

simple.ripley.cl bloquea servidores fuera de Chile, pero su API de catálogo
responde con un token anónimo (el mismo que usa la página).
"""
from __future__ import annotations

import json
import re
import time
import unicodedata
import urllib.parse

from ..http import Bloqueado, Cliente

API = "https://api.ripley.com/experience/retail/web/api-findability-orchestrator/v1"
WEB = "https://simple.ripley.cl"
POR_PAGINA = 50
_HDR = {"Accept": "application/json", "Origin": WEB, "Referer": WEB + "/"}
_token: dict = {"valor": None, "vence": 0.0}


def _slug(txt: str) -> str:
    t = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def _obtener_token(cli: Cliente, forzar: bool = False) -> str:
    if not forzar and _token["valor"] and time.time() < _token["vence"]:
        return _token["valor"]
    j = json.loads(cli.get(API + "/auth", headers=_HDR))
    d = j.get("data") or j
    _token["valor"] = d["access_token"]
    _token["vence"] = time.time() + max(60, int(d.get("expires_in") or 600) - 60)
    return _token["valor"]


def parsear_data(data: dict, categoria: str) -> tuple[list[dict], int]:
    prods = data.get("products") or []
    total = int(data.get("total") or 0)
    limite = int(data.get("limit") or POR_PAGINA) or POR_PAGINA
    total_paginas = max(1, -(-total // limite))

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
            url = f"{WEB}/{_slug(p.get('name') or '')}-{pid}"
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


def _nombre_categoria(data: dict, codigo: str) -> str:
    meta = data.get("meta") or {}
    return (meta.get("name") or meta.get("mainTitle") or codigo.split("*")[-1].replace("_", " ")).lower()


def pagina(cli: Cliente, codigo: str, n: int) -> tuple[list[dict], int]:
    q = {"catalog": codigo, "limit": POR_PAGINA, "offset": (n - 1) * POR_PAGINA}
    url = API + "/findability/catalog?" + urllib.parse.urlencode(q)
    for intento in range(2):
        hdr = {**_HDR, "x-access-token": _obtener_token(cli, forzar=intento > 0)}
        try:
            txt = cli.get(url, headers=hdr)
        except Bloqueado as e:
            if "401" in str(e) and intento == 0:
                continue
            raise
        j = json.loads(txt)
        data = j.get("data") or {}
        if not isinstance(data, dict) or "products" not in data:
            raise Bloqueado(f"Ripley: respuesta inesperada ({str(j)[:120]})")
        return parsear_data(data, _nombre_categoria(data, codigo))
    raise Bloqueado("Ripley: token rechazado")


# Compatibilidad con pruebas antiguas: parsear HTML de la web (__NEXT_DATA__).
_NEXT = re.compile(r'<script id="__NEXT_DATA__" type="application/json"[^>]*>(.*?)</script>', re.S)


def parsear(html: str, categoria: str) -> tuple[list[dict], int]:
    m = _NEXT.search(html)
    if not m:
        raise Bloqueado("Ripley: página sin __NEXT_DATA__")
    pp = json.loads(m.group(1)).get("props", {}).get("pageProps", {})
    return parsear_data((pp.get("findabilityProps") or {}).get("data") or {}, categoria)
