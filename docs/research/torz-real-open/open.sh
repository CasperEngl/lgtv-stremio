#!/bin/sh
# One open of a chosen StremThru Torz link, redirect-following off, body discarded. Prints a
# scrubbed record; the raw headers stay in the private run directory.
# Usage: open.sh <label> <listing.txt> <first 8 characters of the torrent hash> [extra curl args...]
# The first open of an uncached stream starts a download on the debrid account.
set -u
RUN=${RUN:-/tmp/t56/run}
label=$1; list=$2; hash=$3; shift 3
url=$(grep -oE 'https?://[^ ]+/stremio/torz/[^ ]+' "$list" | grep -F "/rd/$hash" || true)
[ -n "$url" ] && [ "$(printf '%s\n' "$url" | wc -l)" = 1 ] || { echo "expected exactly one link for $hash"; exit 2; }
start=$(date -u +%FT%TZ)
w=$(curl -sS --max-time 90 -D "$RUN/$label.headers" -o /dev/null \
  -w 'http=%{http_code} body_bytes=%{size_download} seconds=%{time_total}' "$@" "$url" 2>"$RUN/$label.err"); rc=$?
echo "## $label hash=$hash start=$start curl_exit=$rc $w"
[ -s "$RUN/$label.err" ] && sed -E 's#https?://[^ ]+#<scrubbed>#g' "$RUN/$label.err"
# A clip's address is public and kept whole. Any other address keeps its host and, on the
# instance's own host, its first two path segments; the rest can carry a token.
tr -d '\r' < "$RUN/$label.headers" | grep -Eiv '^(report-to|nel|cf-ray|set-cookie|alt-svc|server-timing):' | sed -E \
  -e '/^[Ll]ocation: https?:\/\/[^\/]+\/v0\/store\/_\/static\/[A-Za-z0-9_]+\.mp4$/b' \
  -e 's#^([Ll]ocation: https?://stremthru\.[^/]+/[^/]+/[^/]+)/.*#\1/<scrubbed>#' \
  -e 't' \
  -e 's#^([Ll]ocation: https?://[^/]+)/.*#\1/<scrubbed>#'
