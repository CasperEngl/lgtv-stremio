# Where is the seam between PlxNative's player and Plex?

Research for issue #5, read at commit `9d2777fe`. Nothing was built or run; every figure is a count
over the source tree or over `git log`. Paths are relative to the repository root.

## Answer

The player can already be started on a link nobody at Plex chose, through public functions, with no
edit to any existing file: set the URL and the five-field declaration on the session, arm the
resume seek, set the audio and subtitle ordinals, start the engine. Six crates (`base`, `machine`,
`platform`, `gfx`, `net`, `ui`) and the storage helper have no dependency on the Plex crate, direct
or transitive, so they stay untouched under any cut. The `media` crate cannot be built without the
Plex crate: 300 production references, 240 of them in route selection, and the engine and route
selection form one import cycle. The engine, demuxer and HTTPS path themselves hold only 19 of those
references, all small (URL types that already live in `net`, one credential gate, one User-Agent
string). So Stremio code can live in new crates beside untouched ones if the Plex crates stay
compiled in as passengers; removing Plex from the player's build means editing the files upstream
changes most often.

## Crates and their Plex dependency

"Transitive" is read from each `Cargo.toml`. "refs" counts occurrences of `plx_plex::` in `.rs`
files, tests included. "mentions" counts files containing the word "plex" in any case.

| Crate | Plex dependency | Evidence |
|---|---|---|
| `base` | none (names only) | No `plx_` dependency at all (`rust-modules/base/Cargo.toml`). 11 of 27 files mention Plex, in comments and in a token redactor keyed on the literal `X-Plex-Token=` (`rust-modules/base/src/eventlog.rs:36`). |
| `machine` | none (names only) | Depends on `plx_base` only (`rust-modules/machine/Cargo.toml:31`). 2 of 8 files mention Plex, comments only (`rust-modules/machine/src/idle.rs:371`, `rust-modules/machine/src/machine.rs:22`). |
| `platform` | none (names only) | Depends on `plx_base`, `plx_machine` (`rust-modules/platform/Cargo.toml:31-32`). 10 of 37 files mention Plex in comments (`rust-modules/platform/src/devcaps.rs:50-56`). It owns the direct-play audio codec table that the Plex crate re-exports (`rust-modules/platform/src/devcaps.rs:54-56`). |
| `gfx` | none (names only) | Depends on `plx_base`, `plx_machine` (`rust-modules/gfx/Cargo.toml:32-33`). 4 of 15 files mention Plex, comments only (`rust-modules/gfx/src/gfx.rs:4475`). |
| `ui` | none (names only) | Depends on `plx_base`, `plx_machine`, `plx_platform`, `plx_gfx` (`rust-modules/ui/Cargo.toml:45-48`). 15 of 102 files mention Plex, in comments and test strings (`rust-modules/ui/src/fmt.rs:123-128`). The layer rule says "no application type" (`ci/module-layers.ini:107`). |
| `net` | none in Cargo; Plex-shaped behaviour | Depends on `plx_base` only (`rust-modules/net/Cargo.toml:33`). But 8 of 13 files mention Plex and the behaviour is Plex-specific: the URL parser's default port is 32400 (`rust-modules/net/src/net/origin.rs:109`), its module doc calls it "a PMS origin parser, not a general URL parser" (`rust-modules/net/src/net/origin.rs:56-63`), and the HTTPS client has a `.plex.direct` certificate fallback (`rust-modules/net/src/net.rs:2459`). |
| `storage` | none | No `plx_` dependency, 2 files, no mention (`rust-modules/storage/Cargo.toml:21-22`). |
| `plex` | is the Plex crate | Depends on `plx_base`, `plx_machine`, `plx_platform`, `plx_net` (`rust-modules/plex/Cargo.toml:32-35`). |
| `telemetry` | shallow | `plx_plex` at `rust-modules/telemetry/Cargo.toml:41`; 51 refs in 7 of 21 files. They are value types (`ServerId`, `IpVersion`, `probe::Location`, two preference enums) in the event schema (`rust-modules/telemetry/src/diag/schema.rs:177-224`, `:351-370`) and four file helpers from the session module (`rust-modules/telemetry/src/telemetry/crashreport.rs:1141`, `:1522`, `rust-modules/telemetry/src/telemetry/spool.rs:80`, `:92`). |
| `data` | deep | `plx_plex` at `rust-modules/data/Cargo.toml:34`; 1,244 refs in 61 of 84 files. It is the content stores over the Plex API (`ci/module-layers.ini:118`). |
| `session` | deep | `plx_plex` at `rust-modules/session/Cargo.toml:39`; 595 refs in 14 of 17 files. It is plex.tv sign-in and discovery (`ci/module-layers.ini:123`). |
| `media` | deep in route selection, shallow in the engine | `plx_plex` at `rust-modules/media/Cargo.toml:48`, `plx_data` at `:50`; 847 refs in 44 of 93 files, 300 of them in production code. Inventory below. |
| `appkit` | shallow directly, deep transitively | `plx_plex` at `rust-modules/appkit/Cargo.toml:44`; 47 refs in 4 of 13 files, 15 in production code, all value types and a language table (`rust-modules/appkit/src/track_menu.rs:299`, `:1233`, `rust-modules/appkit/src/player_hud.rs:388-412`, `rust-modules/appkit/src/source_list.rs:27`). It also names `plx_media` 357 times and `plx_data` 110 times (`rust-modules/appkit/Cargo.toml:46-47`). |
| `screens` | deep | `plx_plex` at `rust-modules/screens/Cargo.toml:44`; 602 refs in 64 of 118 files, plus 1,611 refs to `plx_data` in 80 files. |
| root `plxnative-modules` | deep | `plx_plex` at `rust-modules/Cargo.toml:232`; 1,050 refs in 65 of 98 files. It is the one crate that may name every layer and it holds the webOS port's application side (`ci/module-layers.ini:160-163`, `:166-176`; `docs/module-layers.md:17-21`). |

