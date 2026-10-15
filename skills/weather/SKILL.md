---
name: weather
description: "Current weather and multi-day forecasts for any city or coordinates via free no-key services (wttr.in for a quick line, Open-Meteo for structured JSON). Use when the user asks about weather, temperature, rain or a forecast, or a briefing needs it."
enabled: true
tags: weather, forecast, briefing
---

# Weather

Both services are free and need no API key. Use `curl` (on Windows PowerShell call
`curl.exe`, not the `curl` alias). Answer in the user's units: wttr.in picks units by
the caller's IP, so force them with `m` (metric) or `u` (US).

## Quick answer: wttr.in

```bash
curl -s "https://wttr.in/Seoul?format=3&m"
curl -s "https://wttr.in/New+York?format=%l:+%C+%t+(feels+%f)+%h+%w&u"
```

- Location: city (`New+York`), airport code (`ICN`), `~Eiffel+Tower`, or `lat,lon`.
- Codes: `%C` condition text, `%t` temp, `%f` feels like, `%h` humidity, `%w` wind,
  `%p` precipitation, `%u` UV, `%S`/`%s` sunrise/sunset, `%l` location.
- Forecast as JSON (3 days): `?format=j1`. Text view: `?0` now, `?1` today, `?2` +tomorrow,
  add `T` for no colors (e.g. `?2Tq&m`).
- Language for the text views: `&lang=ko`. Fallback domain if wttr.in is down: `wttr.is`.

## Structured forecast: Open-Meteo

Look up coordinates, then fetch the forecast (`timezone=auto` gives local times):

```bash
curl -s "https://geocoding-api.open-meteo.com/v1/search?name=Seoul&count=1"
curl -s "https://api.open-meteo.com/v1/forecast?latitude=37.566&longitude=126.978&current=temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,weather_code,wind_speed_10m&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=auto&forecast_days=3"
```

- Units: add `&temperature_unit=fahrenheit&wind_speed_unit=mph` for US users.
- Hourly: `&hourly=temperature_2m,precipitation_probability`. Up to 16 days via `forecast_days`.
- `weather_code` is WMO: 0 clear, 1-3 partly cloudy to overcast, 45/48 fog,
  51-57 drizzle, 61-67 rain, 71-77 snow, 80-82 showers, 85/86 snow showers,
  95-99 thunderstorm.
- Docs: https://open-meteo.com/en/docs (free for non-commercial use).

Give the answer in plain words (condition, temperature, rain chance), not raw JSON.
