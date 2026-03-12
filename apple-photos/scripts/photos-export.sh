#!/bin/bash
# Export a photo from Photos library to a viewable format
UUID="$1"
OUTPUT="${2:-/tmp/photo_export.jpg}"
if [ -z "$UUID" ]; then
    echo "Usage: photos-export.sh <uuid> [output_path]" >&2
    exit 1
fi
PHOTOS_LIB=~/Pictures/Photos\ Library.photoslibrary
PHOTOS_DB="$PHOTOS_LIB/database/Photos.sqlite"
if [ ! -f "$PHOTOS_DB" ]; then
    echo "Error: Photos database not found" >&2
    exit 1
fi
read -r FILENAME DIRECTORY < <(sqlite3 "$PHOTOS_DB" "
SELECT ZFILENAME, ZDIRECTORY FROM ZASSET WHERE ZUUID = '$UUID' AND ZTRASHEDSTATE = 0 LIMIT 1;
" 2>/dev/null | tr '|' ' ')
if [ -z "$FILENAME" ]; then
    echo "Error: Photo with UUID '$UUID' not found" >&2
    exit 1
fi

# Try originals first
SOURCE=$(find "$PHOTOS_LIB/originals" -name "$FILENAME" 2>/dev/null | head -1)

# Fallback: derivatives/masters (iCloud optimized storage)
if [ -z "$SOURCE" ] || [ ! -f "$SOURCE" ]; then
    SOURCE=$(find "$PHOTOS_LIB/resources/derivatives/masters" -name "${UUID}*" 2>/dev/null | head -1)
fi

# Fallback: any derivatives
if [ -z "$SOURCE" ] || [ ! -f "$SOURCE" ]; then
    SOURCE=$(find "$PHOTOS_LIB/resources/derivatives" -name "${UUID}*" -not -name "*.dat" 2>/dev/null | head -1)
fi

if [ -z "$SOURCE" ] || [ ! -f "$SOURCE" ]; then
    echo "Error: No local file found for $FILENAME (may need to download from iCloud)" >&2
    exit 1
fi

# Determine extension from source file
EXT="${SOURCE##*.}"
EXT_LOWER=$(echo "$EXT" | tr '[:upper:]' '[:lower:]')
mkdir -p "$(dirname "$OUTPUT")"
HAS_MAGICK=false
if command -v magick >/dev/null 2>&1 || command -v convert >/dev/null 2>&1; then
    HAS_MAGICK=true
fi
if [[ "$EXT_LOWER" == "heic" || "$EXT_LOWER" == "heif" ]]; then
    if [ "$HAS_MAGICK" = true ]; then
        magick "$SOURCE" -auto-orient "$OUTPUT" 2>/dev/null || \
        convert "$SOURCE" -auto-orient "$OUTPUT" 2>/dev/null
    else
        sips -s format jpeg "$SOURCE" --out "$OUTPUT" >/dev/null 2>&1
    fi
elif [[ "$EXT_LOWER" == "png" || "$EXT_LOWER" == "jpg" || "$EXT_LOWER" == "jpeg" ]]; then
    if [ "$HAS_MAGICK" = true ]; then
        magick "$SOURCE" -auto-orient "$OUTPUT" 2>/dev/null || \
        convert "$SOURCE" -auto-orient "$OUTPUT" 2>/dev/null
    else
        cp "$SOURCE" "$OUTPUT"
    fi
else
    cp "$SOURCE" "$OUTPUT"
fi
echo "$OUTPUT"
