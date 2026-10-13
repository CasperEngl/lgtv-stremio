use stremio_core::constants::{
    LIBRARY_RECENT_STORAGE_KEY, LIBRARY_STORAGE_KEY, PROFILE_STORAGE_KEY,
};
use stremio_core::models::catalog_with_filters::CatalogWithFilters;
use stremio_core::models::ctx::Ctx;
use stremio_core::models::meta_details::MetaDetails;
use stremio_core::runtime::{Effects, EnvError};
use stremio_core::types::events::DismissedEventsBucket;
use stremio_core::types::library::LibraryBucket;
use stremio_core::types::notifications::NotificationsBucket;
use stremio_core::types::profile::Profile;
use stremio_core::types::resource::MetaItemPreview;
use stremio_core::types::search_history::SearchHistoryBucket;
use stremio_core::types::server_urls::ServerUrlsBucket;
use stremio_core::types::streams::StreamsBucket;
use stremio_core::Model;

use crate::env::CliEnv;

#[derive(Model, Clone)]
#[model(CliEnv)]
pub struct CliModel {
    pub ctx: Ctx,
    pub catalog: CatalogWithFilters<MetaItemPreview>,
    pub meta_details: MetaDetails,
}

impl CliModel {
    /// Restores the signed-in profile and library from storage, or starts signed out with the
    /// official add-ons.
    pub fn from_storage() -> Result<(Self, Effects), EnvError> {
        let profile = CliEnv::read_storage::<Profile>(PROFILE_STORAGE_KEY)?.unwrap_or_default();
        let uid = profile.uid();
        let mut library = LibraryBucket::new(uid.clone(), vec![]);
        for key in [LIBRARY_RECENT_STORAGE_KEY, LIBRARY_STORAGE_KEY] {
            if let Some(bucket) = CliEnv::read_storage::<LibraryBucket>(key)? {
                library.merge_bucket(bucket);
            }
        }
        let (catalog, catalog_effects) = CatalogWithFilters::<MetaItemPreview>::new(&profile);
        let ctx = Ctx::new(
            profile,
            library,
            StreamsBucket::new(uid.clone()),
            ServerUrlsBucket::new::<CliEnv>(uid.clone()),
            NotificationsBucket::new::<CliEnv>(uid.clone(), vec![]),
            SearchHistoryBucket::new(uid.clone()),
            DismissedEventsBucket::new(uid),
        );
        let model = Self {
            ctx,
            catalog,
            meta_details: MetaDetails::default(),
        };
        Ok((model, catalog_effects))
    }
}
