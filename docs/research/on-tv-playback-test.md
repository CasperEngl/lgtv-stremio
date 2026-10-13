# Play one debrid direct link on the G5 with PlxNative's player

Working notes for [issue #7](https://github.com/CasperEngl/lgtv-stremio/issues/7), part of the map in
[issue #1](https://github.com/CasperEngl/lgtv-stremio/issues/1). App code at `9d2777f`; `main` has since
added only `prototype/` and `CONTEXT.md`, so the package below is still current. The run happened on
the G5 on 2026-10-14; the "Results" section at the end records it. The checklist is the plan as
corrected by that run.

Placeholders used throughout: `<tv-ip>` is the television's address and `<passphrase>` is the
six characters the Developer Mode app shows. Neither is ever committed.

## What is ready

- **The package.** `com.beb.plxnative.debug_0.8.0_arm.ipk`, built by the fork's `CI` workflow
  (`cross-build` job, run 38467762163, commit `9d2777f`), artifact
  `plxnative-9d2777fe4d1fd9cb9cd9eb08503bc780e8a52c17`, 21 MB,
  sha256 `43db162969f77b5d1b48feb0b93fc8b4c57887ce14b9afc25706405a4cc90541`.
  Actions were already enabled on the fork; the job took 9 min 43 s against its 10-minute limit.
  A copy is kept at `/tmp/plx-ipk-9d2777fe/` on this machine. Fetch it again with
  `gh run download 38467762163 -R CasperEngl/lgtv-stremio -n plxnative-9d2777fe4d1fd9cb9cd9eb08503bc780e8a52c17`.
- **Tools on this machine.** `ssh` and `scp` are installed. `ares-cli` and webOS Dev Manager are
  not, and the steps below do not need them: everything goes over plain ssh as the Developer Mode
  user. `npx @webos-tools/cli` is the fallback for the install step only.

## The trigger

The debug flavour reads `/tmp/com.beb.plxnative.debug/plxnative-playurl` about two seconds after
start, on any screen other than sign-in or profile choice
(`rust-modules/src/dev/scenarios.rs:915-926`). The file is one JSON object
(`rust-modules/media/src/player/playurl.rs`):

```json
{"url":"https://<host>:443/<path>","vcodec":"hevc","acodec":"eac3","fps":23.976}
```

- `url`: the direct link, with `:443` written out. A missing port is read as 32400
  (`rust-modules/net/src/net/origin.rs:109,276-281`). The redirect to the debrid file server needs
  no such care: a redirect target without a port gets 443 (`rust-modules/net/src/stream_redirect.rs:350-357`).
- `vcodec`: `h264`, `hevc`, `av1` or `vp9`. `acodec`: `aac`, `ac3` or `eac3`.
- `fps`: optional. It matters for H.264, where the declared rate picks 24 or 60 Hz presentation.
- **There is no audio track number.** The app feeds the first audio track whose codec equals
  `acodec` (`rust-modules/media/src/ff.rs:690-711,8478-8490`). If the track the prototype picked is
  not the first one with that codec, the language can differ; it still plays.
- Leave the Dolby Vision fields out. A Dolby Vision file then plays its HDR10 layer; a profile 5
  file has none, so pick a title that is not profile 5.

`make-trigger.py` beside this file builds that object from the prototype's saved output without
printing the link. The prototype is `prototype/` in this repository:

```sh
(cd prototype && mise trust && mise exec -- cargo run --release -- play movie <imdb id>) > /tmp/play.out
grep -v '^mpv ' /tmp/play.out      # the codecs and the audio track, without the link
docs/research/on-tv-playback-test/make-trigger.py /tmp/play.out --vcodec hevc --acodec eac3 --out /tmp/plxnative-playurl
```

## Getting past sign-in

The trigger is skipped on the sign-in screen. Two ways past it:

1. **Sign in to Plex once on screen** (QR code). The account needs no server for this test only
   if the app leaves the sign-in screen without one; that is not known and is read off the set.
2. **No Plex account: a stand-in server on this machine.** `python3 tests/mock_pms.py --host 0.0.0.0 --port 32499`
   serves a synthetic library; two more trigger files point the app at it: `plxnative-token` (any text;
   the stand-in never checks it) and `plxnative-pms-origin` (`http://<this machine's address>:<port>`)
   (`rust-modules/src/dev/scenarios.rs:203-219`, `rust-modules/src/app/boot.rs:1008-1016`). The app
   then starts on Home with no account at all. This rides the same `/tmp` channel as the link, so
   it works exactly where the link trigger works.

## Checklist for the G5

Steps marked **TV** happen at the television; the rest run from this machine.

1. **TV.** Create or sign in to an LG developer account at <https://webostv.developer.lge.com/>
   (on a phone or computer). On the G5, install **Developer Mode** from the LG Content Store, open
   it, sign in, turn **Dev Mode Status** on (the set restarts), open it again and turn
   **Key Server** on. Note the IP address and the Passphrase it shows.
2. Fetch the login key and remove its passphrase:

   ```sh
   curl -s http://<tv-ip>:9991/webos_rsa -o ~/.ssh/webos_g5 && chmod 600 ~/.ssh/webos_g5
   ssh-keygen -p -P '<passphrase>' -N '' -f ~/.ssh/webos_g5
   ```

3. Read what the set is (answers "which platform release" and "is `/tmp` shared"):

   ```sh
   TV="ssh -p 9922 -i ~/.ssh/webos_g5 -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa prisoner@<tv-ip>"
   $TV 'id; ls -ld /tmp /media/developer /media/developer/temp; cat /var/run/nyx/os_info.json'
   ```

   In zsh, put the ssh line in a small script instead of a variable: zsh does not split `$TV`
   into words. The codec table (`/etc/umediaserver/device_codec_capability_config.json`) is not
   visible to this user on the G5; read the app's `devcaps:` line from its event log instead.

4. Install the package: copy it to `/media/developer/temp/`, then ask the installer.

   ```sh
   $TV 'cat > /media/developer/temp/plx.ipk' < com.beb.plxnative.debug_0.8.0_arm.ipk
   $TV "luna-send-pub -i luna://com.webos.appInstallService/dev/install '{\"id\":\"com.ares.defaultName\",\"ipkUrl\":\"/media/developer/temp/plx.ipk\",\"subscribe\":true}'"
   ```

   The install call keeps printing states; stop it (Ctrl-C, or `timeout 90`) once it prints
   `"state":"installed"`.

5. Launch it, then look at its directory:

   ```sh
   docs/research/on-tv-playback-test/tv-luna.sh luna://com.webos.applicationManager/launch '{"id":"com.beb.plxnative.debug"}'
   $TV 'ls -la /tmp/com.beb.plxnative.debug/'
   ```

   Bus calls go through `tv-luna.sh`, which uses `luna-send-pub -i` and waits for the reply:
   with `-n 1` the command exits before the reply prints and `launch` does not start the app.

   **Stop here if that directory cannot be listed or written.** Then trigger files do not reach
   the app on this set and the fallback (launch parameters) is a code change to decide on.
6. **TV.** Say what is on screen (expected: the QR sign-in screen). Get past it by route 1 or 2
   above.
7. Write the link and relaunch:

   ```sh
   $TV 'cat > /tmp/com.beb.plxnative.debug/plxnative-playurl' < /tmp/plxnative-playurl
   docs/research/on-tv-playback-test/tv-luna.sh luna://com.webos.applicationManager/dev/closeByAppId '{"id":"com.beb.plxnative.debug"}'
   docs/research/on-tv-playback-test/tv-luna.sh luna://com.webos.applicationManager/launch '{"id":"com.beb.plxnative.debug"}'
   ```

8. **TV.** Watch for two minutes: is there a picture, is there sound, is it in sync, does it
   stutter, does pause and a 30-second skip work, does Back leave the player.
9. Pull the logs, remove the link from the set, and scrub before committing:

   ```sh
   $TV 'cat /tmp/com.beb.plxnative.debug/plxnative-events.log' > g5-events.log
   $TV 'rm -f /tmp/com.beb.plxnative.debug/plxnative-playurl'
   ```

## What to record per set

- Model, webOS version and platform release (`os_info.json`).
- `id`, and the modes of `/tmp`, `/media/developer`, `/media/developer/temp`.
- Whether a trigger written by the Developer Mode user reached the app.
- Whether the app's logs could be pulled.
- Whether close-then-launch gave a fresh process (two boot lines in the event log).
- Whether the debug app id played video and audio (media permissions).
- The codec table's audio rows, channel counts, and whether it has a DTS row.
- The stream: container, video and audio codec, resolution, and what the player's log says about
  the open (status, redirect, size), the Load, and the first picture.

## Results

### LG G5 (2025)

**Result: the unmodified player plays a cached debrid direct link on the G5**, with picture, HDR10,
E-AC-3 sound, pause and seeking. Run on 2026-10-14 with the unmodified debug package (`9d2777f`),
installed and driven over Developer Mode ssh only. Scrubbed event log:
[`on-tv-playback-test/g5-events.scrubbed.log`](on-tv-playback-test/g5-events.scrubbed.log).
The crash, diagnostics and stderr logs sit beside it (`g5-crash.scrubbed.log`,
`g5-diag.scrubbed.log`, `g5-stderr.scrubbed.log`), with the two wrappers the run used:
`tv-ssh.sh '<command>'` runs one command on the set as the Developer Mode user, and
`tv-luna.sh <uri> '<json>'` makes one bus call and waits for its reply. For another set, fetch
its key to `~/.ssh/webos_<name>` and run them with `SET=<name>`; `~/.ssh/known_hosts_webos` must
then hold that set's entry only. `tv-luna.sh` takes an optional third argument, the seconds to
wait for the reply (default 3).

**Measured on the set (ssh, `os_info.json`, `device_info.json`, `ls`, `id`):**

- Model `OLED65G54LW`, board `O24_DVB`, SoC name `o24n`, 2.5 GB RAM.
- webOS TV release `10.3.1`, build `10.3.1-3006`, `webos_release_platformcode` 10, codename
  `ponytail-papikonda`, kernel 5.4.268. So the G5 is on platform release 10, not 11.
- ssh user: `uid=5352(prisoner) gid=5000(jailer) groups=29(audio),44(video),505(compositor),509(se),777(crashd)`.
- `/tmp` is `drwxrwxrwt root root`: the system `/tmp`, shared with the app.
  `/media/developer` is `drwxrwxr-x root root`; `/media/developer/temp` is `drwxrwxrwx root root`.
- The app's runtime directory `/tmp/com.beb.plxnative.debug` is listable by the ssh user:
  `drwxrwxrwt`, owned by the app's uid 6365, group `jailer`. Being mode 1777, the ssh user can
  create files in it. It cannot replace a file the app itself wrote there (sticky bit).
- **Logs can be pulled.** `plxnative-events.log`, `-crash.log`, `-stderr.log` and `-diag.log` are
  `0640 6365:jailer` and `cat` over ssh read all of them.
- **The codec table cannot be read over ssh.** `/etc/umediaserver` does not exist inside the ssh
  user's jail. The app can read it and logs a summary at boot (below).
- The key fetch in step 2 worked as written. The key file is an RSA PEM; the ssh options in step 3
  are needed.

**Read from the other session's event log** (its build, `relay-boot` at `dd9666c`, not the
unmodified package; it starts playback from the sign-in screen, which the unmodified app does not):

- Codec table summary as the app logged it:
  `devcaps: hevc=true 4096x2176 vp9=true av1=true audio=aac,ac3,eac3,dts rows: h264=4096x2304@60 hevc=4096x2176@60 vp9=4096x2304@60 av1=4096x2304@60 vp9bits=8 (device table)`.
  **The G5's table has a DTS row.** Channel counts are not in that line.
- `tv.config.supportDolbyHDRContents` answered `supported`.
- The debug app id did get the media pipeline: `Load` returned ok in 198 ms, resources
  `VDEC` port 3 and `ADEC` port 1 were granted, and a 34.3 GB Matroska file (HEVC 3840x1600,
  23.976 fps, AC-3) opened with HTTP 200 and played to position 529 s, ending on a key press.
  Whether picture and sound were actually seen and heard is that session's to report.
- The app's own uid is 6365, gid 5000, groups `15,19,29,44,505,509,511,777`.

**The stream:** Dune: Part Two, 26.7 GB Matroska, HEVC Main 10 3840x1608 at 23.976 fps, Dolby
Vision profile 8, first audio track E-AC-3 7.1 English, 32 subtitle tracks (measured with `ffprobe`
on this machine). Trigger: `vcodec hevc`, `acodec eac3`, `fps 23.976`, no Dolby Vision fields.

**Seen at the set (the owner watching):**

| Check | Result |
| --- | --- |
| Picture | Good |
| Sound | Present, "seems fine" |
| HDR | On |
| Pause and resume | Works |
| Short skip | Works, 3-4 s of buffering |
| Long jump (held key, to 4663 s) | Works, 3-4 s of buffering |
| Back | Leaves the player for Home (the stand-in server's library) |

**Measured from the app's event log:**

- The trigger written by the ssh user reached the app: it opened the player about two seconds
  after landing on Home.
- Open: HTTP 200 after one 302 redirect to another origin, `clen=26652306539`.
- `Load` returned ok in 336 ms with `v=H265 a="AC3 PLUS" fps=23.976`; resources `VDEC` port 3 and
  `ADEC` port 1. So the debug app id has the media permissions on webOS 10.3.1.
- The decoder reported `"hdrType":"HDR10"`, 3840x1608, 23.976 progressive. The file's Dolby Vision
  profile 8 was detected by the demuxer (`dovi=P8 bl_compat=1`) and, as declared, not used.
- Four seeks (to 1212 s, 1371 s, 1399 s and 4663 s), each `ff: seek … rv=0`. Every seek tears the
  pipeline down and does a fresh `Load` and a fresh open of the link, redirects included; that is
  where the 3-4 seconds go. The log has no wall-clock stamps, so the 3-4 s is the owner's estimate.
- Close-then-launch (`dev/closeByAppId`, then `launch`) gave a fresh process each time: a new pid
  and a restarted event log.
- One crash record: `SIGSEGV addr=0x8` inside `/usr/lib/libcrypto.so.3`, stamped at the second the
  app was closed with `dev/closeByAppId` while it sat on the sign-in screen. Nothing crashed during
  playback. Not investigated.
- The event log contains the link's path (`stream: … path=…`), which carries the account token.
  Scrub before sharing any log from a playback.

**What the steps above needed in practice (corrections to the checklist):**

- `luna-send-pub -n 1 …` exits before printing the reply and, for `launch`, did not start the app.
  `luna-send-pub -i … & sleep 3; kill $!` works for `launch`, `dev/closeByAppId` and `dev/running`.
- The app keeps its uid across a reinstall (6365 before and after), and never deletes trigger
  files. A trigger file the app's own uid wrote (the other session's build did this) cannot be
  removed by the ssh user. Only a real restart of the set clears `/tmp`: holding the remote's power
  button was a standby (uptime unchanged), pulling the plug worked. The bus refuses `reboot` to
  the ssh user.
- The set reopened the app by itself after the restart.
- Sign-in was skipped with the stand-in server: `plxnative-token` (any text) and
  `plxnative-pms-origin` set to `http://127.0.0.1:32499`, with `tests/mock_pms.py --host 0.0.0.0
  --port 32499` on this machine and `ssh -N -R 32499:127.0.0.1:32499` to the set. Developer Mode's
  sshd allows the reverse forward, and the jailed app reaches the set's loopback. The tunnel was
  needed because this machine's firewall drops inbound connections to that port.
- Installing with `luna-send-pub -i …/dev/install` over ssh worked; no `ares-cli` or Dev Manager
  was used. The package's sha256 was checked on the set before installing.

**Not done on this set:** playing with the Dolby Vision fields declared; a stream with AC-3 or AAC
(the other session's log shows AC-3 loading); the codec table's channel counts.

### LG C1 (2021)

Not run, and not going to be: on 2026-10-14 the owner said the C1 is no longer a reference set.
What stays unmeasured as a result is everything specific to webOS 6: whether a trigger written by
the Developer Mode user reaches the app there, whether the debug app id gets the media
permissions, and what that set's codec table lists.
