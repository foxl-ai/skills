#!/bin/bash
# Search photos by date range
START_DATE="$1"
END_DATE="${2:-$(date '+%Y-%m-%d %H:%M')}"
LIMIT="${3:-10}"
if [ -z "$START_DATE" ]; then
    echo "Usage: photos-search-date.sh <start_date> [end_date] [limit]" >&2
    exit 1
fi
PHOTOS_DB=~/Pictures/Photos\ Library.photoslibrary/database/Photos.sqlite
if [ ! -f "$PHOTOS_DB" ]; then
    echo "Error: Photos database not found" >&2
    exit 1
fi
start_unix=$(date -j -f "%Y-%m-%d %H:%M" "$START_DATE 00:00" "+%s" 2>/dev/null || date -j -f "%Y-%m-%d %H:%M" "$START_DATE" "+%s" 2>/dev/null)
end_unix=$(date -j -f "%Y-%m-%d %H:%M" "$END_DATE 23:59" "+%s" 2>/dev/null || date -j -f "%Y-%m-%d %H:%M" "$END_DATE" "+%s" 2>/dev/null)
if [ -z "$start_unix" ] || [ -z "$end_unix" ]; then
    echo "Error: Invalid date format" >&2
    exit 1
fi
start_apple=$((start_unix - 978307200))
end_apple=$((end_unix - 978307200))
sqlite3 "$PHOTOS_DB" "
SELECT ZFILENAME, datetime(ZDATECREATED + 978307200, 'unixepoch', 'localtime'),
    CASE ZUNIFORMTYPEIDENTIFIER
        WHEN 'public.heic' THEN 'HEIC' WHEN 'public.jpeg' THEN 'JPEG'
        WHEN 'public.png' THEN 'PNG' WHEN 'com.apple.quicktime-movie' THEN 'VIDEO'
        ELSE ZUNIFORMTYPEIDENTIFIER END, ZUUID
FROM ZASSET WHERE ZTRASHEDSTATE = 0 AND ZFILENAME IS NOT NULL
    AND ZDATECREATED >= $start_apple AND ZDATECREATED <= $end_apple
ORDER BY ZDATECREATED DESC LIMIT $LIMIT;
" 2>/dev/null | while IFS='|' read -r filename date type uuid; do
    echo "$filename | $date | $type | $uuid"
done
result_count=$(sqlite3 "$PHOTOS_DB" "
SELECT COUNT(*) FROM ZASSET WHERE ZTRASHEDSTATE = 0 AND ZFILENAME IS NOT NULL
    AND ZDATECREATED >= $start_apple AND ZDATECREATED <= $end_apple;
" 2>/dev/null)
if [ "$result_count" -eq 0 ]; then
    echo "No photos found in date range"
fi
