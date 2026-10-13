//! PROTOTYPE (issue #31): host link configuration for the desktop simulator binary.
//!
//! Upstream's own build scripts print the SDL2, SDL2_ttf, GL and nanosvg link lines from one file,
//! `rust-modules/build_support/host_link.rs`, and the nanosvg object (a `rustc-link-arg`) reaches
//! only the package whose script prints it. So this package runs the same file, included by path
//! and unedited. For the television target it prints nothing: `host_link::emit` returns at once
//! when the target architecture is 32-bit ARM, where the Makefile links.

#[path = "../rust-modules/build_support/host_link.rs"]
mod host_link;

fn main() {
    println!("cargo:rerun-if-changed=build.rs");
    println!("cargo:rerun-if-changed=../rust-modules/build_support/host_link.rs");
    host_link::emit(&std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join(".."));
}
