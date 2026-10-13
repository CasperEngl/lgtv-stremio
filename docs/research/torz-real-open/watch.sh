#!/bin/sh
# Re-open one chosen link until it stops answering with the downloading clip, then watch the
# stream list's marking. Before each open the title is re-listed (not an open).
# Usage: watch.sh <type> <id> <listing.txt> <hash8> <label> <first delay s> <interval s> <max opens>
# Stops at the first answer that is not a redirect to downloading.mp4, ready or failed alike.
set -u
kind=$1; id=$2; list=$3; hash=$4; label=$5; delay=$6; interval=$7; max=$8
RUN=${RUN:-/tmp/t56/run}; export RUN="$RUN/$label"; mkdir -p "$RUN"
here=$(dirname "$0"); n=2
while [ "$n" -le "$max" ]; do
  sleep "$delay"; delay=$interval
  "$here/marking.sh" "$kind" "$id" "$hash"
  nn=$(printf '%02d' "$n")
  "$here/open.sh" "$label-$nn" "$list" "$hash"
  loc=$(tr -d '\r' < "$RUN/$label-$nn.headers" | awk 'tolower($1)=="location:"{print $2}')
  case $loc in
    */v0/store/_/static/downloading.mp4) ;;
    */v0/store/_/static/*) echo "## $label STOPPED at open $nn: clip $(basename "$loc")"; exit 0;;
    *) echo "## $label READY at open $nn"; break;;
  esac
  n=$((n + 1))
done
[ "$n" -gt "$max" ] && { echo "## $label still downloading after $max opens"; exit 0; }
i=0
while [ "$i" -lt 30 ]; do
  m=$("$here/marking.sh" "$kind" "$id" "$hash"); echo "$m"
  case $m in *"marking=cached"*) echo "## $label FLIPPED"; exit 0;; esac
  i=$((i + 1)); sleep 60
done
echo "## $label marking not flipped after 30 polls"
