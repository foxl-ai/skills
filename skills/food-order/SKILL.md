---
name: food-order
description: Reorder Foodora orders and track ETA/status
trigger: manual
requires: [ordercli]
---

# Food Order (Foodora)

Reorder previous Foodora orders safely.

## Safety Rules

- Never run `--confirm` unless user explicitly confirms
- Always preview first, then ask for confirmation
- If user is unsure, stop at preview

## Setup

```bash
go install github.com/steipete/ordercli/cmd/ordercli@latest

# Set country
ordercli foodora countries
ordercli foodora config set --country AT

# Login (browser session preferred)
ordercli foodora session chrome --url https://www.foodora.at/ --profile "Default"
```

## Find Orders

```bash
ordercli foodora history --limit 10
ordercli foodora history show <orderCode>
```

## Preview Reorder

```bash
ordercli foodora reorder <orderCode>
```

## Place Order (requires explicit confirmation)

```bash
ordercli foodora reorder <orderCode> --confirm
ordercli foodora reorder <orderCode> --confirm --address-id <id>
```

## Track Order

```bash
ordercli foodora orders              # Active orders
ordercli foodora orders --watch      # Live updates
ordercli foodora order <orderCode>   # Single order detail
```
