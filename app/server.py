#!/usr/bin/env python3
from flask import Flask, request, jsonify

import subprocess, pathlib, json, re, os

app = Flask(__name__)
@app.after_request
def cors(r):
    r.headers["Access-Control-Allow-Origin"] = "*"
    r.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    r.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return r
BASE = pathlib.Path.home() / "youtube-knowledge/knowledge/videos"
ROUTER = "http://127.0.0.1:8080"

def grep_top(query, search_path, top_k=10):
    # simple grep -i -l
    try:
        out = subprocess.check_output(["grep", "-r", "-i", "-l", query, str(search_path), "--include=*.md", "--include=*.srt"], text=True)
        files = [l.strip() for l in out.splitlines() if l.strip()][:20]
    except subprocess.CalledProcessError:
        # fallback first word
        first = query.split()[0]
        try:
            out = subprocess.check_output(["grep", "-r", "-i", "-l", first, str(search_path), "--include=*.md", "--include=*.srt"], text=True)
            files = [l.strip() for l in out.splitlines() if l.strip()][:10]
        except: files = []
    return files[:top_k]

@app.route("/api/knowledge/research", methods=["POST"])
def research():
    data = request.get_json() or {}
    query = data.get("query","")
    folders = data.get("folders",[])
    top_k = int(data.get("topk",10))
    model = data.get("model","qwen36-mtp")
    web = data.get("web", False)
    proyecto = data.get("proyecto","")
    if not query: return jsonify({"error":"query required"}),400
    # 1. local
    docs = []
    search_paths = [BASE / f for f in folders] if folders else [BASE]
    for sp in search_paths:
        if sp.exists():
            docs += grep_top(query, sp, top_k)
    docs = docs[:top_k]
    contexto = ""
    for f in docs:
        p = pathlib.Path(f)
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
            # limpiar si es md
            if p.suffix==".md":
                # quitar frontmatter
                txt = re.sub(r'^---.*?---\n','',txt, flags=re.S)
                txt = txt.replace("![thumbnail]","")
            else:
                txt = "\n".join([l for l in txt.splitlines() if not l.startswith("#") and not re.match(r'^\d+$',l.strip()) and not re.match(r'^\d{2}:',l)])
            contexto += f"\n\n--- DOC: {p.name} ---\n" + txt[:8000]
        except: pass
    contexto = contexto[:100000]
    # 2. web (placeholder, si web true añade nota)
    web_ctx = ""
    if web:
        web_ctx = "\n\n--- WEB (radar) ---\nHuggingFace: Qwen3.8 Q4_K_M disponible, 131K ctx. r/LocalLLaMA: nuevo quant Gemma 26B. (mock web)\n"
    full_ctx = contexto + web_ctx
    # 3. proyecto
    if proyecto:
        proj_path = pathlib.Path.home() / f"Documentos/{proyecto}/INDEX.md"
        if proj_path.exists():
            proj_txt = proj_path.read_text()[:5000]
            full_ctx = f"--- PROYECTO {proyecto} INDEX ---\n{proj_txt}\n\n" + full_ctx
    # 4. llamar router (forja / omni / opencode)
    proveedor = data.get("proveedor","forja")
    sesion = data.get("sesion","")
    prompt = f"Responde usando SOLO el contexto. Cita DOC origen.\n\nContexto:\n{full_ctx}\n\nPregunta: {query}\n\nRespuesta concisa en español con citas [DOC]:"
    import requests, os
    # elegir endpoint según proveedor
    if proveedor == "omni":
        OMNI = "http://127.0.0.1:20128"
        OMNI_KEY = os.environ.get("OMNIROUTE_API_KEY") or open(os.path.expanduser("~/.bashrc")).read().split("OMNIROUTE_API_KEY=")[1].split()[0].strip('"').strip("'") if "OMNIROUTE_API_KEY" in open(os.path.expanduser("~/.bashrc")).read() else ""
        url = f"{OMNI}/v1/chat/completions"
        headers = {"Authorization": f"Bearer {OMNI_KEY}", "Content-Type":"application/json"} if OMNI_KEY else {"Content-Type":"application/json"}
    elif proveedor == "opencode":
        # efecto Lázaro: mandar a opencode session (si existe) o crear nueva
        # por ahora reusar forja pero guardando sesion id en histórico
        url = f"{ROUTER}/v1/chat/completions"
        headers = {"Content-Type":"application/json"}
        # nota: sesion se guarda en nombre de archivo
    else:
        url = f"{ROUTER}/v1/chat/completions"
        headers = {"Content-Type":"application/json"}
    try:
        r = requests.post(url, headers=headers, json={
            "model": model,
            "messages":[
                {"role":"system","content":"Eres asistente RAG. Responde solo con contexto, cita DOC."},
                {"role":"user","content": prompt}
            ],
            "temperature":0.2,
            "max_tokens": 800
        }, timeout=120)
        j = r.json()
        msg = j["choices"][0]["message"]
        content = msg.get("content") or msg.get("reasoning_content","")[:3000]
        timings = j.get("timings",{})
    except Exception as e:
        content = f"Error {proveedor}: {e}"
        timings = {}
    # guardar historico
    summ = pathlib.Path.home() / "youtube-knowledge/knowledge/summaries"
    summ.mkdir(parents=True, exist_ok=True)
    base_name = f"{proyecto or 'general'}-{__import__('datetime').date.today()}-{query[:20].replace(' ','-')}"
    if proveedor=="opencode" and sesion:
        base_name = f"{sesion}-{base_name}"
    fname = re.sub(r'[^a-zA-Z0-9._-]', '-', base_name) + ".md"
    (summ / fname).write_text(f"# {query}\n\n{content}\n\n---\n*Proveedor: {proveedor} • Modelo: {model} • {timings.get('predicted_per_second',0):.1f} tok/s • Sesión: {sesion or 'nueva'}*\n", encoding="utf-8")
    return jsonify({"markdown": content, "docs": [str(d) for d in docs], "timings": timings, "file": str(summ/fname), "proveedor": proveedor})

