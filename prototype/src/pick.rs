//! Choosing what to play: which streams are worth opening, in what order, and which audio
//! track of an opened file a television can decode.

use crate::hints::Hints;

/// Audio an LG set decodes whatever its model year. DTS and TrueHD are not on the list:
/// the 2020-2022 and 2025 sets refuse DTS, and nothing downstream re-encodes.
const SAFE_AUDIO: &[&str] = &["eac3", "ac3", "aac"];

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AudioTrack {
    pub codec: String,
    pub channels: u32,
    pub language: Option<String>,
}

impl AudioTrack {
    fn is_untagged(&self) -> bool {
        matches!(self.language.as_deref(), None | Some("und"))
    }
}

/// Audio that neither LG's 2020-2022 nor its 2025 sets decode, as release names spell it.
pub fn is_risky_audio_label(label: &str) -> bool {
    matches!(label, "DTS" | "DTS-HD" | "DTS:X" | "TrueHD")
}

/// The position, among the file's audio tracks, of the safe track in `language` with the most
/// channels. A file that tags no track at all is taken to be in the wanted language.
pub fn safe_track(tracks: &[AudioTrack], language: &str) -> Option<usize> {
    let nothing_tagged = tracks.iter().all(AudioTrack::is_untagged);
    tracks
        .iter()
        .enumerate()
        .filter(|(_, track)| {
            let in_language = match &track.language {
                Some(tag) if !track.is_untagged() => tag.eq_ignore_ascii_case(language),
                _ => nothing_tagged,
            };
            in_language && SAFE_AUDIO.contains(&track.codec.as_str())
        })
        // `max_by_key` keeps the last of equals, so compare positions in reverse to keep the
        // first: a later track with the same layout is usually a commentary.
        .max_by_key(|(position, track)| {
            let codec_rank = SAFE_AUDIO.iter().rev().position(|codec| *codec == track.codec);
            (track.channels, codec_rank, std::cmp::Reverse(*position))
        })
        .map(|(position, _)| position)
}

/// Where a stream sorts among the ones worth opening; higher opens first. `None` leaves it out.
///
/// Sharpest picture first, then streams whose name promises safe audio ahead of ones that say
/// nothing and ones that name DTS or TrueHD, then the larger file.
pub fn rank(hints: &Hints, size_bytes: Option<u64>, max_bytes: u64) -> Option<(u8, u8, u64)> {
    if hints.container == Some("avi") || size_bytes.is_some_and(|size| size > max_bytes) {
        return None;
    }
    let picture = match hints.resolution {
        Some("2160p") => 3,
        Some("1080p") => 2,
        Some("720p") => 1,
        _ => 0,
    };
    let audio = match hints.audio {
        Some(label) if is_risky_audio_label(label) => 0,
        Some(_) => 2,
        None => 1,
    };
    Some((picture, audio, size_bytes.unwrap_or(0)))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn track(codec: &str, channels: u32, language: Option<&str>) -> AudioTrack {
        AudioTrack {
            codec: codec.to_owned(),
            channels,
            language: language.map(str::to_owned),
        }
    }

    #[test]
    fn takes_the_surround_track_over_lossless_and_stereo() {
        let tracks = [
            track("truehd", 8, Some("eng")),
            track("ac3", 6, Some("eng")),
            track("ac3", 2, Some("eng")),
        ];
        assert_eq!(safe_track(&tracks, "eng"), Some(1));
    }

    #[test]
    fn refuses_a_file_whose_only_safe_track_is_a_dub() {
        let tracks = [track("dts", 6, Some("eng")), track("ac3", 6, Some("cze"))];
        assert_eq!(safe_track(&tracks, "eng"), None);
    }

    #[test]
    fn prefers_eac3_and_then_the_earlier_track() {
        let tracks = [
            track("ac3", 6, Some("eng")),
            track("eac3", 6, Some("eng")),
            track("eac3", 6, Some("eng")),
        ];
        assert_eq!(safe_track(&tracks, "eng"), Some(1));
    }

    #[test]
    fn trusts_a_file_that_tags_nothing_but_not_a_stray_untagged_track() {
        assert_eq!(safe_track(&[track("aac", 2, None)], "eng"), Some(0));
        let mixed = [track("dts", 6, Some("ita")), track("ac3", 6, None)];
        assert_eq!(safe_track(&mixed, "eng"), None);
    }

    #[test]
    fn ranks_picture_then_promised_audio_then_size() {
        let gb = 1_000_000_000;
        let rank_of = |name: &str, size| rank(&Hints::parse(&[name], None), Some(size), 30 * gb);
        let uhd_truehd = rank_of("Film 2160p HEVC TrueHD", 20 * gb);
        let uhd_eac3 = rank_of("Film 2160p HEVC DDP5.1", 15 * gb);
        let hd_eac3 = rank_of("Film 1080p H.264 DDP5.1", 25 * gb);
        assert!(uhd_eac3 > uhd_truehd);
        assert!(uhd_truehd > hd_eac3);
        assert_eq!(rank_of("Film 2160p REMUX", 80 * gb), None);
        assert_eq!(rank(&Hints::parse(&["Film"], Some("film.avi")), None, 30 * gb), None);
    }
}
