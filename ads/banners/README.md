# Server-list banners

Animated banners converted from 962×124 VP9 sources (6.8s, 25fps). All
cycle SURVIVAL → PAYOUTS → EVENTS → the listing's tracking IP.

| Set | For | Tracking IP |
|---|---|---|
| `minex-mss-*` | minecraftsurvivalservers.net | `mss.minex.gg` |
| `minex-mcl-*` | (MCL listing) | `mcl.minex.gg` |
| `minex-mcs-*` | (MCS listing) | `mcs.minex.gg` |
| `minex-ml-halloween-*` | (ML listing) — **Halloween version** | `ml.minex.gg` |

## Pick by the site's upload cap

| Rung | mss | mcl | mcs | fps | Colours |
|---|---|---|---|---|---|
| `hi` | 412 KB | 410 KB | 410 KB | 15 | 256 |
| `mid` | 294 KB | 294 KB | 292 KB | 12 | 160 |
| `lo` | 203 KB | 200 KB | 201 KB | 10 | 96 |
| `tiny` | 153 KB | 155 KB | 154 KB | 8 | 64 |
| `native` (962×124) | 1.3 MB | 1.3 MB | 1.3 MB | 15 | 256 |

**Start with `mid`.** It is visually indistinguishable from `hi` at banner
size and fits the 500 KB cap most lists use. Drop to `lo` or `tiny` only if
the upload is rejected — `tiny` still holds the "PREMIUM + CRACKED" text
legibly, checked at 2× zoom.

468×60 is the standard across Minecraft server lists. The source is 7.76:1
and 468×60 is 7.8:1, so the scale is effectively distortion-free.

**The site's actual limit is unverified** — minecraftsurvivalservers.net is
blocked by this environment's network egress proxy, so the ladder covers the
range those sites typically use (100 KB to 1 MB) rather than their stated
figure. Check the upload page for the real cap.

## ML Halloween set

`minex-ml-halloween-*` is the MCL banner with the final panel changed to `ML.MINEX.GG` and a Halloween look:
a dusk colour grade (blue sky to purple and orange, green to autumn), Minecraft jack-o'-lanterns along the
bottom edge, two bats crossing the top and bottom margins, and a slow purple mist. It loops seamlessly.

| Rung | fps | Colours | Size |
|---|---|---|---|
| `hi` | 15 | 256 | 586 KB |
| `mid` | 12 | 160 | 411 KB |
| `lo` | 10 | 96 | 281 KB |
| `tiny` | 8 | 64 | 213 KB |
| `native` (962×124) | 15 | 256 | 1.8 MB |

The extra animation makes these heavier than the plain sets (`mid` is 411 KB against 294 KB), so `hi` is over
the 500 KB cap most lists use. Start with `mid`.

How it was made, from the existing source videos (`tools/`):

```bash
mkdir mcl mss ml hl
ffmpeg -i minex-mcl-source.webm mcl/f%03d.png
ffmpeg -i minex-mss-source.webm mss/f%03d.png
python3 -I tools/swap-ip-text.py mcl mss ml      # new IP text, from the MCL glyphs
python3 -I tools/halloween-pass.py ml hl         # Halloween pass
ffmpeg -framerate 25 -i hl/f%03d.png -c:v ffv1 minex-ml-halloween-lossless.mkv
./webm-to-gif.sh minex-ml-halloween-lossless.mkv  # then drop "-lossless" from the names
```

`swap-ip-text.py` can make any other IP made of the letters already in the three sets (M, C, L, S, I, N, E, X,
G and the dot). A new letter still needs a glyph drawn in the same pixel font.

## Regenerating

```bash
./webm-to-gif.sh minex-mss-source.webm
./webm-to-gif.sh minex-mcl-source.webm
./webm-to-gif.sh minex-mcs-source.webm
W=728 H=90 ./webm-to-gif.sh minex-mss-source.webm   # leaderboard size
```

The script names output after the source file, so rename the `-source-`
segment out afterwards to match the files already here.

## Why the files are this big

GIF is capped at 256 colours per frame and has no interframe compression
worth the name. Normally a banner like this optimises well, because only the
text changes and the rest can be stored once — but here the background scene
animates behind the text, so nearly every pixel changes every frame.
`-layers OptimizeTransparency` was tried and saved under 1%.

That leaves frame rate and palette size as the only real levers, which is
what the ladder varies. If a site rejects even `tiny`, the next step is
shortening the loop rather than degrading quality further — dropping one of
the three rotating panels cuts roughly a third of the frames.

## Note

These are server-list banners, not the Reddit creative. The
"PREMIUM + CRACKED" text is a normal thing to state on a server list; the
concern raised in `../creative-notes.md` is specific to paid Reddit ads,
where it risks failing ad review.
