#!/bin/sh
# Re-list the title with the command-line prototype (opens no stream link) and print how
# StremThru Torz marks one stream. Usage: marking.sh <type> <id> <first 8 characters of the hash>
set -u
BIN=${BIN:-/tmp/t56-target/release/lgtv-stremio}; RUN=${RUN:-/tmp/t56/run}
"$BIN" streams "$1" "$2" --urls > "$RUN/mark.txt" 2>/dev/null
line=$(grep -F "/rd/$3" "$RUN/mark.txt" | grep -F '/stremio/torz/' | sed -E 's#https?://([^/ ]+)/[^ ]*#\1/<scrubbed>#')
case $line in *"· cached") m=cached;; "") m="not listed";; *) m="not cached";; esac
echo "## mark at=$(date -u +%FT%TZ) hash=$3 marking=$m torz_streams=$(grep -c '/stremio/torz/' "$RUN/mark.txt")"
