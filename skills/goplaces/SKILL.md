---
name: goplaces
description: Query Google Places API for text search, details, and reviews
trigger: manual
requires: [goplaces, GOOGLE_PLACES_API_KEY]
---

# goplaces

Modern Google Places API (New) CLI.

## Setup

```bash
brew install steipete/tap/goplaces
export GOOGLE_PLACES_API_KEY="your-key"
```

## Search

```bash
goplaces search "coffee" --open-now --min-rating 4 --limit 5
goplaces search "pizza" --lat 40.8 --lng -73.9 --radius-m 3000
goplaces search "sushi" --json
```

## Pagination

```bash
goplaces search "pizza" --page-token "NEXT_PAGE_TOKEN"
```

## Resolve Location

```bash
goplaces resolve "Soho, London" --limit 5
```

## Place Details

```bash
goplaces details <place_id>
goplaces details <place_id> --reviews
```

## Output

- Human-readable by default
- `--json` for scripts
- `--no-color` or `NO_COLOR` disables ANSI

## Notes

- Price levels: 0 (free) to 4 (very expensive)
- Type filter accepts only one `--type` value
