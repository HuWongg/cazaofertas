"""Ejecución completa: recolecta precios, detecta ofertas, avisa y genera los datos de la web.

Uso:
    python run.py                 # corrida normal
    python run.py --solo falabella --rapido   # prueba rápida de una tienda
"""
from __future__ import annotations

import argparse
import json
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from scraper import alertas, config, datos
from scraper.detectar import detectar
from scraper.http import Bloqueado, Cliente
from scraper.tiendas import falabella, paris, ripley

SITIO_DATA = Path("site/data")


def _paginas(clave: str, maximo: int, corrida: int, conocidas: dict, rapido: bool) -> list[int]:
    maximo = min(maximo, conocidas.get(clave, maximo))
    fijas = list(range(1, min(config.PAGINAS_FIJAS, maximo) + 1))
    if rapido:
        return fijas[:1]
    profundas = list(range(config.PAGINAS_FIJAS + 1, maximo + 1))
    if not profundas:
        return fijas
    k = config.PAGINAS_ROTATIVAS
    ini = (corrida * k) % len(profundas)
    rot = [profundas[(ini + j) % len(profundas)] for j in range(min(k, len(profundas)))]
    return fijas + sorted(set(rot))


def _rotar(lista: list, corrida: int) -> list:
    if not lista:
        return lista
    i = corrida % len(lista)
    return lista[i:] + lista[:i]


