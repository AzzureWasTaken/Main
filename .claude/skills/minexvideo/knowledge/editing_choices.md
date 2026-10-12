# Editing choices: which moment calls for which tool

This file is what separates an *edited* short from a *decorated* one.

`templates.md` answers "which overlay do I use". This answers the earlier,
harder question: **what is happening to THIS moment of the clip, and which
editing gesture says that**. Speeding up, slowing down, freezing, changing
the voice, switching captions, moving the camera or crossing a join are not
effects: they are punctuation.

**The rule that orders everything else:** a resource goes in when the
material asks for it, not when it is available. A short with two well-placed
gestures looks more professional than one with nine. If removing a resource
loses nothing, it was surplus — that is the test, not "does it look cool?".

---

## Step 0: read the material before deciding anything

Before writing a single beat, run the clip through four questions. The
answers give you most of the edit:

1. **Where is the hit?** The moment that justifies the short: the death, the
   discovery, the number, the dumb face. There is almost always exactly one.
   Everything else exists to get there.
2. **Which stretches add nothing?** Walking, mining, waiting, climbing.
   Check them against the transcript: if nothing usable is said there, they
   are ramp candidates.
3. **Where does the narration breathe?** The gaps in `words.json` are where
   freezes, transitions and punchlines fit without stepping on a syllable.
4. **Which emotion dominates?** Fear, pride, embarrassment, greed, rage. The
   register must hold: a dumb-comedy short with an epic slow-mo reads as two
   videos glued together.

A well-edited short usually comes out of this with **two or three big
decisions**, not ten small ones.

---

## The table: situation → gesture

| What happens in the clip | The gesture that says it | Never |
|---|---|---|
| Long stretch with nothing (walking, mining, building) | `ritmo` ramp x2–x4, `"silencio": true` if the audio turns to mush | Speeding past x2 where something is being explained |
| The hit: death, fall, explosion | `ritmo` x0.5 with `"tono": "sigue"` + punch zoom with `shake` | Slow-mo over ~1.5 real seconds; it drags forever |
| The blunder, the "and that's where it went wrong" | `ritmo` freeze 0.4–0.8 s + `meme_text` on top | Freezing mid-word |
| Reveal of something already on screen | `zoom` **pull** (starts close, opens up) | A punch: punches punctuate, they don't reveal |
| Tension rising toward a payoff | `zoom` **push** across the whole beat | Push and punch together; they cancel out |
| Pointing at something tiny (a mob far away, a HUD number) | `spotlight`, or `zoom` with `focus` on that point | A centered zoom when the action is in a corner |
| Rapid-fire listing, countdowns | `subtitulos` style `palabra` on that segment | Changing the whole short's style |
| Blinding biome (snow, desert, the End) and captions drown | `subtitulos` style `bloque` on that segment | Making the karaoke bigger |
| Voicing a villager, a mob, another player | `efectos_voz` `agudo` | A `speech_bubble` AND the voice effect: says it twice |
| Playing the villain, mock-threats, "serious mode" | `efectos_voz` `grave` | More than 2–3 s straight |
| "The server speaking", announcements | `efectos_voz` `megafono` | Over normal narration: sounds like a broken mic |
| World/day/place change between cuts | `transiciones` `pixelize` or `fadeblack` | A transition where both sides are talking |
| The same motion continues into the next cut | `transiciones` `smoothleft`/`smoothright` | A `pixelize`: it would claim a jump that doesn't exist |
| Hard impact at the join (explosion, hit) | `transiciones` `fadewhite` short (0.15–0.25 s) | Chained flashes |
| The zoom or hard cut you already decided on | `sfx` `whoosh.mp3` at the instant of the gesture | A whoosh where the camera doesn't move |
| The punchline that already carries a punch zoom | `sfx` `impact.mp3` nailed to the frame | Adding it when the clip already has its own loud hit |
| A `counter` counting up or an `item_card` entering | `sfx` `ding.mp3` on appearance | A ding per digit: sounds like a slot machine |
| Tension building to a reveal | `sfx` `riser.mp3` ending EXACTLY at the reveal | A riser that lands on nothing |
| The fail, the comic disaster | `sfx` `fail.mp3` right after the blunder | On top of the sentence: it eats the voice |

---

## Sound: the single effect

Best result-per-effort resource in the whole skill. A short with three
well-nailed effects feels "edited"; the same short without them feels
"recorded". And unlike music, it competes with nothing.

