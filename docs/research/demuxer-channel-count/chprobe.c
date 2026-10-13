/* Host-side reproduction for "Why does the bundled demuxer report 4 channels for a 7.1 E-AC-3
 * track?" (lgtv-stremio ticket 43).
 *
 * Linked against an FFmpeg 9.0 built with the app's component list (ci/build-ffmpeg.sh), it opens
 * a file the way the app's demuxer does and prints, for each audio track:
 *
 *   header=  nb_channels after avformat_open_input: what the container's own header led to
 *   probed=  nb_channels after avformat_find_stream_info: the number the app reads today
 *   then every E-AC-3 / AC-3 syncframe of the track's first packet, read by hand, and
 *   counted= the channel count worked out from those frames the way FFmpeg's own E-AC-3 decoder
 *            does (libavcodec/ac3dec.c): the independent substream's speakers plus every location
 *            the dependent substream's channel map names.
 *
 * Build and run: see run-repro.sh beside this file.
 */
#include <stdio.h>
#include <stdint.h>
#include <libavformat/avformat.h>
#include <libavcodec/avcodec.h>

/* Location bits, numbered as in the E-AC-3 `chanmap` field (ATSC A/52 Annex E, table E2.5), bit 0
 * first. Each entry is how many speakers the location stands for. */
static const int LOC_SPEAKERS[16] = { 1, 1, 1, 1, 1, 2, 2, 1, 1, 2, 2, 2, 1, 2, 1, 1 };
enum { L = 1 << 0, C = 1 << 1, R = 1 << 2, LS = 1 << 3, RS = 1 << 4, CS = 1 << 7, LFE = 1 << 15 };
/* Speakers of each `acmod`, in the same bits. A single surround is the back centre, as in FFmpeg's
 * ff_ac3_channel_layout_tab. */
static const int ACMOD_LOCS[8] = { L | R, C, L | R, L | C | R, L | R | CS, L | C | R | CS,
                                   L | R | LS | RS, L | C | R | LS | RS };
static const int ACMOD_CHANNELS[8] = { 2, 1, 2, 3, 3, 4, 4, 5 };
static const int AC3_FRAME_WORDS_48K[19] = { 64, 80, 96, 112, 128, 160, 192, 224, 256, 320,
                                             384, 448, 512, 640, 768, 896, 1024, 1152, 1280 };

static unsigned bits(const uint8_t *p, int *pos, int n)
{
    unsigned v = 0;
    for (int i = 0; i < n; i++, (*pos)++)
        v = (v << 1) | ((p[*pos >> 3] >> (7 - (*pos & 7))) & 1);
    return v;
}

static int count_locs(int locs)
{
    int n = 0;
    for (int i = 0; i < 16; i++)
        if (locs & (1 << i))
            n += LOC_SPEAKERS[i];
    return n;
}

