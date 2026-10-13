//! Start upstream's player on a link Plex did not choose: "Cut A" of the seam findings
//! (`docs/research/plex-seam.md` on the `research/plex-seam` branch). Every call is an existing
//! public function of `plx_media`; a signature change upstream is a compile error here.

use plx_media::player::adapter::PlayerAdapter;
use plx_media::route::PlaybackSession;

/// What a stream pick hands the player. The codecs come from opening the file, since an add-on
/// stream carries none.
pub struct PlayRequest<'a> {
    /// An `https` link with its port written in: the player's URL parser fills a missing port
    /// with Plex's 32400.
    pub url: &'a str,
    pub video_codec: &'a str,
    pub audio_codec: &'a str,
    pub fps: f64,
    pub resume_ns: i64,
    /// `-1` feeds the track that matches `audio_codec`.
    pub audio_track: i32,
    /// `-1` is off.
    pub subtitle_track: i32,
}

/// `false` when the television refused the declaration or the engine did not start.
pub fn start(ps: &mut PlaybackSession, pa: &mut PlayerAdapter, request: &PlayRequest) -> bool {
    plx_media::route::set_url(ps, request.url);
    let declared = plx_media::route::set_stream_declaration(
        ps,
        request.video_codec,
        request.audio_codec,
        request.fps,
        plx_data::metadata::Dovi::default(),
        false,
    );
    if !declared {
        return false;
    }
    if request.resume_ns > 0 {
        let _ = plx_media::player::begin_resume(ps, request.resume_ns);
    }
    plx_media::player::set_audio_track(request.audio_track);
    plx_media::player::request_subtitle(request.subtitle_track);
    plx_media::player::start_bufferfeed(ps, pa)
}