The governing rule: **the effect underlines a gesture that ALREADY exists in
the edit.** It does not invent energy, it confirms it.

- **One per gesture, not one per second.** A zoom, a cut, a counter, a
  punchline. If the gesture is not in the plan, the effect is surplus.
- **Nail it to the frame, not "thereabouts".** An impact 200 ms late reads
  as a sync error. Use the stills or `words.json` to find the instant.
- **The riser is the only one placed BEFORE**: it must die exactly where the
  reveal arrives.
- **Never on top of a key word.** The effect goes in the gap or on the dead
  syllable. The voice always wins.
- **Three is a good number. Six starts being a lot.** The linter warns at
  eight — that is the system ceiling, not the goal.

## Ritmo: speed up, slow down, freeze

The most powerful resource and the most invisible when done right.

**Speeding up (factor 1.5–4).** What you speed up is what the viewer has
already understood. Once they see you are mining, they know you will mine
for a while: the rest of that stretch is borrowed time.

- With narration on top, the real ceiling is **x1.6**. Above it, garble.
- Without narration, **x2–x4** freely. `"silencio": true` also removes the
  chipmunk-buzz of compressed game audio.
- A ramp under 1.5 s does not read as a speed-up, it reads as a playback
  glitch. Short dead gaps: `cortar_silencios`, not a ramp.

**Slowing down (factor 0.4–0.7).** Only on the hit, and **short**: 0.6–1.5
real seconds. Long slow-mo in a comedy short kills the joke — comedy is
timing, and slow time has no punchline.

- With `"tono": "sigue"` the voice drops with the image. That low "vwooom"
  **is** the gag; slow-mo with normal-pitch voice sounds like an error.
- If something the viewer must understand is said there, do not slow it.

**Freezing (0.4–0.8 s).** The "look at what I just did" gesture. It works by
breaking the expectation of motion, so spend it **once per short**.

- It must land in a narration gap: it inserts silence, and silence mid-word
  sounds like a broken video. The linter checks this against the transcript.
- A freeze with nothing on top is a stalled video. Put the `meme_text` ON
  the freeze, not before or after.

**Dose:** up to four ritmo operations in a 60 s short, and that is already a
lot. Normal is one or two.

## Voice: dubbing yourself

A voice effect does a speech bubble's job without covering a pixel of
gameplay. But it ages fast: funny the first time, "why is there a filter"
the fourth.

- **Applies to a SENTENCE, not a paragraph.** 0.8–3 seconds.
- **Max two per short**, three if all different and far apart.
- **`intensidad` is a dial, not a switch.** 1.0 stays fully intelligible;
  1.4 is caricature. For anything that must be UNDERSTOOD, stay at 1.0.
- `eco` is the most dangerous: over noisy gameplay it smears words. One
  short, isolated sentence — or skip it.

Content rule: processed voice must not carry new information. If the fact
matters, say it in the normal voice and keep the effect for the reaction.

## Captions: when to stop being karaoke

Karaoke is the default and the signature. The other two are for SEGMENTS,
each solving one concrete problem:

