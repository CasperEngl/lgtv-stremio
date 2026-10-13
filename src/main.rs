mod env;
mod hints;
mod model;
mod probe;

use std::collections::BTreeMap;
use std::io::{self, Write};
use std::path::PathBuf;
use std::process::ExitCode;
use std::thread;
use std::time::{Duration, Instant};

use futures::channel::mpsc::Receiver;
use stremio_core::models::catalog_with_filters::Selected as CatalogSelected;
use stremio_core::models::common::Loadable;
use stremio_core::models::ctx::CtxStatus;
use stremio_core::models::meta_details::Selected as MetaDetailsSelected;
use stremio_core::runtime::msg::{Action, ActionCtx, ActionLoad, Event};
use stremio_core::runtime::{Env, Runtime, RuntimeAction, RuntimeEvent};
use stremio_core::types::addon::{Descriptor, ResourcePath, ResourceRequest};
use stremio_core::types::api::AuthRequest;
use stremio_core::types::resource::{Stream, StreamSource};
use url::Url;

use crate::env::{CliEnv, FrameExecutor};
use crate::hints::Hints;
use crate::model::CliModel;

const FRAME: Duration = Duration::from_millis(16);
const QUIET_FRAMES_BEFORE_DONE: u32 = 3;
const TIMEOUT: Duration = Duration::from_secs(60);
const LIBRARY_ROWS: usize = 30;

const USAGE: &str = "\
usage: lgtv-stremio <command>

  login                          sign in (STREMIO_EMAIL / STREMIO_PASSWORD, or a prompt)
  addons                         installed add-ons
  library                        most recently changed library items
  catalogs                       every catalogue the installed add-ons offer
  catalog <n>                    first page of catalogue <n> from `catalogs`
  streams <type> <id> [options]  what the add-ons return for a title
      --video <id>               the episode, e.g. tt0944947:1:1 (defaults to <id>)
      --probe <n>                open the first <n> direct links with ffprobe
      --urls                     print full links (they can carry account tokens)";

struct App {
    executor: FrameExecutor,
    runtime: Runtime<CliEnv, CliModel>,
    events: Receiver<RuntimeEvent<CliEnv, CliModel>>,
    frames: u32,
    longest_tick: Duration,
}

impl App {
    fn start() -> Result<Self, String> {
        CliEnv::set_storage_dir(storage_dir()?)?;
        let mut executor = FrameExecutor::install();
        executor
            .block_on(CliEnv::migrate_storage_schema())
            .map_err(|error| error.to_string())?;
        let (model, effects) = CliModel::from_storage().map_err(|error| error.to_string())?;
        let (runtime, events) = Runtime::new(model, effects.into_iter().collect(), 1024);
        Ok(Self {
            executor,
            runtime,
            events,
            frames: 0,
            longest_tick: Duration::ZERO,
        })
    }

    fn dispatch(&self, action: Action) {
        self.runtime.dispatch(RuntimeAction { field: None, action });
    }

    fn with_model<T>(&self, read: impl FnOnce(&CliModel) -> T) -> T {
        read(&self.runtime.model().expect("no frame panicked while writing the model"))
    }

    /// The frame loop: poll core, drain its events, sleep out the frame. Returns once `done`
    /// holds and core has gone quiet, with every event core emitted on the way.
    fn run_until(&mut self, done: impl Fn(&CliModel) -> bool) -> Result<Vec<Event>, String> {
        let started = Instant::now();
        let mut emitted = Vec::new();
        let mut quiet_frames = 0;
        loop {
            let tick = Instant::now();
            self.executor.tick();
            let mut heard_core = false;
            while let Ok(event) = self.events.try_recv() {
                heard_core = true;
                if let RuntimeEvent::CoreEvent(event) = event {
                    emitted.push(event);
                }
            }
            let tick = tick.elapsed();
            self.frames += 1;
            self.longest_tick = self.longest_tick.max(tick);

            let busy = heard_core || CliEnv::fetches_in_flight() > 0;
            quiet_frames = if busy { 0 } else { quiet_frames + 1 };
            if quiet_frames >= QUIET_FRAMES_BEFORE_DONE && self.with_model(&done) {
                return Ok(emitted);
            }
            if started.elapsed() > TIMEOUT {
                return Err(format!("no answer after {} seconds", TIMEOUT.as_secs()));
            }
            thread::sleep(FRAME.saturating_sub(tick));
        }
    }

