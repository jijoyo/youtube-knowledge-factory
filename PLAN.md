# Plan: YouTube Knowledge Factory — Skill para Agensi

> **Fecha:** 2026-10-29
> **Autor:** Opencode-lab
> **Estado:** ✅ Completado (subido, screenshots puestos, precio pendiente)
> **Fuente:** /home/israel/Descargas/agente-youtube-factory-pack/

---

## Objetivo

Empaquetar youtube-knowledge como skill vendible en Agensi sin violar copyright.

**Qué vendemos:** El SISTEMA completo (radar + srt2md + dashboard + yt-ask)
**Qué NO vendemos:** Los 7,301 .md de la hemeroteca (privados)
**Precio:** $9.99 one-time (cambio manual en UI de Agensi)

---

## Veredicto Legal

| Opción | Estado | Razón |
|--------|--------|-------|
| A: Hemeroteca con 7,301 .md | ❌ ILEGAL | Viola Agensi 6.3 + copyright YouTube |
| **B: Tool (radar + dashboard + srt2md)** | ✅ **LEGAL** | Vendés tool como yt-dlp, no contenido |
| C: API con .md de terceros | ❌ ILEGAL | Mismo problema que A |

**Regla:** Solo vendemos código. Los .md de la hemeroteca quedan privados.

---

## Estructura del ZIP

```
youtube-knowledge-factory/
├── SKILL.md              ← Template 03-SKILL-TEMPLATE.md
├── README.md             ← Producto $9.99 (no fix técnico)
├── bin/
│   └── yt-radar.sh       ← Radar secuencial con anti-baneo
├── app/
│   └── server.py         ← Server :8002 + API
├── lib/
│   └── canales.sh        ← Canales de ejemplo (usar los que quieras)
├── dashboard.html        ← UI de progreso
├── srt2md.py             ← Conversor srt → md
├── yt-ask                ← Query hemeroteca como RAG
├── references/
│   └── USAGE.md          ← Guía de instalación
└── logo-512.png          ← Logo original (no YouTube logo)
```

### EXCLUIR SIEMPRE:
- ❌ knowledge/videos/ (7,301 .md)
- ❌ knowledge/index.json
- ❌ *.srt, *.log, .env
- ❌ paths /home/israel/
- ❌ API keys

### INCLUIR:
- ✅canales.sh con canales de ejemplo (comentar que son para probar, el buyer usa los que quiera)
- ✅ Disclaimer legal en SKILL.md y README.md
- ✅ Nota: Shorts, videos privados y de miembros no se descargan (razones obvias de YouTube)
- ✅ Logo 512x512 PNG (original, no logo YouTube)
- ✅ 3 screenshots: dashboard-empty.png, dashboard-progress.png, yt-ask-demo.png (sin texto de terceros, solo UI)

---

## Pasos de ejecución

### Paso 1: Leer archivos fuente
- `lib/canales.sh` → canales de ejemplo (para probar, el buyer usa los que quiera)
- `bin/yt-radar.sh` → radar secuencial
- `app/server.py` → server + API
- `dashboard.html` → UI
- `srt2md.py` → conversor
- `yt-ask` → script de query

### Paso 2: Limpiar archivos
- Eliminar paths `/home/israel/` de todos los archivos
- Eliminar API keys, env vars
- canales.sh con canales de ejemplo (comentar que son para probar, el buyer usa los que quiera)
- Añadir nota: "Shorts, videos privados y de miembros no se descargan"
- Añadir comentarios "DEMO CHANNELS — ejemplo para testing"

### Paso 3: Crear estructura
```bash
mkdir -p /home/israel/Documentos/opencode-lab/fixes/youtube-knowledge-factory/
mkdir -p /home/israel/Documentos/opencode-lab/fixes/youtube-knowledge-factory/{bin,app,lib,references}
```

### Paso 4: Copiar archivos
- Copiar yt-radar.sh, server.py, dashboard.html, srt2md.py, yt-ask
- Copiar canales.sh (limpiado a 3 canales)
- Crear SKILL.md desde template
- Crear README.md como producto
- Crear references/USAGE.md

