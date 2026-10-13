#!/bin/sh
# One open of one listed stream's link, redirects off. THIS CAN QUEUE A DOWNLOAD on the debrid
# account when the list was fetched with the saved key. Prints a scrubbed record; raw headers and
# body stay in the run directory.
# Usage: open.sh <label> <list.json> <stream index, from 0> [extra curl args...]
set -u
RUN=${RUN:-/tmp/hr/run}; label=$1; list=$2; idx=$3; shift 3
url=$(jq -r --argjson i "$idx" '.streams[$i].url // empty' "$list")
[ -n "$url" ] || { echo "no link at index $idx"; exit 2; }
start=$(date -u +%FT%TZ)
w=$(curl -sS -m 120 --max-filesize 5000000 -D "$RUN/$label.headers" -o "$RUN/$label.body" \
  -w 'http=%{http_code} body_bytes=%{size_download} seconds=%{time_total}' "$@" "$url" 2>"$RUN/$label.err"); rc=$?
echo "## $label start=$start stream=$idx curl_exit=$rc $w"
[ -s "$RUN/$label.err" ] && sed -E 's#https?://[^ ]+#<scrubbed>#g' "$RUN/$label.err"
tr -d '\r' < "$RUN/$label.headers" | grep -Eiv '^(report-to|nel|cf-ray|set-cookie|alt-svc):' \
  | sed -E 's#^([Ll]ocation: https?://[^/]+)/.*#\1/<scrubbed>#; s#^([Ll]ocation: )[^h].*#\1<scrubbed, not absolute>#'
[ -f "$RUN/$label.body" ] && echo "body: $(wc -c < "$RUN/$label.body") bytes sha256=$(sha256sum "$RUN/$label.body" | cut -c1-64) type=$(file -b "$RUN/$label.body" | cut -c1-60)"
# What the redirect's address says, with the signature and any path outside the status service left out.
tr -d '\r' < "$RUN/$label.headers" | awk 'tolower($1)=="location:"{print $2}' | python3 -I -c '
import sys,re,urllib.parse as u
loc=sys.stdin.read().strip()
if not loc: print("target: none"); sys.exit()
p=u.urlsplit(loc); q=dict(u.parse_qsl(p.query)); body=q.get("body")
ref=re.findall(r"Ref:\s*(\S+)",body or "")
print("target host:",p.netloc,"| path:",p.path if p.netloc=="slate.elfhosted.com" else "<scrubbed>","| query keys:",sorted(q) if p.netloc=="slate.elfhosted.com" else "<scrubbed>")
if p.netloc=="slate.elfhosted.com": print("title:",q.get("title")); print("body:",body)
print("Ref key:",ref if ref else "NONE")'
