#!/bin/sh
# One open of the picked stream's link, redirects off. Prints a scrubbed record; raw headers and
# body stay in the run directory. Usage: open.sh <label> [extra curl args...]
set -u
RUN=/tmp/hsc/run; LIST=/tmp/hsc/tt0063350.json; HASH=4d5f74f5babcd7bf62b75acd8182370ca495dfa5
label=$1; shift
url=$(jq -r --arg h "$HASH" '.streams[]|select(.behaviorHints.bingeGroup|endswith($h))|.url' "$LIST")
[ "$(printf '%s\n' "$url" | wc -l)" = 1 ] && [ -n "$url" ] || { echo "expected exactly one link"; exit 2; }
start=$(date -u +%FT%TZ)
w=$(curl -sS -m 120 --max-filesize 5000000 -D "$RUN/$label.headers" -o "$RUN/$label.body" \
  -w 'http=%{http_code} body_bytes=%{size_download} seconds=%{time_total}' "$@" "$url" 2>"$RUN/$label.err"); rc=$?
echo "## $label start=$start curl_exit=$rc $w"
[ -s "$RUN/$label.err" ] && sed -E 's#https?://[^ ]+#<scrubbed>#g' "$RUN/$label.err"
tr -d '\r' < "$RUN/$label.headers" | sed -E 's#^([Ll]ocation: https?://[^/]+)/.*#\1/<scrubbed>#'
[ -f "$RUN/$label.body" ] && echo "body: $(wc -c < "$RUN/$label.body") bytes sha256=$(sha256sum "$RUN/$label.body" | cut -c1-64) type=$(file -b "$RUN/$label.body" | cut -c1-60)"
