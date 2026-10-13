# Which audio each LG model year decodes, and whether the app can ask the television

Research for [issue #6](https://github.com/CasperEngl/plx-native/issues/6). Repo read at `9d2777fe`; web sources fetched 2026-10-13.

## Answer

- AAC, AC-3 and E-AC-3 are listed by LG for every webOS version from 3.0 to 26, and no source found says any 2018-2025 set fails to decode them. The limits are in the details: AAC Main profile is unsupported everywhere, and channel ceilings are published nowhere by LG; the one measured set stops AAC and AC-3 at 6 channels and E-AC-3 at 8.
- DTS varies by television, not only by year: 2018-2019 yes, 2020-2022 reported no, 2023-2024 only on some models, 2025 reported no. The webOS version does not settle it, because 2022 sets upgraded to webOS 23 or later still lack DTS.
- The television can be asked in two ways. Its codec table (`/etc/umediaserver/device_codec_capability_config.json`) lists audio codecs with channel counts, and this repo already reads it. A system setting, `tv.model.edidType`, contains `dts` on sets that support DTS; Kodi, Jellyfin and Stremio's own LG app use it, and this repo does not.
- Today the app decides per television from the codec table, falls back to a fixed `aac,ac3,eac3` when the table is unreadable, and has no list by model year, chip or webOS version.

## 1. How this repo decides audio capability today

### The codec table lists audio, and the app reads it

The table is `/etc/umediaserver/device_codec_capability_config.json` (`rust-modules/platform/src/devcaps.rs:59`). It has an `audioCodecs` array beside `videoCodecs`; each audio row carries a name and a channel count (`rust-modules/platform/src/devcaps.rs:217-244`):

```rust
struct Table {
    #[serde(default, rename = "videoCodecs")]
    video_codecs: Vec<VideoRow>,
    #[serde(default, rename = "audioCodecs")]
    audio_codecs: Vec<AudioRow>,
}
struct AudioRow {
    #[serde(default)]
    name: String,
    #[serde(default)]
    channels: u32,
}
```

The only real table in the repo is from the development set, a 2019 49SM9000PLA on webOS 4.10.2, captured 2026-08-10. Its audio rows are MPEG 2, AAC 6, AC3 6, EAC3 8, DTS 6, FLAC 6 (`rust-modules/platform/src/devcaps.rs:434-436`, `489-519`). There is no table from any other set in the repo.

The file format is LG's own. The open-source edition of webOS ships the same file with the same `audioCodecs` rows of `name` and `channels` (https://github.com/webosose/umediaserver-configs/blob/554dc3e7c754516156eec739c09a0dd348d4d390/raspberrypi4/device_codec_capability_config.json.in).

### What the app builds from it

The app can feed four audio codecs: `pub const DP_AUDIO_CODECS: &str = "aac,ac3,eac3,dts";` (`rust-modules/platform/src/devcaps.rs:57`). The result of the boot-time read is two fields of `Caps` (`rust-modules/platform/src/devcaps.rs:109-116`):

```rust
pub audio: String,                                        // the four, intersected with the table's rows
pub audio_channels: std::collections::BTreeMap<String, u32>,  // per-codec channel ceiling
```

The rules, from `parse` (`rust-modules/platform/src/devcaps.rs:313-335`):

- A codec is in `audio` only if the table has a row with its name. Names are matched ignoring case, dots and dashes, so `E-AC3` and `EAC3` are the same (`devcaps.rs:194-202`).
- A channel ceiling is recorded only from a row with a nonzero `channels`. Two rows for one codec keep the smaller number (`devcaps.rs:315-322`).
- DTS needs more than a row: it is admitted only if its row also has a nonzero channel count (`devcaps.rs:327`). This is the "measured DTS row" in `docs/agent-reference.md:1844-1848`.
- If the table parses but names none of the four codecs, the app treats that as a misread and uses `aac,ac3,eac3` (`devcaps.rs:329-335`; test at `devcaps.rs:672-679`).

The check applied to a chosen track (`rust-modules/platform/src/devcaps.rs:145-153`):

```rust
pub fn audio_supports(&self, codec: &str, channels: i64) -> bool {
    if !self.audio_has(codec) {
        return false;
    }
    match self.audio_channels.get(codec) {
        Some(&limit) => (channels > 0 || codec != "dts") && channels <= i64::from(limit),
        None => codec != "dts",
    }
}
```

So AAC, AC-3 and E-AC-3 with no recorded ceiling pass at any channel count; DTS never passes without a ceiling, and never with an unknown channel count.

### A missing or unreadable table

`probe` falls back to `Caps::assumed()` when the file cannot be read or parsed, and logs which happened (`rust-modules/platform/src/devcaps.rs:371-423`). The assumed profile is the development set's old constants: `audio: "aac,ac3,eac3"` with no channel ceilings (`devcaps.rs:123-137`). On such a set DTS is never fed, and AAC, AC-3 and E-AC-3 are fed at any channel count. The whole table is also rejected, with the same fallback, when it has no video rows, no H.264 row, or no stated video size (`devcaps.rs:251-312`). `measured()` records whether the table was read (`devcaps.rs:425-428`).

A table that is read but omits one codec simply drops that codec: a set whose table lacks an `EAC3` row would not be fed E-AC-3.

### No list by model year, chip or webOS version

`rust-modules/platform/src/webos.rs` reads the webOS release and codename from `/var/run/nyx/os_info.json` and the model and board names from the device-info file (`webos.rs:17-19`, `107-120`). None of it feeds an audio decision. Across the crates, the webOS major version is used for the VP9 bit depth (`devcaps.rs:361-367`, `388`), a player event mapping (`rust-modules/media/src/player/mod.rs:2295`), diagnostics and telemetry; the board name is used for a sandbox check and telemetry (`webos.rs:224`). Nothing maps year, chip or version to audio codecs.

### Where the result is used

- `plex::is_dp_audio_track(codec, channels)` is `caps().audio_supports(codec, channels)` (`rust-modules/plex/src/plex/transcoder.rs:29-36`). Its comment names the cases it exists for: "devices whose DTS decoder stops at 5.1 or whose AAC decoder stops at stereo".
- Route planning asks it whether a track can be fed directly: `audio_direct_plays` (`rust-modules/media/src/route/plan.rs:2583-2589`), language matching (`plan.rs:2444`), the conversion preview (`plan.rs:3144`), and the enhancement grade (`plan.rs:831`). `decision.rs` uses it to guess a remux's output codec (`rust-modules/media/src/route/decision.rs:8566`).
- The Direct Play setting "Force" skips the television's table and accepts all four codecs at any channel count (`plan.rs:2584-2585`).
- The Plex profile lists the same set and adds one channel limit per recorded ceiling (`rust-modules/plex/src/plex/transcoder.rs:272-286`). This is the Plex side and would not carry over to Stremio.
- The player turns the codec into LG's name for it and refuses anything else rather than mislabel it (`rust-modules/media/src/player/engine.rs:770-778`, `1310-1318`). The declaration carries no channel count or AAC profile (`engine.rs:58`).

### Format handling that bears on "safe"

- AAC is reframed as ADTS and always declared as AAC-LC, with the core sample rate read from the stream's own configuration so HE-AAC plays through the decoder's implicit extension. The comment records a real HE-AAC 5.1 title that crackled before this (`rust-modules/media/src/ff.rs:3371-3405`). An AAC channel configuration outside 1-7 falls back to stereo in the header (`ff.rs:3379-3396`).
- E-AC-3 with Atmos is fed as ordinary `AC3 PLUS` plus an `"immersive":"ATMOS"` field (`rust-modules/media/src/player/engine.rs:849-868`).
- DTS-HD is cut down to its DTS core before feeding (`rust-modules/media/src/ff.rs:3242-3247`, `8523-8528`).

### What has been measured on a television

- 2019 set, webOS 4.10.2: AAC, AC-3 and E-AC-3 are the everyday path. DTS 5.1 and a DTS-HD MA 5.1 core passed every pipeline check with the television muted; "These results do not claim audible output verification" (`docs/playback-settings.md:91-99`). The release note says "DTS audio has not been heard on a television" (`docs/release-notes/v0.8.0.md:74`).
- 2024 set (model `k24`, webOS 10.3.1, rented remotely): E-AC-3 with Atmos and AAC were both loaded and played (`docs/webos10-lab-report.md:218`, `226`, `299`). The log line `audio=aac,ac3,eac3 (device table)` (`docs/webos10-lab-report.md:52`) is from 2026-08-27, a month before DTS was added to the app's list (commit `0031e2fe`, 2026-09-27), so it does not show whether that set's table has a DTS row.
- No measurement from a 2020-2023 or 2025 set is in the repo.

### The other thing the television can be asked

The repo already makes one call to the television's configuration service, `luna://com.webos.service.config/getConfigs`, for the Dolby Vision key (`rust-modules/platform/src/webos/caps.rs:13`, `136-140`). It does not ask for any audio key. Its own notes say the call "has not yet been measured on device" from this app's unprivileged registration (`docs/dolby-vision.md:434-436`).

Other players ask the same service for `tv.model.edidType` and look for `dts` in the answer:

- Kodi's webOS port: `SupportsDTS()` returns whether `tv.model.edidType` contains `dts`, and DTS is added to the codecs it feeds only then (https://github.com/xbmc/xbmc/blob/492d01b042761bec828bbb31b1a3d79e34bc7e79/xbmc/platform/linux/WebOSTVPlatformConfig.cpp#L75-L78, https://github.com/xbmc/xbmc/blob/492d01b042761bec828bbb31b1a3d79e34bc7e79/xbmc/cores/VideoPlayer/MediaPipelineWebOS.cpp#L205-L207). Kodi installs through Developer Mode and states webOS 5.0 or newer (https://github.com/xbmc/xbmc/blob/492d01b042761bec828bbb31b1a3d79e34bc7e79/docs/README.webOS.md).
- Stremio's own LG app starts with DTS and TrueHD marked unsupported and lifts each when `tv.model.edidType` names it (https://github.com/Stremio/stremio-video/blob/e0019bba3ad75993d5d807aebd39803fc128d908/src/WebOsVideo/WebOsVideo.js#L93-L125).
- Jellyfin's LG app does the same (https://github.com/jellyfin/jellyfin-webos/pull/221).

Where the key comes from: Kodi's webOS maintainer wrote that he "did look into how LG's apps are detecting dts support", gave the command and an example answer `"tv.model.edidType": "TrueHD+dts"`, and added that he was unsure what it returns on webOS 4.x and older (https://github.com/jellyfin/jellyfin-webos/issues/190#issuecomment-2054107367 and the two comments after it). Reported, not LG documentation. The Jellyfin author could not test it because LG's emulators do not answer the key (https://github.com/jellyfin/jellyfin-webos/pull/221).

Known weakness, reported: on a rooted 2025 set where a community patch restores the DTS decoder, the key still says no DTS (https://github.com/NuvioMedia/NuvioTVSmart/pull/460). A Stremio feature request claims the key reflects the connected HDMI device rather than the television's decoder and so hides DTS on 2023-2024 sets that decode it (https://github.com/Stremio/stremio-features/issues/1904); that claim conflicts with the maintainer's account above and is unverified.

## 2. What each model-year group decodes

LG's developer site publishes one "AV format" page per webOS version. The pages describe the television's media player for files and web apps; they do not describe the buffer-feed route this app uses, and they give no channel limits for AAC, AC-3 or E-AC-3 inside video files. "Dolby Digital" is AC-3 and "Dolby Digital Plus" is E-AC-3. LG's year mapping: webOS 4.x is 2018-2019, 5.x is 2020, 6.x is 2021, 22 to 25 are 2022 to 2025 (https://webostv.developer.lge.com/develop/specifications/web-api-and-web-engine).

Source grades: **A** LG documentation or a file read from a television; **B** source code of a shipping player, or a statement LG made to a named outlet; **C** press or forum report, unverified.

| Model year (webOS as shipped) | AAC, AC-3, E-AC-3 | DTS | Channel limits | Sources |
|---|---|---|---|---|
| 2018 (4.0) | All three listed for .mp4, .mkv and .ts. (A) | Listed for .avi and .mkv with no restriction. (A) | Not published. | [4.0 page](https://webostv.developer.lge.com/develop/specifications/video-audio-40) |
| 2019 (4.5) | All three listed. (A) Fed daily on the development set. (A, in repo) | Listed for .avi and .mkv. (A) Development set's table has a DTS row; pipeline accepted DTS 5.1, sound not heard. (A, in repo) One owner reports a 2019 OLED plays DTS. (C) | One set measured: AAC 6, AC-3 6, E-AC-3 8, DTS 6. (A, in repo) | [4.5 page](https://webostv.developer.lge.com/develop/specifications/video-audio-45); `devcaps.rs:489-519`; `docs/playback-settings.md:91-99`; [report](https://github.com/jellyfin/jellyfin-webos/issues/190#issuecomment-2054110449) |
| 2020-2022 (5.0, 6.0, 22) | All three listed. (A) Kodi feeds all three without a check; Jellyfin assumes AC-3 and E-AC-3. (B) | LG's pages still list DTS for .mkv (dropped from .avi). (A) Players and owners say it is not decoded: Jellyfin's source, Kodi's maintainer, an Emby moderator in 2020 (thread read through a search summary only). (B, C) The two disagree; no set measured. | Not published. | [5.0](https://webostv.developer.lge.com/develop/specifications/video-audio-50), [6.0](https://webostv.developer.lge.com/develop/specifications/video-audio-60), [22](https://webostv.developer.lge.com/develop/specifications/video-audio-220) pages; [Jellyfin source L117-L118](https://github.com/jellyfin/jellyfin-web/blob/e74f66f101b1ab32f74a555e82658eb2728759ab/src/scripts/browserDeviceProfile.js#L117-L118); [Emby thread](https://emby.media/community/topic/87802-no-audio-on-lg-oled-cx-for-dts) |
| 2023-2024 (23, 24) | All three listed. (A) E-AC-3 with Atmos and AAC played on one 2024 set. (A, in repo) | "available in specific models only". (A) 2023: "from the QNED85 and up plus all OLED TVs", LG Korea to FlatpanelsHD. (B) 2024: decoded for the speakers and passed over HDMI. (C) | Not published. | [23](https://webostv.developer.lge.com/develop/specifications/video-audio-230), [24](https://webostv.developer.lge.com/develop/specifications/video-audio-240) pages; [FlatpanelsHD 2023](https://www.flatpanelshd.com/news.php?subaction=showfull&id=1672916807); [FlatpanelsHD 2025](https://www.flatpanelshd.com/news.php?subaction=showfull&id=1743140114); `docs/webos10-lab-report.md:218-226` |
| 2025 (25) | All three listed. (A) | "Some models may not support ... DTS". (A) Reported removed from the whole range, from the G5's HDMI data and unnamed insiders; no LG statement. (C) A G5 owner's diagnostic shows no DTS decoder. (C) | Not published. | [25 page](https://webostv.developer.lge.com/develop/specifications/video-audio-250); [FlatpanelsHD 2025](https://www.flatpanelshd.com/news.php?subaction=showfull&id=1743140114); [G5 report](https://github.com/josippapez/dts_restore_plus/issues/5) |

Notes on the table:

- **Atmos in E-AC-3.** LG's pages do not mention it. Kodi declares E-AC-3 Atmos with the same `"immersive":"ATMOS"` field on every webOS version it runs on (5.0 and newer) with no capability check (https://github.com/xbmc/xbmc/blob/492d01b042761bec828bbb31b1a3d79e34bc7e79/xbmc/cores/VideoPlayer/MediaPipelineWebOS.cpp#L685-L686) (B). This repo played it on the 2024 set (A, in repo). Atmos in E-AC-3 is designed as an extension that a plain E-AC-3 decoder skips (stated from general knowledge of the format; no source fetched); whether 2018 sets render it as Atmos was not looked up.
- **The oldest sets.** The webOS 3.0 and 3.5 pages (2016-2017) list the same three codecs for .mp4, .mkv and .ts, and DTS for .avi and .mkv (https://webostv.developer.lge.com/develop/specifications/video-audio-30, https://webostv.developer.lge.com/develop/specifications/video-audio-35) (A).
- **Year is not webOS version.** LG upgrades older sets to newer webOS versions. A 2022 G2 upgraded to webOS 23 reports version 23 and still has no DTS; Emby's developer: "upgrading a G2 to webOS 2023 isn't enough to enable DTS support" and "checking the webOS version is no longer enough" (https://emby.media/community/topic/127933-webos23-and-dts/) (C); Kodi's maintainer says the same (https://github.com/jellyfin/jellyfin-webos/issues/190#issuecomment-2054107367) (B).
- **Within a year, models differ.** 2023 sets below the QNED85 are outside LG Korea's statement, and LG's own pages for 23 to 26 say DTS depends on the model.

## 3. Does "AAC, AC-3 and E-AC-3 are always safe" hold?

At the level of codec names, every source agrees and none contradicts it: LG lists all three on every webOS version from 3.0 to 26, with no "some models" footnote on any of them, while it does put that footnote on DTS, AC-4 and WMA (pages linked in section 2). Kodi's codec map contains AC-3, E-AC-3 and AAC unconditionally (https://github.com/xbmc/xbmc/blob/492d01b042761bec828bbb31b1a3d79e34bc7e79/xbmc/cores/VideoPlayer/MediaPipelineWebOS.cpp#L98-L104), and Jellyfin returns true for AC-3 and E-AC-3 on webOS without testing (https://github.com/jellyfin/jellyfin-web/blob/e74f66f101b1ab32f74a555e82658eb2728759ab/src/scripts/browserDeviceProfile.js#L97-L100, `#L130-L133`). On-set evidence in this repo covers two televisions, 2019 and 2024.

Exceptions and gaps found:

- **AAC Main profile.** "AAC Main profile is not supported", on every page from 3.0 to 26 (A). The app declares every AAC track as AAC-LC and does not check the profile (`rust-modules/media/src/ff.rs:3403-3405`), so an AAC Main track would be fed and mis-declared.
- **AAC above 5.1.** The one measured table stops AAC at 6 channels (`devcaps.rs:495-498`). The repo's own comment anticipates sets "whose AAC decoder stops at stereo" (`rust-modules/plex/src/plex/transcoder.rs:32-33`), without naming one. When the table is unreadable the app applies no ceiling at all (`devcaps.rs:134-135`, `149-152`).
- **AC-3 and E-AC-3 channel counts.** Measured once: 6 and 8 (`devcaps.rs:500-508`). Not published by LG.
- **HE-AAC.** Not mentioned by LG either way. It plays on the 2019 set after the header fix (`rust-modules/media/src/ff.rs:3371-3377`). Jellyfin tests for it at run time on every platform instead of assuming it (https://github.com/jellyfin/jellyfin-web/blob/e74f66f101b1ab32f74a555e82658eb2728759ab/src/scripts/browserDeviceProfile.js#L994-L1000). No evidence for other years.
- **AAC in MKV.** Listed for .mkv on every page (A). Not a separate risk for this app: it demuxes the container itself and feeds ADTS frames whatever the container (`ff.rs:3403-3405`).
- **4K files.** LG's pages restrict the audio of Ultra HD .mkv, .mp4 and .ts files to exactly Dolby Digital, Dolby Digital Plus and AAC, on every version (A). That is the same three.
- **Route.** LG's pages cover file playback. That the same decoders sit behind the buffer-feed route is shown by this repo on two sets and by Kodi on 5.0 and newer, not by LG.

## What a fixed rule and a per-television rule would each rest on

A **fixed rule** ("AAC, AC-3 and E-AC-3 only, on every television") would rest on:

- LG's per-version pages listing the three codecs without model restrictions, 3.0 to 26.
- Kodi and Jellyfin shipping the same assumption on webOS.
- The repo's own fallback already being this list (`devcaps.rs:134`).
- The map's measurement that no sampled title needed DTS (issue #1).
- It would not cover channel counts or AAC Main, which no fixed codec list expresses, and it would leave DTS unused on 2018-2019 and some 2023-2024 sets.

A **per-television rule** would rest on one or both of:

- The codec table, which the repo reads today. It supplies codec names and channel ceilings. Its content is known for one 2019 set only. LG's published pages kept listing DTS for 2020-2022 while players report it missing, so whether a 2020-2022 set's table also still lists DTS is an open risk: if it does, the table alone would send DTS to a set that plays it silent.
- `tv.model.edidType`, which three shipping players use for DTS and TrueHD only. It says nothing about AAC, AC-3, E-AC-3 or channels. Its origin is a maintainer's reverse reading, it is unanswered on LG's emulators, it is reported wrong on patched sets, and whether this app's unprivileged call receives it is unmeasured.

The two reference sets sit on the two sides of the DTS question that are least documented: the 2021 C1 is in the "LG lists it, players say no" group, and the 2025 G5 is in the "reported removed" group.

## Not determined

- What the codec table contains on any set other than the 2019 development set: in particular whether a 2020-2022 or 2025 set has a DTS row, and whether any set omits AAC, AC-3 or E-AC-3 or gives a lower channel count.
- Whether the codec table is readable from a Developer Mode install on every supported webOS version (it was read on the 4.10.2 development set and, through Developer Mode, on the 10.3.1 set: `docs/webos10-lab-report.md:40-52`).
- Whether this app's unprivileged call can read `tv.model.edidType`, and what the key returns on webOS 4.x and on the C1 and G5.
- Whether `tv.model.edidType` reflects the television's decoder or the connected HDMI device.
- Channel ceilings for AAC, AC-3 and E-AC-3 on any set but one; whether any supported set limits AAC to stereo.
- Whether AAC Main, HE-AAC v2 or xHE-AAC tracks occur in Comet's streams, and what a set does when fed AAC Main declared as AAC-LC.
- Whether DTS fed through this route is audible on any set; only pipeline acceptance was measured, muted.
- Whether a set without a DTS decoder refuses a DTS declaration or plays silence.
- Which 2023 and 2024 models below LG's stated line lack DTS, and LG's own confirmation for 2020-2022 and 2025 (only reports were found).
- Whether E-AC-3 with Atmos is rendered as Atmos on 2018-2019 sets.
- LG product manuals for the C1 and G5 were not retrieved.
