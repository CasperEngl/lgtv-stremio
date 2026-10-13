# What the hosted Comet instance answers for an uncached stream

A check for [Check the hosted Comet instance's status clips against the size table](https://github.com/CasperEngl/lgtv-stremio/issues/26), run on 2026-10-13 (UTC) against the account's own add-on, `comet.elfhosted.com`, with a real Real-Debrid account. One uncached stream, chosen by the account's owner, was opened. Redirect-following was off for every request to it.

It tests the predictions in `docs/research/comet-uncached-streams.md` (branch `research/comet-uncached`), which were read from Comet's source at `f56677f` and never run against a server.

## Answer

The size table cannot be trusted on this instance, because the instance serves no status clip at the link's own address. While the download is in progress the link answers `302` with an empty body, to a status-video service of the host's own, `slate.elfhosted.com`. When the file is ready the link also answers `302` with an empty body, to a `download.real-debrid.com` host. So on this instance "the link redirects" does not mean "ready"; where it redirects to does.

The status video behind the first redirect is 3,207,558 bytes, 120 seconds, 1280x720, with an audio track. The table expects 410 to 434 kB, 8.0 seconds and no audio.

The download of a 526.6 MB file listed with 3 seeders took between 23 min 24 s and 25 min 25 s.

## What was opened

| | |
|---|---|
| Title | Night of the Living Dead (1968), `tt0063350` |
| Stream | `Night of the Living Dead (1968) English.mp4`, 526.6 MB, listed with 3 seeders |
| Torrent hash | `4d5f74f5babcd7bf62b75acd8182370ca495dfa5` |
| Marking before | `[RD⬇️] Comet unknown` (uncached) |
| Instance | `comet.elfhosted.com`, manifest version `2.0.0`, name "Comet \| ElfHosted \| RD" |

Requests made to the picked link: 23 in all. 21 `GET`s (one first open, ten 30 seconds apart, ten 2 minutes apart), then one `HEAD` and one `GET` with `Range: bytes=0-0` once it was ready. The redirect to Real-Debrid was never followed, so the file itself was not fetched. The redirect to the slate service was followed once, by hand, in two requests.

## Recorded answers

Every figure in this section is measured, from `curl`'s own output, unless it says derived.

### While the download was in progress (opens 1 to 20)

```
HTTP/2 302
content-length: 0
location: https://slate.elfhosted.com/slate.m3u8?preset=default&w=1280&h=720&title=Not+ready+yet&body=<text>&ts=<unix time>&sig=<scrubbed>&format=auto
cache-control: no-store, no-cache, must-revalidate, max-age=0
expires: 0
pragma: no-cache
server: cloudflare
cf-cache-status: DYNAMIC
```

- No `Content-Type`, no `ETag`, no `Accept-Ranges`. Body 0 bytes.
- The `body` parameter's text was the same on all 20: "This title isn't cached on your debrid service yet. It's being prepared — wait a short while and try again." followed by a blank line and `Ref: MEDIA_NOT_CACHED_YET`. That reference is the status key Comet's source uses for the downloading clip.
- `ts` is the time of the answer and `sig` a signature over the parameters, so the `Location` differs on every open.
- The first open took 4.33 s to answer. The other 19 took 0.23 to 0.80 s (median 0.27 s).
- The three cache headers are the ones the source findings predicted for a status clip. They are on the redirect instead.

### The slate service (followed once, two requests)

| Request | Answer |
|---|---|
| `GET slate.elfhosted.com/slate.m3u8?…` | `302`, 0 bytes, `cache-control: no-store`, to `/cache/<64 hex characters>/slate.mp4?…` on the same host |
| `GET slate.elfhosted.com/cache/…/slate.mp4?…` | `200`, `content-type: video/mp4`, `content-length: 3207558`, `accept-ranges: bytes`, `cache-control: public, max-age=3600, immutable`, `last-modified` set, no `ETag` |

- The video: 3,207,558 bytes, 120.0 s, H.264 1280x720 at 24 frames a second, plus an AAC audio track (read with `ffprobe`). SHA-256 `1543ef15…baf63a`.
- The request sent `curl`'s default headers. The address ends in `.m3u8` and carries `format=auto`, so a client that announces HLS support may be given a playlist instead of an MP4. Not tested.

### Once ready (opens 21 to 23)

```
HTTP/2 302
content-length: 0
location: https://<host>.download.real-debrid.com/<scrubbed>
server: cloudflare
cf-cache-status: DYNAMIC
```

- No cache headers at all, unlike the in-progress answer. No `Content-Type`, no `ETag`, no `Accept-Ranges`. Body 0 bytes.
- The `Location` has three path segments, ends in `.mp4` and has no query string.
- `HEAD` is answered the same way as `GET` (`302`, same `Location`). The source findings guessed it would be rejected.
- `Range: bytes=0-0` is answered the same way too. The instance does not proxy: it redirects, so range support is Real-Debrid's to answer, and that was not requested.
- All three `Location`s were identical, 11 seconds apart, as the stored-link behaviour in the source findings predicts.
- These three took 0.34 s, 0.06 s and 0.06 s.

## Timing

| Event | Time (UTC) |
|---|---|
| First open sent | 22:39:28 |
| Last open answered with the slate (open 20) | 23:02:52 |
| First open answered with the file (open 21) | 23:04:53 |

- Download time: more than 23 min 24 s and at most 25 min 25 s. Derived: 23:02:52 − 22:39:28 and 23:04:53 − 22:39:28. The 2-minute spacing of the later opens is the width of that window.
- Average rate over that time: about 0.35 to 0.38 MB/s. Derived: 526.6 MB ÷ 1,525 s and ÷ 1,404 s.

## Did re-opening at 30 seconds behave as predicted?

Partly.

- Predicted and seen: every re-open while downloading gave the same "not ready" answer, quickly, and the answer changed by itself to the file once the download finished. Nothing else was needed to trigger the change.
- Predicted and seen: the first open is slower than the rest (4.33 s against a median of 0.27 s). The predicted worst case of about 25 seconds did not occur.
- Predicted, not seen: a `200` answer with a 433,923-byte clip in its body. The answer was a `302` with no body.
- Not checked: whether each re-open cost Real-Debrid API calls, and what a failed or refused download answers. Only the `MEDIA_NOT_CACHED_YET` reference was ever seen.

## The stream list's marking

The marking did not flip while it was watched. The title's stream list was re-fetched before each of opens 2 to 21 and then once a minute for 30 more polls; fetching a list opens nothing.

- Before the first open, at every poll during the download, and at every poll after it: `[RD⬇️] Comet unknown`, the uncached mark. Measured.
- Last poll: 23:34:25 UTC, 29 min 32 s after the first answer that redirected to the file (derived: 23:34:25 − 23:04:53). Still uncached, with the stream in the same place in the list and the title's count of cached streams unchanged at 6 of 29.
- So the link redirected to the finished file for at least half an hour while the list still called the stream uncached. When it flips, if it does, was not observed.

This agrees with the source findings, which say the marking is remembered and not checked live, and with the decision that the television keeps its own record of the downloads it started instead of relying on the list.

## What this means for the decision it serves

[What happens when the user picks an uncached stream?](https://github.com/CasperEngl/lgtv-stremio/issues/9) decided that clips are told apart by size against the 55-entry table, that the app plays "when the probe meets something that is not a status clip", and that the wait ends after 30 minutes.

- **The size rule does not work on this instance.** There is no body at the link's address to measure. A probe that follows redirects lands on a 3.2 MB, 2-minute video with audio, which matches no entry in the table and does not look like a clip by size or length. The decided fallback, "unknown clip: keep waiting", needs something to recognise a clip by, and here size gives it nothing.
- **What does tell the states apart here**, with redirect-following off: the host in `Location` (`slate.elfhosted.com` against `*.download.real-debrid.com`), the `Ref:` line inside the `body` parameter, and the no-store cache headers, present only on the not-ready answer. The `Ref:` value is Comet's own status key, so it should also separate a refusal from a download in progress. Only one value was observed.
- **The 30-minute wait is tight.** One small file with three seeders needed 23 to 25 minutes. One sample is not a distribution, but it is the only measured figure there is, and it sits at about 80% of the limit.

## Not determined

- What the instance answers for a refused or failed download. The `Ref:` values other than `MEDIA_NOT_CACHED_YET` are assumed from Comet's source, not seen.
- Whether the slate service answers a television's player with an HLS playlist.
- Which code produces the slate redirect. Upstream Comet's newest commit is still `f56677f` and contains no such code. ElfHosted's public build files (`elfhosted/containers`) build Comet from upstream's latest release, list a separate `slate` app whose source is private, and carry a patch for a different add-on (AIOStreams) that replaces bundled error videos with signed redirects to "the slate error-video service". That Comet is patched the same way is inferred.
- Whether another hosted or self-hosted Comet behaves like upstream (a `200` clip) or like this one.
- How long Real-Debrid keeps the finished torrent.
- How download time varies with size and seeders. This is one sample.

## How to reproduce

The helper scripts are in `docs/research/hosted-status-clips/`. They read the add-on's address from the command-line prototype's saved session (`$XDG_DATA_HOME/lgtv-stremio/profile.json`, written by `prototype`'s `login`), keep raw answers in `/tmp/hsc/run/` and print only scrubbed lines. The stream's hash and the title are fixed at the top of each script.

1. Save the title's stream list to `/tmp/hsc/tt0063350.json` with a `GET` of `<add-on address>/stream/movie/tt0063350.json`. This opens nothing.
2. `open.sh open-01` opens the picked link once, redirects off. **This queues the download on the account.**
3. `watch.sh <count> <interval> <first number>` re-opens it on a timer, re-fetching the stream list before each open, and stops at the first answer that is not the `MEDIA_NOT_CACHED_YET` slate redirect.
4. `open.sh open-22-head -I` and `open.sh open-23-range -H 'Range: bytes=0-0'` for the ready answer.
5. `marking.sh <count> <interval>` polls the stream list until the stream carries the cached mark.

`log.txt` in the same folder is the scripts' output for this run, with the Real-Debrid addresses, the slate signature and Cloudflare's reporting headers removed. The add-on address, which carries the debrid token, was never written to it.

The stream is now on the account, so a second run on the same stream would not see the in-progress answer. Use a different uncached stream.
