# canales.sh — mapa único canal → handle idioma ruta_nicho (fuente verdad para batch + radar)
#
# DEMO CHANNELS — estos son para probar. El buyer reemplaza con sus propios canales.
# Formato: [canal]=" handle idioma ruta_nicho/"
# Idioma: es (castellano) o en (inglés)
# Ruta_nicho: carpeta donde se guardarán los .md (ej: 01-ia-agentes/mi-canal)
#
# Shorts, videos privados y de miembros no se descargan (razones obvias de YouTube).

declare -A CANALES=(
  # DEMO: canales de ejemplo para probar el radar
  [mouredev]=" @mouredev es 02-programacion/mouredev"
  [atareao]=" @atareao es 03-linux-infra/atareao"
  [nichonauta]=" @nichonauta es 01-ia-agentes/nichonauta"
  #
  # AÑADIR TUS CANALES AQUÍ:
  # [mi-canal]=" @handle es 01-ia-agentes/mi-canal"
  # [otro-canal]=" @handle en 02-programacion/otro-canal"
)

# Orden de pasada para el radar (uno por canal, uno por video)
CANAL_ORDEN=(mouredev atareao nichonauta)
