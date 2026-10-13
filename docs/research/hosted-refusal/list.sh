#!/bin/sh
# Fetch one title's stream list from the account's Comet add-on. This opens nothing.
# Usage: list.sh <movie|series> <id> <out.json> [--wrong-key]
# --wrong-key asks with the debrid key in the add-on's configuration replaced by a made-up one of
# the same length, so the links in the answer are sealed for a key Real-Debrid will not accept.
# The add-on address carries the debrid key: it is read from the prototype's saved session and
# never printed.
set -u
kind=$1; id=$2; out=$3; mode=${4:-}
D=${XDG_DATA_HOME:-$HOME/.local/share}/lgtv-stremio
T=$(jq -r '.addons[]|select(.manifest.id=="comet.elfhosted.com")|.transportUrl' "$D/profile.json"); B=${T%/manifest.json}
if [ "$mode" = --wrong-key ]; then
  B=$(printf '%s' "$B" | python3 -I -c '
import sys,base64,json
b=sys.stdin.read().strip(); root,seg=b.rsplit("/",1)
c=json.loads(base64.urlsafe_b64decode(seg+"="*(-len(seg)%4)))
for s in c["debridServices"]: s["apiKey"]="X"*len(s["apiKey"])
print(root+"/"+base64.urlsafe_b64encode(json.dumps(c,separators=(",",":")).encode()).decode().rstrip("="))')
fi
code=$(curl -sS -m 90 -o "$out" -w '%{http_code}' "$B/stream/$kind/$id.json" 2>/dev/null); rc=$?
echo "## list $kind/$id mode=${mode:-saved-key} at=$(date -u +%FT%TZ) curl_exit=$rc http=$code bytes=$(wc -c < "$out") streams=$(jq '.streams|length' "$out" 2>/dev/null)"
jq -r '.streams[].name|gsub("\n";" ")' "$out" 2>/dev/null | sort | uniq -c
