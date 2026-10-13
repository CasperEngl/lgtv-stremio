//! The same three models the command-line prototype runs (`prototype/src/model.rs`), starting
//! signed out with the official add-ons.

use stremio_core::models::catalog_with_filters::CatalogWithFilters;
use stremio_core::models::ctx::Ctx;
use stremio_core::models::meta_details::MetaDetails;
use stremio_core::runtime::Effects;
use stremio_core::types::events::DismissedEventsBucket;
use stremio_core::types::library::LibraryBucket;
use stremio_core::types::notifications::NotificationsBucket;
use stremio_core::types::profile::Profile;
use stremio_core::types::resource::MetaItemPreview;
use stremio_core::types::search_history::SearchHistoryBucket;
use stremio_core::types::server_urls::ServerUrlsBucket;
use stremio_core::types::streams::StreamsBucket;
use stremio_core::Model;

use crate::env::TvEnv;

#[derive(Model, Clone)]
#[model(TvEnv)]
pub struct TvModel {
    pub ctx: Ctx,
    pub catalog: CatalogWithFilters<MetaItemPreview>,
    pub meta_details: MetaDetails,
}

impl TvModel {
    pub fn signed_out() -> (Self, Effects) {
        let profile = Profile::default();
        let uid = profile.uid();
        let (catalog, catalog_effects) = CatalogWithFilters::<MetaItemPreview>::new(&profile);
        let ctx = Ctx::new(
            profile,
            LibraryBucket::new(uid.clone(), vec![]),
            StreamsBucket::new(uid.clone()),
            ServerUrlsBucket::new::<TvEnv>(uid.clone()),
            NotificationsBucket::new::<TvEnv>(uid.clone(), vec![]),
            SearchHistoryBucket::new(uid.clone()),
            DismissedEventsBucket::new(uid),
        );
        (Self { ctx, catalog, meta_details: MetaDetails::default() }, catalog_effects)
    }
}
