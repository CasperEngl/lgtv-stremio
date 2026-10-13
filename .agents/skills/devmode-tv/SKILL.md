---
name: devmode-tv
description: >
  Drive an unrooted LG set (the G5) over Developer Mode ssh as `prisoner` on port 9922.
  Use before any install, launch, trigger file or log pull on that set, and when
  `tools/tv-lock.sh` answers "no TV configured".
---

# Developer Mode sets

`tv-lock`, `tv-session` and `wake-tv` drive upstream's rooted set as `root`; the fork's set gives a
jailed `prisoner` shell instead. Measured detail and results: `docs/research/on-tv-playback-test.md`.
Its folder holds the wrappers: `tv-ssh.sh '<command>'` runs one command on the set, and
`tv-luna.sh <uri> '<json>' [seconds]` makes one bus call and waits for the reply.

1. **See who is on the set first.** List installed and running apps and read the tail of
   `/tmp/<app id>/plxnative-events.log`. When another build or a recent session shows, ask the
   user who is using the set as a question of its own, and keep to read-only commands until they
   answer. Two builds share one app id, so an install replaces the other session's.
2. **Bus calls**: `luna-send-pub -i <uri> '<json>' & sleep 3; kill $!`. With `-n 1` the command
   exits before the reply prints and `launch` does not start the app.
3. **Files in `/tmp/<app id>/`**: the folder is mode 1777, so `prisoner` creates files there and
   removes its own. A file the app's user wrote stays until `/tmp` is cleared, and the app keeps
   its uid across a reinstall.
4. **Clearing `/tmp`** takes pulling the set's power plug. The remote's power button is a standby
   and the bus refuses `reboot` to `prisoner`. Proof: `uptime` near zero.
5. **A port on this machine the set cannot reach**: `ssh -N -R <port>:127.0.0.1:<port>` to the
   set, then point the app at `127.0.0.1`. Save the tunnel's PID and kill that PID afterwards.
6. **Leave the set clean**: remove every trigger file you wrote, close the app, stop tunnels and
   helper servers. Scrub links, `path=` values and addresses from any log before it is committed.

**Done when** the set holds no trigger file of yours and `dev/running` no longer lists the app.
