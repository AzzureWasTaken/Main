# Server-list banners

Animated banners converted from 962×124 VP9 sources (6.8s, 25fps). All
cycle SURVIVAL → PAYOUTS → EVENTS → the listing's tracking IP.

| Set | For | Tracking IP |
|---|---|---|
| `minex-mss-*` | minecraftsurvivalservers.net | `mss.minex.gg` |
| `minex-mcl-*` | (MCL listing) | `mcl.minex.gg` |
| `minex-mcs-*` | (MCS listing) | `mcs.minex.gg` |
| `minex-ml-*` | (ML listing) | `ml.minex.gg` |
| `minex-ml-v3-*` | (ML listing) — **sponsored-slot style remake** | `ml.minex.gg` |
| `minex-ml-v4-*` | (ML listing) — **style 3, block walls and light rays** | `ml.minex.gg` |
| `minex-ml-v5-*` | (ML listing) — **style 4, BlossomCraft format** | `ml.minex.gg` |
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

## ML set

`minex-ml-*` is the MCL banner with the final panel changed to `ML.MINEX.GG`, and nothing else changed. It is
the same size as the MCL set:

| Rung | fps | Colours | Size |
|---|---|---|---|
| `hi` | 15 | 256 | 425 KB |
| `mid` | 12 | 160 | 296 KB |
| `lo` | 10 | 96 | 202 KB |
| `tiny` | 8 | 64 | 152 KB |
| `native` (962×124) | 15 | 256 | 1.4 MB |

It is the Halloween set's steps up to the IP swap (`tools/swap-ip-text.py`), without the Halloween pass.

## ML v3 (sponsored-slot style)

`minex-ml-v3-*` is a remake modelled on the top sponsored slots on Minecraft Buzz (Complex Gaming, ManaCube,
TalonMC, Craftadia and the rest): each panel is a loud colour field with drifting stripes and sparkles, one big
headline in a chunky outlined font that drops in with a bounce, a 3D Minecraft prop sliding in on each side, and a diagonal
wipe with a white flash between panels. The IP sits above every headline as a kicker, and the last panel is the
IP itself under "JOIN NOW". The logo block stays on a dark plate on the left: a 3D voxel gold coin with "MineX" across it in chunky cyan-to-purple pixel letters, "MineX" as
extruded gold voxel letters in the game font, drawn the same way as the props
(`tools/props-3d/make_logo_textures.py`), plus the PREMIUM + CRACKED badge.

| Panel | Colour | Props |
|---|---|---|
| SURVIVAL | green | diamond sword, mirrored on both sides |
| PAYOUTS | gold | gold ingot, mirrored on both sides |
| EVENTS | magenta | firework rocket, mirrored on both sides, falling confetti |
| ML.MINEX.GG | blue | diamond sword, mirrored on both sides |

| File | Size |
|---|---|
| `468x60-hi` | 560 KB |
| `468x60-mid` | 407 KB |
| `468x60-lo` | 289 KB |
| `468x60-tiny` | 206 KB |
| `1092x140-native` | 1.8 MB |
| `1092x140.webm` | 328 KB (the format Minecraft Buzz itself serves) |

```bash
python3 -I tools/sponsor-banner.py tools/sponsor-assets frames ML.MINEX.GG    # 170 frames, 1092x140
ffmpeg -framerate 25 -i frames/f%03d.png -c:v ffv1 minex-ml-v3-lossless.mkv
./webm-to-gif.sh minex-ml-v3-lossless.mkv                                    # 468x60 ladder
W=1092 H=140 ./webm-to-gif.sh minex-ml-v3-lossless.mkv                       # full size
```

The third argument is the IP. Panels, colours and props are the `PANELS` list at the top of
`tools/sponsor-banner.py`; new props come from `tools/props-3d/`.

## ML v4 (style 3: block walls and light rays)

`minex-ml-v4-*` keeps v3's idea (one mode per panel, the IP as a kicker) with its own look and layout:

- the MineX logo block sits on the **right**, on a plate slanting the other way
- one big **3D block** spins in on the left of each panel, matching the panel's wall: grass, gold, TNT, diamond
- each panel's background is a scrolling wall of that block, tinted in the panel colour
- light rays rotate behind the headline
- the headline is gold in Luckiest Guy (a rounder bubbly face) and drops in with a bounce
- the kicker sits under the headline as a pill tag
- its own colours: lime, red, indigo and teal
- panels change with a vertical shutter

| File | Size |
|---|---|
| `468x60-hi` | 659 KB |
| `468x60-mid` | 489 KB |
| `468x60-lo` | 336 KB |
| `468x60-tiny` | 240 KB |
| `1092x140-native` | 2.1 MB |
| `1092x140.webm` | 455 KB |

```bash
python3 -I tools/style3-banner.py tools/sponsor-assets frames ML.MINEX.GG
```
then encode as for v3.

## ML v5 (style 4: BlossomCraft format)

`minex-ml-v5-*` copies the format of the BlossomCraft banner on Minecraft Buzz. Full bleed, no logo plate; each
panel is one bright colour (orange, pink, lilac, cyan) with a broad darker swirl turning behind it.

- Panel 1 is the brand line-up, like BlossomCraft's "1.21 | logo | JAVA + BEDROCK CROSSPLAY": the MineX coin, the
  voxel MineX wordmark, then PREMIUM + CRACKED over the IP.
- Panels 2-4 are a thin kicker over a huge bold white word (Montserrat), with the panel's 3D Minecraft item
  mirrored each side, as in the other styles: BUILD, EXPLORE & / SURVIVAL (diamond swords), GRIND FOR REAL /
  PAYOUTS (gold ingots), COMPETE IN / EVENTS (fireworks).
- Small themed items (diamonds, emeralds, nether stars, gold and TNT blocks) drift in the outer corners to fill
  the width, and the headline and items are sized up.
- Between panels the giant MineX coin sweeps across and reveals the next panel; text zooms in out of a blur and
  the items pop up from the bottom edge.

| File | Size |
|---|---|
| `468x60-hi` | 669 KB |
| `468x60-mid` | 467 KB |
| `468x60-lo` | 345 KB |
| `468x60-tiny` | 248 KB |
| `1092x140-native` | 2.3 MB |

```bash
python3 -I tools/blossom-banner.py tools/sponsor-assets frames ML.MINEX.GG
```
then encode as for v3.

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
