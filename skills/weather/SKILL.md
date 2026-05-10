---
name: weather
description: Get current weather and forecasts using free services (no API key required)
enabled: true
---

# Weather Skill

Get weather information using free services.

## When to use
- User asks about weather
- User asks about forecast
- Morning briefing needs weather info

## How to execute

### wttr.in (Primary - No API key needed)

Quick one-liner:
```bash
curl -s "wttr.in/Seoul?format=3"
# Output: Seoul: ⛅️ +8°C
```

Compact format:
```bash
curl -s "wttr.in/Seoul?format=%l:+%c+%t+%h+%w"
# Output: Seoul: ⛅️ +8°C 71% ↙5km/h
```

Full forecast:
```bash
curl -s "wttr.in/Seoul?T"
```

Format codes:
- `%c` condition
- `%t` temperature
- `%h` humidity
- `%w` wind
- `%l` location
- `%m` moon phase

Tips:
- URL-encode spaces: `wttr.in/New+York`
- Airport codes: `wttr.in/ICN`
- Units: `?m` (metric) `?u` (USCS)
- Today only: `?1`
- Current only: `?0`

### Open-Meteo (Fallback - JSON API)

```bash
curl -s "https://api.open-meteo.com/v1/forecast?latitude=37.5665&longitude=126.9780&current_weather=true"
```

Returns JSON with temp, windspeed, weathercode.
