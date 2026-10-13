#!/bin/sh
# Re-open the picked link <count> times, <interval> seconds apart, numbering from <first>. Before
# each open, re-fetch the title's stream list (not an open) and log the stream's marking.
# Stops at the first answer that is not a redirect to the slate host.
set -u
count=$1; interval=$2; first=$3
RUN=/tmp/hsc/run; HASH=4d5f74f5babcd7bf62b75acd8182370ca495dfa5
D=${XDG_DATA_HOME:-$HOME/.local/share}/lgtv-stremio
T=$(jq -r '.addons[]|select(.manifest.id=="comet.elfhosted.com")|.transportUrl' "$D/profile.json"); B=${T%/manifest.json}
i=0
while [ "$i" -lt "$count" ]; do
  n=$(printf '%02d' $((first + i)))
  curl -s -m 60 -o "$RUN/list-$n.json" "$B/stream/movie/tt0063350.json"
  echo "## list-$n at=$(date -u +%FT%TZ) marking=$(jq -r --arg h "$HASH" '[.streams[]|select(.behaviorHints.bingeGroup|endswith($h))|.name|gsub("\n";" ")]|join(" ; ")' "$RUN/list-$n.json" 2>/dev/null)"
  /tmp/hsc/bin/open.sh "open-$n" | grep -Ev '^(report-to|nel|cf-ray):'
  tr -d '\r' < "$RUN/open-$n.headers" | awk 'tolower($1)=="location:"{print $2}' | python3 -I -c '
import sys,urllib.parse as u
p=u.urlsplit(sys.stdin.read().strip()); q=dict(u.parse_qsl(p.query))
print("target:",p.netloc,p.path if p.netloc=="slate.elfhosted.com" else "<scrubbed>","| title:",q.get("title"),"| body:",q.get("body"))'
  code=$(head -1 "$RUN/open-$n.headers" | awk '{print $2}')
  host=$(tr -d '\r' < "$RUN/open-$n.headers" | awk 'tolower($1)=="location:"{print $2}' | cut -d/ -f3)
  ref=$(tr -d '\r' < "$RUN/open-$n.headers" | grep -ci 'MEDIA_NOT_CACHED_YET')
  if [ "$code" != 302 ] || [ "$host" != slate.elfhosted.com ] || [ "$ref" != 1 ]; then echo "## CHANGED at open-$n: stopping"; exit 0; fi
  i=$((i + 1)); [ "$i" -lt "$count" ] && sleep "$interval"
done
echo "## batch done, still slate"