def recolectar(tienda: str, corrida: int, estado: dict, rapido: bool) -> tuple[list[dict], dict]:
    cli = Cliente(tienda)
    inicio = time.time()
    limite = inicio + (60 if rapido else config.PRESUPUESTO_SEGUNDOS_POR_TIENDA)
    conocidas = estado.setdefault("paginas", {})
    productos: list[dict] = []
    errores: list[str] = []
    bloqueos = 0

    def intento(fn, etiqueta):
        nonlocal bloqueos
        try:
            return fn()
        except Bloqueado as e:
            bloqueos += 1
            errores.append(f"{etiqueta}: {e}")
        except Exception as e:  # noqa: BLE001
            errores.append(f"{etiqueta}: {type(e).__name__}: {e}")
            traceback.print_exc()
        return None

    if tienda == "falabella":
        cats = _rotar(config.FALABELLA_CATEGORIAS, corrida)
        if rapido:
            cats = cats[:2]
        for cat, slug, maxp in cats:
            for n in _paginas(f"fal:{cat}", maxp, corrida, conocidas, rapido):
                if time.time() > limite or bloqueos >= 6:
                    break
                r = intento(lambda: falabella.pagina(cli, cat, slug, n), f"{slug} p{n}")
                if r:
                    prods, tot = r
                    conocidas[f"fal:{cat}"] = tot
                    productos += prods
                    if n >= tot:
                        break
    elif tienda == "ripley":
        cats = _rotar(config.RIPLEY_CATEGORIAS, corrida)
        if rapido:
            cats = cats[:2]
        for ruta, maxp in cats:
            for n in _paginas(f"rip:{ruta}", maxp, corrida, conocidas, rapido):
                if time.time() > limite or bloqueos >= 6:
                    break
                r = intento(lambda: ripley.pagina(cli, ruta, n), f"{ruta} p{n}")
                if r:
                    prods, tot = r
                    conocidas[f"rip:{ruta}"] = tot
                    productos += prods
                    if n >= tot:
                        break
    elif tienda == "paris":
        deps = _rotar(config.PARIS_DEPARTAMENTOS, corrida)
        if rapido:
            deps = deps[:2]
        # 1) Lo más rebajado de cada departamento (donde aparecen los errores de precio).
        for grupo, _ in deps:
            for n in range(1, (1 if rapido else config.PARIS_PAGINAS_DESCUENTO) + 1):
                if time.time() > limite or bloqueos >= 6:
                    break
                r = intento(lambda: paris.pagina(cli, grupo, n, "descuento"), f"{grupo} desc p{n}")
                if r:
                    productos += r[0]
                    conocidas[f"par:{grupo}"] = r[1]
        # 2) Recorrido normal (rotativo) para tener historial y comparar entre tiendas.
        for grupo, maxp in deps:
            for n in _paginas(f"par:{grupo}", maxp, corrida, conocidas, rapido):
                if time.time() > limite or bloqueos >= 6:
                    break
                r = intento(lambda: paris.pagina(cli, grupo, n), f"{grupo} p{n}")
                if r:
                    productos += r[0]

    # Sin duplicados dentro de la misma corrida.
    unicos = {p["id"]: p for p in productos}
    resumen = {
        "ok": len(unicos) > 0,
        "productos": len(unicos),
        "peticiones": cli.peticiones,
        "errores": len(errores),
        "bloqueos": bloqueos,
        "detalle_errores": errores[-5:],
        "segundos": round(time.time() - inicio),
    }
    print(f"[{tienda}] {resumen['productos']} productos, {cli.peticiones} peticiones, "
          f"{len(errores)} errores ({bloqueos} bloqueos), {resumen['segundos']}s")
    for e in errores[-5:]:
        print(f"   ! {e}")
    return list(unicos.values()), resumen


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--solo", choices=["falabella", "ripley", "paris"])
    ap.add_argument("--rapido", action="store_true", help="pocas páginas, para probar")
    ap.add_argument("--sin-alertas", action="store_true")
    args = ap.parse_args()

    ahora = time.time()
    estado = datos.cargar_estado()
    catalogo = datos.cargar_catalogo()
    corrida = estado.get("corrida", 0) + 1
    estado["corrida"] = corrida
    print(f"Corrida #{corrida} — catálogo con {len(catalogo)} productos")

    tiendas = [args.solo] if args.solo else ["falabella", "ripley", "paris"]
    with ThreadPoolExecutor(max_workers=len(tiendas)) as ex:
        resultados = dict(zip(tiendas, ex.map(lambda t: recolectar(t, corrida, estado, args.rapido), tiendas)))

    vistos = set()
    estado_tiendas = estado.setdefault("tiendas", {})
    for t, (prods, resumen) in resultados.items():
        for p in prods:
            datos.registrar(catalogo, p, ahora)
            vistos.add(p["id"])
        previo = estado_tiendas.get(t, {})
        resumen["ts"] = int(ahora)
        resumen["ultimo_ok"] = int(ahora) if resumen["ok"] else previo.get("ultimo_ok")
        estado_tiendas[t] = resumen

    borrados = datos.podar(catalogo, ahora)
    # Se evalúan los productos vistos en las últimas 6 horas: como las páginas profundas
    # van rotando, así el panel muestra todo lo vigente y no solo lo de esta corrida.
    recientes = {k for k, v in catalogo.items() if v.get("ts", 0) >= ahora - 6 * 3600}
    ofertas = detectar(catalogo, recientes | vistos, ahora)
    # Las que solo tienen el descuento "declarado" por la tienda son muchísimas y poco
    # confiables: se guardan solo las 400 mayores (con precio normal ≥ $10.000).
    confirmadas = [o for o in ofertas if o["confianza"] != "baja"]
    declaradas = sorted((o for o in ofertas if o["confianza"] == "baja" and (o.get("precio_lista") or 0) >= 10_000),
                        key=lambda o: -(o.get("desc_declarado") or 0))[:400]
    ofertas = confirmadas + declaradas

    # Recordar desde cuándo se ve cada oferta (para marcar las nuevas).
    desde = estado.setdefault("ofertas_desde", {})
    actuales = {o["id"] for o in ofertas}
    for o in ofertas:
        o["desde"] = desde.setdefault(o["id"], int(ahora))
    for k in [k for k in desde if k not in actuales and desde[k] < ahora - 3 * 86400]:
        del desde[k]

    for o in ofertas:
        o["revisado"] = catalogo[o["id"]].get("ts", int(ahora))
    estado.pop("ofertas_previas", None)

    enviados = 0 if args.sin_alertas else alertas.procesar(ofertas, estado, ahora)

    datos.guardar_catalogo(catalogo)
    datos.guardar_estado(estado)

    SITIO_DATA.mkdir(parents=True, exist_ok=True)
    por_tienda = {}
    for v in catalogo.values():
        por_tienda[v["t"]] = por_tienda.get(v["t"], 0) + 1
    (SITIO_DATA / "ofertas.json").write_text(json.dumps({
        "generado": int(ahora),
        "umbral": config.UMBRAL_DESCUENTO,
        "ofertas": ofertas,
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (SITIO_DATA / "estado.json").write_text(json.dumps({
        "generado": int(ahora),
        "corrida": corrida,
        "catalogo": len(catalogo),
        "por_tienda": por_tienda,
        "tiendas": estado_tiendas,
        "alertas_enviadas": enviados,
        "canal_alertas": alertas.hay_canal(),
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"Ofertas: {len(ofertas)} ({sum(o['confianza'] != 'baja' for o in ofertas)} confirmadas) · "
          f"alertas enviadas: {enviados} · catálogo: {len(catalogo)} (podados {borrados})")


if __name__ == "__main__":
    main()