The enforced graph agrees: `plex` may be named by `telemetry`, `data`, `session`, `media`, `appkit`,
`screens` and `app`, and by none of `base`, `machine`, `platform`, `gfx`, `net`, `ui`
(`ci/module-layers.ini:33`, `:48`, `:62`, `:71`, `:80`, `:98`, `:108`, `:119`, `:128`, `:138`, `:148`, `:157`, `:162`).

## Import inventory for the `media` crate

Method: occurrences of `plx_plex::` on non-comment lines, in files not named `*_tests.rs`,
`*test_support.rs` or `*flight_rig.rs`, above the file's first `#[cfg(test)] mod`. A `use` line that
imports several names counts once, and a name used unqualified after a `use` is not counted, so the
route figures are a floor: `rust-modules/media/src/route/prefs.rs:31-39` alone imports 27 names in
four counted lines.

Production references: 300. Test references: 526.

| Area | Files | Production refs |
|---|---|---:|
| Route selection | `route/decision.rs` 145, `route/plan.rs` 86, `route/prefs.rs` 5, `route/flight.rs` 4 | 240 |
| Player | `player/mod.rs` 18, `player/sidecar.rs` 9, `player/report.rs` 7, `player/engine.rs` 2, `player/preview.rs` 2, `player/subside.rs` 1, `player/threads.rs` 1 | 40 |
| Demuxer | `ff.rs` 3, `ff_subside.rs` 5 | 8 |
| HTTPS media path | `curlio.rs` 8 | 8 |
| HLS parser | `hls.rs` 1 | 1 |
| Adaptive bitrate | `abr/ladder.rs` 3 | 3 |

### By purpose

**Identity and headers: 3.**

- `plex::identity::user_agent` 1: the only header the HTTPS media path sets (`rust-modules/media/src/curlio.rs:821`).
- `plex::identity::PRODUCT` 1 and `plex::identity::version` 1: the support line on the player's error screen (`rust-modules/media/src/player/mod.rs:677-678`).

Small. Each is a string (`rust-modules/plex/src/plex/identity.rs:36`, `:70`, `:153`). `net` already
receives the User-Agent as a value at boot so that it need not name the Plex layer
(`rust-modules/net/src/net.rs:398-402`); the media path could read the same value.

**Credential gate: 6.**

