# Screenshot shot list

The creative is only as good as the source. Your current asset is 766px wide,
which is why the vertical reference came out soft. Everything below is aimed at
producing material that holds up at 1080×1350 on a high-DPI phone.

## One honesty rule before anything else

**Shoot the server as players will actually see it.**

Shaders make any Minecraft screenshot look dramatically better, which is why
every server ad uses them. If a new player joins and gets flat vanilla lighting
instead of what the ad showed, the gap is obvious, and on Reddit it gets said
out loud in the comments under your own ad. A top comment reading "it looks
nothing like that" costs more than the clicks are worth, and you pay for the
impressions that carry it.

So either:

- shoot in vanilla Fancy graphics, which is what most players see; or
- shoot with shaders **and** say so in the Discord, with a pinned link to the
  pack — then it is a showcase, not a claim.

What you should not do is shoot with a heavy shader pack and let people assume
that is the default experience. Good lighting and a good time of day will carry
a vanilla screenshot a long way without needing that.

## Client settings

| Setting | Value | Why |
|---|---|---|
| Graphics | Fancy or Fabulous | Fast graphics flattens everything |
| Render distance | 24–32 chunks | Depth and background detail |
| Smooth lighting | Maximum | Kills the blocky shading artefacts |
| Clouds | Fancy | Sky reads as empty without them |
| Entity shadows | On | Grounds characters |
| Brightness | Default | "Bright" flattens the image completely |
| FOV | 70 normal, 85 for big builds | 90+ distorts at the edges |
| Resolution | 2560×1440 minimum | **The thing that actually matters** |

Run borderless fullscreen on the largest display you have access to. `F2` saves
a screenshot at the window's resolution, so a 1080p window gives a 1080p file
and you are straight back to the upscaling problem. 1440p is the floor; 4K is
better.

Save and keep the **PNG** that Minecraft writes. Do not convert to JPG at any
point — Reddit re-compresses on upload, and compressing twice is where the mush
comes from.

## Before you shoot

```
/weather clear
/gamerule doDaylightCycle false
/time set 23000
```

Freezing the daylight cycle is the one that saves real time. Without it the
light drifts between shots and the set will not cut together.

Times worth trying: `23000` dawn, `1000` bright morning, `12000` early dusk.
Dawn and dusk give long shadows and warm light; midday (`6000`) is flat and is
what everyone else's screenshots look like.

`F1` hides the HUD. `F5` twice gives a front-facing third-person view for
character shots.

## The shots

Six, in priority order. The first three are enough to launch.

**1 — Spawn hero.** Elevated, slightly off-centre, at dawn. The establishing
shot of the place. This is your primary 4:5.

**2 — Populated.** Real players doing real things: a build in progress, a market,
a group crossing a bridge. Not staged in a line. Activity is the single most
persuasive thing you can show, because an empty server is every player's fear
and this answers it without a word of copy.

**3 — The signature build.** Whatever is genuinely the most impressive thing on
the server. If nothing qualifies, that is useful to know before you spend on
ads.

**4 — Scale.** Distant, high, showing how far the world goes. Sells "there is
room here", which pairs with the B3 headline about maps not being strip-mined.

**5 — Intimate.** A small base at night, lanterns on, cosy. Different emotional
register to the hero shot and often outperforms it — it looks like a place to
live rather than a place to be advertised at.

**6 — Native candidate.** Deliberately ordinary: a nice view, well composed, that
could plausibly be a screenshot someone posted. No grand architecture. This
feeds the no-text variant.

## Framing for the 4:5 crop

The thing that makes a screenshot usable as an ad rather than just nice:

**Leave the bottom 40% quiet.** Ground, water, mist, open path — low detail,
low contrast. That is where the headline sits. A screenshot with a detailed
build running to the bottom edge cannot take type without the type fighting it.

**Put the subject in the upper third.** The composer crops from the top edge for
4:5 and 1:1, so anything important low in the frame gets cut.

**Shoot wider than you need.** You are producing three different ratios from the
same session; headroom on all sides is what makes that possible.

## Then

```bash
./build-creative.sh screenshots/spawn-dawn.png out/
```

It writes all three sizes plus a no-text variant of each, and warns if the
source is too small. Headline and IP are environment variables at the top of the
script:

```bash
HEADLINE=$'Nobody has claimed\nthe good land yet.' \
SUBLINE="New map, new update" \
  ./build-creative.sh screenshots/scale-shot.png out/b3/
```
