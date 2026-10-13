# Play Dolby Vision and a DTS track on the G5

Working notes for [issue #30](https://github.com/CasperEngl/lgtv-stremio/issues/30), part of the map in
[issue #1](https://github.com/CasperEngl/lgtv-stremio/issues/1). It continues
[`on-tv-playback-test.md`](on-tv-playback-test.md), whose checklist, wrappers and trigger helper
it uses. Run on 2026-10-14 on the LG G5 (OLED65G54LW, webOS 10.3.1) with the unmodified debug
package from `9d2777f`; the installed binary's sha256 matched the package's before the first launch.

**Result.** Dolby Vision plays. A DTS track does not: the set refuses the player's Load.

| Run | Declared | Outcome |
| --- | --- | --- |
| Dune: Part Two | HEVC, E-AC-3, Dolby Vision profile 8 | Plays in Dolby Vision |
| Inception | HEVC, DTS | Refused, no picture |
| Inception (control) | HEVC, AC-3 | Plays, HDR10 |
| Inception (repeat) | HEVC, DTS | Refused again |

## What the trigger can declare (read from the code)

- **Dolby Vision**: a `dovi` object, `{"profile":8,"bl_compat":1,"el_present":false}`
  (`rust-modules/media/src/player/playurl.rs`). The node reaches the Load only when the set's
  configd answer is "supported" and `vcodec` is spelled `hevc`; `h265` selects the HEVC payload
  but drops the Dolby Vision node (`route/decision.rs`, `set_stream_declaration_with_capability`).
  A dual-layer file (`el_present`) is refused.
- **DTS**: `acodec` is a free string and `"dts"` (lower case) maps to the Load's `"DTS"`
  (`player/engine.rs`, `audio_payload_codec`). Any other spelling fails the start.
- **The DTS track need not be the file's first.** The demuxer feeds the first audio track whose
  codec equals `acodec` (`ff.rs`, `audio_stream_matching`). For DTS it feeds the core only and
  discards DTS-HD extensions (`ff.rs`, `dts_core_packet`).

`on-tv-playback-test/make-trigger.py` now writes both: `--dovi-profile 8 --dovi-bl-compat 1`, and
`--acodec dts`. The prototype's `play` never picks a DTS track, so `--line N` takes the link from
a saved `streams <type> <id> --urls` listing and refuses a line not marked cached.

## How it was run

As in the first run: the stand-in server (`tests/mock_pms.py --host 0.0.0.0 --port 32499`), a
reverse ssh tunnel for that port, and the trigger files `plxnative-token` and
`plxnative-pms-origin` (`http://127.0.0.1:32499`). Per run: write `plxnative-playurl`, launch,
read the log, close with `dev/closeByAppId`, remove the trigger.

One correction to the checklist: **the trigger file must be readable by the app's user.** The
app runs as another uid in group `jailer`, so mode 0640 works and 0600 does not.

Links: Dune from `play movie tt15239678` (one stream opened by the prototype's probe, then by the
set). Inception from `streams movie tt1375666 --urls` saved to a mode-0600 file, the approved
line opened once with `ffprobe` on this machine and three times by the set. All cached.

## Run 1: Dolby Vision

**The stream** (measured with `ffprobe`): Dune: Part Two, 26.7 GB Matroska, HEVC Main 10
3840x1608 at 23.976 fps, Dolby Vision profile 8, first audio track E-AC-3 7.1 English. The same
file as the first run. Trigger: `vcodec hevc`, `acodec eac3`, `fps 23.976`,
`dovi {profile 8, bl_compat 1}`.

**Seen at the set (the owner watching):**

| Check | Result |
| --- | --- |
| Badge | Dolby Vision |
| Sound | Yes, from the set's speakers |
| Lip sync | In sync |
| Stutter | Smooth |

**Implied by the app's log** ([`g5-dolby-vision-events.scrubbed.log`](g5-dolby-vision-dts/g5-dolby-vision-events.scrubbed.log)):

- `dv: sourceInfo contents.DolbyHdrInfo profileId=8 trackType=single encryptionType=clear` and
  `load: v=H265 a="AC3 PLUS" fps=23.976 dv=present:1 P8/1 el:0`.
- The decoder reported `"hdrType":"DolbyVision"`, 3840x1608, 23.976 progressive. The first run,
  without the `dovi` object, got `"hdrType":"HDR10"` from the same file.
- Five Loads (the start and four seeks, to 132 s, 145 s, 410 s and 959 s), each returning in
  139-202 ms and each answered `DolbyVision`. Playback reached 1028 s.
- The presented-frame counter: 4566 frames over 953 polls of 200 ms, which is 23.96 frames a
  second (4566 / (953 x 0.2 s)). No `sink: dropped` line.

## Run 2: DTS

**The stream** (measured with `ffprobe`): Inception, 26.2 GB Matroska, HEVC Main 10 3840x1598 at
23.976 fps, HDR10 (PQ), no Dolby Vision. Audio track 1 is DTS-HD MA 5.1 English, track 2 is AC-3
5.1 Hindi. Trigger: `vcodec hevc`, `acodec dts`, `fps 23.976`.

**Seen at the set (the owner watching):** no picture; the player's message "Playback failed. This
TV could not start the video stream". The same on the repeat.

**Implied by the app's log** ([first](g5-dolby-vision-dts/g5-dts-first-events.scrubbed.log),
[repeat](g5-dolby-vision-dts/g5-dts-repeat-events.scrubbed.log)), identical both times:

```
load: v=H265 a="DTS" fps=23.976 dv=present:0 P0/0 el:0 atmos:0 max=3840x2160@60
smp_cb type=8 num=0 str=audio/x-dts (null) (null) 0.000000 1 (null) 0 0 0 0 dts 0 (null) 0
smp_cb type=18 num=601 str=Resource Allocation Error
smp: Load refused by the pipeline before any picture (type=18 num=601) — failing the source
```

- The set's pipeline accepted the word `DTS` and built `audio/x-dts` caps, then refused the Load.
  No decoder grant (`type=17`) was logged. The refusal comes before any audio is fed, so it does
  not depend on this file or on its track being DTS-HD.
- The link itself opened (HTTP 200 after one redirect) and the demuxer logged
  `ff: DTS core extraction on`.
- The app's stderr from the repeat ([`g5-dts-repeat-stderr.scrubbed.log`](g5-dolby-vision-dts/g5-dts-repeat-stderr.scrubbed.log))
  holds `GStreamer-CRITICAL … gst_element_factory_create_with_properties: assertion 'factory != NULL' failed`
  stamped at that launch. The first run's stderr (85 bytes) had no such line. That points at a
  GStreamer element the set does not have; which element was not determined.

**Control: the same file declared as AC-3**
([`g5-ac3-control-events.scrubbed.log`](g5-dolby-vision-dts/g5-ac3-control-events.scrubbed.log)).
Run between the two DTS attempts. Seen by the owner: picture and sound, not in English (track 2
is the Hindi dub). Log: `load: v=H265 a="AC3"`, a `VDEC` and an `ADEC` granted, Load returned in
178 ms, `"hdrType":"HDR10"`, 4580 frames over 953 polls (24.0 a second), none dropped. So the
file, the link, the video declaration and the set's state are ruled out: the DTS declaration is
the only difference between a Load that is granted and one that is refused.

**What this does and does not show.**

- The G5's codec table lists DTS (`devcaps: … audio=aac,ac3,eac3,dts`, logged at every boot), and
  the set still refuses a DTS Load from this player. The table is not evidence that a track plays.
- This is the player's own path (the app feeds elementary streams to LG's pipeline). Whether LG's
  built-in player decodes DTS on this set was not tested.
- Sound output was set to the TV speakers with a soundbar attached over HDMI eARC/ARC (the
  owner's answer). Whether the Load is granted with the output set to the soundbar was not tested.
- Why the pipeline refuses is not determined beyond the two log lines above.

## Seen along the way: no sound through the soundbar

Reported by the owner, unprompted: with the set's sound output switched to the soundbar (HDMI
eARC/ARC), this app played no sound and the soundbar did not react, on both Dune (E-AC-3 7.1) and
the Inception control (AC-3 5.1). Switching back to the TV speakers during playback brought the
sound back. The soundbar plays other apps on the same set. Nothing in the app's log was matched
to it, and the cause is not determined. The first run's "sound present" was therefore a
TV-speakers result.

## Left on the set

Nothing of this run: the three trigger files were removed, the app closed (`dev/running` lists
nothing), the tunnel and the stand-in server stopped. No new crash record. The debug package
and the other installed app (`com.beb.plxnative`) were left as found.
