---
status: accepted
---

# Carry verbatim copies of upstream's webOS window glue and keyboard code

The Stremio top crate needs upstream's webOS window glue (`rust-modules/src/system.rs`, 870 lines:
window surface, opaque region, bus pump, frame probe, 12 of the 24 port-table entries) and its
on-screen keyboard code (`rust-modules/src/textinput.rs`, 790 lines), and both are private to
upstream's top crate. The fork carries its own verbatim copies of the two files in the Stremio
crates and offers upstream nothing for now. Moving them into a layer crate is a design change, not
a file move (`system.rs` names `plx_telemetry`, which sits above the `platform` layer, and
`textinput.rs` takes its SDL declarations from the top crate); upstream's `docs/module-layers.md`
records the decision to leave the port's members where they are "until a second TV OS exists"; and
the move would help only the fork, so the rule in
[the first decision record](https://github.com/CasperEngl/lgtv-stremio/pull/14) that changes useful
to a Plex client are offered upstream does not ask for it.

## The rules this sets

- **Upstream's private files are off limits.** The Stremio crate does not compile them where they
  sit, although a `#[path]` line pointing at each was measured to compile on the host with no edit
  to either file. The fork builds only its own files and upstream's public functions, which is the
  line the first decision record draws, and a copy means each upstream change to the glue is read
  as a patch at the weekly merge instead of arriving unread.
- **The copies are verbatim.** Each is upstream's file at a recorded upstream commit, edited only
  where the fork cannot compile or behave correctly otherwise. Upstream's later changes are applied
  to the copy as patches, not re-made by hand.
- **A blocking check keeps them in step.** The Stremio workflow fails when either original differs
  from the commit its copy records. The weekly upstream merge applies upstream's change to the copy
  and moves the recorded commit forward before it lands, so a copy never lags by more than a week.
- **Only files that stand alone are copied.** A private upstream file is copied this way only when
  a few lines in the Stremio crate can supply everything it names. Today that is these two. The
  window creation, frame loop and remote-key decoding (`app/boot.rs`, `app/run.rs`,
  `app/events.rs`) are written against upstream's app, its Plex start-up and its screens, so Rill's
  are written fresh, with upstream's as a reference and no check tying the two together.

## Considered options

- **Compile upstream's two files in place.** No copy and no patch step, and a change upstream shows
  as a compile error at the weekly merge. Ruled out by the owner: it reaches past the line of new
  files and public functions, and upstream's changes to the glue would arrive without anyone
  reading them.
- **Offer the move upstream, with or without copies in the meantime.** Rejected for now: it asks
  upstream to reverse a decision it wrote down, for a benefit only the fork gets, and waiting on
  the answer would block the first milestone, which is the top crate's own window.
- **Trimmed copies the fork owns.** About 300 of `system.rs`'s lines are a frame-timing probe built
  only into developer builds, and Rill could drop it. Rejected: every upstream change would then be
  read and re-made by hand, and the probe is compiled out of a release build anyway.

## Consequences

- Most weekly merges carry a patch step: upstream changed `system.rs` 16 times and `textinput.rs`
  14 times in the three months to 2026-10-14.
- The Stremio crate declares the `hostsim` and `devtriggers` features and forwards them to
  upstream's crates, depends on `libc`, and supplies the seven SDL names the keyboard code expects
  from its own SDL declarations. Forwarding matters: declared but not forwarded, the developer
  triggers compile and never fire.
- The copies alone do not make the keyboard work. Rill's own window code has to hand it the window
  and route text events to it.

## Reopen this decision when

- upstream moves the window glue or the keyboard code out of its top crate itself: the fork drops
  that copy and depends on upstream's crate; or
- upstream's change fails to apply cleanly to a copy at two weekly merges running: the fork then
  chooses between offering the move upstream and trimming the copies into code it owns.
