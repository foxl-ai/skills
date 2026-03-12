---
name: bird
description: X/Twitter CLI for reading, searching, posting, and engagement
trigger: manual
requires: [bird]
---

# bird (X/Twitter CLI)

Fast X/Twitter CLI using GraphQL + cookie auth.

## Setup

```bash
brew install steipete/tap/bird
# or
npm install -g @steipete/bird
```

Auth via cookies: `--auth-token`, `--ct0`, or `--cookie-source` for browser cookies.

## Reading

```bash
bird read <url-or-id>          # Single tweet
bird thread <url-or-id>        # Full conversation
bird replies <url-or-id>       # List replies
```

## Timelines

```bash
bird home                      # For You timeline
bird home --following          # Following timeline
bird user-tweets @handle -n 20 # User's tweets
bird mentions                  # Mentions
```

## Search

```bash
bird search "query" -n 10
bird search "from:user" --all --max-pages 3
```

## News & Trending

```bash
bird news -n 10
bird news --ai-only
bird trending
```

## Bookmarks & Likes

```bash
bird bookmarks -n 10
bird likes -n 10
bird unbookmark <url-or-id>
```

## Engagement

```bash
bird follow @handle
bird unfollow @handle
```

## Posting

```bash
bird tweet "hello world"
bird reply <url-or-id> "nice thread!"
bird tweet "check this" --media image.png --alt "description"
```

Warning: Posting is more likely to be rate limited.

## Output Options

- `--json` - JSON output
- `--plain` - No emoji, no color
- `--no-color` - Disable ANSI colors

## Config

`~/.config/bird/config.json5`:
```json5
{
  cookieSource: ["chrome"],
  chromeProfileDir: "/path/to/Profile",
}
```
