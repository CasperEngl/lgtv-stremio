# What the hosted Comet instance answers for a refused debrid key

A check for [Observe a refused or failed download on the hosted Comet instance and record the answer](https://github.com/CasperEngl/lgtv-stremio/issues/62), run on 2026-10-13 (UTC) against `comet.elfhosted.com`. It tests the rule decided in [How does the app tell not ready, refused and ready apart when the link redirects?](https://github.com/CasperEngl/lgtv-stremio/issues/57).

One refusal was provoked: a debrid key that Real-Debrid does not accept. Nothing was added to any debrid account. A refusal of a download on a valid key (a dead torrent, an infringing file, the active-download limit) was not observed.

## Answer

**The observed refusal carries no `Ref:` key and no no-store cache headers.** The link answers `302` with an empty body to the bare address `https://comet.feels.legal/`, another host's Comet home page, both times it was opened. Read by the rule, that is step 4, "a redirect with neither is ready". The size guard does not apply either, because the entry lists no size.

The same refusal is visible before any open. With a refused key the stream list holds one entry in place of the title's 29 streams, named `[❌] realdebrid` and described "realdebrid: Invalid API key." The rule has no step for an entry like that.

So the rule's assumption that a refusal carries a key other than `MEDIA_NOT_CACHED_YET` is false for this kind of refusal. Whether it holds for a refused download on a valid key is still not determined.

## What was done

| | |
|---|---|
| Title | Night of the Living Dead (1968), `tt0063350` |
| Instance | `comet.elfhosted.com`, the account's own add-on |
| Key | the saved add-on configuration with its debrid key replaced by a made-up one of the same length (52 characters) |
| Opened | the one entry of the list fetched with that key, twice, 30 seconds apart, redirect-following off |
| Left on the account | nothing: the link was sealed for a key Real-Debrid rejects |

Requests made: three stream lists (one with the saved key, two with the made-up key; a list opens nothing), two opens of the error entry's link, and two requests to the redirect's target (its home page and the page that redirects to). No Real-Debrid address was requested.

## Why a made-up key and not a refused download

Everything in this section is measured locally from the saved list unless it says derived.

- The hosted instance seals its playback links. An ordinary stream's link is `/playback/` followed by about 26 path pieces of 64 characters, which decode from base64 to about 1,200 bytes of high-entropy data (7.84 bits per byte). The torrent hash is not in it as text or as bytes, and two links from the same list share no prefix.
- So a link cannot be edited: a made-up hash, a wrong episode number or a torrent with no video file cannot be requested. Upstream Comet's source at `f56677f` builds a readable path; the hosted instance does not.
- The add-on's own address is readable: one path piece of base64 JSON, with the debrid key in `debridServices[].apiKey`. A list can therefore be asked for with a different key, and the instance seals the links in the answer for that key.

The refusals considered, with which status key each should carry (derived from Comet's source at `f56677f` and StremThru at `b66650a`, see `comet-uncached-streams.md` on branch `research/comet-uncached`, section 5):

| Way | Expected key | Left on the account | Done |
|---|---|---|---|
| A key Real-Debrid rejects | `UNAUTHORIZED` | nothing | yes |
| An uncached stream listed with 0 seeders | `STORE_MAGNET_INVALID` if Real-Debrid fails it, otherwise `MEDIA_NOT_CACHED_YET` | one stalled torrent, deleted and re-added on every further open once failed | no |
| Filling the active-download limit | `STORE_LIMIT_EXCEEDED` | dozens of downloads | no |
| An infringing file, a torrent too big | `UNAVAILABLE_FOR_LEGAL_REASONS`, `UNPROCESSABLE_ENTITY` | nothing | no: which torrent is refused cannot be known before opening it |

## Recorded answers

Every figure in this section is measured, from `curl`'s own output and `jq` over the saved answers.

### The stream list with a refused key

```
GET <add-on address with the made-up key>/stream/movie/tt0063350.json
200, 419 bytes, one entry
name:        [❌] realdebrid
description: realdebrid: Invalid API key.
             Please check your configuration.
```

- The entry has three fields: `name`, `description` and `url`. It has no `behaviorHints`, so no size, no file name and no binge group.
- Its link is a sealed playback link on `comet.elfhosted.com` with 4 path pieces after `/playback` (64, 64, 64 and 58 characters) and no query.
- A second fetch 83 seconds later gave the same single entry with a different link.
- With the saved key the same title lists 29 streams, 6 cached and 23 uncached.

### The error entry's link (two opens, 30 seconds apart)

```
HTTP/2 302
content-length: 0
location: https://comet.feels.legal/
access-control-allow-origin: *
cf-cache-status: DYNAMIC
server: cloudflare
```

- No `Cache-Control`, no `Pragma`, no `Expires`. No `Content-Type`. Body 0 bytes.
- The `Location` is a bare home page: no path beyond `/`, no query, so no `Ref:` key, no `title`, no `body` and no signature.
- Both opens gave the same answer and the same `Location`. They took 0.061 s and 0.060 s.
- The target is not `slate.elfhosted.com`, the status-video service seen for a download in progress, and not `comet.elfhosted.com` itself.

### The redirect's target

| Request | Answer |
|---|---|
| `GET https://comet.feels.legal/` | `307`, 0 bytes, to `/configure` |
| `GET https://comet.feels.legal/configure` | `200`, `text/html`, 59,327 bytes, `cache-control: public, max-age=86400, stale-while-revalidate=21600`, title "Comet - Stremio's fastest torrent/debrid search add-on." |

So following the link ends on a web page, not a video.

## Read against the rule

| Step of the rule | This answer |
|---|---|
| 1. redirect to a StremThru clip address | no |
| 2. redirect whose address carries a `Ref:` key | no key |
| 3. redirect with the no-store cache headers | none of the three headers |
| 4. redirect with neither: ready | **matches** |
| size guard: target under 20 MB where the list promised ten times that | does not apply, the entry lists no size |

- Derived: the app would call the link ready and hand it to the probe, which would follow two redirects to an HTML page and find no video. What the probe and the pick do with an HTML page was not run. The rule's line "anything that is neither a redirect nor a video goes straight to the failure read-out" is written for the link's own answer, not for a redirect's target.
- Derived: the automatic pick counts error clips by a refusal that arrives as a redirect with a key, or by a probe that finds no audio. This answer is neither by the rule's wording.
- What does tell this refusal apart, measured: the list entry itself (the `[❌]` name, the error text, the missing `behaviorHints`), and the content type of the final target.

## How far this carries

- **Strong** for a refused key: 2 of 2 opens, identical, on the instance the first version is tested against. This is the state an account is in when its debrid key expires or is revoked.
- **Silent** on a refused download with a valid key. The error entry's link is far shorter than an ordinary stream's, so it is probably a fixed pointer made when the list was built, and not the playback path that adds a torrent and reports a status key. Inferred from the link's length; the instance's code is not public.
- Not shown: that a download refusal carries a `Ref:` key. That part of the rule is as unproven as before.

## Not determined

- What the instance answers for a download Real-Debrid refuses or fails on a valid key: a dead torrent, an infringing file, the active-download limit. The only untried way that leaves little behind is an uncached stream with no seeders, and it may only answer "not ready yet".
- Whether the error entry's link answers the same for every kind of list-level error, or only for a refused key.
- Why the target is `comet.feels.legal` and not the instance's own address. Not looked into.
- Whether Real-Debrid was asked at all when the error entry's link was opened. The answer took 0.06 s, against 0.23 to 0.80 s for a link that asks about a download in progress, which suggests not. Inferred.
- What the app's probe does when a redirect's final target is a web page.
- Whether upstream Comet lists a refused key the same way. Not read.

## How to reproduce

The helper scripts are in `docs/research/hosted-refusal/`. They read the add-on's address from the command-line prototype's saved session (`$XDG_DATA_HOME/lgtv-stremio/profile.json`), keep raw answers in `/tmp/hr/run/` and print only scrubbed lines.

1. `list.sh movie tt0063350 /tmp/hr/wrongkey.json --wrong-key` fetches the list with a made-up key. This opens nothing.
2. `open.sh open-01 /tmp/hr/wrongkey.json 0` opens entry 0 once, redirects off. With the made-up key this reaches no account. **With a list fetched on the saved key, the same script queues a download.**
3. Repeat step 2 as `open-02` after 30 seconds.

`log.txt` in the same folder is the scripts' output for this run. The add-on address, the made-up key's configuration and every link's path were never written to it.
