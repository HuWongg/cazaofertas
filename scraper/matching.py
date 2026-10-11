"""Reconoce el mismo producto publicado en distintas tiendas (o por distintos vendedores).

Dos formas de agrupar:
1. Código de modelo (fuerte): tokens como "15-FB3027LA", "A14-52MT-59PE", "DD1391-100",
   "SM-S921B", "MKBP2R9WS0"... Mismo código + misma marca = mismo producto.
2. Huella del nombre (débil): marca + palabras importantes del nombre, en cualquier orden.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict

# Patrones de "especificaciones" que se repiten en muchos productos y NO identifican un modelo.
_GENERICO = re.compile(
    r"^("
    r"\d+(GB|TB|MB|HZ|W|WH|MAH|MM|CM|ML|KG|GR|G|PULG|MP|K|V|LT|L|LTS|BTU|RPM|NITS|MS|P|FPS|X)"
    r"|(RTX|GTX|RX|GT|MX|RTX\d*TI|ARC)\d+[A-Z]*"
    r"|I[3579]\d*[A-Z]*|R[3579]|RYZEN\d*|CORE\d*|ULTRA\d*|M[1-5](PRO|MAX)?"
    r"|DDR\d+[A-Z]*|LPDDR\d+[A-Z]*|GEN\d+|USB\d*[A-Z]*|WIFI\d*[A-Z]*|BT\d*|5G|4G|LTE|NFC"
    r"|\d+K|UHD\d*|FHD\d*|QHD\d*|OLED\d*|HDMI\d*|PCIE\d*|NVME\d*|SSD\d*|HDD\d*"
    r"|PS[345]|PS\d+PRO|XBOX\d*|SWITCH\d*|IPHONE\d+[A-Z]*|GALAXY[A-Z]*\d*"
    r"|\d{4}"  # años
    r")$"
)

_STOP = set(
    """de del la el los las y con para en sin por al a un una x
    color negro blanco gris azul rojo verde rosado rosa beige cafe plateado dorado morado
    amarillo naranjo celeste lila crema grafito plata oro negra blanca roja
    hombre mujer unisex nino nina ninos ninas adulto infantil juvenil
    nuevo nueva original oficial pack set kit
    zapatilla zapatillas running urbana urbanas deportiva deportivas
    talla tallas modelo version edicion
    """.split()
)

_ACCESORIOS = set(
    """funda fundas carcasa carcasas lamina laminas protector protectores mica micas
    cable cables cargador cargadores adaptador soporte correa correas repuesto repuestos
    estuche case cover skin sticker vidrio templado control mando
    """.split()
)


def normalizar(txt: str) -> str:
    t = unicodedata.normalize("NFKD", txt or "").encode("ascii", "ignore").decode()
    return t.lower()


def palabras(txt: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", normalizar(txt))


def es_accesorio(nombre: str) -> bool:
    return bool(set(palabras(nombre)) & _ACCESORIOS)


def codigos(nombre: str, sku: str | None = None) -> set[str]:
    """Extrae posibles códigos de modelo del nombre."""
    t = unicodedata.normalize("NFKD", nombre or "").encode("ascii", "ignore").decode().upper()
    candidatos = set()
    for tok in re.findall(r"[A-Z0-9]+(?:[-/.][A-Z0-9]+)*", t):
        limpio = re.sub(r"[-/.]", "", tok)
        if not (5 <= len(limpio) <= 20):
            continue
        if not (re.search(r"[A-Z]", limpio) and re.search(r"\d", limpio)):
            continue
        if _GENERICO.match(limpio):
            continue
        # Tokens con guion pueden traer el color/talla al final: guardamos también la base.
        candidatos.add(limpio)
        if "-" in tok:
            base = tok.split("-")[0]
            if len(base) >= 5 and re.search(r"\d", base) and re.search(r"[A-Z]", base) and not _GENERICO.match(base):
                candidatos.add(base)
    return candidatos


def huella(nombre: str, marca: str) -> str | None:
    """Marca + palabras significativas ordenadas. None si es muy poco específica."""
    m = normalizar(marca).strip()
    if not m:
        return None
    ps = sorted({p for p in palabras(nombre)
                 if p not in _STOP and p not in palabras(marca) and (len(p) > 1 or p.isdigit())})
    if len(ps) < 3:
        return None
    return m + "|" + " ".join(ps)


def jaccard(a: str, b: str) -> float:
    A = {p for p in palabras(a) if p not in _STOP}
    B = {p for p in palabras(b) if p not in _STOP}
    if not A or not B:
        return 0.0
    return len(A & B) / len(A | B)


def agrupar(productos: list[dict]) -> dict[str, list[dict]]:
    """Devuelve {clave_de_grupo: [productos]} solo para grupos con 2+ publicaciones."""
    # Códigos que aparecen en demasiados productos distintos son genéricos (p.ej. "RTX4060").
    frecuencia = Counter()
    cods_por_prod = {}
    for p in productos:
        cs = codigos(p["nombre"])
        cods_por_prod[p["id"]] = cs
        for c in cs:
            frecuencia[c] += 1

    grupos: dict[str, list[dict]] = defaultdict(list)
    for p in productos:
        marca = normalizar(p.get("marca") or "").strip() or "?"
        for c in cods_por_prod[p["id"]]:
            if frecuencia[c] <= 25:
                grupos[f"cod:{marca}:{c}"].append(p)
        h = huella(p["nombre"], p.get("marca") or "")
        if h:
            grupos[f"nom:{h}"].append(p)

    return {k: v for k, v in grupos.items() if len({x["id"] for x in v}) >= 2}
