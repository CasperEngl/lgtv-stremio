# PROTOTYPE (issue #15): cross-build and package the Stremio top crate without editing a file
# upstream PlxNative owns.
#
# Run from the repository root:
#     make -f stremio/Makefile WEBOS_SDK=<sdk>            build and package the .ipk
#     make -f stremio/Makefile stremio-report             sizes and the package count
#
# It INCLUDES upstream's Makefile and adds targets beside it, so the toolchain, the C boot shim and
# Starfish seam (src/*.c), the bundled FFmpeg and libass, Sentry Native, the codegen flags and the
# link line are upstream's own variables and rules, read where they are defined. Nothing here
# restates them, so an upstream change to any of them reaches this build at the next merge.
include Makefile

.DEFAULT_GOAL := stremio-ipk

# A placeholder: the app's name and id are issue #11's to decide.
STREMIO_APPID   = com.example.stremio.placeholder
STREMIO_VERSION = 0.0.1
STREMIO_OUT     = stremio/out
STREMIO_LIB     = stremio/target/$(RUST_TARGET)/$(ARM_PROFILE)/libstremio_tv.a
STREMIO_BIN     = $(STREMIO_OUT)/stremio-tv
STREMIO_STAGE   = $(STREMIO_OUT)/ipkroot/usr/palm/applications/$(STREMIO_APPID)
STREMIO_IPK     = $(STREMIO_OUT)/$(STREMIO_APPID)_$(STREMIO_VERSION)_arm.ipk
STREMIO_INPUTS := $(shell find stremio/src -type f) stremio/Cargo.toml stremio/Cargo.lock

# `-Z build-std` on the command line because upstream sets it in `rust-modules/.cargo/config.toml`,
# which cargo does not read from this directory. The codegen flags arrive through $(RUST_ENV).
$(STREMIO_LIB): $(STREMIO_INPUTS) $(RUST_INPUTS) ci/install-identities.json stremio/Makefile $(FFABI_STAMP)
	cd stremio && PATH="$$HOME/.cargo/bin:$$PATH" $(RUST_ENV) \
	  cargo +$(RUST_NIGHTLY) rustc $(ARM_PROFILE_FLAG) --target $(RUST_TARGET) --locked \
	    -Z build-std=std,panic_unwind --lib --crate-type staticlib --target-dir target

# Upstream's link line (`pkg/plxnative`) with this crate's archive in place of upstream's.
$(STREMIO_BIN): $(OBJS) $(STREMIO_LIB) $(FFMPEG_STAGED) $(LIBASS_STAGED) $(SENTRY_NATIVE_STAMP)
	mkdir -p $(STREMIO_OUT)
	$(CC) $(CFLAGS) -Wl,--build-id=sha1 $(GC_SECTIONS_LDFLAG) $(SMP_INTERPOSER_LDFLAG) \
	  $(OBJS) $(STREMIO_LIB) $(SENTRY_NATIVE_LIB) \
	  $(SENTRY_UNWIND_LIB) $(LIBS_REAL) -ldl -lrt -lpthread -lm -o $@

# The payload is what this prototype can run with: the binary, the bundled FFmpeg and libass the
# player opens from the app directory, the descriptor, icons and licence texts. The fonts, the
# crash handler and the storage helper service that upstream's package also carries are left out.
.PHONY: stremio-ipk stremio-report
stremio-ipk: $(STREMIO_BIN)
	rm -rf $(STREMIO_OUT)/ipkroot && mkdir -p $(STREMIO_STAGE)/licenses
	cp $(STREMIO_BIN) $(FFMPEG_STAGED) $(LIBASS_STAGED) pkg/icon.png pkg/largeIcon.png \
	  THIRD-PARTY-NOTICES.md LICENSING.md $(STREMIO_STAGE)/
	cp $(LICENSE_FILES) $(STREMIO_STAGE)/licenses/
	$(TOOLPREFIX)strip --strip-unneeded $(STREMIO_STAGE)/stremio-tv
	python3 stremio/mkipk.py --id $(STREMIO_APPID) --version $(STREMIO_VERSION) \
	  --root $(STREMIO_OUT)/ipkroot --out $(STREMIO_IPK)

stremio-report: stremio-ipk
	@python3 stremio/report.py --nm $(TOOLPREFIX)nm --profile $(ARM_PROFILE) \
	  --binary $(STREMIO_BIN) --stripped $(STREMIO_STAGE)/stremio-tv --ipk $(STREMIO_IPK) \
	  --toolchain $(RUST_NIGHTLY)
