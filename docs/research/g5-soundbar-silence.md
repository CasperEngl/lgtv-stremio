# Find out why the app is silent through an HDMI soundbar on the G5

Working notes for [issue #37](https://github.com/CasperEngl/lgtv-stremio/issues/37), part of the map in
[issue #1](https://github.com/CasperEngl/lgtv-stremio/issues/1). It continues
[`g5-dolby-vision-dts.md`](g5-dolby-vision-dts.md) and uses its wrappers and trigger helper.

**Status: postponed by the owner on 2026-10-14, unresolved.** One start was made with the soundbar
selected; whether it was audible was not observed. Nothing below names a cause.

## Read from the code and the saved logs

- The player feeds the set raw audio packets and names only the codec in the Load: `AC3`,
  `AC3 PLUS`, `AAC` or `DTS` (`rust-modules/media/src/player/engine.rs`, `audio_payload_codec`,
  `PAYLOAD_AV` with `"needAudio":true`). It never names an output device.
- On webOS 5 and later there is no ACB library (`src/starfish.c`, `vp_mode`), so the app makes no
  audio call outside the Load. On webOS 4 its one ACB audio call is the Atmos descriptor.
- The repository's only word on passthrough is `docs/playback-settings.md`: "Audio passthrough
  remains the television's Digital Sound Output setting". Nothing mentions ARC, eARC or a soundbar.
- Every saved start on the TV speakers shows the same audio lines: `smp_cb type=8` (the format
  built), `type=17` (an `ADEC` granted), `type=7` (track info) and `type=10001` with
  `"audioSinkType":"main_sound"`; `type=10002` closes it.

## The set's sound settings can be read over ssh

Measured on the G5 as the Developer Mode user. Both calls answer; `com.webos.service.apiadapter`
refuses ("Not permitted").

```sh
docs/research/on-tv-playback-test/tv-luna.sh luna://com.webos.settingsservice/getSystemSettings \
  '{"category":"sound","keys":["soundOutput","eArcSupport","soundOutputDigital"]}'
docs/research/on-tv-playback-test/tv-luna.sh luna://com.webos.service.audio/master/getVolume '{}'
```

| When | Sound output | Digital sound output | eARC | Volume |
| --- | --- | --- | --- | --- |
| 01:03, as found | `tv_speaker` | `auto` | `on` | 10 |
| 01:06, after the owner switched | `external_arc` | `auto` | `on` | 40 |
| 01:10, during playback | `external_arc` | `auto` | `on` | 71 |

So a step the owner takes at the set can be checked remotely before building on it. Writing these
settings over ssh was not tried.

## The one start made

Unmodified debug package from `9d2777f` (installed binary sha256 `2db5cf28…056c`, equal to the
package's), sound output `external_arc` from before the app started, Dune: Part Two declared as
HEVC, E-AC-3, Dolby Vision profile 8.

- **Seen by the owner:** not observed. The question "do you hear sound from the soundbar?" was not
  answered. The owner had said beforehand that the soundbar "was maybe off" during the earlier
  silent runs; that is not confirmed either.
- **Implied by the app's log**
  ([`g5-soundbar-selected-events.scrubbed.log`](g5-soundbar-silence/g5-soundbar-selected-events.scrubbed.log)):
  `load: v=H265 a="AC3 PLUS"`, `type=8 audio/x-eac3`, `type=17` with `ADEC` port 1, `type=7`,
  `type=10001 … "audioSinkType":"main_sound"`, position advancing. These are the same lines as a
  TV-speakers start, so on this evidence the log does not tell the two outputs apart. The log goes
  on to one seek and two items of the stand-in server's library (H.264 with AC-3, then AAC), each
  with a granted `ADEC`; none was observed for sound.

## Which build the earlier runs used

At 00:38 another session ("Time a probe on the G5") installed an instrumented build under the same
app id (binary sha256 `3d50e3c6…13c4`, 12,561,788 bytes against the package's 12,557,668). It
describes it as the unmodified app plus extra log lines. The Dolby Vision and DTS runs checked the
hash before their first launch only, so those after 00:38, and the owner's soundbar observation
with them, may have run on that build. This session reinstalled the unmodified package from
`/media/developer/temp/plx.ipk` (sha256 matched) at 01:08.

## Still to record

Everything the ticket asks: the soundbar's model and connection; sound per digital sound output
setting for AC-3 and E-AC-3; AAC stereo; a silent start's log beside an audible one; one DTS Load
with the soundbar as output.

## Left on the set

The three trigger files removed, the app closed (`dev/running` lists nothing), the tunnel and the
stand-in server stopped. The unmodified debug package is installed. Sound output is `external_arc`
as the owner set it; it was `tv_speaker` when this session began.
