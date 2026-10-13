#!/usr/bin/env bash
# Host-side reproduction for lgtv-stremio ticket 43: what channel count does an FFmpeg built with
# the app's component list report, against what a desktop ffprobe (with audio decoders) reports?
#
# Needs: curl, tar, gcc, make, zlib headers, and a desktop ffmpeg/ffprobe with the eac3, ac3, aac,
# dca and truehd codecs. No television, no stream link. Everything lands under $WORK.
#
#   run-repro.sh [WORK]        # default /tmp/t43
#
# The FFmpeg version, its checksum and the component list are copied from ci/build-ffmpeg.sh. Two
# differences from the shipped build, neither of which touches a parser or a demuxer: this is a
# native build for the host's processor (not 32-bit ARM), and --disable-x86asm is added so it
# builds without nasm.
set -euo pipefail

WORK=${1:-/tmp/t43}
HERE=$(cd "$(dirname "$0")" && pwd)
VERSION=9.0
SHA256=7f607a00dd0d28a729d5a4811205812eef01cf6ef6155025febb6f36a9062d52
mkdir -p "$WORK"/{dl,src,build,samples,fx,bin}

# 1. The pinned FFmpeg source.
if [ ! -d "$WORK/src/ffmpeg-$VERSION" ]; then
  curl -sSfL "https://ffmpeg.org/releases/ffmpeg-$VERSION.tar.xz" -o "$WORK/dl/ffmpeg-$VERSION.tar.xz"
  echo "$SHA256  $WORK/dl/ffmpeg-$VERSION.tar.xz" | sha256sum -c -
  tar -xf "$WORK/dl/ffmpeg-$VERSION.tar.xz" -C "$WORK/src"
fi

# 2. Build it with the app's component list. The libraries are used from the build tree.
if [ ! -e "$WORK/build/libavformat/libavformat-plx.so" ]; then
  (cd "$WORK/build" && "$WORK/src/ffmpeg-$VERSION/configure" --disable-x86asm \
    --build-suffix=-plx --enable-shared --disable-static --enable-pic \
    --extra-cflags='-Dstatic_assert=_Static_assert' \
    --disable-programs --disable-doc --disable-avdevice --disable-avfilter \
    --disable-network --disable-swresample --disable-debug --enable-small \
    --disable-everything --disable-autodetect --enable-zlib \
    --enable-demuxer=matroska,mov,mpegts,h264,hevc \
    --enable-parser=h264,hevc,aac,ac3,dvdsub,dvbsub \
    --enable-bsf=h264_mp4toannexb,hevc_mp4toannexb,extract_extradata \
    --enable-decoder=pgssub,dvdsub,dvbsub,ass,srt,subrip,text,mov_text,webvtt \
    --enable-protocol=file --enable-encoder=mpeg1video --enable-muxer=mpegts >configure.log 2>&1 &&
    make -j"$(nproc)" >make.log 2>&1)
fi
B=$WORK/build
gcc -O1 -Wall -I"$B" -I"$WORK/src/ffmpeg-$VERSION" "$HERE/chprobe.c" -o "$WORK/bin/chprobe" \
  -L"$B/libavformat" -L"$B/libavcodec" -L"$B/libavutil" -lavformat-plx -lavcodec-plx -lavutil-plx \
  -Wl,-rpath,"$B/libavformat:$B/libavcodec:$B/libavutil"

# 3. Fixtures. E-AC-3 comes from FFmpeg's own test suite, because FFmpeg's E-AC-3 encoder cannot
#    write a dependent substream; the rest is a generated tone.
for n in the_great_wall_7.1 csi_miami_5.1_256_spx_small csi_miami_stereo_128_spx_small; do
  [ -s "$WORK/samples/$n.eac3" ] || curl -sSfL "https://fate-suite.ffmpeg.org/eac3/$n.eac3" -o "$WORK/samples/$n.eac3"
done
cd "$WORK/fx"
ff() { ffmpeg -hide_banner -loglevel error -y "$@"; }
tone() { ff -f lavfi -i "sine=frequency=440:duration=2" "$@"; }
for n in the_great_wall_7.1 csi_miami_5.1_256_spx_small csi_miami_stereo_128_spx_small; do
  ff -i "$WORK/samples/$n.eac3" -c copy "eac3_$n.mkv"
  ff -i "$WORK/samples/$n.eac3" -c copy "eac3_$n.mp4"
done
tone -ac 6 -c:a ac3 -b:a 384k ac3_5.1.mkv
tone -ac 2 -c:a ac3 -b:a 192k ac3_2.0.mkv
tone -ac 2 -c:a aac aac_2.0.mkv
tone -ac 6 -c:a aac aac_5.1.mkv
tone -ac 8 -c:a aac aac_7.1.mkv
for n in ac3_5.1 ac3_2.0 aac_2.0 aac_5.1 aac_7.1; do ff -i "$n.mkv" -c copy "$n.mp4"; done
tone -ac 6 -c:a dca -strict -2 dts_5.1.mkv
tone -ac 6 -c:a truehd -strict -2 truehd_5.1.mkv

# 4. The two readings, side by side.
echo "=== desktop ffprobe ($(ffprobe -version | head -1 | cut -d' ' -f3)), audio decoders present"
for f in *.mkv *.mp4; do
  printf '%s: ' "$f"
  ffprobe -v error -select_streams a -show_entries stream=codec_name,channels,channel_layout -of csv=p=0 "$f"
done
echo "=== FFmpeg $VERSION with the app's component list"
"$WORK/bin/chprobe" *.mkv *.mp4
