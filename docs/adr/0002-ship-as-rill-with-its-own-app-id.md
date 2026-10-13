---
status: accepted
---

# Ship as Rill, under its own app id, as an `.ipk` on GitHub Releases

The app is called **Rill**. Its app ids are `com.casperengelmann.rill` and, for the developer
install beside it, `com.casperengelmann.rill.debug`. A release is a GitHub Release on
`CasperEngl/lgtv-stremio` that people install with webOS Dev Manager on a television in Developer
Mode. The name has no "Stremio" in it because "Stremio" is a registered mark (US word mark
5760736, classes 9 and 41) and the official app of that name is in the LG Content Store for 2020
and later models, so this app's tile sits beside the real one; and it is not PlxNative's because
`TRADEMARKS.md` reserves that name, logo and splash from forks.

## The rules this sets

- **"Stremio" describes, it never names.** The word appears in one describing line, "Unofficial
  client for Stremio - not affiliated with Stremio", in the launcher description and at the top of
  the README. It is not in the title, not in the app id, and the id is not in Stremio's `io.strem`
  namespace. The repository keeps the name `lgtv-stremio`; the app does not share it.
- **Artwork is new.** The icon and splash borrow nothing from the PLX logo and nothing from
  Stremio's diamond or purple (the logo is Stremio's second registered mark, US 7832606).
- **The app id is fixed from the first release.** A television treats a different id as a
  different app, so changing it means everyone reinstalls and signs in again. The name can still
  change before the first release; the id's last segment would follow it.
- **Two installs, not three.** The released app and the `.debug` install. No nightly.
- **A release carries the `.ipk`, its SHA-256 and the matching source bundle**, the last because
  `LICENSING.md` requires it next to every binary. The install guide lives in this repository.
  There is no website.
- **The app says when it is old.** At most once a day it asks GitHub for the latest release and
  shows a quiet "version X is available" line with the release address. It cannot install the
  update itself; that is Dev Manager again. This makes `api.github.com` one of the hosts the app
  reaches.
- **No Homebrew Channel in the first version.** No repository feed of the fork's own, and no
  submission to Homebrew Channel's default catalogue.
- **Its own version, starting at `0.1.0`**, unrelated to upstream's.

## Considered options

- **"… for Stremio" as the title.** Most unofficial webOS ports do this and none was found to
  have been pursued for it. Rejected because the one confirmed enforcement was against an app
  using Stremio's name and logo in a store, the word mark covers client software, and a
  Homebrew Channel maintainer has already said of one such port that "the package name may confuse
  people".
- **`io.github.casperengl.` as the id prefix.** Rejected: it ties a permanent id to a hosting
  account, and the owner holds `casperengelmann.com`.
- **No update notice.** Rejected: an app that cannot update itself and never says it is old stays
  old.
- **A Homebrew Channel repository feed**, so updates need the remote and no computer. Left out of
  the first version: it needs a hosted feed and a manifest per release, and whether Homebrew
  Channel can install other apps on a television without root is stated by upstream's install
  guide but was not confirmed from Homebrew Channel's own documentation.
- **Submitting to Homebrew Channel's default catalogue.** Rejected for now: its rules include "NO
  PIRACY", two Stremio submissions sit unmerged, and a submission needs a release tested on a real
  television.

## Consequences

- Rill installs beside PlxNative on one television. Any id other than `com.beb.plxnative` gets its
  own folder under `/tmp` and its own sign-in file (`rust-modules/base/src/paths.rs`).
- `pkg/appinfo.json` and the artwork under `pkg/` are upstream's files, which
  [0001](0001-track-upstream-with-stremio-in-new-crates.md) leaves unedited. Rill's descriptor and
  artwork are therefore new files, and how they reach the package is the build plan's to settle.
- The name was checked on 2026-10-14 by web search only. Two other products use the word: Rill
  Data, a business-intelligence tool, and an iOS app listed as "Rill Live Streaming App". No
  television app, media player or Homebrew Channel entry of that name was found. The USPTO and
  EUIPO registers were not queried, so whether "RILL" is registered for software is not known.
