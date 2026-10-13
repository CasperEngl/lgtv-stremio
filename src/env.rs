//! The host side of stremio-core: where its futures run, how it reaches the network and where
//! it keeps state.
//!
//! The shape mirrors a television app's main loop. Core's futures are polled on the main thread
//! once per frame by [`FrameExecutor::tick`], and every HTTP request runs on its own
//! `std::thread`, handing raw bytes back through a channel. There is no async runtime.

use std::cell::RefCell;
use std::fs;
use std::io::ErrorKind;
use std::path::PathBuf;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::OnceLock;
use std::thread;
use std::time::Duration;

use chrono::{DateTime, Utc};
use futures::channel::{mpsc, oneshot};
use futures::executor::{LocalPool, LocalSpawner};
use futures::future::{self, LocalBoxFuture};
use futures::task::LocalSpawnExt;
use futures::{Future, FutureExt, StreamExt};
use http::{Method, Request};
use serde::{Deserialize, Serialize};
use stremio_core::models::ctx::Ctx;
use stremio_core::models::streaming_server::StreamingServer;
use stremio_core::runtime::{Env, EnvError, EnvFuture, EnvFutureExt, TryEnvFuture};

const FETCH_TIMEOUT: Duration = Duration::from_secs(30);
const MAX_RESPONSE_BYTES: u64 = 64 * 1024 * 1024;

type SequentialJob = LocalBoxFuture<'static, ()>;

thread_local! {
    static SPAWNER: RefCell<Option<LocalSpawner>> = const { RefCell::new(None) };
    static SEQUENTIAL: RefCell<Option<mpsc::UnboundedSender<SequentialJob>>> = const { RefCell::new(None) };
}

static STORAGE_DIR: OnceLock<PathBuf> = OnceLock::new();
static AGENT: OnceLock<ureq::Agent> = OnceLock::new();
static FETCHES_IN_FLIGHT: AtomicUsize = AtomicUsize::new(0);
static FETCHES_STARTED: AtomicUsize = AtomicUsize::new(0);

/// Polls core's futures on the thread that created it. Call [`tick`](Self::tick) once per frame.
pub struct FrameExecutor {
    pool: LocalPool,
}

impl FrameExecutor {
    /// Makes this thread the one core's futures run on.
    pub fn install() -> Self {
        let pool = LocalPool::new();
        let spawner = pool.spawner();
        let (tx, mut rx) = mpsc::unbounded::<SequentialJob>();
        spawner
            .spawn_local(async move {
                while let Some(job) = rx.next().await {
                    job.await;
                }
            })
            .expect("the pool was just created");
        SPAWNER.with(|slot| *slot.borrow_mut() = Some(spawner));
        SEQUENTIAL.with(|slot| *slot.borrow_mut() = Some(tx));
        Self { pool }
    }

    /// Runs every future that can make progress, then returns without waiting for the rest.
    pub fn tick(&mut self) {
        self.pool.run_until_stalled();
    }

    /// Blocks until `future` finishes. For startup only; a frame loop uses `tick`.
    pub fn block_on<F: Future>(&mut self, future: F) -> F::Output {
        self.pool.run_until(future)
    }
}

pub enum CliEnv {}

impl CliEnv {
    pub fn set_storage_dir(dir: PathBuf) -> Result<(), String> {
        fs::create_dir_all(&dir).map_err(|error| format!("{}: {error}", dir.display()))?;
        STORAGE_DIR
            .set(dir)
            .map_err(|_| "the storage directory is already set".to_owned())
    }

    pub fn fetches_in_flight() -> usize {
        FETCHES_IN_FLIGHT.load(Ordering::Relaxed)
    }

    pub fn fetches_started() -> usize {
        FETCHES_STARTED.load(Ordering::Relaxed)
    }

    pub fn read_storage<T: for<'de> Deserialize<'de>>(key: &str) -> Result<Option<T>, EnvError> {
        let path = storage_path(key)?;
        match fs::read(&path) {
            Ok(bytes) => serde_json::from_slice(&bytes)
                .map(Some)
                .map_err(|error| EnvError::StorageReadError(format!("{key}: {error}"))),
            Err(error) if error.kind() == ErrorKind::NotFound => Ok(None),
            Err(error) => Err(EnvError::StorageReadError(format!("{key}: {error}"))),
        }
    }

    fn write_storage<T: Serialize>(key: &str, value: Option<&T>) -> Result<(), EnvError> {
        let path = storage_path(key)?;
        let write_error = |error: std::io::Error| EnvError::StorageWriteError(format!("{key}: {error}"));
        match value {
            Some(value) => {
                let staged = path.with_extension("json.tmp");
                fs::write(&staged, serde_json::to_vec(value)?).map_err(write_error)?;
                fs::rename(&staged, &path).map_err(write_error)
            }
            None => match fs::remove_file(&path) {
                Err(error) if error.kind() != ErrorKind::NotFound => Err(write_error(error)),
                _ => Ok(()),
            },
        }
    }
}

