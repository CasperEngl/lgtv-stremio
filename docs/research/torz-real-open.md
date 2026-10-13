# What the hosted StremThru Torz instance answers when a link is opened

Record for [Open one cached and one uncached StremThru Torz stream on the hosted instance and record the answers](https://github.com/CasperEngl/lgtv-stremio/issues/56). It checks, against the hosted instance, what `docs/research/torz-streams.md` (branch `wayfinder/torz-streams`) read from StremThru's source at `b66650a`.

Every fact is tagged **measured** (a command's output, in `torz-real-open/log.txt`), **derived** (worked out, with the arithmetic) or **read** (StremThru's source at `b66650a`). Nothing here was seen by the owner on a screen: every observation is read from output. All times are UTC.

## Answer

The redirect rule decided in [How does the app treat StremThru Torz's streams?](https://github.com/CasperEngl/lgtv-stremio/issues/51) held on every answer seen: a ready link redirected to Real-Debrid, and a link that was not ready redirected to a StremThru clip at `/v0/store/_/static/<name>.mp4`.

The `downloading` clip was never seen. Of the three streams the list marked not cached, two answered the `500` clip on every open and one was already held by Real-Debrid and redirected to the file. So no download was watched, and the download time, the 15 to 40 second first open and the once-a-minute fresh answer stay unmeasured.

## What was done

On 2026-10-13, between 23:48:49 and 23:52:05, on the owner's account, with the title *Night of the Living Dead* (1968, `tt0063350`), a public-domain film. The owner chose every stream from a list; no other stream or playback link was opened, and no redirect was followed.

| Stream | Listed as | File | Opens |
| --- | --- | --- | --- |
| 1, `7def7af5…` | cached | `Night of the Living Dead 1968.mkv`, 2.4 GB | 1 |
| 2, `50b7dafb…` | not cached | `Night.Of.The.Living.Dead.1968.720p.BluRay.x264-[YTS.AM].mp4`, 0.8 GB | 4 |
| 3, `00122841…` | not cached | `Night.of.the.Living.Dead.1968.REMASTERED.REPACK.720p.BluRay.999MB…`, 1.0 GB | 1 |
| 4, `11ea0258…` | not cached | `Night.Of.The.Living.Dead.1968.1080p.BluRay.x264-[YTS.AM].mp4`, 1.6 GB | 1 |

Seven opens in all (derived: 1 + 4 + 1 + 1), each a `GET` with redirect-following off and the body discarded. Streams 3 and 4 and the last open of stream 2 were added by the owner after stream 2 answered the `500` clip.

## The answers

| Open | Started | Answer | Seconds |
| --- | --- | --- | --- |
| Stream 1, first | 23:48:49 | `302` to `131-4.download.real-debrid.com` | 3.38 |
| Stream 2, first | 23:48:53 | `302` to `…/v0/store/_/static/500.mp4` | 3.30 |
| Stream 2, second | 23:49:09 | the same clip address | 0.19 |
| Stream 2, third | 23:50:10 | the same clip address | 1.72 |
| Stream 2, fourth | 23:51:47 | the same clip address | 1.74 |
| Stream 3, first | 23:51:50 | `302` to `128-4.download.real-debrid.com` | 3.38 |
| Stream 4, first | 23:51:53 | `302` to `…/v0/store/_/static/500.mp4` | 3.67 |

All measured.

- **Status line.** `HTTP/2 302` on all seven. Measured.
- **Headers, the same set on all seven.** `content-type: text/html; charset=utf-8`, `location`, `access-control-allow-origin: *`, `request-id`, `cf-cache-status: BYPASS`, `server: cloudflare`, `date`. Measured.
- **Headers that were absent.** No `content-length`, no `cache-control`, no `expires`, no `pragma`, no `etag`. The ready and the not-ready answer carry the same header names, so nothing but `location` tells them apart. Measured.
- **Body.** A short HTML redirect page: 79 bytes for the clip, 121 and 170 bytes for the two file redirects. Measured (`curl`'s byte count; the body was not kept).
- **A ready link redirects to Real-Debrid**, not to the instance's own proxy address. Measured, twice.
- **The clip address** is the instance's own host and exactly `/v0/store/_/static/500.mp4`. Measured, five times.

## Against what was expected

| Expected from source | Seen | Verdict |
| --- | --- | --- |
| Cached stream: `302` to the file | `302` to Real-Debrid in 3.38 s | matches |
| Uncached stream, first open: `302` to `downloading.mp4` after 15 to 40 s | `302` to `500.mp4` after 3.30 s and 3.67 s (two streams) | not seen; a failure was met instead |
| A second open within a minute: the remembered clip address, at once | the same address in 0.19 s, 13 s after the first answer | matches |
| A fresh answer at most once a minute | opens 74 s and 95 s after the previous fresh answer took 1.72 s and 1.74 s, against 0.19 s for the remembered one | consistent, not proved: the answer did not change, so only the time says it was fresh |
| The uncached stream once ready: `302` to the file | not reached: no download was watched | not measured |
| A ready link goes to Real-Debrid or to a proxy address | Real-Debrid | measured |

The 74 s and 95 s are derived: 23:50:10 − 23:48:56, and 23:51:47 − 23:50:12.

## The marking

- Stream 3 was listed not cached at 23:51:49, answered the file at 23:51:53, and was listed cached at 23:52:05, the first listing after the open. Measured.
- So the marking flipped within 12 seconds of an open that found the file ready (derived: 23:52:05 − 23:51:53). That is the behaviour read from source: a stream is recorded as cached when a link to its file is generated.
- It also shows a stream marked not cached that Real-Debrid already held. Opening it answered in 3.38 s, the same as a stream marked cached.
- The opposite case, a stream wrongly marked cached, was not met, so the "Play may hold up to 40 seconds" figure stays derived.

## The `500` clip

- Streams 2 and 4, both from the same release group, answered `500` on every fresh open: three for stream 2 over 2 min 54 s (derived: 23:51:47 − 23:48:53) and one for stream 4. Measured.
- Real-Debrid answered for streams 1 and 3 within the same three minutes, so the account, the token and the service were working. Measured.
- **Why `500`: not determined.** Read from source, Torz redirects to `500` in four places: the service reported down while the torrent was added (a code only the Premiumize store ever sets, so not this one), the torrent's status could not be read or was one the handler does not name, the file's link could not be generated, or a private torrent's file could not be fetched. An answer in under 5 seconds rules out a status wait that ran to its end, since each poll sleeps 5 seconds. What is left is a status read that failed at once, or a torrent Real-Debrid already reports as downloaded whose link it then refuses to generate. Derived, not run; the answer itself does not say which.
- **Whether these opens left anything on the account: not observed.** The owner was asked to look at the Real-Debrid torrent list and did not report on it.
- The decided rule reads `500` as "stop", with "Try again". Here trying again three times over three minutes changed nothing.

## What this means for the decisions

- **The clip rule holds.** A clip is recognisable by its address and readable by its name, and a redirect anywhere else was a ready file, on all seven answers. The size table was not needed and not tested: no clip body was fetched.
- **The 30-second check: nothing measured against it.** No download was watched. The one thing measured is that a re-open inside the minute costs 0.19 s and asks the service nothing.
- **The up-to-40-second hold on Play: not seen.** Every fresh answer took 1.7 to 3.7 seconds. The 15 to 40 seconds applies to a torrent that is queued or downloading, which never occurred.
- **New, and not covered by a decision:** two of the three streams listed not cached could not be started at all. If that is common, "uncached streams start on the user's choice" fails often with a reason line that says only that something went wrong.

## Not determined

- What the `downloading` answer looks like on the hosted instance, and how long its first open takes.
- How long a download takes, and what the link answers once it finishes.
- Why streams 2 and 4 answered `500`, and how common that is. Three streams of one title are not a sample.
- Whether a `500` open adds a torrent to the account.
- Whether a television's player, which follows redirects, treats the 30-second silent clip as the film. Unchanged from the source research.

## A departure from the method

The second open of stream 2 came 13 seconds after the first answer, inside the 30-second floor set for this ticket. It was answered from the instance's memory in 0.19 s, which by the source means Real-Debrid was not asked.

## How to reproduce

The scripts in `torz-real-open/` take a listing saved with the command-line prototype, `lgtv-stremio streams movie <id> --urls > listing.txt`, which opens nothing but holds full links and so stays outside the repository.

- `candidates.py listing.txt 14` prints Torz candidates with each link reduced to a hash prefix, a file index and a filename.
- `open.sh <label> listing.txt <hash prefix>` opens one link once and prints a scrubbed record. On a stream that is not cached this can start a download on the account.
- `marking.sh movie <id> <hash prefix>` re-lists the title and prints how Torz marks the stream.
- `watch.sh` re-opens a link once a minute until it stops answering `downloading`. It was written for this ticket and never ran, because no stream reached that state.

Use different streams: stream 3 is now marked cached.
