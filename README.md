# YouTube Knowledge Factory — Build Your Own Hemeroteca

**No more 200h of videos you can't watch.**

This is the TOOL to automatically capture subtitles from ALL videos of your favorite YouTube channels and convert them to clean markdown for RAG. Without watching a single video.

## What you get

- **Radar:** automatic capture 1 channel → 1 video sequentially with anti-ban (sleeps, IPv4, breaker x3, lock, blocklist)
- **srt2md:** srt → md with YAML frontmatter, no timestamps, dedup
- **Dashboard :8002:** live progress per channel, search, explorer
- **yt-ask:** ask your hemeroteca like local RAG — "What did X say about Y?"
- **Cron + backup:** automatic, without touching terminal

## How it works

```
YouTube → Radar (subs only) → srt2md (.md) → Dashboard :8002 → yt-ask (RAG)
```

1. Add your channels in `lib/canales.sh`
2. Run `bash bin/yt-radar.sh` (one channel, one video at a time)
3. Dashboard shows progress live at `http://localhost:8002`
4. Ask questions with `bash yt-ask "what about X?"`

## Demo channels

Includes 3 demo channels in `lib/canales.sh` (mouredev, atareao, nichonauta) for testing. Replace them with your own channels.

## Requirements

- `python3`
- `yt-dlp` (install: `pip install yt-dlp`)
- `deno` (optional, for YouTube challenge solving)

**Does NOT require:** Node.js, npm, pip packages.

## Installation (5 min)

```bash
# 1. Extract the ZIP
unzip youtube-knowledge-factory.zip

# 2. Install yt-dlp
pip install yt-dlp

# 3. Add your channels to lib/canales.sh
# Format: [channel-name]=" @handle es 01-nicho/channel-name"

# 4. Start the dashboard
python3 app/server.py

# 5. Open dashboard
open http://localhost:8002

# 6. Run the radar (one channel at a time)
bash bin/yt-radar.sh [channel-name]

# Or capture all channels
bash bin/yt-radar.sh --all
```

## Notes

- **Shorts, private videos, and members-only videos cannot be downloaded** (obvious YouTube reasons)
- The radar captures **subtitles only** — no video files (0 MB per video)
- Each video takes ~15 seconds with anti-ban (sleeps between videos)
- Shorts are excluded by design (no subtitles)

## What is NOT included

This skill contains **only code**. No transcripts, no subtitles, no video data. You capture your own channels with your own means for personal study. User responsible for YouTube ToS compliance.

## License

MIT. Use for personal study.

## Tested with

27 channels, 7,301+ videos (privately, not included). Anti-ban tested with rate-limits, 429 errors, and session degradation.
