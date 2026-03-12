---
name: local-places
description: Search for places via local Google Places API proxy
trigger: manual
requires: [uv, GOOGLE_PLACES_API_KEY]
---

# Local Places

Search for nearby places using a local Google Places API proxy.

## Setup

```bash
echo "GOOGLE_PLACES_API_KEY=your-key" > .env
uv venv && uv pip install -e ".[dev]"
uv run --env-file .env uvicorn local_places.main:app --host 127.0.0.1 --port 8000
```

## Resolve Location

```bash
curl -X POST http://127.0.0.1:8000/locations/resolve \
  -H "Content-Type: application/json" \
  -d '{"location_text": "Soho, London", "limit": 5}'
```

## Search Places

```bash
curl -X POST http://127.0.0.1:8000/places/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "coffee shop",
    "location_bias": {"lat": 51.5137, "lng": -0.1366, "radius_m": 1000},
    "filters": {"open_now": true, "min_rating": 4.0},
    "limit": 10
  }'
```

## Get Details

```bash
curl http://127.0.0.1:8000/places/{place_id}
```

## Filter Options

- `filters.types`: ONE type (restaurant, cafe, gym)
- `filters.price_levels`: 0-4
- `filters.min_rating`: 0-5
- `filters.open_now`: boolean
- `limit`: 1-20
