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
# Departamentos del buscador de Paris: (id de grupo, páginas máximas de 100 productos).
PARIS_DEPARTAMENTOS = [
    ("tecnologia", 40),
    ("electro", 15),
    ("lineablanca", 15),
    ("zapatos", 40),
    ("deportes", 40),
    ("belleza", 20),
    ("dormitorio", 15),
    ("muebles", 10),
    ("jugueteria", 10),
]

# Páginas ordenadas por "mejor descuento" que se revisan siempre en cada departamento.
PARIS_PAGINAS_DESCUENTO = 3
