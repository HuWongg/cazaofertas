"""Pruebas rápidas con datos de ejemplo (formato real de cada tienda, sin conexión).

    python -m pytest tests -q      (o)      python tests/test_basico.py
"""
import json
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["CAZA_DATA"] = tempfile.mkdtemp()

from scraper import datos  # noqa: E402
from scraper.detectar import detectar  # noqa: E402
from scraper.matching import codigos, huella  # noqa: E402
from scraper.tiendas import falabella, paris, ripley  # noqa: E402


def html_next(obj):
    return ('<html><script id="__NEXT_DATA__" type="application/json">'
            + json.dumps(obj) + "</script></html>")


FAL = html_next({"props": {"pageProps": {
    "pagination": {"count": 1260, "currentPage": 1, "perPage": 48},
    "results": [{
        "productId": "17482518", "skuId": "17482518", "brand": "HP",
        "displayName": "Notebook Gamer Victus 15-FB3027LA AMD Ryzen 7 16GB RAM DDR5 NVIDIA RTX 4050 512GB SSD",
        "url": "https://www.falabella.com/falabella-cl/product/17482518/x",
        "mediaUrls": ["https://media.falabella.com/falabellaCL/17482518_01/public"],
        "sellerName": "Falabella",
        "prices": [
            {"type": "cmrPrice", "price": ["399.990"], "crossed": False},
            {"type": "internetPrice", "price": ["419.990"], "crossed": False},
            {"type": "normalPrice", "price": ["1.159.990"], "crossed": True},
        ],
    }],
}}})

RIP = html_next({"props": {"pageProps": {"findabilityProps": {"data": {
    "total": 790, "limit": 48, "offset": 0,
    "products": [{
        "sku": "26439997", "parentProductID": "MPM10003194461", "brand": "HP",
        "name": "NOTEBOOK HP VICTUS 15-FB3027LA RYZEN 7 16GB 512GB RTX 4050",
        "primaryImage": "https://rimage.ripley.cl/a.jpg",
        "priceNumber": 1049990, "masterPriceNumber": 1199990, "ripleyPriceNumber": 999990,
        "seller": "MARKETPLACE", "shop": {"shopName": "HP STORE"}, "inStock": True,
    }],
    "structuredData": {"@graph": [{}, {}, {"mainEntity": {"itemListElement": [
        {"item": {"image": "https://rimage.ripley.cl/a.jpg", "url": "https://simple.ripley.cl/notebook-hp-mpm10003194461"}}
    ]}}]},
}}}}})

_prod_paris = {
    "id": "MKBP2R9WS0", "key": "MKBP2R9WS0", "name": "Notebook HP Victus 15-FB3027LA Ryzen 7 16GB 512GB",
    "slug": "notebook-hp-victus-15-fb3027la-MKBP2R9WS0", "brand": "HP", "sellers": ["HP"],
    "masterVariant": {"id": "MKBP2R9WS0-1", "sku": "MKBP2R9WS0-1", "prices": {
        "regular": {"value": {"type": "centPrecision", "centAmount": 1199990, "currencyCode": "CLP", "fractionDigits": 0}},
        "offer": {"value": {"type": "centPrecision", "centAmount": 999990, "currencyCode": "CLP", "fractionDigits": 0}},
        "paymentMethod": {"value": {"type": "centPrecision", "centAmount": 949990, "currencyCode": "CLP", "fractionDigits": 0}},
    }, "images": [{"url": "https://cl-cenco/792x1068/a.jpg"}]},
}
_rsc = '5:["$","div",null,{"initialState":{"productData":{"products":[' + json.dumps(_prod_paris, separators=(",", ":")) + ']}}}]'
PAR = ('<html><script>self.__next_f.push([1,' + json.dumps(_rsc) + '])</script></html>')


def test_parsers():
    f, tot = falabella.parsear(FAL, "notebooks")
    assert tot == 27 and f[0]["precio"] == 419990 and f[0]["precio_tarjeta"] == 399990
    assert f[0]["precio_lista"] == 1159990
    r, tot = ripley.parsear(RIP, "notebooks")
    assert tot == 17 and r[0]["precio"] == 1049990 and r[0]["url"].endswith("mpm10003194461")
    assert r[0]["vendedor"] == "HP STORE"
    p = paris.parsear(PAR, "notebooks")
    assert p and p[0]["precio"] == 999990 and p[0]["precio_lista"] == 1199990
    assert p[0]["sku"] == "MKBP2R9WS0" and p[0]["url"].endswith("MKBP2R9WS0.html")
    return f, r, p


def test_codigos():
    assert "15FB3027LA" in codigos("Notebook Gamer Victus 15-FB3027LA AMD Ryzen 7 16GB RTX 4050 512GB")
    assert codigos("Notebook 16GB 512GB RTX4050 i7-13620H 2025") == set()
    assert {"DD1391100", "DD1391"} <= codigos("Zapatilla Nike Dunk Low DD1391-100 Hombre")
    a = huella("Smart TV LG 55 UHD 4K ThinQ AI Negro", "LG")
    b = huella("Smart TV 55 UHD 4K ThinQ AI LG", "lg")
    assert a and a == b


def test_deteccion_entre_tiendas():
    f, r, p = test_parsers()
    cat = {}
    ahora = time.time()
    for x in f + r + p:
        datos.registrar(cat, x, ahora)
    ofertas = detectar(cat, {x["id"] for x in f + r + p}, ahora)
    ids = {o["id"]: o for o in ofertas}
    o = ids.get("falabella:17482518")
    assert o, f"no detectó la oferta cruzada: {ofertas}"
    assert "entre_tiendas" in o["tipos"] and o["confianza"] == "alta", o
    assert round(o["desc_cruzado"], 2) == round(1 - 419990 / 1024990, 2)
    # Las publicaciones caras no son oferta.
    assert "ripley:26439997" not in ids and "paris:MKBP2R9WS0" not in ids


def test_historial():
    cat = {}
    hoy = datos.hoy()
    prod = {"id": "ripley:1", "tienda": "ripley", "nombre": "Aspiradora Robot X200 Pro", "marca": "Xiaomi",
            "url": "u", "precio": 49990, "categoria": "c"}
    datos.registrar(cat, prod, time.time())
    cat["ripley:1"]["h"] = [[hoy - 5, 199990], [hoy - 4, 189990], [hoy - 3, 199990], [hoy, 49990]]
    ofertas = detectar(cat, {"ripley:1"}, time.time())
    assert ofertas and ofertas[0]["tipos"] == ["historial"] and ofertas[0]["confianza"] == "media"


if __name__ == "__main__":
    for nombre, fn in list(globals().items()):
        if nombre.startswith("test_"):
            fn()
            print("ok", nombre)
