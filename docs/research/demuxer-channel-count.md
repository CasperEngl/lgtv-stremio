# Why the bundled demuxer reports 4 channels for a 7.1 E-AC-3 track

Research for the ticket
[Why does the bundled demuxer report 4 channels for a 7.1 E-AC-3 track?](https://github.com/CasperEngl/lgtv-stremio/issues/43),
2026-10-14. No television and no stream link were used.

Each fact is tagged **read** (from source or a log, with the place), **run** (executed on this
machine, output in `demuxer-channel-count/repro-output.txt`) or **derived** (reasoned from the
others).

## Answer

The 4 is real, and it is the wrong number. It is what FFmpeg's AC-3 parser derives when FFmpeg is
built without an E-AC-3 decoder, which is how the app's bundled FFmpeg is built. It is not what the
file states and it is not a misread of the struct.

A 7.1 E-AC-3 track carries each moment of sound as two frames: an independent substream (a
complete 5.1 programme) followed by a dependent substream holding the channels that turn it into
7.1. The parser reports the channel count of the **last frame in the packet**. For 7.1 that is the
dependent substream, which codes 4 channels of its own.

The count is right for AC-3, AAC and any E-AC-3 track with no dependent substream. It is wrong for
every E-AC-3 track that has one, in Matroska and in MP4.

The right number can be read from the track's first packet with about 60 lines of the app's own
code, shown working in `demuxer-channel-count/chprobe.c`.

## The mechanism

All line numbers are FFmpeg 9.0, the version `ci/build-ffmpeg.sh` pins. The tarball's SHA-256 was
checked against the script's (**run**).

1. **The bundled FFmpeg has the AC-3 parser and no audio decoder.** **Read:**
   `ci/build-ffmpeg.sh`, `--enable-parser=h264,hevc,aac,ac3,dvdsub,dvbsub` and a decoder list of
   subtitle formats only. **Run:** the same flags give `CONFIG_AC3_PARSER 1`,
   `CONFIG_EAC3_DECODER 0`, `CONFIG_AC3_DECODER 0`, `CONFIG_AAC_DECODER 0` in
   `config_components.h`.
2. **Without the decoder, the parser overwrites the track's channel layout from a frame header.**
   **Read:** `libavcodec/aac_ac3_parser.c:132-140`. The condition is
   `if (!CONFIG_EAC3_DECODER || avctx->codec_id != AV_CODEC_ID_EAC3)`. A desktop FFmpeg has the
   decoder, so for E-AC-3 its parser leaves the layout alone and the decoder supplies it. That is
   why desktop `ffprobe` and the app disagree about the same file.
3. **The header it uses is the last frame's.** **Read:** `aac_ac3_parser.c:109-125`. A loop steps
   over every frame that is followed by another (`buf += hdr.frame_size; continue;`) and stops on
   the final one. The dependent substream always follows its independent substream, so for a 7.1
   track the final frame is the dependent one.
4. **A frame's own count ignores the channel map.** **Read:** `libavcodec/ac3_parser.c:383`,
   `hdr->channels = ff_ac3_channels_tab[hdr->channel_mode] + hdr->lfe_on`. The dependent
   substream's channel map, which says where its channels go, is parsed (`ac3_parser.c:148-162`)
   but not used for the count.
5. **Both containers hand the parser a packet holding both frames.** **Read:** Matroska sets
   `AVSTREAM_PARSE_HEADERS` for every audio codec except AAC, MP3, MLP and TrueHD
   (`libavformat/matroskadec.c:2890-2895`), so the parser sees each block whole. MP4 sets
   `AVSTREAM_PARSE_FULL` for AC-3 and E-AC-3 (`libavformat/mov.c:3144-3150`), and the parser joins
   a dependent frame to the frame before it (`ac3_parser.c:466`).
6. **The parser's value replaces the container's.** **Read:** `avformat_find_stream_info` copies
   the parser's context over the track's parameters (`libavformat/demux.c:2580`) and restores only
   colour fields from the container afterwards (`demux.c:2584-2598`).

FFmpeg's own decoder counts differently. **Read:** `libavcodec/ac3dec.c:1598-1615` starts from the
independent substream's speakers and adds every location the dependent substream's channel map
names. That is the rule `chprobe.c` copies.

## Reproduction on this machine

`demuxer-channel-count/run-repro.sh` builds FFmpeg 9.0 with the app's component list, makes
fixtures, and prints two readings for each. It was **run** on x86-64 Linux; the build reports
libavformat 63, libavcodec 63, libavutil 61, the majors the app binds.

Two differences from the shipped build: it is a native build, not 32-bit ARM, and it adds
`--disable-x86asm` because `nasm` is not installed. Neither touches a parser or a demuxer.

The E-AC-3 fixtures are FFmpeg's own test samples (`fate-suite.ffmpeg.org/eac3/`), remuxed with
`-c copy`. FFmpeg's E-AC-3 encoder cannot write a dependent substream, so a 7.1 track could not be
generated. The rest are generated tones.

| Track | Desktop `ffprobe` | App's FFmpeg, Matroska | App's FFmpeg, MP4 |
| --- | --- | --- | --- |
| E-AC-3 7.1 (`the_great_wall_7.1`) | 8 | **4** | **4** |
| E-AC-3 5.1 | 6 | 6 | 6 |
| E-AC-3 stereo | 2 | 2 | 2 |
| AC-3 5.1, AC-3 stereo | 6, 2 | 6, 2 | 6, 2 |
| AAC stereo, 5.1, 7.1 | 2, 6, 8 | 2, 6, 8 | 2, 6, 8 |
| DTS 5.1, TrueHD 5.1 | 6, 6 | 6, 6 | not made |

All **run**. The 7.1 track's first packet, read by hand in `chprobe.c`:

```
frame 0: ac3 acmod=7 lfeon=1 own_channels=6 size=2304
frame 1: eac3 dependent substream=0 acmod=5 lfeon=0 own_channels=4 chanmap=0x1a00 size=2304
counted=8
```

The dependent frame codes 4 channels, which is the number the parser reports. Its channel map
names left surround, right surround and the rear pair. Added to the independent frame's six
speakers that makes 8 (**run**), matching the decoder.

## The three questions

**Is 4 what the file states, what the parser derives, or a misread?**

- **What the parser derives.** Shown above, **read** and **run**.
- **Not what the file states.** In the fixture the Matroska header led to 8 and the MP4 header
  to 6, and both were replaced by 4 (**run**: `header=8 probed=4` and `header=6 probed=4`). MP4's
  6 is because FFmpeg reads only the independent substream's fields from the `dec3` box
  (**read**: `mov.c:1146-1160`).
- **Not a misread.** **Read:** `ci/ffabi-assert.c` pins `AVCodecParameters.ch_layout` at offset
  112 and `sample_rate` at 136 for 32-bit ARM, and `AVChannelLayout.nb_channels` at 4, compiled
  against the bundled headers by the build. **Read:** the same log lines carry `sr=48000` from the
  neighbouring field and `ch=6` for the MP4's tracks. **Derived:** a host build through FFmpeg's
  real headers gives the same 4, so no misread is needed to explain the number.
- **Not determined:** what the Matroska header of the film measured on the G5 states. Finding out
  means opening its link, and the answer would change nothing, since the parser replaces it.

**Is it right for AC-3, AAC and plain 5.1 E-AC-3, and wrong only with dependent substreams?**

- **AC-3: right.** One frame per packet, no substreams (**run**, stereo and 5.1, both containers).
- **AAC: right for the cases run.** The parser never touches an AAC track's count
  (**read**: `aac_ac3_parser.c:99` skips the channel code for AAC), so the number is the
  container's (**run**: stereo, 5.1, 7.1). **Not determined:** HE-AAC v2, where the container can
  state one channel for a track that plays as two. No encoder for it is installed here.
- **E-AC-3 without a dependent substream: right** (**run**, stereo and 5.1, both containers).
- **E-AC-3 with a dependent substream: wrong, in both containers** (**run**, one 7.1 sample).
  **Derived:** the wrong number is whatever the dependent substream codes, so it is not always 4.
- **Atmos: not run**, no fixture. **Derived:** an Atmos track is misreported exactly when its
  packets hold a dependent substream, and reads correctly when they do not.
- **DTS and TrueHD:** the bundle has no parser for either, so the number is the container's
  (**run**, Matroska 5.1). Both are risky audio and do not enter the pick's channel rule.
- **Not determined:** MPEG-TS, and E-AC-3 with more than one independent substream.

**What should the automatic pick do?**

Keep the rule "most channels the set can take" and change where an E-AC-3 track's number comes
from.

- **AC-3 and AAC:** the probe's number, as now.
- **E-AC-3:** the app counts from the track's first packet: the independent substream's speakers
  plus every location in the dependent substream's channel map. `chprobe.c`'s `walk_packet` is that
  rule in about 60 lines, and it returned 8, 6 and 2 for the three samples (**run**), each equal
  to desktop `ffprobe`.
- **E-AC-3 when no packet could be read:** the count is unknown. The track stays a safe audio
  track and ranks as 5.1 for the "most channels" comparison. **Derived:** 5.1 is the commonest
  independent substream, so this is the number least likely to mis-order two tracks; it is a
  default, not a measurement.
- **Never treat an E-AC-3 track as over the set's channel ceiling because of this count.** The
  G5 played the measured 7.1 track (**read**:
  `docs/research/on-tv-playback-test.md` on branch `wayfinder/on-tv-playback-test`).

Reading that packet should cost no further request. **Read:** `avformat_find_stream_info` keeps
the packets it read and `av_read_frame` returns them first (`demux.c:2810-2811`, `1597-1598`), and
the parser can only have produced a number for a track whose packet it saw. **Not measured on the
set.**

Fixing it inside FFmpeg instead is not open. **Derived:** enabling the E-AC-3 decoder would stop
the parser overwriting the count, but it means editing upstream's `ci/build-ffmpeg.sh`, and MP4
would then report the `dec3` box's 6 for a 7.1 track.

## What this does not change

- **Playback.** **Read:** the only place the player uses the count is the AAC header it writes
  (`rust-modules/media/src/ff.rs`, `adts_params`). An E-AC-3 track is handed to the television
  without it, which is why the 7.1 track played on the G5 while reporting 4.
- **Probe timing.** The figures in `docs/research/probe-timing.md` stand.

## Files

- `demuxer-channel-count/run-repro.sh`: builds, makes fixtures, prints both readings.
- `demuxer-channel-count/chprobe.c`: the probe, and the counting rule.
- `demuxer-channel-count/repro-output.txt`: the output of the run reported here.
