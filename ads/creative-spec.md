# Rebuilding the creative for paid Reddit

Ordered by how much each change is worth. The first one is worth more than the
rest combined.

Layout references built from your banner are in `creative/ref-*.png`. They show
the **structure**, not the final art — the old logo, sign and badge are still
baked into the backdrop because they are part of the source image. That clutter
is exactly what the rebuild removes.

---

## 1. Stop making a banner

This is the whole game and everything below is detail.

Your current asset is a **server banner**: centred logo, badges in the corners,
offer panel, contact bars. That is the correct design for a server-list entry or
a Discord header, where someone is already browsing servers and comparing them
side by side.

Reddit is a feed of posts. Your ad appears between a screenshot someone posted
and a comment thread. A centred logo lockup with corner badges reads as *an
advertisement* in about 200 milliseconds, and the thumb keeps moving. The
response is not "what's this?" — it is "ad", and scroll.

The creative that works in this slot looks like **something a player posted**: a
real screenshot, off-centre, no logo lockup, no badges, minimal or no overlay
text. Polish is not the goal — belonging in the feed is.

**Action:** build the ad from an actual in-game screenshot, not from the banner.
A good build on your server, shot at a nice time of day, is better raw creative
than anything with a logo on it.

## 2. Right sizes, mobile first

766×555 is not a Reddit slot. Export three:

| Size | Ratio | Priority |
|---|---|---|
| 1080×1350 | 4:5 | **highest** — most feed real estate on mobile |
| 1200×1200 | 1:1 | high |
| 1200×628 | 1.91:1 | lowest — smallest on a phone |

Most Reddit browsing is mobile, and 4:5 occupies roughly twice the vertical
space of 1.91:1 for the same impression. If you only build one, build 4:5.

**Design each one separately.** `creative/ref-feed-1200x628.png` shows why:
cropping the banner to 1.91:1 cuts "Free Rank" in half, because the layout
stacks vertically for a tall frame. Each ratio needs its own composition.

## 3. One message

The current banner carries eight competing elements: logo, "Premium And
Cracked", creeper, "New Update" sign, coin, two characters, the rank panel, an
IP bar and a Discord bar.

In a feed you get **one**. "Free rank when you join" is the strongest — it is
concrete, it is a reason to act now, and it answers "why this server" without a
claim you have to defend.

Everything else moves out of the image:

| Currently in image | Where it belongs |
|---|---|
| "New Update" | Reddit headline field |
| Discord link | the CTA button |
| "Premium And Cracked" | nowhere in paid media (see `creative-notes.md`) |
| Server name | the backdrop, small, or omitted |

The Reddit headline sits directly above your image and is free. Use it for the
second message instead of crowding the first.

## 4. Remove the two rejection risks

Covered in `creative-notes.md`: the **"Premium And Cracked"** badge is a likely
ad-review failure, and the **Deadpool skin** is third-party IP in a commercial
ad. Both need to be out before launch — neither is a style note.

## 5. The IP is not a call to action

`fun.minex.gg` in the image cannot be clicked, cannot be attributed, and on
mobile cannot be used at all — the phone cannot run the game. You are asking
someone to memorise a string and act on it hours later at a different device.

Keep the IP small at the bottom for the desktop minority, make the **clickable
destination the Discord**, and let the Discord hand over the IP when they are at
a PC. That bridges the device gap instead of losing it.

The references put the IP in a quiet bottom bar rather than a shouting one, for
this reason — it is a footnote, not the ask.

## 6. Legibility floor

Feed images render small. The rule that holds up: **cap height no less than 1/14
of image height**, and test by shrinking the export to 400px wide and looking at
it on a phone.

- Headline: white, bold, left-aligned, 2 lines maximum.
- Always sit type on a darkened scrim — Minecraft skies are bright and white
  type vanishes into them.
- Left-align rather than centre. Centred type reads as a poster; left-aligned
  reads as a caption.

## 7. Source resolution

`creative/ref-vertical-1080x1350.png` is visibly soft. Your source is 766px
wide, so the 4:5 export upscales roughly 2.4× and the detail is not there to
recover. Reddit's feed is served to high-DPI phone screens, where soft creative
reads as low-effort.

**Action:** re-export from the original project file at 2× the target, or take
fresh screenshots at 1440p or higher. This is not fixable at the ad end — the
pixels do not exist in the file you have.

## 8. Build a variant with no overlay text at all

Worth one slot on its own. A clean screenshot, no text, no logo, with the whole
message carried by the Reddit headline above it.

This is the "native" hypothesis, and on Reddit it frequently beats designed
creative — not because it is better-looking, but because it does not announce
itself as an ad before anyone has read the headline. Pair it with the Angle D
copy in `ad-copy.md`.

---

## Build checklist

- [ ] Fresh in-game screenshots at 1440p+, no HUD, good lighting
- [ ] 4:5 composed first, then 1:1, then 1.91:1 — separately, not cropped
- [ ] One headline per image, cap height ≥ H/14, on a scrim
- [ ] No "Cracked" badge, no Deadpool, no Discord bar
- [ ] IP small, bottom, de-emphasised
- [ ] A no-text screenshot variant for the native test
- [ ] Shrink to 400px wide and check on an actual phone before uploading
