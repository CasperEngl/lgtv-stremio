# How StremThru Torz marks and delivers cached and uncached streams

Research for [How does StremThru Torz mark and deliver cached and uncached streams?](https://github.com/CasperEngl/lgtv-stremio/issues/45). It follows the model of the Comet research (`docs/research/comet-uncached-streams.md` on branch `research/comet-uncached`).

No stream or playback link was opened. Every fact is tagged **read** (from source or documentation), **run** (a command was executed and its output read) or **derived** (worked out from read or run facts, with the reasoning shown).

## Answer

Torz marks a cached stream with a lightning bolt at the start of the stream's name, so the prototype's `is_cached` test is right for it. An uncached Torz stream carries no symbol of its own: it is the same name without the bolt.

Opening an uncached Torz stream's link adds the torrent to the Real-Debrid account and starts every video file in it, through the same StremThru code Comet uses. The link then answers `302` to a named clip, `…/v0/store/_/static/downloading.mp4`, until the file is downloaded, when it answers `302` to the file. A refusal or failure is also a `302` to a named clip, and the name says why. So the reason can be read from the redirect's address, without recognising a clip by size.

The add-on has no status check other than opening the link again.

The uncached-stream decision needs a second rule. Torz's clips are 12 to 28 kB against Comet's 410 to 434 kB, so the size table knows none of them and a refused Torz download would read as "not ready yet" for the whole 30 minutes. The proposal is in section 6.

## Sources

- **StremThru**: `github.com/MunifTanjim/stremthru` at commit `b66650a5c91833932ecaf815a98c53719f7c0e9f` (2026-10-02, "chore: release 0.105.3"). This is the same commit the Comet research read, and was still the head of the default branch on 2026-10-14. Paths below are relative to that repository.
- **Real-Debrid's numbered errors**: as listed in the Comet research, from <https://api.real-debrid.com/>. Not re-read for this ticket.
- **The hosted instance**: the owner's Torz add-on is served from `stremthru.13377001.xyz` (run: the prototype's stream listing prints each stream's host). Two kinds of public address on that host were read, neither of which carries an account or is a stream link: the unconfigured manifest and the static clips' headers (section 7).
- **The command-line prototype** in `prototype/`, for the per-add-on count in section 8.

## 1. Torz is part of StremThru

- **Read.** Torz is the package `internal/stremio/torz/`, mounted at `/stremio/torz/` (`internal/stremio/torz/torz.go:37-51`). Its manifest names it "StremThru Torz" (`internal/stremio/torz/manifest.go:17`).
- **Run.** The hosted instance's manifest reports `name: StremThru Torz`, `version: 0.105.3`, the release this commit is tagged as.
- **Derived.** Comet's debrid calls and Torz's go through the same StremThru store code, so what happens on the Real-Debrid account is the same for both. Only the answer the client sees differs.

## 2. How a stream is marked

### Read

- Torz always uses StremThru's default name template and offers no setting to change it (`internal/stremio/torz/stream.go:33`). The template (`internal/stremio/transformer/stream_template_default.go:7-9`) writes three lines:
  1. `✨ ` if the instance proxies the file; then, if the stream has a store code, `⚡️ ` if it is cached followed by the code in square brackets, such as `[RD]`; then ` 🔑` if the torrent is private.
  2. The add-on's name, `Torz`.
  3. The resolution.
- A cached stream sets the cached flag and gets a link (`stream.go:830-849`). An uncached stream runs the same template with the flag unset (`stream.go:850-884`), so its first line is `[RD]` with nothing before it. There is no "uncached" symbol.
- Every debrid stream has a store code, so every Torz debrid stream's name starts with either `⚡️ [XX]` or `[XX]` (after an optional `✨ `).
- Cached streams are listed first, then uncached ones (`stream.go:888-899`).
- With the add-on's "cached only" setting on, uncached streams are left out (`internal/stremio/torz/userdata.go:22`, `stream.go:850`).
- Uncached private torrents are left out unless a setting allows them, and then only for TorBox (`stream.go:859-861`).
- With the store set to peer-to-peer, the stream is a bare torrent with the code `[P2P]`, no bolt and no link (`stream.go:817-829`). That is a peer-to-peer stream, which the map rules out of scope.
- If more than one debrid service is configured, an uncached torrent is listed once per service (`stream.go:851-885`).
- The marking is remembered, not asked live. It comes from StremThru's own table of earlier observations (`store/realdebrid/store.go:412`, `internal/buddy/store.go:168-195`), and an entry counts as fresh for at least 18 hours when cached and 6 hours when uncached on an instance connected to an upstream (`docs/configuration/index.md:163-181`).
- StremThru records a torrent as cached when a link to its file has been generated (`internal/stremio/torz/playback.go:237`, where the cache-miss argument is false once the torrent is downloaded).
- If the cached check fails for the only configured service, the whole stream request is answered with an HTTP error and no streams (`stream.go:794-805`).

### Run

- The bolt in the template is U+26A1 followed by U+FE0F (bytes `e2 9a a1 ef b8 8f`, from `od` on the template line).
- On the owner's account all 4,153 Torz streams over five titles were direct links, so the add-on is configured with a debrid service, not peer-to-peer (section 8).

### Derived

- `is_cached` in `prototype/src/main.rs` looks for U+26A1 anywhere in the name, so it matches Torz's cached streams. Its comment, "Comet and StremThru both mark held files with a lightning bolt in the stream's name", is correct for Torz.
- A Torz stream cannot carry "no marking at all" in the sense of saying nothing: the absence of the bolt after a store code means uncached. But a client that looks for the bolt and for Comet's `⬇️` would find neither on an uncached Torz stream and call it unknown. To put it in the stream list's Not cached section the app must recognise it as Torz's, by the link's path (`/stremio/torz/…/_/strem/…`) or by a first line that is a bracketed store code.
- As with Comet, the marking can be wrong in both directions, so a clip can be met on any stream.
- A finished download is marked cached on a later stream list only after its link has been opened once more with the file ready, or after another user's observation reaches the instance. It does not flip by itself when the download finishes.

## 3. What opening a link does

### Read

- Cached and uncached streams share one handler, at `/stremio/torz/{configuration}/_/strem/{title id}/{store code}/{torrent hash}/{file index}/{filename}` (`torz.go:47-48`). It does not look at the marking.
- `GET` and `HEAD` both run the whole handler (`playback.go:46`). A `HEAD` is not a side-effect-free check.
- The handler first looks for an answer it remembered for the same client address, service, token, title, torrent, file index and filename. If it has one it redirects to it and calls nothing (`playback.go:79-86`). A file's link is remembered for 3 hours (`playback.go:26-29`, `:268`); a clip's address for 1 minute (`playback.go:31-34`).
- Otherwise it adds the torrent to the account (`playback.go:130`). For Real-Debrid that is the code the Comet research describes (`store/realdebrid/store.go:240-370`): find the torrent by hash on the account; add the magnet if it is not there; wait up to 5 polls, 5 seconds apart, for file selection; select every video file. A torrent already on the account in an error state, or with a different file selection, is deleted and added afresh (`store.go:184-187`, `:282-291`).
- It then asks for the torrent's status up to 3 times, 5 seconds apart, waiting for "downloaded" (`playback.go:187`, `internal/stremio/shared/store.go:41-68`).
- Downloaded: it picks the file, asks the service for a link, remembers it and answers `302` to it (`playback.go:205-290`). If the instance proxies files, the link is the instance's own proxy address (`internal/shared/store.go:230-249`).
- Not downloaded, and queued, downloading or processing: it answers `302` to the downloading clip (`playback.go:194-197`, `:283-286`).
- The clip's address is `<instance>/v0/store/_/static/<name>.mp4` (`internal/store/video/video.go:59-67`). It is a public address that needs no account (`internal/endpoint/store.go:443-454`, `:469`).

### Derived

- The first open of an uncached Torz link has the same effect on the account as Comet's: a torrent is added and every video file in it starts downloading.
- "Ready" is "the link redirects somewhere other than a static clip". Unlike Comet, the not-ready answer is also a redirect, so the HTTP status alone never tells ready from not ready; the redirect's address does.
- An open that reaches the debrid service takes at least 15 seconds before it answers with the downloading clip (3 polls × 5 s), and up to 40 seconds for a torrent that is new to the account (5 × 5 s for file selection, then 3 × 5 s). A client's timeout has to allow for that.
- Opening the link again within a minute returns the remembered clip address and does not ask the service. Checking every 30 seconds therefore gets a fresh answer at most once a minute.
- Because a failed torrent is deleted and re-added on the next open, an open after a slow failure most likely answers with the downloading clip again, not the failed one. This follows from the Real-Debrid code both add-ons share. It was not run.

## 4. How a refusal or failure is answered

### Read

Every failure inside the handler is a `302` to a named clip (`playback.go:281-287`). Which one:

| Cause | Clip name | Source |
| --- | --- | --- |
| Still queued, downloading or processing after the wait | `downloading` | `playback.go:194-197` |
| The service rejects the token | `401` | `playback.go:140-143` |
| The service says too many requests | `429` | `playback.go:144-147` |
| Unavailable for legal reasons | `451` | `playback.go:148-151` |
| Payment required | `payment_required` | `playback.go:152-155` |
| Account limit exceeded | `store_limit_exceeded` | `playback.go:156-158` |
| The service is down | `500` | `playback.go:159-162` |
| Any other error while adding the torrent | `download_failed` | `playback.go:131-136` |
| The torrent is failed, invalid or in an unknown state after adding | `download_failed` | `playback.go:198-200` |
| No file in the torrent matches the title | `no_matching_file` | `playback.go:251-256` |
| The status could not be read, or the link could not be generated | `500` | `playback.go:189-193`, `:259-265` |
| A private torrent's file could not be fetched or decoded | `500` | `playback.go:97-127` |

- Real-Debrid's numbered errors reach that switch through StremThru's translation (`store/realdebrid/error.go:51-90`):

| Real-Debrid error | Clip Torz redirects to |
| --- | --- |
| 35 Infringing file | `451` |
| 21 Too many active downloads, 23 Traffic exhausted, 36 Fair Usage Limit | `store_limit_exceeded` |
| 34 Too many requests, 5 Slow down | `429` |
| 8 Bad token | `401` |
| 9 Permission denied, 14 Account locked, 22 IP Address not allowed | `download_failed` |
| 24 File unavailable | `download_failed` |
| 29 Torrent too big, 28 File not allowed | `download_failed` |

- A magnet that never reaches file selection within the 25 seconds is an error of a kind the switch does not match (`store.go:189-209`, `core/error.go:75-84`), so it answers `download_failed`.
- A bad configuration segment in the address is answered with an HTTP error in JSON, not a clip (`playback.go:60-71`).
- Three clips exist that Torz never redirects to: `200`, `403` and `content_proxy_limit_reached`.

### Run

Measured on the files in `internal/store/video/` at this commit, with `stat` and `ffprobe`. Every clip is 1280×720 H.264, 30.0 seconds, with no audio track.

| Clip | Bytes |
| --- | --- |
| `200` | 11,992 |
| `403` | 14,766 |
| `no_matching_file` | 17,361 |
| `download_failed` | 18,408 |
| `429` | 18,677 |
| `downloading` | 18,847 |
| `401` | 18,911 |
| `store_limit_exceeded` | 19,987 |
| `500` | 20,404 |
| `content_proxy_limit_reached` | 22,722 |
| `451` | 23,172 |
| `payment_required` | 27,966 |

### Derived

- The reason can be read without recognising a clip by size: it is the last part of the address the link redirects to. The twelve names are distinct.
- Size also works for Torz, and better than for Comet: all twelve sizes differ, so size alone names the reason too.
- None of the twelve sizes is near Comet's 410 to 434 kB. Against Comet's table every Torz clip is an unknown clip.
- The clips have no audio track, so the automatic pick's test for an error clip (a probe that finds no audio track) holds for Torz. A test that depended on the clip being 8 seconds long would not: these are 30 seconds.
- `download_failed` does not always mean a permanent failure. It also covers a magnet whose details were slow to arrive and three account-level refusals.

## 5. Checking status without opening the link

### Read

- The add-on has two kinds of address, the stream list and the playback link (`torz.go:36-51`). Neither reports a download's progress.
- StremThru has a separate store interface with a status per torrent (`GET /v0/store/torz`, `GET /v0/store/torz/{id}`, statuses `queued`, `downloading`, `downloaded`, `failed` and others; `docs/api/torz.md`). It needs the debrid service's token in a request header (`docs/api/store.md`) and the torrent's id on the account, which the playback link never returns. It reports no percentage.

### Derived

- For the app as decided, there is no status check other than opening the link again. The store interface would mean the app handling the Real-Debrid token itself, which the uncached-stream decision ruled out ("the app does not talk to Real-Debrid itself").
- Asking for the stream list again is not a status check: the marking does not change when a download finishes (section 2).

## 6. Proposal: a second rule for the uncached-stream decision

What the closed decision says, and what changes for Torz:

| Decision today | For Torz |
| --- | --- |
| Clips are told apart by size, against a table of Comet's 55 sizes. | Add: a link that redirects to an address ending `/v0/store/_/static/<name>.mp4` is a StremThru clip, told apart by `<name>`. Size is the fallback, against a second table of the 12 sizes above. |
| Known downloading clip: keep waiting. | `downloading`: keep waiting. |
| Known error clip: stop. | Any other name: stop, with the existing failure read-out. |
| Unknown clip: keep waiting, "not ready yet". | Unchanged, and now only for a clip that matches neither add-on's rule. |
| The reason is not shown, since several error clips share a size. | The reason can be shown for Torz, since each name is one reason. Whether to show it is a wording choice; nothing forces it. |
| The app opens the link again every 30 seconds. | Unchanged. A fresh answer arrives at most once a minute, and each fresh open takes 15 to 40 seconds to answer. |

Two further points the same follow-up should settle, because they follow from the same facts:

- **The stream list's sections.** An uncached Torz stream has no uncached symbol. Unless the app recognises it as Torz's, it lands in Unknown. Over the five titles in section 8 that would be 4,083 of 4,935 streams.
- **Scope.** The map says the first version is "tested against Comet with Real-Debrid; any other add-on on the account still loads". Torz's cached streams already pass the cached test, so the automatic pick opens them today whether or not Torz is in scope.

Nothing else in the decision changes: starting with no prompt, the 30-minute limit, the saved started downloads and the rule that the app never deletes from the account all hold for Torz as they are.

## 7. The hosted instance

### Run

- `GET /stremio/torz/manifest.json` on `stremthru.13377001.xyz` (the unconfigured manifest, no account): `version` is `0.105.3`.
- `HEAD /v0/store/_/static/<name>.mp4` for all twelve names: each answered `200`, `content-type: video/mp4`, `accept-ranges: bytes`, a `last-modified` date and no `etag`, with a `content-length` equal to the size in section 4. An invented name answered `404`.

### Derived

- The hosted instance's clips match this commit's, so the size table and the names hold there as of 2026-10-14.

## 8. Streams per add-on on the owner's account

### Run

`lgtv-stremio streams <type> <id>` on 2026-10-14, without `--probe` and without `play`, so no stream link was opened. The five titles are this session's choice; the ids of the five measured earlier are not recorded. "Cached" is the prototype's bolt test.

| Title | Torz streams | Torz cached | Comet streams | Comet cached | Other |
| --- | --- | --- | --- | --- | --- |
| `tt1375666` (film) | 1,090 | 9 | 340 | 58 | 3 |
| `tt15239678` (film) | 1,204 | 10 | 121 | 51 | 4 |
| `tt0133093` (film) | 963 | 10 | 180 | 51 | 3 |
| `tt0944947:1:1` (episode) | 572 | 23 | 98 | 42 | 1 |
| `tt0903747:1:1` (episode) | 324 | 18 | 30 | 19 | 2 |
| **Total** | **4,153** | **70** | **769** | **221** | **13** |

### Derived

- Torz supplied 84 % of the streams (4,153 ÷ 4,935) and 24 % of the cached ones (70 ÷ 291).
- 4,083 of the 4,935 streams (83 %) were uncached Torz streams (4,153 − 70).
- Comet's totals here (769 streams, 221 cached) differ from the map's earlier figure for Comet (2,559 streams, 130 cached over five titles). The titles differ and the earlier run's ids are not recorded, so the two are not comparable.

## Not determined

- What a real open answers on the hosted instance: the exact status line and headers of the `302`, and how long it takes. Only opening a link can settle that, and none was opened.
- Whether the hosted instance proxies Real-Debrid files for this account. If it does, a ready link redirects to the instance's own proxy address instead of to Real-Debrid.
- Whether a torrent that fails slowly ever answers with `download_failed`, or always shows `downloading` again after being re-added (section 3, derived, not run).
- How long a typical download takes, and how long Real-Debrid keeps the torrent afterwards. Unchanged from the Comet research.
- What is drawn in each clip. The files were measured, not viewed.
- Why Torz marks so few of its streams cached (70 of 4,153). The marking is the instance's memory of earlier observations; nothing read says how complete that memory is.
- Whether the app's network layer can read the address a link redirected to. That belongs to the build, and size is the fallback if it cannot.
