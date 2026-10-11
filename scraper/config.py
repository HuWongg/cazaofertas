"""Configuración general de Cazaofertas.

Para agregar o quitar categorías, edita las listas de abajo.
"""

# ---------------------------------------------------------------- Umbrales
# Descuento mínimo (0.5 = 50%) para que algo cuente como oferta.
UMBRAL_DESCUENTO = 0.50

# Descuento mínimo para mandar alerta al celular (más estricto para no spamear).
UMBRAL_ALERTA = 0.55

# No alertar productos cuyo precio de referencia sea menor a esto (CLP).
REFERENCIA_MINIMA_ALERTA = 15_000

# Máximo de alertas por ejecución.
MAX_ALERTAS_POR_CORRIDA = 8

# Días de historial que se guardan por producto.
DIAS_HISTORIAL = 45

# Días mínimos de historial antes de comparar contra el propio historial.
DIAS_MINIMOS_HISTORIAL = 3

# Un precio visto hace más de esto ya no sirve para comparar entre tiendas.
HORAS_VIGENCIA_PRECIO = 72

# Tiempo máximo por tienda en cada ejecución (segundos).
PRESUPUESTO_SEGUNDOS_POR_TIENDA = 6 * 60

# Pausa entre peticiones a una misma tienda (segundos, se agrega azar).
PAUSA_ENTRE_PETICIONES = 1.2

# Páginas "fijas" que se revisan siempre por categoría (las primeras),
# más algunas páginas profundas que van rotando en cada ejecución.
PAGINAS_FIJAS = 2
PAGINAS_ROTATIVAS = 2

# ---------------------------------------------------------------- Falabella
# (id de categoría, nombre en la URL, páginas máximas a recorrer)
FALABELLA_CATEGORIAS = [
    ("cat70057", "Notebooks", 20),
    ("cat720161", "Smartphones", 20),
    ("cat7190148", "Smart-TV", 12),
    ("cat2062", "Monitores", 10),
    ("cat7230007", "Tablets", 8),
    ("cat1640002", "Audifonos", 20),
    ("cat3171", "Parlantes-bluetooth", 8),
    ("cat2045", "Soundbar-y-Home-Theater", 5),
    ("cat202303", "Consolas", 6),
    ("cat4440005", "Playstation", 8),
    ("cat70003", "Nintendo", 8),
    ("cat4290063", "SmartWatch", 10),
    ("cat13520029", "Componentes-gamer", 8),
    ("cat2003", "Almacenamiento", 8),
    ("cat2049", "Impresoras-y-Tintas", 6),
    ("cat2038", "Fotografia", 6),
    ("cat7230062", "Drones", 3),
    ("cat8600022", "Aspiradoras-Robot", 5),
    ("cat3205", "Refrigeradores", 8),
    ("cat4060", "Lavadoras", 6),
    ("cat3099", "Freidoras", 6),
    ("cat2019", "Aire-Acondicionado", 4),
    ("cat850064", "Zapatillas-Hombre", 30),
    ("cat850068", "Zapatillas-Mujer", 30),
    ("cat6930003", "Ropa-deportiva-hombre", 15),
    ("cat6930168", "Ropa-deportiva-mujer", 15),
    ("cat70007", "Bicicletas", 6),
    ("cat2069", "Perfumes", 15),
    ("cat2020", "Colchones", 6),
    ("cat3208", "Relojes", 10),
]

# ---------------------------------------------------------------- Ripley
# (ruta, páginas máximas)
RIPLEY_CATEGORIAS = [
    ("/tecno/computacion/notebooks", 16),
    ("/tecno/computacion/tablets", 5),
    ("/tecno/computacion/monitores", 8),
    ("/tecno/celulares", 30),
    ("/tecno/television", 20),
    ("/tecno/audio-y-musica", 30),
    ("/tecno/playstation", 15),
    ("/tecno/nintendo", 15),
    ("/tecno/xbox", 4),
    ("/electro/refrigeracion", 8),
    ("/electro/electrodomesticos", 20),
    ("/electro/climatizacion", 10),
    ("/zapatos-y-zapatillas/zapatillas", 40),
    ("/deporte-y-aventura", 30),
]