@app.route("/api/knowledge/sessions", methods=["GET"])
def sessions():
    # lista sesiones opencode (grep docs/sessions)
    sess_dir = pathlib.Path.home() / "Documentos/alcon/docs/sessions"
    files = sorted(sess_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:10] if sess_dir.exists() else []
    return jsonify([{"id": f.stem, "name": f.name} for f in files])

# --- Dashboard vivo hemeroteca ---
@app.route("/dashboard")
def dashboard():
    return open("~/youtube-knowledge/dashboard.html").read()
def _ahora():
    # estado humano del radar (fresco <10min); si no, parado
    import time as _t
    try:
        st = json.loads(pathlib.Path("/tmp/yt-estado.json").read_text())
        if _t.time() - int(st.get("ts", 0)) > 600:
            return {"activo": False}
        st["activo"] = True
        return st
    except Exception:
        return {"activo": False}

def _qdrant_puntos(url, timeout=6, reintento=True):
    # vacuna anti-ceguera: vacío/timeout/HTTP raro/forma mala = CIEGO con motivo, nunca "todo bien"
    import urllib.request as _ur
    for intento in (1, 2) if reintento else (1,):
        try:
            with _ur.urlopen(url, timeout=timeout) as _r:
                if _r.status != 200:
                    continue  # reintenta 1 vez lo transitorio
                d = json.loads(_r.read().decode("utf-8", "ignore"))
                pts = d["result"]["points_count"]  # valida FORMA (KeyError = ceguera)
                if not isinstance(pts, int):
                    return {"estado": "CIEGO", "motivo": "forma inválida"}
                return {"estado": "ok", "puntos": pts}
        except Exception as e:
            ultimo = f"{type(e).__name__}: {str(e)[:80]}"
    return {"estado": "CIEGO", "motivo": ultimo}

def _rag_estado(total_md):
    # puntos Qdrant local + espejo HP (cache 10min, SSH con timeout corto)
    import time as _t
    rag = {"puntos": None, "total_md": total_md, "hp": {"puntos": None}}
    _l = _qdrant_puntos("http://127.0.0.1:6333/collections/hemeroteca")
    if _l.get("estado") == "ok":
        rag["puntos"] = _l["puntos"]
    else:
        rag["local_ciego"] = _l.get("motivo", "?")
    try:
        hp = pathlib.Path("/tmp/rag-hp.json")
        if hp.exists() and _t.time() - hp.stat().st_mtime < 600:
            rag["hp"] = json.loads(hp.read_text())
        else:
            out = subprocess.check_output(
                ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
                 "server@100.107.54.12", "curl -s -m 8 http://127.0.0.1:6333/collections/hemeroteca"],
                text=True, timeout=20)
            pts = json.loads(out)["result"]["points_count"]
            if not isinstance(pts, int):
                raise ValueError("forma inválida")
            rag["hp"] = {"puntos": pts}
            hp.write_text(json.dumps(rag["hp"]))
    except Exception as e:
        rag["hp"] = {"puntos": None, "sordo": f"{type(e).__name__}: {str(e)[:80]}"}
        try:
            hp = pathlib.Path("/tmp/rag-hp.json")
            if hp.exists():
                _viejo = json.loads(hp.read_text())
                if _viejo.get("puntos") is not None:
                    rag["hp"] = {"puntos": _viejo["puntos"], "desactualizado": True}
        except: pass
    return rag

