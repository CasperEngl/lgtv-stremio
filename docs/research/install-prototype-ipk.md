# Install the placeholder package on the G5

Working notes for [issue #24](https://github.com/CasperEngl/lgtv-stremio/issues/24), part of the map in
[issue #1](https://github.com/CasperEngl/lgtv-stremio/issues/1). Run on 2026-10-14.

**Result: the placeholder package installs on the unrooted LG G5 and the app starts, runs and
exits cleanly in the developer jail.** It was installed over Developer Mode ssh, not with webOS
Dev Manager, on the owner's instruction during the session; Dev Manager's own window was never
used, so that half of the question is not observed.

The television's address is never written here. The wrappers read it from
`~/.ssh/known_hosts_webos`; the login key is `~/.ssh/webos_g5`.

## The package

`com.example.stremio.placeholder_0.0.1_arm.ipk`, 4,090,328 B, sha256
`e54107d108abfde8bca9f0a312888b5eeb580f698628e4370b08ea953499f986`. It is the artifact
`stremio-prototype-030b7540b76ba427131badc2507ecb7e32319e5a` of the `Stremio` workflow,
[run 38476805685](https://github.com/CasperEngl/lgtv-stremio/actions/runs/38476805685), on pull
request #20 (branch commit `4e255510`). Fetch it with
`gh run download 38476805685 -R CasperEngl/lgtv-stremio`.

## What was run

`tv-ssh.sh '<command>'` runs one command on the set as the Developer Mode user (`prisoner`, port
9922). `tv-luna.sh <uri> '<json>' [seconds]` makes one bus call and waits that long for replies.
Both sit in [`on-tv-playback-test/`](on-tv-playback-test/), where the first run on this set left
them.

```sh
cd docs/research/on-tv-playback-test
ID=com.example.stremio.placeholder
IPK=/path/to/com.example.stremio.placeholder_0.0.1_arm.ipk
./tv-luna.sh luna://com.webos.applicationManager/dev/running '{}'           # who is on the set
./tv-ssh.sh 'cat > /media/developer/temp/stremio-placeholder.ipk' < "$IPK"
./tv-ssh.sh 'sha256sum /media/developer/temp/stremio-placeholder.ipk'
./tv-luna.sh luna://com.webos.appInstallService/dev/install \
  '{"id":"com.ares.defaultName","ipkUrl":"/media/developer/temp/stremio-placeholder.ipk","subscribe":true}' 20
./tv-luna.sh luna://com.webos.applicationManager/launch "{\"id\":\"$ID\"}" 2
./tv-ssh.sh "cat /tmp/$ID/plxnative-events.log"
./tv-ssh.sh 'rm -f /media/developer/temp/stremio-placeholder.ipk'
```

## What the set answered

Every line below is implied by a log or a command's output. Nobody watched the screen during this
first install; what the owner later saw is under "Seen by the owner at the television".

| Step | Result | Raw output |
| --- | --- | --- |
| Copy | 4,090,328 B on the set, same sha256 | [`01-copy.txt`](install-prototype-ipk/raw/01-copy.txt) |
| Install | 20 status messages ending in `"state":"installed"`, no error | [`02-install.jsonl`](install-prototype-ipk/raw/02-install.jsonl) |
| Installed files | `stremio-tv` 3,758,180 B and the five bundled libraries under `/media/developer/apps/usr/palm/applications/<id>/` | [`03-installed.txt`](install-prototype-ipk/raw/03-installed.txt) |
| Launch | `{"returnValue":true}`; two seconds later `dev/running` lists the id as a native app, pid 7249 | [`04-launch.txt`](install-prototype-ipk/raw/04-launch.txt) |
| Exit | Nine seconds after the launch call `dev/running` is empty again | same file |
| Event log | 11 lines, from the boot line to the 300-frame line | [`placeholder-events.log`](install-prototype-ipk/raw/placeholder-events.log) |
| Crash log | Only the image marker the boot shim always writes; no crash record | [`placeholder-crash.log`](install-prototype-ipk/raw/placeholder-crash.log) |

The event log, whole:

```
stremio-tv prototype 0.0.1 booting as com.example.stremio.placeholder
net: bound libcurl -> libcurl.so.4 (libcurl/7.82.0 OpenSSL/3.0.13 zlib/1.2.11 c-ares/1.19.0 nghttp2/1.47.0; AsynchDNS=yes); threaded-tls=true legacy-locks=NotNeeded
vplane: SDL exported window (webOS 5+)
vplane: exported window (webOS 5+) — created per session
curlio: bound libcurl.so.4 curl_multi_* (7 symbols)
ff: bound avutil -> libavutil-plx.so.61
ff: bound avcodec -> libavcodec-plx.so.63
ff: bound avformat -> libavformat-plx.so.63
ff: bound swscale -> libswscale-plx.so.10
ff: avformat=63.1.100 avcodec=63.1.100 avutil=61.1.100
stremio-tv: 1 catalogue page(s) held after 300 frames
```

What those lines establish on the G5 (webOS 10.3.1, platform release 10):

- **The set starts the binary under the placeholder app id.** The app id is read from the install
  folder's name, as the build ticket predicted, and the runtime folder is
  `/tmp/com.example.stremio.placeholder/`, mode 1777.
- **The app gets its own user.** The files are owned by uid 6725, group `jailer`; PlxNative's
  debug install on the same set runs as uid 6365. The logs are mode 0640 and the ssh user reads
  them through the group.
- **The set's own libcurl loads and the network is reachable from the jail.** `stremio-core` held
  one catalogue page at the end, and a catalogue page only arrives over HTTPS from an add-on.
  Which add-on answered is not in the log.
- **The bundled FFmpeg loads** from the app's folder, all four libraries.
- **The player's video-plane setup runs without a window** and without an error line.
- **The process exits by itself** with no crash record and an empty stderr log.

## Not observed

This list is as of the first install. The screen and the home-row launch were seen later the same
day; see "Seen by the owner at the television" at the end.

- **webOS Dev Manager.** Not used. The install went through the developer install service
  (`com.webos.appInstallService/dev/install`) called directly over ssh. The Developer Mode
  research (issue #3) reads Dev Manager as reaching the same service over the same ssh user; that
  is a reading of its source, not something this run saw. The set's Key Server was off, and Dev
  Manager needs it to add a television by passphrase.
- **Anything on the screen during this first install and launch**: what the television showed
  while the package installed and during the nine seconds the app ran, and whether a "Stremio
  prototype" tile with PlxNative's icon appeared in the home row.
- **The process's exit status.** The log's last line is written just before `plex_run` returns 0;
  the status the set recorded was not read.
- **A launch from the remote or the home row**, at this point. The one launch was a bus call.
- **Player start.** The placeholder starts the player only when handed a link, and none was.

## State the set was left in

The placeholder app is still installed, so the home row can be looked at. The copied package was
removed from `/media/developer/temp/`. The app's three log files remain in its runtime folder
until the set loses power. Remove the app with:

```sh
./tv-luna.sh luna://com.webos.appInstallService/dev/remove '{"id":"com.example.stremio.placeholder","subscribe":true}' 10
```

## About the television lock

`tools/tv-lock.sh` answers "no TV configured" for this set: it drives upstream's rooted set as
`root`. The run followed the `devmode-tv` skill (`.agents/skills/devmode-tv/`, pull request #29)
instead. Another session was playing something with PlxNative's debug app on the same set until
about a minute before the install ([`00-before.txt`](install-prototype-ipk/raw/00-before.txt));
the install and launch were done in the gap, after `dev/running` came back empty twice.

## Later the same day: Rill's tile on the placeholder

The owner asked for the installed placeholder to carry Rill's branding so it stands out in the
home row. [`rebrand-ipk.py`](install-prototype-ipk/rebrand-ipk.py) rewrites the package without
rebuilding it:

```sh
docs/research/install-prototype-ipk/rebrand-ipk.py com.example.stremio.placeholder_0.0.1_arm.ipk \
  <checkout of wayfinder/rill-final-artwork>/artwork-prototype/out/final rill-prototype_0.0.1_arm.ipk
```

| | Placeholder | Rebranded |
| --- | --- | --- |
| Title | Stremio prototype | Rill prototype |
| Icons | PlxNative's | Rill's 80 px and 130 px tile (aqua on blue-black) |
| `iconColor`, `bgColor` | absent | `#0c2330` |
| Splash | none | `splash.png`, 1920x1080, as `splashBackground` |
| App id, version, binary | | unchanged; `stremio-tv` has the same sha256 in both |
| Package | 4,090,328 B | 4,096,540 B, sha256 `0d8710c5…790a9e2a` |

The artwork is commit `74746678` of `wayfinder/rill-final-artwork` (pull request #33), whose
values are still that ticket's to settle. Two runs of the script give the same sha256.

Implied by logs and command output, as before:

- The install ran through to `installed` over the first one, with no error
  ([`12-install.jsonl`](install-prototype-ipk/raw/12-install.jsonl),
  [`13-installed.txt`](install-prototype-ipk/raw/13-installed.txt)).
- The app started and left by itself within ten seconds
  ([`14-launch.txt`](install-prototype-ipk/raw/14-launch.txt)), and its event log is byte for byte
  the first run's ([`rill-events.log`](install-prototype-ipk/raw/rill-events.log)).
- The app kept uid 6725 across the reinstall.
- The crash log, which is append-only, held three image markers after this launch and one after
  the first. This session launched the app twice, so one start is unaccounted for. Not
  investigated.

How the tile and the splash look on the television, and whether the set shows a splash at all for
an app that opens no window, could not be told from these logs. The owner's look, next, answers
both.

The rebranded package is what the set holds now.

### Seen by the owner at the television

Reported after the rebranded install, in the owner's words: "it shows up, but it exits after the
splash screen".

- **Seen by a person:** the tile is in the home row; a launch from there shows the splash; the app
  then leaves by itself.
- **Implied by the log:** that launch (01:35 on the set's clock) wrote the same eleven lines,
  ending with the 300-frame line, with no crash record and an empty stderr log. The exit is the
  placeholder's design, not a failure: it runs 300 frames and returns.
- So the set does show `splashBackground` for a native app that never opens a window.
- **Seen by a person, on being asked** how the tile looks (icon sharpness, the blue-black against
  its neighbours): "it looks fine".
- **Not observed:** how long the splash stayed (asked in the same question, not answered), and
  what the screen showed as the app left (not asked). Dev Manager is still unused.
