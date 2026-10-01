# Creative review — `creative/v1-original.webp`

The supplied banner (766×555) works as a Discord or website header. As a paid
Reddit ad it has four problems, two of which can get the ad rejected or the
account actioned.

## 1. "Premium And Cracked" — rejection risk

"Cracked" means the server accepts non-premium accounts, i.e. unlicensed copies
of Minecraft. Reddit's advertising policy prohibits ads that promote copyright
infringement or circumventing licensing. A reviewer who knows the term will read
that badge as advertising piracy support, and Mojang's EULA is a separate issue
on top of the ad platform one.

**Recommendation: remove the cracked badge from paid creative and paid copy.**

To be clear about what I am not suggesting — do not reword it into a euphemism
to slip it past review. That is the same ad with worse copy, and if it is caught
the cost lands on the ad account, not on the wording. Either drop it from paid
media entirely, or decide the server is premium-only. What the Discord says to
people who have already arrived is your call and outside Reddit's ad policy.

Dropping it is also not much of a loss commercially. Cracked-seeking players
find servers through server-list sites and search, not paid Reddit ads, and they
monetise far worse than premium players. You would be paying Reddit CPMs to
reach the segment least likely to ever spend.

## 2. Deadpool skin — third-party IP

The left-hand character is Deadpool (Marvel/Disney). Using a recognisable
licensed character in a commercial advertisement is a trademark problem, and
Reddit's review can reject it independently.

**Recommendation: replace with staff/custom MineX skins.** A custom skin also
builds your brand instead of Marvel's.

## 3. Wrong aspect ratio

766×555 is ~1.38:1, which matches none of Reddit's slots and will be cropped or
letterboxed unpredictably in-feed.

| Placement | Size | Ratio |
|---|---|---|
| Feed image (primary) | 1200×628 | 1.91:1 |
| Square | 1200×1200 | 1:1 |
| Vertical / mobile | 1080×1350 | 4:5 |

Mobile is the majority of Reddit traffic, so **1:1 and 4:5 matter more than
1.91:1**. Export all three rather than letting Reddit crop.

## 4. Text density at feed size

An in-feed image is scrolled past in well under a second on a phone. The current
banner carries the logo, two badges, a sign, a coin, a three-line rank panel, an
IP bar and a Discord bar — around eight competing elements.

**Recommendation: one headline in the image, maximum.** "Free rank for every new
player" is the strongest single message; let Reddit's own headline field carry
the rest. Keep the IP bar, drop the duplicate Discord bar (the ad's CTA button
already goes there).

Reddit also penalises image ads that look like dense banner adverts — they read
as intrusive in a feed of posts. The further the creative gets from "banner" and
the closer to "screenshot someone posted", the better it performs.

## Suggested creative set to produce

| ID | Concept | Why |
|---|---|---|
| A | Rank hook. Clean gameplay backdrop, one line: "Free rank when you join." IP bar at the bottom. | Tests the offer directly |
| B | In-game screenshot, no overlay text at all, IP in the corner. | Tests the native/"not an ad" angle |
| C | Before/after or build showcase. | Tests the "this server looks good" angle |

Run A and B against each other first. They are genuinely different hypotheses —
one sells the offer, the other sells the place.

## What is already working

Worth keeping across the rebuild:

- The orange/purple palette is distinctive and survives a dark-mode feed.
- "Free for every new player" removes the usual "is this for me?" hesitation.
- The IP is set in a high-contrast bar and is readable at small sizes.

## Layout references

`creative/ref-feed-1200x628.png`, `ref-square-1200x1200.png` and
`ref-vertical-1080x1350.png` were built from this banner to show the
recommended structure at each Reddit size.

They are **layout references, not final assets.** The old logo, "New Update"
sign and cracked badge are still visible because they are baked into the source
image — removing them is the point of the rebuild, and it needs the original
project file. The vertical reference is also visibly soft: a 766px-wide source
cannot fill a 1080×1350 frame.

Read them for the structure only: one headline, bottom-left, on a scrim, with
the IP demoted to a quiet bar. Full spec in `creative-spec.md`.