# ---------------------------------------------------------------- Paris
# Paris solo entrega la primera página (30 productos) sin JavaScript,
# por eso usamos muchas subcategorías chicas.
PARIS_CATEGORIAS = [
    "/tecnologia/computadores/notebooks/",
    "/tecnologia/computadores/pc-gamer/",
    "/tecnologia/computadores/desktop-all-in-one/",
    "/tecnologia/computadores/ipad-tablet/",
    "/tecnologia/celulares/smartphone/",
    "/tecnologia/celulares/iphone/",
    "/tecnologia/celulares/samsung/",
    "/tecnologia/celulares/xiaomi/",
    "/tecnologia/celulares/motorola/",
    "/tecnologia/celulares/reacondicionados/",
    "/tecnologia/wearables/smartwatches/",
    "/tecnologia/wearables/audifonos-inalambricos/",
    "/tecnologia/consolas-videojuegos/consolas-playstation/",
    "/tecnologia/consolas-videojuegos/consolas-nintendo/",
    "/tecnologia/consolas-videojuegos/consolas-xbox/",
    "/tecnologia/consolas-videojuegos/juegos/",
    "/tecnologia/consolas-videojuegos/accesorios/",
    "/tecnologia/accesorios-computacion/monitor-gamer/",
    "/tecnologia/accesorios-computacion/disco-duro/",
    "/tecnologia/accesorios-computacion/proyectores/",
    "/tecnologia/accesorios-computacion/mouse-teclados/",
    "/tecnologia/fotografia/drones/",
    "/tecnologia/fotografia/camaras-deportivas/",
    "/tecnologia/gamers/headset/",
    "/tecnologia/gamers/sillas-escritorios-gamer/",
    "/tecnologia/smart-home/mundo-robot/",
    "/tecnologia/impresoras/",
    "/electro/television/smart-tv/",
    "/electro/elige-tu-pulgada/55-a-60-pulgadas/",
    "/electro/elige-tu-pulgada/60-a-70-pulgadas/",
    "/electro/elige-tu-pulgada/70-o-mas-pulgadas/",
    "/electro/television/soundbar-home-theater/",
    "/electro/audio/parlantes-bluetooth-portables/",
    "/electro/audio/audifonos/",
    "/linea-blanca/refrigeracion/refrigeradores/",
    "/linea-blanca/refrigeracion/side-by-side/",
    "/linea-blanca/lavado-secado/todas/",
    "/linea-blanca/electrodomesticos/freidoras-de-aire/",
    "/linea-blanca/electrodomesticos/cafeteras/",
    "/linea-blanca/electrodomesticos/microondas/",
    "/linea-blanca/aspirado-limpieza/aspiradoras-robot/",
    "/linea-blanca/aspirado-limpieza/aspiradoras-verticales/",
    "/linea-blanca/climatizacion/split/",
    "/deportes/zapatillas/running/",
    "/deportes/zapatillas/urbanas/",
    "/deportes/zapatillas/hombres/",
    "/deportes/zapatillas/mujer/",
    "/deportes/marcas/nike/",
    "/deportes/marcas/adidas/",
    "/deportes/marcas/puma/",
    "/deportes/ofertas/zapatillas/",
    "/deportes/bicicletas/mountain-bike/",
    "/deportes/fitness/trotadoras/",
    "/deportes/movilidad-electrica/scooters-electricos/",
    "/hombre/zapatos/zapatillas/",
    "/mujer/zapatos/zapatillas/",
    "/belleza/perfumes/mujer/",
    "/belleza/perfumes/hombre/",
    "/dormitorio/colchones/2-plazas/",
    "/dormitorio/colchones/king/",
]

# Cuántas categorías de Paris se revisan por ejecución (van rotando).
PARIS_CATEGORIAS_POR_CORRIDA = 30
