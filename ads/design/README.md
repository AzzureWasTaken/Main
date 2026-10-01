# The graphic

`ad.html` is the design. It renders to all three Reddit sizes, with a no-text
variant of each for the native test.

```bash
./render.sh out                                   # defaults
./render.sh out "bg=shots/spawn-dawn.png&pos=center 30%"
./render.sh out/b3 "head=Nobody has claimed the good land yet.&eyebrow=New map"
```

Open `ad.html?f=4x5` in a browser to design against it live. Query parameters:
`f` (`4x5`/`1x1`/`191`), `head`, `eyebrow`, `sub`, `ip`, `bg`, `pos`, `notext`.

**The backdrop is a placeholder** — your banner, blurred, standing in for the
screenshot slot. Swap it via `bg=` once you have shots (`../shot-list.md`).

## The design decisions

**Photography full-bleed, type in the lower third.** The one structural choice
everything else follows from. A feed ad competes with real posts, so the frame
has to open with an image, not a logo lockup.

**The wordmark is deliberately quiet.** Small, letterspaced, top-left, at about
a quarter the weight of the headline. Your name is not what makes someone stop —
the offer is. The orange square next to it does the brand work that a full logo
would, at a fraction of the attention cost.

**A hairline rule, not a solid bar.** The original had the IP in a filled bar at
the bottom, which is the single strongest "this is an advert" signal in a feed.
A 1px rule carries the same separation without the banner read.

**Archivo 800 for the headline.** Geometric, tight, slightly condensed — it
holds at small sizes where a softer face goes mushy, and the negative tracking
(-0.028em) keeps two lines compact enough to leave the image visible.

**Silkscreen for the IP only.** A pixel face is the one unmistakable Minecraft
signal available, but it is bad at length — so it carries eight characters and
nothing else. Using it for the headline would cost more legibility than the
atmosphere is worth.

**One accent colour.** `#FFA32E`, carried from your banner, on the eyebrow, the
IP and the wordmark square. Everything else is white, dim white, or the scrim.
The restraint is what separates designed from decorated.

**Sentence case with a full stop.** "Free rank when you join." reads as a person
saying something. Title Case with an exclamation mark reads as a billboard, and
this audience is unusually hostile to billboards.

## Changing it

Colours and the backdrop are CSS variables at the top of `ad.html`. Per-format
type sizes are in the `body[data-f=...]` block at the bottom of the stylesheet —
each ratio has its own values rather than scaling one set, because 4:5 takes two
headline lines where 1.91:1 takes one.

Swap `FONT_BOLD`/Archivo for the real MineX brand face if there is one. Archivo
and Silkscreen are vendored in `fonts/` under the SIL Open Font License, so
rendering needs no network.

## Still outstanding

The two rejection risks from `../creative-notes.md` are not design problems and
this file does not solve them: no "Cracked" badge and no Deadpool skin in the
final creative. The placeholder backdrop still shows both, because it is made
from the original banner.
