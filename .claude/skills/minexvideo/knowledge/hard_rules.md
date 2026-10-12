# Hard rules

If a plan breaks these, fix the plan — do not deliver the short. Several are
enforced by `scripts/lint_plan.py`; the rest depend on you.

---

## 1. The gameplay is never covered

The rule almost every other rule comes from. The viewer opened a Minecraft
short to watch Minecraft. A full-screen overlay, even for one second, is an
ad break in a format where the thumb is one centimeter from swiping.

That is why **no full-frame `kind` exists** in this skill, and none should be
added. `image_overlay` is capped at 0.9 of the width and defaults to 0.56.

## 2. Captions always on

Most Shorts are watched muted, especially on first view. If the joke only
lives in the audio, half the audience gets no joke.

`CAPTIONS=0` only when the source already has captions burned in. Never
"because there is already text on screen": `meme_text` and captions do
different jobs — one punches, the other narrates.

## 3. Hook at frame 0

A `hook_title` starting exactly at `0.0`. **The linter requires it and aborts
the render without it.**

The reason is the format, not aesthetics: the stay-or-swipe decision happens
in the first second, with the eyes. If frame 0 is generic gameplay, nothing
promises the video is going anywhere.

The hook is the clip's best promise — usually the punchline, teased. Write it
LAST, once you know what the best thing in the clip is.

## 4. A beat every 2–4 seconds, and not one more

Two symmetric failures:

- **Long gap** (>6 s with nothing): the short feels unedited and gets skipped.
- **Piling up**: two overlays at once compete and neither gets read. The
  linter blocks same-lane overlaps, but noise is possible across lanes — a
  `spotlight` plus a `meme_text` plus three emojis at once is soup.

Healthy coverage: some beat active for **40%–75%** of the clip's duration.

## 5. YouTube Shorts safe zones

- **Top 8%**: the phone's status bar.
- **Bottom 18%**: title, channel name, UI buttons.

Nothing readable lives there. The templates respect this by construction
(`SAFE` in `remotion/src/theme.ts`). When you place things manually with
`x`/`y` (`spotlight`, `speech_bubble`) — they are % of the frame, so `y: 88`
is under YouTube's title and will not be seen.

## 6. Every beat carries a `reason`

One line saying what that overlay adds to that concrete moment. **The linter
requires it.**

It is not documentation — it is a brake on the urge to decorate. If writing
the `reason` produces nothing beyond "looks nice", the beat is surplus. Four
meaningful beats beat twelve ornamental ones.

Bad (reject mentally): "adds dynamism", "so it isn't boring", "support text".
Good: "He says he died for the fifteenth time — the counter makes it funny
instead of anecdotal".

## 7. The ending lands

The last beat is the joke, the surprise, or the tease for the next video.
Never a "and that's it for today". In a looping format, a soft ending is an
exit; a dry punchline invites a rewatch.

Two endings that work:
- **Loop**: the last frame connects to the first and the short rewatches itself.
- **Punch**: the strongest `meme_text` goes at the end, not the middle.

## 8. Editing resources justify themselves like beats do

Speeding a stretch, slowing the hit, freezing a frame, transforming the
voice, switching caption style or crossing a join are editing gestures, not
settings. Each must answer to something happening in the clip.

Ceiling: **one per 8 seconds of short** (`lint_plan.py` counts). Most good
shorts sit far below it: two or three big decisions and nothing else.

The pre-render test: **mentally remove the resource. If the short loses
nothing, it was surplus.** And one case where the answer is always no: when
the reason to add it is that it exists.

Which situation calls for which tool: `editing_choices.md`.

## 9. Karaoke captions are the signature, not an option

Karaoke is the default style. The other two (`palabra`, `bloque`) are for
**segments**: a rapid burst, a blinding biome where the black outline
struggles. Changing the whole short's style is wrong even if it looks good —
it throws away the recognizability the channel is building. Under 45% of the
short in alternate styles, and never switch styles mid-sentence.

## 10. A sound effect only plays where the game would make it

Before placing an effect, ask **which in-game action triggers it on that
exact frame**. If the answer is "none, but it sounds good there" — out.

Real example that shaped this rule: a trap video had four hiss sounds; two
got cut because one played while the player was *breaking* a pressure plate
(a plate being removed does not trigger) and another while digging a hole
(breaking dirt does not trigger a note block). An impossible sound betrays
the edit exactly like an overlay stating a false mechanic — if the game
doesn't do that on that frame, neither does the short.

## 11. Deliver only finished files in clean names

The user must never dig through previews and working files to find what to
upload. The uploadable file gets the clean name (`short-1.mp4`, and
`short-1 with music.mp4` when it exists); everything else stays as working
files. See the delivery layout in `SKILL.md`.
