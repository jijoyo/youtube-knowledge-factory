# YouTube Knowledge Factory — Radar Secuencial
#
# Este radar captura subtítulos de canales de YouTube uno por uno.
# Incluye anti-baneo: sleeps, disyuntor x3, lock, blocklist con causa.
#
# Para usar: bash yt-radar.sh [canal] [--all]
# Shorts, videos privados y de miembros no se descargan.
#!/bin/bash
# v3.3 STEALTH - no pega si IP quemada, usa pausa + proxy + cookies
export PATH="$HOME/.local/deno/bin:$PATH"
set -e
SCRIPT_DIR="$(dirname "$(realpath "$0")")"
source "$SCRIPT_DIR/../lib/canales.sh"
BASE="$HOME/youtube-knowledge/knowledge/videos"
INDEX="$HOME/youtube-knowledge/knowledge/index.json"
ARCHIVE="$HOME/.cache/yt-archive.txt"
mkdir -p "$BASE" "$(dirname "$ARCHIVE")" "$(dirname "$INDEX")"
touch "$ARCHIVE"
[ -f "$INDEX" ] || echo "{}" > "$INDEX"
shopt -s nullglob

# candado: un solo radar a la vez (si ya hay uno, el segundo sale sin duplicar trabajo ni doblar el rate-limit)
exec 9>/tmp/yt-radar.lock
flock -n 9 || { echo "⏸ Ya hay un radar corriendo. Salgo sin duplicar."; exit 0; }

MODE="new"; [[ "$*" == *"--all"* ]] && MODE="all"
TARGET=""; for arg in "$@"; do [[ "$arg" != "--all" ]] && TARGET="$arg"; done

# STEALTH CONFIG - editar si hace falta
PROXY="${YT_RADAR_PROXY:-}" # ej: socks5://127.0.0.1:9050  o  http://127.0.0.1:8080
USE_COOKIES="${YT_RADAR_COOKIES:-auto}" # auto, chrome, firefox, no
COOKIES_FILE="${YT_RADAR_COOKIES_FILE:-$HOME/.cache/yt-cookies/youtube.txt}" # archivo Netscape, gana a browser
FORCE_IPV4="${YT_RADAR_IPV4:-yes}" # yes = --force-ipv4 (IPv6 roto cuelga Downloading webpage)
CLIENTS="android,web" # fallback clients
LOTE="${YT_RADAR_LOTE:-30}" # tope de videos NUEVOS por canal y pasada (0 = sin tope); round-robin diario
TABS="videos streams" # pestañas unificadas en una sola lista (dedupe por ID); shorts fuera por diseño

CANAL_ORDEN=(edteam emprende-aprendiendo atareao adrian-saenz mouredev codacus bettatech alejavi-rivera gentleman-programming verabadias romuald-fons martin-toledo ray-codes nichonauta mitormento andrea-paulin denoise-ai comfyui-workflows cintika oneman-nerdy jokioki ivandm torticode pixaroma academia-sd holamundo frizzy)

get_args() {
  local a="--js-runtimes deno --no-warnings --ignore-errors --extractor-args youtube:player_client=android,web --no-check-formats"
  [ "$FORCE_IPV4" = "yes" ] && a="$a --force-ipv4"
  [ -n "$PROXY" ] && a="$a --proxy $PROXY"
  if [ -f "$COOKIES_FILE" ]; then
    a="$a --cookies $COOKIES_FILE"
  elif [ "$USE_COOKIES" = "auto" ]; then
    if [ -d "$HOME/.config/google-chrome" ] || [ -d "$HOME/.mozilla" ]; then
      a="$a --cookies-from-browser chrome" 2>/dev/null || a="$a --cookies-from-browser firefox" 2>/dev/null || true
    fi
  elif [ "$USE_COOKIES" != "no" ]; then
    a="$a --cookies-from-browser $USE_COOKIES"
  fi
  echo "$a"
}

get_total() {
  local h=$1
  local args=$(get_args)
  local ids=""
  for _t in $TABS; do
    # shellcheck disable=SC2086
    ids="$ids $(timeout 35 yt-dlp $args --flat-playlist --print id "https://www.youtube.com/$h/$_t" 2>/dev/null || true)"
  done
  echo "$ids" | tr ' ' '\n' | grep -c . || echo 0
}

