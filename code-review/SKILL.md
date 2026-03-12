---
name: "Code Review"
description: "Automated code review for pull requests"
trigger: webhook
webhookPath: "/webhook/code-review"
enabled: false
tags: development, code, review
---

# Code Review Skill

## When to use
- When a pull request is opened
- When code changes are pushed
- When user requests a code review

## How to execute
1. Fetch the diff or changed files
2. Analyze code for:
   - Syntax errors
   - Style violations
   - Security issues
   - Performance concerns
   - Best practice violations
3. Generate review comments
4. Suggest improvements

## Review Criteria
- Code readability
- Error handling
- Test coverage
- Documentation
- Security best practices
