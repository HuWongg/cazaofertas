"""Cliente HTTP que se presenta como un navegador Chrome real.

Usa curl_cffi (imita la huella TLS de Chrome), que es lo que más ayuda
a no ser bloqueado por los sistemas anti-bots de las tiendas.
"""
from __future__ import annotations

import random
import time

from curl_cffi import requests as creq

from . import config

HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-CL,es;q=0.9,en;q=0.7",
    "Cache-Control": "no-cache",
}


IDENTIDADES = ["chrome", "safari", "firefox", "edge", "chrome_android"]


class Bloqueado(Exception):
    """La tienda respondió con un bloqueo o una página que no es de productos."""


class Cliente:
    def __init__(self, nombre: str):
        self.nombre = nombre
        self.s = creq.Session(impersonate="chrome", headers=HEADERS, timeout=40)
        self._ultimo = 0.0
        self.peticiones = 0
        self.errores = 0

    def _pausa(self) -> None:
        espera = config.PAUSA_ENTRE_PETICIONES + random.uniform(0, 0.8)
        falta = self._ultimo + espera - time.time()
        if falta > 0:
            time.sleep(falta)

    def _rotar_identidad(self) -> None:
        """Cambia la huella de navegador (y reinicia cookies) tras un bloqueo."""
        self._idx = (getattr(self, "_idx", 0) + 1) % len(IDENTIDADES)
        self.s = creq.Session(impersonate=IDENTIDADES[self._idx], headers=HEADERS, timeout=40)

    def get(self, url: str, intentos: int = 3) -> str:
        ultimo_error: Exception | None = None
        for n in range(intentos):
            self._pausa()
            self._ultimo = time.time()
            self.peticiones += 1
            try:
                r = self.s.get(url, allow_redirects=True)
                if r.status_code in (403, 429, 503):
                    srv = r.headers.get("server", "?")
                    ultimo_error = Bloqueado(f"HTTP {r.status_code} ({srv}) en {url}")
                    self._rotar_identidad()
                    time.sleep(4 * (n + 1))
                    continue
                if r.status_code == 404:
                    raise Bloqueado(f"HTTP 404 en {url}")
                r.raise_for_status()
                return r.text
            except Bloqueado:
                raise
            except Exception as e:  # red, timeout, etc.
                ultimo_error = e
                time.sleep(2 * (n + 1))
        self.errores += 1
        raise ultimo_error or RuntimeError(f"Falló {url}")
