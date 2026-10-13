# Play a debrid stream on the G5 through a relay on this machine

A follow-on to [`on-tv-playback-test.md`](on-tv-playback-test.md), which played a debrid direct
link by writing the link itself onto the set. Here the set is given only an address on this
machine: a relay picks the stream, holds the Comet address and its account key, and passes the
file through. Run on 2026-10-14 on the LG G5 with the unmodified debug package (`9d2777f`).

Placeholders: `<tv-ip>` is the television's address and `<this-machine>` is this machine's address
on the home network. Neither is committed.

## Result

**The unmodified player plays a relayed debrid stream on the G5**, at normal speed, and a seek
with the remote works through the relay. Picture, HDR and sound were not observed by a person on
this run; see [What was not observed](#what-was-not-observed).

## What ran

- **The relay**, [`relay-on-g5/relay.py`](relay-on-g5/relay.py), Python standard library plus
  `ffprobe`. It asks Comet for a title's streams, takes the first cached stream that probes as
  playable (HEVC or H.264 video, a safe audio track, not an error clip), and serves two addresses:
  `/playurl.json`, the `plxnative-playurl` object for that file, and `/stream`, the file itself,
  passed through from the debrid direct link with `Range` honoured.
- **The app**: the debug package already on the set. The newest `img: build_id=` line in its crash
  log was `10fb8cbb…`, the build id of the `9d2777f` package.
- **Past sign-in**: route 2 of `on-tv-playback-test.md`, the stand-in server
  (`tests/mock_pms.py --host 127.0.0.1 --port 32499`) reached through
  `ssh -N -R 32499:127.0.0.1:32499`, with `plxnative-token` and `plxnative-pms-origin`.

```sh
relay-on-g5/relay.py movie tt0133093 --bind <this-machine> --match 1080p   # port 8787
curl -s -0 http://<this-machine>:8787/playurl.json \
  | on-tv-playback-test/tv-ssh.sh 'umask 027; cat > /tmp/com.beb.plxnative.debug/plxnative-playurl'
```

The relay's answer, which is the whole trigger:

```json
{"url":"http://<this-machine>:8787/stream","vcodec":"hevc","acodec":"ac3","fps":23.976,"atmos":false}
```

## Measured

**The relay's pick.** Comet returned 283 streams. With `--match 1080p` the relay took stream 101,
a release named as a 1080p remux with TrueHD Atmos. Probed, it is HEVC 3840x1600 with no Dolby
Vision, 32.0 GB, and its first safe audio track is AC-3 5.1 in English. The release name was wrong
about the resolution and silent about the AC-3 track.

**From the app's event log:**

- `devcaps: hevc=true 4096x2176 vp9=true av1=true audio=aac,ac3,eac3,dts` (device table).
- `load: v=H265 a="AC3" fps=23.976 dv=present:0`, then `route=player` within the same second.
- Position advanced one second per log second with `play=` between 997 and 1001 per thousand, and
  the interface loop held 59 to 61 fps.
- One seek by a held key: `scrub: keyup commit (held) 581s`, `ff: seek 581s rv=0`, and playback
  continued from there at `play=1000pm`.
- No refusal or failure line. FFmpeg's stderr noted an unsized PGS subtitle track twice.

**From the relay:**

- The set opened `/stream` whole, read the end of the file (`bytes=34317026536-`), then read
  forward: the Matroska open. Data then flowed at 3.5 to 4.1 MB/s, the file's own rate
  (32 GB over 136 minutes).
- From another machine on the home network, a 20 MB ranged read came through at 24 MB/s.

## What was not observed

Nobody reported the picture, the HDR badge or the sound for this run. The log shows frames
displayed and audio fed, which is not the same as hearing it: issue #37 is about this app being
silent through an HDMI soundbar on this set.

## What this settles

- **No rebuilt app is needed to relay.** A branch built earlier the same night,
  `stremio-relay-boot`, has the debug app fetch `/playurl.json` itself at boot and start from the
  sign-in screen. Its first build (`dd9666c`) played the film under the sign-in page; its fix
  (`1004f92`) passed CI and was never run on a set. With trigger files reachable over Developer
  Mode ssh, that branch buys only the removal of the stand-in server, at the cost of a private
  address compiled into the package.
- **The player's seek works against a relay.** Every seek is a fresh open with `Range`, and the
  relay answers each with `206` and the length of that response's body
  (`tests/serve_fixtures.py`, THE SPEC).

## Open

- **The relay listened on the home network**, which needed a firewall rule on this machine for
  port 8787. The Developer Mode skill's reverse tunnel (`ssh -N -R 8787:127.0.0.1:8787`, then
  `http://127.0.0.1:8787/stream` in the trigger) would need no rule. Not tried.
- **The relay repeats the prototype's stream pick.** `prototype/`'s `play` command already picks a
  cached stream with a safe audio track in the wanted language; the relay picks by file order and
  ignores language.
- **A dual-layer Dolby Vision file was not played.** Without `--match`, the relay picks stream 1
  for the same title: 57.1 GB, profile 7, with an AC-3 5.1 English track. The relay declares it
  as profile 7 with an enhancement layer, which `9d2777f` refuses; dropping the `dovi` object from
  the trigger feeds the same file undeclared.

## Left as found

The app was closed and the three trigger files removed; the tunnel, the stand-in server and the
relay were stopped. The app's own logs stay in `/tmp/com.beb.plxnative.debug/` until the set loses
power. The firewall rule for port 8787 is still on this machine.