### Paso 5: Crear logo + screenshots
- Logo 512x512 (no usar YouTube logo)
- 3 screenshots:
  - dashboard-empty.png (UI sin datos)
  - dashboard-progress.png (UI con progreso)
  - yt-ask-demo.png (UI de query)

### Paso 6: Validar checklist
- [ ] ZIP no contiene knowledge/videos/*.md
- [ ] ZIP no contiene index.json
- [ ] canales.sh solo 3 canales demo
- [ ] SKILL.md tiene disclaimer "Does NOT include transcripts"
- [ ] README.md es producto, no fix técnico
- [ ] Logo 512x512 PNG
- [ ] 3 screenshots de UI vacía
- [ ] Precio $9.99 (cambio manual)
- [ ] Licencia MIT en SKILL.md
- [ ] Sin paths /home/israel/
- [ ] Sanitizado: sin .env, sin API keys

### Paso 7: Crear ZIP
```bash
cd /home/israel/Documentos/opencode-lab/fixes/youtube-knowledge-factory/
zip -r /tmp/opencode/youtube-knowledge-factory.zip .
```

### Paso 8: Subir a Agensi
- Ir a `agensi.io/dashboard/submit`
- Upload ZIP
- Precio manual: $9.99 (NO vía MCP tools — no funciona)
- Submit for review

---

## Archivos de referencia

| Archivo | Ruta | Para qué |
|---------|------|----------|
| 00-LEE-ESTO-AGENTE.md | `/home/israel/Descargas/agente-youtube-factory-pack/00-LEE-ESTO-AGENTE.md` | Contexto y fuentes |
| 01-VEREDICTO-LEGAL.md | `/home/israel/Descargas/agente-youtube-factory-pack/01-VEREDICTO-LEGAL.md` | Legalidad |
| 02-ESTRUCTURA-ZIP.md | `/home/israel/Descargas/agente-youtube-factory-pack/02-ESTRUCTURA-ZIP.md` | Estructura del ZIP |
| 03-SKILL-TEMPLATE.md | `/home/israel/Descargas/agente-youtube-factory-pack/03-SKILL-TEMPLATE.md` | SKILL.md template |
| 04-README-PRODUCTO.md | `/home/israel/Descargas/agente-youtube-factory-pack/04-README-PRODUCTO.md` | README como producto |
| 05-CHECKLIST-AGENSI.md | `/home/israel/Descargas/agente-youtube-factory-pack/05-CHECKLIST-AGENSI.md` | Checklist de Agensi |
| 06-FORMULA-7.md | `/home/israel/Descargas/agente-youtube-factory-pack/06-FORMULA-7-HEMEROTECA-TO-SKILL-FACTORY.md` | Fórmula 7 (privada) |
| 07-PARA-EL-AGENTE-TODO.md | `/home/israel/Descargas/agente-youtube-factory-pack/07-PARA-EL-AGENTE-TODO.md` | TODO concreto |

---

## Lecciones post-mortem (previsibles)

1. **El price_usd/price_cents no funciona vía API** — se cambia manual en UI
2. **El dashboard form resetea el precio** — hay que usar submit initial
3. **Los 7,301 .md NO van al ZIP** — son privados, no vendemos contenido
4. **yt-ask puede ser .sh o .py** — verificar qué tenemos
5. **Logo no puede ser YouTube logo** — debe ser original

---

## Dependencias externas

- `yt-dlp` (instalado por el buyer)
- `python3` (instalado por el buyer)
- `deno` (para challenge de YouTube, opcional)
- **NO requiere:** Node.js, npm, pip packages

---

## Timeline estimado

| Paso | Tiempo |
|------|--------|
| Leer archivos | 10 min |
| Limpiar archivos | 15 min |
| Crear estructura + copiar | 15 min |
| Crear SKILL.md + README + USAGE | 20 min |
| Logo + screenshots | 15 min |
| Validar checklist | 5 min |
| Crear ZIP | 2 min |
| Subir a Agensi | 10 min |
| **TOTAL** | **~1h 30 min** |

---

## GATE

> **¿Autorizado para ejecutar este plan?**
> 
> Se requiere confirmación explícita del usuario antes de proceder.
