"""Detección de errores de precio.

Señales (todas comparan contra precios de OTRAS fuentes, nunca contra el "precio normal"
que la misma tienda dice):
  - entre_tiendas: el mismo producto en OTRA tienda (Falabella/Ripley/Paris) cuesta el doble o más.
  - caida:         el producto costaba el doble o más hace poco (lo vimos nosotros) y bajó de golpe.
  - historial:     cuesta la mitad o menos que su precio habitual de los últimos días (nuestro historial).
  - externo:       SoloTodo confirma: otras tiendas lo venden al doble o más, o su precio habitual
                   en 45 días es el doble o más.
  - declarado:     solo lo que dice la tienda (no confiable; sirve para elegir qué verificar).
"""
from __future__ import annotations

import statistics

from . import config
from .datos import a_producto, hoy
from .matching import agrupar, conflicto, es_accesorio, jaccard


def _referencia_cruzada(p: dict, grupos_de: dict, ahora: float):
    """Precio de referencia = la publicación más barata del mismo producto en OTRA tienda."""
    vigencia = ahora - config.HORAS_VIGENCIA_PRECIO * 3600
    otros: dict[str, tuple[dict, str]] = {}
    for clave, miembros in grupos_de.get(p["id"], []):
        fuerte = clave.startswith("cod:")
        for o in miembros:
            if o["tienda"] == p["tienda"] or o["id"] in otros:
                continue
            if o.get("ts", 0) < vigencia or o.get("agotado"):
                continue
            if es_accesorio(p["nombre"]) != es_accesorio(o["nombre"]) or conflicto(p["nombre"], o["nombre"]):
                continue
            sim = jaccard(p["nombre"], o["nombre"])
            minimo = (0.25 if len(clave.rsplit(":", 1)[-1]) >= 7 else 0.45) if fuerte else 0.6
            if sim < minimo:
                continue
            otros[o["id"]] = (o, "codigo" if fuerte else "nombre")
    if not otros:
        return None, [], None
    comparados = sorted(otros.values(), key=lambda x: x[0]["precio"])
    lista = [{"tienda": o["tienda"], "nombre": o["nombre"], "precio": o["precio"], "url": o["url"], "por": t}
             for o, t in comparados[:6]]
    por = "codigo" if any(t == "codigo" for _, t in comparados) else "nombre"
    return comparados[0][0]["precio"], lista, por


def _referencia_historial(h: list) -> int | None:
    d = hoy()
    pasados = [precio for dia, precio in h if dia < d]
    if len(pasados) < config.DIAS_MINIMOS_HISTORIAL:
        return None
    return int(statistics.median(pasados))


def _desc(precio: int, ref) -> float | None:
    return round(1 - precio / ref, 4) if ref else None


def detectar(catalogo: dict, evaluar: set[str], ahora: float, externos: dict | None = None) -> list[dict]:
    """externos: {id_producto: resultado de SoloTodo} ya consultados."""
    externos = externos or {}
    productos = [a_producto(k, v) for k, v in catalogo.items()]
    grupos_de: dict[str, list] = {}
    for clave, miembros in agrupar(productos).items():
        for m in miembros:
            grupos_de.setdefault(m["id"], []).append((clave, miembros))

    u = config.UMBRAL_DESCUENTO
    ofertas = []
    for p in productos:
        if p["id"] not in evaluar or p.get("agotado"):
            continue
        precio = p["precio"]
        senales: dict[str, float] = {}

        ref_c, comparados, por = _referencia_cruzada(p, grupos_de, ahora)
        d_c = _desc(precio, ref_c)
        if d_c is not None and d_c >= u:
            senales["entre_tiendas"] = d_c

        ant = p.get("precio_anterior")
        d_caida = None
        if ant and p.get("cambio_ts") and ahora - p["cambio_ts"] < 48 * 3600:
            d_caida = _desc(precio, ant)
            if d_caida >= u:
                senales["caida"] = d_caida

        h = catalogo[p["id"]].get("h", [])
        ref_h = _referencia_historial(h)
        d_h = _desc(precio, ref_h)
        if d_h is not None and d_h >= u:
            senales["historial"] = d_h

        ext = externos.get(p["id"])
        d_ext_t = d_ext_h = None
        if ext:
            d_ext_t = _desc(precio, ext.get("ref_tiendas"))
            d_ext_h = _desc(precio, ext.get("ref_historial"))
            mejor = max(x for x in (d_ext_t, d_ext_h, -1.0) if x is not None)
            if mejor >= u:
                senales["externo"] = mejor

        d_dec = _desc(precio, p.get("precio_lista"))
        if d_dec is not None and d_dec >= u:
            senales["declarado"] = d_dec

        if not senales:
            continue

        # ¿SoloTodo lo desmiente? (otras tiendas y su historial lo tienen a un precio parecido)
        desmentido = bool(ext) and "externo" not in senales and all(
            x is None or x < u * 0.6 for x in (d_ext_t, d_ext_h))

        reales = [k for k in senales if k != "declarado"]
        if desmentido:
            confianza = "falso"
        elif ("externo" in senales or ("entre_tiendas" in reales and len(reales) >= 2)
              or ("entre_tiendas" in reales and por == "codigo" and len({c["tienda"] for c in comparados}) >= 2)):
            confianza = "alta"
        elif reales:
            confianza = "media"
        else:
            confianza = "baja"

        descuento = max((v for k, v in senales.items() if k != "declarado"), default=senales.get("declarado", 0))
        ofertas.append({
            **{k: p[k] for k in ("id", "tienda", "nombre", "marca", "url", "img", "categoria",
                                 "vendedor", "precio", "precio_tarjeta", "precio_lista")},
            "tipos": list(senales),
            "confianza": confianza,
            "descuento": round(descuento, 4),
            "desc_cruzado": d_c, "ref_cruzada": int(ref_c) if ref_c else None, "comparados": comparados,
            "desc_caida": d_caida if "caida" in senales else None,
            "precio_anterior": ant if "caida" in senales else None,
            "desc_historial": d_h, "ref_historial": ref_h,
            "desc_declarado": d_dec,
            "externo": ({**ext, "desc_tiendas": d_ext_t, "desc_historial": d_ext_h} if ext else None),
            "historial": h[-30:],
        })

    orden = {"alta": 0, "media": 1, "baja": 2, "falso": 3}
    ofertas.sort(key=lambda o: (orden[o["confianza"]], -o["descuento"]))
    return ofertas


def candidatos_externos(ofertas: list[dict], cache: dict, ahora: float, maximo: int) -> list[dict]:
    """Elige qué ofertas verificar en SoloTodo: primero las señales fuertes, luego las declaradas grandes."""
    def prioridad(o):
        fuerte = bool(set(o["tipos"]) & {"caida", "entre_tiendas", "historial"})
        return (0 if fuerte else 1, -(o["descuento"] or 0))

    elegidos = []
    for o in sorted(ofertas, key=prioridad):
        if len(elegidos) >= maximo:
            break
        c = cache.get(o["id"])
        if c and ahora - c["ts"] < (4 * 3600 if c.get("r") else 24 * 3600):
            continue  # ya consultado hace poco
        if o["tipos"] == ["declarado"] and (o.get("desc_declarado") or 0) < config.UMBRAL_VERIFICAR_DECLARADO:
            continue
        elegidos.append(o)
    return elegidos
