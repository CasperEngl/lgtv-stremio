# How Comet delivers an uncached stream through Real-Debrid

Research for [issue #2](https://github.com/CasperEngl/plx-native/issues/2). Read from source and documentation only; no stream link was opened and no account was used.

## Answer

Opening an uncached stream's direct link adds the torrent to the Real-Debrid account and starts it, with every video file selected. While Real-Debrid is fetching, the same link answers `200` with an 8-second silent MP4 status clip served from the link's own address (no redirect, no HTTP error). Once the torrent is downloaded, the same link answers `302` to the Real-Debrid file. So "ready" is "the link redirects"; "not ready" and "refused" are both a small `200` clip and differ only in which clip.

Comet has no status endpoint. The only way to ask is to open the link again, which in the normal case adds nothing new but is not free of side effects. The cached/uncached marking exists only as an emoji in the stream's display name and reflects what Comet believed when it built the list, so a client must handle the status clip on any stream.

## Sources

- **Comet**: `github.com/g0ldyy/comet` at commit `f56677f05ed9a158f9a0338ad2f44d8efde35969` (2026-07-29). Paths below are relative to that repository.
- **StremThru**: `github.com/MunifTanjim/stremthru` at commit `b66650a5c91833932ecaf815a98c53719f7c0e9f` (2026-10-02). Comet does not talk to Real-Debrid itself; every debrid call goes through a StremThru server (`comet/debrid/manager.py:69-84`, `comet/debrid/stremthru.py:96`, default `STREMTHRU_URL` in `comet/core/models.py:263`). What happens on the Real-Debrid account is therefore decided by StremThru's code.
- **Real-Debrid API documentation**: <https://api.real-debrid.com/>.

A hosted instance may run a different Comet commit and a different StremThru. Everything below describes these two commits.

## 1. What the first request triggers, and whether it is repeatable

### Stated by the source

- Cached and uncached streams use the same playback endpoint. Comet does not look at the marking when a link is opened (`comet/api/endpoints/playback.py:184-202`).
- Comet first looks for a link it generated for this account, torrent, season and episode in the last hour. If it finds one it uses it and makes no debrid call (`playback.py:238-262`; one hour is `DOWNLOAD_LINK_CACHE_TTL = 3600`, `comet/core/database.py:42`).
- Otherwise it builds a magnet link from the torrent hash and sends `POST /v0/store/magnets` to StremThru (`playback.py:339-357`, `comet/debrid/stremthru.py:427-437`). This happens on every open that has no fresh stored link.
- StremThru, for Real-Debrid (`store/realdebrid/store.go:240-370`):
  - looks for a torrent with that hash already in the account, listing the account's torrents if it has no recent record (`262-271`);
  - if there is none, calls Real-Debrid's add-magnet (`294-307`);
  - if the torrent is not yet queued, downloading or downloaded, polls up to 5 times, 5 seconds apart, for the "waiting for file selection" status, then selects **all video files** in the torrent (`333-348`, loop at `189-209`);
  - returns the torrent's status and files (`350-369`).
- If a torrent with that hash is already in the account, StremThru does not add it again (`272-294`). It **deletes** the existing one first when it is in an error state, or when it is queued, downloading or downloaded with a file selection other than "exactly all video files" (`184-187`, `282-291`), and then adds it afresh.
- Real-Debrid documents the calls involved: `POST /torrents/addMagnet` ("Add a magnet link to download"), `POST /torrents/selectFiles/{id}` ("Select files of a torrent to start it"), `GET /torrents/info/{id}`, `DELETE /torrents/delete/{id}` (<https://api.real-debrid.com/>).
- When the torrent is downloaded, Comet picks a file, asks StremThru for a download link (Real-Debrid's `POST /unrestrict/link`, `store.go:419-447`), stores it for an hour and redirects (`stremthru.py:661-682`, `playback.py:377-395`).
- Comet forwards the viewer's IP address to StremThru, which passes it to Real-Debrid, unless Comet is proxying the stream (`playback.py:345`, `store.go:301`).

### Inferred

- The first open of an uncached link puts a torrent in the account and starts downloading every video file in it, not just the wanted episode. It counts against the account's active-torrent limit (`GET /torrents/activeCount` returns "currently active torrents number and the current maximum limit", Real-Debrid docs).
- Opening the link again while the torrent is in progress is idempotent in the usual case: StremThru finds the torrent by hash and only reads its status. It still costs Real-Debrid API calls (a torrent list, a torrent info), against a documented limit of 250 requests per minute.
- It is not side-effect free in two cases: a failed torrent is deleted and re-added on the next open (so each open is a retry), and a torrent the user added themselves with a different file selection is deleted and replaced.
- The first open can take a long time to answer: up to about 25 seconds of polling inside StremThru before Comet gets a status.

## 2. What the link answers while fetching, and how to tell states apart

### Stated by the source

- StremThru maps Real-Debrid's torrent statuses to its own (`store/realdebrid/store.go:21-48`); Comet sorts those into three groups (`comet/debrid/stremthru.py:80-84`, `442-460`):

| Real-Debrid status | StremThru status | Comet answer |
| --- | --- | --- |
| `downloaded` | `downloaded` | `302` to the file |
| `waiting_files_selection`, `queued`, `downloading`, `compressing`, `uploading` | `queued`, `downloading`, `processing`, `uploading` | `MEDIA_NOT_CACHED_YET` clip |
| `magnet_error`, `error`, `virus`, `dead`, `magnet_conversion` | `failed`, `invalid` | `STORE_MAGNET_INVALID` clip |
| anything else | `unknown` | `UNKNOWN` clip |

- A status clip is sent as a file response from the playback address itself, with `Cache-Control: no-store, no-cache, must-revalidate, max-age=0`, `Pragma: no-cache`, `Expires: 0` (`comet/services/status_video.py:73-100`, `comet/utils/cache.py:11-15`). There is no redirect to a static address and no error status code. This differs from StremThru's own add-on, which redirects to `.../static/<code>.mp4`.
- The clips are files in `comet/assets/status_videos/`, one per status key, 55 at this commit. The key is chosen from the debrid error; if no clip matches, `UNKNOWN.mp4` is used (`status_video.py:50-70`).
- The only non-video answer is a JSON `500` when the clip file itself is missing on the server (`status_video.py:80-95`).
- A ready file is answered with `302` and the debrid download address in `Location` (`playback.py:395`). If the instance has stream proxying switched on and the user's configuration carries the right password, Comet streams the file through itself instead of redirecting (`playback.py:265-268`, `386-393`).
- Other reasons for the `UNKNOWN` clip: the torrent holds no video file, or no file has a link (`stremthru.py:489-491`, `606-610`). A series torrent with no file matching the requested episode raises `EPISODE_MATCH_NOT_FOUND`, which has no clip of its own and so also shows `UNKNOWN` (`stremthru.py:593-605`).

### Measured from the files at this commit (not from a server)

- Every clip checked (`MEDIA_NOT_CACHED_YET`, `UNKNOWN`, `UNAVAILABLE_FOR_LEGAL_REASONS`) is 8.0 seconds long and has no audio track. All 55 are between 410 kB and 434 kB.
- `MEDIA_NOT_CACHED_YET.mp4` is 433,923 bytes and no other clip has that size. Sizes are not unique in general: `UNAVAILABLE_FOR_LEGAL_REASONS.mp4` (410,511 bytes) shares its size with five other clips.

### Inferred

- Without decoding video, with redirect-following switched off:
  - `302` with a `Location` on another host: ready.
  - `200`, a video body of roughly 0.4 MB, and the no-store headers above: a status clip. The file is not ready or was refused.
- Telling "still fetching" from "refused" needs the clip's identity. The response carries nothing but the body: no header names the status key. `Content-Length` 433,923 identifies the fetching clip at this commit, but that is a property of one asset file, not a contract, and a hosted instance may ship different files.
- On an instance that proxies streams, a ready file is also a `200` or `206` video response. Size and the no-store headers are then the only distinction.
- The route is declared for `GET` only (`playback.py:184`), so a `HEAD` request is probably rejected rather than answered cheaply. Not confirmed, and a `GET` that reads only the headers triggers the same work on the server as a full one.

## 3. Asking for status without triggering anything, and how long a fetch takes

### Stated by the source

- Comet's public routes are the manifest, the stream list, playback, the debrid-sync trigger, configuration pages and integrations for other clients. None reports the progress of a torrent (route declarations in `comet/api/endpoints/*.py`; flow described in `docs/advanced/03-streaming-and-debrid-flow.md`).
- Real-Debrid's own API has what a progress display needs: `GET /torrents/info/{id}` returns `status`, `progress` ("0 to 100"), `speed` and `seeders` (Real-Debrid docs). StremThru exposes the same through `GET /v0/store/magnets/{id}` (`internal/endpoint/store.go:465`). Both need the account's API token.
- Real-Debrid's documentation has no endpoint that says whether a torrent is cached before it is added, and says nothing about how long a download takes.

### Inferred

- Through Comet alone, the only status check is opening the playback link again. That is safe to repeat in the usual case (section 1) but is the same request that starts the download, so it cannot be used before the user has chosen the stream.
- Asking for the stream list again does not trigger a download, but the marking it returns can lag (section 4), so it is not a reliable readiness signal.
- A percentage or time remaining is only available from Real-Debrid or StremThru directly with the account's token. Comet gives a client two states: clip or redirect.
- Fetch time depends on the torrent's size and on how many peers are seeding it. No source gives a typical figure.

## 4. How cached and uncached streams are marked, and whether to rely on it

### Stated by the source

- The marking is an emoji inside the stream's `name`: `[{service}{icon}] Comet {resolution}`, with `⚡` for cached and `⬇️` for uncached, and `RD` as the service code for Real-Debrid (`comet/api/endpoints/stream.py:75-85`, `457-465`; `comet/debrid/manager.py:8`).
- Clients that identify themselves as Kodi get a plain form instead: `[RD C]` and `[RD U]` (`stream.py:87`, `464`).
- No structured field carries it. `behaviorHints` holds only `bingeGroup`, `filename` and, when known, `videoSize` (`stream.py:448-455`).
- Two weaker signals: uncached streams are listed after all cached ones unless the user chose mixed sorting (`stream.py:491-494`, `538-541`), and the file-index part of an uncached link is always `n` (`stream.py:478-481`). A cached stream whose file index is unknown also gets `n`.
- With the "cached only" option on, uncached streams are left out entirely (`stream.py:442-443`).
- Comet's documentation says only that debrid streams come "with cached/uncached indicators" (`docs/advanced/03-streaming-and-debrid-flow.md:26`). It does not define the format.
- The marking is not a live answer from Real-Debrid. It is merged from Comet's own table of earlier results, kept for one day by default (`DEBRID_CACHE_TTL`, `comet/core/models.py:176`; `comet/services/debrid_cache.py:158-168`), an optional snapshot of the account's torrents, and StremThru's check endpoint (`comet/services/media_search.py:642-706`). StremThru answers that check from its own database of earlier observations (`store/realdebrid/store.go:412`, `internal/buddy/store.go:168-195`).

### Inferred

- The format has been the same string template for the non-Kodi path at this commit, but it is a display string, not an interface. Parsing `⚡` versus `⬇️` (U+2B07, optionally followed by U+FE0F) inside the leading square brackets is workable; treat anything unrecognised as "unknown", not as cached.
- Because the marking is remembered rather than checked, it can be wrong both ways. A stream marked cached can have left Real-Debrid's cache, in which case opening it starts a download and shows the fetching clip. A stream marked uncached may redirect at once.
- The plan should therefore not use the marking to decide whether a link is safe to open automatically without also handling the status clip, and should handle the clip on every stream.

## 5. What happens when the debrid service refuses a file

### Stated by the source

- A Real-Debrid error at any step (adding the magnet, selecting files, generating the link) reaches Comet as a StremThru error object with a `code` and the original Real-Debrid error under `__upstream_cause__` (`internal/server/legacy_error.go:31-46`, `store/realdebrid/response.go:12-16`).
- Comet turns it into a list of status keys: the upstream error's `code` or `error` text first, then StremThru's code (`comet/debrid/stremthru.py:118-122`, `188-202`; `comet/debrid/exceptions.py:44-51`). It serves the first key that has a clip, otherwise `UNKNOWN` (`playback.py:358-363`).
- StremThru's translation of Real-Debrid's numbered errors (`store/realdebrid/error.go:51-90`; numbers listed at <https://api.real-debrid.com/>) includes:

| Real-Debrid error | StremThru code |
| --- | --- |
| 35 Infringing file | `UNAVAILABLE_FOR_LEGAL_REASONS` |
| 21 Too many active downloads, 23 Traffic exhausted, 36 Fair Usage Limit | `STORE_LIMIT_EXCEEDED` |
| 34 Too many requests, 5 Slow down | `TOO_MANY_REQUESTS` |
| 8 Bad token | `UNAUTHORIZED` |
| 9 Permission denied, 14 Account locked, 22 IP Address not allowed | `FORBIDDEN` |
| 24 File unavailable | `NOT_FOUND` |
| 29 Torrent too big, 28 File not allowed | `UNPROCESSABLE_ENTITY` |

- A clip exists for each of those codes in `comet/assets/status_videos/`.
- A torrent that Real-Debrid accepts and then fails (`error`, `virus`, `dead`, `magnet_error`) shows the `STORE_MAGNET_INVALID` clip (section 2).
- A refusal is never stored: only a successful link is written to the link table (`playback.py:377-384`), so the next open asks again.

### Inferred

- A refusal looks to the client exactly like "still fetching": `200`, a silent 8-second clip, no-store headers. Only the clip differs.
- For Real-Debrid the upstream error has no `code` field, so the first key is Real-Debrid's own error text, which has no clip, and the StremThru code decides the clip.
- A magnet whose metadata never resolves does not reach file selection within StremThru's five polls and comes back as an error, most likely the `UNKNOWN` clip.

## Not determined

- Which Comet commit and which StremThru the hosted instance runs, and whether it proxies streams. All behaviour above is for the two commits named.
- The response's exact status line and headers on a real server (`Content-Type`, `Content-Length`, `ETag`, range support, the answer to `HEAD`). These come from the web framework and were not read or tested.
- Whether the clip sizes on the hosted instance match this commit, and so whether `Content-Length` can identify the fetching clip there.
- What is drawn in each clip. The files were measured, not viewed.
- How long a typical uncached fetch takes on Real-Debrid. No source documents it.
- Whether the stream list's marking flips to cached after a download finishes, and how soon. It depends on Comet's and StremThru's remembered results and their expiry settings on the instance.
- Whether the torrent stays in the Real-Debrid account afterwards and for how long. Nothing in Comet's playback path removes it.
- Real-Debrid's exact error text for each numbered error, and therefore which first status key Comet tries before falling back to StremThru's code.
