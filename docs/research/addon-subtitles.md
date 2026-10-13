# How an add-on's subtitles reach the app's subtitle renderer

Research for the ticket [How do an add-on's subtitles reach the app's subtitle renderer?](https://github.com/CasperEngl/lgtv-stremio/issues/48)
on the map [Stremio on LG webOS: plan the first version](https://github.com/CasperEngl/lgtv-stremio/issues/1).
Done 2026-10-14.

## Short answer

- `stremio-core` asks every installed subtitle add-on itself and keeps the answers on the player
  model. An entry is an address, a language code and an id. The host downloads the file and draws it.
- The two subtitle add-ons asked here answer in full with no file hash, size or filename.
- They serve SubRip text converted to UTF-8 by the server. A copy of the app's own cue reader
  indexed all 1,328 cues of one downloaded file.
- The existing sidecar path cannot take an add-on's address: it accepts only a Plex stream key on a
  registered Plex server. Its fetch, store and reader are private to upstream's file.
- The smallest new path is one new file in the Stremio crate: fetch with upstream's public network
  call, read the cues, and draw each line with upstream's public caption draw.
- Subtitle tracks inside the file use a separate store and a separate selector, so they are
  unaffected.

Every fact below says where it came from and whether it was **read** (source or documentation),
**run** (a command executed for this ticket) or **derived** (reasoned from the two).

## What was looked at

| Source | Version |
|---|---|
| `stremio-core` | `c4806e8614452fd49d5dbb22db74afa88959b554`, the commit `prototype/Cargo.toml` pins, read from cargo's checkout |
| Stremio add-on SDK documentation | `Stremio/stremio-addon-sdk` at `ec4e0a49e61bac4f2285891d39414dfbafe93f58` |
| This repository | `5da16c85`, which holds upstream PlxNative at `9d2777fe` |
| The fork's Stremio crate | `stremio/` on branch `wayfinder/desktop-simulator` |
| The account's add-on list | the prototype's saved profile, read for add-on names, hosts and declared resources only |
| Live add-on answers | `opensubtitles-v3.strem.io` and `subtitlesv2.strem.io`, asked on 2026-10-14 from a desktop with `curl` |

No stream or playback link was opened. No television was used. No FFmpeg, desktop or bundled, was
run.

## 1. What a subtitle entry carries, and where it sits

**The entry.** `Subtitles` has five fields: `id` (text), `lang` (text), `url` (an address), an
optional `label`, and a list of `fonts` addresses that is usually empty. *Read:*
`src/types/resource/subtitles.rs`.

The SDK documentation lists `id`, `url` and `lang` as required and `label` as optional, and says
`lang` holds an ISO 639-2 code or, failing that, free text to show as written. It does not mention
`fonts`. *Read:* `docs/api/responses/subtitles.md`.

Entries have no format field, no encoding field and no flag for hearing-impaired or forced
subtitles. The format is only known from the address or from the file itself. *Read:* same files.

**Two places an entry can come from.**

1. A subtitle add-on's answer. These sit on the player model as
   `Player.subtitles: Vec<ResourceLoadable<Vec<Subtitles>>>`, one element per add-on asked, each
   with its request and a loading, ready or failed state. An add-on that answers with an empty list
   is stored as failed with `EmptyContent`. *Read:* `src/models/player.rs` lines 106-110,
   `src/models/common/resource_loadable.rs` lines 264-275.
2. The stream itself. A stream may carry its own `subtitles` list, which stays on
   `Player.selected.stream.subtitles`. Core does not merge it into `Player.subtitles`. *Read:*
   `src/types/resource/stream.rs` lines 66-84; no code in `player.rs` copies one list into the
   other.

Core does not download a subtitle file, and holds no subtitle text. *Read:* no fetch of
`Subtitles.url` exists in the crate; the only uses of the type are the two lists above. This
matches what [What does stremio-core give a host for each first-version screen?](https://github.com/CasperEngl/lgtv-stremio/issues/4)
found.

**What the official web host adds when it reads the model.** It flattens the per-add-on lists
into one, replaces each `id` with `<add-on address>_<position>` so ids from different add-ons cannot
collide, and attaches the add-on's name as `origin`. An entry's own `id` is therefore not unique
across add-ons. *Read:* `stremio-core-web/src/model/serialize_player.rs` lines 219-248.

**What core remembers about the choice.** Three things, all supplied by the host:

- `StreamItemState.subtitle_track` (`id`, `embedded` true or false, optional `language`),
  `subtitle_delay` in milliseconds, `subtitle_size` and `subtitle_offset`, saved per stream when the
  host dispatches `StreamStateChanged`. *Read:* `src/types/streams/streams_item.rs` lines 26-70.
- `SubtitlePreference` (`enabled`, optional `source` of `Embedded` or `External`, optional
  `language`), kept for the player session across loads. *Read:* `src/types/player.rs` lines 27-41.
- Account settings: `subtitles_language` (default `eng`), `secondary_subtitles_language`,
  `subtitles_auto_select` (default true), `ass_subtitles_styling` (default false), and size, font
  and colour settings. *Read:* `src/types/profile/settings.rs` lines 25-36 and 81-92. On the owner's
  account the saved values are `eng`, none, true and false. *Run:* read from the prototype's saved
  profile.

## 2. When the add-ons are asked, and what the request needs

**The host starts it by naming a path.** The player's `Load` action carries
`Selected.subtitles_path`, a resource path the host builds: resource `subtitles`, the title's type,
and the video id (`tt0111161` for a film, `tt0944947:1:1` for an episode). With no path, core asks
nobody and the list stays empty. *Read:* `src/models/player.rs` lines 88-94 and 1575-1643.

**Core then asks every installed add-on that covers the path.** An add-on is asked when its
manifest lists the `subtitles` resource, its types include the path's type, and its id prefixes
(if it has any) match the id. *Read:* `AggrRequest::AllOfResource` in
`src/types/addon/request.rs` lines 359-368 and `is_resource_supported` in
`src/types/addon/manifest.rs` lines 108-148.

**The request is held back until core has something about the file.** `subtitles_update` runs at
`Load` and again at `VideoParamsChanged`. It sends nothing while all four of these are missing: a
hash, a size, a filename, and a `video_params` value. *Read:* `player.rs` lines 1615-1621.

- Hash, size and filename are taken from the stream's own `behaviorHints` (`videoHash`,
  `videoSize`, `filename`) first, and from the host's `VideoParamsChanged` action second. *Read:*
  `player.rs` lines 1590-1613.
- So a stream that carries a filename or a size is asked about at `Load`, with no further action
  from the host. *Derived* from the two readings above. Comet's streams carry both: the prototype
  reads `behavior_hints.filename` and `behavior_hints.video_size` from them
  (`prototype/src/main.rs` lines 401, 446).
- A stream that carries none of the three is asked about only after the host dispatches
  `VideoParamsChanged` with a value. A value whose three fields are all empty is enough to release
  the request. *Derived* from the condition at lines 1615-1621.

**On the wire.** The three values travel as optional extras named `videoHash`, `videoSize` and
`filename`; an empty one is left out. The request is a plain GET:
`<add-on>/subtitles/<type>/<id>.json` with no extras, or
`<add-on>/subtitles/<type>/<id>/filename=…&videoSize=…&videoHash=….json` with them (each extra is
placed before the ones already there, so the last one added comes first). *Read:*
`src/constants.rs` lines 111-128, `extend_one` in `src/types/addon/request.rs` lines 26-51,
`src/addon_transport/http_transport/http_transport.rs` lines 48-64. The SDK documentation names
the same three extras and marks none as required. *Read:* `docs/api/requests/defineSubtitlesHandler.md`.

The hash is the OpenSubtitles file hash: the file size plus checksums of the first and last 64 KiB
of the file. The official hosts get it from the streaming server, which this app does not have.
*Read:* the comment on `VideoParams.hash`, `player.rs` lines 77-84. The 64 KiB detail is from the
OpenSubtitles hash description the SDK page links to, recalled and not re-read for this ticket.

## 3. What the add-ons answer without a hash, size or filename

**The account's subtitle add-ons.** Three installed add-ons declare the `subtitles` resource.
*Run:* read from the prototype's saved profile; none of the three addresses carries a token or a
configuration string.

| Add-on | Host | Types | Id prefixes |
|---|---|---|---|
| OpenSubtitles v3 | `opensubtitles-v3.strem.io` | movie, series | `tt` |
| stremio-opensubtitlesv2 | `subtitlesv2.strem.io` | movie, series, other | `tt`, `bt:`, `file:` |
| OpenSubtitles | `opensubtitles.strem.io` (the older `/stremio/v1` protocol) | series, movie, other | none |

Comet and StremThru Torz declare `stream` only.

**Answers with no extras.** *Run:* `curl` from a desktop, 2026-10-14.

| Request | Add-on | Entries | Languages |
|---|---|---|---|
| film `tt0111161` | OpenSubtitles v3 | 39 | 17 |
| film `tt0111161` | stremio-opensubtitlesv2 | 55 | 17 |
| film `tt1254207` | OpenSubtitles v3 | 2 | 2 |
| film `tt1254207` | stremio-opensubtitlesv2 | 2 | 2 |
| episode `tt0944947:1:1` | OpenSubtitles v3 | 94 | 27 |
| an id that does not exist | OpenSubtitles v3 | 0, with HTTP 200 | |

Each answered in under 0.25 s.

**The same request with extras.** *Run:* film `tt0111161` on OpenSubtitles v3, asked four more
times: with an invented filename, with an invented size, with an invented hash, and with all three.
All four returned the same 39 entries (same id, language and address for each) as the request with
no extras. With the invented hash the order of two entries differed, and an undocumented field `g`
differed on two entries.

So the answer to what the closed ticket left open is: **yes, these add-ons answer usefully with no
file hash.** *Derived* from the two runs.

**Not determined:** whether a hash that really matches a file changes the order or marks a match.
Every entry carried the undocumented field `m` with the value `i` in all five requests; nothing run
here could produce another value. Computing a real hash needs the first and last 64 KiB of a
stream's file, which means opening a stream link, and that was out of bounds for this ticket.

**What else the answers show.** *Run:* same requests.

- The two add-ons overlap completely for this film: all 39 addresses from OpenSubtitles v3 are
  among stremio-opensubtitlesv2's 55. A host that shows both lists shows duplicates unless it drops
  entries with the same address.
- One language can have several entries (Greek 6, Brazilian Portuguese 4, English 3) and no entry
  has a `label`, so nothing in the fields core keeps tells two English entries apart.
- OpenSubtitles v3 sends extra fields core drops (`subtitleFileName`, `movieReleaseName`,
  `SubEncoding`, `fpsMilli`, `releaseGroup` and others). They would tell entries apart, but core's
  `Subtitles` type has no place for them. *Read:* the type in section 1.
- Language codes are three letters but not all ISO 639-2: `pob` (Brazilian Portuguese) is
  OpenSubtitles' own code, and `cze`, `fre`, `ell` and `ron` mix the two ISO 639-2 variants.
- The answer is cacheable: `Cache-Control: max-age=14400` for the film with 39 entries.

**Not run:** the third add-on, OpenSubtitles on the older protocol. Core has a translation layer for
it (`src/addon_transport/http_transport/legacy/mod.rs`) and would ask it for every title, since it
declares no id prefixes.

## 4. File formats and text encodings

### What the add-ons serve

**The first file downloaded.** *Run:* the entry OpenSubtitles v3 listed for film `tt0111161` in Greek,
whose `SubEncoding` field said `CP1253` and whose `subtitleFileName` ended in `.srt`.

| Measured | Value |
|---|---|
| Host | `subs5.strem.io`, the host of all 39 addresses |
| Redirects | none |
| `Content-Type` | `application/x-subrip; charset=utf-8` |
| `Content-Encoding` | none |
| Size | 133,059 bytes |
| Format | SubRip: 1,328 timing lines of the form `00:01:46,065 --> 00:01:49,385` |
| Text encoding | valid UTF-8, no byte-order mark, 34,874 Greek letters, no replacement characters |
| Line endings | CRLF |
| Markup | no `<…>` tags and no `{\…}` codes in this file |

Every address has the path segment `subencoding-stremio-utf8`, and the file listed as CP1253 arrived
as UTF-8. So this host converts the text to UTF-8 before serving it. *Derived* from the run.

The source encodings the 39 entries named were CP1252 (19), CP1250 (7), CP1253 (6), CP1254 (3),
ASCII (2), CP1251 (1) and CP1255 (1). *Run.* Only two of 39 were ASCII, so without the server's
conversion nearly every file would arrive in a legacy code page.

The original filenames ended in `.srt` for 34 entries and `.txt` for 5. *Run.*

**A second file, one with a `.txt` filename, was downloaded** after the owner allowed it. *Run:*
the Turkish entry for the same film, listed with `SubEncoding` `CP1254`.

| Measured | Value |
|---|---|
| `Content-Type` | `application/x-subrip; charset=utf-8` |
| Size | 129,685 bytes, no redirect |
| Format | SubRip: 1,685 timing lines, no frame-based lines |
| Text encoding | valid UTF-8, no byte-order mark, 4,998 Turkish letters, no replacement characters |

So this `.txt` entry is SubRip under another name, and the copy of the app's reader indexed all
1,685 of its cues. *Run.* The other four `.txt` entries were not downloaded.

Fifteen of the 39 entries have `CD1` or `CD2` in their filename (7 `CD1`, 8 `CD2`, two of those
ending in `.txt`), which suggests halves of a two-disc release, with timings that restart partway
through the film. Two of the three English entries are among them, and the only Romanian and the
only Swedish entry are too. *Run* for the names; *derived* for what they mean, since none of those
files was downloaded. Nothing in the fields core keeps marks such an entry.

**Not determined:**

- What other subtitle add-ons serve. The account has only the OpenSubtitles family, and all three
  are Stremio's own hosts.

**What the documentation allows.** *Read:* `docs/api/responses/subtitles.md`.

- It names no required format. The example on `docs/api/requests/defineSubtitlesHandler.md` is an
  `.srt` file.
- ASS and SSA files are allowed, served with a `.ass` or `.ssa` address or recognised by their
  opening section.
- It tells add-on authors with badly encoded files to point `url` at
  `http://127.0.0.1:11470/subtitles.vtt?from=…`, the local streaming server, which guesses the
  encoding and converts to WebVTT. It also allows addresses of files inside a torrent on that same
  local server. **This app has no streaming server, so such an address cannot be fetched.**

### What the app accepts for a file outside the video

**The bundled FFmpeg cannot open a subtitle file.** It is built with the demuxers `matroska`,
`mov`, `mpegts`, `h264` and `hevc` only, and `file` as its only protocol. The subtitle decoders it
carries (`pgssub`, `dvdsub`, `dvbsub`, `ass`, `srt`, `subrip`, `text`, `mov_text`, `webvtt`) work on
packets from a track inside a container. *Read:* `ci/build-ffmpeg.sh` lines 200-204. So a file
outside the video is read by the app's own Rust code, not by FFmpeg.

**The app's reader for such a file** is in `rust-modules/media/src/player/sidecar.rs`. *Read:*

- **SubRip and WebVTT** share one reader, `index_srt`. A line containing `-->` opens a cue; its
  text is every line up to the next blank line or timing line. Timestamps are `[H:]MM:SS` with a
  comma or a full stop before the fraction. A `WEBVTT` header, counter lines and `NOTE` lines are
  skipped. Lines 504-570.
- **ASS and SSA** are recognised by an `[Events]` line plus a `Dialogue:` line and handed whole to
  the bundled libass. They are never turned into plain text. Lines 298-322.
- **Size limit:** 4 MiB (`SIDECAR_MAX_BYTES`, `rust-modules/plex/src/plex/mod.rs` line 42).
- **Text encoding: UTF-8 only.** The bytes go through `String::from_utf8`, falling back to a lossy
  conversion, and a leading UTF-8 byte-order mark is dropped. There is no detection of UTF-16 or of
  a legacy code page. Lines 456-471.
- **Markup:** when a cue is drawn, `<…>` tags and `{…}` codes are removed and `\N` becomes a line
  break (`sub_text`, `rust-modules/media/src/player/mod.rs` lines 2094-2128).
- Nothing else is read. A MicroDVD or other frame-based file has no `-->` line, so it yields no
  cues. *Derived* from `index_srt`.

**A copy of that reader was run on the downloaded file.** *Run:* `index_srt`, `timing_line`,
`timestamp` and `sub_text` copied unchanged into a scratch program, compiled with desktop
`rustc 1.99.0`, and given the 133,059-byte file. It indexed 1,328 cues, all usable, from 1:46.065 to
2:16:52.323, with no replacement characters. This is a copy run on a desktop, not the app.

**The same file in its original code page fails.** *Run:* the file converted back to CP1253 with
`iconv` and given to the same program. It still indexed 1,328 cues, but all 1,328 contained
replacement characters. So a legacy-encoded file is timed correctly and drawn as unreadable text.

**Which scripts the caption font can draw.** Plain captions are drawn with the app's text
renderer, whose font chain is Inter, then the bundled Noto Sans CJK KR, then the television's
`DroidSansFallback.ttf`. *Read:* `rust-modules/gfx/src/text.rs` lines 29-33. *Run:* `fc-query` on
`pkg/appfont.ttf` and `pkg/appfont-cjk.ttf`:

| Script | Inter | Noto Sans CJK KR |
|---|---|---|
| Latin with accents, Czech, Turkish, Vietnamese | yes | partly |
| Greek, Cyrillic | yes | yes |
| Chinese, Japanese, Korean | no | yes |
| Hebrew, Arabic, Thai, Devanagari | no | no |

The source says the television's own fallback font had no Hebrew and no Arabic on webOS 4.10.
*Read:* same file. **Not determined:** whether the G5's system font has them, and how any caption
looks drawn over the video plane. Both need the television.

## 5. Can the existing sidecar path take a plain HTTPS address?

**No.** *Read:* `rust-modules/media/src/player/sidecar.rs` and
`rust-modules/plex/src/plex/library.rs`.

- The only public way in is `sidecar::select(server, stream_id, key, codec)`. It looks up a Plex
  client for `server` and gives up when there is none (lines 113-123).
- The fetch is `Client::sidecar_subtitle_detailed`, which refuses any key that is not
  `/library/streams/<digits>[.ext]` (`library.rs` lines 8-13 and 266-270), then adds a Plex token
  and Plex query parameters and sends the request to that server's address.
- The function that takes the fetch as a parameter, `select_with_fetch`, is private. So are the
  cue store (`Subtitles`), the reader (`index_srt`) and the state. `sidecar::parse` exists only in
  test builds.

A call from new code can therefore neither point the sidecar path at another address nor hand it
bytes it fetched itself. Changing that means editing upstream's file, which
[decision record 0001](https://github.com/CasperEngl/lgtv-stremio/pull/14) rules out.

**What is public and usable from a new file.** *Read.*

| Need | Existing public function |
|---|---|
| Fetch an HTTPS address, following redirects, with a size limit | `plx_net::net::request(url, headers, "GET", None, timeouts, true, Some(max_body), None)`, `rust-modules/net/src/net.rs` line 749. It allows only HTTP and HTTPS, follows at most 5 redirects, and never lets an HTTPS start fall back to plain HTTP (lines 1618-1640). The fork's Stremio crate already sends every `stremio-core` request through it (`stremio/src/env.rs` on `wayfinder/desktop-simulator`). |
| The clock a cue is looked up on | `plx_media::player::playpos_ns()` |
| Draw one caption in the place, size and tone the viewer set | `plx_appkit::player_hud::draw_subtitle_message(text, hud_up)`, `rust-modules/appkit/src/player_hud.rs` line 166 |
| Turn inside-file subtitles off | `plx_media::player::request_subtitle(-1)`, `mod.rs` line 1667 |
| Rasterise a whole ASS script | `plx_media::player::ass::request(source, clock_ms, …)` with a `Source` built from the file's bytes; all fields are public, `ass.rs` lines 55-76 and 218 |

**Three limits of those public functions.** *Read.*

1. `draw_subtitle_message` does not page. Upstream's own caption draw, `draw_subtitles`, splits a
   cue too tall for the screen into pages, but it reads only the sidecar store and the inside-file
   store (`player_hud.rs` lines 276-283), so new code cannot feed it. A very long add-on cue is
   drawn whole at the smallest text size instead.
2. Upstream's timing offset cannot be negative for an add-on subtitle.
   `subtitle_offset_range_ms` allows an advance only while `sidecar::selected()` is true
   (`mod.rs` lines 1779-1786). New code could make it true only by calling `sidecar::select` with a
   made-up Plex key, which records the selection before a fetch that then fails (`sidecar.rs`
   lines 129-137); that is a trick, not a door. New code that holds the whole file can keep its
   own delay, in either direction, and core already has a place to save it
   (`StreamItemState.subtitle_delay`).
3. For ASS, `ass::request` returns rendered images, but the code that uploads them as textures is
   `AssSubtitles` in `rust-modules/screens/src/player/ass_subtitles.rs` (216 lines), and its
   `update` reads only the sidecar store and the inside-file store (lines 22-28). Drawing an add-on's
   ASS file means a second copy of that uploader in a new file, or a change offered to upstream.

**A route that was considered and rejected.** `plx_media::player::push_subtitle_text` is public, so
new code could push an add-on's cues into the inside-file store under an unused track number and let
`draw_subtitles` page them. *Read:* `mod.rs` lines 1866-1898 and
`rust-modules/media/src/ff_subs.rs` lines 401-419. That store is a window: it drops everything more
than 32 s behind the playhead, caps at 512 cues shared with every text track in the file, and is
emptied on a seek or reload, so the new code would have to keep refilling it. Selecting a track
number the file does not have also switches on image-subtitle decoding for every image track in
the file. *Derived:* more moving parts than a store of its own, for the sake of paging alone.

## 6. Are subtitle tracks inside the file unaffected?

**Yes.** *Read,* then *derived.*

- Inside-file tracks are found by the demuxer and pushed into their own stores: text cues into
  `SHARED.sub_cues`, images into `SHARED.sub_bitmaps`, ASS events into `ass_source`
  (`mod.rs` lines 1882-1925, `ff_subs.rs`). One is chosen with
  `plx_media::player::request_subtitle(index)`, which the fork's `stremio/src/play.rs` already
  calls at start.
- The sidecar store is separate state in `sidecar.rs`, and nothing in the proposal below writes to
  it or to the inside-file stores.
- The one rule new code must keep: an add-on subtitle and an inside-file track are never on
  together. Choosing an add-on subtitle calls `request_subtitle(-1)`; choosing an inside-file track
  clears the add-on selection. Upstream keeps the same rule between its sidecar and its inside-file
  tracks (`player_hud.rs` lines 138-142).

The formats an inside-file track can be in are the bundled FFmpeg's decoder list, unchanged.

**Not determined:** who draws captions at all in the Stremio app. The fork's crate draws nothing
over playback yet, and upstream's player screen is tied to a Plex playback plan
([Where is the seam between PlxNative's player and Plex?](https://github.com/CasperEngl/lgtv-stremio/issues/5)
left its behaviour without one open). The public draws for inside-file tracks exist:
`draw_subtitles`, `draw_subtitle_bitmap` and `AssSubtitles`. Which screen calls them belongs to
"Screens and navigation" on the map.

## 7. Proposal: from `stremio-core` to the screen

All of it in new files in the Stremio crate. No upstream file is edited.

1. **Ask.** When the app loads the player model, it sets `Selected.subtitles_path` to
   `subtitles/<type>/<video id>`. For a stream with a filename or size in its `behaviorHints`, core
   asks the add-ons at once and sends those values along. For a stream with neither, the app
   dispatches `VideoParamsChanged` once the probe has finished, with the size the probe saw and the
   filename from the link when it has them. The app never computes the OpenSubtitles hash.
2. **Collect.** The app reads `Player.subtitles` (one list per add-on) and the chosen stream's own
   `subtitles`, and builds one list. It drops entries with an address already seen, and entries
   whose address is not HTTP or HTTPS or points at `127.0.0.1` or `localhost`.
3. **Fetch.** When an entry is chosen, a worker thread fetches its address with
   `plx_net::net::request`: GET, redirects followed, body limited to 4 MiB, the 25-second timeout
   the other requests use. It goes through the crate's existing address override, so host tests and
   the simulator fetch it from the stand-in server
   (decision record 0002, in the pull request
   [Record how the app is tested without a real account](https://github.com/CasperEngl/lgtv-stremio/pull/28)).
   An answer for an entry the viewer has already moved off is thrown away.
4. **Read.** The bytes must be valid UTF-8, with a leading byte-order mark dropped. A file that
   starts as an ASS script is set aside as styled (see step 6). Anything else goes through a SubRip
   and WebVTT cue reader written in the new file, following the rules of upstream's `index_srt`.
   The whole file's cues are kept, sorted by start, so a backward seek needs no second download.
5. **Draw.** Each frame, the Stremio player screen looks up the cue at the playhead less the
   viewer's delay and, when there is one, calls `player_hud::draw_subtitle_message(text, hud_up)`
   after removing markup the way `sub_text` does. While an add-on subtitle is on, the inside-file
   selection is `-1`.
6. **Refuse what cannot be drawn, and say so.** A fetch that fails, a file over 4 MiB, a file that
   is not valid UTF-8, a file with no cues, and an ASS file all end as "this subtitle cannot be
   shown", with the reason logged. What the viewer sees then is a later decision.

Estimated size: 300 to 400 lines of Rust with tests. *Derived* from upstream's `sidecar.rs`, whose
fetch, store and reader come to about 570 lines without tests and which also carries the ASS branch
and a faster lookup this path can do without.

**Why UTF-8 only, and no ASS, in this step.** Both add-ons asked here convert to UTF-8 on the
server and listed only `.srt` and `.txt` files, and the `.txt` file downloaded was SubRip too, so
neither gap was hit in what was run. Guessing a
code page and drawing an add-on's ASS file are each a separate piece of work (section 5, limit 3),
and nothing measured here shows either is needed for the account the first version is tested
against.

## 8. Left for a later decision

These are the remainder the map lists under "Subtitles". This ticket did not decide them.

- **The menu.** What a row shows when entries carry only a language code and several share one;
  whether the add-on's name is shown; whether inside-file tracks and add-on subtitles share one
  list; how the language codes that are not ISO 639-2 (`pob`) are named.
- **The default.** Whether a subtitle is on when playback starts, and which: the account's
  `subtitles_language` and `subtitles_auto_select`, the saved choice for the stream
  (`StreamItemState.subtitle_track`), an inside-file track before an add-on's, and whether an
  add-on subtitle may be fetched without the viewer asking.
- **When none fit.** What the viewer sees for a file that cannot be shown (step 6), for a language
  the caption font cannot draw (Hebrew, Arabic, Thai), when no add-on has the wanted language, and
  when an entry turns out to cover only part of the film.
- **Timing.** Whether the viewer can shift an add-on subtitle, how far, and whether the shift is
  saved through `StreamItemState.subtitle_delay`.
- **Scope.** Whether an add-on's ASS file, a legacy code page, or a frame-based `.txt` file is in
  the first version at all.

## 9. Not determined

| Point | Why |
|---|---|
| Whether a hash that matches a file changes an add-on's answer | needs the first and last 64 KiB of a stream's file; no stream link was opened |
| Whether the 15 entries named `CD1` or `CD2` each hold only half of the film | their names were read; the files were not downloaded |
| Which screen draws captions in the Stremio app | belongs to "Screens and navigation" on the map |
| What the older OpenSubtitles add-on answers through core's translation layer | not run |
| Whether Comet's or StremThru Torz's streams carry their own `subtitles` list | no stream list was requested for this ticket |
| Formats and encodings of subtitle add-ons outside the OpenSubtitles family | none is installed on the account |
| Whether `subs5.strem.io`'s certificate is accepted by the television's trust store | needs the television |
| How a caption drawn by `draw_subtitle_message` looks over the video plane, and whether the G5's system font draws Hebrew or Arabic | needs the television |
| The exact line count of the new path | estimated, not written |