@app.route("/api/progreso")
def progreso():
    import re, pathlib, subprocess, json
    base = pathlib.Path.home() / "youtube-knowledge/canales-index.csv"
    index_json = pathlib.Path.home() / "youtube-knowledge/knowledge/index.json"
    videos_dir = pathlib.Path.home() / "youtube-knowledge/knowledge/videos"

    # denominador: index.json (vivo de YouTube) > CSV (estático)
    yt_totals = {}
    index_data = {}
    if index_json.exists():
        try:
            index_data = json.loads(index_json.read_text())
            for k, v in index_data.items():
                yt_totals[k] = v.get("youtube", 0)
        except: pass
    csv_esperado = {}
    handles = {}
    idiomas = {}
    notas = {}
    for line in open(base):
        if line.startswith("canal,"): continue
        p = line.strip().split(",", 8)
        if len(p) >= 6:
            try: csv_esperado[p[0]] = int(p[5])
            except: pass
            if len(p) >= 2 and p[1].startswith("@"):
                handles[p[0]] = "https://www.youtube.com/" + p[1] + "/videos"
            if len(p) >= 5 and p[4] in ("es", "en"):
                idiomas[p[0]] = p[4]
            if len(p) >= 9 and p[8].strip():
                notas[p[0]] = p[8].strip()[:140]

    # numerador: [ids] únicos por carpeta (no archivos, no duplica traducidos)
    import re as _re
    actual = {}
    srt_pendientes = 0
    for md in videos_dir.rglob("*.md"):
        groups = _re.findall(r'\[([^\]]+)\]', md.stem)
        # el videoId va al final; títulos como "[TUTORIAL Kotlin] ... [abc123XYZ_-]" engañan al primero
        vid_id = next((g for g in groups if _re.fullmatch(r'[A-Za-z0-9_-]{11}', g or '')), groups[-1] if groups else None)
        if vid_id:
            canal_dir = md.parent.name
            if canal_dir not in actual:
                actual[canal_dir] = set()
            actual[canal_dir].add(vid_id)
    for srt in videos_dir.rglob("*.srt"):
        md = srt.parent / (srt.stem + '.md')  # foo.es.srt -> foo.es.md (antes buscaba foo.md)
        if not md.exists():
            srt_pendientes += 1

    # snapshot diario por canal (retención 8 fechas) para deltas hoy/7d
    import datetime as _dtd
    snap_path = videos_dir.parent / "historial-canales.json"
    try:
        snaps = json.loads(snap_path.read_text()) if snap_path.exists() else {}
    except: snaps = {}
    try:
        hoy_str = _dtd.date.today().isoformat()
        snaps[hoy_str] = {k: {"local": int(v.get("local", 0)), "youtube": int(v.get("youtube", 0))} for k, v in index_data.items()}
        for _old in sorted(snaps.keys())[:-8]:
            del snaps[_old]
        snap_path.write_text(json.dumps(snaps))
    except: pass
    fechas = sorted(snaps.keys())
    ayer = fechas[-2] if len(fechas) >= 2 else None

    # imposibles + members-only + recuperables por canal desde blocklist
    impos = {}
    miembros = {}
    recups = {}
    impos_lista = {}
    try:
        for _ln in pathlib.Path.home().joinpath(".cache/yt-bloqueados.txt").read_text().splitlines():
            _m = _re.match(r'^(\S+) (\S+) # (\S+) (.*)$', _ln)
            if _m:
                _id, _fe, _c, _ca = _m.groups()
                impos[_c] = impos.get(_c, 0) + 1
                impos_lista.setdefault(_c, []).append({"id": _id, "fecha": _fe, "causa": _ca})
                if "members-only" in _ca:
                    miembros[_c] = miembros.get(_c, 0) + 1
                if _ca in ("sin-md", "no subtitles", "subs-vacios"):
                    recups[_c] = recups.get(_c, 0) + 1
    except: pass

    # merge: todos los canales que existan en CSV o index
    all_canales = sorted(set(list(csv_esperado.keys()) + list(yt_totals.keys())))
    canales = []
    for canal in all_canales:
        e = yt_totals.get(canal) or csv_esperado.get(canal) or 0
        h = len(actual.get(canal, set()))
        pct = int(h * 100 / e) if e else 0
        r = max(e - h - impos.get(canal, 0), 0)  # faltan de verdad (sin imposibles)
        canales.append({"canal": canal, "esperado": e, "hecho": h, "pct": pct, "reales": r, "imposibles": impos.get(canal, 0)})

    total_e = sum(c["esperado"] for c in canales)
    total_h = sum(c["hecho"] for c in canales)
    radar = "activo" if subprocess.getoutput("ps aux | grep yt-radar | grep -v grep | wc -l").strip() != "0" else "pausado"
    log = subprocess.getoutput("tail -1 /tmp/yt-radar.log 2>/dev/null | cut -c1-80")
    # guardia throttle: state de /tmp/yt-throttle.json, fresco <2h
    throttle = {"activo": False}
    try:
        import datetime as _dt
        st = json.loads(pathlib.Path("/tmp/yt-throttle.json").read_text())
        desde = _dt.datetime.strptime(st.get("desde", ""), "%Y-%m-%d %H:%M")
        if (_dt.datetime.now() - desde).total_seconds() < 7200:
            throttle = {"activo": True, "desde": st.get("desde"), "canal": st.get("canal"), "consec": st.get("consec", 3)}
    except: pass
    # snapshot para grafo temporal (1 cada 5min max)
    try:
        import datetime, time
        hist_path = pathlib.Path.home() / "youtube-knowledge/knowledge/historial.json"
        hist = json.loads(hist_path.read_text()) if hist_path.exists() else []
        now = int(time.time())
        if not hist or (now - hist[-1].get("t",0)) >= 300:
            hist.append({"t": now, "md": total_h, "pct": int(total_h*100/total_e) if total_e else 0})
            hist = hist[-288:]
            hist_path.write_text(json.dumps(hist))
    except: pass
    # en vivo: canal activo detectado desde yt-dlp en ejecución
    live = None
    try:
        ps_out = subprocess.getoutput("ps aux | grep '[y]t-dlp.*--write-sub' | grep -v tee").strip()
        if ps_out:
            # extraer canal: último directorio antes de %(upload_date en el output path
            matches = _re.findall(r'/([a-zA-Z0-9_-]+)/(?:%\(upload_date)', ps_out)
            if matches:
                canal = matches[-1]  # último match = nombre del canal
            else:
                # fallback: buscar @ChannelName en cmdline antiguo
                m = _re.search(r'@([a-zA-Z0-9_-]+)\s', ps_out)
                canal = m.group(1) if m else "?"
            # buscar progreso en su log
            log_path = f"/tmp/radar-{canal}.log"
            if os.path.exists(log_path):
                tail = open(log_path, "rb").read()[-8000:].decode("utf-8", "ignore")
                item_m = _re.findall(r"Downloading item (\d+) of (\d+)", tail)
                if item_m:
                    live = {"canal": canal, "item": int(item_m[-1][0]), "total": int(item_m[-1][1]), "descargando": True}
                else:
                    bm = _re.findall(r"# BATCH total=(\d+)", tail)
                    if bm:
                        total_b = int(bm[-1])
                        seg = tail.split("# BATCH")[-1]
                        item_n = len(_re.findall(r"Extracting URL", seg))
                        live = {"canal": canal, "item": min(item_n, total_b) if total_b else item_n, "total": total_b, "descargando": True}
                    else:
                        live = {"canal": canal, "item": None, "total": None, "descargando": True}
            else:
                live = {"canal": canal, "item": None, "total": None, "descargando": True}
        # si no hay yt-dlp, no mostrar live bar
    except Exception:
        pass
    # desglose hoy por canal + historial 7d + avisos
    detalle = []
    try:
        _live_canal = (live or {}).get("canal")
        _h7 = fechas[-7:]
        for canal in all_canales:
            _v = index_data.get(canal, {})
            _loc = int(_v.get("local", 0))
            _yt = int(yt_totals.get(canal) or 0)
            _faltan = max(_yt - _loc, 0)
            _nh = (_loc - int(snaps[ayer].get(canal, {}).get("local", 0))) if ayer else None
            _hist = []
            for _i, _f in enumerate(_h7):
                _prev = _h7[_i - 1] if _i > 0 else (fechas[fechas.index(_f) - 1] if _f in fechas and fechas.index(_f) > 0 else None)
                _pv = int(snaps[_prev].get(canal, {}).get("local", 0)) if _prev else 0
                _hist.append(int(snaps[_f].get(canal, {}).get("local", 0)) - _pv)
            _av = []
            try:
                _lc = _dtd.datetime.strptime(_v.get("last_check", ""), "%d/%m/%Y-%H:%M")
                if _faltan > 0 and (_dtd.datetime.now() - _lc).total_seconds() > 172800:
                    _av.append("atorado")
            except: pass
            if _yt and miembros.get(canal, 0) * 10 > _yt:
                _av.append("miembros_altos")
            _est = "ok" if _faltan == 0 else ("curso" if _live_canal == canal else "pendiente")
            _prop = ""
            try:
                _pf = pathlib.Path(f"/tmp/yt-idioma-{canal}.json")
                if _pf.exists():
                    _pj = json.loads(_pf.read_text())
                    _prop = f"{_pj.get('propuesta','?')} (mapa {idiomas.get(canal,'?')})"
                    _av.append("idioma_por_confirmar")
            except: pass
            detalle.append({"canal": canal, "nuevos_hoy": _nh, "faltan": _faltan, "estado": _est,
                            "imposibles": impos.get(canal, 0), "miembros": miembros.get(canal, 0),
                            "recuperables": recups.get(canal, 0), "url": handles.get(canal, ""),
                            "imposibles_lista": impos_lista.get(canal, [])[:300],
                            "idioma": idiomas.get(canal, "?"), "nota": notas.get(canal, ""),
                            "propuesta": _prop,
                            "last_check": _v.get("last_check", ""), "hist7": _hist, "avisos": _av})
    except Exception:
        pass
    return jsonify({"total_md": total_h, "total_esperado": total_e, "pct": int(total_h * 100 / total_e) if total_e else 0, "srt_pendientes": srt_pendientes, "canales": canales, "radar": radar, "log": log, "live": live, "throttle": throttle, "detalle": detalle, "cookie": _cookie_resumen(), "ahora": _ahora(), "rag": _rag_estado(total_h)})