- `http::credential_transport_allowed` 4: before opening a media URL (`rust-modules/media/src/curlio.rs:2119`, `rust-modules/media/src/player/engine.rs:1418`) and passed as a function pointer into the plaintext redirect follower (`rust-modules/media/src/ff.rs:2634`, `rust-modules/media/src/ff_subside.rs:251`).
- `http::credential_transport_allowed_by_policy` 1 and `plex::CredentialPolicy` 1: a `#[cfg(test)]` helper (`rust-modules/media/src/curlio.rs:2122-2126`).

Small at the call site, deep behind it. The gate only refuses a request that carries
`X-Plex-Token` or an `Authorization` header (`rust-modules/plex/src/http.rs:341-349`, `:351-358`),
so a link without either always passes. Its body consults the Plex grant store
(`rust-modules/plex/src/http.rs:357`). `net`'s redirect follower already takes the gate as a
`credential_gate` field (`rust-modules/media/src/ff.rs:2627-2635`), so the trait-or-function shape
exists.

**Origin and URL types: 12.**

- `plex::Origin` 4 and `plex::Origin::http` 1 (`rust-modules/media/src/ff.rs:1936`, `:2625`, `rust-modules/media/src/ff_subside.rs:161`, `:237`, `:271`).
- `plex::origin::split` 5 (`rust-modules/media/src/curlio.rs:818`, `:872`, `:2118`, `:2124`, `rust-modules/media/src/ff_subside.rs:206`).
- `use plx_plex::plex::{origin, Origin}` 1 (`rust-modules/media/src/hls.rs:9`).
- `plex::StreamUrl::parse` 1 (`rust-modules/media/src/player/engine.rs:1409`).

Names only. `Origin` and `split` are defined in `net` (`rust-modules/net/src/net/origin.rs:131`,
`:276`) and the Plex crate re-exports them (`rust-modules/plex/src/plex/origin.rs:13`,
`rust-modules/plex/src/plex/mod.rs:107`). `StreamUrl::parse` is a ten-line wrapper over `split`
(`rust-modules/plex/src/plex/client.rs:966-976`). All 12 could name `plx_net` directly.

**Server registry and client handle: 48.**

- `plex::ServerId` 13 with its constants (`rust-modules/media/src/player/preview.rs:48`, `rust-modules/media/src/player/report.rs:87`, `:710`, `:785`, `rust-modules/media/src/player/sidecar.rs:75`, `:113`, `rust-modules/media/src/route/decision.rs:15`, `:8981`, `rust-modules/media/src/route/plan.rs:12`).
- `plex::client_for` 18 (`rust-modules/media/src/player/report.rs:741`, `rust-modules/media/src/player/sidecar.rs:115`, `rust-modules/media/src/player/subside.rs:108`, `rust-modules/media/src/route/plan.rs:1340`, and 14 in `route/decision.rs` from `:2620`).
- `plex::Client` 15 (`rust-modules/media/src/route/decision.rs:4054`, `rust-modules/media/src/route/flight.rs:462`, `:486`, `rust-modules/media/src/route/plan.rs:2292`).
- `plex::current_server` 1 (`rust-modules/media/src/route/decision.rs:7345`), `plex::register_for_test` 1 (`:9785`).

`ServerId` is a small value type, a wrapped `u16` (`rust-modules/plex/src/plex/servers.rs:115`).
`client_for` and `Client` are deep: they are the door to every Plex server call. In the player they
fetch a sidecar subtitle (`rust-modules/media/src/player/sidecar.rs:113-122`), build a second
reader's URL (`rust-modules/media/src/player/subside.rs:107-109`) and read the connection kind for
telemetry (`rust-modules/media/src/player/report.rs:741-743`).

**Route decision and `/decision`: 122.**

