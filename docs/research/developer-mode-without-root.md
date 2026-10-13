# Can a Developer Mode app be driven and debugged without root?

Research for [issue #3](https://github.com/CasperEngl/plx-native/issues/3), part of the map in
[issue #1](https://github.com/CasperEngl/plx-native/issues/1). Repo read at `9d2777f`. External
sources read on 2026-10-13. No television was contacted.

## Answer

Yes on the LG C1 (webOS 6), and on the LG G5 while it runs webOS 25 (platform release 10.x), but
through different tools than this repo ships. Developer Mode gives a non-root ssh user, `prisoner`
on port 9922, that can install, launch, close, run commands and copy files. LG's own jail config
gives that user the same `/tmp` as the app up to release 10, so trigger files and logs should be
reachable there.

On platform release 11 (webOS 26) LG's config takes `/tmp` away from the ssh user. The app still
has it, the computer does not. A G5 that receives the webOS 26 upgrade loses the trigger and log
channel as built today.

Launch parameters are a second channel that works on every release: `ares-launch --params` and
Dev Manager both pass them, and a native app receives them as JSON in `argv[1]`. This app ignores
them today.

None of the above has been run on a real unrooted set with this app. The media permissions for
the debug app id are shown on webOS 10.3.1 only.

How to read the labels below:

- **Documented**: stated by LG, or by the source code of the tool or system that does it.
- **Reported**: seen by someone else on a real set, and written down where it can be cited.
- **Unproven**: follows from the above, but nobody has run it with this app on an unrooted set.

---

## 1. Can trigger files be written from a computer, and does the app see the same `/tmp`?

### What the app does

- The debug flavour reads `/tmp/com.beb.plxnative.debug/plxnative-<name>`. A flag is a plain
  `exists()` and a value is a plain `read_to_string()`; neither checks who owns the file.
  `rust-modules/base/src/devtrig.rs:82-84,130-134`, `rust-modules/base/src/paths.rs:423-446`
- The app creates that directory on first use and sets it to mode 1777, but only if it owns it. If
  another user created the directory first, the app leaves the mode alone, and then cannot write
  its own logs there. `rust-modules/base/src/paths.rs:329-387`
- The repo's tooling handles this as root: `mkdir -p` then `chmod 1777` before writing any trigger.
  `tests/run.py:1245-1268`, `tools/tv-ssh:41`

### What Developer Mode gives the computer

- **Documented.** Developer Mode exposes ssh on port 9922, user `prisoner`, no password, with a key
  fetched from the television's Key Server using the passphrase shown on screen.
  <https://webostv.developer.lge.com/develop/getting-started/developer-mode-app>
- **Documented.** LG's command-line tools run commands as that user: `ares-novacom --run "ps aux"`.
  <https://webostv.developer.lge.com/develop/tools/cli-dev-guide>
- **Documented.** webOS Dev Manager writes and reads files as that user over SFTP, and falls back
  to `cat > path` on a plain exec channel when the set has no SFTP.
  `src-tauri/src/plugins/file.rs` in
  [webosbrew/dev-manager-desktop@ea027c8](https://github.com/webosbrew/dev-manager-desktop/tree/ea027c8d7b057657d93563bc616eaabcc2dddf6b),
  `common/connection/src/transfer.rs:95-103,262` in
  [webosbrew/ares-cli-rs@ed48a05](https://github.com/webosbrew/ares-cli-rs/tree/ed48a05897e1b646d2b86f473a2c2d5280daae61)
- **Documented.** webosbrew's Rust rewrite of the ares tools has `ares-push`, `ares-pull` and
  `ares-shell --run` that work against a television. LG's official CLI has the same three commands
  but refuses them on the `tv` profile; only `ares-novacom` is offered there.
  ares-cli-rs `README.md`, `ares-push/README.md`, `ares-shell/README.md`;
  `files/conf/ares.json:20-48` and `bin/ares-shell.js:57-58` in
  [webos-tools/cli@ed7a699](https://github.com/webos-tools/cli/tree/ed7a6994be443207f3427b19f210f6606f004eb6)
- **Reported.** Kodi's webOS guide tells developers to ssh in as `prisoner` on 9922 and run
  `bash -i`, and says "You will be put into /media/developer by default".
  `docs/README.webOS.md:301-316` in
  [xbmc/xbmc@492d01b](https://github.com/xbmc/xbmc/blob/492d01b042761bec828bbb31b1a3d79e34bc7e79/docs/README.webOS.md)
- **Reported.** On webOS 4 and older the unrooted shell has no pseudo-terminal, so Dev Manager
  shows a one-command-at-a-time "dumb shell". Commands still run.
  <https://github.com/webosbrew/dev-manager-desktop/wiki/About-Dumb-Shell>

So `docs/distribution.md:982` ("A Dev Mode user has no shell") is too strong. The user has a
non-root shell inside a jail. What they lack is root, and with it `scp` into the app directory
(`docs/distribution.md:502-504` stands).

### Is it the same `/tmp`?

LG publishes the Developer Mode jail config per platform release at
`https://developer.lge.com/common/file/DownloadFile.dev?sdkVersion=<ver>&fileType=conf`. One file
describes both the jail a Developer Mode native app runs in and the jail the ssh server runs in:
it copies the ssh host keys and mounts `/opt/openssh` (sdkVersion 6.0.0, lines 164-172 and
402-410). Fetched on 2026-10-13:

| Release asked for | `/tmp` for the app | `/tmp` for the ssh user |
| --- | --- | --- |
| 6.0.0 (C1) | system `/tmp`, rw, 1777 (lines 29-33) | the same line; no exception |
| 10.0.0, 10.3.0 | system `/tmp`, rw, 1777 (lines 29-32) | the same line; no exception |
| 11.0.0, 11.2.0, 12.0.0 | system `/tmp`, rw, 1777 (lines 31-34) | **empty, root-owned, mode 0111; only `/tmp/var/log` read-only** (lines 35-40) |

The release 11 text is:

```
if $APPID != com.palm.devmode.openssh
    mount rw /tmp
    chmod 1777 /tmp
    link /tmp /var/tmp
else
    mkdir /tmp
    chown /tmp 0 0
    chmod 0111 /tmp
    mount ro /tmp/var/log
```

- **Documented (by LG's config).** Up to release 10 the ssh user and the app are given the same
  `/tmp`. From release 11 they are not.
- **Reported, release 10 and older.** Until August 2026 Dev Manager uploaded every package to
  `/tmp/devman_dl_<n>.ipk` as `prisoner` and the system installer read it from there, which only
  works if that `/tmp` is the system one. Dev Manager also lists crash reports for a `prisoner`
  connection from `/tmp/faultmanager/crash/`.
  [dev-manager-desktop commit e3fb8a2](https://github.com/webosbrew/dev-manager-desktop/commit/e3fb8a2b1f),
  `src/app/core/services/device-manager.service.ts:77-81`, `src/app/debug/debug.component.html:1-10`
- **Reported, release 11.** On an LG OLED55C31LA on 11.2.0 (webOS 26), an unrooted user ran, in
  Dev Manager's shell:

  ```
  $ id
  uid=5343(prisoner) gid=5000(jailer) groups=29(audio),44(video),505(compositor),509(se),777(crashd)
  $ touch /tmp/testfile
  touch: /tmp/testfile: Permission denied
  $ ls -ld /tmp /media/developer
  drwxrwxr-x    4 root     root   /media/developer
  d--x--x--x    3 root     root   /tmp
  ```

  [dev-manager-desktop issue 403, comment of 2026-08-25](https://github.com/webosbrew/dev-manager-desktop/issues/403).
  This matches LG's release 11 config line for line. The same thread has a 2026 LG C6 and B6
  failing the same way.

That report also settles a point `docs/distribution.md:982-990` left open: the ssh user is uid
5343, gid 5000. It is in the app's group and is not the app's uid (the app was measured as uid
6910 and 6303, gid 5000: `docs/distribution.md:408`, `docs/agent-reference.md:1507`). So the
0640 logs are group-readable to it wherever it can reach the directory. The uid was read on
release 11 only.

### What follows

- **C1 (webOS 6): unproven, expected to work.** Write
  `/tmp/com.beb.plxnative.debug/plxnative-playurl` with `ares-push`, `ares-shell --run`, or Dev
  Manager's Files view. Either launch the app once first so it creates the directory, or create it
  with `mkdir -p -m 1777` so the app can still write its logs there.
- **G5 on webOS 25 (release 10.x): unproven, expected to work** for the same reason. The mapping
  of webOS 25 to release 10.x comes from webosbrew's `appinfo.md` ("Since webOS 25 (10.x)") and
  from the firmware table in `docs/webos5-port.md:108-122`; the G5's own release number was not
  read off a set.
- **Any set on release 11 or later: does not work.** The app's `/tmp` is invisible to the
  computer. Triggers cannot be written and the app's logs cannot be fetched.
  `docs/troubleshooting.md:125-140` and `docs/install-and-verify.md:185` tell users to download
  logs from `/tmp` with Dev Manager; on release 11 that advice cannot work.
- **A shared place that survives release 11 is not established.** LG's config mounts
  `/media/developer` read-write for both sides on every release (11.0.0 lines 431, 691-692), but
  the report above shows its top level is `root:root 775`, so `prisoner` cannot create entries
  there. The installers stage packages in `/media/developer/temp`
  (`lib/install.js:53` in webos-tools/cli, `ares-install/src/install.rs:107-122` in ares-cli-rs),
  and one user in that thread installed successfully on 11.2.0 with LG's current CLI, so that
  directory is writable by `prisoner` on at least one set. Whether the jailed app can read it was
  not found written down anywhere.

---

## 2. Can the app be launched with parameters, and does it read any?

### Launching with parameters

- **Documented.** `ares-launch --device myTV com.example.sampleapp --params "{'url':'www.lge.com'}"`.
  <https://webostv.developer.lge.com/develop/tools/cli-dev-guide>
- **Documented.** Both CLIs and Dev Manager do this by running, as `prisoner`,
  `luna-send-pub luna://com.webos.applicationManager/launch '{"id":…,"params":…}'`.
  `files/conf/command-service.json` and `lib/launch.js:182-191` in webos-tools/cli;
  `ares-launch/src/launch.rs:14-21` in ares-cli-rs;
  `src/app/core/services/app-manager.service.ts:137-141` and
  `src/app/core/services/remote-luna.service.ts:29-32` in dev-manager-desktop
- Dev Manager's Apps screen launches with no parameters
  (`src/app/apps/apps.component.ts:101-103`). Its terminal can run the `luna-send-pub` line by
  hand.
- This path does not touch `/tmp`, so the release 11 change above does not affect it.

### How a native app receives them

- **Documented for web apps only.** LG describes the `webOSLaunch` and `webOSRelaunch` events and
  nothing for native apps.
  <https://webostv.developer.lge.com/develop/guides/app-lifecycle-management>
- **Documented by source, for open-source webOS.** The application manager starts a jailed native
  app as `jailer -t native_devmode -i <id> -p <folder> <binary> <json>`, where `<json>` is the
  caller's `params` object with `event`, `reason`, `appId`, `nid` and `@system_native_app` added.
  So the parameters are the top level of `argv[1]`. A launch of an app that is already running
  sends a `relaunch` event, with the parameters under `parameters`, to whoever called
  `registerApp`.
  `src/bus/client/NativeContainer.cpp:104-120,183-190` and `src/base/RunningApp.h:272-279` in
  [webosose/sam@96161d3](https://github.com/webosose/sam/tree/96161d3e50670fb21daccfb12a75c35fe406ce0e).
  LG's television build of this service is not public.
- **Reported on televisions.** Moonlight reads `argv[1]` as JSON and takes `host_uuid` and
  `host_app_id` from its top level.
  `src/app/platform/webos/app_webos.c:39-64` in
  [mariotaku/moonlight-tv@cf96ecc](https://github.com/mariotaku/moonlight-tv/blob/cf96ecc72cdab3aae7ba0698f463b89065ae7e3b/src/app/platform/webos/app_webos.c).
  Kodi subscribes to `registerApp` and acts on `event == "relaunch"`.
  `xbmc/windowing/wayland/WinSystemWaylandWebOS.cpp:35,196-209` in xbmc/xbmc@492d01b

### What this app does

- It reads no launch parameters. `main` looks at `argv[1]` once, to ask whether it is the path of a
  crash envelope; anything else "proceeds as a normal launch" and the argument is dropped.
  `src/main.c:156-161`, `rust-modules/telemetry/src/telemetry/native.rs:207-229`
- No Rust code reads `std::env::args`, and nothing under `src/`, `rust-modules/` or `pkg/` calls
  `registerApp` or handles a relaunch event. The only use of the application manager is launching
  the home screen. `rust-modules/platform/src/webos.rs:279-304,457`
- `pkg/appinfo.json:13-14` declares `"nativeLifeCycleInterfaceVersion": 2` and
  `"handlesRelaunch": false`.

### What follows

- **Unproven, small to build.** A debug build could parse `argv[1]` and treat, say, a `playurl`
  key the way it treats the `plxnative-playurl` file. That gives a way to hand the app a link on
  every release, including 11.
- It only covers a cold start. Close the app first (`ares-launch --close`, which calls
  `dev/closeByAppId`), then launch with parameters. Parameters sent to a running app arrive as a
  relaunch event, which this app does not subscribe to.
- Moonlight's `appinfo.json` does not set `nativeLifeCycleInterfaceVersion`; this app sets 2.
  Whether a television wraps `argv[1]` differently for version 2 was not found documented. The
  open-source code above does not branch on it.

---

## 3. Install, relaunch, read logs, and get past sign-in

### Install

- **Documented.** `ares-install --device <tv> <file>.ipk`, or Dev Manager's Apps → Install. Both
  copy the package to `/media/developer/temp` and call
  `luna://com.webos.appInstallService/dev/install`.
  LG CLI guide (above); `app-manager.service.ts:202-239` in dev-manager-desktop;
  `ares-install/src/install.rs:107-122` in ares-cli-rs
- **Reported.** On release 11 (webOS 26) Dev Manager 1.99.16 and the old `@webosose/ares-cli`
  2.4.0 fail to install; `@webos-tools/cli` 3.2.5 succeeded on the same set. Dev Manager moved its
  staging directory out of `/tmp` on 2026-08-19 for this reason. Issue 403 and commit e3fb8a2, both
  cited above.
- The package to install already exists: the `cross-build` job packages
  `com.beb.plxnative.debug_*.ipk` with the trigger surface on, and needs no secrets.
  `.github/workflows/ci.yml:370-429`
- Every change needs a full package install. `make deploy` copies into the app directory as root
  and has no unrooted equivalent. `docs/distribution.md:502-504`

### Relaunch

- **Documented.** `ares-launch --close <id>` then `ares-launch <id>`, or the same two calls from
  Dev Manager. `ares-launch --running` lists running apps.
  `ares-launch/README.md` in ares-cli-rs; `files/conf/command-service.json` in webos-tools/cli
- The repo's own relaunch (`tools/tv-session.sh:478-499`) kills the process as root and checks
  that the pid changed. Without root, close-then-launch is the replacement. The repo notes that
  the application manager can keep stale "running" state after a hard kill, making the next
  launch a silent no-op (`docs/agent-reference.md:1373`); whether `dev/closeByAppId` avoids that
  is unproven.

### Read logs

- The app writes `plxnative-events.log`, `plxnative-crash.log` and `plxnative-stderr.log` into its
  runtime directory, mode 0640, so the app's group can read them. `src/main.c:86-99`
- **Unproven, expected to work on release 10 and older**: `ares-pull`, `ares-shell --run 'cat …'`
  or Dev Manager's Files view, since the ssh user is in gid 5000 and sees the same `/tmp`. Live
  following (`tail -f` over `ares-shell --run`) is plausible and unproven.
- **Does not work on release 11 and later**, for the reason in section 1.
- **Documented.** Dev Manager hides its Syslog, dmesg and ls-monitor tabs for a `prisoner`
  connection. Only Crash Reports remains. `src/app/debug/debug.component.html:10-30`
- **Documented.** LG's `ares-log` is refused on the `tv` profile. `bin/ares-log.js:105-106` in
  webos-tools/cli. `ares-inspect` is for web apps and JS services only (LG CLI guide).
- **Reported.** Other native apps keep logs where the ssh user can read them: Kodi under its app
  directory (`docs/README.webOS.md:309-310`). webosbrew's guide says native debugging is done with
  `gdbserver` started from "a shell on the TV", meaning `ares-shell` or plain ssh, and that the
  launcher sets `APPID` where a shell does not. The page is marked a stub and does not say it was
  run unrooted.
  `src/views/develop/guides/gdb.md` and `env-setup.md` in
  [webosbrew/webosbrew.github.io@cbe95e2](https://github.com/webosbrew/webosbrew.github.io/tree/cbe95e2e74cfed28c206ff618a82d821811db42c)
- The repo already has a log channel that needs no shell at all: a `LAB=1` build posts a scrubbed
  log snapshot over HTTPS to a receiver and can poll for commands. Diagnostics are device-verified
  on the developer's own set; the command leg is host-verified only.
  `docs/lab-diagnostics.md:3-12`. `docs/webos10-lab-report.md` is ten such snapshots from a rented
  webOS 10.3.1 set.

### Getting past sign-in

- The play-a-URL trigger is skipped while the app is on the Login or Profiles screen.
  `rust-modules/src/dev/scenarios.rs:915-926`
- The app boots to Login unless it has a usable session or a `plxnative-token` trigger.
  `rust-modules/src/app/boot.rs:883,1007-1145`, `rust-modules/src/dev/scenarios.rs:198-212`
- So today a debug build needs one of:
  - **A one-time on-screen Plex sign-in.** The session is saved at
    `/media/developer/<id>-auth.json` and survives relaunch and reinstall
    (`docs/distribution.md:474-476`). The rented webOS 10.3.1 set did exactly this: run 1 was "no
    session → QR sign-in", runs 2 and 3 used the stored session
    (`docs/webos10-lab-report.md:22-26`). Needs a Plex account, no root.
  - **The `plxnative-token` trigger**, which rides the same `/tmp` channel as every other trigger
    and so has the same release 11 limit. It also assumes a server address compiled in from
    `src/config.local.h`, which the CI build does not have (`src/config.local.h.example:1-8`).
- For the Stremio fork the Plex sign-in screen is being replaced, so the lasting fact is the
  gate, not the mechanism: the trigger must be allowed on whatever the first screen is, or a
  debug build must be able to skip that screen.

---

## 4. Does the installer grant the debug app id the media permissions?

### What the app needs

- Playback goes through LG's media pipeline over the Luna bus. On the stable id, the Developer
  Mode installer wrote a role file granting `com.webos.media.client.*`, `com.webos.rm.client.*`
  and `com.webos.pipeline.*`; the app declares nothing for it. Read off a rooted webOS 4.5 set.
  `docs/distribution.md:430-438`
- The app's `requiredPermissions` are for storage only. `pkg/appinfo.json:17-20`
- **Reported.** Kodi and Moonlight ship no `requiredPermissions` at all and play video from a
  Developer Mode install. `tools/webOS/packaging/appinfo.json.in` in xbmc/xbmc@492d01b;
  `deploy/webos/appinfo.json` in mariotaku/moonlight-tv@cf96ecc
- The device nodes and groups come from the jail config, which is chosen by install location, not
  by app id. `docs/two-installs.md:249-252`. LG's config for 6.0.0 and 10.0.0 both grant
  `video,audio,luna,compositor,crashd,se` (line 23 in each).

### The debug id

- The repo says outright that the role file for `com.beb.plxnative.debug` is "ASSUMED to follow
  it, not observed". `docs/two-installs.md:241-245,463-468`
- **Shown on webOS 10.3.1, by outcome.** The debug id, installed at the Developer Mode location on
  a rented 2024 LG set with no ssh, signed in and direct-played a 4K HEVC Dolby Vision file.
  `docs/webos10-lab-report.md:1-5,38-44`. The role file itself was not looked at, and the report
  notes it cannot prove the package was installed rather than copied
  (`docs/webos10-lab-report.md:762-769`).
- **webOS 6: unproven for the debug id.** The one webOS 6 playback report (6.5.2, six of eight
  attempts played) used the stable id installed through Homebrew Channel, not a Developer Mode
  install. `docs/release-audits/v0.8.0.md:55`,
  [GLinnik21/plx-native issue 22](https://github.com/GLinnik21/plx-native/issues/22)
- **Reported in aggregate, stable id.** The repo's package notes say opt-in usage reports show
  playback "on Developer Mode installs of every firmware line from 4.4.2 to 11.2.0".
  `docs/webosbrew-package.yml:97-99`. The reports themselves are not in the repo.
- **2025 set (G5): unproven.** The nearest evidence is the 2024 set above on the same platform
  release line. LG's release 12 config drops the `se` group (12.0.0 line 23); what that changes
  for playback is unknown.
- No external document was found that describes how LG's television installer generates role
  files. The open-source installer (webosose/appinstalld2) does not contain that logic.

### Known exception

Some 2019 sets on LG's k5lp and k3lp chips cannot play video from a Developer Mode install
because the jail withholds a device, and without root there is no fix. `README.md:80`. Neither
reference set is one of these.

---

## Which of the repo's own "unproven" notes still stand

| Repo statement | Status after this research |
| --- | --- |
| "A Dev Mode user has no shell" (`docs/distribution.md:982`) | Wrong as written. They have a jailed non-root shell. |
| Dev Manager reading `/tmp` logs is "Not yet proven on a real unrooted set" (`docs/distribution.md:987-990`) | Still unproven for this app. Supported by LG's config up to release 10. Contradicted by LG's config and a user report from release 11. |
| Dev Manager's reader is in the app's group (`docs/distribution.md:984`) | Reported true on one release 11.2.0 set: gid 5000, a different uid. |
| "`make deploy` will not work for an unrooted user" (`docs/distribution.md:502`) | Stands. |
| "No `/tmp` trigger can be armed on a lab set" (`docs/lab-diagnostics.md:53`) | Stands for the lab, which has no ssh. Does not carry over to an owner's Developer Mode set on release 10 or older. |
| Role file for the debug id "ASSUMED … not observed" (`docs/two-installs.md:241`) | Still not observed. Playback with the debug id is shown on 10.3.1 only. |

---

## Not determined

Each item has the cheapest check on a real television that would settle it. All of them use the
debug `.ipk` from the `cross-build` job and need Developer Mode only.

1. **Whether a trigger written by `prisoner` reaches the app on the C1 and the G5.**
   Launch the app once and sign in, then
   `ares-shell --run 'ls -ld /tmp/com.beb.plxnative.debug; touch /tmp/com.beb.plxnative.debug/plxnative-login'`
   and relaunch. That trigger forces the sign-in screen even with a stored session
   (`rust-modules/src/dev/scenarios.rs:198-201`), so the result is visible on screen. The `ls`
   alone answers whether the two see the same `/tmp`.
2. **Which platform release the G5 reports, and whether it has the release 11 `/tmp` rule.**
   `ares-shell --run 'id; ls -ld /tmp /media/developer /media/developer/temp; cat /var/run/nyx/os_info.json'`.
   Repeat after any webOS upgrade.
3. **Whether the app's logs can be pulled.** `ares-pull /tmp/com.beb.plxnative.debug/plxnative-events.log .`
   on each set.
4. **Whether a directory under `/media/developer` works as a shared drop on release 11.**
   On a release 11 set, as `prisoner`: write a file into `/media/developer/temp`. Reading it from
   inside the app needs a build that looks there, so this one costs a small code change.
5. **What `argv[1]` looks like on a television for this app.**
   `ares-launch --params '{"probe":"1"}' com.beb.plxnative.debug` with a build that logs `argv[1]`
   to the event log. One log line settles the shape, and whether lifecycle version 2 changes it.
   Costs a one-line code change.
6. **Whether close-then-launch reliably gives a fresh process.**
   `ares-launch --close`, `ares-launch`, and compare the two boot lines in the event log.
7. **Whether the debug id gets media permissions on webOS 6 and on the G5.**
   Install the debug `.ipk`, sign in, play one file. The event log says whether the pipeline
   loaded. The role file cannot be listed without root; playback is the test.
8. **Whether the 1000-hour session, the reboot limit and the one-television-per-account rule
   interfere with keeping two reference sets in Developer Mode.** LG documents the limits
   (Developer Mode page above); how they play out across two sets on one account was not looked
   into here.
