//! PROTOTYPE (issue #15): the Stremio app's top crate. It answers one question: can stremio-core
//! and upstream PlxNative's layer crates link into one installable webOS binary without editing a
//! file upstream owns? It has no screens. It boots, runs stremio-core in a frame loop for a few
//! seconds, logs what loaded and exits.
//!
//! Upstream's C boot shim (`src/main.c`, compiled unedited) calls `plex_run`, so this crate
//! exports that name in place of upstream's top crate.

mod env;
mod model;
mod play;

use std::os::raw::{c_char, c_int};
use std::time::Duration;

use plx_base::eventlog::log;
use stremio_core::runtime::msg::{Action, ActionLoad};
use stremio_core::runtime::{Runtime, RuntimeAction};

use crate::env::{FrameExecutor, TvEnv};
use crate::model::TvModel;

/// The webOS port table (`plx_platform::tv::Port`). The identity, key store, toast and window
/// binding entries are upstream's public functions. The window-surface, opaque-region, bus-pump
/// and frame-probe entries are private to upstream's top crate (`rust-modules/src/system.rs`), so
/// the Stremio app supplies its own; this prototype opens no window and leaves them empty.
static PORT: plx_platform::tv::Port = plx_platform::tv::Port {
    probe_device: plx_platform::webos::probe,
    start_capability_probe: plx_platform::webos::caps::start_probe,
    repair_sandbox: plx_platform::webos::jail_repair::execute,
    seal: plx_platform::keymanager::seal,
    open: plx_platform::keymanager::open,
    remove: plx_platform::keymanager::remove,
    system_locale: plx_platform::webos::system_locale,
    go_home: plx_platform::webos::go_home,
    poll_home: plx_platform::webos::poll_home,
    deliver_toast: plx_platform::webos::toast::deliver,
    bind_window: plx_platform::webos::bind_window,
    grab_surface: |_| {},
    release_surface: || false,
    arm_opaque_region: || {},
    opaque_route: |_| {},
    clear_opaque_region: || {},
    pump_bus: || {},
    frame_probe_request: || {},
    frame_probe_prepare_begin: || {},
    frame_probe_prepare_end: || {},
    frame_probe_waiting: || {},
    frame_probe_acquired: || {},
    frame_probe_fields: String::new,
    sink: &plx_media::player::ffi::StarfishSink,
};

const FRAMES: u32 = 300;
const FRAME: Duration = Duration::from_millis(16);

/// The C shim's entry. The two arguments are upstream's compiled-in Plex server address and are
/// ignored.
#[no_mangle]
pub extern "C" fn plex_run(_pms_host: *const c_char, _pms_port: c_int) -> c_int {
    let _ = plx_platform::tv::install(&PORT);
    // SAFETY: the C shim calls this once, on the process's main thread.
    let main_thread = unsafe { plx_base::task::MainThread::assume() };
    log(&format!("stremio-tv prototype {} booting as {}", env!("CARGO_PKG_VERSION"), plx_base::paths::app_id()));
    plx_net::net::set_user_agent(concat!("stremio-tv-prototype/", env!("CARGO_PKG_VERSION")).to_owned());
    if !plx_net::net::global_init() {
        log("stremio-tv: libcurl could not be loaded");
        return 1;
    }

    // Upstream's player boot (`rust-modules/src/app/boot.rs`): bind the video plane and load the
    // bundled FFmpeg. Without the second the demuxer refuses every start.
    plx_media::player::acb_init(&main_thread);
    plx_media::ff::boot();

    let mut executor = FrameExecutor::install();
    let (model, effects) = TvModel::signed_out();
    let (runtime, _events) = Runtime::<TvEnv, _>::new(model, effects.into_iter().collect(), 1024);
    runtime.dispatch(RuntimeAction { field: None, action: Action::Load(ActionLoad::CatalogWithFilters(None)) });

    // The player is started only when a link is handed in, so an ordinary launch never loads one.
    let mut session = plx_media::route::PlaybackSession::IDLE;
    let mut adapter = plx_media::player::adapter::PlayerAdapter::new(main_thread);
    if let Ok(url) = std::env::var("STREMIO_TV_PLAY_URL") {
        let request = play::PlayRequest {
            url: &url,
            video_codec: "h264",
            audio_codec: "aac",
            fps: 0.0,
            resume_ns: 0,
            audio_track: -1,
            subtitle_track: -1,
        };
        log(&format!("stremio-tv: player start accepted={}", play::start(&mut session, &mut adapter, &request)));
    }

    let started = std::time::Instant::now();
    for _ in 0..FRAMES {
        executor.tick();
        if plx_media::player::is_started() {
            plx_media::player::pump(&mut session, &mut adapter, started.elapsed().as_millis() as u32);
        }
        std::thread::sleep(FRAME);
    }
    plx_media::player::stop_bufferfeed(&mut session, &mut adapter);
    let catalog_items = runtime
        .model()
        .map(|model| model.catalog.catalog.iter().filter_map(|page| page.content.as_ref()).count())
        .unwrap_or(0);
    log(&format!("stremio-tv: {catalog_items} catalogue page(s) held after {FRAMES} frames"));
    0
}