- `plex::AudioEnhancements` 43 (`rust-modules/media/src/player/mod.rs:1798-1822`, `rust-modules/media/src/route/decision.rs:4179`, `rust-modules/media/src/route/plan.rs:721`).
- `plex::LinkPolicy` 16 and `plex::link_policy` 2 (`rust-modules/media/src/route/plan.rs:488-538`, `:1696`, `rust-modules/media/src/route/decision.rs:7175`).
- `plex::serverinfo::Subscription` and `subscription_of` 13 (`rust-modules/media/src/player/mod.rs:985-989`, `:1102-1103`, `rust-modules/media/src/route/plan.rs:582`, `rust-modules/media/src/route/decision.rs:7111`).
- `plex::probe::Location` 12 (`rust-modules/media/src/route/plan.rs:1650`, `:1769`, `:1870-1872`, `rust-modules/media/src/route/decision.rs:6532-6533`).
- `plex::MediaContainer` 8 and `plex::JsonDeadlineOutcome` 5 (`rust-modules/media/src/route/plan.rs:342-354`, `:779`, `rust-modules/media/src/route/decision.rs:6792`).
- `plex::is_dp_audio_track` 5, `plex::is_dp_subtitle` 2, `plex::DP_AUDIO_CODECS` 1 (`rust-modules/media/src/route/plan.rs:831`, `:2444`, `:2585-2587`, `:2822`, `:2899`).
- `plex::QueueRow` 5, `plex::same_item` 3, `plex::ShowLangPrefs` 2, `plex::StreamSelection` 1 (`rust-modules/media/src/route/plan.rs:1023`, `:1134`, `:2918`, `rust-modules/media/src/route/decision.rs:6868`).
- `plex::account::*` 4 (`rust-modules/media/src/route/plan.rs:1515-1529`).

Deep, except the codec predicates, whose table lives in `platform`
(`rust-modules/platform/src/devcaps.rs:54-56`). `Subscription` and `AudioEnhancements` are value
types that leak into the player's public surface (`rust-modules/media/src/player/mod.rs:983-989`,
`:1798-1822`).

**Transcode and HLS fallback: 79.**

- `plex::TranscodeDelivery` 35 (`rust-modules/media/src/route/decision.rs:3251`, `:3454`, `:3889`, `rust-modules/media/src/route/plan.rs:1954`).
- `plex::EncodeContract` 27 (`rust-modules/media/src/route/decision.rs:153`, `:449`, `rust-modules/media/src/route/flight.rs:137`, `rust-modules/media/src/route/plan.rs:378`).
- `plex::TranscodeOffset` 9 and `plex::TranscodeSpec` 3 (`rust-modules/media/src/route/plan.rs:375-403`, `rust-modules/media/src/route/decision.rs:3244`, `:6160`).
- `plex::Ceiling` 5 (`rust-modules/media/src/abr/ladder.rs:175-177`, `:206`, `rust-modules/media/src/route/decision.rs:5497`, `:8395`).

Deep. All but the three in `abr/ladder.rs` are in route selection. The types are plain structs and
enums (`rust-modules/plex/src/plex/params.rs:16`, `:99`, `:227`), but they describe a server-side
transcode a debrid link does not have.

**Progress reporting: 7.**

- `plex::TimelineState` 5 (`rust-modules/media/src/player/threads.rs:155`, `rust-modules/media/src/route/decision.rs:1055`, `:5564`, `:10100`, `:10141`).
- `plex::TimelineReport` 2 (`rust-modules/media/src/route/decision.rs:5562`, `:10157`).

`TimelineState` is a three-variant enum (`rust-modules/plex/src/plex/params.rs:322-326`). The
reporter thread itself is generic: every ten seconds it reads the position and duration atomics and
calls one route function (`rust-modules/media/src/player/threads.rs:82`, `:150-172`). The Plex call
is behind that function (`rust-modules/media/src/route/decision.rs:10139-10155`). Position and
duration are also public readers (`rust-modules/media/src/player/mod.rs:529`, `:542`).

**Preferences and the persisted session: 18 counted, 36 names imported.**

- `plex::session::*` in route (`rust-modules/media/src/route/prefs.rs:31-39`, `rust-modules/media/src/route/plan.rs:416`, `:1506-1511`, `rust-modules/media/src/route/decision.rs:16`, `:7634`, `:7653`).
- `plex::session::SubtitleTone`, `SubtitleTonePref`, `AudioEnhancementsPref` in the player (`rust-modules/media/src/player/mod.rs:1682-1687`, `:1816`, `:1831-1839`).
- `plex::session::peek` for the trailer-autoplay setting (`rust-modules/media/src/player/preview.rs:457`).
- `plex::grant::account_key` (`rust-modules/media/src/route/prefs.rs:416`).

