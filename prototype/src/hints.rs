//! What a stream says about itself. Add-ons carry no codec fields, so the only description
//! before opening the file is the release name in the stream's title and filename.

use std::fmt;

#[derive(Debug, Default, PartialEq, Eq)]
pub struct Hints {
    pub container: Option<&'static str>,
    pub resolution: Option<&'static str>,
    pub video: Option<&'static str>,
    pub hdr: Option<&'static str>,
    pub audio: Option<&'static str>,
}

const CONTAINERS: &[(&str, &str)] = &[
    ("mkv", "mkv"),
    ("mp4", "mp4"),
    ("m4v", "mp4"),
    ("avi", "avi"),
    ("m3u8", "hls"),
    ("ts", "mpegts"),
    ("webm", "webm"),
];

const RESOLUTIONS: &[(&str, &str)] = &[
    ("2160p", "2160p"),
    ("4k", "2160p"),
    ("uhd", "2160p"),
    ("1080p", "1080p"),
    ("720p", "720p"),
    ("480p", "480p"),
];

const VIDEO: &[(&str, &str)] = &[
    ("hevc", "HEVC"),
    ("x265", "HEVC"),
    ("h265", "HEVC"),
    ("av1", "AV1"),
    ("vp9", "VP9"),
    ("x264", "H.264"),
    ("h264", "H.264"),
    ("avc", "H.264"),
];

const HDR: &[(&str, &str)] = &[
    ("dv", "Dolby Vision"),
    ("dovi", "Dolby Vision"),
    ("dolbyvision", "Dolby Vision"),
    ("hdr10plus", "HDR10+"),
    ("hdr10", "HDR10"),
    ("hdr", "HDR"),
];

// Ordered so the codec a television may refuse wins over a compatibility track beside it.
const AUDIO: &[(&str, &str)] = &[
    ("truehd", "TrueHD"),
    ("dtshd", "DTS-HD"),
    ("dtsx", "DTS:X"),
    ("dts", "DTS"),
    ("flac", "FLAC"),
    ("opus", "Opus"),
    ("eac3", "E-AC-3"),
    ("ddp", "E-AC-3"),
    ("ddp5", "E-AC-3"),
    ("atmos", "E-AC-3"),
    ("ac3", "AC-3"),
    ("dd5", "AC-3"),
    ("aac", "AAC"),
];

impl Hints {
    /// Reads `texts` as release names. `file` is a filename or URL whose extension names the
    /// container.
    pub fn parse(texts: &[&str], file: Option<&str>) -> Self {
        let normalized = texts
            .join(" ")
            .to_lowercase()
            .replace("h.26", "h26")
            .replace("dts-hd", "dtshd")
            .replace("dts:x", "dtsx")
            .replace("dts-x", "dtsx")
            .replace("e-ac-3", "eac3")
            .replace("e-ac3", "eac3")
            .replace("dd+", "ddp")
            .replace("hdr10+", "hdr10plus")
            .replace("dolby vision", "dolbyvision");
        let tokens: Vec<&str> = normalized
            .split(|c: char| !c.is_ascii_alphanumeric())
            .filter(|token| !token.is_empty())
            .collect();
        let first = |table: &[(&str, &'static str)]| {
            table
                .iter()
                .find(|(needle, _)| tokens.contains(needle))
                .map(|(_, label)| *label)
        };
        let extension = file.and_then(|file| {
            let path = file.split(['?', '#']).next().unwrap_or(file);
            let (_, extension) = path.rsplit_once('.')?;
            let extension = extension.to_lowercase();
            CONTAINERS
                .iter()
                .find(|(needle, _)| *needle == extension)
                .map(|(_, label)| *label)
        });
        // "TS" in a release name means a telesync, so only an extension may name MPEG-TS.
        let named_container = CONTAINERS
            .iter()
            .find(|(needle, _)| *needle != "ts" && tokens.contains(needle))
            .map(|(_, label)| *label);
        Self {
            container: extension.or(named_container),
            resolution: first(RESOLUTIONS),
            video: first(VIDEO),
            hdr: first(HDR),
            audio: first(AUDIO),
        }
    }
}

impl fmt::Display for Hints {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let parts = [self.container, self.resolution, self.video, self.hdr, self.audio];
        let named: Vec<&str> = parts.into_iter().flatten().collect();
        if named.is_empty() {
            f.write_str("nothing stated")
        } else {
            f.write_str(&named.join(" · "))
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn reads_a_remux_release_name() {
        let hints = Hints::parse(
            &["Movie.2021.2160p.UHD.BluRay.REMUX.DV.HDR.HEVC.TrueHD.7.1.Atmos-GRP"],
            Some("Movie.2021.2160p.REMUX.mkv"),
        );
        assert_eq!(
            hints,
            Hints {
                container: Some("mkv"),
                resolution: Some("2160p"),
                video: Some("HEVC"),
                hdr: Some("Dolby Vision"),
                audio: Some("TrueHD"),
            }
        );
    }

    #[test]
    fn reads_punctuated_codec_names() {
        let hints = Hints::parse(&["Show S01E02 1080p WEB-DL DD+5.1 H.264"], None);
        assert_eq!(hints.video, Some("H.264"));
        assert_eq!(hints.audio, Some("E-AC-3"));
        assert_eq!(hints.container, None);
    }

    #[test]
    fn takes_the_container_from_a_url_and_ignores_its_query() {
        let hints = Hints::parse(&[], Some("https://host.example/v/file.MP4?token=a.b"));
        assert_eq!(hints.container, Some("mp4"));
    }

    #[test]
    fn does_not_read_a_telesync_tag_as_a_container() {
        let hints = Hints::parse(&["Movie 2024 TS x264 AAC"], None);
        assert_eq!(hints.container, None);
        assert_eq!(hints.video, Some("H.264"));
    }

    #[test]
    fn does_not_find_codecs_inside_other_words() {
        let hints = Hints::parse(&["Advice for the Hdrive Tsunami"], None);
        assert_eq!(hints, Hints::default());
    }
}