# --- Procesos vivos ---
@app.route("/api/procesos")
def procesos():
    import subprocess
    procs = []
    checks = [
        ("radar", "yt-radar.sh"),
        ("yt-dlp", "yt-dlp"),
        ("server", "server.py"),
        ("traductor", "yt-translate-ray"),
        ("post-filter", "yt-post-filter"),
        ("srt2md", "srt2md.py"),
    ]
    for nombre, patron in checks:
        out = subprocess.getoutput(f"ps aux | grep '{patron}' | grep -v grep | head -1")
        if out.strip():
            parts = out.split()
            pid = parts[1]
            cpu = parts[2]
            mem = parts[3]
            detalle = ""
            if patron == "yt-dlp":
                import re as _r
                m = _r.search(r'/([^/]+)/%\(', out)
                if m: detalle = m.group(1)
                else:
                    m = _r.search(r'youtube\.com/@(\S+)/videos', out)
                    if m: detalle = m.group(1)
            procs.append({"nombre": nombre, "pid": pid, "cpu": cpu, "mem": mem, "estado": "activo", "detalle": detalle})
        else:
            detalle = ""
            if patron == "yt-dlp":
                try:
                    import subprocess as _sp
                    radar_vivo = _sp.getoutput("ps aux | grep 'yt-radar.sh' | grep -v grep | wc -l").strip() != "0"
                    log = pathlib.Path("/tmp/yt-radar.log").read_text(errors="ignore").splitlines()
                    for line in reversed(log):
                        if "▶" in line:
                            import re as _r
                            m = _r.search(r'▶\s*(\S+)', line)
                            if m:
                                detalle = m.group(1) + (" (pausa 15s)" if radar_vivo else " (último)")
                            break
                except: pass
            procs.append({"nombre": nombre, "pid": "", "cpu": "", "mem": "", "estado": "detenido", "detalle": detalle})
    return jsonify(procs)

