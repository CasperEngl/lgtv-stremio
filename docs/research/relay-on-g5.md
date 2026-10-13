# Play a debrid stream on the G5 through a relay on this machine

A follow-on to [`on-tv-playback-test.md`](on-tv-playback-test.md), which played a debrid direct
link by writing the link itself onto the set. Here the set is given only an address on this
machine: a relay picks the stream, holds the Comet address and its account key, and passes the
file through. Run on 2026-10-14 on the LG G5 with the unmodified debug package (`9d2777f`).

Placeholders: `<tv-ip>` is the television's address and `<this-machine>` is this machine's address
on the home network. Neither is committed.

## Result

**The unmodified player plays a relayed debrid stream on the G5**, at normal speed, and a seek
with the remote works through the relay. A second run played a **dual-layer Dolby Vision file
(profile 7) as HDR10**, fed undeclared. Picture, HDR and sound were not observed by a person on
either run; see [What was not observed](#what-was-not-observed).

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

## Second run: a dual-layer Dolby Vision file, through the reverse tunnel

Same title without `--match`, so the relay took stream 1: HEVC 3840x2160, Dolby Vision profile 7,
57.1 GB, first safe audio track AC-3 5.1 in English. Two things differed from the first run:

- **No firewall rule.** The relay bound `127.0.0.1` and the set reached it through one more
  forward on the Developer Mode tunnel:
  `ssh -N -R 32499:127.0.0.1:32499 -R 8787:127.0.0.1:8787`. The trigger then names
  `http://127.0.0.1:8787/stream`.
- **Dolby Vision left undeclared.** The relay's answer carries
  `"dovi":{"profile":7,"bl_compat":6,"el_present":true}`, which `9d2777f` refuses as dual-layer
  (`rust-modules/data/src/metadata.rs`, `Dovi::presentation`). The `dovi` object was dropped
  before the trigger was written, so the app fed the one video track as plain HEVC.

**From the app's event log:**

- `load: v=H265 a="AC3" fps=23.976 dv=present:0`, `ff: open status=200 clen=61282183944`, and
  `Load returned ok=1` after 223 ms.
- The demuxer saw what the file is: `dovi=P7 level=6 bl_compat=6 rpu=1 el=1 bl=1`.
- The decoder reported `"hdrType":"HDR10"`, 3840x2160, 23.976 progressive,
  `transferCharacteristics` 16, `colorPrimaries` 9, `matrixCoeffs` 9.
- 145 seconds played before the app was closed. Of 124 one-second samples, 119 read `play=`
  between 996 and 1001 per thousand; three read 985 and two read 1041. The interface loop held
  60 fps. No refusal, stall or failure line.

So the G5's decoder takes a single-track profile 7 file with its enhancement layer and RPU left
in the stream, and presents the base layer as HDR10. Nothing was stripped on the way.

## What was not observed

Nobody reported the picture, the HDR badge or the sound for either run. The log shows frames
displayed and audio fed, which is not the same as hearing it: issue #37 is about this app being
silent through an HDMI soundbar on this set. For the profile 7 file in particular, a wrong
picture (colour cast, blockiness from the unstripped layer) would not show in the log.

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
- **The refusal of profile 7 is the app's choice, not the set's.** Changing
  `Dovi::presentation` to present a dual-layer file with `bl_compat == 6` as not Dolby Vision
  gives the result measured here; branch `dv-p7-base-layer` (`b770520`) does that and passes CI.

## Open

- **The relay repeats the prototype's stream pick.** `prototype/`'s `play` command already picks a
  cached stream with a safe audio track in the wanted language; the relay picks by file order and
  ignores language.
- **The relay declares profile 7 as it finds it**, which the app refuses. Until the app's rule
  changes, the relay should leave `dovi` out for a dual-layer file, as the second run did by hand.
- **No seek was made on the profile 7 file**, and the tunnel was not measured at the file's peak
  bitrate. Ten seconds mid-run read 4.2 MB/s against an average of 7 MB/s for the file.
- **The first run's relay listened on the home network**, which needed a firewall rule on this
  machine for port 8787. The second run shows the tunnel makes that rule unnecessary.

## Left as found

After each run the app was closed and the three trigger files removed; the tunnel, the stand-in
server and the relay were stopped. The app's own logs stay in `/tmp/com.beb.plxnative.debug/` until the set loses
power. The firewall rule for port 8787 is still on this machine.