/* Walk the syncframes of one packet; return the counted channels, or -1 if it is not AC-3. */
static int walk_packet(const uint8_t *buf, int size)
{
    int off = 0, locs = 0, frames = 0;
    while (size - off >= 8 && buf[off] == 0x0b && buf[off + 1] == 0x77) {
        const uint8_t *p = buf + off;
        int bsid = p[5] >> 3, pos = 16, frame_size;
        if (bsid <= 10) { /* plain AC-3: one frame, no substreams */
            int fscod = p[4] >> 6, frmsizecod = p[4] & 0x3f, acmod, lfeon;
            pos = 48;
            acmod = bits(p, &pos, 3);
            if ((acmod & 1) && acmod != 1) pos += 2;
            if (acmod & 4) pos += 2;
            if (acmod == 2) pos += 2;
            lfeon = bits(p, &pos, 1);
            frame_size = fscod == 0 && frmsizecod / 2 < 19 ? AC3_FRAME_WORDS_48K[frmsizecod / 2] * 2 : size - off;
            printf("    frame %d: ac3 acmod=%d lfeon=%d own_channels=%d size=%d\n", frames, acmod, lfeon,
                   ACMOD_CHANNELS[acmod] + lfeon, frame_size);
            locs |= ACMOD_LOCS[acmod] | (lfeon ? LFE : 0);
        } else {
            int strmtyp = bits(p, &pos, 2), substreamid = bits(p, &pos, 3);
            int fscod, acmod, lfeon, chanmape = 0, chanmap = 0;
            frame_size = (bits(p, &pos, 11) + 1) * 2;
            fscod = bits(p, &pos, 2);
            pos += 2; /* fscod2 or numblkscod */
            (void)fscod;
            acmod = bits(p, &pos, 3);
            lfeon = bits(p, &pos, 1);
            pos += 5; /* bsid */
            for (int i = 0; i < (acmod ? 1 : 2); i++) {
                pos += 5; /* dialnorm */
                if (bits(p, &pos, 1)) pos += 8; /* compr */
            }
            if (strmtyp == 1 && (chanmape = bits(p, &pos, 1)))
                chanmap = bits(p, &pos, 16);
            printf("    frame %d: eac3 %s substream=%d acmod=%d lfeon=%d own_channels=%d chanmap=%s0x%04x size=%d\n",
                   frames, strmtyp == 0 ? "independent" : strmtyp == 1 ? "dependent" : "other", substreamid,
                   acmod, lfeon, ACMOD_CHANNELS[acmod] + lfeon, chanmape ? "" : "(absent) ", chanmap, frame_size);
            if (substreamid == 0 && strmtyp != 1)
                locs |= ACMOD_LOCS[acmod] | (lfeon ? LFE : 0);
            else if (substreamid == 0 && strmtyp == 1 && chanmape)
                for (int i = 0; i < 16; i++) /* chanmap's most significant bit is location 0 */
                    if (chanmap & (1 << (15 - i)))
                        locs |= 1 << i;
        }
        frames++;
        if (frame_size <= 0) break;
        off += frame_size;
    }
    return frames ? count_locs(locs) : -1;
}

int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr, "usage: chprobe FILE...\n");
        return 2;
    }
    printf("libavformat %u libavcodec %u libavutil %u\n", avformat_version() >> 16, avcodec_version() >> 16,
           avutil_version() >> 16);
    printf("eac3 decoder: %s, ac3 decoder: %s, aac decoder: %s\n",
           avcodec_find_decoder(AV_CODEC_ID_EAC3) ? "present" : "absent",
           avcodec_find_decoder(AV_CODEC_ID_AC3) ? "present" : "absent",
           avcodec_find_decoder(AV_CODEC_ID_AAC) ? "present" : "absent");
    for (int a = 1; a < argc; a++) {
        AVFormatContext *fmt = NULL;
        int header[64] = { 0 }, seen[64] = { 0 };
        AVPacket *pkt = av_packet_alloc();
        if (avformat_open_input(&fmt, argv[a], NULL, NULL) < 0) {
            printf("%s: open failed\n", argv[a]);
            continue;
        }
        for (unsigned i = 0; i < fmt->nb_streams && i < 64; i++)
            header[i] = fmt->streams[i]->codecpar->ch_layout.nb_channels;
        int rv = avformat_find_stream_info(fmt, NULL);
        printf("%s: format=%s find_stream_info=%d\n", argv[a], fmt->iformat->name, rv);
        for (unsigned i = 0; i < fmt->nb_streams && i < 64; i++) {
            AVCodecParameters *cp = fmt->streams[i]->codecpar;
            if (cp->codec_type != AVMEDIA_TYPE_AUDIO) continue;
            printf("  track #%u codec=%s header=%d probed=%d sr=%d\n", i, avcodec_get_name(cp->codec_id),
                   header[i], cp->ch_layout.nb_channels, cp->sample_rate);
        }
        while (av_read_frame(fmt, pkt) >= 0) {
            unsigned i = pkt->stream_index;
            AVCodecParameters *cp = fmt->streams[i]->codecpar;
            if (i < 64 && !seen[i] && cp->codec_type == AVMEDIA_TYPE_AUDIO &&
                (cp->codec_id == AV_CODEC_ID_EAC3 || cp->codec_id == AV_CODEC_ID_AC3)) {
                seen[i] = 1;
                printf("  track #%u first packet, %d bytes:\n", i, pkt->size);
                printf("    counted=%d\n", walk_packet(pkt->data, pkt->size));
            }
            av_packet_unref(pkt);
        }
        av_packet_free(&pkt);
        avformat_close_input(&fmt);
    }
    return 0;
}