# --- Actividad (bitácora del día) ---
@app.route("/api/actividad")
def actividad():
    import subprocess
    log_path = pathlib.Path.home() / "tmp/yt-radar.log"
    if not log_path.exists():
        log_path = pathlib.Path("/tmp/yt-radar.log")
    entradas = []
    if log_path.exists():
        lines = log_path.read_text(encoding="utf-8", errors="ignore").strip().splitlines()
        prev = None
        import re as _r
        _spam = _r.compile(r'\d+\.\d+[KM]iB at|^\[download\]|Deleting original|Converting subtitles|Writing video subtitles|player API JSON|Downloading webpage|Extracting URL|^Downloading \d+ format')
        for line in lines[-400:]:
            line = line.strip()
            if not line: continue
            if line == prev: continue  # yt-dlp duplica stdout+stderr con 2>&1
            prev = line
            if _spam.search(line): continue  # progreso técnico: no es actividad humana
            # parsear líneas conocidas
            if "▶" in line or "✓" in line or "⚠" in line or "RADAR" in line or "v3" in line or "init" in line or "🧺" in line or "🛑" in line or "⏸" in line or "🎣" in line or "imposible" in line:
                entradas.append({"texto": line[:120], "tipo": "info"})
            elif "Error" in line or "FALLO" in line or "fallo" in line:
                entradas.append({"texto": line[:120], "tipo": "error"})
            elif "completado" in line or "OK" in line:
                entradas.append({"texto": line[:120], "tipo": "ok"})
            else:
                entradas.append({"texto": line[:120], "tipo": "neutral"})
    entradas.reverse()
    return jsonify(entradas[:20])

# --- Conversiones (srt→md) ---
@app.route("/api/conversiones")
def conversiones():
    import subprocess
    videos_dir = pathlib.Path.home() / "youtube-knowledge/knowledge/videos"
    pendientes = list(videos_dir.rglob("*.srt"))
    # contar md creados hoy
    import datetime
    hoy = datetime.date.today().isoformat()
    convertidos_hoy = 0
    for md in videos_dir.rglob("*.md"):
        try:
            if md.stat().st_mtime > datetime.datetime.now().timestamp() - 86400:
                convertidos_hoy += 1
        except: pass
    # cola por canal (solo srt sin .md hermano: foo.es.srt -> foo.es.md)
    cola = {}
    for srt in pendientes:
        if (srt.parent / (srt.stem + '.md')).exists():
            continue
        canal = srt.parent.name
        cola[canal] = cola.get(canal, 0) + 1
    pendientes_reales = sum(cola.values())
    return jsonify({"pendientes": pendientes_reales, "convertidos_hoy": convertidos_hoy, "cola": cola})

# --- Estado del índice ---
@app.route("/api/index-status")
def index_status():
    import datetime
    index_json = pathlib.Path.home() / "youtube-knowledge/knowledge/index.json"
    data = {}
    if index_json.exists():
        try: data = json.loads(index_json.read_text())
        except: pass
    resultado = []
    for canal, info in sorted(data.items()):
        last = info.get("last_check", "")
        yt = info.get("youtube", 0)
        local = info.get("local", 0)
        status = info.get("status", "")
        # verificar si es viejo (>24h)
        desactualizado = False
        if last:
            try:
                fecha = datetime.datetime.strptime(last, "%d/%m/%Y-%H:%M")
                if (datetime.datetime.now() - fecha).total_seconds() > 86400:
                    desactualizado = True
            except: pass
        resultado.append({"canal": canal, "youtube": yt, "local": local, "status": status, "last_check": last, "desactualizado": desactualizado})
    return jsonify(resultado)