Deep. Playback settings (quality, skip interval, subtitle size, position and tone, next-episode
mode) are stored in the Plex session record and re-exported by route selection under its own names
(`rust-modules/media/src/route/plan.rs:416`).

**Telemetry connection facts: 3.** `plex::IpVersion`, `plex::probe::Location` and the
`encode_link`/`decode_link` helpers (`rust-modules/media/src/player/report.rs:100`, `:776`). Small
value types.

**Sidecar size cap: 2.** `plex::SIDECAR_MAX_BYTES` (`rust-modules/media/src/player/sidecar.rs:305`,
`:457`), a constant (`rust-modules/plex/src/plex/mod.rs:42`).

### What the engine, demuxer and HTTPS path hold

`player/engine.rs`, `ff.rs`, `ff_subside.rs`, `curlio.rs` and `hls.rs` together hold 19 production
references: 12 URL types, 6 credential gate, 1 User-Agent. None is a model or a server call.

The coupling that matters is not to the Plex crate but to route selection inside the same crate.
`player/engine.rs` names `crate::route` 59 times across 37 functions and `player/pump.rs` 62 times
across 33 (for example `rust-modules/media/src/player/engine.rs:1159`, `:1277`, `:1313`, `:1392`,
`:1510`; `rust-modules/media/src/player/pump.rs:802`, `:828`, `:1210`). The layering record lists
`abr curlio ff hls player route` as one import cycle that stays inside the crate
(`docs/module-layers.md:61`, `ci/module-layers.ini:136`). Route selection also names the data
crate 111 times in production, mostly track and Dolby Vision types
(`rust-modules/media/src/route/plan.rs:161`, `:1218-1221`, `:1281`), and takes the metadata store
as a parameter of every play request (`rust-modules/media/src/route/decision.rs:7359`).

## What a play request must carry

The engine takes no request value. `start_bufferfeed(ps, pa)` reads the playback session and a few
process-wide atomics (`rust-modules/media/src/player/engine.rs:1041`). What must be in place before
it is called:

| Field | Where the engine reads it | Normal path writes it | Play-a-URL path writes it |
|---|---|---|---|
| Link | `route::url(ps)` (`rust-modules/media/src/player/engine.rs:1159`) | `apply_plan` from `Plan::url` (`rust-modules/media/src/route/decision.rs:8049`) | `route::set_url` (`rust-modules/media/src/player/engine.rs:1620`) |
| Video codec | `route::stream_vcodec` (`rust-modules/media/src/player/engine.rs:1277`); `""`, `h264`, `hevc`, `h265`, `av1`, `vp9`, else refused (`:581-588`) | `apply_plan` (`rust-modules/media/src/route/decision.rs:8102`) | `set_stream_declaration` (`rust-modules/media/src/player/engine.rs:1609-1616`) |
| Audio codec | `route::stream_acodec` (`rust-modules/media/src/player/engine.rs:1313`, `:1445`); `ac3`, `eac3`, `aac`, `dts`, else refused (`:770-777`) | `apply_plan` (`rust-modules/media/src/route/decision.rs:8103`) | `set_stream_declaration` |
| Frame rate | `route::stream_fps` (`rust-modules/media/src/player/engine.rs:806`) | `apply_plan` (`rust-modules/media/src/route/decision.rs:8104`) | `set_stream_declaration`; 0 omits it (`rust-modules/media/src/player/playurl.rs:58-60`) |
| Dolby Vision | `route::stream_dovi` (`rust-modules/media/src/player/engine.rs:1359`) | `apply_plan` (`rust-modules/media/src/route/decision.rs:8105-8106`) | `set_stream_declaration`: profile, base-layer compatibility id, enhancement-layer flag (`rust-modules/media/src/player/playurl.rs:110-136`); a declaration the set cannot present is refused (`rust-modules/media/src/route/decision.rs:5411-5427`) |
| Dolby Atmos | `route::stream_immersive` (`rust-modules/media/src/player/engine.rs:822`) | `apply_plan` (`rust-modules/media/src/route/decision.rs:8107`) | `set_stream_declaration` (`rust-modules/media/src/player/engine.rs:1615`) |
| Resume position | `SHARED.seek_to_ns`, taken by the demuxer at first open (`rust-modules/media/src/ff.rs:8723`) | `pump_play` returns it (`rust-modules/media/src/route/decision.rs:7875-7878`); the app calls `begin_resume`, which for a direct play calls `arm_seek` (`rust-modules/src/app/run.rs:2264-2268`, `rust-modules/media/src/player/engine.rs:1672-1683`, `:1628-1633`) | not written |
| Audio track | `SHARED.desired_audio_idx`; `-1` feeds the track matching the declared codec (`rust-modules/media/src/ff.rs:8465-8489`) | `apply_plan` calls `set_audio_track(ord)` (`rust-modules/media/src/route/decision.rs:8145-8147`) | not written |
| Subtitle track | `SHARED.desired_sub_idx` (`rust-modules/media/src/player/mod.rs:1659-1668`) | `apply_plan` calls `request_subtitle(ord)` (`rust-modules/media/src/route/decision.rs:8151-8157`) | not written |
| Title lines | fixed buffers on the session (`rust-modules/media/src/route/decision.rs:5530-5531`) | `request_play` at the press (`rust-modules/media/src/route/decision.rs:7357-7366`, `:7473-7476`) | not written |
| Item identity for progress | `cur_rk`, `cur_sid` (`rust-modules/media/src/route/decision.rs:10074-10084`) | `apply_plan` (`rust-modules/media/src/route/decision.rs:8076-8077`) | deliberately not written, so no reporter starts (`rust-modules/media/src/route/decision.rs:5381-5383`) |

