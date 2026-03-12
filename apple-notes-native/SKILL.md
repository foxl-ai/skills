---
name: apple-notes-native
description: Manage Apple Notes using native AppleScript (no CLI required)
trigger: manual
platforms: [darwin]
enabled: true
---

# Apple Notes (Native AppleScript)

Manage Apple Notes directly using osascript on macOS.

## When to use
- User wants to create a note in Apple Notes
- User wants to read notes
- User wants to search notes
- User mentions "Apple Notes", "notes", "memo"

## How to execute

### Create a New Note

Use the `bash` tool to run this AppleScript:

```bash
osascript -e 'tell application "Notes"
  set newNote to make new note at folder "Notes"
  set body of newNote to "YOUR_NOTE_CONTENT_HERE"
  return id of newNote
end tell'
```

Replace `YOUR_NOTE_CONTENT_HERE` with the actual content.

### Create Note with Title

```bash
osascript -e 'tell application "Notes"
  set newNote to make new note at folder "Notes"
  set body of newNote to "<h1>TITLE_HERE</h1><br>CONTENT_HERE"
  return "Note created"
end tell'
```

### List Recent Notes

```bash
osascript -e 'tell application "Notes"
  set noteList to ""
  repeat with n in (notes of folder "Notes")
    set noteList to noteList & name of n & "\n"
  end repeat
  return noteList
end tell' | head -10
```

### Search Notes

```bash
osascript -e 'tell application "Notes"
  set results to ""
  repeat with n in (notes of folder "Notes")
    if name of n contains "SEARCH_TERM" then
      set results to results & name of n & "\n"
    end if
  end repeat
  return results
end tell'
```

### Read a Note by Name

```bash
osascript -e 'tell application "Notes"
  repeat with n in (notes of folder "Notes")
    if name of n contains "NOTE_NAME" then
      return plaintext of n
    end if
  end repeat
  return "Note not found"
end tell'
```

## Important Notes
- Notes app must have proper permissions
- First run may prompt for Automation permission
- HTML tags in body create formatting (h1 for title, br for line break)
