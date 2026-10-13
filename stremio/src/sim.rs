//! PROTOTYPE (issue #31): the Stremio top crate as a desktop simulator. It answers one question:
//! does this crate build for a desktop with upstream's `hostsim` feature, open a window, run
//! stremio-core in the frame loop and reach a stand-in server through upstream's network client,
//! with no edit to a file upstream owns?
//!
//! It is not the app: one hard-coded screen that says what the catalogue request returned.
//!
//! Environment:
//!   STREMIO_TV_STAND_IN      address every stremio-core request is sent to (see `env::stand_in`)
//!   STREMIO_TV_SIM_SHOT      write the window's pixels here (binary PPM) once the catalogue
//!                            request has an answer, then exit: 0 if it loaded, 3 if it failed
//!   STREMIO_TV_SIM_FRAMES    give up after this many frames (exit 4); default 900 with a shot
//!                            path, unlimited without one
//!   PLXNATIVE_RUNTIME_DIR    where the event log goes (upstream's variable)
//!   PLXNATIVE_APP_DIR        where the fonts live: the repository's `pkg/` (upstream's variable)
//!   PLXNATIVE_WIN            window size as `<w>x<h>`; default 1280x720

use std::ffi::{c_char, c_int, c_uint, c_void, CStr, CString};
use std::time::{Duration, Instant};

use plx_base::eventlog::log;
use stremio_core::models::common::Loadable;
use stremio_core::runtime::msg::{Action, ActionLoad};
use stremio_core::runtime::{Runtime, RuntimeAction};

use crate::env::{FrameExecutor, TvEnv};
use crate::model::TvModel;

// Stock SDL2 and desktop GL, linked by `build.rs`. Upstream declares the same functions privately
// in its top crate (`rust-modules/src/app/`), which no other crate can reach.
extern "C" {
    fn SDL_SetMainReady();
    fn SDL_Init(flags: u32) -> c_int;
    fn SDL_GetError() -> *const c_char;
    fn SDL_GetCurrentVideoDriver() -> *const c_char;
    fn SDL_GL_SetAttribute(attr: c_int, value: c_int) -> c_int;
    fn SDL_CreateWindow(title: *const c_char, x: c_int, y: c_int, w: c_int, h: c_int, flags: u32) -> *mut c_void;
    fn SDL_GL_CreateContext(win: *mut c_void) -> *mut c_void;
    fn SDL_GL_SetSwapInterval(interval: c_int) -> c_int;
    fn SDL_GL_SwapWindow(win: *mut c_void);
    fn SDL_PollEvent(event: *mut Event) -> c_int;
    fn glGetString(name: c_uint) -> *const u8;
    fn glViewport(x: c_int, y: c_int, w: c_int, h: c_int);
    fn glReadPixels(x: c_int, y: c_int, w: c_int, h: c_int, format: c_uint, ty: c_uint, pixels: *mut c_void);
    fn _exit(code: c_int) -> !;
}

/// `SDL_Event` is a 56-byte union; only the type and a key press's symbol are read.
#[repr(C, align(8))]
struct Event([u8; 64]);

const SDL_INIT_VIDEO: u32 = 0x20;
const SDL_QUIT: u32 = 0x100;
const SDL_KEYDOWN: u32 = 0x300;
const SDLK_ESCAPE: u32 = 27;
/// `SDL_WINDOW_OPENGL | SDL_WINDOW_ALLOW_HIGHDPI`, upstream's simulator flags.
const WINDOW_FLAGS: u32 = 0x2 | 0x2000;
const WINDOWPOS_CENTERED: c_int = 0x2FFF_0000;
// SDL_GLattr
const A_RED: c_int = 0;
const A_GREEN: c_int = 1;
const A_BLUE: c_int = 2;
const A_ALPHA: c_int = 3;
const A_DEPTH: c_int = 6;
const A_STENCIL: c_int = 7;
const A_CTX_MAJOR: c_int = 17;
const A_CTX_MINOR: c_int = 18;
const A_CTX_PROFILE_MASK: c_int = 21;
const CTX_PROFILE_CORE: c_int = 0x0001;
const GL_RENDERER: c_uint = 0x1F01;
const GL_VERSION: c_uint = 0x1F02;
const GL_RGB: c_uint = 0x1907;
const GL_UNSIGNED_BYTE: c_uint = 0x1401;

const FRAME: Duration = Duration::from_millis(16);

/// What the catalogue request has come to.
enum Catalogue {
    Waiting,
    Loaded { titles: usize, first: String },
    Failed(String),
}

fn catalogue(runtime: &Runtime<TvEnv, TvModel>) -> Catalogue {
    let Ok(model) = runtime.model() else { return Catalogue::Waiting };
    for page in &model.catalog.catalog {
        match &page.content {
            Some(Loadable::Ready(items)) => {
                let first = items.first().map(|item| item.name.clone()).unwrap_or_default();
                return Catalogue::Loaded { titles: items.len(), first };
            }
            Some(Loadable::Err(error)) => return Catalogue::Failed(format!("{error:?}")),
            _ => {}
        }
    }
    Catalogue::Waiting
}