# --- Abrir carpeta del canal (solo local: xdg-open en el host del server) ---
@app.route("/api/carpeta/<canal>")
def abrir_carpeta(canal):
    import json as _js
    base = pathlib.Path.home() / "youtube-knowledge/knowledge/videos"
    # mapa canal -> subruta desde lib/canales.sh (anti path-traversal: solo slugs conocidos)
    mapa = {}
    try:
        lib = pathlib.Path.home() / "youtube-knowledge/lib/canales.sh"
        for mm in re.finditer(r'\[([a-z0-9-]+)\]=\s*"([^"]+)"', lib.read_text()):
            mapa[mm.group(1)] = mm.group(2).split()[-1]
    except Exception:
        pass
    if canal not in mapa:
        return jsonify({"ok": False, "error": "canal desconocido"}), 404
    ruta = base / mapa[canal]
    ruta.mkdir(parents=True, exist_ok=True)
    subprocess.Popen(["xdg-open", str(ruta)], start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return jsonify({"ok": True, "ruta": str(ruta)})

# --- Radar control ---
import subprocess, signal, os

@app.route("/api/radar/start")
def radar_start():
    cur = subprocess.getoutput("ps aux | grep '[y]t-radar.sh --all' | wc -l").strip()
    if cur != "0":
        return jsonify({"status": "already_running", "motivo": "ya hay un radar corriendo; no se duplica"})
    log_file = "/tmp/yt-radar.log"
    script = pathlib.Path.home() / "youtube-knowledge/bin/yt-radar.sh"
    proc = subprocess.Popen(
        ["bash", str(script), "--all"],
        stdout=open(log_file, "a"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
        cwd=str(pathlib.Path.home() / "youtube-knowledge"),
        env={**os.environ, "PATH": str(pathlib.Path.home() / ".local/deno/bin") + ":" + os.environ.get("PATH", "")}
    )
    return jsonify({"status": "ok", "pid": proc.pid})

@app.route("/api/radar/stop")
def radar_stop():
    import signal
    killed = []
    for line in subprocess.check_output(["ps", "aux"], text=True).splitlines():
        if "yt-radar.sh" in line or ("yt-dlp" in line and "youtube-knowledge" in line):
            pid = int(line.split()[1])
            try:
                os.kill(pid, signal.SIGTERM)
                killed.append(pid)
            except: pass
    return jsonify({"status": "ok", "killed": killed})

@app.route("/api/server/restart")
def server_restart():
    subprocess.Popen(["systemctl", "--user", "restart", "knowledge-server.service"])
    return jsonify({"status": "restarting"})

@app.route("/api/radar-log")
def radar_log():
    import re as _rx
    try:
        main = pathlib.Path("/tmp/yt-radar.log").read_text(errors="ignore").splitlines()
        canal = ""
        for line in reversed(main):
            m = _rx.search(r'▶\s*(\S+)', line)
            if m: canal = m.group(1); break
        detalle = []
        if canal:
            p = pathlib.Path(f"/tmp/radar-{canal}.log")
            if p.exists():
                detalle = p.read_text(errors="ignore").splitlines()[-8:]
        lines = [l for l in main[-10:] if l.strip()]
        dedup = [l for i, l in enumerate(lines) if i == 0 or l != lines[i-1]]
        detalle = [l for l in detalle if l.strip()]
        detalle = [l for i, l in enumerate(detalle) if i == 0 or l != detalle[i-1]]
        return jsonify({"lines": dedup, "canal": canal, "detalle": detalle})
    except: return jsonify({"lines": [], "canal": "", "detalle": []})

# --- Proponer canal: análisis de factibilidad antes de descargar ---
@app.route("/api/canal/check", methods=["GET", "POST"])
def canal_check():
    import re as _re, subprocess as _sp, json as _json, time as _time
    data = request.get_json(silent=True) or {}
    _jbody = data
    raw = (data.get("url") or data.get("handle") or request.args.get("u") or "").strip()
    if not raw:
        return jsonify({"error": "pasa url o @handle (?u= o JSON {url})"}), 400
    # normalizar: @handle, /@handle, /channel/ID, /c/nombre, watch?v=
    handle = ""
    m = _re.search(r'@([A-Za-z0-9_.-]+)', raw)
    if m:
        handle = "@" + m.group(1)
    elif _re.match(r'^[A-Za-z0-9_.-]+$', raw):
        handle = "@" + raw
    else:
        m2 = _re.search(r'(channel/|/c/|/user/)([^/?#&]+)', raw)
        handle = m2.group(2) if m2 else raw
    playlist = f"https://www.youtube.com/{handle}/videos" if handle.startswith("@") else raw
    # ¿ya existe?
    conocidos = {}
    try:
        lib = pathlib.Path.home() / "youtube-knowledge/lib/canales.sh"
        for mm in _re.finditer(r'\[([a-z0-9-]+)\]=\s*"([^"]+)"', lib.read_text()):
            conocidos[mm.group(1)] = mm.group(2).split()
    except Exception:
        pass
    for slug, parts in conocidos.items():
        if parts and parts[0].lower() == handle.lower():
            idx = {}
            try:
                idx = _json.loads((pathlib.Path.home() / "youtube-knowledge/knowledge/index.json").read_text()).get(slug, {})
            except Exception:
                pass
            return jsonify({"handle": handle, "slug": slug, "ya_existe": True,
                            "progreso": idx.get("progress", ""), "status": idx.get("status", ""),
                            "veredicto": "YA_LO_TIENES",
                            "motivo": f"Ya está en hemeroteca como '{slug}' ({idx.get('progress','?')}). No lo agregues de nuevo."})
    # conteo ligero flat (igual que radar, con cookies+ipv4+deno)
    env = {**os.environ, "PATH": str(pathlib.Path.home() / ".local/deno/bin") + ":" + os.environ.get("PATH", "")}
    cookie = pathlib.Path.home() / ".cache/yt-cookies/youtube.txt"
    base_args = ["yt-dlp", "--js-runtimes", "deno", "--force-ipv4", "--no-warnings", "--ignore-errors",
                 "--extractor-args", "youtube:player_client=android,web", "--no-check-formats"]
    if cookie.exists():
        base_args += ["--cookies", str(cookie)]
    try:
        ids = _sp.check_output(base_args + ["--flat-playlist", "--print", "id", playlist],
                               text=True, timeout=40, env=env).split()
    except Exception as e:
        return jsonify({"handle": handle, "ya_existe": False, "veredicto": "BLOQUEADO_O_INEXISTENTE",
                        "motivo": f"flat-playlist dio 0 (¿IP marcada, handle mal o videos ocultos?). Detalle: {str(e)[:150]}. Prueba en 12-24h o revisa el @handle.",
                        "total": 0})
    total = len(ids)
    if total == 0:
        return jsonify({"handle": handle, "ya_existe": False, "veredicto": "BLOQUEADO_O_INEXISTENTE",
                        "motivo": "YouTube devolvió 0 videos (flat 0). Causas típicas: IP temporalmente marcada, canal sin pestaña videos, o handle incorrecto.",
                        "total": 0})
    # muestra: 3 primeros videos, ¿tienen subs? ¿son members-only / age-restricted?
    muestra, sin_subs, privados, miembros, edad = [], 0, 0, 0, 0
    langs = []
    for vid in ids[:3]:
        try:
            j = _json.loads(_sp.check_output(base_args + ["-J", "--skip-download", f"https://www.youtube.com/watch?v={vid}"],
                                             text=True, timeout=30, env=env))
            tit = j.get("title", "")[:60]
            subs = j.get("subtitles") or {}
            auto = j.get("automatic_captions") or {}
            tiene = bool(subs or auto)
            vl = (j.get("language") or "")[:2]
            if vl:
                langs.append(vl)
            disp = {"subs_es": bool((subs.get("es") or auto.get("es"))),
                    "subs_en": bool((subs.get("en") or auto.get("en")))}
            muestra.append({"id": vid, "titulo": tit, "subs": tiene, "lang": vl or "?", **disp})
            if not tiene:
                sin_subs += 1
        except Exception as e:
            msg = str(e)[:200]
            muestra.append({"id": vid, "titulo": "?", "subs": False, "error": msg[:80]})
            if "members-only" in msg or "Join this channel" in msg:
                miembros += 1
            elif "age" in msg.lower():
                edad += 1
            else:
                privados += 1
    # veredicto
    estim_min = round(total * 8 / 60)  # ~8s/video con sleep 2-5 + overhead
    if miembros >= 2:
        veredicto, motivo = "NO_FACTIBLE", "Mayoría members-only (requiere membresía del canal). No descargable."
    elif total > 1500:
        veredicto, motivo = "PESADO", f"Canal gigante ({total} videos, ~{estim_min} min + pausas). Factible pero en tandas nocturnas, no de golpe."
    elif sin_subs >= 2:
        veredicto, motivo = "RIESGO_SIN_SUBS", f"Muestra sin subtítulos ({sin_subs}/3). Se bajarían pocos .md y el resto iría a blocklist. Revisa si el canal activa CC."
    elif edad >= 1 or privados >= 1:
        veredicto, motivo = "FACTIBLE_CON_PERDIDAS", "Hay videos con restricción de edad o privados; se rescata la mayoría, el resto queda en blocklist."
    else:
        veredicto, motivo = "FACTIBLE", f"Canal sano: {total} videos con subs (~{estim_min} min). Para agregarlo: lib/canales.sh + CANAL_ORDEN en yt-radar.sh + fila en canales-index.csv."
    # idioma: mayoría de la muestra; alerta si el propuesto no coincide
    idioma_det = max(set(langs), key=langs.count) if langs else "?"
    propuesto = ((_jbody.get("lang") or "")[:2] if isinstance(_jbody, dict) else "")
    alerta_idioma = ""
    if propuesto and idioma_det != "?" and propuesto != idioma_det:
        alerta_idioma = f"habla {idioma_det} pero propones {propuesto}: usa {idioma_det} o traerás auto-traducciones"
    # sospecha auto-traducción: subs en ambos idiomas en la mayoría (el metadata language es ruidoso)
    ambos = sum(1 for m in muestra if m.get("subs_es") and m.get("subs_en"))
    if ambos >= 2 and not alerta_idioma:
        alerta_idioma = "subs en ES+EN en la muestra (posible auto-traducción): baja 1 video y verifica cuál es el original"
    return jsonify({"handle": handle, "ya_existe": False, "total": total, "muestra": muestra,
                    "estim_min": estim_min, "veredicto": veredicto, "motivo": motivo,
                    "idioma_detectado": idioma_det, "alerta_idioma": alerta_idioma})

# --- Cookie: salud offline (sin tocar red, no alarga rate-limits) ---
@app.route("/api/cookie/status")
def cookie_status():
    return jsonify(_cookie_resumen())

def _cookie_resumen():
    import time as _t, datetime as _dt
    p = pathlib.Path.home() / ".cache/yt-cookies/youtube.txt"
    if not p.exists():
        return {"existe": False, "motivo": "no existe ~/.cache/yt-cookies/youtube.txt", "veredicto": "SIN_COOKIE", "login": False}
    try:
        names, validas, expiradas, sesion = [], 0, 0, 0
        for line in p.read_text(errors="ignore").splitlines():
            if line.startswith("#HttpOnly_"):
                line = line[len("#HttpOnly"):]  # las de login vienen así; no son comentarios
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 7:
                continue
            names.append(parts[5])
            try:
                e = int(parts[4])
            except Exception:
                e = 0
            if e == 0:
                sesion += 1
            elif e < _t.time():
                expiradas += 1
            else:
                validas += 1
        login_markers = {"SID", "HSID", "SSID", "APISID", "SAPISID", "LOGIN_INFO", "__Secure-1PSID", "__Secure-3PSID"}
        tiene = login_markers.intersection(names)
        return {
            "existe": True,
            "mtime": _dt.datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
            "total": len(names),
            "validas": validas, "expiradas": expiradas, "sesion": sesion,
            "login": bool(tiene),
            "login_cookies": sorted(tiene),
            "veredicto": "CON_LOGIN" if tiene else "ANONIMA",
            "motivo": ("Con sesión (age-restricted OK). Si hay rate-limit igual hay que esperar 12-24h."
                       if tiene else
                       "Sin login: los videos con restricción de edad SIEMPRE fallarán. Re-exporta logueado en la cuenta desechable."),
        }
    except Exception as e:
        return {"existe": True, "error": str(e)[:150], "veredicto": "ERROR", "login": False}

# --- Explorador: buscar por título/contenido, árbol, doc, abrir ---
import unicodedata as _ud
def _norm(s):
    return ''.join(c for c in _ud.normalize('NFD', (s or '').lower()) if _ud.category(c) != 'Mn')

def _videos_base():
    return (pathlib.Path.home() / "youtube-knowledge/knowledge/videos").resolve()

def _ficha(md):
    import re as _rx
    stem = md.stem
    m = _rx.match(r'^(\d{4}-\d{2}-\d{2})\s*-\s*(.*)$', stem)
    fecha = m.group(1) if m else ''
    titulo = (m.group(2) if m else stem)
    titulo = _rx.sub(r'\s*\[[A-Za-z0-9_-]{11}\](\.\w+)?$', '', titulo).strip()
    g = _rx.findall(r'\[([A-Za-z0-9_-]{11})\]', stem)
    return {"titulo": titulo or stem, "canal": md.parent.name, "fecha": fecha,
            "id": g[-1] if g else '', "ruta": str(md)}

@app.route("/api/buscar")
def buscar():
    q = (request.args.get("q") or "").strip()
    if len(q) < 2:
        return jsonify({"error": "q mínimo 2 letras"}), 400
    base = _videos_base()
    nq = _norm(q)
    res, vistas = [], set()
    for md in sorted(base.rglob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        if "00-legacy" in md.parts:
            continue
        if nq in _norm(md.stem):
            res.append({"por": "titulo", **_ficha(md)})
            vistas.add(str(md))
        if len(res) >= 20:
            break
    if len(res) < 20:
        for f in grep_top(q, base, 20):
            if f in vistas or "00-legacy" in f:
                continue
            p = pathlib.Path(f)
            if p.suffix == ".md" and p.is_file():
                res.append({"por": "contenido", **_ficha(p)})
                vistas.add(f)
            if len(res) >= 20:
                break
    return jsonify(res[:20])

@app.route("/api/doc")
def doc_ver():
    r = (request.args.get("ruta") or "").strip()
    if not r:
        return jsonify({"error": "ruta required"}), 400
    base = _videos_base()
    p = (base / r).resolve() if not r.startswith("/") else pathlib.Path(r).resolve()
    if (base not in p.parents) or p.suffix != ".md" or not p.is_file():
        return jsonify({"error": "ruta fuera de hemeroteca"}), 404
    txt = p.read_text(encoding="utf-8", errors="ignore")
    txt = re.sub(r'^---.*?---\n', '', txt, flags=re.S)
    txt = txt.replace("![thumbnail]", "")
    return jsonify({**_ficha(p), "texto": txt[:15000]})

@app.route("/api/abrir", methods=["POST"])
def abrir_doc():
    data = request.get_json(silent=True) or {}
    r = (data.get("ruta") or "").strip()
    base = _videos_base()
    p = (base / r).resolve() if r and not r.startswith("/") else (pathlib.Path(r).resolve() if r else None)
    if not p or (base not in p.parents) or p.suffix != ".md" or not p.is_file():
        return jsonify({"ok": False, "error": "ruta fuera de hemeroteca"}), 404
    subprocess.Popen(["xdg-open", str(p)], start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return jsonify({"ok": True, "ruta": str(p)})

@app.route("/api/arbol")
def arbol():
    import time as _t
    import datetime as _dt
    cp = pathlib.Path("/tmp/yt-arbol.json")
    try:
        if cp.exists() and _t.time() - cp.stat().st_mtime < 300:
            return jsonify(json.loads(cp.read_text()))
    except: pass
    import re as _rx2
    base = _videos_base()
    out = {}
    for nicho in sorted([d for d in base.iterdir() if d.is_dir()]):
        if nicho.name == "00-legacy":
            continue
        for canal in sorted([d for d in nicho.iterdir() if d.is_dir()]):
            ids, ult = set(), 0
            for md in canal.glob("*.md"):
                g = _rx2.findall(r'\[([A-Za-z0-9_-]{11})\]', md.stem)
                if g:
                    ids.add(g[-1])
                try:
                    ult = max(ult, md.stat().st_mtime)
                except: pass
            out.setdefault(nicho.name, {})[canal.name] = {
                "n": len(ids),
                "ultimo": _dt.datetime.fromtimestamp(ult).strftime("%d/%m") if ult else "—"}
    try:
        cp.write_text(json.dumps(out))
    except: pass
    return jsonify(out)

@app.route("/api/lista")
def lista_canal():
    slug = (request.args.get("canal") or "").strip()
    try:
        pag = max(int(request.args.get("pag") or 0), 0)
    except: pag = 0
    if not slug or "/" in slug or slug.startswith("."):
        return jsonify({"error": "canal inválido"}), 400
    base = _videos_base()
    dirs = [d for n in base.iterdir() if n.is_dir() for d in ([n] if n.name == slug else ([n / slug] if (n / slug).is_dir() else []))]
    if not dirs:
        return jsonify({"error": "canal desconocido"}), 404
    mds = sorted(dirs[0].glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    total = len(mds)
    items = [{**_ficha(m)} for m in mds[pag * 50:(pag + 1) * 50]]
    return jsonify({"canal": slug, "total": total, "pag": pag, "items": items})

@app.route("/api/historial")
def historial():
    import datetime
    hist_path = pathlib.Path.home() / "youtube-knowledge/knowledge/historial.json"
    try: hist = json.loads(hist_path.read_text()) if hist_path.exists() else []
    except: hist = []
    return jsonify(hist[-288:])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8002)
