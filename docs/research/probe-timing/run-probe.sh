#!/bin/sh
# run-probe.sh <trigger file> <label>: one timed open on the set. Fresh launch, wait for the
# demuxer's "tracks known" line, pull the event log, close the app, remove the link from the set.
# Needs the stand-in server and the reverse tunnel up (see the notes). Prints no link.
set -eu
here=$(dirname "$0"); trig=$1; label=$2
app=com.beb.plxnative.debug; dir=/tmp/$app
"$here/tv-luna.sh" luna://com.webos.applicationManager/dev/closeByAppId "{\"id\":\"$app\"}" 2 >/dev/null || true
"$here/tv-ssh.sh" "mkdir -p $dir 2>/dev/null; printf standin > $dir/plxnative-token; printf 'http://127.0.0.1:32499' > $dir/plxnative-pms-origin; cat > $dir/plxnative-playurl; ls $dir | tr '\n' ' '" < "$trig"
echo
start=$(date +%s.%N)
"$here/tv-luna.sh" luna://com.webos.applicationManager/launch "{\"id\":\"$app\"}" 3 >/dev/null || true
i=0
while [ $i -lt 45 ]; do
  if "$here/tv-ssh.sh" "grep -c -E 'probe-timing: (tracks known|open_input FAILED)|https open FAILED|find_stream_info failed' $dir/plxnative-events.log" 2>/dev/null | grep -q '^[1-9]'; then break; fi
  i=$((i+1)); sleep 2
done
sleep 4
"$here/tv-ssh.sh" "cat $dir/plxnative-events.log" > "$here/raw/$label.events.log"
"$here/tv-luna.sh" luna://com.webos.applicationManager/dev/closeByAppId "{\"id\":\"$app\"}" 2 >/dev/null || true
"$here/tv-ssh.sh" "rm -f $dir/plxnative-playurl; ls $dir | tr '\n' ' '"
echo
echo "$label: launched $start, polled $i times"
grep -a -E 'probe-timing:|^ff: open|curlio: redirect|^ff: v=|Load returned' "$here/raw/$label.events.log" | sed -E 's#https?://[^ ]+#<link>#g' | cut -c1-230