The developer trigger's own fields are `url`, `vcodec`, `acodec`, `fps`, `dovi`, `atmos`, plus four
test-fixture fields for adaptive bitrate (`rust-modules/media/src/player/playurl.rs:43-104`). It
therefore covers link, codecs, frame rate, Dolby Vision and Atmos. It does not cover resume, audio
track, subtitle track or title, and the project's own notes say that tier reaches "no resume,
marker, Up Next, timeline, track-SELECTION or transcode path" (`docs/agent-reference.md:1885-1888`).

Everything the normal path does for those missing fields is a public function, reachable without
going through a plan:

- `plx_media::route::set_url` and `set_stream_declaration` (`rust-modules/media/src/route/decision.rs:688`, `:5384`; re-exported at `rust-modules/media/src/route/mod.rs:6`).
- `plx_media::player::begin_resume` (`rust-modules/media/src/player/mod.rs:272-275`) or `player::engine::arm_seek` (`rust-modules/media/src/player/engine.rs:1628`; the module is public, `rust-modules/media/src/player/mod.rs:23`).
- `plx_media::player::set_audio_track` and `request_subtitle` (`rust-modules/media/src/player/mod.rs:1602`, `:1667`); a later audio switch on a direct play is `request_audio_track(ps, idx, codec)`, which re-declares the codec and reloads (`rust-modules/media/src/player/mod.rs:1572-1584`).
- `plx_media::player::start_bufferfeed` (`rust-modules/media/src/player/mod.rs:272-273`). A URL already on the session takes precedence over the trigger (`rust-modules/media/src/player/engine.rs:1156-1159`).

The trigger is compiled out of release builds (`rust-modules/media/src/player/playurl.rs:161-168`),
but none of the functions above is.

Three constraints a caller has to meet:

1. **Codecs are declared before the file is opened.** The Load payload is composed from the
   declared codecs (`rust-modules/media/src/player/engine.rs:1277-1313`) before the demuxer thread
   is spawned (`:1449-1451`). An add-on stream carries no codec fields, so something must probe the
   file first. With no audio index set, the demuxer feeds the track whose codec matches the
   declaration (`rust-modules/media/src/ff.rs:8478-8489`). The demuxer does publish the file's own
   track names once open (`rust-modules/media/src/ff.rs:8445-8459`).
