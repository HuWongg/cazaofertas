"""Monitoreo continuo de errores de precio.

Cada ciclo (~3 min): recolecta un tramo de cada tienda (en paralelo), detecta, verifica
en SoloTodo, avisa al celular y actualiza los datos de la web.

Uso:
    python run.py --minutos 340            # bucle continuo (lo que corre en GitHub)
    python run.py --ciclos 1 --sin-alertas  # un solo ciclo, para probar
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from scraper import alertas, config, datos, externo
from scraper.detectar import candidatos_externos, detectar
from scraper.http import Bloqueado, Cliente
from scraper.tiendas import falabella, paris, ripley

SITIO_DATA = Path("site/data")
_CLI_SOLOTODO: dict = {}
TIENDAS = ["falabella", "ripley", "paris"]


# ------------------------------------------------------------------ cola de páginas
def _nueva_cola(tienda: str, conocidas: dict) -> list[list]:
    """Barrido completo de la tienda, intercalando categorías (pág. 1 de todas, luego pág. 2...)."""
    if tienda == "falabella":
        cats = [(["fal", c, s], min(m, conocidas.get(f"fal:{c}", m))) for c, s, m in config.FALABELLA_CATEGORIAS]
    elif tienda == "ripley":
        cats = [(["rip", c], min(m, conocidas.get(f"rip:{c}", m))) for c, m in config.RIPLEY_CATEGORIAS]
    else:
        cats = [(["par", g], min(m, conocidas.get(f"par:{g}", m))) for g, m in config.PARIS_DEPARTAMENTOS]
    cola = []
    for n in range(1, max(m for _, m in cats) + 1):
        cola += [base + [n] for base, m in cats if n <= m]
    return cola


def _ejecutar(cli: Cliente, tarea: list, conocidas: dict) -> list[dict]:
    tipo = tarea[0]
    if tipo == "fal":
        _, cat, slug, n = tarea
        prods, tot = falabella.pagina(cli, cat, slug, n)
        conocidas[f"fal:{cat}"] = tot
    elif tipo == "rip":
        _, cod, n = tarea
        prods, tot = ripley.pagina(cli, cod, n)
        conocidas[f"rip:{cod}"] = tot
    elif tipo == "pardesc":
        _, grupo, n = tarea
        prods, _ = paris.pagina(cli, grupo, n, "descuento")
    else:
        _, grupo, n = tarea
        prods, tot = paris.pagina(cli, grupo, n)
        conocidas[f"par:{grupo}"] = tot
    return prods


class Recolector:
    def __init__(self, tienda: str, estado: dict):
        self.tienda = tienda
        self.cli = Cliente(tienda)
        self.estado = estado
        self.bloqueos_seguidos = 0
        self.pausado_hasta = 0.0

    def ciclo(self, segundos: float) -> tuple[list[dict], dict]:
        inicio = time.time()
        fin = inicio + segundos
        colas = self.estado.setdefault("colas", {})
        conocidas = self.estado.setdefault("paginas", {})
        productos, errores = [], []
        pet0 = self.cli.peticiones

        if time.time() < self.pausado_hasta:
            return [], {"ok": False, "productos": 0, "errores": 0, "pausado": True,
                        "detalle_errores": ["En pausa tras varios bloqueos seguidos"], "segundos": 0}

        tareas = []
        if self.tienda == "paris":  # lo más rebajado de Paris, en cada ciclo
            tareas = [["pardesc", g, n] for g, _ in config.PARIS_DEPARTAMENTOS
                      for n in range(1, config.PARIS_PAGINAS_DESCUENTO + 1)]
        cola = colas.get(self.tienda) or []
        while time.time() < fin:
            if tareas:
                t = tareas.pop(0)
            else:
                if not cola:
                    cola = _nueva_cola(self.tienda, conocidas)
                    self.estado.setdefault("barridos", {})[self.tienda] = int(time.time())
                t = cola.pop(0)
            try:
                productos += _ejecutar(self.cli, t, conocidas)
                self.bloqueos_seguidos = 0
            except Bloqueado as e:
                errores.append(f"{t[1]} p{t[-1]}: {e}")
                self.bloqueos_seguidos += 1
                if self.bloqueos_seguidos >= 5:  # la tienda nos frenó: descansar 10 min
                    self.pausado_hasta = time.time() + 600
                    self.bloqueos_seguidos = 0
                    break
            except Exception as e:  # noqa: BLE001
                errores.append(f"{t[1]} p{t[-1]}: {type(e).__name__}: {e}")
                traceback.print_exc()
        colas[self.tienda] = cola

        unicos = {p["id"]: p for p in productos}
        resumen = {
            "ok": len(unicos) > 0,
            "productos": len(unicos),
            "peticiones": self.cli.peticiones - pet0,
            "errores": len(errores),
            "detalle_errores": errores[-4:],
            "segundos": round(time.time() - inicio),
            "pendientes_barrido": len(cola),
        }
        return list(unicos.values()), resumen


# ------------------------------------------------------------------ publicar en GitHub
def publicar(rama: str, archivos: dict[str, Path]) -> bool:
    """Sube los archivos a una rama huérfana de un solo commit (no hace crecer el repo)."""
    token, repo = os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_REPOSITORY")
    if not (token and repo):
        return False
    tmp = Path(f"/tmp/pub-{rama}")
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    for nombre, origen in archivos.items():
        if origen.exists():
            shutil.copy2(origen, tmp / nombre)
    url = f"https://x-access-token:{token}@github.com/{repo}.git"
    cmds = [
        ["git", "init", "-q", "-b", rama],
        ["git", "-c", "user.name=cazaofertas-bot", "-c", "user.email=bot@users.noreply.github.com",
         "commit", "-q", "--allow-empty", "-m", f"{rama} {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}"],
        ["git", "push", "-q", "-f", url, rama],
    ]
    try:
        subprocess.run(cmds[0], cwd=tmp, check=True)
        subprocess.run(["git", "add", "-A"], cwd=tmp, check=True)
        subprocess.run(cmds[1], cwd=tmp, check=True)
        subprocess.run(cmds[2], cwd=tmp, check=True, timeout=120, capture_output=True)
        return True
    except Exception as e:  # noqa: BLE001
        print("No se pudo publicar", rama, type(e).__name__)
        return False


# ------------------------------------------------------------------ un ciclo
def ciclo(recolectores: dict, estado: dict, catalogo: dict, sin_alertas: bool, segundos: float) -> dict:
    ahora = time.time()
    with ThreadPoolExecutor(max_workers=len(recolectores)) as ex:
        futuros = {t: ex.submit(r.ciclo, segundos) for t, r in recolectores.items()}
        resultados = {t: f.result() for t, f in futuros.items()}

    ahora = time.time()
    estado_tiendas = estado.setdefault("tiendas", {})
    vistos = set()
    for t, (prods, resumen) in resultados.items():
        for p in prods:
            datos.registrar(catalogo, p, ahora)
            vistos.add(p["id"])
        previo = estado_tiendas.get(t, {})
        resumen["ts"] = int(ahora)
        resumen["ultimo_ok"] = int(ahora) if resumen["ok"] else previo.get("ultimo_ok")
        resumen["barrido"] = estado.get("barridos", {}).get(t)
        estado_tiendas[t] = resumen
        print(f"  [{t}] {resumen['productos']} productos, {resumen.get('peticiones', 0)} pet., "
              f"{resumen['errores']} errores, faltan {resumen.get('pendientes_barrido', '?')} páginas del barrido")
        for e in resumen.get("detalle_errores", [])[-2:]:
            print("     !", e)

    vigentes = {k for k, v in catalogo.items() if v.get("ts", 0) >= ahora - config.HORAS_VIGENTE * 3600} | vistos
    cache = estado.setdefault("externo", {})
    externos = {k: v["r"] for k, v in cache.items() if v.get("r")}
    ofertas = detectar(catalogo, vigentes, ahora, externos)

    # Verificar en SoloTodo los candidatos más prometedores.
    cands = candidatos_externos(ofertas, cache, ahora, config.VERIFICACIONES_POR_CICLO)
    if cands:
        cli = _CLI_SOLOTODO.setdefault("c", Cliente("solotodo"))
        nuevos = 0
        for o in cands:
            r = externo.verificar(cli, o, cache, ahora)
            nuevos += bool(r)
        print(f"  SoloTodo: {len(cands)} consultados, {nuevos} encontrados")
        externos = {k: v["r"] for k, v in cache.items() if v.get("r")}
        ofertas = detectar(catalogo, vigentes, ahora, externos)
    externo.podar_cache(cache, ahora)

    # Lo que solo tiene el descuento "declarado" sin verificar: guardar solo los 300 mayores.
    principales = [o for o in ofertas if o["confianza"] in ("alta", "media")]
    falsos = [o for o in ofertas if o["confianza"] == "falso"][:150]
    declaradas = sorted((o for o in ofertas if o["confianza"] == "baja" and (o.get("precio_lista") or 0) >= 10_000),
                        key=lambda o: -(o.get("desc_declarado") or 0))[:300]
    ofertas = principales + declaradas + falsos

    desde = estado.setdefault("ofertas_desde", {})
    actuales = {o["id"] for o in ofertas}
    for o in ofertas:
        o["desde"] = desde.setdefault(o["id"], int(ahora))
        o["revisado"] = catalogo[o["id"]].get("ts", int(ahora))
    for k in [k for k in desde if k not in actuales and desde[k] < ahora - 3 * 86400]:
        del desde[k]

    enviados = 0 if sin_alertas else alertas.procesar(ofertas, estado, ahora)
    estado["alertas_total"] = estado.get("alertas_total", 0) + enviados

    SITIO_DATA.mkdir(parents=True, exist_ok=True)
    por_tienda = {}
    for v in catalogo.values():
        por_tienda[v["t"]] = por_tienda.get(v["t"], 0) + 1
    (SITIO_DATA / "ofertas.json").write_text(json.dumps({
        "generado": int(ahora), "umbral": config.UMBRAL_DESCUENTO, "ofertas": ofertas,
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (SITIO_DATA / "estado.json").write_text(json.dumps({
        "generado": int(ahora),
        "ciclo": estado.get("corrida", 0),
        "catalogo": len(catalogo),
        "por_tienda": por_tienda,
        "tiendas": estado_tiendas,
        "alertas_enviadas": estado.get("alertas_total", 0),
        "canal_alertas": alertas.hay_canal(),
        "verificados_solotodo": len(externos),
        "segundos_por_ciclo": config.SEGUNDOS_POR_CICLO,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    n_conf = len(principales)
    print(f"  → {n_conf} posibles errores ({sum(o['confianza'] == 'alta' for o in principales)} alta), "
          f"{len(falsos)} descuentos falsos, alertas: {enviados}, catálogo {len(catalogo)}")
    return {"ofertas": n_conf}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutos", type=float, default=0, help="duración del bucle continuo")
    ap.add_argument("--ciclos", type=int, default=0, help="cantidad fija de ciclos")
    ap.add_argument("--segundos", type=float, default=config.SEGUNDOS_POR_CICLO)
    ap.add_argument("--sin-alertas", action="store_true")
    ap.add_argument("--solo", choices=TIENDAS)
    args = ap.parse_args()

    inicio = time.time()
    fin = inicio + args.minutos * 60 if args.minutos else None
    max_ciclos = args.ciclos or (10**9 if fin else 1)

    estado = datos.cargar_estado()
    catalogo = datos.cargar_catalogo()
    estado.pop("ofertas_previas", None)
    print(f"Inicio — catálogo con {len(catalogo)} productos")
    recolectores = {t: Recolector(t, estado) for t in ([args.solo] if args.solo else TIENDAS)}
    ultimo_respaldo = time.time()
    n = 0
    while n < max_ciclos:
        if fin and time.time() + args.segundos + 60 > fin:
            break
        n += 1
        estado["corrida"] = estado.get("corrida", 0) + 1
        print(f"Ciclo {n} (#{estado['corrida']})")
        try:
            ciclo(recolectores, estado, catalogo, args.sin_alertas, args.segundos)
        except Exception:  # noqa: BLE001
            traceback.print_exc()
        publicar("web-datos", {"ofertas.json": SITIO_DATA / "ofertas.json",
                               "estado.json": SITIO_DATA / "estado.json"})
        if time.time() - ultimo_respaldo > config.MINUTOS_RESPALDO * 60:
            respaldar(catalogo, estado)
            ultimo_respaldo = time.time()
    respaldar(catalogo, estado)
    print(f"Fin tras {n} ciclos en {round((time.time() - inicio) / 60)} min")


def respaldar(catalogo: dict, estado: dict) -> None:
    datos.podar(catalogo, time.time())
    datos.guardar_catalogo(catalogo)
    datos.guardar_estado(estado)
    publicar("datos", {"catalogo.json.gz": datos.CATALOGO, "estado.json": datos.ESTADO,
                       "sitio-ofertas.json": SITIO_DATA / "ofertas.json",
                       "sitio-estado.json": SITIO_DATA / "estado.json"})


if __name__ == "__main__":
    main()
