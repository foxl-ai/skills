#!/usr/bin/env python3
"""
Validate a skill folder against the frontmatter rules Foxl's skill loader uses.

Foxl reads SKILL.md frontmatter with a simple line parser (one `key: value` per
line, surrounding quotes stripped, `[a, b]` read as a list), so this checks the
file the same way rather than as full YAML. Standard library only.

Usage: python3 quick_validate.py <skill_directory>
Exit 0 when valid; 1 with a message otherwise. Warnings do not fail.
"""

import re
import sys
from pathlib import Path

KNOWN_KEYS = {
    # Read by Foxl
    'name', 'description', 'enabled', 'tags', 'requires', 'requiresAny',
    'platforms', 'version', 'author', 'always', 'provides_tools',
    # Accepted by other agent runtimes (Claude Code, Agent Skills spec); Foxl ignores them
    'license', 'allowed-tools', 'metadata', 'compatibility',
}
IGNORED_KEYS = {'trigger', 'schedule'}
PLATFORMS = {'darwin', 'linux', 'win32'}


def strip_quotes(value):
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        return value[1:-1]
    return value


def parse_frontmatter(text):
    text = text.replace('\r\n', '\n')
    match = re.match(r'^---\n([\s\S]*?)\n---\n', text)
    if not match:
        return None
    fields = {}
    for line in match.group(1).split('\n'):
        if not line.strip() or line.lstrip().startswith('#') or line[0] in ' \t':
            continue
        if ':' not in line:
            continue
        key, raw = line.split(':', 1)
        fields[key.strip()] = raw.strip()
    return fields


def validate_skill(skill_path):
    skill_path = Path(skill_path)
    skill_md = skill_path / 'SKILL.md'
    if not skill_md.exists():
        return False, 'SKILL.md not found', []

    content = skill_md.read_text(encoding='utf-8')
    fields = parse_frontmatter(content)
    if fields is None:
        return False, "No frontmatter: the file must start with '---', a line per field, then '---'", []

    warnings = []
    for key in fields:
        if key in IGNORED_KEYS:
            warnings.append(f"'{key}' is ignored by Foxl; remove it (use the Schedules page for recurring runs)")
        elif key not in KNOWN_KEYS:
            warnings.append(f"Unknown key '{key}' (Foxl keeps it but does not use it)")

    name = strip_quotes(fields.get('name', ''))
    if not name:
        return False, "Missing 'name'", warnings
    if not re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', name) or len(name) > 64:
        return False, f"Name '{name}' should be kebab-case (a-z, 0-9, single hyphens), at most 64 characters", warnings
    if name != skill_path.name:
        warnings.append(f"Name '{name}' differs from the folder name '{skill_path.name}'")

    raw_desc = fields.get('description', '')
    if raw_desc in ('>', '|', '>-', '|-'):
        warnings.append('Description is a block scalar; Foxl reads it, but a single line is safer for other parsers')
    else:
        if '\\"' in raw_desc:
            return False, "Description contains '\\\"'; the line parser does not unescape it. Use single quotes inside", warnings
        desc = strip_quotes(raw_desc)
        if not desc:
            return False, "Missing 'description' (it must be on the same line as 'description:')", warnings
        if desc in ('true', 'false') or re.match(r'^-?\d+(\.\d+)?$', desc):
            return False, 'Description must be text', warnings
        if len(desc) > 1024:
            return False, f'Description is {len(desc)} characters; keep it under 1024 (it is in every prompt)', warnings
        if len(desc) > 400:
            warnings.append(f'Description is {len(desc)} characters; shorter is cheaper (it is in every prompt)')
        if ': ' in raw_desc and not (raw_desc.startswith('"') or raw_desc.startswith("'")):
            warnings.append("Description contains ': '; wrap it in double quotes for YAML-based tools")

    enabled = fields.get('enabled')
    if enabled is not None and enabled not in ('true', 'false'):
        return False, f"'enabled' must be true or false, got '{enabled}'", warnings

    platforms = fields.get('platforms')
    if platforms:
        items = [strip_quotes(p.strip()) for p in platforms.strip('[]').split(',') if p.strip()]
        bad = [p for p in items if p not in PLATFORMS]
        if bad:
            return False, f"Unknown platform(s) {bad}; use darwin, linux, win32", warnings

    requires = fields.get('requires')
    if requires and not (requires.startswith('[') and requires.endswith(']')):
        warnings.append("'requires' should be an inline list, for example [jq, MY_API_TOKEN]")

    return True, 'Skill is valid', warnings


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python3 quick_validate.py <skill_directory>')
        sys.exit(1)
    valid, message, warnings = validate_skill(sys.argv[1])
    for warning in warnings:
        print(f'warning: {warning}')
    print(message)
    sys.exit(0 if valid else 1)
