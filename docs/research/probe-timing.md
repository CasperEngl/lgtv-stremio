# Time a probe on the G5

Findings for [issue #19](https://github.com/CasperEngl/lgtv-stremio/issues/19), part of the map in
[issue #1](https://github.com/CasperEngl/lgtv-stremio/issues/1). It feeds the "give up after 5
opens" limit chosen in [issue #10](https://github.com/CasperEngl/lgtv-stremio/issues/10).

**Result: one probe of a cached stream takes 1.2 to 1.7 s for a Matroska file and 2.6 to 3.6 s for
an MP4 file on the LG G5, and every track's language comes back. The 5-open limit stands.**

## How it was measured

- **Where.** On the LG G5 (OLED65G54LW, webOS 10.3.1), in the app's own process, on 2026-10-14.
  The app's bundled demuxer (FFmpeg, `libavformat-plx.so.63`) read the file through the app's own
  HTTPS transport (`curlio`, the set's libcurl 7.82.0). No `ffprobe` and no desktop were involved.
- **With what.** The debug package built from `main` plus log lines in the demuxer's open sequence:
  a clock started at the first request, the bytes the demuxer had read, a count of its seeks, and
  each track's codec, channel count and `language` tag. The patch is
  [`ff-probe-timing.patch`](https://github.com/CasperEngl/lgtv-stremio/blob/research/probe-timing/docs/research/probe-timing/ff-probe-timing.patch)
  on branch `research/probe-timing`. It was applied only on the build-only branch
  `build/probe-timing` (CI run 38478436127, package sha256 `263cb6fd…e1d024`), which never merges:
  upstream's files stay unedited on `main` (decision record 0001).
- **The setup** is the on-TV playback test's: Developer Mode ssh, the play-a-URL trigger file, and
  the stand-in server behind a reverse tunnel to get past sign-in
  (`docs/research/on-tv-playback-test.md` on branch `wayfinder/on-tv-playback-test`).
  `run-probe.sh` on the research branch does one run: fresh launch, wait for the track list, pull
  the event log, close the app, remove the link from the set.
- **The streams.** Two cached streams of one film, both from Comet with Real-Debrid, chosen and
  approved by the owner: a 26.7 GB Matroska file (HEVC 3840x1608, 34 tracks) and a 65.8 GB MP4 file
  (HEVC 3840x2160, 7 tracks). Each was opened three times, a fresh app launch each time.
- **What the clock covers.** From the moment before the transport's first request until
  `avformat_find_stream_info` returned, which is when the track list exists. In this build the
  player's `Load` runs at the same time on another thread (147 to 226 ms, app log); a probe in the
  real app would run before it.

## Figures

Every figure below is **measured on the set, from the app's event log**, unless marked derived.

| | Matroska, 26.7 GB | MP4, 65.8 GB |
| --- | --- | --- |
| First request to track list, runs 1 / 2 / 3 | 1.675 / 1.304 / 1.228 s | 3.625 / 2.566 / 2.923 s |
| First request to response headers | 0.801 / 0.531 / 0.476 s | 1.581 / 0.456 / 0.488 s |
| Bytes the demuxer read before the track list | 594,816 / 600,640 / 600,742 | 12,002,859 / 11,997,811 / 11,996,243 |
| Requests for the link (first open plus one per seek) | 3 | 4 |
| Audio tracks' language | `eng` | `eng`, `spa` |

- **Median**, derived from the three runs: 1.30 s for Matroska, 2.92 s for MP4.
- **Each seek asks for the link again** and is redirected again; the transport does not keep the
  redirect's target. One such round trip took 0.25 to 0.37 s in 14 of the 15 seeks and 0.86 s in
  one (seek begin to seek done, app log). Derived: seeks are 0.61 / 0.53 / 0.52 s of each Matroska
  probe and 0.98 / 1.00 / 1.50 s of each MP4 probe.
- **Why the MP4 is slower.** Its index sits at the end of the file and is 9.5 MB: the demuxer had
  read 16,384 bytes before the seek to it and 9,490,499 after reading it, 0.6 to 0.7 s of
  transfer. The Matroska file needed 27,200 bytes to open and 0.6 MB in all.
- **Bytes on the wire: not determined.** The figures are bytes handed to the demuxer. The
  transport held 0 to 8,192 received bytes beyond them when the track list was known (measured),
  and whatever it had received on a connection it then left at a seek was not counted.

## Does each audio track's language come back?

**Yes, for both containers** (measured): the bundled demuxer fills the `language` tag for every
audio and subtitle track of the Matroska file and for both audio tracks of the MP4 file. The app
does not read it today; it is one `av_dict_get` call on the same dictionary the app already reads
each track's `title` from. The Matroska file's video track had no language tag; the MP4's had `eng`.

**Channel counts need care.** The demuxer reported 4 channels for the Matroska file's E-AC-3 track,
which `ffprobe` on a desktop reported as 7.1 during the on-TV playback test. The MP4's two tracks
reported 6. The bundled FFmpeg has no audio decoders, so the count is whatever the container or
parser states. One file, not investigated: the automatic pick's "most channels the set can take"
rule cannot rely on this number until it is.

## Seconds to recognise an error clip

**Not determined.** No error clip turned up: all six opens answered HTTP 200 with the full file
length. Opening an uncached stream on purpose was out of bounds for this ticket.

## Does the 5-open limit stand?

Yes. Derived from the slowest run of each kind: five opens that all miss cost
5 × 1.675 = 8.4 s for Matroska files and 5 × 3.625 = 18.1 s for large MP4 files with the index at
the end. With the medians it is 6.5 s and 14.6 s. The prototype found a playable stream on the
first open for 3 of 5 titles, so the usual wait is one probe: 1.2 to 3.6 s.

What the figures do not cover: one film, one evening, one network path and one debrid file server;
three runs each, which shows a spread but not a tail; no MP4 with its index at the front (expected
faster, not measured); no error clip.

## What this suggests for the build

- Reading `language` is confirmed to work, so the stream-pick's wanted-language rule can be built
  as decided.
- If probes ever need to be faster, the cheapest lever is to keep the redirect's target for seeks:
  it would remove two or three link round trips per probe. Not needed for the limit to stand.

## Raw outputs

On branch [`research/probe-timing`](https://github.com/CasperEngl/lgtv-stremio/tree/research/probe-timing/docs/research/probe-timing):
the patch, `run-probe.sh`, `mk-trigger.py`, the two ssh wrappers, and the six scrubbed event logs
under `logs/`. Links, paths, addresses and long tokens are scrubbed.

## Left on the set

The instrumented build is still installed under the debug app id (`com.beb.plxnative.debug`). It
behaves like the unmodified app and writes extra `probe-timing:` lines to its event log. The
unmodified package is at `/media/developer/temp/plx.ipk` on the set for whoever wants it back. No
trigger file, tunnel or helper server of this ticket remains.
