---
name: "Morning Briefing"
description: "Daily morning briefing with calendar, tasks, and weather"
enabled: true
trigger: cron
schedule: "0 7 * * *"
tags: daily, briefing, productivity
---

# Morning Briefing Skill

## When to use
- Every day at 7:00 AM
- When user asks for a morning briefing

## How to execute
1. Check calendar for today's events
2. List incomplete tasks from yesterday
3. Check weather forecast for the day
4. Summarize any important notifications
5. Send briefing via configured channel

## Output Format
- Start with a greeting based on time of day
- List events in chronological order
- Highlight urgent tasks
- Include weather summary
- End with motivational note