2. **A link with no port is dialled on 32400 for its first request.** The engine splits the URL
   with the Plex-origin parser (`rust-modules/media/src/player/engine.rs:1409`,
   `rust-modules/plex/src/plex/client.rs:966-968`), which fills a missing port with 32400
   (`rust-modules/net/src/net/origin.rs:276-281`), and the demuxer rebuilds the URL from that
   origin (`rust-modules/media/src/ff.rs:8282`). Redirect hops are parsed by a different function
   that keeps libcurl's 443 default, for exactly this reason
   (`rust-modules/media/src/curlio.rs:2046-2049`). So `https://host/file.mkv` must be passed as
   `https://host:443/file.mkv`, or the parser must change. Read from the code, not tested.
3. **Plain `http` needs a dotted-quad host.** The plaintext socket path does no DNS
   (`rust-modules/media/src/player/playurl.rs:44-45`); `https` goes through libcurl
   (`rust-modules/media/src/player/engine.rs:1410-1412`).

Progress sync to Stremio has no existing hook: the reporter is only spawned for a session with a
Plex item key (`rust-modules/media/src/player/engine.rs:1509-1512`,
`rust-modules/media/src/route/decision.rs:10083-10085`). A new reporter can read
`player::playpos_ns()` and `player::duration_ns()` (`rust-modules/media/src/player/mod.rs:529`,
`:542`).

## How often upstream changes each side

From `git log --no-merges --since='3 months ago' --numstat -M` at `9d2777fe`. The repository's
first commit is dated 2026-07-03, so the window (from 2026-07-14) is nearly its whole life: 1,363
non-merge commits, 948 of them touching `rust-modules/`. The crates were split out on 2026-10-03
and 2026-10-04 (first commit of each `Cargo.toml`), so older paths under `rust-modules/src/` were
mapped to crates with the member list in `ci/module-layers.ini`. A commit counts once for every
crate it touches. Line totals are not reported: the split shows up as whole-file adds and deletes.

| Crate | Commits, 3 months | Commits since 2026-10-05 (165 total) |
|---|---:|---:|
| `ui` | 513 | 53 |
| root app (`rust-modules/src`) | 423 | 51 |
| `media` | 325 | 31 |
| `data` | 246 | 27 |
| `plex` | 211 | 20 |
| `screens` | 188 | 49 |
| `gfx` | 127 | 13 |
| `base` | 80 | 6 |
| `telemetry` | 77 | 3 |
| `session` | 73 | 6 |
| `net` | 59 | 3 |
| `platform` | 45 | 8 |
| `appkit` | 25 | 14 |
| `machine` | 15 | 12 |
| `storage` | 2 | 0 |

The six Plex-free crates together were touched by 612 commits in three months and 70 since the
split. The Plex-dependent crates and the root together: 648 and 95. Before step L10 the player
widgets lived under `ui/` (`docs/module-layers.md:76`), so some of `ui`'s older count is work that
now belongs to `appkit`.

Inside `media`, by group:

| Group | Commits, 3 months | Since 2026-10-05 |
|---|---:|---:|
| Player engine and the rest of `player/` | 160 | 18 |
| Route selection (`route/`) | 158 | 22 |
| Demuxer (`ff*.rs`) | 113 | 12 |
| Adaptive bitrate (`abr/`) | 80 | 1 |
| Plex-facing player files (`report`, `sidecar`, `subside`, `preview`) | 36 | 4 |
| HTTPS media path (`curlio*.rs`) | 27 | 2 |
| `aq.rs` | 8 | 1 |
| `hls.rs` | 7 | 0 |

Player core (engine, demuxer, HTTPS path, HLS, adaptive bitrate, queue) was touched by 251 commits;
route selection plus the four Plex-facing player files by 167; 93 commits touched both sides at
once. Since the split: 20, 23 and 12. The busiest single files over three months are `ff.rs` (110
commits), `player/engine.rs` (85), `player/mod.rs` (85), `route.rs` before it became a directory
(81), `route/decision.rs` (59), `player/shared.rs` (57) and `player/pump.rs` (51).

## Candidate cuts

No choice is made here.

### Cut A: no cut in existing crates, a new entry beside them

New crates hold `stremio-core`, the Stremio screens and a small play function that calls the public
functions listed above. The Plex crates (`plex`, `data`, `session`, `telemetry`, and `media`'s
route selection) stay compiled in and unused at run time.

