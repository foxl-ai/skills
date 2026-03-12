#!/bin/bash
# List all albums
osascript -e '
tell application "Photos"
    set output to ""
    repeat with a in albums
        set albumName to name of a
        set photoCount to count of media items of a
        set output to output & albumName & " | " & photoCount & "\n"
    end repeat
    return output
end tell
' 2>/dev/null | sed '/^$/d'
