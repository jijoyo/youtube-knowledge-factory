---
name: youtube-knowledge-factory
displayName: YouTube Knowledge Factory
description: Use when you want to build your own YouTube hemeroteca — capture channels, transcribe to clean MD, dashboard :8002, RAG yt-ask, automatic radar with anti-ban. Build your own knowledge factory without terminal.
summary: Captura subtítulos de TODOS los videos de tus canales favoritos y conviértelos en texto limpio para RAG. Sin ver un solo video.
version: 1.0.0
tags:
  - youtube
  - rag
  - hemeroteca
  - research
  - dashboard
  - transcription
  - factory
  - automation
use_cases:
  - Build a personal knowledge base from YouTube channels
  - Research without wasting time watching videos
  - Convert video content to RAG-ready markdown
docs_url: https://github.com/jijoyo/youtube-knowledge-factory
---

# YouTube Knowledge Factory

Build your own hemeroteca of YouTube channels. Capture subtitles from ALL videos of your favorite channels and convert them to clean markdown for RAG. Without watching a single video.

## What it does

- **Radar secuencial:** 1 channel → 1 video with sleeps, lock, blocklist with cause, breaker x3, IPv4 anti-ban
- **srt2md:** srt → clean md with YAML frontmatter (no timestamps, dedup)
- **Dashboard :8002** live (progress per channel, explorer, search)
- **yt-ask:** ask your hemeroteca like local RAG ("What did X say about Y?")
- **Cron daily + automatic backup**

## Use when

- You follow 10+ YouTube channels and don't have time to watch
- You want to research without losing time
- You need a personal knowledge base from channels you watch
- You want to capture entire channels automatically (anti-ban included)

## What it does NOT include

This skill does NOT include any video transcripts or subtitles. You build your own hemeroteca with channels you follow. The 3 demo channels in `lib/canales.sh` are for testing only — replace them with your own channels.

User responsible for YouTube ToS compliance. Shorts, private videos, and members-only videos cannot be downloaded (obvious YouTube reasons).

## Installation

See `README.md` for 5-minute setup.

## Components

- `bin/yt-radar.sh` — Automatic radar with anti-ban
- `app/server.py` — Server + API (:8002)
- `dashboard.html` — Live progress UI
- `srt2md.py` — Subtitle to markdown converter
- `yt-ask` — Query hemeroteca like RAG
- `lib/canales.sh` — Channel map (3 demo channels, replace with yours)

## Tested with

27 channels, 7,301+ videos privately (not included). Anti-ban tested with rate-limits, 429 errors, and session degradation.

## License

MIT. Use for personal study.
