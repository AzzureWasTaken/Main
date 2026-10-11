# Templates: full schemas, and which to use when

To see them all in motion:
`cd remotion && npx remotion studio` → composition **Catalogo**.
The catalog's background imitates a biome on purpose: a template that reads
on flat gray but drowns over a jungle is useless.

⚠️ Plan field names are Spanish (shared machinery) — copy them exactly.
All VISIBLE text (titles, labels, captions) is written in English.

---

## `hook_title` — frame 0

Mandatory, always at `0.0`, lasts 1.2–2.5 s. Big emoji on top, outlined
text below, directly over the gameplay — no background band.

```jsonc
{ "kind": "hook_title", "start_sec": 0.0, "end_sec": 2.0,
  "kicker": "DAY 100",            // optional small line above. Use rarely
  "title": "ALMOST\nDIED",        // 2–4 words. \n to split. Max 2 lines
  "emoji": "💀", "accent": "redstone", "reason": "..." }
```

- **Always set `emoji`.** It communicates the most and covers the least: it
  states the short's tone at a glance. A hook without an emoji wastes the
  template.
- `kicker` only if it adds context the title can't hold ("DAY 100",
  "HARDCORE"). It is one more line on screen: if it adds nothing, drop it.

## `meme_text` — the punchline

The most used template and the easiest to ruin.

```jsonc
{ "kind": "meme_text", "start_sec": 4.2, "end_sec": 6.0,
  "text": "THAT WAS\n*THE PLAN*",   // 3-4 words; *word* takes the accent color
  "position": "top",                // top (default) | center | bottom
  "emoji": "😰", "impact": 1,       // impact 0 = no entry shake
  "reason": "..." }
```

- **Default is top.** In Minecraft the important thing happens center-frame.
  `center` only when the text IS the moment.
- `*word*` colors that word with the accent. One per text; two stop
  standing out.
- `impact: 0` removes the entry shake — useful when several run in a row.

## `counter` — when the number IS the joke

"DIED 47 TIMES", "9 HOURS", "1,200 BLOCKS". The number **counts up**, and
that is the whole effect: a written number does not impress, a climbing one
does.

```jsonc
{ "kind": "counter", "start_sec": 8.0, "end_sec": 10.0,
  "value": 247, "from": 0, "label": "DIED", "unit": "TIMES",
  "count_duration": 1.1, "position": "center",
  "reason": "..." }
```

Do not use it for small numbers (under ~10): counting to 4 has no journey
and looks silly. Use `meme_text` there.

## `item_card` — item/block card

For when you name something from the game. The lapsed player does not know
what a netherite pickaxe is; the active player enjoys seeing it.

```jsonc
{ "kind": "item_card", "start_sec": 3.0, "end_sec": 5.5,
  "name": "NETHERITE\nPICKAXE", "sub": "max tier",
  "image_path": "netherite_pickaxe.png",   // assets/items/ or next to the video
  "anchor": "top-right",          // top-left | top-right | bottom-left | bottom-right
  "reason": "..." }
```

- 🚨 **No real icon → do not use this template.** Without `image_path` it
  renders a flat color square that looks like a loading error. Name the
  block in a short `meme_text` instead.
- Icons go in `assets/items/` and are referenced by filename alone. They
  render `pixelated`, so a 16×16 game PNG looks crisp.
- **Watch the lane**: anchored `top-*` (default) it invades the `meme_text`
  band and they clash — the linter blocks it. Need both? Anchor the card
  bottom.

## `tip_banner` — the fact

Usable information, not a joke. Slides in from the left — a calmer gesture
than the punchline's, and that difference tells the viewer "this one is for
writing down".

```jsonc
{ "kind": "tip_banner", "start_sec": 12.0, "end_sec": 15.0,
  "label": "TRICK", "text": "An enchanting table needs 15 bookshelves.",
  "emoji": "📚", "position": "top",
  "reason": "..." }
```

- ⚠️ **In practice use `position: "top"`.** At the bottom it collides with
  two-row captions (captions never turn off), and the banner text becomes
  unreadable. Bottom only works in a gap with no narration.
- A `tip_banner` right after a punchline kills the punchline. Leave air.

## `speech_bubble` — roleplay

Voicing a villager, a creeper, or whoever is causing trouble. Without the
bubble the viewer does not know WHO is talking and the joke collapses.

```jsonc
{ "kind": "speech_bubble", "start_sec": 6.0, "end_sec": 8.5,
  "text": "Maybe... don't do that?", "x": 50, "y": 62,
  "speaker": "VILLAGER",
  "reason": "..." }
```

`x`/`y` in % of the frame point at where the character is. The tail orients
itself; the body stops at the frame edges. Get coordinates from a real
frame: `extract_stills.sh`.

## `image_overlay` — memes, screenshots, clips

A floating tilted card, like a sticker. **Never full-screen** (rule 1).

```jsonc
{ "kind": "image_overlay", "start_sec": 9.0, "end_sec": 11.0,
  "image_path": "reaction.png", "caption": "ME WATCHING THIS",
  "size": 0.56, "anchor": "center", "tilt": -3,
  "reason": "..." }
```

Accepts images and video. Video is always muted: the short's audio is the
voice, and two tracks at once is noise.

## `spotlight` — "look at this"

Darkens everything except a circle, with a pulsing ring. Solves pointing at
something tiny — a block, a distant mob, a HUD number — in a busy frame.

```jsonc
{ "kind": "spotlight", "start_sec": 5.0, "end_sec": 7.0,
  "x": 62, "y": 48, "radius": 16, "dim": 0.72, "label": "did you see it?",
  "reason": "..." }
```

**Use it sparingly.** Darkening the screen five times in 40 seconds stops
meaning "this matters". Once per short, twice at most.

## `emoji_burst` — the reaction

See `style.md` for the emoji-per-moment table. The mechanics:

```jsonc
{ "kind": "emoji_burst", "start_sec": 7.0, "end_sec": 9.0,
  "items": [ { "emoji": "💀", "appear_sec": 7.1 },
             { "emoji": "😂", "appear_sec": 7.6, "size": 1.3 } ],
  "reason": "..." }
```

- Each emoji has its own `appear_sec` (absolute, inside the beat), so they
  cascade instead of appearing at once.
- They float upward while alive — that gives them weight.
- Positions spread themselves on a scattered grid. Only set `left`/`top`
  manually to point at something specific.
- `items` also accept `{ "image_path": "reaction.png", ... }` for custom
  transparent PNG reactions if the user provides them.

## Captions are not a template, but they also choose

Always running, never declared as a beat. Three styles, chosen with the same
judgement as a template — `karaoke` (default, the signature), `palabra`
(bursts), `bloque` (blinding biomes). Doses and criteria:
`editing_choices.md`. All three visible in the **Catalogo** composition.

---

## Adding a new template

If one is ever missing, three places must change or it breaks silently:

1. `remotion/src/templates/TheNew.tsx` — the component.
2. `remotion/src/Short.tsx` — the `Beat` type and the `BeatRenderer` switch.
3. `scripts/lint_plan.py` — `REQUERIDOS`, `CARRILES` (or `carril()`), and
   `DURACION`.

A `kind` known to the linter but not to `Short.tsx` validates and renders
nothing; the reverse gets rejected as unknown. Add it to both, and to
`Showcase.tsx` so it can be eyeballed over a biome background.