fn window_size() -> (c_int, c_int) {
    std::env::var("PLXNATIVE_WIN")
        .ok()
        .and_then(|value| {
            let (w, h) = value.split_once('x')?;
            Some((w.parse().ok()?, h.parse().ok()?))
        })
        .unwrap_or((1280, 720))
}

fn sdl_error() -> String {
    // SAFETY: SDL returns a NUL-terminated string it owns, never null.
    unsafe { CStr::from_ptr(SDL_GetError()) }.to_string_lossy().into_owned()
}

/// The window and its GL context: upstream's sequence in `app/boot.rs`, with the same 4.1 core
/// request the `hostsim` drawing layer expects.
unsafe fn open_window() -> Result<*mut c_void, String> {
    SDL_SetMainReady();
    if SDL_Init(SDL_INIT_VIDEO) != 0 {
        return Err(format!("SDL_Init failed: {}", sdl_error()));
    }
    let driver = SDL_GetCurrentVideoDriver();
    if !driver.is_null() {
        log(&format!("video driver: {}", CStr::from_ptr(driver).to_string_lossy()));
    }
    SDL_GL_SetAttribute(A_CTX_PROFILE_MASK, CTX_PROFILE_CORE);
    SDL_GL_SetAttribute(A_CTX_MAJOR, 4);
    SDL_GL_SetAttribute(A_CTX_MINOR, 1);
    for attr in [A_RED, A_GREEN, A_BLUE, A_ALPHA] {
        SDL_GL_SetAttribute(attr, 8);
    }
    SDL_GL_SetAttribute(A_DEPTH, 0);
    SDL_GL_SetAttribute(A_STENCIL, 0);
    let (w, h) = window_size();
    let win = SDL_CreateWindow(c"Stremio prototype".as_ptr(), WINDOWPOS_CENTERED, WINDOWPOS_CENTERED, w, h, WINDOW_FLAGS);
    if win.is_null() {
        return Err(format!("SDL_CreateWindow failed: {}", sdl_error()));
    }
    if SDL_GL_CreateContext(win).is_null() {
        return Err(format!("SDL_GL_CreateContext failed: {}", sdl_error()));
    }
    SDL_GL_SetSwapInterval(1);
    let (renderer, version) = (glGetString(GL_RENDERER), glGetString(GL_VERSION));
    if !renderer.is_null() && !version.is_null() {
        log(&format!(
            "GL: {} / {}",
            CStr::from_ptr(renderer.cast()).to_string_lossy(),
            CStr::from_ptr(version.cast()).to_string_lossy()
        ));
    }
    Ok(win)
}

/// Drains SDL's queue. `false` when the window was closed or Escape pressed. Stock SDL2's event
/// layout, which is what upstream's `hostsim` key decoding reads too.
unsafe fn pump_events() -> bool {
    let mut event = Event([0; 64]);
    let mut running = true;
    while SDL_PollEvent(&mut event) != 0 {
        let kind = u32::from_ne_bytes(event.0[0..4].try_into().unwrap());
        let key = u32::from_ne_bytes(event.0[20..24].try_into().unwrap());
        if kind == SDL_QUIT || (kind == SDL_KEYDOWN && key == SDLK_ESCAPE) {
            running = false;
        }
    }
    running
}

fn draw(status: &str, detail: &str) {
    const PANEL: [f32; 4] = [0.10, 0.13, 0.20, 1.0];
    const INK: [f32; 4] = [0.93, 0.95, 0.98, 1.0];
    const DIM: [f32; 4] = [0.62, 0.68, 0.78, 1.0];
    plx_gfx::text::begin_frame();
    let (vx, vy, vw, vh) = plx_base::surface::viewport();
    // SAFETY: a GL context is current on this thread for the life of the loop.
    unsafe { glViewport(vx, vy, vw, vh) };
    plx_gfx::gfx::frame_clear(0.04, 0.05, 0.09);
    plx_gfx::gfx::draw_rrect(160.0, 380.0, 1600.0, 320.0, 28.0, 28.0, PANEL.as_ptr());
    let line = |text: &str, y: f32, size: c_int, colour: &[f32; 4], bold: c_int| {
        let Ok(text) = CString::new(text) else { return };
        plx_gfx::text::draw_text(text.as_ptr(), 220.0, y, size, colour.as_ptr(), 0, bold, plx_gfx::gfx::Zoom::NONE);
    };
    line("Stremio prototype: desktop simulator", 430.0, 44, &INK, 1);
    line(status, 520.0, 34, &INK, 0);
    line(detail, 590.0, 28, &DIM, 0);
}

