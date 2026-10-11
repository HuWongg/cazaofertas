# 🎯 Cazaofertas

Panel personal que revisa **Falabella, Ripley y Paris** cada hora y muestra productos con **≥50% de descuento real**:

- **Entre tiendas**: el mismo producto (mismo código de modelo, o misma marca y nombre) cuesta al menos el doble en **todas** las demás publicaciones (se compara contra la más barata de ellas, y se descartan variantes distintas como 128GB vs 256GB o 55" vs 65").
- **Bajo su historial**: cuesta al menos 50% menos que su precio habitual de días anteriores.
- **Según la tienda**: solo el "precio normal" tachado que anuncia la tienda (apagado por defecto, es el menos confiable).

Todo corre gratis en GitHub: **GitHub Actions** recolecta los precios y **GitHub Pages** publica la web.

## Cómo está armado

| Carpeta / archivo | Qué hace |
|---|---|
| `scraper/tiendas/` | Lectores de cada tienda (Falabella, Ripley, Paris) |
| `scraper/matching.py` | Reconoce el mismo producto en distintas publicaciones |
| `scraper/detectar.py` | Calcula descuentos y la confianza de cada oferta |
| `scraper/alertas.py` | Avisos por WhatsApp (CallMeBot) y/o Telegram |
| `scraper/config.py` | **Umbrales y categorías**: edítalo para ajustar |
| `web/` | La página (HTML/CSS/JS sin dependencias) |
| `.github/workflows/cazar.yml` | Ejecución automática cada hora |
| rama `datos` | Historial de precios (se reescribe en cada corrida) |

## Alertas al celular

En GitHub: **Settings → Secrets and variables → Actions → New repository secret**.

**WhatsApp (CallMeBot)**
1. Agrega el número de CallMeBot a tus contactos y mándale *"I allow callmebot to send me messages"* (instrucciones: https://www.callmebot.com/blog/free-api-whatsapp-messages/).
2. Te responde con tu `apikey`.
3. Crea los secrets `CALLMEBOT_PHONE` (ej. `56912345678`, sin `+`) y `CALLMEBOT_APIKEY`.

**Telegram (respaldo)**
1. Habla con @BotFather → `/newbot` → copia el token.
2. Escríbele cualquier cosa a tu bot y abre `https://api.telegram.org/bot<TOKEN>/getUpdates` para ver tu `chat.id`.
3. Crea los secrets `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`.

## Probar en tu PC (opcional)

```bash
pip install -r requirements.txt
python run.py --solo ripley --rapido --sin-alertas
python tests/test_basico.py
```

## Límites conocidos

- **Mercado Libre** pide iniciar sesión para ver listados y su API pública responde "prohibido", así que no está incluido.
- **Ripley** y **Paris** bloquean servidores fuera de Chile, así que se leen desde los mismos servicios que usan sus webs (la API de catálogo de Ripley y el buscador de Paris).
- Las tiendas cambian sus sitios: si una deja de funcionar, el panel lo muestra en el estado de arriba.
- Un error de precio no garantiza la compra: las tiendas a veces anulan esos pedidos.
