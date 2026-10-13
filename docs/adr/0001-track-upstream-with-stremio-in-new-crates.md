---
status: accepted
---

# Track upstream PlxNative, with Stremio code in new crates and new files

This repository is a fork of PlxNative (`GLinnik21/plx-native`, the `upstream` remote) and a
separate product for good: upstream is never asked to carry Stremio. The fork keeps merging
upstream's `main` and puts all Stremio code in new crates and new files beside upstream's, leaving
upstream's files unedited and its Plex crates compiled in but unused. One maintainer lands over 100
commits a week on the player, demuxer, drawing and firmware support the app needs (92, 111, 132 and
148 in the four weeks to 2026-10-13), and the player can already start on a link Plex did not
choose through existing public functions, so staying mergeable costs nothing in playback and
diverging would give that work up.

## The rules this sets

- **New files only.** Stremio code, its cargo workspace, its build script, its CI workflow and its
  agent instructions live in new files and folders. An edit to a file upstream owns needs a
  recorded reason in one list of exceptions, which is meant to stay near empty. Whether the Stremio
  crates can build and link this way is unproven and is the build plan's first thing to show.
- **Upstream's `CI` workflow stays untouched and must be green after every merge.** It runs on the
  fork without secrets or a Plex server and passed on `main` with `prototype/` present. Stremio
  code is checked by its own workflow. Upstream's layering check (which only reads `plx_*` crates
  under `rust-modules/`) and its build budget (72 third-party packages, 13.8 MB) do not apply to
  Stremio crates; the fork sets its own limits once there is a binary to measure.
- **Upstream's release tooling is switched off in the fork's GitHub settings, not deleted.**
  Release, Release candidate, Nightly, the site deploy and the site video would publish PlxNative
  under its own name. The fork's release path is a new workflow.
- **Changes useful to a Plex client are offered upstream, and the fork does not carry them.** Each
  goes as its own pull request from a branch cut from upstream's `main`, signed off as
  `CONTRIBUTING.md` requires. Until upstream merges one, the fork works around the gap in its own
  crates (for example, writing `:443` into a link because the parser defaults to port 32400).
- **Upstream is merged weekly, as a merge commit.** `upstream/main` comes in through a pull request
  that lands only when upstream's `CI` and the Stremio workflow are both green; a compile error in
  the Stremio crates from a changed player function is fixed in that pull request. This is the one
  kind of commit on `main` that is not a squash: squashing upstream's commits would hide them from
  git and make every later merge conflict with itself. The fork's own work still lands as squashes.

## Considered options

- **Track upstream with about 19 one-line edits to the player**, so the engine stops naming the
  Plex crate. Rejected: the edits sit in the files upstream changes most (`ff.rs` 110 commits and
  `player/engine.rs` 85 in three months) and playback does not need them.
- **Diverge: delete the Plex code and split the player from route selection.** A smaller binary and
  only the code the app uses, but 251 upstream commits touched the player's side in three months
  and each would be ported by hand or dropped.
- **Aim to land Stremio in PlxNative itself.** Rejected: it would bind every new crate to
  upstream's layering, naming and budget rules and make the plan wait on a maintainer's view of
  debrid streams in a Plex client.

## Consequences

- The Plex code ships in the binary, unused. Its size cost has not been measured.
- The fork depends on a handful of public player functions keeping their shape (`set_url`,
  `set_stream_declaration`, `begin_resume`, `set_audio_track`, `request_subtitle`,
  `start_bufferfeed`). A change upstream shows as a compile error at the weekly merge, not as a
  merge conflict.
- Upstream's `AGENTS.md` says `main` takes squash merges only; in this fork the weekly upstream
  merge is the stated exception.

## Reopen this decision when

- the list of edited upstream files passes five entries; or
- the weekly merge takes more than a day of fixing two weeks running; or
- upstream removes or reshapes the public player functions so playback can no longer start without
  editing its files.
