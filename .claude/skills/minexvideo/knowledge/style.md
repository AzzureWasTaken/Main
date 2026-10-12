# The register: gameplay comedy

Memes, jokes, roleplay, trolling, tricks, minigames. The tone of a friend
telling you what just happened to them — not a tutorial. This is not a taste
detail: it defines every editing decision that follows.

---

## Lessons already paid for

This skill's editing system was battle-tested on a real Minecraft Shorts
channel. These are the verdicts that came back from a real audience and a
real channel owner — treat them as rules:

**What worked, repeat it:**

- **The karaoke captions.** The single most-praised element. Do not turn
  them off, trim them, or replace them with on-screen text.
- **The closer**: a cascade of emoji reactions + a short two-line
  `meme_text` as the final punch. A reliable ending formula.

**What was rejected, and why:**

- **A color band behind the hook title.** It covered half the frame in the
  exact second the viewer decides whether the gameplay is interesting. The
  hook is now emoji + outlined text over raw gameplay. **At the start, the
  thing that must look good is the game.**
- **`item_card` without a real icon.** Without a PNG it renders a flat color
  square that looks like a loading error. If there is no icon, name the
  block in a short `meme_text` or leave it to the captions.
- **Three-line meme texts mid-action.** They block the view. Two lines max,
  placed where the important thing is not happening.
- **Rounded corners, anywhere.** Minecraft has not a single rounded corner.
  A pill or rounded card over a world of cubes reads as an app
  notification. The templates use stepped (blocky) corners — keep it that
  way if you ever touch them.
- **Mixed typography.** All panel text uses the caption font (Montserrat
  900, uppercase, outlined), just smaller. An overlay in another weight
  looks pasted from a different video.

**The pattern behind all of it:** fewer, lighter overlays — and the ones
that stay must feel native to the game and the channel. The gameplay is the
protagonist; the captions already carry the narration. When in doubt between
adding a beat or not: don't.

---

## The pacing

Fast, but with silences. The classic mistake when imitating this style is
putting something on screen at all times; the result is exhausting and,
paradoxically, flat — if everything shouts, nothing stands out.

The shape that works: **tension, tension, punch**. Two or three seconds of
clean gameplay with only captions, then the `meme_text` with its punch zoom.
The gap before is what makes the punch land.

A 40-second short usually carries between 8 and 14 beats.

And pacing is edited in TIME too, not just overlays: speed up what adds
nothing, slow the hit, freeze the blunder. One asymmetry to keep in mind:
**speeding up is invisible and slowing down is expensive**. Nobody notices
you removed eight seconds of digging; everybody notices a slow-mo. Ramps can
be several; the brake is one — the moment that justifies the short.

## The text tone

- **UPPERCASE always** in `meme_text` and `hook_title`. It is the format's
  convention and what reads at a glance on a phone.
- **Three or four words.** A full sentence belongs to the captions, not the
  meme text.
- **Colloquial, spoken English.** "THAT WENT WELL", "NOT THE PLAN", "WORTH
  IT", "RIP INVENTORY". Internet-native, not corporate. No hashtags.
- **Don't repeat the caption word-for-word.** The viewer reads the same
  thing twice in two sizes. The meme adds, it does not duplicate.

## The emojis

The stand-in for the streamer's face. In a short without a facecam, the
emoji tells the viewer what to feel.

| Emoji | Moment |
|---|---|
| 💀 | Death, failure, "it killed me" |
| 😂 | The comic punchline |
| 😱 😰 | Scare, things going wrong |
| 🤑 💎 | Loot, riches |
| 🔥 | Something going really well |
| 🤔 | Right before a reveal |
| 🗿 | Deadpan, no words |

**One or two per moment, never six.** A burst of six emojis turns the frame
into soup and stops meaning anything.

## The color

The palette comes from Minecraft and is used by **meaning**, not taste (see
the table in `SKILL.md`). If redstone red always means "this went wrong",
the viewer reads it without thinking, video after video. A short should have
**one dominant accent** (the plan's global) and use others as marked
exceptions.

## The zooms

The punch zoom is this style's punctuation mark. It goes glued to the
punchline, not sprinkled around.

- **1.15–1.25** — the normal range. Noticeable, not annoying.
- **1.3–1.45** — for the short's big punchline. Once, twice at most.
- **>1.5** — source pixels become visible. No.

A zoom with no punchline behind it is noise.

## What NOT to do

Things that look like the style and ruin it:

- **Filling every silence.** Silence sets up the punch.
- **Meme text that repeats the caption verbatim.**
- **Decorative emojis** unrelated to what happens that second.
- **Different fonts per beat.** Three fonts exist and are assigned by
  function: Luckiest Guy (meme), Bangers (numbers), Montserrat (captions).
- **Explaining the joke** with a `tip_banner` right after the punchline.

## Meme vs. fact

The most common confusion when writing a plan:

- **`meme_text`** → the punchline. Reaction, exaggeration, joke. Top,
  large, with zoom.
- **`tip_banner`** → the information. Something the viewer could write
  down. Bottom, slides in, no zoom.

Mixing them makes both fail: the fact reads as a joke and the joke reads as
a manual.