    fn report_frames(&self) {
        eprintln!(
            "\nframe loop: {}, longest main-thread tick {:.1} ms, {} on worker threads",
            count(self.frames as usize, "frame"),
            self.longest_tick.as_secs_f64() * 1000.0,
            count(CliEnv::fetches_started(), "request"),
        );
    }
}

fn storage_dir() -> Result<PathBuf, String> {
    let base = match std::env::var_os("XDG_DATA_HOME") {
        Some(dir) => PathBuf::from(dir),
        None => PathBuf::from(std::env::var_os("HOME").ok_or("HOME is not set")?).join(".local/share"),
    };
    Ok(base.join("lgtv-stremio"))
}

fn signed_in_as(model: &CliModel) -> String {
    match &model.ctx.profile.auth {
        Some(auth) => format!("signed in as {}", auth.user.email),
        None => "signed out (official add-ons only; run `login` for yours)".to_owned(),
    }
}

fn login(app: &mut App) -> Result<(), String> {
    let email = match std::env::var("STREMIO_EMAIL") {
        Ok(email) => email,
        Err(_) => {
            print!("Stremio email: ");
            io::stdout().flush().map_err(|error| error.to_string())?;
            let mut line = String::new();
            io::stdin().read_line(&mut line).map_err(|error| error.to_string())?;
            line.trim().to_owned()
        }
    };
    let password = match std::env::var("STREMIO_PASSWORD") {
        Ok(password) => password,
        Err(_) => rpassword::prompt_password("Stremio password: ").map_err(|error| error.to_string())?,
    };
    app.dispatch(Action::Ctx(ActionCtx::Authenticate(AuthRequest::Login {
        email,
        password,
        facebook: false,
    })));
    let events = app.run_until(|model| model.ctx.status == CtxStatus::Ready)?;
    let failure = events.iter().find_map(|event| match event {
        Event::Error { error, .. } => Some(format!("{error:?}")),
        _ => None,
    });
    app.with_model(|model| match (&model.ctx.profile.auth, failure) {
        (Some(_), _) => {
            println!(
                "{}: {} add-ons, {} library items",
                signed_in_as(model),
                model.ctx.profile.addons.len(),
                model.ctx.library.items.len(),
            );
            Ok(())
        }
        (None, Some(failure)) => Err(format!("sign-in failed: {failure}")),
        (None, None) => Err("sign-in failed without a reason from core".to_owned()),
    })
}

fn addons(app: &App) {
    app.with_model(|model| {
        println!("{}\n", signed_in_as(model));
        for addon in &model.ctx.profile.addons {
            let manifest = &addon.manifest;
            println!("{} {}  [{}]", manifest.name, manifest.version, manifest.types.join(", "));
            println!("    {}", addon.transport_url.host_str().unwrap_or("local"));
        }
    });
}

