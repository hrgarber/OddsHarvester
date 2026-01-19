# Harrison's OddsHarvester Extensions

Custom additions to the OddsHarvester scraper for live odds polling.

## Live Odds Scraping (`scrape_live`)

New command for continuous polling of live/in-play odds from OddsPortal.

### Usage

```bash
# Basic - polls every 30s until Ctrl+C
uv run python src/main.py scrape_live --sport football --markets 1x2 --headless

# Custom interval, limited cycles
uv run python src/main.py scrape_live --sport football --markets 1x2,over_under_2_5 \
    --poll_interval 60 --max_cycles 10 --headless

# Overwrite mode (replace file each cycle instead of append)
uv run python src/main.py scrape_live --sport football --output_mode overwrite \
    --file_path live_odds.json --headless
```

### New CLI Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--poll_interval` | 30 | Seconds between scrape cycles (min: 10) |
| `--output_mode` | append | `append` adds to file, `overwrite` replaces |
| `--max_cycles` | None | Max polling cycles (None = infinite until Ctrl+C) |

### Output Schema

Each match includes live-specific fields:

```json
{
  "match_link": "https://www.oddsportal.com/football/england/premier-league/...",
  "home_team": "Aston Villa",
  "away_team": "Everton",
  "league_name": "Premier League",
  "home_score": "0",
  "away_score": "1",
  "partial_results": "0:0, 0:1",
  "1x2_market": [
    {"1": "41.00", "X": "4.00", "2": "1.25", "bookmaker_name": "bet365.us", "period": "FullTime"}
  ],
  "scrape_type": "live",
  "poll_cycle": 5,
  "match_status": "new"
}
```

### Sport Filtering

Live page shows all sports. Filtering happens by URL pattern:
- `--sport football` → only `/football/` URLs
- `--sport basketball` → only `/basketball/` URLs

The `_filter_links_by_sport()` method also supports league filtering for future UI use:
```python
# In odds_portal_scraper.py
filtered = self._filter_links_by_sport(links, sport="football", leagues=["england-premier-league"])
```

## Files Modified

| File | Change |
|------|--------|
| `src/utils/command_enum.py` | Added `LIVE = "scrape_live"` |
| `src/utils/output_mode_enum.py` | **New** - `APPEND`/`OVERWRITE` enum |
| `src/cli/cli_argument_parser.py` | Added `_add_live_parser()` |
| `src/cli/cli_argument_validator.py` | Added validation for live args |
| `src/cli/cli_argument_handler.py` | Added live args to return dict |
| `src/core/url_builder.py` | Added `get_live_matches_url()` |
| `src/core/odds_portal_scraper.py` | Added `scrape_live()`, `_filter_links_by_sport()` |
| `src/core/scraper_app.py` | Added `CommandEnum.LIVE` routing |
| `src/main.py` | Added `_run_live_scraper()` with callback storage |

## Technical Notes

- **URL**: OddsPortal live page is `/inplay-odds/` (no sport suffix)
- **Graceful shutdown**: Ctrl+C finishes current cycle before stopping
- **Signal handling**: SIGINT/SIGTERM caught and restored after scraping
- **Concurrency**: Uses existing concurrent scraping (default 3 tasks)
- **Rate limiting**: Min 10s poll interval enforced to avoid hammering

## Future Ideas

- WebSocket real-time updates (if OddsPortal exposes)
- Delta-only storage (only changed odds)
- Match completion detection via page parsing
- Multi-sport simultaneous scraping
- UI with league filtering dropdowns