- Edits to existing files: none required for playback by this reading. The port default is handled
  by the caller writing `:443`.
- Stays mergeable from upstream: all 13 crates, including the 325-commit `media`.
- Does not stay mergeable: whatever replaces the root app and `screens`. The root crate is the one
  static library the build links and holds the webOS port's application side
  (`docs/module-layers.md:17-21`, `ci/module-layers.ini:166-176`); it had 423 commits in three
  months, `screens` 188.
- Cost: the fork depends on the public functions listed above keeping their signatures. A change upstream
  shows as a compile error in the new crate, not a merge conflict. The Plex code ships in the
  binary. Title lines, progress and the player's error screen are still Plex-shaped
  (`rust-modules/media/src/route/decision.rs:7473-7476`, `rust-modules/media/src/player/mod.rs:983-989`).
  `appkit`'s player panels read route selection 357 times and may expect state only a plan installs.

### Cut B: move the engine's 19 references down, keep the crate

Change the engine, demuxer, HTTPS path and HLS parser to name `plx_net` for `Origin` and `split`,
take the credential gate as an injected function, and read the User-Agent from the value `net`
already holds. Optionally give `split` a scheme-aware default port.

- Edits to existing files: about 19 one-line changes in `player/engine.rs`, `ff.rs`,
  `ff_subside.rs`, `curlio.rs`, `hls.rs`, plus `net/src/net/origin.rs` if the port default changes.
- Stays mergeable from upstream: everything, with small recurring conflicts. The touched files are
  the busiest in the crate (`ff.rs` 110 commits, `player/engine.rs` 85, `curlio.rs` 27 in three
  months).
- What it buys: the first-hop port problem is fixed at the source, and the engine no longer names
  the Plex crate. It does not remove `plx_plex` from `media`'s `Cargo.toml`, because route
  selection and seven `player/` files still name it. It is the same direction as the project's own
  step L6, which moved the URL types into `net` (`docs/module-layers.md:80`), so it could be
  offered upstream.

### Cut C: split `media` into a player crate and a Plex route crate

Break the `player`-`route` cycle with a trait the player owns (declaration, URL, start transaction,
seek and reload hooks, progress sink), leave route selection, sidecar fetch, telemetry connection
facts and preferences in a Plex-side crate, and give Stremio its own implementation.

- Edits to existing files: the 121 route references in `player/engine.rs` and `player/pump.rs`,
  the 40 Plex references in `player/`, the three in `abr/ladder.rs`, and `appkit`, `screens` and
  the root wherever they name `plx_media::route`.
- Stays mergeable from upstream: the six Plex-free crates. `media` does not: 251 commits touched
  the player-core side in three months and 93 touched both sides in one commit.
- What it buys: the only cut after which the player builds without the Plex, data and session
  crates. It turns the fork into a parallel line for `media`, unless upstream takes the split.

## Not determined

- Whether a session prepared by `set_url` and `set_stream_declaration` and then started in a
  release build behaves as the developer trigger does. The code paths are the same by reading;
  nothing was run.
- Whether a first-hop `https` link without a port really fails on a television. The 32400 default
  is read from the code; issue #1 records that HTTPS links played through the trigger, without
  saying whether they carried a port.
- What `appkit`'s player HUD, track menu and info panel show when no plan was installed (no
  `PlayingItem`, no title, no item key). Only the reference counts were taken.
- How the codecs of a debrid file get known before the Load. The demuxer learns them on open, but
  the declaration is needed first.
- Whether subtitles supplied by an add-on can use the sidecar path, which fetches through a Plex
  client (`rust-modules/media/src/player/sidecar.rs:113-122`).
- Seek, pause-resume from the background and audio switching on a session with no plan. Several of
  those go through route-selection state machines that were not traced
  (`rust-modules/media/src/player/pump.rs:802`, `:1210`).
- Upstream commits after `9d2777fe`. The `upstream` remote was not fetched, so the counts stop at
  the fork point.
- How long each crate takes to build, and how much binary size the unused Plex crates add under
  Cut A.
- Whether upstream would accept Cut B or Cut C.
- The HTTPS path's certificate and key-pinning behaviour for a host that is not a Plex server.
