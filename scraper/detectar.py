"""Detección de ofertas ≥ UMBRAL comparando:
- entre publicaciones del mismo producto (otras tiendas u otros vendedores), y
- contra el historial de precios del propio producto.
El descuento que "declara" la tienda (precio normal tachado) se informa aparte.
"""
from __future__ import annotations

import statistics

from . import config
from .datos import hoy
from .matching import agrupar, es_accesorio, jaccard


def _referencia_cruzada(p: dict, grupos_de: dict, ahora: float):
    """Precio de referencia = mediana de las OTRAS publicaciones del mismo producto."""
    vigencia = ahora - config.HORAS_VIGENCIA_PRECIO * 3600
    otros: dict[str, tuple[dict, str]] = {}
    for clave, miembros in grupos_de.get(p["id"], []):
        fuerte = clave.startswith("cod:")
        for o in miembros:
            if o["id"] == p["id"] or o["id"] in otros:
                continue
            if o.get("ts", 0) < vigencia or o.get("agotado"):
                continue
            if es_accesorio(p["nombre"]) != es_accesorio(o["nombre"]):
                continue
            sim = jaccard(p["nombre"], o["nombre"])
            # Códigos cortos (p.ej. "15IRH8") pueden ser de una familia y no de un modelo exacto.
            minimo = (0.25 if len(clave.rsplit(":", 1)[-1]) >= 7 else 0.45) if fuerte else 0.6
            if sim < minimo:
                continue
            otros[o["id"]] = (o, "codigo" if fuerte else "nombre")
    if not otros:
        return None, [], None
    precios = [o["precio"] for o, _ in otros.values()]
    ref = statistics.median(precios)
    # Si hay un solo comparado, exigimos que el emparejamiento sea por código.
    tipos = {t for _, t in otros.values()}
    comparados = sorted(otros.values(), key=lambda x: x[0]["precio"])
    lista = [
        {"tienda": o["tienda"], "nombre": o["nombre"], "precio": o["precio"], "url": o["url"],
         "vendedor": o.get("vendedor"), "por": t}
        for o, t in comparados[:6]
    ]
    return ref, lista, ("codigo" if "codigo" in tipos else "nombre")


def _referencia_historial(h: list) -> int | None:
    d = hoy()
    pasados = [precio for dia, precio in h if dia < d]
    if len(pasados) < config.DIAS_MINIMOS_HISTORIAL:
        return None
    return int(statistics.median(pasados))


def detectar(catalogo: dict, vistos_ahora: set[str], ahora: float) -> list[dict]:
    from .datos import a_producto

    productos = [a_producto(k, v) for k, v in catalogo.items()]
    grupos = agrupar(productos)
    grupos_de: dict[str, list] = {}
    for clave, miembros in grupos.items():
        for m in miembros:
            grupos_de.setdefault(m["id"], []).append((clave, miembros))

    u = config.UMBRAL_DESCUENTO
    ofertas = []
    for p in productos:
        if p["id"] not in vistos_ahora or p.get("agotado"):
            continue
        precio = p["precio"]
        tipos, desc_conf = [], 0.0

        ref_c, comparados, por = _referencia_cruzada(p, grupos_de, ahora)
        d_c = (1 - precio / ref_c) if ref_c else None
        if d_c is not None and d_c >= u and (len(comparados) >= 2 or por == "codigo"):
            tipos.append("entre_tiendas")
            desc_conf = max(desc_conf, d_c)

        h = catalogo[p["id"]].get("h", [])
        ref_h = _referencia_historial(h)
        d_h = (1 - precio / ref_h) if ref_h else None
        if d_h is not None and d_h >= u:
            tipos.append("historial")
            desc_conf = max(desc_conf, d_h)

        d_dec = (1 - precio / p["precio_lista"]) if p.get("precio_lista") else None
        if d_dec is not None and d_dec >= u:
            tipos.append("declarado")

        if not tipos:
            continue

        if "entre_tiendas" in tipos and "historial" in tipos:
            confianza = "alta"
        elif "entre_tiendas" in tipos:
            confianza = "alta" if por == "codigo" and len(comparados) >= 2 else "media"
        elif "historial" in tipos:
            confianza = "media"
        else:
            confianza = "baja"  # solo lo que dice la tienda

        ofertas.append({
            **{k: p[k] for k in ("id", "tienda", "nombre", "marca", "url", "img", "categoria",
                                 "vendedor", "precio", "precio_tarjeta", "precio_lista")},
            "tipos": tipos,
            "confianza": confianza,
            "descuento": round(desc_conf if desc_conf else (d_dec or 0), 4),
            "desc_cruzado": round(d_c, 4) if d_c is not None else None,
            "ref_cruzada": int(ref_c) if ref_c else None,
            "comparados": comparados,
            "desc_historial": round(d_h, 4) if d_h is not None else None,
            "ref_historial": ref_h,
            "desc_declarado": round(d_dec, 4) if d_dec is not None else None,
            "historial": h[-30:],
        })

    orden = {"alta": 0, "media": 1, "baja": 2}
    ofertas.sort(key=lambda o: (orden[o["confianza"]], -o["descuento"]))
    return ofertas
