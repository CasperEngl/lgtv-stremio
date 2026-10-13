# Stremio on LG webOS

A Stremio client for LG televisions that draws its own interface and hands video to the set's decoder. This glossary covers how a title becomes something the television can play.

## Language

**Add-on**:
A web service the Stremio account has installed, which answers requests for catalogues, title details or streams.
_Avoid_: Plugin, provider, source

**Catalogue**:
A browsable list of titles that one add-on offers, such as popular films.
_Avoid_: Feed, shelf, list

**Stream**:
One way to play a title, as returned by an add-on: a release of the film or episode plus how to reach it.
_Avoid_: Source, link, result

**Debrid stream**:
A stream whose file comes from a torrent but is delivered by a debrid service over a direct link, so the television never speaks the torrent protocol.
_Avoid_: Torrent stream, RD stream

**Peer-to-peer stream**:
A stream given as a bare torrent, playable only through a separate streaming server that joins the swarm.
_Avoid_: Torrent stream, magnet

**Direct link**:
A stream reached by an ordinary HTTPS address that serves the file itself.
_Avoid_: URL stream, HTTP stream

**Cached stream**:
A debrid stream whose file the debrid service already holds, so its direct link plays at once.
_Avoid_: Instant stream, available stream

**Release name**:
The text a stream carries about itself: its title, description and filename. It is the only description of a stream before the file is opened, and it is often incomplete or wrong.
_Avoid_: Label, tags, metadata

**Uncached stream**:
A debrid stream whose file the debrid service must first download from the swarm before its direct link serves anything.
_Avoid_: Pending stream, download stream

**Probe**:
Opening a stream's file to read which tracks it really contains.
_Avoid_: Scan, inspect, analyse

**Error clip**:
A short silent video an add-on serves in place of the file when it refuses or fails a request, with the reason written in the picture.
_Avoid_: Placeholder, static video

**Safe audio track**:
An audio track in AAC, AC-3 or E-AC-3 with no more channels than this television takes. The set's own codec table can take a format away or lower its channel count, and can never add a format.
_Avoid_: Compatible track, fallback track

**Risky audio**:
DTS, DTS-HD, DTS:X and TrueHD. A track in one of them is never a safe audio track, whatever the television's codec table lists.
_Avoid_: Unsupported audio, lossless audio

**Refusal**:
The television turning a stream down as playback starts, whatever its probe found.
_Avoid_: Load error, playback failure

**Wanted language**:
The language a title's soundtrack must be in for a stream to count as playable, normally the title's original language.
_Avoid_: Preferred language, default language

**Playable stream**:
A cached stream whose probe finds a safe audio track in the wanted language.
_Avoid_: Good stream, valid stream
