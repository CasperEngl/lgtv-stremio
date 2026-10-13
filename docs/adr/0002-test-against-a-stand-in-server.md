---
status: accepted
---

# Test the unchanged app against a stand-in server

Host tests and the simulator run the app as the television runs it, with its real network code,
against a stand-in server that answers as Stremio's API, the add-ons and the debrid service would.
`stremio-core` offers a cheaper seam (every request passes through one function, `Env::fetch`, and
its own tests swap that function for a table of answers), and we chose not to test there: a pass
should mean the code the television runs passed, and the same stand-in server can feed a real
television that has no account.

## The rules this sets

- **The app is not told it is under test.** The one non-real part is an address override, needed
  because `stremio-core` fixes `api.strem.io`, `link.stremio.com` and Cinemeta in its source.
  A request the stand-in server has no answer for fails the test.
- **Add-on answers are recorded; the account is invented.** Recorded answers keep the real release
  names the automatic pick and the stream list must parse. The user, library and Continue Watching
  are made up, so nothing from a real library can be committed.
- **A link is replaced the moment it is recorded.** The raw answer never reaches the disk. The
  recording tool runs only on the owner's machine. A required check refuses a committed recording
  that contains an address outside a short allowed list (the stand-in itself and public hosts such
  as Cinemeta's images). Release names, filenames, sizes and torrent hashes stay.
- **Recorded titles are taken by rank** from Cinemeta's public popular catalogue on the recording
  day, six at most, and the owner sees the list before it is committed.
- **The stand-in server answers stream links as Comet does:** `200` with a status clip while a
  file is "downloading", `302` to the file when ready, a different clip when refused. The files
  are small generated clips. No real film and no copy of Comet's own clips is committed.
- **On a host the track list is supplied.** The app's demuxer is built for 32-bit ARM only, so one
  tool writes each clip and its track list together; a host reads the list, a television reads the
  clip.
- **Recordings are redone by hand,** when the pinned `stremio-core` is upgraded or a television
  check disagrees with the stand-in. Nothing automatic talks to the real services, so no account
  secret is stored outside the owner's machine.
- **The simulator uses the stand-in server by default** and signs in through its link code. The
  real account is behind an explicit switch on the owner's machine, and with it no stream link is
  ever opened.

## What must pass before a change lands

All on GitHub, with no secrets: upstream's `CI` unchanged; the check that upstream's files are
unedited; the Stremio crates' host tests against the stand-in server; the ARM build and package.
A simulator build-and-launch check joins them once a Stremio simulator exists.

## What is only ever verified on a television

Neither tier is required for a change to land.

1. **With the stand-in server and no account:** the whole flow from link-code sign-in to playback
   of generated clips, with the real demuxer reading tracks, the wait on a status clip and the
   redirect. Run by hand until driving a set without root is proven.
2. **With the owner's real account, by the owner, before each release:** real sign-in, one cached
   stream the owner chooses, progress appearing in another Stremio client. A real error clip is
   checked only when one happens on its own, an uncached stream only when the owner chooses it.
   Never automated.

Picture, text rendering, frame rate, audio formats and responsiveness on the 2021 set are
television-only as well.

## Considered options

- **A table of answers swapped in at `Env::fetch`,** as `stremio-core`'s own tests do. One
  mechanism and no second program, but the HTTP client, redirects and the link-opening code would
  go untested on a host, and a television could not use it.
- **Generate every answer,** as upstream's `tests/mock_pms.py` does for Plex. Needs no scrubbing,
  but tests the automatic pick against release names nobody published.
- **A scheduled check against the real services.** Rejected: it needs the account's add-on
  configuration as a secret on GitHub.

## Consequences

- A stream list is large: 421,524 bytes for one film's 192 streams, 79% of it links (measured
  2026-10-14). With links replaced that is about 450 bytes a stream, so six titles at the 512
  streams a title seen earlier come to about 1.4 MB of plain JSON.
- The recognition of Comet's real status and refusal clips is never tested on a host or in CI.
- The simulator part depends on the Stremio top crate building for a desktop with upstream's
  simulator feature, which is unproven. If it cannot without editing upstream's files, the
  simulator rules here are reopened; the host tests and the stand-in server stand either way.
