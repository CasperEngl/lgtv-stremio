# Stremio top crate (prototype)

PROTOTYPE for issue #15: does `stremio-core` build and link with upstream PlxNative's layer crates
into an installable webOS app without editing a file upstream owns? It has no screens and is not
the app. It boots, runs `stremio-core` in a frame loop for about five seconds, logs what loaded
and exits.

Everything is new files:

- `Cargo.toml`, `Cargo.lock`, `src/`: the top crate `stremio-tv`, in its own cargo workspace. It
  depends on the thirteen `plx_*` crates by path and on `stremio-core`, and exports `plex_run`,
  the entry upstream's unedited C boot shim calls.
- `Makefile`: includes upstream's `Makefile` and adds the Stremio targets beside it.
- `mkipk.py`, `report.py`: the packer and the size and package-count report.
- `upstream-exceptions.txt`: the list of edited upstream files. It is empty.
- `../.github/workflows/stremio.yml`: the workflow that builds, packages and checks all of this.

Build, from the repository root, on a host the webOS toolchain exists for (macOS or arm64 Linux):

    make -f stremio/Makefile stremio-report

The package id `com.example.stremio.placeholder` is a placeholder; issue #11 decides the real one.
