#!/usr/bin/env python3
"""srt2md.py — convierte 1 .srt (con o sin cabecera # TITLE/CHANNEL/DATE/URL/THUMBNAIL/DESC) a 1 .md limpio para RAG.
Uso: python3 srt2md.py entrada.srt salida.md
- Quita timestamps, números de bloque y líneas duplicadas consecutivas (típico de auto-subs)
- Si hay cabecera, la usa para frontmatter + thumbnail online (no baja imagen)
"""
import re, sys, pathlib

def srt_to_clean(srt_text):
    lines = srt_text.splitlines()
    out = []
    prev = ""
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if re.match(r'^\d+$', line):
            continue
        if re.match(r'^\d{2}:\d{2}:\d{2}', line):
            continue
        if line.startswith('#'):
            continue
        if line == prev:  # dedup consecutivos de auto-subs
            continue
        prev = line
        out.append(line)
    text = ' '.join(out)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

if len(sys.argv) < 3:
    print("uso: srt2md.py entrada.srt salida.md")
    sys.exit(1)

srt_path = pathlib.Path(sys.argv[1])
md_path = pathlib.Path(sys.argv[2])

srt = srt_path.read_text(encoding='utf-8', errors='ignore')
header_lines = [l for l in srt.splitlines() if l.startswith('#')]
clean = srt_to_clean(srt)

def get(field):
    for l in header_lines:
        if l.startswith(f'# {field}:'):
            return l.split(':', 1)[1].strip()
    return ''

title = get('TITLE') or srt_path.stem
channel = get('CHANNEL') or ''
date = get('DATE') or ''
url = get('URL') or ''
thumb = get('THUMBNAIL') or ''
desc = get('DESC') or ''

md = f"""---
title: "{title}"
channel: "{channel}"
date: {date}
url: {url}
thumbnail: {thumb}
---

# {title}

![thumbnail]({thumb})

**Canal:** {channel} | **Fecha:** {date} | **URL:** {url}

> {desc}

---

{clean}
"""
md_path.write_text(md, encoding='utf-8')
print(f"✓ {md_path.name} ({len(clean)} chars)")