fn library(app: &App) {
    app.with_model(|model| {
        println!("{}\n", signed_in_as(model));
        let mut items: Vec<_> = model
            .ctx
            .library
            .items
            .values()
            .filter(|item| !item.removed && !item.temp)
            .collect();
        items.sort_by_key(|item| std::cmp::Reverse(item.mtime));
        for item in items.iter().take(LIBRARY_ROWS) {
            let minutes = item.state.time_watched / 60_000;
            println!("{:<8} {:<12} {}  ({minutes} min watched)", item.r#type, item.id, item.name);
        }
        println!("\n{} of {} items", items.len().min(LIBRARY_ROWS), items.len());
    });
}

/// Catalogues that load without a search term or another required filter.
fn browsable_catalogs(addons: &[Descriptor]) -> Vec<(String, ResourceRequest)> {
    let mut found = Vec::new();
    for addon in addons {
        for catalog in &addon.manifest.catalogs {
            let Some(extra) = catalog.default_required_extra() else {
                continue;
            };
            let label = format!(
                "{:<8} {}  ({})",
                catalog.r#type,
                catalog.name.as_deref().unwrap_or(&catalog.id),
                addon.manifest.name,
            );
            let path = ResourcePath::with_extra("catalog", &catalog.r#type, &catalog.id, &extra);
            found.push((label, ResourceRequest::new(addon.transport_url.clone(), path)));
        }
    }
    found
}

fn catalogs(app: &App) {
    let found = app.with_model(|model| browsable_catalogs(&model.ctx.profile.addons));
    for (index, (label, _)) in found.iter().enumerate() {
        println!("{index:>3}  {label}");
    }
}

fn catalog(app: &mut App, index: &str) -> Result<(), String> {
    let index: usize = index.parse().map_err(|_| format!("`{index}` is not a catalogue number"))?;
    let (label, request) = app
        .with_model(|model| browsable_catalogs(&model.ctx.profile.addons))
        .into_iter()
        .nth(index)
        .ok_or_else(|| format!("there is no catalogue {index}; see `catalogs`"))?;
    app.dispatch(Action::Load(ActionLoad::CatalogWithFilters(Some(CatalogSelected { request }))));
    app.run_until(|model| {
        model
            .catalog
            .catalog
            .iter()
            .all(|page| !matches!(page.content, Some(Loadable::Loading)))
    })?;
    app.with_model(|model| {
        println!("{label}\n");
        match model.catalog.catalog.first().and_then(|page| page.content.as_ref()) {
            Some(Loadable::Ready(items)) => {
                for item in items {
                    let year = item.release_info.as_deref().unwrap_or("");
                    println!("{:<8} {:<12} {} {year}", item.r#type, item.id, item.name);
                }
                Ok(())
            }
            Some(Loadable::Err(error)) => Err(format!("the add-on answered with an error: {error}")),
            Some(Loadable::Loading) | None => Err("the catalogue did not load".to_owned()),
        }
    })
}

struct StreamOptions {
    kind: String,
    id: String,
    video: Option<String>,
    probe: usize,
    full_urls: bool,
}

impl StreamOptions {
    fn parse(args: &[String]) -> Result<Self, String> {
        let [kind, id, flags @ ..] = args else {
            return Err("streams needs a type and an id, e.g. `streams movie tt0111161`".to_owned());
        };
        let mut options = Self {
            kind: kind.clone(),
            id: id.clone(),
            video: None,
            probe: 0,
            full_urls: false,
        };
        let mut flags = flags.iter();
        while let Some(flag) = flags.next() {
            match flag.as_str() {
                "--urls" => options.full_urls = true,
                "--video" => options.video = Some(flags.next().ok_or("--video needs an id")?.clone()),
                "--probe" => {
                    let count = flags.next().ok_or("--probe needs a count")?;
                    options.probe = count.parse().map_err(|_| format!("`{count}` is not a count"))?;
                }
                other => return Err(format!("unknown option `{other}`")),
            }
        }
        Ok(options)
    }
}

/// How the stream reaches a player, and the direct link when it has one.
fn delivery(stream: &Stream) -> (&'static str, Option<&Url>) {
    match &stream.source {
        StreamSource::Url { url } => ("direct link", Some(url)),
        StreamSource::Torrent { .. } => ("torrent", None),
        StreamSource::YouTube { .. } => ("youtube", None),
        StreamSource::External { .. } => ("external page", None),
        StreamSource::PlayerFrame { .. } => ("embedded page", None),
        StreamSource::Nzb { .. } => ("usenet", None),
        StreamSource::Rar { .. }
        | StreamSource::Zip { .. }
        | StreamSource::Zip7 { .. }
        | StreamSource::Tgz { .. }
        | StreamSource::Tar { .. } => ("archive", None),
    }
}

fn count(n: usize, noun: &str) -> String {
    format!("{n} {noun}{}", if n == 1 { "" } else { "s" })
}

#[derive(Default)]
struct Tally {
    streams: usize,
    delivery: BTreeMap<&'static str, usize>,
    video: BTreeMap<&'static str, usize>,
    audio: BTreeMap<&'static str, usize>,
}

impl Tally {
    fn add(&mut self, delivery: &'static str, hints: &Hints) {
        self.streams += 1;
        *self.delivery.entry(delivery).or_default() += 1;
        *self.video.entry(hints.video.unwrap_or("not stated")).or_default() += 1;
        *self.audio.entry(hints.audio.unwrap_or("not stated")).or_default() += 1;
    }

    fn print(&self) {
        let line = |counts: &BTreeMap<&'static str, usize>| {
            counts
                .iter()
                .map(|(name, count)| format!("{name} {count}"))
                .collect::<Vec<_>>()
                .join(", ")
        };
        println!("{}", count(self.streams, "stream"));
        if self.streams > 0 {
            println!("  delivery: {}", line(&self.delivery));
            println!("  video:    {}", line(&self.video));
            println!("  audio:    {}", line(&self.audio));
        }
    }
}

fn streams(app: &mut App, options: &StreamOptions) -> Result<(), String> {
    let video = options.video.as_deref().unwrap_or(&options.id);
    app.dispatch(Action::Load(ActionLoad::MetaDetails(MetaDetailsSelected {
        meta_path: ResourcePath::without_extra("meta", &options.kind, &options.id),
        stream_path: Some(ResourcePath::without_extra("stream", &options.kind, video)),
        guess_stream: false,
    })));
    app.run_until(|model| {
        let details = &model.meta_details;
        details.meta_items.iter().all(|item| !matches!(item.content, Some(Loadable::Loading)))
            && details.streams.iter().all(|group| !matches!(group.content, Some(Loadable::Loading)))
    })?;

    let mut tally = Tally::default();
    let mut to_probe = Vec::new();
    app.with_model(|model| {
        let title = model.meta_details.meta_items.iter().find_map(|item| match &item.content {
            Some(Loadable::Ready(meta)) => Some(meta.preview.name.as_str()),
            _ => None,
        });
        println!("{} ({} {video})\n", title.unwrap_or("unknown title"), options.kind);
        if model.meta_details.streams.is_empty() {
            println!("no installed add-on offers streams for this title");
        }
        for group in &model.meta_details.streams {
            let addon = model
                .ctx
                .profile
                .addons
                .iter()
                .find(|addon| addon.transport_url == group.request.base)
                .map_or("unknown add-on", |addon| addon.manifest.name.as_str());
            match &group.content {
                Some(Loadable::Ready(found)) => {
                    println!("{addon}: {}", count(found.len(), "stream"));
                    for stream in found {
                        let (delivery, url) = delivery(stream);
                        let filename = stream.behavior_hints.filename.as_deref();
                        let texts: Vec<&str> = [stream.name.as_deref(), stream.description.as_deref(), filename]
                            .into_iter()
                            .flatten()
                            .collect();
                        let hints = Hints::parse(&texts, filename.or(url.map(Url::path)));
                        tally.add(delivery, &hints);
                        let whereabouts = match url {
                            Some(url) if options.full_urls => format!(" {url}"),
                            Some(url) => format!(" {}", url.host_str().unwrap_or("no host")),
                            None => String::new(),
                        };
                        let size = stream
                            .behavior_hints
                            .video_size
                            .map_or(String::new(), |bytes| format!(" · {:.1} GB", bytes as f64 / 1e9));
                        println!("  {delivery}{whereabouts} · {hints}{size}");
                        if let Some(url) = url {
                            if stream.behavior_hints.proxy_headers.is_none() {
                                to_probe.push(url.clone());
                            }
                        }
                    }
                }
                Some(Loadable::Err(error)) => println!("{addon}: {error}"),
                Some(Loadable::Loading) | None => println!("{addon}: no answer"),
            }
        }
        println!();
        tally.print();
    });

    if options.probe > 0 {
        println!("\nopened with ffprobe:");
        if to_probe.is_empty() {
            println!("  no direct links to open");
        }
        for url in to_probe.iter().take(options.probe) {
            let host = url.host_str().unwrap_or("no host");
            match probe::describe(url.as_str()) {
                Ok(found) => println!("  {host}: {found}"),
                Err(reason) => println!("  {host}: could not open ({reason})"),
            }
        }
    }
    Ok(())
}

fn run(args: &[String]) -> Result<(), String> {
    let (command, rest) = args.split_first().ok_or(USAGE)?;
    let mut app = App::start()?;
    let outcome = match (command.as_str(), rest) {
        ("login", []) => login(&mut app),
        ("addons", []) => Ok(addons(&app)),
        ("library", []) => Ok(library(&app)),
        ("catalogs", []) => Ok(catalogs(&app)),
        ("catalog", [index]) => catalog(&mut app, index),
        ("streams", rest) => StreamOptions::parse(rest).and_then(|options| streams(&mut app, &options)),
        _ => Err(USAGE.to_owned()),
    };
    if app.frames > 0 {
        app.report_frames();
    }
    outcome
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    match run(&args) {
        Ok(()) => ExitCode::SUCCESS,
        Err(message) => {
            eprintln!("{message}");
            ExitCode::FAILURE
        }
    }
}
