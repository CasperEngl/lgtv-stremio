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

**Direct link**:
A stream reached by an ordinary HTTPS address that serves the file itself.
_Avoid_: URL stream, HTTP stream

**Cached stream**:
A stream whose file the debrid service already holds, so its direct link plays at once.
_Avoid_: Instant stream, available stream

**Release name**:
The text a stream carries about itself: its title, description and filename. It is the only description of a stream before the file is opened, and it is often incomplete or wrong.
_Avoid_: Label, tags, metadata

**Probe**:
Opening a stream's file to read which tracks it really contains.
_Avoid_: Scan, inspect, analyse

**Error clip**:
A short silent video an add-on serves in place of the file when it refuses or fails a request, with the reason written in the picture.
_Avoid_: Placeholder, static video

**Safe audio track**:
An audio track in AAC, AC-3 or E-AC-3, the formats every targeted television decodes.
_Avoid_: Compatible track, fallback track

**Risky audio**:
DTS, DTS-HD, DTS:X and TrueHD, which the targeted televisions do not decode.
_Avoid_: Unsupported audio, lossless audio

**Wanted language**:
The language a title's soundtrack must be in for a stream to count as playable, normally the title's original language.
_Avoid_: Preferred language, default language

**Playable stream**:
A cached stream whose probe finds a safe audio track in the wanted language.
_Avoid_: Good stream, valid stream