- **`palabra`** — one huge word at a time. For bursts: listings ("wood,
  stone, iron, DIAMONDS"), countdowns, chopped phrases. Reads at a glance
  even when the gameplay is flying. Great right after a speed ramp.
- **`bloque`** — the sentence with the active word in a colored box. Solves
  a physical problem: over snow, desert or the End the black outline barely
  survives. Also underlines the key sentence without spending `enfasis`.

**Dose:** under 45% of the short, and every segment covers whole sentences —
switching styles mid-sentence looks like a render bug.

## Camera: the five moves

The source is a static take. The camera is what the edit adds, and each
curve means something:

| Type | Says | Typical scale |
|---|---|---|
| `punch` | A hit. Glued to the punchline. | 1.2–1.3 |
| `snap` | An even drier hit, for chained cuts. | 1.15–1.25 |
| `rampa` | "Look at this". Neutral move-in. | 1.15–1.25 |
| `push` | Rising tension. Lasts the whole beat. | 1.2–1.3 |
| `pull` | Reveal: opens up and context appears. | 1.25–1.4 |

Three things that raise the grade and are almost never used:

- **`focus`.** Zoom toward where the thing happens, not the center. The
  difference between a camera that looks and one that merely enlarges. Get
  coordinates from a real frame via `extract_stills.sh`.
- **`shake`.** 0.4–1.2% of width, on falls, explosions, hits. Decays on its
  own. Above 1.5 the scale needed to hide the borders eats the framing.
- **`rot`.** One to one-and-a-half degrees on a big punch. Not consciously
  visible; makes the hit feel physical. Above 2.5 it is visible and queasy.

**Dose:** at most two zooms of 1.3+ per short — the big zoom is the
punchline, and with four of them none punches. The rest live at 1.15–1.25.

## Transitions: only at joins, and for a reason

They exist only where there is a real cut between clips, and they do two
jobs: hide that there were several recordings, and **state the relation**
between the two sides.

- `pixelize`, `fadeblack`, `slideup` → *we're going somewhere/somewhen else*.
- `smoothleft` / `smoothright` / `smoothup` → *the same action continues*.
- `fadewhite` (0.15–0.25 s) → *impact*: explosion, hit, surprise.
- `corte` → the norm. A hard cut is a transition and usually the right one.

Hard rules:

- **Duration 0.2–0.5 s.** Above half a second the transition watches itself.
- **It must fit in a silence.** Audio is summed at unity, so no syllable is
  lost, but if both sides talk during the overlap you hear two voices. The
  assembly measures it and warns; obey it.
- **At most two distinct languages of transition per short.**
- Changing a transition's TYPE moves no plan times. Changing its DURATION
  moves everything after it.

---

## Combos that work

The three or four "chords" of the format. Each is one composite gesture, not
several in a row:

**The hit.** Ramp x0.5 with `tono: sigue` + punch zoom 1.3 with `shake` +
two-word `meme_text`. All at the same instant, all short. The most expensive
thing in the short: once, on the moment that justifies it.

**The frozen blunder.** 0.6 s freeze in the gap right after the fail +
`meme_text` on top + `emoji_burst` 💀 on unfreeze.

**The montage.** Ramp x2.5 with `silencio` over the building stretch +
`palabra` captions on that segment + a `counter` at the end with the block
count. Rhythm, caption and number say the same thing from three places.

**The reveal.** Pull zoom 1.35→1.0 over 1.5 s while the narration says what
it is. No text on top: the gesture is the text.

**The closer.** `emoji_burst` cascading in + a short two-line `meme_text` as
the final punch. A reliable ending formula.

## Combos that kill each other

- **`shake` + `spotlight`**: a static circle over a trembling image — the
  circle's edge visibly swims.
- **`palabra` style + `meme_text` at once**: two huge texts competing. Pick.
- **Transition + zoom at the same instant**: the transition IS the movement.
- **`push` and `punch` overlapping**: the bigger scale wins, the other is
  wasted work.
- **Voice effect over a ramped segment**: pitch is already altered; the
  result is unrecognizable.
- **Freeze right before a transition**: two brakes in a row; the second
  never reads.

---

## The budget

Count the special resources in the plan: ritmo operations + voice effects +
alternate caption segments + transitions + zooms with `shake`/`push`/`pull`.

**Roughly one fits per 8 seconds of short.** A 40 s short holds five; a 15 s
one, two. `lint_plan.py` counts and warns — but the number is a ceiling, not
a target.

The final filter before rendering: **for each resource, say out loud which
moment of the clip asked for it.** No answer → out.

---

## Don't make two shorts the same

A channel needs two opposite things at once: **recognizability** and **not
boring**. What repeats is identity — typography, colors, the caption style.
What must NOT repeat is the editing recipe. If the last five shorts all open
with `hook_title` + push, drop a `meme_text` at 4 s and close with
`emoji_burst`, the sixth is predictable and gets swiped.

When cutting several shorts from one VOD, give each a **dominant register**
and rotate:

| Register | Leans on | Feels like |
|---|---|---|
| **Rhythm** | ramps, freezes, slow-mo | nervy montage, many cuts |
| **Voice** | `efectos_voz`, `speech_bubble` | sketch, roleplay, dubbing mobs |
| **Data** | `item_card`, `tip_banner`, `counter` | tutorial, "did you know" |
| **Reaction** | `emoji_burst`, `meme_text` | pure comedy, reacting |
| **Sound** | nailed `sfx`, silences, a riser | tension, reveal |

The variation is not decorative: **it comes from the material**. A building
clip asks for data; a dumb death asks for reaction; a troll asks for rhythm.

The test: **show someone the last three shorts. If they say "it's the same
video with different gameplay", the problem is not the gameplay.**
