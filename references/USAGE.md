# Usage Guide — YouTube Knowledge Factory

## Quick Start

```bash
# 1. Extract the ZIP
unzip youtube-knowledge-factory.zip
cd youtube-knowledge-factory

# 2. Install yt-dlp
pip install yt-dlp

# 3. Start the dashboard
python3 app/server.py &

# 4. Open dashboard in browser
# http://localhost:8002

# 5. Run the radar
bash bin/yt-radar.sh [channel-name]
# Or: bash bin/yt-radar.sh --all

# 6. Ask questions
bash yt-ask "what about Rust async?"
```

## Adding Your Channels

Edit `lib/canales.sh`:

```bash
# Format: [channel-name]=" @handle idioma ruta/"
[mi-canal]=" @handle es 01-nicho/mi-canal"
[otro-canal]=" @handle en 02-programacion/otro-canal"
```

Then add to `CANAL_ORDEN`:
```bash
CANAL_ORDEN=(mi-canal otro-canal ...)
```

## Understanding the Output

Each video becomes a `.md` file in:
```
youtube-knowledge/knowledge/videos/[nicho]/[channel]/[date] - [title].[video-id].md
```

Each `.md` has YAML frontmatter:
```yaml
---
title: "Video Title"
channel: "Channel Name"
date: 2026-10-29
url: https://www.youtube.com/watch?v=VIDEO_ID
thumbnail: https://i.ytimg.com/vi/VIDEO_ID/hqdefault.jpg
---

[Clean transcript text]
```

## Dashboard Endpoints

| Endpoint | What it does |
|----------|-------------|
| `/api/progreso` | Live progress per channel |
| `/api/radar/start` | Start the radar |
| `/api/radar/stop` | Stop the radar |
| `/api/canal/check` | Check a specific channel |
| `/api/buscar?q=term` | Search in transcripts |

## Cron Setup (optional)

```bash
# Run radar daily at 12:00
crontab -e
0 12 * * * cd ~/youtube-knowledge && bash bin/yt-radar.sh >> /tmp/yt-radar.log 2>&1
```

## Troubleshooting

- **YouTube rate-limited:** The radar stops automatically after 3 consecutive rate-limits. Wait 12-24h and resume.
- **No subtitles:** Some videos don't have subtitles. They are skipped with cause in blocklist.
- **IPv6 issues:** The radar forces IPv4 by default (`--force-ipv4`).
- **Deno not found:** Install Deno for challenge solving: `brew install deno` (macOS) or download from deno.land.

## License

MIT. For personal study only.
