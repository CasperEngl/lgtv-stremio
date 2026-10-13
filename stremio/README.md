# Stremio top crate (prototype)

PROTOTYPE for issue #15: does `stremio-core` build and link with upstream PlxNative's layer crates
into an installable webOS app without editing a file upstream owns? It has no screens and is not
the app. It boots, runs `stremio-core` in a frame loop for about five seconds, logs what loaded
and exits.

Everything is new files:

- `Cargo.toml`, `Cargo.lock`, `build.rs`, `src/`: the top crate `stremio-tv`, in its own cargo
  workspace. It depends on the thirteen `plx_*` crates by path and on `stremio-core`, and exports
  `plex_run`, the entry upstream's unedited C boot shim calls.
- `Makefile`: includes upstream's `Makefile` and adds the Stremio targets beside it.
- `mkipk.py`, `report.py`: the packer and the size and package-count report.
- `upstream-exceptions.txt`: the list of edited upstream files. It is empty.
- `../.github/workflows/stremio.yml`: the workflow that builds, packages and checks all of this.

Build, from the repository root, on a host the webOS toolchain exists for (macOS or arm64 Linux):

    make -f stremio/Makefile stremio-report

## Desktop simulator (prototype for issue #31)

The same crate builds for a desktop with upstream's `hostsim` feature as `stremio-sim`: one window
that runs `stremio-core` in the frame loop and shows what its catalogue request returned. It needs
stable Rust, a C compiler, `pkg-config` and the SDL2, SDL2_ttf and OpenGL development files; no
webOS toolchain. From the repository root:

    make -f stremio/Makefile stremio-sim-smoke

That launches it against a throwaway server on loopback (`sim-smoke.py`) and writes
`stremio/out/sim/stremio-sim.png`. `STREMIO_TV_STAND_IN=<address>` is the address override of
`docs/adr/0002`: every request `stremio-core` makes goes to `<address>/<original host>/<path>`.
Without it the simulator talks to the real services. `src/sim.rs` lists the other variables.

The package id `com.example.stremio.placeholder` is a placeholder; issue #11 decides the real one.