/// The drawable as a binary PPM, top row first.
unsafe fn write_shot(path: &str) -> std::io::Result<()> {
    let (vx, vy, vw, vh) = plx_base::surface::viewport();
    let (w, h) = (vw as usize, vh as usize);
    let mut pixels = vec![0u8; w * h * 3];
    // Rows are read one at a time so no row padding (GL_PACK_ALIGNMENT) is involved.
    for row in 0..h {
        let target = pixels[(h - 1 - row) * w * 3..].as_mut_ptr();
        glReadPixels(vx, vy + row as c_int, vw, 1, GL_RGB, GL_UNSIGNED_BYTE, target.cast());
    }
    let mut file = format!("P6\n{w} {h}\n255\n").into_bytes();
    file.extend_from_slice(&pixels);
    std::fs::write(path, file)
}

fn run() -> c_int {
    let root = plx_base::paths::runtime_dir();
    let events = plx_base::eventlog::events_log();
    if let Err(error) = std::fs::create_dir_all(root).and_then(|()| std::fs::write(&events, "sim: THIS IS THE DESKTOP SIMULATOR, not a television.\n")) {
        eprintln!("stremio-sim: cannot start the event log {}: {error}", events.display());
        return 1;
    }
    eprintln!("stremio-sim: log={}", events.display());

    let _ = plx_platform::tv::install(&crate::PORT);
    plx_net::net::set_user_agent(concat!("stremio-tv-prototype/", env!("CARGO_PKG_VERSION")).to_owned());
    if !plx_net::net::global_init() {
        log("stremio-sim: libcurl could not be loaded");
        return 1;
    }

    // SAFETY: `main` calls this once, on the process's main thread.
    let win = match unsafe { open_window() } {
        Ok(win) => win,
        Err(error) => {
            log(&format!("stremio-sim: {error}"));
            return 1;
        }
    };
    plx_base::surface::probe(win);
    plx_gfx::gfx::init_gl();
    plx_gfx::text::init_text();

    let mut executor = FrameExecutor::install();
    let (model, effects) = TvModel::signed_out();
    let (runtime, _events) = Runtime::<TvEnv, _>::new(model, effects.into_iter().collect(), 1024);
    runtime.dispatch(RuntimeAction { field: None, action: Action::Load(ActionLoad::CatalogWithFilters(None)) });

    let shot = std::env::var("STREMIO_TV_SIM_SHOT").ok().filter(|path| !path.is_empty());
    let frame_limit = std::env::var("STREMIO_TV_SIM_FRAMES")
        .ok()
        .and_then(|value| value.parse::<u64>().ok())
        .or(shot.as_ref().map(|_| 900));
    let started = Instant::now();
    let mut answered_at = None;
    let mut frame = 0u64;
    loop {
        let frame_started = Instant::now();
        // SAFETY: SDL was initialised on this thread.
        if !unsafe { pump_events() } {
            log(&format!("stremio-sim: closed after {frame} frames"));
            return 0;
        }
        executor.tick();
        let state = catalogue(&runtime);
        let (status, detail, code) = match &state {
            Catalogue::Waiting => ("Catalogue: waiting for an answer".to_owned(), String::new(), None),
            Catalogue::Loaded { titles, first } => (format!("Catalogue: {titles} titles"), format!("First: {first}"), Some(0)),
            Catalogue::Failed(error) => ("Catalogue: the request failed".to_owned(), error.clone(), Some(3)),
        };
        if code.is_some() && answered_at.is_none() {
            answered_at = Some(frame);
            log(&format!("stremio-sim: {status}; {detail}; frame {frame}, {} ms after the window opened", started.elapsed().as_millis()));
        }
        draw(&status, &detail);
        // One more drawn frame after the answer, so the shot shows it.
        if let (Some(path), Some(code), Some(at)) = (&shot, code, answered_at) {
            if frame > at {
                // SAFETY: reads the back buffer of the context made current in `open_window`.
                match unsafe { write_shot(path) } {
                    Ok(()) => log(&format!("stremio-sim: shot written to {path}")),
                    Err(error) => {
                        log(&format!("stremio-sim: cannot write the shot {path}: {error}"));
                        return 1;
                    }
                }
                return code;
            }
        }
        plx_base::surface::present_supersampled();
        // SAFETY: `win` is the live window created above.
        unsafe { SDL_GL_SwapWindow(win) };
        frame += 1;
        if frame_limit.is_some_and(|limit| frame >= limit) {
            log(&format!("stremio-sim: no catalogue answer after {frame} frames"));
            return 4;
        }
        // A software rasteriser's swap does not wait for a display.
        if let Some(rest) = FRAME.checked_sub(frame_started.elapsed()) {
            std::thread::sleep(rest);
        }
    }
}

pub fn main() -> ! {
    let code = run();
    // Not `std::process::exit`: request threads may still be inside libcurl, and libc's exit
    // handlers free OpenSSL's tables under them (`rust-modules/src/bin/sim.rs` explains the crash).
    // SAFETY: `_exit` takes no pointers and ends every thread at once.
    unsafe { _exit(code) }
}
