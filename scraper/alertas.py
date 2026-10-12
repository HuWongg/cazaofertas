"""Alertas al celular: WhatsApp (CallMeBot) y/o Telegram.

Se configuran con "secrets" del repositorio en GitHub (Settings → Secrets → Actions):
  WhatsApp: CALLMEBOT_PHONE (ej. 56912345678) y CALLMEBOT_APIKEY
  Telegram: TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID
Si no están configurados, simplemente no se envía nada.
"""
from __future__ import annotations

import os
import time
import urllib.parse

from curl_cffi import requests as creq

from . import config

NOMBRES = {"falabella": "Falabella", "ripley": "Ripley", "paris": "Paris"}


def _clp(n) -> str:
    return "$" + f"{int(n):,}".replace(",", ".")


def texto(o: dict, sitio: str | None) -> str:
    marca = "🚨 POSIBLE ERROR DE PRECIO" if o["confianza"] == "alta" else "🔥 Posible error"
    lineas = [f"{marca}: -{round(o['descuento'] * 100)}% en {NOMBRES.get(o['tienda'], o['tienda'])}",
              o["nombre"][:110],
              f"Ahora: {_clp(o['precio'])}"]
    if o.get("ref_cruzada") and "entre_tiendas" in o["tipos"]:
        otra = o["comparados"][0] if o["comparados"] else None
        extra = f" (ej. {NOMBRES.get(otra['tienda'], otra['tienda'])} {_clp(otra['precio'])})" if otra else ""
        lineas.append(f"En otras publicaciones: {_clp(o['ref_cruzada'])}{extra}")
    if o.get("precio_anterior") and "caida" in o["tipos"]:
        lineas.append(f"Hace poco costaba: {_clp(o['precio_anterior'])}")
    if o.get("ref_historial") and "historial" in o["tipos"]:
        lineas.append(f"Su precio habitual: {_clp(o['ref_historial'])}")
    ext = o.get("externo") or {}
    if ext.get("ref_tiendas"):
        t0 = ext["otras"][0]["tienda"] if ext.get("otras") else ""
        lineas.append(f"SoloTodo: otras tiendas desde {_clp(ext['ref_tiendas'])} ({t0})")
    if ext.get("ref_historial"):
        lineas.append(f"SoloTodo: precio habitual {_clp(ext['ref_historial'])}")
    lineas.append(o["url"])
    if sitio:
        lineas.append(f"Panel: {sitio}")
    return "\n".join(lineas)


def _whatsapp(msg: str) -> bool:
    tel, key = os.environ.get("CALLMEBOT_PHONE"), os.environ.get("CALLMEBOT_APIKEY")
    if not (tel and key):
        return False
    url = ("https://api.callmebot.com/whatsapp.php?phone=" + urllib.parse.quote(tel)
           + "&text=" + urllib.parse.quote(msg) + "&apikey=" + urllib.parse.quote(key))
    try:
        r = creq.get(url, timeout=30)
        return r.status_code == 200
    except Exception as e:  # noqa: BLE001
        print("WhatsApp falló:", e)
        return False


def _telegram(msg: str) -> bool:
    tok, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not (tok and chat):
        return False
    try:
        r = creq.post(f"https://api.telegram.org/bot{tok}/sendMessage",
                      json={"chat_id": chat, "text": msg, "disable_web_page_preview": False}, timeout=30)
        return r.status_code == 200
    except Exception as e:  # noqa: BLE001
        print("Telegram falló:", e)
        return False


def hay_canal() -> bool:
    return bool((os.environ.get("CALLMEBOT_PHONE") and os.environ.get("CALLMEBOT_APIKEY"))
                or (os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID")))


def enviar(msg: str) -> bool:
    ok_w = _whatsapp(msg)
    ok_t = _telegram(msg)
    return ok_w or ok_t


def procesar(ofertas: list[dict], estado: dict, ahora: float) -> int:
    """Envía alertas nuevas. Recuerda lo enviado para no repetir."""
    enviados = estado.setdefault("alertados", {})
    # Olvidar alertas de hace más de 7 días.
    for k in [k for k, v in enviados.items() if v.get("ts", 0) < ahora - 7 * 86400]:
        del enviados[k]
    if not hay_canal():
        return 0
    sitio = os.environ.get("SITIO_URL")
    n = 0
    for o in ofertas:
        if n >= config.MAX_ALERTAS_POR_CORRIDA:
            break
        if o["confianza"] not in ("alta", "media") or o["descuento"] < config.UMBRAL_ALERTA:
            continue
        ext = o.get("externo") or {}
        ref = max(o.get("ref_cruzada") or 0, o.get("ref_historial") or 0, o.get("precio_anterior") or 0,
                  ext.get("ref_tiendas") or 0, ext.get("ref_historial") or 0)
        if ref < config.REFERENCIA_MINIMA_ALERTA:
            continue
        previo = enviados.get(o["id"])
        if previo and o["precio"] > previo["precio"] * 0.9:
            continue
        if enviar(texto(o, sitio)):
            enviados[o["id"]] = {"ts": int(ahora), "precio": o["precio"]}
            n += 1
            time.sleep(3)  # CallMeBot pide no enviar muy seguido
    return n
