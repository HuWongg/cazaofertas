"""Paris: Next.js con React Server Components.

Los productos vienen dentro de los fragmentos `self.__next_f.push([1,"..."])`.
Cada producto tiene un bloque `"masterVariant":{..."prices":{"regular":...,"offer":...,"paymentMethod":...}}`.
"""
from __future__ import annotations

import json
import re

from ..http import Bloqueado, Cliente

BASE = "https://www.paris.cl"
_PUSH = re.compile(r'self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)', re.S)
_MV = '"masterVariant":{'
_dec = json.JSONDecoder()


def _rsc(html: str) -> str:
    partes = []
    for m in _PUSH.finditer(html):
        try:
            partes.append(json.loads('"' + m.group(1) + '"'))
        except json.JSONDecodeError:
            continue
    return "".join(partes)


def _monto(precios: dict, clave: str) -> int | None:
    v = (precios.get(clave) or {}).get("value") or {}
    c = v.get("centAmount")
    if c is None:
        return None
    dig = int(v.get("fractionDigits") or 0)
    return int(round(c / (10 ** dig)))


def _campo_antes(txt: str, desde: int, limite: int, campo: str) -> str | None:
    i = txt.rfind(f'"{campo}":"', limite, desde)
    if i < 0:
        return None
    try:
        val, _ = _dec.raw_decode(txt, i + len(campo) + 3)
        return val if isinstance(val, str) else None
    except json.JSONDecodeError:
        return None


def parsear(html: str, categoria: str) -> list[dict]:
    txt = _rsc(html)
    if _MV not in txt:
        if "__next_f" not in html:
            raise Bloqueado("Paris: página sin datos de productos (posible bloqueo)")
        return []
    productos, vistos = [], set()
    pos, anterior = 0, 0
    while True:
        i = txt.find(_MV, pos)
        if i < 0:
            break
        pos = i + len(_MV)
        try:
            mv, fin = _dec.raw_decode(txt, i + len(_MV) - 1)
        except json.JSONDecodeError:
            continue
        # Inicio aproximado del objeto producto: el "slug" más cercano hacia atrás.
        lim = max(anterior, i - 20000)
        slug = _campo_antes(txt, i, lim, "slug")
        nombre = _campo_antes(txt, i, lim, "name")
        marca = _campo_antes(txt, i, lim, "brand") or ""
        anterior = fin
        precios = mv.get("prices") or {}
        regular = _monto(precios, "regular")
        oferta = _monto(precios, "offer")
        tarjeta = _monto(precios, "paymentMethod")
        precio = oferta or regular
        if not (slug and nombre and precio):
            continue
        sku = str(mv.get("sku") or mv.get("id") or slug).split("-")[0]
        if sku in vistos:
            continue
        vistos.add(sku)
        lista = regular if regular and regular > precio else None
        if tarjeta and tarjeta >= precio:
            tarjeta = None
        imgs = mv.get("images") or []
        img = imgs[0].get("url") if imgs and isinstance(imgs[0], dict) else None
        if img:
            img = img.replace("792x1068", "384x0")
        productos.append({
            "id": f"paris:{sku}",
            "tienda": "paris",
            "sku": sku,
            "nombre": nombre.replace('\\"', '"').strip(),
            "marca": marca.strip(),
            "url": f"{BASE}/{slug}.html",
            "img": img,
            "precio": precio,
            "precio_tarjeta": tarjeta,
            "precio_lista": lista,
            "vendedor": None,
            "categoria": categoria,
        })
    return productos


def pagina(cli: Cliente, ruta: str) -> list[dict]:
    partes = [p for p in ruta.strip("/").split("/") if p]
    cat = (partes[-1] if partes else ruta).replace("-", " ")
    return parsear(cli.get(BASE + ruta), cat)