fn storage_path(key: &str) -> Result<PathBuf, EnvError> {
    let dir = STORAGE_DIR.get().ok_or(EnvError::StorageUnavailable)?;
    Ok(dir.join(format!("{key}.json")))
}

fn spawn_on_frame_thread<F: Future<Output = ()> + 'static>(future: F) {
    SPAWNER.with(|slot| {
        slot.borrow()
            .as_ref()
            .expect("core must be driven from the thread that called FrameExecutor::install")
            .spawn_local(future)
            .expect("the frame executor outlives core");
    });
}

struct InFlight;

impl InFlight {
    fn start() -> Self {
        FETCHES_IN_FLIGHT.fetch_add(1, Ordering::Relaxed);
        FETCHES_STARTED.fetch_add(1, Ordering::Relaxed);
        Self
    }
}

impl Drop for InFlight {
    fn drop(&mut self) {
        FETCHES_IN_FLIGHT.fetch_sub(1, Ordering::Relaxed);
    }
}

/// Runs on a worker thread, so it may block.
fn http_round_trip(request: Request<Option<String>>) -> Result<Vec<u8>, String> {
    let agent = AGENT.get_or_init(|| {
        ureq::Agent::config_builder()
            .timeout_global(Some(FETCH_TIMEOUT))
            .build()
            .into()
    });
    let (parts, body) = request.into_parts();
    let response = match body {
        Some(body) => agent.run(Request::from_parts(parts, body)),
        None => agent.run(Request::from_parts(parts, ())),
    };
    response
        .map_err(|error| error.to_string())?
        .body_mut()
        .with_config()
        .limit(MAX_RESPONSE_BYTES)
        .read_to_vec()
        .map_err(|error| error.to_string())
}

impl Env for CliEnv {
    fn fetch<IN: Serialize + 'static, OUT: for<'de> Deserialize<'de> + 'static>(
        request: Request<IN>,
    ) -> TryEnvFuture<OUT> {
        let (parts, body) = request.into_parts();
        let body = match serde_json::to_string(&body) {
            Ok(body) if body != "null" && parts.method != Method::GET => Some(body),
            Ok(_) => None,
            Err(error) => return future::err(EnvError::from(error)).boxed_env(),
        };
        let url = parts.uri.to_string();
        let request = Request::from_parts(parts, body);
        let (tx, rx) = oneshot::channel();
        let in_flight = InFlight::start();
        thread::spawn(move || {
            // The receiver is gone when core dropped the request, which is not an error.
            let _ = tx.send(http_round_trip(request));
        });
        async move {
            let _in_flight = in_flight;
            let bytes = rx
                .await
                .map_err(|_| EnvError::Fetch(format!("{url}: the request thread died")))?
                .map_err(|error| EnvError::Fetch(format!("{url}: {error}")))?;
            serde_json::from_slice(&bytes).map_err(|error| EnvError::Fetch(format!("{url}: {error}")))
        }
        .boxed_env()
    }

    fn get_storage<T: for<'de> Deserialize<'de> + 'static>(key: &str) -> TryEnvFuture<Option<T>> {
        future::ready(Self::read_storage(key)).boxed_env()
    }

    fn set_storage<T: Serialize>(key: &str, value: Option<&T>) -> TryEnvFuture<()> {
        future::ready(Self::write_storage(key, value)).boxed_env()
    }

    fn exec_concurrent<F: Future<Output = ()> + 'static>(future: F) {
        spawn_on_frame_thread(future);
    }

    fn exec_sequential<F: Future<Output = ()> + 'static>(future: F) {
        SEQUENTIAL.with(|slot| {
            slot.borrow()
                .as_ref()
                .expect("core must be driven from the thread that called FrameExecutor::install")
                .unbounded_send(future.boxed_local())
                .expect("the frame executor outlives core");
        });
    }

    fn now() -> DateTime<Utc> {
        Utc::now()
    }

    fn flush_analytics() -> EnvFuture<'static, ()> {
        future::ready(()).boxed_env()
    }

    fn analytics_context(
        _ctx: &Ctx,
        _streaming_server: &StreamingServer,
        _path: &str,
    ) -> serde_json::Value {
        serde_json::Value::Null
    }

    #[cfg(debug_assertions)]
    fn log(message: String) {
        if std::env::var_os("STREMIO_DEBUG").is_some() {
            eprintln!("[core] {message}");
        }
    }
}
