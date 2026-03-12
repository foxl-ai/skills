---
name: blogwatcher
description: Monitor blogs and RSS/Atom feeds for updates
trigger: manual
requires: [blogwatcher]
---

# blogwatcher

Track blog and RSS/Atom feed updates.

## Setup

```bash
go install github.com/Hyaxia/blogwatcher/cmd/blogwatcher@latest
```

## Commands

```bash
# Add a blog
blogwatcher add "My Blog" https://example.com

# List tracked blogs
blogwatcher blogs

# Scan for updates
blogwatcher scan

# List articles
blogwatcher articles

# Mark article read
blogwatcher read 1

# Mark all read
blogwatcher read-all

# Remove a blog
blogwatcher remove "My Blog"
```

## Example

```bash
$ blogwatcher scan
Scanning 1 blog(s)...

  xkcd
    Source: RSS | Found: 4 | New: 4

Found 4 new article(s) total!
```