cuenta_ids() { # $1=dir -> nº de videoIDs únicos en .md (igual que el dashboard)
  ls -1 "$1"/*.md 2>/dev/null | grep -oP '\[\K[a-zA-Z0-9_-]{11}(?=\])' | sort -u | wc -l
}

convierte_pendientes() { # $1=dir $2=canal [$3=solo este id] -> .srt a .md con cabecera del filename, al instante
  local _o=$1 _c=$2 _f=${3:-} _srt _md _fn _id _dt _ti _tmp
  for _srt in "$_o"/*.srt; do
    [ -e "$_srt" ] || return 0
    if [ -n "$_f" ]; then case "$_srt" in *"[$_f]"*) ;; *) continue ;; esac; fi
    _md="${_srt%.srt}.md"; [ -f "$_md" ] && { rm -f "$_srt"; continue; }
    if ! head -1 "$_srt" | grep -q "^# TITLE:"; then
      _fn=$(basename "$_srt")
      _id=$(echo "$_fn" | sed -n 's/.*\[\(.\{11\}\)\].*/\1/p' | tail -1)
      _dt=$(echo "$_fn" | cut -d' ' -f1); [[ "$_dt" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || _dt=""
      _ti=$(echo "$_fn" | sed 's/^....-..-.. - //; s/ \[[^]]*\]\..*//')
      _tmp=$(mktemp); { echo "# TITLE: $_ti"; echo "# CHANNEL: ($_c)"; echo "# DATE: $_dt"; echo "# URL: https://www.youtube.com/watch?v=$_id"; echo "# THUMBNAIL: https://i.ytimg.com/vi/$_id/hqdefault.jpg"; echo "# DESC: "; echo ""; cat "$_srt"; } > "$_tmp" && mv "$_tmp" "$_srt"
    fi
    python3 "$SCRIPT_DIR/srt2md.py" "$_srt" "$_md" >/dev/null 2>&1 && rm -f "$_srt" || true
  done
}

radar_canal() {
  local canal=$1; local modo=${2:-$MODE}
  local info="${CANALES[$canal]}"; [ -z "$info" ] && return 1
  local handle=$(echo "$info" | awk '{print $1}')
  local lang=$(echo "$info" | awk '{print $2}')
  local subpath=$(echo "$info" | awk '{print $3}')
  local out="$BASE/$subpath"; mkdir -p "$out"
  convierte_pendientes "$out" "$canal"  # barrido: .srt huérfanos de corridas cortadas -> .md (resume limpio)
  local yt_idx=$(python3 -c "import json; print(json.load(open('$INDEX')).get('$canal',{}).get('youtube',0))" 2>/dev/null || echo 0)
  local total=$(get_total "$handle")
  echo "▶ $canal [$handle] IP check: yt=$total idx=$yt_idx"
  _estado() { echo "{\"canal\": \"$canal\", \"fase\": \"$1\", \"item\": $2, \"total\": $3, \"detalle\": \"$4\", \"hora\": \"$(date '+%R')\", \"ts\": $(date +%s)}" > /tmp/yt-estado.json; }
  _estado "revisando" 0 "$total" "flat $handle"
  if [ "$total" -eq 0 ]; then
    echo "  ⏸ IP aun marcada (flat 0). No pego, dejo $yt_idx/$yt_idx. Pausa 12-24h recomendada."
    return 0
  fi
  # resto igual que v3.2
  local local_idx=$(python3 -c "import json; print(json.load(open('$INDEX')).get('$canal',{}).get('local',0))" 2>/dev/null || echo 0)
  local real=$(cuenta_ids "$out")
  if [ "$modo" != "all" ] && [ "$real" -ge "$total" ] && [ "$total" -gt 0 ]; then
    echo "  ✓ Sin novedades ($real/$total)"
    _estado "terminado" "$real" "$total" "$canal sin novedades"
    python3 "$SCRIPT_DIR/../lib/update_index.py" "$canal" "$real" "$total"
    return 0
  fi
  if [ "$modo" = "all" ] && [ "$real" -ge "$total" ] && [ "$total" -gt 0 ]; then
    echo "  ✓ Completo ($real/$total)"
    _estado "terminado" "$real" "$total" "$canal completo"
    python3 "$SCRIPT_DIR/../lib/update_index.py" "$canal" "$real" "$total"
    return 0
  fi
  # (filtro de modo para el flat: se aplica abajo como flat_extra)
  local args=$(get_args)

  # --- LISTA: solo lo que falta (flat IDs videos+streams - .md - bloqueados) ---
  flat_extra=""; [ "$modo" != "all" ] && flat_extra="--dateafter now-14days --playlist-end 50"
  all_ids=""
  for _t in $TABS; do
    # shellcheck disable=SC2086
    set +e; _fo=$(timeout 60 yt-dlp $args --flat-playlist --print id $flat_extra "https://www.youtube.com/$handle/$_t" 2>/dev/null); _frc=$?; set -e
    if [ $_frc -eq 124 ]; then echo "  👁 CIEGO flat $canal/$_t (timeout 60s, no es 0)" | tee -a "/tmp/radar-$canal.log"; continue; fi
    if [ $_frc -ne 0 ]; then echo "  ⚠ flat $canal/$_t falló (rc=$_frc), sigo con lo que haya" | tee -a "/tmp/radar-$canal.log"; continue; fi
    all_ids="$all_ids $_fo"
  done
  all_ids=$(echo "$all_ids" | tr ' ' '\n' | grep . | sort -u)
  [ -z "$all_ids" ] && all_ids=""

  existing_ids=$(ls -1 "$out"/*.md 2>/dev/null | grep -oP '\[\K[a-zA-Z0-9_-]{11}(?=\])' | sort -u)
  BLOCKLIST="$HOME/.cache/yt-bloqueados.txt"
  touch "$BLOCKLIST"
  faltan=""
  missing=0
  skipped=0
  while IFS= read -r id; do
    [ -z "$id" ] && continue
    if ! echo "$existing_ids" | grep -qx -e "$id"; then
      if awk -v id="$id" -v lim="$(date -d '30 days ago' +%F)" '$1==id{if($0~/members-only|Private video|unavailable/){perm=1; exit} if($2>=lim){found=1; exit}} END{exit !(found||perm)}' "$BLOCKLIST" 2>/dev/null; then
        skipped=$((skipped + 1))
        continue
      fi
      faltan="$faltan $id"
      missing=$((missing + 1))
    fi
  done <<< "$all_ids"

  if [ "$missing" -eq 0 ]; then
    echo "  ✓ Sin novedades ($real/$total)"
    _estado "terminado" "$real" "$total" "$canal sin novedades"
    python3 "$SCRIPT_DIR/../lib/update_index.py" "$canal" "$real" "$total"
    return 0
  fi

  # --- PUERTA IDIOMA: canal nuevo (0 .md) -> 1 video test, propuesta, sin backfill ---
  if [ "$real" -eq 0 ] && [ ! -f "/tmp/yt-idioma-$canal.json" ]; then
    _tid=$(echo "$faltan" | awk '{print $1}')
    _otro="es"; [ "$lang" = "es" ] && _otro="en"
    # shellcheck disable=SC2086
    timeout 120 yt-dlp $args --download-archive "$ARCHIVE" --write-sub --write-auto-sub --sub-langs "$lang,$_otro" --convert-subs srt --skip-download --sleep-interval 2 --max-sleep-interval 5 -o "$out/%(upload_date>%Y-%m-%d)s - %(title)s [%(id)s].%(ext)s" "https://www.youtube.com/watch?v=$_tid" 2>/dev/null || true
    _hay_mapa=$(ls -1 "$out" 2>/dev/null | grep -cF -e "[$_tid].$lang.srt" || true)
    _hay_otro=$(ls -1 "$out" 2>/dev/null | grep -cF -e "[$_tid].$_otro.srt" || true)
    if [ "$_hay_mapa" -gt 0 ]; then _prop="$lang"; elif [ "$_hay_otro" -gt 0 ]; then _prop="$_otro"; else _prop="?"; fi
    echo "{\"mapa\": \"$lang\", \"propuesta\": \"$_prop\", \"video\": \"$_tid\", \"fecha\": \"$(date '+%F %R')\"}" > "/tmp/yt-idioma-$canal.json"
    echo "  ⏸ $canal NUEVO: 1 video test, propongo $_prop (mapa $lang) — confirma idioma antes del backfill"
    echo "# IDIOMA propuesta=$_prop mapa=$lang" >> "/tmp/radar-$canal.log"
    convierte_pendientes "$out" "$canal" "$_tid"
    python3 "$SCRIPT_DIR/../lib/update_index.py" "$canal" "$(cuenta_ids "$out")" "$total"
    return 0
  fi

  # --- UNO POR UNO: lento pero seguro, contador en vivo, resume ante cortes ---
  echo "  📥 Uno por uno: $missing/$total videos"
  echo "# BATCH total=$missing" >> "/tmp/radar-$canal.log"
  _hoy=$(date +%F)
  _n=0
  _ok=0
  _rl=0
  for _id in $faltan; do
    _n=$((_n + 1))
    _estado "descargando" "$_n" "$missing" "$_id"
    _out=$(timeout 120 yt-dlp $args --download-archive "$ARCHIVE" --write-sub --write-auto-sub --sub-lang "$lang" --convert-subs srt --skip-download --sleep-interval 2 --max-sleep-interval 5 -o "$out/%(upload_date>%Y-%m-%d)s - %(title)s [%(id)s].%(ext)s" "https://www.youtube.com/watch?v=$_id" 2>&1 || true)
    echo "$_out" >> "/tmp/radar-$canal.log"
    echo "$_out" >> "/tmp/yt-radar.log"
    convierte_pendientes "$out" "$canal" "$_id"
    # cuerpos vacíos ([Music]/silencio): el .md no cuenta y va a causa fina
    _vacio=0
    for _mdv in "$out"/*"[$_id]".*.md; do
      [ -e "$_mdv" ] || break
      if [ "$(awk '/^---$/{f++} f>=2' "$_mdv" | grep -vE '^[#>|![]' | wc -w)" -lt 15 ]; then
        rm -f "$_mdv" "$out"/*"[$_id]".*.srt; _vacio=1
      fi
    done
    if ls -1 "$out"/*.md 2>/dev/null | grep -qF -e "[$_id]"; then
      echo "  [$_n/$missing] $_id ✓"
      _estado "listo" "$_n" "$missing" "$_id ✓"
      _rl=0
      _ok=$((_ok + 1))
      python3 "$SCRIPT_DIR/../lib/update_index.py" "$canal" "$(cuenta_ids "$out")" "$total"
      if [ "$LOTE" -gt 0 ] && [ "$_ok" -ge "$LOTE" ]; then
        echo "  🧺 Lote completo ($_ok/$LOTE nuevos): $canal sigue mañana"
        echo "# LOTE $_ok/$LOTE" >> "/tmp/radar-$canal.log"
        break
      fi
    else
      if [ "$_vacio" -eq 1 ]; then _cause="subs-vacios"
      else _cause=$(echo "$_out" | grep -oE "no subtitles|Private video|unavailable|members-only|confirm your age|Sign in|has no automatic captions|rate-limited" | head -1); fi
      [ -z "$_cause" ] && _cause="sin-md"
      # rate-limited no se archiva: es transitorio (horas), reintenta en la próxima corrida
      if [ "$_cause" != "rate-limited" ]; then grep -q -e "^$_id " "$BLOCKLIST" || echo "$_id $_hoy # $canal ${_cause}" >> "$BLOCKLIST"; fi
      echo "  [$_n/$missing] $_id → imposible ($_cause)"
      _estado "listo" "$_n" "$missing" "$_id → $_cause"
      # DISYUNTOR: 3 rate-limited seguidos = sesión quemada → state + paro total
      if [ "$_cause" = "rate-limited" ]; then _rl=$((_rl + 1)); else _rl=0; fi
      if [ "$_rl" -ge 3 ]; then
        echo "{\"desde\": \"$(date '+%F %R')\", \"canal\": \"$canal\", \"consec\": $_rl}" > /tmp/yt-throttle.json
        echo "  🛑 THROTTLE: 3 rate-limited seguidos en $canal — paro total, retoma con play"
        echo "  🛑 THROTTLE $canal" >> "/tmp/radar-$canal.log"
        echo "  🛑 THROTTLE $canal" >> "/tmp/yt-radar.log"
        return 2
      fi
    fi
  done
  echo "  ✓ $canal: $_ok nuevos de $missing (blocklist: $skipped saltados)"
  _estado "terminado" "$_ok" "$missing" "$canal $_ok nuevos"
  local final=$(cuenta_ids "$out")
  echo "  -> $canal: $final/$total"
  python3 "$SCRIPT_DIR/../lib/update_index.py" "$canal" "$final" "$total"
  sleep 15
}

if [ -n "$TARGET" ]; then radar_canal "$TARGET" "$MODE"
else
  for c in "${CANAL_ORDEN[@]}"; do radar_canal "$c" "$MODE"; [ $? -eq 2 ] && { echo "🛑 THROTTLE total: paro --all, retoma con play"; break; }; done
fi
