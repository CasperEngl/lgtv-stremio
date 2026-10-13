//! The host side of stremio-core on the television: the command-line prototype's frame executor
//! (`prototype/src/env.rs`) with the desktop HTTP and TLS stack replaced by upstream's libcurl
//! client, `plx_net`.
//!
//! PROTOTYPE: storage is in memory, so nothing survives a relaunch.

use std::cell::RefCell;
use std::collections::HashMap;
use std::sync::Mutex;

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

type SequentialJob = LocalBoxFuture<'static, ()>;

thread_local! {
    static SPAWNER: RefCell<Option<LocalSpawner>> = const { RefCell::new(None) };
    static SEQUENTIAL: RefCell<Option<mpsc::UnboundedSender<SequentialJob>>> = const { RefCell::new(None) };
}

static STORAGE: Mutex<Option<HashMap<String, String>>> = Mutex::new(None);

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
}

pub enum TvEnv {}

/// Runs on a worker thread, so it may block. `plx_net` follows redirects and verifies the peer
/// against the television's trust store.
fn http_round_trip(url: &str, method: &Method, body: Option<String>) -> Result<Vec<u8>, String> {
    let headers = match body {
        Some(_) => vec!["Content-Type: application/json".to_owned()],
        None => Vec::new(),
    };
    let response = plx_net::net::request(
        url,
        &headers,
        method.as_str(),
        body.as_deref().map(str::as_bytes),
        plx_net::net::API,
        true,
        None,
        None,
    )
    .ok_or_else(|| "the request failed".to_owned())?;
    if !response.ok() {
        return Err(format!("status {}", response.status));
    }
    Ok(response.body)
}

impl Env for TvEnv {
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
        let (tx, rx) = oneshot::channel();
        let worker_url = url.clone();
        plx_base::task::spawn("stremio-fetch", move || {
            // The receiver is gone when core dropped the request, which is not an error.
            let _ = tx.send(http_round_trip(&worker_url, &parts.method, body));
        });
        async move {
            let bytes = rx
                .await
                .map_err(|_| EnvError::Fetch(format!("{url}: the request thread died")))?
                .map_err(|error| EnvError::Fetch(format!("{url}: {error}")))?;
            serde_json::from_slice(&bytes).map_err(|error| EnvError::Fetch(format!("{url}: {error}")))
        }
        .boxed_env()
    }

    fn get_storage<T: for<'de> Deserialize<'de> + 'static>(key: &str) -> TryEnvFuture<Option<T>> {
        let stored = STORAGE.lock().unwrap().as_ref().and_then(|map| map.get(key).cloned());
        let value = match stored {
            Some(json) => serde_json::from_str(&json)
                .map(Some)
                .map_err(|error| EnvError::StorageReadError(format!("{key}: {error}"))),
            None => Ok(None),
        };
        future::ready(value).boxed_env()
    }

    fn set_storage<T: Serialize>(key: &str, value: Option<&T>) -> TryEnvFuture<()> {
        let json = match value.map(serde_json::to_string).transpose() {
            Ok(json) => json,
            Err(error) => return future::err(EnvError::from(error)).boxed_env(),
        };
        let mut storage = STORAGE.lock().unwrap();
        let map = storage.get_or_insert_with(HashMap::new);
        match json {
            Some(json) => map.insert(key.to_owned(), json),
            None => map.remove(key),
        };
        future::ready(Ok(())).boxed_env()
    }

    fn exec_concurrent<F: Future<Output = ()> + 'static>(future: F) {
        SPAWNER.with(|slot| {
            slot.borrow()
                .as_ref()
                .expect("core must be driven from the thread that called FrameExecutor::install")
                .spawn_local(future)
                .expect("the frame executor outlives core");
        });
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

    fn analytics_context(_ctx: &Ctx, _streaming_server: &StreamingServer, _path: &str) -> serde_json::Value {
        serde_json::Value::Null
    }

    #[cfg(debug_assertions)]
    fn log(message: String) {
        plx_base::eventlog::log(&format!("[core] {message}"));
    }
}
