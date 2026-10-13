//! Opens a stream URL with `ffprobe` to read what the file actually contains, as opposed to
//! what its release name claims.

use std::process::Command;

use serde::Deserialize;

const PROBE_TIMEOUT_SECS: &str = "40";

#[derive(Deserialize)]
struct Report {
    #[serde(default)]
    streams: Vec<Track>,
    format: Option<Format>,
}

#[derive(Deserialize)]
struct Format {
    format_name: String,
}

#[derive(Deserialize)]
struct Track {
    codec_type: Option<String>,
    codec_name: Option<String>,
    profile: Option<String>,
    width: Option<u32>,
    height: Option<u32>,
    pix_fmt: Option<String>,
    channels: Option<u32>,
    #[serde(default)]
    side_data_list: Vec<SideData>,
    #[serde(default)]
    tags: Tags,
}

#[derive(Deserialize, Default)]
struct Tags {
    language: Option<String>,
}

#[derive(Deserialize)]
struct SideData {
    dv_profile: Option<u32>,
}

/// One line describing the container and every video and audio track, or why it couldn't be read.
pub fn describe(url: &str) -> Result<String, String> {
    let output = Command::new("timeout")
        .args([PROBE_TIMEOUT_SECS, "ffprobe", "-v", "error", "-of", "json"])
        .args(["-show_format", "-show_streams", "-rw_timeout", "20000000"])
        .arg(url)
        .output()
        .map_err(|error| format!("could not run ffprobe: {error}"))?;
    if !output.status.success() {
        return Err(failure_reason(&String::from_utf8_lossy(&output.stderr), url));
    }
    let report: Report =
        serde_json::from_slice(&output.stdout).map_err(|error| format!("unreadable ffprobe output: {error}"))?;
    Ok(summarize(&report))
}

/// ffprobe's last complaint, without the link it quotes: links can carry account tokens.
fn failure_reason(stderr: &str, url: &str) -> String {
    let reason = stderr.lines().last().unwrap_or("timed out").replace(url, "");
    reason.trim().trim_start_matches(':').trim().to_owned()
}

fn summarize(report: &Report) -> String {
    let container = report
        .format
        .as_ref()
        .map_or("unknown container", |format| format.format_name.as_str());
    let mut video = Vec::new();
    let mut audio = Vec::new();
    for track in &report.streams {
        let codec = track.codec_name.as_deref().unwrap_or("unknown");
        match track.codec_type.as_deref() {
            Some("video") => {
                let mut line = codec.to_owned();
                if let Some(profile) = &track.profile {
                    line.push_str(&format!(" {profile}"));
                }
                if let (Some(width), Some(height)) = (track.width, track.height) {
                    line.push_str(&format!(" {width}x{height}"));
                }
                if let Some(pix_fmt) = &track.pix_fmt {
                    line.push_str(&format!(" {pix_fmt}"));
                }
                if let Some(dv) = track.side_data_list.iter().find_map(|side| side.dv_profile) {
                    line.push_str(&format!(" Dolby Vision profile {dv}"));
                }
                video.push(line);
            }
            Some("audio") => {
                let channels = track.channels.map_or(String::new(), |n| format!(" {n}ch"));
                let language = track.tags.language.as_ref().map_or(String::new(), |code| format!(" {code}"));
                audio.push(format!("{codec}{channels}{language}"));
            }
            _ => {}
        }
    }
    format!(
        "{container} | video: {} | audio: {}",
        if video.is_empty() { "none".to_owned() } else { video.join(", ") },
        if audio.is_empty() { "none".to_owned() } else { audio.join(", ") },
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn failure_reason_leaves_the_link_out() {
        let url = "https://host.example/playback/secret-token/file.mkv";
        assert_eq!(failure_reason(&format!("{url}: Connection timed out\n"), url), "Connection timed out");
        assert_eq!(failure_reason("", url), "timed out");
    }

    #[test]
    fn summarizes_tracks_and_dolby_vision() {
        let report: Report = serde_json::from_str(
            r#"{"format":{"format_name":"matroska,webm"},"streams":[
                {"codec_type":"video","codec_name":"hevc","profile":"Main 10","width":3840,"height":2160,
                 "pix_fmt":"yuv420p10le","side_data_list":[{"dv_profile":8}]},
                {"codec_type":"audio","codec_name":"truehd","channels":8,"tags":{"language":"eng"}},
                {"codec_type":"audio","codec_name":"ac3","channels":6},
                {"codec_type":"subtitle","codec_name":"subrip"}]}"#,
        )
        .unwrap();
        assert_eq!(
            summarize(&report),
            "matroska,webm | video: hevc Main 10 3840x2160 yuv420p10le Dolby Vision profile 8 | audio: truehd 8ch eng, ac3 6ch"
        );
    }
}
