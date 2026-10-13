# Play one debrid direct link on the G5 and the C1 with PlxNative's player

Working notes for [issue #7](https://github.com/CasperEngl/lgtv-stremio/issues/7), part of the map in
[issue #1](https://github.com/CasperEngl/lgtv-stremio/issues/1). App code at `9d2777f`; `main` has since
added only `prototype/` and `CONTEXT.md`, so the package below is still current. Nothing below
has been run on a television yet; the "Results" section at the end is filled in per set.

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
   $TV 'cat /etc/umediaserver/device_codec_capability_config.json'
   ```

4. Install the package: copy it to `/media/developer/temp/`, then ask the installer.

   ```sh
   $TV 'cat > /media/developer/temp/plx.ipk' < com.beb.plxnative.debug_0.8.0_arm.ipk
   $TV "luna-send-pub -i luna://com.webos.appInstallService/dev/install '{\"id\":\"com.ares.defaultName\",\"ipkUrl\":\"/media/developer/temp/plx.ipk\",\"subscribe\":true}'"
   ```

5. Launch it, then look at its directory:

   ```sh
   $TV "luna-send-pub -n 1 luna://com.webos.applicationManager/launch '{\"id\":\"com.beb.plxnative.debug\"}'"
   $TV 'ls -la /tmp/com.beb.plxnative.debug/'
   ```

   **Stop here if that directory cannot be listed or written.** Then trigger files do not reach
   the app on this set and the fallback (launch parameters) is a code change to decide on.
6. **TV.** Say what is on screen (expected: the QR sign-in screen). Get past it by route 1 or 2
   above.
7. Write the link and relaunch:

   ```sh
   $TV 'cat > /tmp/com.beb.plxnative.debug/plxnative-playurl' < /tmp/plxnative-playurl
   $TV "luna-send-pub -n 1 luna://com.webos.applicationManager/dev/closeByAppId '{\"id\":\"com.beb.plxnative.debug\"}'"
   $TV "luna-send-pub -n 1 luna://com.webos.applicationManager/launch '{\"id\":\"com.beb.plxnative.debug\"}'"
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

Not run yet.

### LG C1 (2021)

Not run yet.
