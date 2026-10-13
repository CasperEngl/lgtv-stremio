#!/bin/sh
# Re-fetch the title's stream list (not an open) every <interval> seconds, at most <count> times,
# and log the picked stream's marking. Stops when it carries the cached mark.
set -u
count=$1; interval=$2
RUN=/tmp/hsc/run; HASH=4d5f74f5babcd7bf62b75acd8182370ca495dfa5
D=${XDG_DATA_HOME:-$HOME/.local/share}/lgtv-stremio
T=$(jq -r '.addons[]|select(.manifest.id=="comet.elfhosted.com")|.transportUrl' "$D/profile.json"); B=${T%/manifest.json}
i=0
while [ "$i" -lt "$count" ]; do
  curl -s -m 60 -o "$RUN/mark.json" "$B/stream/movie/tt0063350.json"
  m=$(jq -r --arg h "$HASH" '[.streams[]|select(.behaviorHints.bingeGroup|endswith($h))|.name|gsub("\n";" ")]|join(" ; ")' "$RUN/mark.json" 2>/dev/null)
  echo "## mark at=$(date -u +%FT%TZ) marking=$m streams=$(jq '.streams|length' "$RUN/mark.json" 2>/dev/null)"
  case $m in *⚡*) cp "$RUN/mark.json" "$RUN/mark-flipped.json"; echo "## FLIPPED"; exit 0;; esac
  i=$((i + 1)); sleep "$interval"
done
echo "## not flipped after $count polls"
