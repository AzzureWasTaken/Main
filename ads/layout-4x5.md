# The 4:5 layout, in detail

1080×1350. Build this one first and build it properly — it takes roughly twice
the vertical space of a 1.91:1 ad in a mobile feed for the same impression, and
mobile is where the audience is.

Implemented in `build-creative.sh`; this is the reasoning behind the numbers, so
you can deviate from them on purpose rather than by accident.

## The grid

```
┌─────────────────────────────┐  0
│                             │
│   ░░░ IMAGE ZONE ░░░        │     subject lives here,
│                             │     upper third
│                             │
├─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┤  608   scrim begins (45%)
│                             │
│                             │
│                             │
│  Free rank when             │  ~1090  headline baseline
│  you join.                  │
│  New update live now        │  ~1192  subline
├─────────────────────────────┤  1250  IP bar top
│  JAVA   fun.minex.gg        │
└─────────────────────────────┘  1350
```

| Element | Value |
|---|---|
| Frame | 1080 × 1350 |
| Side padding | 58px |
| IP bar height | 100px |
| Headline | 86pt bold, 2 lines max, +9 interline |
| Subline | 33pt regular |
| Scrim | transparent → black, 86% max opacity, bottom-up |
| Corner safety | keep content 24px inside — feed cards round the corners |

## Why each number

**58px side padding (5.4%).** Below about 4% the type looks like it is falling
off the card; above 7% the headline loses too much line length and wraps to
three lines. 5–6% is the usable band.

**86pt headline.** The legibility floor is cap height ≥ H/14. At 1350 tall that
is ~96px of line height, and 86pt bold lands just above it. This is sized for
the feed thumbnail, not for how it looks at full size on your monitor — which is
the mistake that produces most unreadable ads.

**Two lines, hard maximum.** Three lines of 86pt eats the lower half of the
frame and starts covering the image you paid to shoot. If the headline will not
fit in two lines, the headline is too long — Reddit's own headline field above
the image is free and unlimited by comparison.

**Scrim from 45%.** Minecraft skies and sand are bright. White type on an
unprotected screenshot is illegible at feed size roughly half the time,
depending on time of day. The gradient costs you nothing visually at the top and
guarantees contrast at the bottom.

**100px IP bar (7.4%).** Big enough to read, small enough to read as a footnote.
The IP is deliberately not the hero — see `creative-spec.md` on why the Discord
is the actual destination.

**Subject in the upper third.** The composer fills 4:5 from the top edge
(`-gravity North`), so the bottom of a wide screenshot is what gets cut. Compose
for that at capture time rather than fighting it afterwards.

## Type

- **Left-aligned, not centred.** Centred type reads as a poster. Left-aligned
  reads as a caption on something real, which is the register that works here.
- **Sentence case**, with a full stop. "Free rank when you join." reads as a
  person saying a thing. "FREE RANK WHEN YOU JOIN!" reads as a billboard.
- **One weight.** Bold headline, regular subline. Introducing a third style is
  where server creative usually tips into looking like a banner again.
- Swap `FONT_BOLD` in the script for the real MineX face. DejaVu is a stand-in
  so the references build anywhere.

## Colour

Carried over from your existing banner, which was already doing this part well:

| Token | Hex | Use |
|---|---|---|
| Headline | `#FFFFFF` | — |
| Subline | `#C9C2E8` | muted lilac, recedes from the headline |
| Bar background | `#1A1424` | near-black with a purple cast |
| Bar label | `#8C8099` | "JAVA" — quiet |
| Bar IP | `#FFA32E` | the one warm accent |

Exactly one accent colour in the frame. The orange reads as MineX and survives a
dark-mode feed, which is how most of Reddit is browsing.

## Check before upload

1. Export, then **shrink to 400px wide** and look at it on a phone. That is
   closer to the real feed size than anything on your monitor.
2. Is the headline readable in under a second?
3. Does anything other than the headline compete for first read?
4. Does it look like a post, or like an advert?

Question 4 is the one that decides whether this works.
