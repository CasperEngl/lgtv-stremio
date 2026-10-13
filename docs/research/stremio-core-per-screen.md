# What stremio-core gives a host for each first-version screen

Research for [issue #4](https://github.com/CasperEngl/plx-native/issues/4), part of the map at [issue #1](https://github.com/CasperEngl/plx-native/issues/1).

## Answer

Every first-version screen has a ready model in `stremio-core`: the host adds one field per screen to its model struct, dispatches a `Load` action aimed at that field, and reads plain Rust structs back.
Beyond fetch, storage and a task runner, the host owns four things: polling the link code and turning the returned key into a session, feeding the player model a steady stream of time, pause, seek and end actions, downloading and rendering subtitle files, and choosing which stream to play.
`StreamingServer` can be left out of the model. `Player` and `Ctx` only read the streaming-server URL setting, and debrid HTTPS streams pass through unchanged unless an add-on sets proxy headers on them.
The two official hosts carry 4,232 and 6,062 lines of Rust glue, of which most is translation to JavaScript or Protobuf that a Rust host does not need. Estimate for this host: 1,000 to 2,000 lines, excluding drawing and stream picking.

## Sources and how they are cited

- **core** = `github.com/Stremio/stremio-core` at commit `c4806e8614452fd49d5dbb22db74afa88959b554` (the commit the prototype pins). Paths such as `src/models/player.rs:160` are relative to that repository root. `stremio-core-web` lives in the same repository.
- **kotlin** = `github.com/Stremio/stremio-core-kotlin` at `2a8083f1026603e7c49f104473340d110902a72c` (20 March 2026). It tracks core's `development` branch (`Cargo.toml:6`), so it is older than the pinned core commit.
- **web** = `github.com/Stremio/stremio-web` at `9d1d526591b4c076c7307a1ba9ec056d483f169a` (12 October 2026). This is the JavaScript interface that sits on `stremio-core-web`; it shows which actions a real client dispatches and when.
- **link-ui** = `github.com/Stremio/stremio-account-link-ui` at `f02c8f6229bfde989164d435deb9db5c4925b2f6` (25 October 2021).
- **prototype** = `/home/casperengl/Work/lgtv-stremio` at `8dffb28`.

Everything below was read from source. Nothing was run against Stremio's API.

## Per-screen table

"Field" means a field of the host's model struct. All `Load` and `Unload` actions must be dispatched at a named field (see "How dispatch works").

| Screen | Model (type) | Actions the host dispatches | State exposed, and what the host supplies |
|---|---|---|---|
| Sign in on a TV | `Link<LinkAuthKey>`, then `Ctx` | `Load(Link)`; `Link(ReadData)` repeatedly; then `Ctx(Authenticate(LoginWithToken))` or `Ctx(PullUserFromAPI { token })`; `Ctx(Logout)` | `code`: loading, error, or `{ code, link, qrcode }`. `data`: loading, error, or `{ auth_key }`. `ctx.profile.auth` once signed in. Host supplies: the poll timer, the QR or code drawing, the follow-up sign-in action. |
| Continue Watching | `ContinueWatchingPreview` (row) or `LibraryWithFilters<ContinueWatchingFilter>` (full list) | None for the row: it updates itself. `Ctx(RewindLibraryItem(id))` or `Ctx(RemoveFromLibrary(id))` to dismiss. | `items: Vec<Item>`, each a `LibraryItem` plus a notification count, newest first, capped at 100. Host supplies: progress bar from `state.time_offset / state.duration`, and the route from an item to a stream. |
| Library | `LibraryWithFilters<NotRemovedFilter>` (one grid) or `LibraryByType<NotRemovedFilter>` (one row per type) | `Load(LibraryWithFilters(Selected { request: { type, sort, page } }))`, `LibraryWithFilters(LoadNextPage)`; or `Load(LibraryByType(Selected { sort }))`, `LibraryByType(LoadNextPage(row))`. `Ctx(AddToLibrary)`, `Ctx(RemoveFromLibrary)`, `Ctx(SyncLibraryWithAPI)`. | `catalog: Vec<LibraryItem>` and `selectable { types, sorts, next_page }`, each option carrying the request to load it; or `catalogs: Vec<Vec<Vec<LibraryItem>>>` (rows of pages). No network: built from `ctx.library`. |
| Home board | `CatalogsWithExtra` | `Load(CatalogsWithExtra(Selected { type: None, extra: [] }))`, then `CatalogsWithExtra(LoadRange(a..b))` as rows scroll into view, `CatalogsWithExtra(LoadNextPage(row))` | `catalogs: Vec<Vec<ResourceLoadable<Vec<MetaItemPreview>>>>`: one entry per add-on catalogue, each a list of pages, each page not requested, loading, ready or failed. Host supplies: row titles (looked up from the add-on manifest by `request.base` and `request.path`). |
| Add-on catalogue (one catalogue, filterable) | `CatalogWithFilters<MetaItemPreview>` | `Load(CatalogWithFilters(Some(Selected { request })))`, `CatalogWithFilters(LoadNextPage)` | `catalog` (pages of `MetaItemPreview`) and `selectable { types, catalogs, extra, next_page }`, each option carrying the request to load it. |
| Search | A second `CatalogsWithExtra` field; optionally `LocalSearch` for suggestions | `Load(CatalogsWithExtra(Selected { type: None, extra: [search = query] }))`, `LoadRange`; for suggestions `Load(LocalSearch)` once, then `Search(Search { search_query, max_results })` per keystroke | Same shape as the board, limited to catalogues that accept `search`. `LocalSearch.search_results: Vec<Searchable>`. `ctx.search_history` records each query. Host supplies: the on-screen keyboard and debounce. |
| Title page with streams | `MetaDetails` | `Load(MetaDetails(Selected { meta_path, stream_path, guess_stream }))`; `MetaDetails(MarkAsWatched / MarkVideoAsWatched / MarkSeasonAsWatched)`; `Ctx(AddToLibrary)` | `meta_items` (one per add-on that serves meta), `streams` (one loadable list per add-on that serves streams), `meta_streams`, `last_used_stream`, `library_item`, `watched`. Host supplies: season and episode grouping, the stream pick, cached or uncached marking, the "cannot play" marking. |
| Player | `Player` | `Load(Player(Selected { stream, stream_request, meta_request, subtitles_path }))`; `Player(PausedChanged)`, `Player(TimeChanged)`, `Player(Seek)`, `Player(Ended)`, `Player(NextVideo)`, `Player(VideoParamsChanged)`, `Player(StreamStateChanged)`; `Unload` on exit | `stream` (converted URL), `library_item` (resume position), `meta_item`, `series_info`, `next_video`, `next_stream`, `subtitles`, `stream_state`, `intro_outro`. Host supplies: the decoder, the position clock, subtitle download and rendering, the track menus. |

## How dispatch works (applies to every row)

- `Runtime::dispatch` takes `RuntimeAction { field: Option<Field>, action }`. With a field it updates only that field; without one it runs the action through every field. Source: core `src/runtime/runtime.rs:57-69`.
- Every screen model clears itself on `Action::Unload`: `link.rs:65`, `catalogs_with_extra.rs:56`, `catalog_with_filters.rs:188`, `library_with_filters.rs:192`, `library_by_type.rs:79`, `meta_details.rs:123`, `player.rs:390` (all under core `src/models/`). An `Unload` without a field therefore clears every screen at once.
- Two fields of the same type both answer the same `Load`. The board and search are both `CatalogsWithExtra` in the official hosts (core `stremio-core-web/src/model/model.rs:48,55`), so their `Load` must name the field. The web client always passes the field name, for example `'player'` in web `src/routes/Player/usePlayer.js:93-99`.
- The prototype dispatches with `field: None` (prototype `src/main.rs:80-82`). That is safe with one catalogue field and one title field and stops being safe once the board and search coexist.
- After each update the runtime emits `RuntimeEvent::NewState(changed_fields)` and, separately, `RuntimeEvent::CoreEvent(Event)` for things such as `UserAuthenticated`, `LibraryItemsPushedToAPI`, `PlayerEnded` and `Error`. Source: core `src/runtime/runtime.rs:15-18,79-123`, `src/runtime/msg/event.rs:17-164`. The changed-field list is the redraw signal.

## Bullet 1: model, actions and drawable state per screen

### Sign in on a TV

- The model is `Link<T>` with two fields: `code: Option<Loadable<LinkCodeResponse, LinkError>>` and `data: Option<Loadable<T, LinkError>>`. Source: core `src/models/link.rs:33-39`.
- `Load(Link)` requests a code and clears `data`. Source: core `src/models/link.rs:48-55,114-126`.
- The code response is `{ code, link, qrcode }`, all strings. Source: core `src/types/api/response.rs:89-94`.
- `Link(ReadData)` asks once whether the code has been used. It does nothing unless a code is ready. Source: core `src/models/link.rs:56-64,128-144`.
- A successful read is `LinkAuthKey { auth_key }`. Source: core `src/types/api/response.rs:96-115`.
- The requests are `GET https://link.stremio.com/api/v2/create?type=Create` and `.../api/v2/read?type=Read&code=...`. Source: core `src/types/api/request.rs:264-295` (endpoint, version `v2`, paths, and the query serialised from the tagged enum), `src/types/api/fetch_api.rs:17-23` (the `api/` prefix), `src/constants.rs:90-91`.
- The person finishes the flow in a browser. `link.stremio.com` asks for "the 4-character code displayed on your app" and forwards to `https://link.stremio.com/<CODE>`; a wrong or old code shows "Code Expired". Source: link-ui `index.html:80-91`, `404.html` ("Code Expired" block).
- Both official hosts include the field as `auth_link: Link<LinkAuthKey>`. Source: core `stremio-core-web/src/model/model.rs:45`; kotlin `stremio-core-kotlin/src/commonMain/rust/model/model.rs:35`.
- Core has no action that goes from a link key straight to a signed-in profile. Two existing actions accept a key:
  - `Ctx(Authenticate(AuthRequest::LoginWithToken { token }))` runs the full sign-in: it calls `loginWithToken`, then fetches the add-on collection and the whole library, and emits `UserAuthenticated`. Source: core `src/types/api/request.rs:159,211-213`, `src/models/ctx/ctx.rs:113-116,311-380`.
  - `Ctx(PullUserFromAPI { token: Some(key) })` fetches the user with that key and, because a token was passed, stores `Auth { key, user }` in the profile. It does not fetch add-ons or the library. Source: core `src/runtime/msg/action.rs:83-90`, `src/models/ctx/update_profile.rs:51-67,390-415,475-496`.
- Email and password sign-in (already working in the prototype) stays available as a fallback through the same `Authenticate` action.

### Continue Watching

- `ContinueWatchingPreview { items: Vec<Item> }`, where `Item` is a `LibraryItem` plus `notifications: usize`. Source: core `src/models/continue_watching_preview.rs:17-31`.
- It is built at start-up with `ContinueWatchingPreview::new(&library, &notifications)` and rebuilds itself on `LibraryChanged(true)` and `NotificationsChanged`. It handles no host action, not even `Load` or `Unload`. Source: core `src/models/continue_watching_preview.rs:33-54`.
- An item is included when it is in progress or has a new-episode notification, and is not live. Sorted by newest notification video or modification time, capped at `CATALOG_PREVIEW_SIZE` (100). Source: core `src/models/continue_watching_preview.rs:61-123`, `src/constants.rs:33`.
- "In progress" means: type is not `other`, not removed (or is temporary), and `state.time_offset > 0`. Source: core `src/types/library/library_item.rs:55-59`.
- Progress percentage is `time_offset / duration`. Source: core `src/types/library/library_item.rs:63-69`.
- A full Continue Watching screen with paging and sorting is `LibraryWithFilters<ContinueWatchingFilter>`. Source: core `src/models/library_with_filters.rs:29-42`; used as `continue_watching` in core `stremio-core-web/src/model/model.rs:51`.
- New-episode notifications only fill in if the host dispatches `Ctx(PullNotifications)`. Source: core `src/runtime/msg/action.rs:94-101`. The web client does this at start-up and on focus (web `src/App/App.js:142-147`).

### Library

- `LibraryWithFilters<F>` exposes `selected`, `selectable { types, sorts, next_page }` and `catalog: Vec<LibraryItem>`. Source: core `src/models/library_with_filters.rs:138-153`.
- The request is `{ type: Option<String>, sort, page }`; sorts are last watched, name, name reversed, times watched, watched, not watched. Source: core `src/models/library_with_filters.rs:53-64,96-112`.
- `LoadNextPage` re-selects using the request held in `selectable.next_page`. Source: core `src/models/library_with_filters.rs:210-235`.
- `LibraryByType<F>` exposes `catalogs: Vec<Vec<Vec<LibraryItem>>>` (a row per type, pages of 100) and takes `LoadNextPage(row_index)`. Source: core `src/models/library_by_type.rs:33-45,87-112`, `src/constants.rs:32`.
- Both rebuild on `LibraryChanged`. Neither makes a network request. Source: core `src/models/library_with_filters.rs:236-250`, `src/models/library_by_type.rs:113-118`.
- The web host uses `LibraryWithFilters` only; the kotlin host (Android TV) has both. Source: core `stremio-core-web/src/model/model.rs:50-51`; kotlin `.../model/model.rs:40-42`.
- The library reaches the device at sign-in (full fetch, core `src/models/ctx/ctx.rs:347-367`) and afterwards only when the host dispatches `Ctx(SyncLibraryWithAPI)` (core `src/models/ctx/update_library.rs:169-170,491-544`). The web client dispatches it at start-up and on every window focus, together with `PullAddonsFromAPI` and `PullUserFromAPI` (web `src/App/App.js:121-151`).

### Home board and add-on catalogues

- `CatalogsWithExtra { selected, catalogs }`. Source: core `src/models/catalogs_with_extra.rs:15-30`.
- `Load` plans one request per matching catalogue of every installed add-on but sends none: every row starts with `content: None`. Source: core `src/models/catalogs_with_extra.rs:35-38,165-225` (the `range` argument is `None` on load, and only an index inside a range gets `Loading` and an effect, lines 189-216).
- `LoadRange(Range<usize>)` is what triggers the requests, for the rows in that index range. The range is treated as inclusive at both ends. Source: core `src/models/catalogs_with_extra.rs:61-68,190`. The web client dispatches it as rows become visible (web `src/routes/Board/useBoard.js:20`).
- `LoadNextPage(row)` appends a page using the `skip` extra, only if the add-on's manifest declares `skip` for that catalogue. Source: core `src/models/catalogs_with_extra.rs:69-138`.
- Rows are refreshed when the profile's add-ons change. Source: core `src/models/catalogs_with_extra.rs:150-152`.
- `CatalogWithFilters<MetaItemPreview>` is the single-catalogue browser ("Discover"). It exposes `selected`, `catalog` and `selectable { types, catalogs, extra, next_page }`, where every option carries the `ResourceRequest` that selects it. Source: core `src/models/catalog_with_filters.rs:69-134`.
- `Load(CatalogWithFilters(None))` selects a default; `LoadNextPage` uses `selectable.next_page`. Source: core `src/models/catalog_with_filters.rs:158-219`. Already exercised by the prototype (prototype `src/main.rs:250`).
- A catalogue item is a `MetaItemPreview`; a failed or empty page is visible as the page's `Loadable` state.

### Search

- Search is the same `CatalogsWithExtra` model with an extra named `search`. Source: core `src/models/catalogs_with_extra.rs:39-53`, `src/constants.rs:21`.
- When a `search` extra is present, the query is written to `ctx.search_history` and persisted. Source: core `src/models/catalogs_with_extra.rs:44-48`, `src/models/ctx/update_search_history.rs:25-41`.
- Like the board, search results load only after `LoadRange`. The web client does the same (web `src/routes/Search/useSearch.js:58`).
- `LocalSearch` is an optional suggestion list. `Load(LocalSearch)` downloads a feed of popular titles from Cinemeta; `Search(Search { search_query, max_results })` filters it locally into `search_results`. It never asks the user's add-ons. Source: core `src/models/local_search.rs:71-81,98-118,172-202`. The web client uses it for the search bar's dropdown with a 250 ms debounce (web `src/components/NavBar/HorizontalNavBar/SearchBar/SearchBar.js:88`).

### Title page with streams

- `MetaDetails` exposes `selected`, `meta_items`, `meta_streams`, `streams`, `last_used_stream`, `library_item`, `rating_info` and `watched`. Source: core `src/models/meta_details.rs:52-71`.
- `Selected { meta_path, stream_path, guess_stream }`. With `stream_path: Some(..)` it asks every add-on that serves streams for that video. Source: core `src/models/meta_details.rs:41-50,895-915`.
- With `stream_path: None, guess_stream: true` it waits for the meta item and fills in the stream path itself, but only when the item has a default video id or has no videos (a film). For a series without a default video it does not pick an episode. Source: core `src/models/meta_details.rs:603-680`.
- `streams` is one `ResourceLoadable<Vec<Stream>>` per add-on, so the page can show add-ons arriving one at a time and which ones failed.
- `last_used_stream` finds, among the loaded streams, the one matching what was last played for this title or the previous episodes, by equality and then by `bingeGroup`. Source: core `src/models/meta_details.rs:917-992`. This is an input to the automatic stream pick, not a replacement for it.
- Loading the page also pulls that one library item from the API if signed in. Source: core `src/models/meta_details.rs:107,586-601`.
- Watched marking for a film, an episode or a season is in the model. Source: core `src/runtime/msg/action.rs:157-170`, `src/models/meta_details.rs:146-242`.
- Already exercised by the prototype with a three-field model (prototype `src/model.rs:20-26`, `src/main.rs:371`).

### Player

- `Load(Player(Selected { stream, stream_request, meta_request, subtitles_path }))`. Source: core `src/models/player.rs:86-94,162`.
- Progress tracking needs both optional requests. `library_item` is only set when `meta_request` is present (core `src/models/player.rs:1473-1507`), and `TimeChanged` only acts when `stream_request` and `library_item` are both present (core `src/models/player.rs:635-650`). A host that loads the player with a bare stream gets playback and no progress.
- The web client builds the three requests from the title's type, id, video id and the two add-on base URLs. Source: web `src/routes/Player/usePlayer.js:39-82`.
- **Resume position.** The host reads it from `player.library_item.state.time_offset`, and uses it only when `state.video_id` equals the video being played; otherwise it starts at 0. Core does not expose a ready "start at" value. Source: web `src/routes/Player/Player.js:547-553`.
- **Start of playback.** `PausedChanged { paused: false }` marks the session as loaded, emits `PlayerPlaying`, and pushes the library item. Without it the model never counts as loaded. Source: core `src/models/player.rs:771-820`.
- **Time updates.** `TimeChanged { time, duration, device }` updates `time_offset`, `duration`, `time_watched` and `last_watched`. Time must only move forward between calls; a backward `TimeChanged` is ignored for the offset. Source: core `src/models/player.rs:635-686`, `src/runtime/msg/action.rs:271-280`.
- **Seeking.** `Seek { time, duration, device }` sets `time_offset` directly without adding watch time. The host must send `Seek` for seeks and `TimeChanged` for normal playback, and must not send `TimeChanged` while a seek is in progress. Source: core `src/models/player.rs:545-633`, `src/runtime/msg/action.rs:259-270`; web `src/routes/Player/Player.js:576-578`.
- **Units.** Milliseconds. `ExternalPlayerProgressChanged` documents `time` as milliseconds (core `src/runtime/msg/action.rs:171-175`) and it writes the same `time_offset` field; the seek cut-off constant is `600_000` (core `src/constants.rs:73`).
- **Progress pushed to the library and to Stremio.** The player emits the internal `UpdateLibraryItem` message: at most once every 180 seconds during `TimeChanged` and `Seek` (core `src/models/player.rs:50,1258-1274`), on every `PausedChanged` (lines 811-817), on `NextVideo` (lines 836-849), and on `Unload` (lines 425-438). `Ctx` handles that message by writing the item to storage and, when signed in, sending a `datastorePut` to the API. Source: core `src/models/ctx/update_library.rs:214-241,447-470`, `src/types/api/request.rs:317`.
- So the host makes no API call for progress. It must dispatch `Unload` at the player field when leaving the player, or the last position (up to 180 seconds) is lost.
- **Watched.** When watched time passes 70% of the duration the item is flagged watched and a "watched" rating call is sent. Source: core `src/models/player.rs:688-731,1969-1990`, `src/constants.rs:46`.
- **End of a video.** On `Unload` or the next `Load`, if the position is past 90% of the duration the offset resets to 0 and the library item advances to the next video. Source: core `src/models/player.rs:1276-1314`, `src/constants.rs:47`.
- **Next episode.** `next_video` is computed from the meta item. Core then requests the next video's streams from the same add-on (`next_streams`) and sets `next_stream` to the first one whose `bingeGroup` equals the current stream's. Source: core `src/models/player.rs:1341-1441`, `src/types/resource/stream.rs:141-149`.
- `NextVideo` and `Ended` only record state and emit `PlayerNextVideo` and `PlayerEnded`. They do not load anything: the host must dispatch a new `Load(Player(..))` for the next video. Source: core `src/models/player.rs:822-878` (comment at line 851: "Load will actually take care of loading the next video"); web `src/routes/Player/Player.js:250-262`.
- **Subtitles from add-ons.** With `subtitles_path` set, core asks every add-on that serves subtitles, adding `videoHash`, `videoSize` and `filename` extras taken from the stream's behaviour hints or from `VideoParamsChanged`. Source: core `src/models/player.rs:1575-1644`.
- No subtitle request is made until at least one of hash, size, filename or a `VideoParamsChanged` call is available. Source: core `src/models/player.rs:1615-1621`. A host that cannot compute the hash should still dispatch `VideoParamsChanged` with the size and filename it knows.
- Results arrive as `subtitles: Vec<ResourceLoadable<Vec<Subtitles>>>`, each entry `{ id, lang, url, label, fonts }`. Core gives URLs only; the host downloads, parses and renders the files. Source: core `src/models/player.rs:110`, `src/types/resource/subtitles.rs:9-21`.
- Streams can also carry their own `subtitles` list. Source: core `src/types/resource/stream.rs:68-84`.
- **Per-stream settings.** `StreamStateChanged { state }` stores the chosen subtitle track, subtitle delay, size and offset, audio track, audio delay, playback speed and video scale for the title in the streams bucket, and `stream_state` gives them back next time. Source: core `src/types/streams/streams_item.rs:29-51`, `src/models/player.rs:510-523,988-1001,1316-1339`, `src/models/ctx/update_streams.rs:63-75`.
- **Intro and outro skipping** is requested from Stremio's API only for accounts with active premium, a series, and an OpenSubtitles hash. Source: core `src/models/player.rs:1840-1921`. A host without the hash never triggers it.
- **Add-on player events.** Start, pause and stop events are sent to add-ons that declare the `player` resource. Source: core `src/models/player.rs:1941-1967`. No host work.

## Bullet 2: what the host implements beyond fetch, storage and a task runner

### Sign-in by link code

- A timer. Core reads the link once per `ReadData`; nothing in core repeats it. Source: core `src/models/link.rs:56-64`.
- Drawing the code and a QR. The response carries a `qrcode` string and a `link` string (core `src/types/api/response.rs:89-94`); what the `qrcode` string contains was not checked against a live response.
- The hand-off from `LinkAuthKey` to a signed-in `Ctx`, by dispatching one of the two actions listed under "Sign in on a TV".
- Telling "not used yet" from "expired". Any failed read lands in `data` as `Loadable::Err(LinkError)` (core `src/models/link.rs:84-108`), and a later `ReadData` sets it back to loading. Which error the service returns in each case was not established, so the host needs its own time limit after which it dispatches `Load(Link)` for a fresh code.

### Start-up and background sync

- Reading the profile and buckets from storage and passing them to `Ctx::new`. The web host reads eight keys: profile, recent library, library, streams, streaming-server URLs, notifications, search history, dismissed events. Source: core `stremio-core-web/src/stremio_core_web.rs:113-161`.
- The prototype reads only the profile and the two library keys and starts the other buckets empty (prototype `src/model.rs:31-56`). The streams bucket must be read too, or `last_used_stream` and `stream_state` forget everything on restart.
- Dispatching `PullAddonsFromAPI`, `PullUserFromAPI {}`, `SyncLibraryWithAPI` and `PullNotifications` at start-up and when the app returns to the foreground. Source: web `src/App/App.js:121-151`.
- Storage schema migration: the web host calls `migrate_storage_schema` in its `init` before reading. The trait provides it. Source: core `src/runtime/env.rs:174-200`.

### Player reporting

- The action sequence under "Player" above: `Load`, `PausedChanged(false)` when playback actually starts, `TimeChanged` on the position clock, `Seek` on seeks, `PausedChanged` on pause and resume, `Ended`, and `Unload` on exit.
- The `device` string in `TimeChanged` and `Seek` is only copied into analytics context. Source: core `src/models/player.rs:587-589,749-751`. The web client passes its video implementation's name.

### Stream choice and uncached streams

- Core lists streams and offers `last_used_stream` and `next_stream`. It has no notion of cached versus uncached, of codecs, or of what the television can decode. The automatic pick, the markings, and the uncached "downloading" state are all host code (the prototype's `src/pick.rs`, `src/hints.rs` and `src/probe.rs`, 474 lines).
- Core never opens a stream URL itself. `Player` only stores the converted URL in `player.stream`. Source: core `src/models/player.rs:1552-1573`. So "never open an uncached link unless the user chose it" is entirely in the host's hands.

### Anything that assumes Stremio's streaming server

- `Player` reads one thing: `ctx.profile.settings.streaming_server_url`, passed to `Stream::convert`. Source: core `src/models/player.rs:256-260,1552-1573`. The default is `http://127.0.0.1:11470`. Source: core `src/constants.rs:92-93`, `src/types/profile/settings.rs:76`.
- A `Url` stream whose scheme is not `magnet`, `ftp` or `ftps` and which has no proxy headers is returned unchanged. Source: core `src/types/resource/stream.rs:454-497` (the fall-through at line 493) and `186-200` for the FTP rewrite.
- A `Url` stream that sets `behaviorHints.proxyHeaders` is rewritten to `<streaming_server_url>/proxy/...`, because `Player` always passes `Some(url)`. Source: core `src/types/resource/stream.rs:459-492`. On a television with no streaming server that rewritten URL points at nothing. The host must read `player.selected.stream` (the original) for such streams and apply the request headers itself.
- Torrent, YouTube, archive (rar, zip, 7zip, tar, tgz) and Usenet sources are all converted to streaming-server URLs. Source: core `src/types/resource/stream.rs:238-453,503-580`. These are the peer-to-peer and related cases already out of scope.
- The OpenSubtitles hash in `VideoParams` is "usually retrieved from a streaming server endpoint". Source: core `src/models/player.rs:78-84`. Without it, subtitle add-ons are asked by filename and size only, and intro skipping never runs.
- `Env::analytics_context` takes a `&StreamingServer` argument. Source: core `src/runtime/env.rs:158-162`. This is a type in a signature that core never calls from the models read here; the prototype implements it as a stub (prototype `src/env.rs:236`).
- The web client waits for the streaming server's settings to finish loading before starting playback. Source: web `src/routes/Player/Player.js:540`. That gate is the client's, not core's.

## Bullet 3: which models can be left out

- The `Model` derive requires exactly one thing: a field named `ctx`. Source: core `stremio-derive/src/lib.rs:21-27`.
- For each message it updates `ctx` first with `Update::update`, then every other field with `UpdateWithCtx::update(&mut field, msg, &self.ctx)`. Source: core `stremio-derive/src/lib.rs:83-112`.
- No field is ever handed another non-`ctx` field. The trait signature is `fn update(&mut self, msg: &Msg, ctx: &Ctx)`. Source: core `src/runtime/update.rs:22-24`. Models interact only through `Ctx` and through internal messages that are broadcast to all fields (core `src/runtime/runtime.rs:109-118`).
- So any subset of models compiles and runs. The prototype's three-field model is the proof (prototype `src/model.rs:20-26`).
- `Player` does not reference the `StreamingServer` model. The only matches for "streaming_server" in `player.rs` are the profile setting at line 259 and the parameter of `stream_update` at lines 1552-1562. Verified by search over the file.
- `Ctx` does not contain a `StreamingServer`. It holds `streaming_server_urls: ServerUrlsBucket`, a stored list of URLs that only changes on `AddServerUrl`, `DeleteServerUrl` and sign-in. Source: core `src/models/ctx/ctx.rs:49-78`, `src/models/ctx/update_streaming_server_urls.rs:13-42`. `Ctx::new` needs the bucket as an argument, which is one line (prototype `src/model.rs:46`).
- Including `StreamingServer` has a cost: `StreamingServer::new` immediately issues four requests to the configured server URL (settings, playback devices, network info, device info). Source: core `src/models/streaming_server.rs:73-79`. On a television these would all fail against `127.0.0.1:11470`.
- Both official hosts do include it and pass it into their serialisers to build deep links and stream URLs. Source: core `stremio-core-web/src/model/model.rs:62,133-207`; kotlin `.../model/model.rs:50`. That use is in host glue, not in core's models.

Suggested first-version model, as a consequence of the above:

| Field | Type | Screen |
|---|---|---|
| `ctx` | `Ctx` | all |
| `auth_link` | `Link<LinkAuthKey>` | sign in |
| `continue_watching_preview` | `ContinueWatchingPreview` | home row |
| `board` | `CatalogsWithExtra` | home |
| `discover` | `CatalogWithFilters<MetaItemPreview>` | one catalogue |
| `library` | `LibraryWithFilters<NotRemovedFilter>` or `LibraryByType<NotRemovedFilter>` | library |
| `search` | `CatalogsWithExtra` | search |
| `meta_details` | `MetaDetails` | title page |
| `player` | `Player` | player |

Left out with no effect on the fields above: `StreamingServer`, `LocalSearch`, `Calendar`, `LiveTvGuide`, `LiveTvContinueWatching`, `DataExport`, `AddonDetails`, `InstalledAddonsWithFilters`, `CatalogWithFilters<Descriptor>`. The last three are add-on management, which the map puts out of scope.

## Bullet 4: rough size of the host layer

Counted with `wc -l` over the checkouts named under "Sources".

| Host | What was counted | Lines |
|---|---|---|
| `stremio-core-web` | all Rust under `src/` | 4,232 |
| | of which `model/serialize_*.rs` (model to JavaScript objects) | 2,741 |
| | of which `env.rs` (fetch, storage, executors, analytics) | 623 |
| | of which `stremio_core_web.rs` (start-up, dispatch, get state) | 359 |
| | of which `model/model.rs` (the model struct) | 209 |
| | JavaScript bridge (`bridge.js`, `worker.js`) | 71 |
| `stremio-core-kotlin` | Rust in the `stremio-core-kotlin` crate (env, JNI, model) | 1,640 |
| | Rust in the `stremio-core-protobuf` crate (model to Protobuf) | 4,422 |
| | `.proto` definitions | 1,770 |
| | Kotlin | 113 |
| prototype | all of `src/` | 1,420 |
| | of which `env.rs` | 250 |
| | of which `model.rs` | 57 |
| core itself | Rust under `src/`, excluding `unit_tests` | 22,969 |

Reading the counts:

- In both official hosts roughly two thirds of the glue translates Rust structs into another language's objects (2,741 of 4,232 lines; 4,422 of 6,062 lines). A Rust interface reads the structs directly and needs none of that translation.
- The translation layer does contain some real derivation that a Rust host still needs in some form: per-video `watched`, `progress` and `upcoming` flags, the player title, the add-on a stream came from. Source: core `stremio-core-web/src/model/serialize_player.rs:56-64,108-125`.
- The parts that carry over are the environment (250 lines in the prototype, 623 in the web host, 333 plus 287 for fetch and storage in the kotlin host), start-up (about 100 lines of the web host's 359), and the model struct (about 100 lines for nine fields).

**Estimate (not a measurement):** 1,000 to 2,000 lines of Rust for the host layer of the first version, covering the environment, start-up and sync, the model struct, the link-code poller, the player reporter, and per-screen view adapters. It excludes drawing, navigation, the video pipeline, subtitle rendering and stream picking. The low end assumes the prototype's `env.rs` and `model.rs` carry over nearly as they are; the high end assumes view adapters about half the size of the web host's serialisers.

## Not determined

- **What the browser side of the link flow does.** The page served at `https://link.stremio.com/<CODE>` is not in the link-ui repository, which holds only the code-entry page and the expiry page. Whether it signs the person in on the phone and writes the key, and what else it can write, was not established.
- **Which follow-up action a link key is meant for.** `LoginWithToken` and `PullUserFromAPI { token }` both accept a key in core, and no public client was found that uses `Link`: the web client at the commit read does not reference `auth_link` at all, and the Android TV app's source is not public. Whether the API's `loginWithToken` accepts a key issued by the link service needs one live test.
- **Link code lifetime and the expected polling interval.** Neither is in core or link-ui. The link-ui pages imply codes are 4 characters and expire.
- **What the `qrcode` field contains** (an image URL, a data URL or raw content). Only its type, `String`, was read.
- **What a link read returns before the code is used, and after it expires.** Core maps any failure to `LinkError`; the service's actual responses were not observed.
- **How many add-ons set `proxyHeaders` on HTTPS streams.** Comet's streams in the prototype's measurements were plain direct links, but this was not counted for this ticket.
- **Whether subtitle add-ons return useful results without the OpenSubtitles hash**, by filename and size alone. That needs a live request.
- **Android TV specifics.** The kotlin host's `Player` handling and Protobuf player messages were not read line by line; only its model struct, environment and line counts were. It is also pinned to core's `development` branch as of March 2026, older than the commit read here, which is why it has no live-TV fields.
- **Main-thread cost of the extra models on a television.** Adding six fields means every internal message visits six more `update` functions. Not measured; this belongs with the map's "Responsiveness on slow sets" item.
- **`Runtime`'s bounds on a non-`Send` environment.** `Runtime::new` requires `E: Env + Send` and `M: Send + Sync` (core `src/runtime/runtime.rs:34-38`). The prototype already satisfies this, so it was taken as established and not re-examined for the larger model.
