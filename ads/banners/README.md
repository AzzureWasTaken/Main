# Server-list banners

Animated banner for minecraftsurvivalservers.net, converted from
`minex-mss-source.webm` (962×124, VP9, 6.8s, 25fps).

Cycles SURVIVAL → PAYOUTS → EVENTS → `mss.minex.gg`.

## Pick by the site's upload cap

| File | Size | fps | Colours |
|---|---|---|---|
| `minex-mss-468x60-hi.gif` | 412 KB | 15 | 256 |
| `minex-mss-468x60-mid.gif` | 294 KB | 12 | 160 |
| `minex-mss-468x60-lo.gif` | 203 KB | 10 | 96 |
| `minex-mss-468x60-tiny.gif` | 153 KB | 8 | 64 |
| `minex-mss-962x124-native.gif` | 1.3 MB | 15 | 256 |

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

## Regenerating

```bash
./webm-to-gif.sh minex-mss-source.webm
W=728 H=90 ./webm-to-gif.sh minex-mss-source.webm   # leaderboard size
```

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
